"""
Sender module for initiating file transfers.
"""

import os
import socket
import struct
import sys
from typing import Optional
from beam_transfer.network import NetworkDiscovery, ConnectionHandler
from beam_transfer.security import generate_transfer_key, get_key_hash, AESEncryptor
from beam_transfer.utils import safe_print
from tqdm import tqdm


class FileSender:
    """Handle file sending operations."""
    
    def __init__(self, filepath: str, transfer_key: Optional[str] = None):
        """Initialize file sender."""
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.file_size = os.path.getsize(filepath)
        self.transfer_key = transfer_key or generate_transfer_key()
        # Use large chunks to reduce per-chunk overhead and increase throughput
        self.chunk_size = 4 * 1024 * 1024  # 4MB chunks
        self.cipher = None
        
    def find_receiver(self) -> Optional[tuple]:
        """Discover available receivers on the network."""
        discovery = NetworkDiscovery()
        message = f"SENDER_REQUEST:{self.filename}:{self.file_size}:{self.transfer_key}"
        devices = discovery.discover_devices(message)

        # Prefer non-local receivers; ignore any of our local addresses if discovered
        if devices:
            local_ips = self._get_local_ipv4_addresses()
            local_ips.update({discovery.local_ip, "127.0.0.1"})
            non_local = [d for d in devices if d[0] not in local_ips]
            if non_local:
                return non_local[0]
            return devices[0]  # fallback to first (e.g., single-machine transfer)
        return None

    def _get_local_ipv4_addresses(self) -> set:
        """Return a set of local IPv4 addresses for this host."""
        addresses = {"127.0.0.1"}
        try:
            hostname = socket.gethostname()
            # gethostbyname_ex returns (hostname, aliaslist, ipaddrlist)
            _, _, ip_list = socket.gethostbyname_ex(hostname)
            addresses.update(ip_list)
        except Exception:
            pass
        # Best-effort: probe typical local endpoint to infer primary IP
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            addresses.add(s.getsockname()[0])
            s.close()
        except Exception:
            pass
        return {ip for ip in addresses if ":" not in ip}
    
    def send_file(self, receiver_ip: str) -> bool:
        """Send file to receiver."""
        try:
            print(f"Connecting to receiver at {receiver_ip}...")
            # Show the transfer key BEFORE the receiver asks for it
            print(f"Transfer Key: {self.transfer_key}")
            
            # Connect to receiver
            sock = ConnectionHandler.create_client_socket()
            try:
                # Increase socket send buffer for higher throughput
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4 * 1024 * 1024)
            except Exception:
                pass
            sock.connect((receiver_ip, 25001))
            
            try:
                # Send header: filename, file size, and key hash
                key_hash = get_key_hash(self.transfer_key)
                header = struct.pack(
                    f"!I{len(self.filename.encode())}sQ{len(key_hash)}s",
                    len(self.filename.encode()),
                    self.filename.encode(),
                    self.file_size,
                    key_hash
                )
                sock.sendall(header)
                
                # Wait for receiver confirmation
                response = sock.recv(1)
                if response != b'Y':
                    print("Receiver declined the transfer.")
                    return False
                
                # Initialize encryption
                self.cipher = AESEncryptor(key_hash)
                print(f"Sending file: {self.filename} ({self._format_size(self.file_size)})")
                print("-" * 60)
                
                # Send file in chunks
                sent_bytes = 0
                with open(self.filepath, 'rb') as f:
                    with tqdm(total=self.file_size, unit='B', unit_scale=True, desc="Uploading") as pbar:
                        while sent_bytes < self.file_size:
                            chunk = f.read(self.chunk_size)
                            if not chunk:
                                break
                            
                            # Encrypt chunk
                            encrypted_chunk = self.cipher.encrypt(chunk)
                            
                            # Send encrypted chunk with size prefix
                            chunk_header = struct.pack('!I', len(encrypted_chunk))
                            sock.sendall(chunk_header)
                            # Use memoryview to avoid extra copies in Python
                            sock.sendall(memoryview(encrypted_chunk))
                            
                            sent_bytes += len(chunk)
                            pbar.update(len(chunk))
                
                # Wait for final confirmation
                final_response = sock.recv(1)
                if final_response == b'Y':
                    safe_print("\n[OK] File sent successfully!")
                    return True
                else:
                    safe_print("\n[ERROR] Transfer failed.")
                    return False
                    
            finally:
                sock.close()
                
        except Exception as e:
            safe_print(f"\n[ERROR] Error sending file: {e}")
            return False
    
    def _format_size(self, size: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"
    
    def transfer(self) -> bool:
        """Complete transfer workflow."""
        safe_print(f"\n[SEARCHING] Searching for receivers on network...")
        receiver = self.find_receiver()
        
        if not receiver:
            safe_print("\n[ERROR] No receivers found on the network.")
            safe_print("\nMake sure the receiver is running: beam receive")
            return False
        
        receiver_ip, _ = receiver
        safe_print(f"[OK] Found receiver at {receiver_ip}")
        
        return self.send_file(receiver_ip)

