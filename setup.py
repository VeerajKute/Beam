"""
Setup script for Beam Transfer CLI tool.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
readme_file = Path(__file__).parent / "README.md"
if readme_file.exists():
    try:
        long_description = readme_file.read_text(encoding='utf-8')
    except Exception:
        long_description = ""
else:
    long_description = ""

setup(
    name="beam-transfer",
    version="1.0.0",
    author="Beam Transfer Team",
    description="Fast, secure CLI-based file transfer tool for local networks",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/beam-transfer/beam-transfer",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Communications :: File Sharing",
        "Topic :: Utilities",
    ],
    python_requires=">=3.8",
    install_requires=[
        "cryptography>=3.4.8",
        "tqdm>=4.62.0",
    ],
    entry_points={
        "console_scripts": [
            "beam=beam_transfer.cli:main",
        ],
    },
    keywords="file-transfer network local-network cli security encryption",
)

