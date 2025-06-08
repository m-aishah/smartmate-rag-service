from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Supabase Configuration
    supabase_url: str
    supabase_key: str
    supabase_service_role_key: str
    
    # Database Configuration
    database_url: str
    
    # Embedding Model Configuration
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    
    # Text Processing Configuration
    chunk_size: int = 500
    chunk_overlap: int = 50
    max_file_size_mb: int = 50
    
    # API Configuration
    api_title: str = "RAG Service API"
    api_version: str = "1.0.0"
    api_description: str = "Retrieval-Augmented Generation Service for Document Processing"
    
    # CORS Configuration
    cors_origins: list = ["*"]
    
    # Logging Configuration
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()