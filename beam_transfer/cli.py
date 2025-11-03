"""
Command-line interface for Beam Transfer.
"""

import argparse
import sys
from pathlib import Path
from beam_transfer.sender import FileSender
from beam_transfer.receiver import FileReceiver, ReceiverDiscovery
from beam_transfer.utils import safe_print, setup_windows_encoding

# Setup Windows encoding
setup_windows_encoding()


def cmd_send(args):
    """Handle send command."""
    filepath = args.file
    transfer_key = args.key
    
    # Validate file exists
    if not Path(filepath).exists():
        safe_print(f"[ERROR] File '{filepath}' not found.")
        sys.exit(1)
    
    if not Path(filepath).is_file():
        safe_print(f"[ERROR] '{filepath}' is not a file.")
        sys.exit(1)
    
    # Send file
    sender = FileSender(filepath, transfer_key)
    success = sender.transfer()
    
    sys.exit(0 if success else 1)


def cmd_receive(args):
    """Handle receive command."""
    download_dir = args.directory
    
    # Validate download directory
    download_path = Path(download_dir)
    if download_path.exists() and not download_path.is_dir():
        safe_print(f"[ERROR] '{download_dir}' is not a directory.")
        sys.exit(1)
    
    try:
        # Start receiver discovery
        discovery = ReceiverDiscovery()
        discovery.start_announcing()
        
        # Start receiver
        receiver = FileReceiver(str(download_path))
        receiver.start_listening()
        
    except KeyboardInterrupt:
        safe_print("\n\n[WARNING] Shutting down...")
        sys.exit(0)
    except Exception as e:
        safe_print(f"\n[ERROR] Error: {e}")
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Beam Transfer - Fast, secure file transfer for local networks",
        epilog="Example: beam send document.pdf | beam receive"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Send command
    send_parser = subparsers.add_parser('send', help='Send a file')
    send_parser.add_argument('file', help='File to send')
    send_parser.add_argument('-k', '--key', help='Transfer key (auto-generated if not provided)')
    send_parser.set_defaults(func=cmd_send)
    
    # Receive command
    receive_parser = subparsers.add_parser('receive', help='Start receiving files')
    receive_parser.add_argument('-d', '--directory', default='.', help='Download directory (default: current directory)')
    receive_parser.set_defaults(func=cmd_receive)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)


if __name__ == '__main__':
    main()

