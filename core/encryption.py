"""
Encryption utilities for secure memory storage
"""
import os
import base64
import secrets
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Union, Dict, Any
import json
import logging

logger = logging.getLogger(__name__)

class MemoryEncryption:
    """Secure encryption for memory storage with proper key derivation"""
    
    def __init__(self, password: str = None, salt: str = None):
        """
        Initialize encryption with password and salt
        
        Args:
            password: Master password for encryption
            salt: Salt for key derivation (should be unique per user)
        """
        if not password:
            raise ValueError("Password is required for encryption")
        
        if not salt:
            raise ValueError("Salt is required for secure encryption")
        
        try:
            # Convert salt to bytes if it's a string
            if isinstance(salt, str):
                salt_bytes = salt.encode('utf-8')
            else:
                salt_bytes = salt
            
            # Derive key from password using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt_bytes,
                iterations=100000,  # OWASP recommended minimum
            )
            key = base64.urlsafe_b64encode(kdf.derive(password.encode('utf-8')))
            self.key = key
            self.cipher_suite = Fernet(key)
            
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            raise ValueError(f"Encryption initialization failed: {e}")
    
    def encrypt_data(self, data: Union[str, Dict[str, Any]]) -> str:
        """
        Encrypt data and return base64 encoded string
        
        Args:
            data: String or dictionary to encrypt
            
        Returns:
            Base64 encoded encrypted string
        """
        try:
            if isinstance(data, dict):
                data = json.dumps(data, ensure_ascii=False)
            
            if not isinstance(data, str):
                data = str(data)
            
            encrypted_data = self.cipher_suite.encrypt(data.encode('utf-8'))
            return base64.urlsafe_b64encode(encrypted_data).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Failed to encrypt data: {e}")
            raise ValueError(f"Encryption failed: {e}")
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """
        Decrypt base64 encoded string and return original data
        
        Args:
            encrypted_data: Base64 encoded encrypted string
            
        Returns:
            Decrypted string
        """
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
            decrypted_data = self.cipher_suite.decrypt(encrypted_bytes)
            return decrypted_data.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Failed to decrypt data: {e}")
            raise ValueError(f"Decryption failed: {e}")
    
    def encrypt_json(self, data: Dict[str, Any]) -> str:
        """
        Encrypt JSON data
        
        Args:
            data: Dictionary to encrypt
            
        Returns:
            Base64 encoded encrypted string
        """
        try:
            return self.encrypt_data(json.dumps(data, ensure_ascii=False))
        except Exception as e:
            logger.error(f"Failed to encrypt JSON: {e}")
            raise ValueError(f"JSON encryption failed: {e}")
    
    def decrypt_json(self, encrypted_data: str) -> Dict[str, Any]:
        """
        Decrypt and parse JSON data
        
        Args:
            encrypted_data: Base64 encoded encrypted string
            
        Returns:
            Decrypted dictionary
        """
        try:
            decrypted_str = self.decrypt_data(encrypted_data)
            return json.loads(decrypted_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse decrypted JSON: {e}")
            raise ValueError(f"Invalid JSON data: {e}")
        except Exception as e:
            logger.error(f"Failed to decrypt JSON: {e}")
            raise ValueError(f"JSON decryption failed: {e}")
    
    def get_key_string(self) -> str:
        """Get the encryption key as a string for storage"""
        return base64.urlsafe_b64encode(self.key).decode('utf-8')
    
    @classmethod
    def from_key_string(cls, key_string: str):
        """Create encryption instance from key string"""
        try:
            instance = cls.__new__(cls)
            instance.key = base64.urlsafe_b64decode(key_string.encode('utf-8'))
            instance.cipher_suite = Fernet(instance.key)
            return instance
        except Exception as e:
            logger.error(f"Failed to create encryption from key string: {e}")
            raise ValueError(f"Invalid key string: {e}")
    
    @staticmethod
    def generate_user_salt(user_id: str) -> str:
        """Generate a deterministic but unique salt for a user"""
        # Create a deterministic salt based on user ID
        # This ensures the same user always gets the same salt
        import hashlib
        return hashlib.sha256(f"echoself_user_{user_id}".encode()).hexdigest()[:32]