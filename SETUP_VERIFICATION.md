# Setup Verification Guide

Use this guide to verify that Beam Transfer is correctly installed and configured.

## Pre-Installation Check

### 1. Check Python Installation

```bash
python --version
# Should show Python 3.8 or higher

pip --version
# Should show pip version
```

### 2. Test Dependencies Manually

```bash
# Test cryptography
python -c "import cryptography; print('✓ cryptography OK')"

# Test tqdm
python -c "import tqdm; print('✓ tqdm OK')"
```

If either fails, install them:
```bash
pip install cryptography tqdm
```

### 3. Test Project Imports

Run the test script:
```bash
python test_imports.py
```

Expected output:
```
Testing imports...
  ✓ Testing standard library imports... OK
  ✓ Testing third-party imports... OK
  OK
  ✓ Testing local module imports... OK

✅ All imports successful!

You can now install the package with: pip install .
```

## Installation Verification

### 1. Install the Package

```bash
pip install .
```

Look for output like:
```
Processing d:\drts_project
Building wheels for collected packages: beam-transfer
...
Successfully installed beam-transfer-1.0.0
```

### 2. Verify CLI Installation

```bash
beam --help
```

Expected output:
```
usage: beam [-h] {send,receive} ...

Beam Transfer - Fast, secure file transfer for local networks

positional arguments:
  {send,receive}  Available commands
    send          Send a file
    receive       Start receiving files

options:
  -h, --help      show this help message and exit

Example: beam send document.pdf | beam receive
```

### 3. Test CLI Commands

```bash
# Test send command help
beam send --help

# Test receive command help
beam receive --help
```

## Functional Testing

### Test 1: Discovery Only

**On Machine 1 (Receiver):**
```bash
beam receive
```

Should show:
```
🟢 Receiver is listening for incoming transfers...
Download directory: /path/to/dir
Press Ctrl+C to stop
```

**On Machine 2 (Sender):**
```bash
beam send nonexistent.txt
```

Should show:
```
✗ Error: File 'nonexistent.txt' not found.
```

### Test 2: Full Transfer

Create a test file:
```bash
echo "Hello, Beam Transfer!" > test.txt
```

**On Machine 1 (Receiver):**
```bash
beam receive -d ~/test_downloads
```

**On Machine 2 (Sender):**
```bash
beam send test.txt
```

Expected flow:
1. Sender finds receiver
2. Sender displays transfer key
3. Receiver prompts for acceptance
4. Receiver asks for key
5. Both show progress
6. File transfers successfully

### Test 3: Key Verification

Repeat Test 2, but enter wrong key when prompted.

Expected:
- Transfer should be rejected
- File should not be saved
- Error message displayed

## Network Configuration Check

### Port Check

Verify ports are available:
```bash
# Windows
netstat -an | findstr "25000 25001"

# Linux/macOS
netstat -an | grep "25000\|25001"
```

If ports are in use, you'll need to modify the port configuration in `beam_transfer/network.py`.

### Firewall Check

**Windows:**
```powershell
# Check firewall rules
Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*beam*"}

# If no rules exist, add them:
New-NetFirewallRule -DisplayName "Beam Transfer UDP" -Direction Inbound -Protocol UDP -LocalPort 25000 -Action Allow
New-NetFirewallRule -DisplayName "Beam Transfer TCP" -Direction Inbound -Protocol TCP -LocalPort 25001 -Action Allow
```

**Linux:**
```bash
# Ubuntu/Debian
sudo ufw allow 25000/udp
sudo ufw allow 25001/tcp

# CentOS/RHEL
sudo firewall-cmd --add-port=25000/udp --permanent
sudo firewall-cmd --add-port=25001/tcp --permanent
sudo firewall-cmd --reload
```

**macOS:**
System Preferences → Security & Privacy → Firewall → Firewall Options → Add Application

## Troubleshooting Failed Verification

### Issue: "beam: command not found"

**Solution:**
```bash
# Find where pip installed it
python -m site --user-base

# Add Scripts/bin to PATH, then:
beam --help

# Or use direct call:
python -m beam_transfer.cli --help
```

### Issue: Import errors

**Solution:**
```bash
# Install dependencies
pip install -r requirements.txt

# Or manually:
pip install cryptography tqdm
```

### Issue: Ports already in use

**Solution:**
1. Kill processes using ports 25000-25001
2. Or modify ports in `beam_transfer/network.py`
3. Ensure receivers use same ports

### Issue: Network discovery fails

**Solution:**
1. Verify both machines on same network
2. Check broadcast settings
3. Try disabling VPN
4. Test with ping between machines

## Post-Installation Checklist

- [ ] Python 3.8+ installed
- [ ] All dependencies installed
- [ ] Package installed via pip
- [ ] `beam --help` works
- [ ] Both commands accessible
- [ ] Ports 25000-25001 available
- [ ] Firewall configured
- [ ] Test transfer successful
- [ ] Key verification working
- [ ] Progress bars displaying

## Next Steps

Once verification is complete:
1. Read [QUICKSTART.md](QUICKSTART.md) for usage
2. Review [README.md](README.md) for features
3. Check [PROJECT.md](PROJECT.md) for architecture
4. Start transferring files!

---

**Last Updated**: 2024  
**Version**: 1.0.0

