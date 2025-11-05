"""
Application settings and configuration
"""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra='ignore'  # Ignore extra fields from .env
    )
    
    # Application
    app_name: str = "CargoDham AI Platform"
    
    # Environment
    environment: str = "development"
    debug: bool = True
    
    # Development/Testing Mode
    dev_mode: bool = True  # Bypass auth for testing
    bypass_tenant_check: bool = True  # Auto-assign tenant for testing
    
    # MongoDB
    mongodb_url: str
    mongodb_database: str = "ai_logistics_platform"
    
    # Redis
    redis_url: str
    redis_password: str = ""
    
    # OpenAI
    openai_api_key: str
    
    # Anthropic
    anthropic_api_key: str = ""
    
    # Google Gemini
    google_gemini_api_key: str = ""
    
    # Mistral AI (OCR)
    mistral_api_key: str = ""
    
    # Groq (Ultra-fast inference)
    groq_api_key: str = ""
    
    # Mem0
    mem0_api_key: str = ""
    
    # Pinecone
    pinecone_api_key: str = ""
    pinecone_environment: str = "us-west1-gcp"
    
    # JWT
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # CORS
    allowed_origins: str = "http://localhost:3000"
    
    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",")]
    
    # File Upload
    max_upload_size: int = 52428800  # 50MB
    upload_dir: str = "./uploads"
    
    # OCR Settings
    ocr_max_file_size: int = 52428800  # 50MB
    ocr_dpi: int = 200  # DPI for PDF to image conversion
    ocr_concurrent_limit: int = 5  # Max concurrent API calls
    ocr_cache_ttl: int = 3600  # Cache TTL in seconds (1 hour)
    ocr_max_batch_size: int = 10  # Max files per batch
    ocr_max_retries: int = 3  # Max retry attempts for failed pages
    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    
    # Vector DB (Chroma)
    vector_db_persist_dir: str = "./vector_db_data"
    vector_db_collection_prefix: str = "api_docs"
    embedding_model: str = "all-MiniLM-L6-v2"
    vector_db_chunk_size: int = 1000
    vector_db_chunk_overlap: int = 200
    vector_db_top_k: int = 3
    
    # Flow Vector Store (NEW - for test execution semantic memory)
    flow_db_path: str = "./data/flow_chroma_db"
    flow_db_enabled: bool = True
    sequential_learning: bool = True  # Enable sequential test execution with progressive learning
    flow_query_limit: int = 3  # Top-k results from flow queriessize: int = 1000
    vector_db_chunk_overlap: int = 200
    vector_db_top_k: int = 3


# Global settings instance
_settings = None

def get_settings() -> Settings:
    """Get global settings instance"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

# Export settings for direct import
settings = get_settings()


