#  Beam Transfer

**Fast, secure CLI-based file transfer tool for local networks.**

Beam Transfer allows you to effortlessly transfer files between devices connected to the same Wi-Fi network or hotspot. No internet required, fully encrypted, and blazing fast!

---

##  Features

-  **High-speed transfers** – Async pipeline with optional multi-stream TCP sends keeps the link saturated
-  **AES-256 encryption** – Streamed AES-CTR encryption protects your data end-to-end
-  **Key-based verification** – Prevents unauthorized access with unique transfer keys
-  **Progress tracking** – Real-time progress bars for uploads and downloads (files and folders)
-  **Auto-discovery** – Automatically finds receivers on your network
-  **Multi-recipient fanout** – Broadcast the same transfer to multiple receivers that enter the key
-  **Directory streaming** – Send entire folders without temporary archives via on-the-fly tar streaming
-  **Configurable CLI** – Tune chunk size, compression level, stream count, and disable/enable fanout quickly

---

##  Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- All devices on the same Wi-Fi network or hotspot

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

This installs the `beam` command globally on your system.

---

##  Quick Start

### 1. Start the Receiver

On every device that should receive files:

```bash
beam receive
```

Or specify a download directory:

```bash
beam receive -d ~/Transfers
```

Leave the receiver running; each device will show a prompt when a transfer request arrives.

### 2. Send a File or Directory

On the sending device:

```bash
# Send a single file
beam send movie.mkv

# Stream an entire folder
beam send ./project-folder
```

If multiple receivers are listening and enter the same key, the sender will stream the file/folder to all of them simultaneously.

**Sender output (fanout example):**
```
[SEARCHING] Searching for receivers on network...
[OK] Found 2 receivers: 192.168.1.105, 192.168.1.144
Transfer Key: A7K9X2
Connecting to 2 receivers (192.168.1.105, 192.168.1.144)...
Uploading: 100%|████████████████| 2.57G/2.57G [00:52<00:00, 49.8MB/s]

[OK] Transfer completed successfully for all receivers!
```

**Receiver output:**
```
============================================================
Incoming directory: project-folder
Size: streaming
Streams: 1
Compression: Off
============================================================
Accept this transfer? (y/n): y
Enter transfer key: A7K9X2
[OK] Key verified. Transferring files...
Downloading: 100%|████████████████| 2.57G/2.57G [00:52<00:00, 49.8MB/s]
[OK] Directory saved to: /path/to/download/project-folder
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

### Sending a Directory

```bash
beam send ./assets
```

### Broadcast to Multiple Receivers

Start `beam receive` on each target device, then run:

```bash
beam send presentation.pdf
```

Every receiver that enters the displayed key receives the same encrypted stream. Use `--no-fanout` if you want to send only to the first responder.

### Specifying Download Directory

```bash
beam receive -d ~/Downloads/Transfers
```

---

##  Advanced Usage

Customize the transfer pipeline with these flags:

```bash
beam send large.iso \
  --streams 3 \
  --chunk-size $((8 * 1024 * 1024)) \
  --compress-level 0 \
  --no-fanout
```

- `--streams` – parallel TCP streams per receiver (files only)
- `--chunk-size` – bytes per read/encrypt/send (default 4 MB)
- `--compress-level` – zlib compression level (0 disables compression)
- `--no-compress` – convenience flag to disable compression
- `--no-fanout` – send only to the first receiver, even if others respond
- `-k/--key` – provide your own transfer key

### Checking Installation

```bash
beam --help
```

---

##  Security Features

1. **AES-256-CTR Encryption** – Streaming cipher keeps latency low without sacrificing security
2. **Key Verification** – Transfers require a short alphanumeric key displayed on the sender
3. **Network Discovery** – Only devices that answer discovery broadcasts can join the transfer
4. **Connection Timeouts** – Automatic timeouts protect against stalled sockets

### How It Works

1. **Discovery** – The sender broadcasts a discovery message on the local network
2. **Verification** – Receivers respond only if they are actively listening
3. **Handshake** – Sender and receiver(s) establish secure TCP connections
4. **Key Exchange** – Sender transmits a hash of the transfer key; receiver must match it
5. **Streaming Encryption** – Files/folders are read in large chunks, optionally compressed, encrypted with AES-CTR, then streamed
6. **Confirmation** – Each receiver acknowledges success or reports failure at the end

---

##  Architecture

```
beam_transfer/
├── __init__.py
├── cli.py               # Command-line interface and option parsing
├── sender.py            # Async transfer engine, fanout, tar streaming
├── receiver.py          # Async receiver server, extraction pipeline
├── network.py           # Discovery broadcasts and UDP responses
├── security.py          # AES helpers and key hashing
└── utils.py             # Console utilities and helpers
```

---

##  Configuration Defaults

- **Broadcast Port**: 25000 (UDP for discovery)
- **Transfer Port**: 25001 (TCP for encrypted data)
- **Discovery Timeout**: ~3 seconds
- **Chunk Size**: 4 MB (configurable)
- **Parallel Streams**: 1 per receiver (configurable)
- **Fanout**: Enabled (disable with `--no-fanout`)

---

##  Troubleshooting

### "No receivers found on the network"

**Solution:**
1. Ensure all devices share the same Wi-Fi network or hotspot
2. Make sure each receiver is running `beam receive`
3. Check firewall/antivirus settings for ports 25000–25001
4. Temporarily disable VPN if active

### "Connection refused" or "Connection timeout"

**Solution:**
1. Verify firewall rules allow inbound TCP on port 25001
2. Confirm the receiver is listening (look for the READY banner)
3. Restart both sender and receiver processes

### "Invalid transfer key"

**Solution:**
- Enter the exact key shown on the sender (case-insensitive)
- Double-check that you’re typing the characters correctly

### Installation Issues

```bash
pip install --upgrade --force-reinstall .
```
Make sure the Python Scripts directory (or equivalent) is on your system PATH.

---

## Contributing

Contributions are welcome! Please open a Pull Request with your improvements or ideas.

---

##  Roadmap

Future enhancements:
- Resume/retry support for interrupted transfers
- Transfer history/logging
- Optional bandwidth throttling
- GUI front-end companion

---

##  Acknowledgments

Built with:
- Python `cryptography` for AES-CTR encryption
- `tqdm` for progress bars
- Standard library `asyncio`/`socket` for networking

---

**Made with ❤️ for seamless local file transfers**

