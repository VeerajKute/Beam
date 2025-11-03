# Installation Guide

This guide will help you install Beam Transfer on your system.

## Prerequisites

Before installing Beam Transfer, ensure you have:

- **Python 3.8 or higher** installed on your system
- **pip** (Python package installer) - usually comes with Python
- Access to a terminal/command prompt

To check if Python is installed:

```bash
python --version
# or
python3 --version
```

To check if pip is installed:

```bash
pip --version
# or
pip3 --version
```

### Upgrading Python or pip (If Using Older Versions)

If your Python version is below 3.8 or your pip is outdated, follow these steps:

#### Upgrading pip

If pip is installed but outdated, upgrade it using:

**Windows:**
```cmd
python -m pip install --upgrade pip
# or
python -m pip install --upgrade pip --user
```

**macOS / Linux:**
```bash
python3 -m pip install --upgrade pip
# or
python3 -m pip install --upgrade pip --user
```

**Alternative method (using pip itself):**
```bash
pip install --upgrade pip
# or
pip3 install --upgrade pip
```

#### Upgrading Python

If Python version is below 3.8, you need to upgrade Python:

**Windows:**
1. Visit [python.org/downloads](https://www.python.org/downloads/)
2. Download the latest Python 3.x version
3. Run the installer and check "Add Python to PATH"
4. Restart your terminal and verify: `python --version`

**macOS:**
```bash
# Using Homebrew (recommended)
brew install python3
# or upgrade if already installed
brew upgrade python3

# Verify installation
python3 --version
```

**Linux (Ubuntu/Debian):**
```bash
# Update package list
sudo apt update

# Install Python 3.8 or higher
sudo apt install python3.8
# or for latest version
sudo apt install python3

# Verify installation
python3 --version
```

**Linux (Fedora/RHEL/CentOS):**
```bash
# Install Python 3.8 or higher
sudo dnf install python3
# or
sudo yum install python3

# Verify installation
python3 --version
```

After upgrading Python, pip should be included automatically. If not, use:
```bash
python3 -m ensurepip --upgrade
```

## Installation Steps

### Windows

1. **Open Command Prompt as Administrator**
   - Press `Win + X` and select "Command Prompt (Admin)" or "PowerShell (Admin)"

2. **Navigate to the project directory**
   ```cmd
   cd D:\drts_project
   ```

3. **Install the package**
   ```cmd
   pip install .
   ```

4. **Verify installation**
   ```cmd
   beam --help
   ```

### macOS / Linux

1. **Open Terminal**

2. **Navigate to the project directory**
   ```bash
   cd /path
   ```

3. **Install the package**
   ```bash
   pip3 install .
   ```

4. **Verify installation**
   ```bash
   beam --help
   ```

## Alternative: Installing from Requirements

If you prefer to install dependencies separately:

```bash
# Install dependencies
pip install -r requirements.txt

# Then install the package
pip install .
```

## Troubleshooting Installation

### Issue: Python or pip version is too old

**Solution:**
- If Python is below 3.8, see the [Upgrading Python or pip](#upgrading-python-or-pip-if-using-older-versions) section above
- If pip is outdated, upgrade it using: `python -m pip install --upgrade pip` (Windows) or `python3 -m pip install --upgrade pip` (macOS/Linux)
- Some packages may require specific pip features available in newer versions

### Issue: "pip: command not found"

**Solution:**
- Install pip: `python -m ensurepip --upgrade`
- Or download get-pip.py and run it

### Issue: "Permission denied" (Linux/macOS)

**Solution:**
- Use `sudo pip3 install .` (not recommended)
- Better: Use a virtual environment or install with `pip install --user .`

### Issue: Python not found in PATH

**Solution:**
1. Reinstall Python and check "Add Python to PATH" during installation
2. Manually add Python to your system PATH environment variable

### Issue: "beam: command not found" after installation

**Solution:**
1. Find where pip installed scripts:
   ```bash
   python -m site --user-base
   ```
2. Add that path + `/Scripts` (Windows) or `/bin` (Linux/macOS) to your PATH
3. Restart your terminal

**Detailed Steps for Windows:**

If you see a warning during installation like:
```
WARNING: The script beam.exe is installed in 'C:\Users\...\Scripts' which is not on PATH.
```

Follow these steps to add the Scripts directory to your PATH:

**Step 1: Find the Scripts directory**

Open Command Prompt or PowerShell and run:
```cmd
python -m site --user-base
```

This will output a path like:
```
C:\Users\VEERAJ\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.10_qbz5n2kfra8p0\LocalCache\local-packages\Python310
```

**Step 2: Add `\Scripts` to the path**

Copy that path and add `\Scripts` at the end:
```
C:\Users\VEERAJ\AppData\Local\Packages\PythonSoftwareFoundation.Python.3.10_qbz5n2kfra8p0\LocalCache\local-packages\Python310\Scripts
```

**Step 3: Add to PATH**

Choose one of these methods:

**Method 1 - Using Settings GUI:**

1. Press `Win + I` to open Settings
2. Search for "environment variables" in the search bar
3. Click "Edit the system environment variables"
4. Click "Environment Variables" button at the bottom
5. Under "User variables" (top section), find and select "Path"
6. Click "Edit..."
7. Click "New"
8. Paste the Scripts path you copied (with `\Scripts` at the end)
9. Click "OK" on all open dialogs

**Method 2 - Using System Properties:**

1. Press `Win + X` and select "System"
2. Click "Advanced system settings" on the right
3. Click "Environment Variables" button
4. Under "User variables" (top section), find and select "Path"
5. Click "Edit..."
6. Click "New"
7. Paste the Scripts path (with `\Scripts` at the end)
8. Click "OK" on all open dialogs

**Step 4: Restart your terminal**

- Close all open Command Prompt/PowerShell windows
- Open a new Command Prompt or PowerShell window
- The `beam` command should now work!

**Step 5: Verify it works**

```cmd
beam --help
```

If it still doesn't work, try:
```cmd
refreshenv
```
Or restart your computer.

**Alternative: Use Python module directly (No PATH changes needed)**

If you prefer not to modify PATH, you can use:
```cmd
python -m beam_transfer.cli --help
python -m beam_transfer.cli send file.txt
python -m beam_transfer.cli receive
```

**For macOS/Linux:**

1. Find the Scripts/bin directory:
   ```bash
   python3 -m site --user-base
   ```
2. Add to PATH in your shell profile (`~/.bashrc`, `~/.zshrc`, etc.):
   ```bash
   export PATH="$PATH:$(python3 -m site --user-base)/bin"
   ```
3. Reload your shell:
   ```bash
   source ~/.bashrc  # or source ~/.zshrc
   ```

### Using a Virtual Environment (Recommended)

Create an isolated environment for Beam Transfer:

```bash
# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install Beam Transfer
pip install .

# Use it
beam --help

# Deactivate when done
deactivate
```

## Uninstallation

To uninstall Beam Transfer:

```bash
pip uninstall beam-transfer
```

## Next Steps

After installation, read the [README.md](README.md) for usage instructions!

