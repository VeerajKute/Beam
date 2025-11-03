#  Beam Transfer

**Fast, secure CLI-based file transfer tool for local networks.**

Beam Transfer allows you to effortlessly transfer files between devices connected to the same Wi-Fi network or hotspot. No internet required, fully encrypted, and blazing fast!

---

##  Features

-  **High-speed transfers** - Optimized for fast local network file transfers
-  **AES-256 encryption** - Your files are encrypted during transfer
-  **Key-based verification** - Prevents unauthorized access with unique transfer keys
-  **Progress tracking** - Real-time progress bars for uploads and downloads
-  **Auto-discovery** - Automatically finds receivers on your network
-  **Cross-platform** - Works on Windows, macOS, and Linux
-  **Simple CLI** - Easy-to-use command-line interface

---

##  Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Both devices must be on the same Wi-Fi network or hotspot

### Install from Source

1. Clone or download this repository
2. Open a terminal/command prompt in the project directory
3. Run the installer:

```bash
# For Windows
pip install .

# For macOS/Linux
pip3 install .
```

This will install `beam` command globally on your system.

---

##  Quick Start

### 1. Start the Receiver

On the device that will receive the file:

```bash
beam receive
```

Or specify a download directory:

```bash
beam receive -d ~/Downloads
```

The receiver will start listening for incoming transfers and display:

```
 Receiver is listening for incoming transfers...
Download directory: /path/to/download

Press Ctrl+C to stop
```

### 2. Send a File

On the device that has the file, navigate to the folder containing the file:

```bash
# From any folder
beam send document.pdf

# Or with absolute path
beam send C:\Users\YourName\Documents\video.mp4
```

The sender will:
1. Automatically discover the receiver
2. Display transfer details with a unique key
3. Send the encrypted file

**Receiver will see:**
```
============================================================
Incoming file: document.pdf
Size: 2.45 MB
From: 192.168.1.100
============================================================
Accept this transfer? (y/n):
```

Type `y` to accept, then enter the transfer key displayed on the sender's screen.

**Sender will see:**
```
 Searching for receivers on network...
✓ Found receiver at 192.168.1.105
Connecting to receiver at 192.168.1.105...
Sending file: document.pdf (2.45 MB)
Transfer Key: A7K9X2
------------------------------------------------------------
Uploading: 100%|████████████████| 2.57M/2.57M [00:01<00:00, 1.50MB/s]

✓ File sent successfully!
```

**Receiver will see:**
```
✓ Key verified. Transferring file...
Downloading: 100%|████████████████| 2.57M/2.57M [00:01<00:00, 1.50MB/s]

✓ File saved to: /path/to/download/document.pdf
✓ File received successfully!
```

---

##  Usage Examples

### Basic File Transfer

**Receiver:**
```bash
beam receive
```

**Sender:**
```bash
beam send photo.jpg
```

### Specifying Download Directory

**Receiver:**
```bash
beam receive -d ~/Downloads/Transfers
```

### Multiple File Transfers

The receiver can handle multiple transfers sequentially. Just keep it running and accept transfers as they come in.

---

##  Advanced Usage

### Using a Custom Transfer Key

You can specify your own transfer key for additional security:

```bash
beam send document.pdf -k MYCUSTOMKEY
```

The receiver must enter exactly this key to accept the transfer.

### Checking Installation

To verify that Beam Transfer is installed correctly:

```bash
beam --help
```

You should see the help menu with available commands.

---

##  Security Features

1. **AES-256 Encryption**: All file transfers are encrypted using industry-standard AES-256-CBC encryption
2. **Key Verification**: Each transfer requires a unique alphanumeric key (6 characters by default)
3. **Network Discovery**: Only devices that respond to discovery broadcasts can initiate transfers
4. **Connection Timeouts**: Automatic timeout handling prevents hanging connections

### How It Works

1. **Discovery**: The sender broadcasts a discovery message on the local network
2. **Verification**: The receiver must be actively listening and responding to discovery requests
3. **Handshake**: The sender and receiver establish a secure TCP connection
4. **Key Exchange**: The sender transmits the key hash to the receiver
5. **Encryption**: Files are encrypted in 64KB chunks before transmission
6. **Confirmation**: The receiver must provide the correct key to decrypt and save the file

---

##  Architecture

```
beam_transfer/
├── __init__.py          # Package initialization
├── cli.py               # Command-line interface
├── sender.py            # File sending logic
├── receiver.py          # File receiving logic
├── network.py           # Network discovery and communication
└── security.py          # Encryption and key management
```

### Key Components

- **NetworkDiscovery**: Handles UDP broadcasting for device discovery
- **ConnectionHandler**: Manages TCP connections for file transfers
- **FileSender**: Orchestrates file sending with encryption
- **FileReceiver**: Handles incoming transfers with decryption
- **AESEncryptor**: Provides AES-256-CBC encryption/decryption

---

##  Configuration

### Default Settings

- **Broadcast Port**: 25000 (UDP for discovery)
- **Transfer Port**: 25001 (TCP for file transfer)
- **Discovery Timeout**: 3 seconds
- **Chunk Size**: 64 KB
- **Connection Timeout**: 30-60 seconds

These are currently hardcoded but can be customized in the source code if needed.

---

##  Troubleshooting

### "No receivers found on the network"

**Solution:**
1. Ensure both devices are on the same Wi-Fi network or hotspot
2. Make sure the receiver is running with `beam receive`
3. Check that firewall/antivirus isn't blocking ports 25000-25001
4. Try disabling VPN if active

### "Connection refused" or "Connection timeout"

**Solution:**
1. Verify firewall settings allow incoming connections on port 25001
2. Ensure receiver is listening: check for "🟢 Receiver is listening" message
3. Try restarting both sender and receiver

### "Invalid transfer key"

**Solution:**
- Make sure you're entering the exact key shown on the sender's screen
- Keys are case-insensitive, but verify you have the right characters

### Installation Issues

**"beam: command not found"**

**Solution:**
```bash
# Ensure pip install path is in your PATH environment variable
# Try reinstalling:
pip install --upgrade --force-reinstall .

# On Windows, you may need to add Python Scripts to PATH
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

##  Roadmap

Future enhancements:
- Transfer progress persistence across disconnections
- Directory/folder transfers
- Transfer history and logs
- GUI alternative to CLI
- Transfer scheduling
- Bandwidth throttling controls

---

##  Acknowledgments

Built with:
- Python `cryptography` library for encryption
- `tqdm` for progress bars
- Standard library `socket` for network operations

---

**Made with ❤️ for seamless local file transfers**

