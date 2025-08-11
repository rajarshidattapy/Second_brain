"""
Configuration settings for Echoself AI
"""
import os
import secrets
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Authentication
    AUTH_TOKEN: str = Field(..., description="Bearer token for MCP authentication")
    MY_NUMBER: str = Field(..., description="WhatsApp number for Puch AI integration")
    
    # Puch AI Configuration
    PUCH_AI_TOKEN: Optional[str] = Field(None, description="Puch AI API token")
    PUCH_AI_BASE_URL: str = Field("https://api.puch.ai/v1", description="Puch AI base URL")
    
    # LLM Configuration (Gemini Pro)
    GEMINI_API_KEY: str = Field(..., description="Google Gemini API key")
    GEMINI_MODEL: str = Field("gemini-pro", description="Gemini model to use")
    
    # Qdrant Configuration
    QDRANT_URL: str = Field("http://localhost:6333", description="Qdrant server URL")
    QDRANT_API_KEY: Optional[str] = Field(None, description="Qdrant API key")
    QDRANT_COLLECTION_NAME: str = Field("echoself_memories", description="Qdrant collection name")
    
    # Embedding Model
    EMBEDDING_MODEL: str = Field("all-MiniLM-L6-v2", description="Sentence transformer model")
    
    # Whisper STT Configuration
    WHISPER_MODEL: str = Field("small", description="Whisper model size")
    
    # Encryption
    ENCRYPTION_KEY: Optional[str] = Field(None, description="Encryption key (auto-generated if not provided)")
    ENCRYPTION_SALT: Optional[str] = Field(None, description="Encryption salt (auto-generated if not provided)")
    
    # Storage
    DATA_DIR: str = Field("./data", description="Data directory path")
    MEMORIES_FILE: str = Field("memories.json", description="Memories file name")
    
    # MCP Server
    MCP_SERVER_HOST: str = Field("0.0.0.0", description="MCP server host")
    MCP_SERVER_PORT: int = Field(8086, description="MCP server port")
    
    # Logging
    LOG_LEVEL: str = Field("INFO", description="Logging level")
    
    @validator('AUTH_TOKEN')
    def validate_auth_token(cls, v):
        if not v or len(v) < 32:
            raise ValueError("AUTH_TOKEN must be at least 32 characters long")
        return v
    
    @validator('MY_NUMBER')
    def validate_phone_number(cls, v):
        if not v or not v.isdigit() or len(v) < 10:
            raise ValueError("MY_NUMBER must be a valid phone number with at least 10 digits")
        return v
    
    @validator('GEMINI_API_KEY')
    def validate_gemini_key(cls, v):
        if not v or len(v) < 20:
            raise ValueError("GEMINI_API_KEY is required and must be valid")
        return v
    
    @validator('DATA_DIR')
    def validate_data_dir(cls, v):
        Path(v).mkdir(parents=True, exist_ok=True)
        return v
    
    @validator('ENCRYPTION_KEY', pre=True, always=True)
    def generate_encryption_key(cls, v):
        if not v:
            return secrets.token_urlsafe(32)
        return v
    
    @validator('ENCRYPTION_SALT', pre=True, always=True)
    def generate_encryption_salt(cls, v):
        if not v:
            return secrets.token_urlsafe(16)
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

# Global settings instance
try:
    settings = Settings()
except Exception as e:
    print(f"Configuration error: {e}")
    print("Please check your .env file and ensure all required variables are set.")
    raise

# Ensure data directory exists
Path(settings.DATA_DIR).mkdir(parents=True, exist_ok=True)