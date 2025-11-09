"""
Receiver module for accepting file transfers.
"""

import os
import queue
import socket
import struct
import threading
from typing import Optional
from beam_transfer.network import NetworkDiscovery, ConnectionHandler, BROADCAST_PORT, FILE_TRANSFER_PORT
from beam_transfer.security import get_key_hash, AESEncryptor, AESCTREncryptor
from beam_transfer.utils import safe_print


class FileReceiver:
    """Handle file receiving operations."""
    
    def __init__(self, download_dir: str = "."):
        """Initialize file receiver."""
        self.download_dir = download_dir
        # Use larger internal read size; actual encrypted chunk size is prefixed by sender
        self.chunk_size = 4 * 1024 * 1024  # 4MB
        self.running = False
        self.server_socket = None
        
    def start_listening(self) -> None:
        """Start listening for file transfer requests."""
        self.running = True
        self.server_socket = ConnectionHandler.create_server_socket()
        self.server_socket.bind(('', FILE_TRANSFER_PORT))
        self.server_socket.listen(5)
        
        safe_print("\n[READY] Receiver is listening for incoming transfers...")
        safe_print(f"Download directory: {os.path.abspath(self.download_dir)}")
        safe_print("\nPress Ctrl+C to stop\n")
        
        try:
            while self.running:
                try:
                    client_socket, client_address = self.server_socket.accept()
                    try:
                        # Increase socket receive buffer to improve throughput
                        client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
                    except Exception:
                        pass
                    try:
                        client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    except Exception:
                        pass
                    
                    # Handle each transfer in a separate thread
                    thread = threading.Thread(
                        target=self._handle_transfer,
                        args=(client_socket, client_address),
                        daemon=True
                    )
                    thread.start()
                    
                except socket.timeout:
                    continue
                except OSError:
                    break
        except KeyboardInterrupt:
            safe_print("\n\n[WARNING] Shutting down receiver...")
        finally:
            self.stop()
    
    def _handle_transfer(self, sock: socket.socket, addr: tuple) -> None:
        """Handle a single file transfer."""
        try:
            # Receive header
            filename_len_data = sock.recv(4)
            if len(filename_len_data) != 4:
                return
            
            filename_len = struct.unpack('!I', filename_len_data)[0]
            filename_data = sock.recv(filename_len)
            if len(filename_data) != filename_len:
                return
            
            filename = filename_data.decode()
            
            # Receive file size
            file_size_data = sock.recv(8)
            if len(file_size_data) != 8:
                return
            file_size = struct.unpack('!Q', file_size_data)[0]
            
            # Receive key hash and session IV (CTR)
            key_hash_len = 32  # SHA-256 = 32 bytes
            key_hash_data = sock.recv(key_hash_len)
            if len(key_hash_data) != key_hash_len:
                return
            session_iv = sock.recv(16)
            if len(session_iv) != 16:
                return
            
            # Prompt user for acceptance
            print(f"\n{'=' * 60}")
            print(f"Incoming file: {filename}")
            print(f"Size: {self._format_size(file_size)}")
            print(f"From: {addr[0]}")
            print(f"{'=' * 60}")
            
            # For automatic acceptance or ask user
            response = input("Accept this transfer? (y/n): ").strip().lower()
            
            if response in ['y', 'yes']:
                # Ask for key verification
                received_key = input("Enter transfer key: ").strip().upper()
                expected_hash = get_key_hash(received_key)
                
                if expected_hash != key_hash_data:
                    safe_print("[ERROR] Invalid transfer key. Transfer declined.")
                    sock.sendall(b'N')
                    sock.close()
                    return
                
                safe_print("[OK] Key verified. Transferring file...")
                sock.sendall(b'Y')
                
                # Receive and save file
                self._receive_file(sock, filename, file_size, key_hash_data, session_iv)
                
                # Send final confirmation
                sock.sendall(b'Y')
                safe_print("[OK] File received successfully!")
            else:
                safe_print("Transfer declined.")
                sock.sendall(b'N')
                
        except Exception as e:
            safe_print(f"\n[ERROR] Error handling transfer: {e}")
        finally:
            sock.close()
    
    def _receive_file(self, sock: socket.socket, filename: str, file_size: int, key_hash: bytes, session_iv: bytes) -> None:
        """Receive and decrypt file."""
        # Ensure download directory exists
        os.makedirs(self.download_dir, exist_ok=True)
        filepath = os.path.join(self.download_dir, filename)
        
        # Initialize streaming decryption (CTR) with the session IV
        cipher = AESCTREncryptor(key_hash, session_iv, is_encryptor=False)
        
        chunk_queue: "queue.Queue[Optional[bytearray]]" = queue.Queue(maxsize=6)
        network_error: list[Exception] = []
        network_stop = threading.Event()
        bytes_expected = file_size

        def _network_reader() -> None:
            try:
                bytes_received_total = 0
                while True:
                    chunk_size_data = sock.recv(4)
                    if len(chunk_size_data) != 4:
                        break

                    encrypted_chunk_size = struct.unpack('!I', chunk_size_data)[0]
                    encrypted_chunk = bytearray(encrypted_chunk_size)
                    view = memoryview(encrypted_chunk)
                    bytes_read = 0
                    while bytes_read < encrypted_chunk_size:
                        n = sock.recv_into(
                            view[bytes_read:],
                            min(encrypted_chunk_size - bytes_read, self.chunk_size),
                        )
                        if not n:
                            break
                        bytes_read += n

                    if bytes_read != encrypted_chunk_size:
                        break

                    chunk_queue.put(encrypted_chunk)
                    bytes_received_total += encrypted_chunk_size

                    if bytes_received_total >= bytes_expected:
                        break
            except Exception as exc:
                network_error.append(exc)
            finally:
                network_stop.set()
                chunk_queue.put(None)

        reader_thread = threading.Thread(target=_network_reader, daemon=True)
        reader_thread.start()

        received_bytes = 0
        with open(filepath, 'wb', buffering=self.chunk_size) as f:
            from tqdm import tqdm
            with tqdm(total=file_size, unit='B', unit_scale=True, desc="Downloading") as pbar:
                while received_bytes < file_size:
                    chunk = chunk_queue.get()
                    if chunk is None:
                        chunk_queue.task_done()
                        break

                    try:
                        decrypted_chunk = cipher.update(chunk)
                    finally:
                        chunk_queue.task_done()

                    f.write(decrypted_chunk)
                    received_bytes += len(decrypted_chunk)
                    pbar.update(len(decrypted_chunk))

                    if network_stop.is_set() and chunk_queue.empty():
                        break

        reader_thread.join()

        if network_error:
            raise network_error[0]
        
        if received_bytes == file_size:
            safe_print(f"\n[OK] File saved to: {os.path.abspath(filepath)}")
        else:
            safe_print(f"\n[ERROR] Incomplete transfer. Expected: {file_size}, Received: {received_bytes}")
            # Clean up incomplete file
            if os.path.exists(filepath):
                os.remove(filepath)
    
    def stop(self) -> None:
        """Stop the receiver."""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
    
    def _format_size(self, size: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"


class ReceiverDiscovery:
    """Handle receiver discovery announcements."""
    
    def __init__(self):
        self.discovery = NetworkDiscovery()
        self.socket = None
        self.running = False
        
    def start_announcing(self) -> None:
        """Start announcing receiver availability on the network."""
        self.running = True
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('', BROADCAST_PORT))
        self.socket.settimeout(1.0)
        
        def listen():
            while self.running:
                try:
                    data, addr = self.socket.recvfrom(1024)
                    message = data.decode()
                    
                    if message.startswith("SENDER_REQUEST:"):
                        # Respond to sender discovery
                        response = "RECEIVER_READY"
                        self.discovery.send_response(addr[0], response)
                        
                except socket.timeout:
                    continue
                except Exception:
                    break
        
        # Start listening in background
        listen_thread = threading.Thread(target=listen, daemon=True)
        listen_thread.start()
    
    def stop_announcing(self) -> None:
        """Stop announcing."""
        self.running = False
        if self.socket:
            self.socket.close()

