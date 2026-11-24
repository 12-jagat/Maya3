"""
MAYA Backend Configuration
Centralized configuration management using Pydantic Settings.
"""

from functools import lru_cache
from typing import List, Union
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    APP_NAME: str = "MAYA"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # Frontend CORS Origins
    FRONTEND_URL: Union[str, List[str]] = "http://localhost:5173"

    @property
    def cors_origins(self) -> List[str]:
        base_defaults = [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ]
        if isinstance(self.FRONTEND_URL, list):
            configured = self.FRONTEND_URL
        elif "," in self.FRONTEND_URL:
            configured = [o.strip() for o in self.FRONTEND_URL.split(",") if o.strip()]
        elif self.FRONTEND_URL:
            configured = [self.FRONTEND_URL.strip()]
        else:
            configured = []

        # Merge base defaults with configured origins preserving uniqueness
        merged = []
        for o in base_defaults + configured:
            if o and o not in merged:
                merged.append(o)
        return merged

    # Future AI & Database configuration (Milestones 2+)
    GEMINI_API_KEY: str = Field(default="")
    GEMINI_MODEL: str = Field(default="gemini-3.5-flash")

    SUPABASE_URL: str = Field(default="")
    SUPABASE_KEY: str = Field(default="")

    ZILLIZ_URI: str = Field(default="")
    ZILLIZ_TOKEN: str = Field(default="")

    EMBEDDING_MODEL: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")
    EMBEDDING_BATCH_SIZE: int = Field(default=64, description="Batch size for generating embeddings")
    CHUNK_SIZE: int = Field(default=700, description="Token-oriented target chunk size")
    CHUNK_OVERLAP: int = Field(default=120, description="Token overlap between adjacent chunks")
    ZILLIZ_COLLECTION: str = Field(default="maya_notice_chunks", description="Target Zilliz Cloud collection name")


    # Milestone 3: Crawler & Worker Configuration
    PDF_WORKERS: int = Field(default=8, description="Strict exactly 8 worker processes by default")
    PDF_DOWNLOAD_CONCURRENCY: int = Field(default=10, description="Max concurrent async PDF downloads")
    PDF_MAX_SIZE_MB: int = Field(default=30, description="Max size of PDF allowed to download in MB")
    OCR_ENABLED: bool = Field(default=True, description="Flag for OCR enablement (Milestone 4)")
    STORAGE_DIR: str = Field(default="storage", description="Base local directory for downloaded assets")

    # Milestone 5: Conversational RAG Configuration
    RAG_TOP_K: int = Field(default=5, description="Number of top chunks to retrieve for RAG context")
    RAG_SIMILARITY_THRESHOLD: float = Field(default=0.45, description="Initial tunable cosine similarity threshold")
    MAX_CONVERSATION_HISTORY: int = Field(default=8, description="Max previous messages to carry into prompt context")
    RAG_MAX_CONTEXT_TOKENS: int = Field(default=3500, description="Max tokens for retrieved document context")

    # Milestone 6: Multimodal Configuration
    MAX_IMAGE_SIZE_MB: int = Field(default=10, description="Max allowed image upload size in MB")
    MAX_DOCUMENT_SIZE_MB: int = Field(default=30, description="Max allowed document (PDF/DOCX) upload size in MB")
    MAX_AUDIO_SIZE_MB: int = Field(default=20, description="Max allowed audio upload size in MB")
    MAX_AUDIO_DURATION_SECONDS: int = Field(default=300, description="Max audio duration in seconds (5 minutes)")
    UPLOAD_DIR: str = Field(default="storage/uploads", description="Base directory for user uploaded files")

    @property
    def clean_supabase_url(self) -> str:
        """Return base Supabase URL stripped of /rest/v1 suffix if present."""
        url = self.SUPABASE_URL.strip()
        if url.endswith("/rest/v1/"):
            return url[:-9]
        if url.endswith("/rest/v1"):
            return url[:-8]
        return url.rstrip("/")



@lru_cache()
def get_settings() -> Settings:
    """Return cached singleton instance of application settings."""
    return Settings()
