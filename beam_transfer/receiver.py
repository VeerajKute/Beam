"""
Async receiver module for Beam Transfer.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import queue
import shutil
import socket
import struct
import threading
import tarfile
import zlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from tqdm import tqdm

from beam_transfer.network import BROADCAST_PORT, FILE_TRANSFER_PORT, NetworkDiscovery
from beam_transfer.security import AESCTREncryptor, get_key_hash
from beam_transfer.utils import safe_print

FLAG_COMPRESS = 0x01
FLAG_MULTI_STREAM = 0x02
FLAG_TAR_ARCHIVE = 0x04


@dataclass
class StreamInfo:
    index: int
    iv: bytes
    offset: int
    length: int


@dataclass
class TransferState:
    transfer_id: bytes
    filename: str
    filepath: str
    file_size: int
    key_hash: bytes
    compression_enabled: bool
    compression_level: int
    chunk_size: int
    streams: Dict[int, StreamInfo]
    progress: tqdm
    loop: asyncio.AbstractEventLoop
    remaining_streams: int = field(init=False)
    tasks: List[asyncio.Task] = field(default_factory=list)
    done_event: asyncio.Event = field(default_factory=asyncio.Event)
    error: Optional[Exception] = None

    def __post_init__(self) -> None:
        self.remaining_streams = len(self.streams)

    def add_task(self, task: asyncio.Task) -> None:
        self.tasks.append(task)
        task.add_done_callback(self._task_done)

    def _task_done(self, task: asyncio.Task) -> None:
        try:
            task.result()
        except Exception as exc:  # pylint: disable=broad-except
            if not self.error:
                self.error = exc
            for other in self.tasks:
                if other is not task and not other.done():
                    other.cancel()
        self.remaining_streams -= 1
        if self.remaining_streams <= 0 or self.error:
            self.done_event.set()

    async def wait_complete(self) -> None:
        await self.done_event.wait()

    def close_progress(self) -> None:
        self.progress.close()


class FileReceiver:
    """Handle file receiving operations with async, compression, and parallel support."""

    def __init__(self, download_dir: str = "."):
        self.download_dir = download_dir
        self._server: Optional[asyncio.AbstractServer] = None
        self._active_transfers: Dict[bytes, TransferState] = {}

    def start_listening(self) -> None:
        safe_print("\n[READY] Receiver is listening for incoming transfers...")
        safe_print(f"Download directory: {os.path.abspath(self.download_dir)}")
        safe_print("\nPress Ctrl+C to stop\n")
        try:
            asyncio.run(self._run_server())
        except KeyboardInterrupt:
            safe_print("\n\n[WARNING] Shutting down receiver...")
        finally:
            if self._server:
                self._server.close()

    async def _run_server(self) -> None:
        self._server = await asyncio.start_server(
            self._handle_client,
            host="0.0.0.0",
            port=FILE_TRANSFER_PORT,
            reuse_address=True,
        )
        async with self._server:
            await self._server.serve_forever()

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        self._configure_socket(writer.get_extra_info("socket"))
        try:
            prefix = await reader.readexactly(4)
        except asyncio.IncompleteReadError:
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()
            return

        if prefix == b"STRM":
            await self._handle_stream_connection(reader, writer)
            return

        await self._handle_primary_connection(prefix, reader, writer)

    async def _handle_primary_connection(
        self,
        prefix: bytes,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        filename_len = struct.unpack("!I", prefix)[0]
        filename_bytes = await reader.readexactly(filename_len)
        filename = filename_bytes.decode()

        file_size = struct.unpack("!Q", await reader.readexactly(8))[0]
        key_hash = await reader.readexactly(32)
        flags, compression_level, stream_count, chunk_size = struct.unpack(
            "!BBHI", await reader.readexactly(8)
        )
        transfer_id = await reader.readexactly(16)

        compression_enabled = bool(flags & FLAG_COMPRESS) and compression_level > 0
        is_tar_archive = bool(flags & FLAG_TAR_ARCHIVE)

        streams: Dict[int, StreamInfo] = {}
        for idx in range(stream_count):
            iv = await reader.readexactly(16)
            offset, length = struct.unpack("!QQ", await reader.readexactly(16))
            streams[idx] = StreamInfo(index=idx, iv=iv, offset=offset, length=length)

        safe_print(f"\n{'=' * 60}")
        safe_print(f"Incoming {'directory' if is_tar_archive else 'file'}: {filename}")
        if file_size:
            safe_print(f"Size: {self._format_size(file_size)}")
        else:
            safe_print("Size: streaming")
        safe_print(f"Streams: {stream_count}")
        safe_print(f"Compression: {'On' if compression_enabled else 'Off'}")
        safe_print(f"{'=' * 60}")

        loop = asyncio.get_running_loop()
        response = (await loop.run_in_executor(None, input, "Accept this transfer? (y/n): "))
        if response.strip().lower() not in {"y", "yes"}:
            safe_print("Transfer declined.")
            writer.write(b"N")
            await writer.drain()
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()
            return

        received_key = (await loop.run_in_executor(None, input, "Enter transfer key: ")).strip().upper()
        expected_hash = get_key_hash(received_key)
        if expected_hash != key_hash:
            safe_print("[ERROR] Invalid transfer key. Transfer declined.")
            writer.write(b"N")
            await writer.drain()
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()
            return

        os.makedirs(self.download_dir, exist_ok=True)
        writer.write(b"Y")
        await writer.drain()

        if is_tar_archive:
            success, target_dir, error = await self._handle_tar_transfer(
                reader=reader,
                iv=streams[0].iv,
                file_size=file_size,
                key_hash=key_hash,
                compression_enabled=compression_enabled,
                base_name=filename,
            )

            if success:
                writer.write(b"Y")
                await writer.drain()
                safe_print(f"[OK] Directory saved to: {os.path.abspath(target_dir)}")
            else:
                writer.write(b"N")
                await writer.drain()
                if target_dir:
                    shutil.rmtree(target_dir, ignore_errors=True)
                safe_print(f"\n[ERROR] Transfer failed: {error}")

            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()
            return

        filepath = os.path.join(self.download_dir, filename)
        with open(filepath, "wb") as temp_file:
            temp_file.truncate(file_size)

        progress = tqdm(total=file_size, unit="B", unit_scale=True, desc="Downloading")
        state = TransferState(
            transfer_id=transfer_id,
            filename=filename,
            filepath=filepath,
            file_size=file_size,
            key_hash=key_hash,
            compression_enabled=compression_enabled,
            compression_level=compression_level,
            chunk_size=chunk_size,
            streams=streams,
            progress=progress,
            loop=loop,
        )
        self._active_transfers[transfer_id] = state

        first_stream = streams[0]
        task = asyncio.create_task(
            self._receive_stream(state, first_stream, reader, writer, close_writer=False)
        )
        state.add_task(task)

        await state.wait_complete()
        state.close_progress()

        self._active_transfers.pop(transfer_id, None)

        if state.error:
            safe_print(f"\n[ERROR] Transfer failed: {state.error}")
            writer.write(b"N")
        else:
            safe_print(f"[OK] File saved to: {os.path.abspath(filepath)}")
            writer.write(b"Y")
        await writer.drain()
        writer.close()
        with contextlib.suppress(Exception):
            await writer.wait_closed()

    async def _handle_stream_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            index = struct.unpack("!H", await reader.readexactly(2))[0]
            transfer_id = await reader.readexactly(16)
        except asyncio.IncompleteReadError:
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()
            return

        state = self._active_transfers.get(transfer_id)
        if not state:
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()
            return

        stream_info = state.streams.get(index)
        if not stream_info:
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()
            return

        self._configure_socket(writer.get_extra_info("socket"))

        task = asyncio.create_task(
            self._receive_stream(state, stream_info, reader, writer, close_writer=True)
        )
        state.add_task(task)

    async def _receive_stream(
        self,
        state: TransferState,
        stream: StreamInfo,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        *,
        close_writer: bool,
    ) -> None:
        cipher = AESCTREncryptor(state.key_hash, stream.iv, is_encryptor=False)
        remaining = stream.length
        loop = state.loop

        def _decompress(data: bytes) -> bytes:
            return zlib.decompress(data)

        with open(state.filepath, "r+b", buffering=state.chunk_size) as handle:
            handle.seek(stream.offset)
            while True:
                header = await reader.readexactly(8)
                plain_len, payload_len = struct.unpack("!II", header)
                if plain_len == 0 and payload_len == 0:
                    break

                ciphertext = await reader.readexactly(payload_len)
                payload = cipher.update(ciphertext)

                if state.compression_enabled:
                    chunk = await loop.run_in_executor(None, _decompress, payload)
                else:
                    chunk = payload

                if len(chunk) != plain_len:
                    raise ValueError("Chunk length mismatch detected")

                handle.write(chunk)
                remaining -= plain_len
                state.progress.update(plain_len)

        cipher.finalize()

        if remaining != 0:
            raise ValueError("Stream ended before receiving expected bytes")

        if close_writer:
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()

    async def _handle_tar_transfer(
        self,
        *,
        reader: asyncio.StreamReader,
        iv: bytes,
        file_size: int,
        key_hash: bytes,
        compression_enabled: bool,
        base_name: str,
    ) -> tuple[bool, Optional[str], Optional[Exception]]:
        loop = asyncio.get_running_loop()
        target_dir = self._resolve_target_directory(base_name)
        os.makedirs(target_dir, exist_ok=True)

        total = file_size if file_size else None
        progress = tqdm(total=total, unit="B", unit_scale=True, desc="Downloading")
        extraction = TarExtractionWorker(target_dir)
        cipher = AESCTREncryptor(key_hash, iv, is_encryptor=False)

        success = False
        error: Optional[Exception] = None

        try:
            while True:
                header = await reader.readexactly(8)
                plain_len, payload_len = struct.unpack("!II", header)
                if plain_len == 0 and payload_len == 0:
                    break

                ciphertext = await reader.readexactly(payload_len)
                payload = cipher.update(ciphertext)

                if compression_enabled:
                    chunk = await loop.run_in_executor(None, zlib.decompress, payload)
                else:
                    chunk = payload

                if len(chunk) != plain_len:
                    raise ValueError("Chunk length mismatch detected")

                extraction.feed(chunk)
                progress.update(plain_len)

            success = True
        except Exception as exc:  # pylint: disable=broad-except
            error = exc
        finally:
            extraction.close()
            try:
                await loop.run_in_executor(None, extraction.wait)
            except Exception as exc:  # pylint: disable=broad-except
                if not error:
                    error = exc
                success = False
            cipher.finalize()
            progress.close()

        return success, target_dir, error

    def _resolve_target_directory(self, name: str) -> str:
        base_name = os.path.basename(name.rstrip(os.sep)) or "beam_transfer"
        candidate = os.path.join(self.download_dir, base_name)
        counter = 1
        while os.path.exists(candidate):
            candidate = os.path.join(self.download_dir, f"{base_name}_{counter}")
            counter += 1
        return candidate


class TarQueueReader:
    """File-like reader that pulls tar bytes from a queue."""

    def __init__(self, data_queue: "queue.Queue[Optional[bytes]]"):
        self._queue = data_queue
        self._buffer = bytearray()
        self._finished = False

    def read(self, size: int = -1) -> bytes:  # type: ignore[override]
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


class TarExtractionWorker:
    """Extract tar bytes fed over time into a target directory."""

    def __init__(self, target_dir: str):
        self.target_dir = target_dir
        self._queue: "queue.Queue[Optional[bytes]]" = queue.Queue(maxsize=4)
        self._reader = TarQueueReader(self._queue)
        self._closed = False
        self.error: Optional[Exception] = None
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        try:
            with tarfile.open(fileobj=self._reader, mode="r|*") as tar:
                self._extract_members(tar)
        except Exception as exc:  # pylint: disable=broad-except
            self.error = exc

    def _extract_members(self, tar: tarfile.TarFile) -> None:
        base_dir = os.path.abspath(self.target_dir)
        for member in tar:
            if not member.name:
                continue
            member_name = member.name.lstrip("./")
            target_path = _safe_join(base_dir, member_name)

            if member.isdir():
                os.makedirs(target_path, exist_ok=True)
                continue

            if member.islnk() or member.issym():
                # Skip links for safety in streaming mode
                continue

            parent = os.path.dirname(target_path)
            os.makedirs(parent, exist_ok=True)

            extracted = tar.extractfile(member)
            if extracted is None:
                continue
            with extracted as src, open(target_path, "wb") as dst:
                shutil.copyfileobj(src, dst)

            if member.mode:
                try:
                    os.chmod(target_path, member.mode)
                except PermissionError:
                    pass
            if member.mtime:
                try:
                    os.utime(target_path, (member.mtime, member.mtime))
                except OSError:
                    pass

    def feed(self, data: bytes) -> None:
        if self._closed or not data:
            return
        self._queue.put(data)

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            self._queue.put(None)

    def wait(self) -> None:
        if self._thread.is_alive():
            self._thread.join()
        if self.error:
            raise self.error


def _safe_join(base_dir: str, member_name: str) -> str:
    base_abs = os.path.abspath(base_dir)
    target = os.path.abspath(os.path.join(base_abs, member_name))
    if not target.startswith(base_abs + os.sep) and target != base_abs:
        raise ValueError(f"Blocked unsafe path: {member_name}")
    return target


class ReceiverDiscovery:
    """Handle receiver discovery announcements."""

    def __init__(self):
        self.discovery = NetworkDiscovery()
        self.socket: Optional[socket.socket] = None
        self.running = False
        self._thread: Optional[threading.Thread] = None

    def start_announcing(self) -> None:
        self.running = True
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(("", BROADCAST_PORT))
        self.socket.settimeout(1.0)

        def listen() -> None:
            while self.running:
                try:
                    data, addr = self.socket.recvfrom(1024)
                    message = data.decode()
                    if message.startswith("SENDER_REQUEST:"):
                        self.discovery.send_response(addr[0], "RECEIVER_READY")
                except socket.timeout:
                    continue
                except Exception:
                    break

        self._thread = threading.Thread(target=listen, daemon=True)
        self._thread.start()

    def stop_announcing(self) -> None:
        self.running = False
        if self.socket:
            self.socket.close()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

