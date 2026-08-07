"""
Application Configuration
==========================
Centralized settings management using Pydantic BaseSettings.
All values are read from environment variables / .env file.
"""

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application-wide configuration.

    All fields are populated from environment variables or the .env file.
    Using @lru_cache (see get_settings()) ensures this is a singleton.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ─────────────────────────────────────────
    APP_NAME: str = "AI Resume Intelligence Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # ── Server ───────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── PostgreSQL ───────────────────────────────────────────
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:password@localhost:5432/resume_intelligence",
        description="Async PostgreSQL connection string (asyncpg driver)",
    )
    DATABASE_URL_SYNC: str = Field(
        default="postgresql+psycopg2://postgres:password@localhost:5432/resume_intelligence",
        description="Sync PostgreSQL connection string for Alembic migrations",
    )
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    # ── Security ─────────────────────────────────────────────
    SECRET_KEY: str = "change-this-secret-key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ── Google Gemini ────────────────────────────────────────
    GEMINI_API_KEY: str = Field(default="", description="Google Gemini API key")
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # ── Embedding Model ──────────────────────────────────────
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_CACHE_DIR: str = "cache/embeddings"

    # ── FAISS ────────────────────────────────────────────────
    FAISS_INDEX_DIR: str = "cache/faiss"

    # ── Redis ────────────────────────────────────────────────
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for L1 embedding cache",
    )
    REDIS_EMBEDDING_TTL: int = 86_400   # 24 hours
    REDIS_RESPONSE_TTL: int = 43_200    # 12 hours

    # ── File Uploads ─────────────────────────────────────────
    MAX_FILE_SIZE_MB: int = 10
    UPLOAD_DIR: str = "uploads"
    ALLOWED_EXTENSIONS: str = "pdf,docx,txt"

    # ── RAG Pipeline ─────────────────────────────────────────
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50
    TOP_K_RESULTS: int = 5

    # ── CORS ─────────────────────────────────────────────────
    ALLOWED_ORIGINS: List[str] = ["http://localhost:8501", "http://localhost:3000"]

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def parse_db_url(cls, v):
        """Fix asyncpg connection issues with Neon DB query parameters."""
        if isinstance(v, str) and "?" in v:
            base_url, query = v.split("?", 1)
            if "ssl" in query.lower():
                return f"{base_url}?ssl=require"
            return base_url
        return v

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v):
        """Accept comma-separated string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @property
    def allowed_extensions_list(self) -> List[str]:
        """Return allowed file extensions as a list."""
        return [ext.strip().lower() for ext in self.ALLOWED_EXTENSIONS.split(",")]

    @property
    def max_file_size_bytes(self) -> int:
        """Return max file size in bytes."""
        return self.MAX_FILE_SIZE_MB * 1024 * 1024


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return a cached singleton Settings instance.
    Using lru_cache ensures the .env file is only read once.
    """
    return Settings()


# Module-level singleton for convenience
settings: Settings = get_settings()
