# Quick Start Guide

Get started with Beam Transfer in under 2 minutes!

## Step 1: Install Beam Transfer

Open a terminal/command prompt in this directory and run:

```bash
pip install .
```

Or if you're on macOS/Linux:

```bash
pip3 install .
```

## Step 2: Test the Installation

Verify it's installed:

```bash
beam --help
```

You should see the help menu.

## Step 3: Transfer Your First File

### On Device 1 (Receiver):

```bash
beam receive
```

You'll see:
```
🟢 Receiver is listening for incoming transfers...
Download directory: /current/directory

Press Ctrl+C to stop
```

### On Device 2 (Sender):

```bash
beam send your-file.txt
```

## Step 4: Accept the Transfer

On the receiver screen:
1. You'll see an incoming file notification
2. Type `y` to accept
3. Enter the transfer key from the sender's screen
4. The file will download!

## Common Issues

**"No receivers found"**
- Make sure both devices are on the same Wi-Fi
- Ensure the receiver is running first
- Check firewall settings (ports 25000-25001)

**"beam: command not found"**
- Add Python Scripts to your PATH
- Or use: `python -m beam_transfer.cli send your-file.txt`

**Permission errors**
- Run as administrator (Windows) or with sudo (Linux/macOS)

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- See [INSTALL.md](INSTALL.md) for troubleshooting

Enjoy lightning-fast file transfers! ⚡

