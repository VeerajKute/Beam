"""
Utility functions for cross-platform compatibility.
"""

import sys
import io


def safe_print(*args, **kwargs):
    """Print with Windows console encoding support."""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        # Replace Unicode characters with ASCII equivalents
        safe_args = []
        for arg in args:
            if isinstance(arg, str):
                arg = arg.replace('✓', '[OK]').replace('✗', '[ERROR]')
                arg = arg.replace('⚠️', '[WARNING]').replace('🟢', '[READY]')
                arg = arg.replace('🔍', '[SEARCHING]')
            safe_args.append(arg)
        print(*safe_args, **kwargs)


def setup_windows_encoding():
    """Setup UTF-8 encoding for Windows console."""
    if sys.platform == 'win32':
        try:
            # Try to set UTF-8 encoding
            if sys.stdout.encoding != 'utf-8':
                sys.stdout = io.TextIOWrapper(
                    sys.stdout.buffer,
                    encoding='utf-8',
                    errors='replace',
                    line_buffering=True
                )
        except Exception:
            pass  # If it fails, continue with default encoding

