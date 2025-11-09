"""
High-performance sender module for Beam Transfer.
"""

from __future__ import annotations

import asyncio
import contextlib
import math
import os
import queue
import socket
import struct
import tarfile
import threading
import zlib
from dataclasses import dataclass
from typing import List, Optional, Sequence

from tqdm import tqdm

from beam_transfer.network import FILE_TRANSFER_PORT, NetworkDiscovery
from beam_transfer.security import AESCTREncryptor, generate_transfer_key, get_key_hash
from beam_transfer.utils import safe_print


FLAG_COMPRESS = 0x01
FLAG_MULTI_STREAM = 0x02
FLAG_TAR_ARCHIVE = 0x04


@dataclass
class TransferOptions:
    """Runtime options for advanced transfers."""

    chunk_size: int = 4 * 1024 * 1024
    enable_compression: bool = True
    compression_level: int = 1
    parallel_streams: int = 1

    def normalized(self) -> "TransferOptions":
        chunk = max(256 * 1024, self.chunk_size)
        level = min(9, max(0, self.compression_level))
        streams = max(1, min(4, self.parallel_streams))
        return TransferOptions(chunk, self.enable_compression, level, streams)


@dataclass
class StreamSegment:
    start: int
    length: int
    iv: bytes


class FileSender:
    """Handle file sending operations with async, compression, and parallel support."""

    def __init__(
        self,
        filepath: str,
        transfer_key: Optional[str] = None,
        *,
        options: Optional[TransferOptions] = None,
    ):
        self.filepath = filepath
        self.filename = os.path.basename(os.path.normpath(filepath))
        self.is_directory = os.path.isdir(filepath)
        self.file_size = 0 if self.is_directory else os.path.getsize(filepath)
        self.transfer_key = transfer_key or generate_transfer_key()
        self.options = (options or TransferOptions()).normalized()

    def find_receiver(self) -> Optional[tuple]:
        """Discover available receivers on the network."""
        discovery = NetworkDiscovery()
        message = f"SENDER_REQUEST:{self.filename}:{self.file_size}:{self.transfer_key}"
        devices = discovery.discover_devices(message)

        if devices:
            local_ips = self._get_local_ipv4_addresses()
            local_ips.update({discovery.local_ip, "127.0.0.1"})
            non_local = [d for d in devices if d[0] not in local_ips]
            if non_local:
                return non_local[0]
            return devices[0]
        return None

    def _get_local_ipv4_addresses(self) -> set:
        addresses = {"127.0.0.1"}
        try:
            hostname = socket.gethostname()
            _, _, ip_list = socket.gethostbyname_ex(hostname)
            addresses.update(ip_list)
        except Exception:
            pass
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            addresses.add(s.getsockname()[0])
            s.close()
        except Exception:
            pass
        return {ip for ip in addresses if ":" not in ip}

    def send_file(self, receiver_ip: str) -> bool:
        """Entry-point for sending a file with the configured options."""
        print(f"Connecting to receiver at {receiver_ip}...")
        print(f"Transfer Key: {self.transfer_key}")
        if self.is_directory:
            safe_print(f"[INFO] Packaging directory '{self.filename}' for streaming transfer...")
        try:
            return asyncio.run(self._async_send_file(receiver_ip))
        except KeyboardInterrupt:
            safe_print("\n[WARNING] Transfer cancelled by user.")
            return False
        except Exception as exc:
            safe_print(f"\n[ERROR] Error sending file: {exc}")
            return False

    async def _async_send_file(self, receiver_ip: str) -> bool:
        reader, writer = await asyncio.open_connection(receiver_ip, FILE_TRANSFER_PORT)
        self._configure_socket(writer.get_extra_info("socket"))

        key_hash = get_key_hash(self.transfer_key)
        options = self.options

        if self.is_directory:
            stream_count = 1
            segments = [StreamSegment(start=0, length=0, iv=os.urandom(16))]
        else:
            stream_count = min(options.parallel_streams, self._suggest_stream_count())
            segments = self._build_segments(stream_count)

        flags = 0
        if options.enable_compression and options.compression_level > 0:
            flags |= FLAG_COMPRESS
        if stream_count > 1:
            flags |= FLAG_MULTI_STREAM
        if self.is_directory:
            flags |= FLAG_TAR_ARCHIVE

        transfer_id = os.urandom(16)
        header = self._build_header(
            key_hash=key_hash,
            flags=flags,
            transfer_id=transfer_id,
            segments=segments,
            options=options,
        )
        writer.write(header)
        await writer.drain()

        try:
            response = await asyncio.wait_for(reader.readexactly(1), timeout=30)
        except asyncio.TimeoutError as exc:
            raise RuntimeError("Timed out waiting for receiver confirmation") from exc

        if response != b"Y":
            safe_print("Receiver declined the transfer.")
            writer.close()
            await writer.wait_closed()
            return False

        progress_total = self.file_size if self.file_size else None
        progress = tqdm(total=progress_total, unit="B", unit_scale=True, desc="Uploading")
        stream_tasks: List[asyncio.Task] = []
        loop = asyncio.get_running_loop()

        try:
            if self.is_directory:
                await self._send_directory_stream(
                    writer=writer,
                    options=options,
                    key_hash=key_hash,
                    iv=segments[0].iv,
                    progress=progress,
                    loop=loop,
                )
            else:
                stream_tasks.append(
                    asyncio.create_task(
                        self._send_stream(
                            stream_index=0,
                            segment=segments[0],
                            writer=writer,
                            options=options,
                            key_hash=key_hash,
                            progress=progress,
                            loop=loop,
                            close_writer=False,
                        )
                    )
                )

                for idx in range(1, stream_count):
                    sr, sw = await asyncio.open_connection(receiver_ip, FILE_TRANSFER_PORT)
                    self._configure_socket(sw.get_extra_info("socket"))
                    handshake = struct.pack("!4sH16s", b"STRM", idx, transfer_id)
                    sw.write(handshake)
                    await sw.drain()
                    stream_tasks.append(
                        asyncio.create_task(
                            self._send_stream(
                                stream_index=idx,
                                segment=segments[idx],
                                writer=sw,
                                options=options,
                                key_hash=key_hash,
                                progress=progress,
                                loop=loop,
                                close_writer=True,
                            )
                        )
                    )

                await asyncio.gather(*stream_tasks)

            try:
                final_response = await asyncio.wait_for(reader.readexactly(1), timeout=30)
            except asyncio.TimeoutError as exc:
                raise RuntimeError("Timed out waiting for receiver acknowledgement") from exc

            if final_response == b"Y":
                safe_print("\n[OK] Transfer completed successfully!")
                return True

            safe_print("\n[ERROR] Receiver reported a failure.")
            return False

        finally:
            progress.close()
            for task in stream_tasks:
                if not task.done():
                    task.cancel()
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()

    def _suggest_stream_count(self) -> int:
        if self.file_size < 256 * 1024 * 1024:
            return 1
        return self.options.parallel_streams

    def _build_segments(self, stream_count: int) -> Sequence[StreamSegment]:
        segments: List[StreamSegment] = []
        remaining = self.file_size
        offset = 0
        base = math.ceil(self.file_size / stream_count) if stream_count else self.file_size
        for _ in range(stream_count):
            length = min(base, remaining)
            segments.append(StreamSegment(start=offset, length=length, iv=os.urandom(16)))
            remaining -= length
            offset += length
        if segments:
            last = segments[-1]
            if last.start + last.length < self.file_size:
                segments[-1] = StreamSegment(
                    start=last.start,
                    length=self.file_size - last.start,
                    iv=last.iv,
                )
        return segments

    def _build_header(
        self,
        *,
        key_hash: bytes,
        flags: int,
        transfer_id: bytes,
        segments: Sequence[StreamSegment],
        options: TransferOptions,
    ) -> bytes:
        filename_bytes = self.filename.encode()
        parts = [
            struct.pack("!I", len(filename_bytes)),
            filename_bytes,
            struct.pack("!Q", self.file_size),
            key_hash,
            struct.pack(
                "!BBHI",
                flags,
                options.compression_level if options.enable_compression and options.compression_level > 0 else 0,
                len(segments),
                options.chunk_size,
            ),
            transfer_id,
        ]
        for segment in segments:
            parts.append(segment.iv)
            parts.append(struct.pack("!QQ", segment.start, segment.length))
        return b"".join(parts)

    async def _send_stream(
        self,
        *,
        stream_index: int,
        segment: StreamSegment,
        writer: asyncio.StreamWriter,
        options: TransferOptions,
        key_hash: bytes,
        progress: tqdm,
        loop: asyncio.AbstractEventLoop,
        close_writer: bool,
    ) -> None:
        cipher = AESCTREncryptor(key_hash, segment.iv, is_encryptor=True)
        remaining = segment.length
        chunk_size = options.chunk_size
        compression_enabled = options.enable_compression and options.compression_level > 0

        def _read_chunk(handle, size) -> bytes:
            return handle.read(size)

        try:
            with open(self.filepath, "rb", buffering=chunk_size) as handle:
                handle.seek(segment.start)
                while remaining > 0:
                    to_read = min(chunk_size, remaining)
                    chunk = await loop.run_in_executor(None, _read_chunk, handle, to_read)
                    if not chunk:
                        break

                    plain_len = len(chunk)
                    if compression_enabled:
                        payload = await loop.run_in_executor(
                            None,
                            lambda data=chunk: zlib.compress(data, options.compression_level),
                        )
                    else:
                        payload = chunk

                    encrypted_payload = cipher.update(payload)
                    header = struct.pack("!II", plain_len, len(payload))
                    writer.write(header)
                    writer.write(encrypted_payload)
                    await writer.drain()

                    written = min(plain_len, remaining)
                    remaining -= written
                    progress.update(written)

            writer.write(struct.pack("!II", 0, 0))
            await writer.drain()
            cipher.finalize()
        finally:
            if close_writer:
                writer.close()
            with contextlib.suppress(Exception):
                if close_writer:
                    await writer.wait_closed()

    async def _send_directory_stream(
        self,
        *,
        writer: asyncio.StreamWriter,
        options: TransferOptions,
        key_hash: bytes,
        iv: bytes,
        progress: tqdm,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        compression_enabled = options.enable_compression and options.compression_level > 0
        tar_stream = TarStreamProducer(self.filepath)
        cipher = AESCTREncryptor(key_hash, iv, is_encryptor=True)

        try:
            while True:
                chunk = await loop.run_in_executor(None, tar_stream.read, options.chunk_size)
                if not chunk:
                    break

                plain_len = len(chunk)
                if compression_enabled:
                    payload = await loop.run_in_executor(
                        None,
                        lambda data=chunk: zlib.compress(data, options.compression_level),
                    )
                else:
                    payload = chunk

                encrypted_payload = cipher.update(payload)
                header = struct.pack("!II", plain_len, len(payload))
                writer.write(header)
                writer.write(encrypted_payload)
                await writer.drain()
                progress.update(plain_len)

            writer.write(struct.pack("!II", 0, 0))
            await writer.drain()
            cipher.finalize()
        finally:
            tar_stream.close()

    def _configure_socket(self, sock: Optional[socket.socket]) -> None:
        if not sock:
            return
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 16 * 1024 * 1024)
        except Exception:
            pass
        try:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except Exception:
            pass
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        except Exception:
            pass

    def _format_size(self, size: int) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"

    def transfer(self) -> bool:
        safe_print("\n[SEARCHING] Searching for receivers on network...")
        receiver = self.find_receiver()
        if not receiver:
            safe_print("\n[ERROR] No receivers found on the network.")
            safe_print("\nMake sure the receiver is running: beam receive")
            return False
        receiver_ip, _ = receiver
        safe_print(f"[OK] Found receiver at {receiver_ip}")
        return self.send_file(receiver_ip)


