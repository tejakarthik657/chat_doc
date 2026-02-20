from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        protected_namespaces=("settings_",),  # allows model_cache_dir (no model_ conflict)
    )
    # MongoDB
    mongodb_url: str = "mongodb://localhost:27017"
    db_name: str = "rag_db"

    # Auth
    secret_key: str = "dev-secret-key-change-in-prod"
    access_token_expire_minutes: int = 10080

    # Storage
    storage_dir: str = "./storage"
    model_cache_dir: str = "./models"

    # Models
    embedding_model: str = "all-MiniLM-L6-v2"
    local_llm_path: str = "./models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
    local_llm_type: str = "llama"

    # Groq
    groq_api_key: Optional[str] = None

    # RAG
    retrieval_top_k: int = 6
    context_top_k: int = 3
    similarity_threshold: float = 0.20
    chunk_size: int = 700
    chunk_overlap: int = 100

    # Free-tier limits
    max_storage_mb: float = 50.0
    max_docs: int = 5
    max_questions_per_day: int = 50


@lru_cache()
def get_settings() -> Settings:
    return Settings()
