"""
Security utilities for encryption and key management.
"""

import secrets
import string
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
import hashlib
import os


def generate_transfer_key(length: int = 6) -> str:
    """Generate a unique alphanumeric transfer key."""
    characters = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))


def get_key_hash(key: str) -> bytes:
    """Get SHA-256 hash of the transfer key."""
    return hashlib.sha256(key.encode()).digest()


class AESEncryptor:
    """AES encryption utility for secure file transfers."""
    
    def __init__(self, key: bytes):
        """Initialize with encryption key."""
        self.key = key
    
    def encrypt(self, plaintext: bytes) -> bytes:
        """Encrypt data using AES-256-CBC."""
        # Generate random IV
        iv = os.urandom(16)
        
        # Create cipher
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv))
        encryptor = cipher.encryptor()
        
        # Pad plaintext
        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(plaintext)
        padded_data += padder.finalize()
        
        # Encrypt
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()
        
        # Return IV + ciphertext
        return iv + ciphertext
    
    def decrypt(self, ciphertext: bytes) -> bytes:
        """Decrypt data using AES-256-CBC."""
        # Extract IV and ciphertext
        iv = ciphertext[:16]
        encrypted_data = ciphertext[16:]
        
        # Create cipher
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        
        # Decrypt
        padded_plaintext = decryptor.update(encrypted_data) + decryptor.finalize()
        
        # Unpad
        unpadder = padding.PKCS7(128).unpadder()
        plaintext = unpadder.update(padded_plaintext)
        plaintext += unpadder.finalize()
        
        return plaintext

