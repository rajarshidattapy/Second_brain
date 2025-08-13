"""
Encryption utilities for secure memory storage
"""
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Union
import json

class MemoryEncryption:
    def __init__(self, password: str = None):
        if password is None:
            # Generate a random key if none provided
            self.key = Fernet.generate_key()
        else:
            # Derive key from password
            salt = b'echoself_salt_2024'  # In production, use random salt
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
            self.key = key
        
        self.cipher_suite = Fernet(self.key)
    
    def encrypt_data(self, data: Union[str, dict]) -> str:
        """Encrypt data and return base64 encoded string"""
        if isinstance(data, dict):
            data = json.dumps(data)
        
        encrypted_data = self.cipher_suite.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted_data).decode()
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt base64 encoded string and return original data"""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self.cipher_suite.decrypt(encrypted_bytes)
            return decrypted_data.decode()
        except Exception as e:
            raise ValueError(f"Failed to decrypt data: {e}")
    
    def encrypt_json(self, data: dict) -> str:
        """Encrypt JSON data"""
        return self.encrypt_data(json.dumps(data))
    
    def decrypt_json(self, encrypted_data: str) -> dict:
        """Decrypt and parse JSON data"""
        decrypted_str = self.decrypt_data(encrypted_data)
        return json.loads(decrypted_str)
    
    def get_key_string(self) -> str:
        """Get the encryption key as a string for storage"""
        return base64.urlsafe_b64encode(self.key).decode()
    
    @classmethod
    def from_key_string(cls, key_string: str):
        """Create encryption instance from key string"""
        instance = cls.__new__(cls)
        instance.key = base64.urlsafe_b64decode(key_string.encode())
        instance.cipher_suite = Fernet(instance.key)
        return instance