from functools import lru_cache
from pathlib import Path
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")
    app_env: str = "development"
    database_url: str = "sqlite:///./data/app.db"
    jwt_secret: str = Field(default="development-only-change-me-immediately-123", min_length=32)
    cors_origins: str = "http://localhost:5173"
    storage_dir: Path = Path("./data/uploads")
    qdrant_path: Path = Path("./data/qdrant")
    qdrant_url: str = ""
    redis_url: str = ""
    max_upload_mb: int = Field(default=30, ge=1, le=500)
    embedding_provider: str = "bge"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    vector_backend: str = "qdrant"
    llm_provider: str = "extractive"
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5"
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3"
    whisper_model: str = "medium"
    enable_reranker: bool = False
    rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    enable_image_caption: bool = False
    enable_clip: bool = False
    ocr_lang: str = "eng"
    ocr_engine: str = "tesseract"
    pdf_table_engine: str = "pdfplumber"
    unstructured_fallback: bool = False
    admin_email: str = ""
    admin_password: str = ""

    @field_validator("embedding_provider")
    @classmethod
    def embedding_choice(cls, v: str) -> str:
        if v not in {"bge", "e5", "sentence-transformers", "openai", "hash"}:
            raise ValueError("unsupported embedding provider")
        return v

    @field_validator("vector_backend")
    @classmethod
    def vector_choice(cls, v: str) -> str:
        if v not in {"qdrant", "chroma", "faiss"}:
            raise ValueError("unsupported vector backend")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
