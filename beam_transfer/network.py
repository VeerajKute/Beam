"""
Network utilities for discovery and communication.
"""

import socket
import threading
import time
from typing import Optional, List, Tuple

BROADCAST_PORT = 25000
FILE_TRANSFER_PORT = 25001
DISCOVERY_TIMEOUT = 3


def get_local_ip() -> str:
    """Get the local IP address of the machine."""
    try:
        # Connect to a remote address to determine local IP
        # Note: This doesn't actually send data
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"


def get_broadcast_addresses() -> List[str]:
    """Get all broadcast addresses for the local network."""
    import ipaddress
    local_ip = get_local_ip()
    
    try:
        # Try to determine network from local IP
        interfaces = []
        if local_ip != "127.0.0.1":
            # Create network from IP
            ip = ipaddress.ip_address(local_ip)
            if ip.version == 4:
                # Assume /24 network for simplicity
                network = ipaddress.IPv4Network(f"{local_ip}/24", strict=False)
                interfaces.append(str(network.broadcast_address))
        
        return interfaces if interfaces else ["255.255.255.255"]
    except Exception:
        return ["255.255.255.255"]


class NetworkDiscovery:
    """Handle network discovery and broadcasting."""
    
    def __init__(self):
        self.local_ip = get_local_ip()
        self.discovered_devices = []
        self.socket = None
        
    def start_listener(self) -> None:
        """Start listening for discovery broadcasts."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('', BROADCAST_PORT))
        self.socket.settimeout(1.0)
        
    def broadcast_presence(self, message: str, duration: float = 3.0) -> None:
        """Broadcast presence message on the network."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        broadcast_addrs = get_broadcast_addresses()
        start_time = time.time()
        
        while time.time() - start_time < duration:
            for addr in broadcast_addrs:
                try:
                    sock.sendto(message.encode(), (addr, BROADCAST_PORT))
                except Exception:
                    pass
            time.sleep(0.5)
        
        sock.close()
    
    def discover_devices(self, message: str) -> List[Tuple[str, str]]:
        """Discover devices by broadcasting and listening for responses."""
        discovered = []
        
        # Start listening thread
        def listen():
            while time.time() < start_time + DISCOVERY_TIMEOUT:
                try:
                    if self.socket:
                        data, addr = self.socket.recvfrom(1024)
                        response = data.decode()
                        if message in response:
                            discovered.append((addr[0], response))
                except socket.timeout:
                    continue
                except Exception:
                    break
        
        self.start_listener()
        start_time = time.time()
        listen_thread = threading.Thread(target=listen, daemon=True)
        listen_thread.start()
        
        # Broadcast presence
        self.broadcast_presence(message, DISCOVERY_TIMEOUT)
        
        # Wait for listener to complete
        listen_thread.join(timeout=DISCOVERY_TIMEOUT + 1)
        
        if self.socket:
            self.socket.close()
            self.socket = None
        
        return discovered
    
    def send_response(self, ip: str, message: str) -> None:
        """Send a response to a specific IP."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.sendto(message.encode(), (ip, BROADCAST_PORT))
        except Exception:
            pass
        finally:
            sock.close()


class ConnectionHandler:
    """Handle TCP connections for file transfers."""
    
    @staticmethod
    def create_server_socket() -> socket.socket:
        """Create and bind a server socket for file transfers."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(60)  # 1 minute timeout for connections
        return sock
    
    @staticmethod
    def create_client_socket() -> socket.socket:
        """Create a client socket for file transfers."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(30)
        return sock

