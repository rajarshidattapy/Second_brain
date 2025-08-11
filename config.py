"""
Configuration settings for Echoself AI
"""
import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Puch AI Configuration
    PUCH_AI_TOKEN: str = ""
    PUCH_AI_BASE_URL: str = "https://api.puch.ai/v1"
    PUCH_USER_PHONE: str = ""  # Your WhatsApp number
    
    # LLM Configuration (Gemini Pro)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-pro"
    
    # Qdrant Configuration
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION_NAME: str = "echoself_memories"
    
    # Embedding Model
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    
    # Whisper STT Configuration
    WHISPER_MODEL: str = "small"  # small, medium, large
    
    # Encryption
    ENCRYPTION_KEY: Optional[str] = None  # Will be generated if not provided
    
    # Storage
    DATA_DIR: str = "./data"
    MEMORIES_FILE: str = "memories.json"
    
    # MCP Server
    MCP_SERVER_HOST: str = "0.0.0.0"
    MCP_SERVER_PORT: int = 8086
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Global settings instance
settings = Settings()

# Ensure data directory exists
os.makedirs(settings.DATA_DIR, exist_ok=True)