class TarStreamProducer:
    """Stream tar archive data for a directory without temporary files."""

    def __init__(self, root_path: str):
        self.root_path = os.path.abspath(root_path)
        self.arcname = os.path.basename(os.path.normpath(root_path))
        self._queue: "queue.Queue[Optional[bytes]]" = queue.Queue(maxsize=4)
        self._buffer = bytearray()
        self._finished = False
        self._thread = threading.Thread(target=self._produce, daemon=True)
        self._thread.start()

    def _produce(self) -> None:
        try:
            with tarfile.open(fileobj=self, mode="w|", format=tarfile.GNU_FORMAT) as tar:
                tar.add(self.root_path, arcname=self.arcname)
        finally:
            self._queue.put(None)

    # tarfile calls this method while building the archive
    def write(self, data: bytes) -> None:  # type: ignore[override]
        if data:
            self._queue.put(data)

    def read(self, size: int) -> bytes:
        while (size < 0 or len(self._buffer) < size) and not self._finished:
            chunk = self._queue.get()
            if chunk is None:
                self._finished = True
                break
            self._buffer.extend(chunk)

        if size < 0 or size > len(self._buffer):
            size = len(self._buffer)

        if size == 0:
            return b""

        data = bytes(self._buffer[:size])
        del self._buffer[:size]
        return data

    def close(self) -> None:
        self._finished = True
        if self._thread.is_alive():
            self._queue.put(None)
            self._thread.join(timeout=1.0)

