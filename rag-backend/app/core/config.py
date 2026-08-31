from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        protected_namespaces=("settings_",),
    )

    # ── Environment ─────────────────────────────────────────────────────────────
    environment: str = "development"

    # ── MongoDB ─────────────────────────────────────────────────────────────────
    mongodb_url: str = "mongodb://localhost:27017"
    db_name: str = "rag_db"

    # ── Auth ─────────────────────────────────────────────────────────────────────
    secret_key: str = "dev-secret-key-change-in-prod"
    access_token_expire_minutes: int = 10080

    # ── Storage ─────────────────────────────────────────────────────────────────
    storage_dir: str = "./storage"
    model_cache_dir: str = "./models"

    # ── Models ──────────────────────────────────────────────────────────────────
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    reranker_model: str = "BAAI/bge-reranker-base"
    reranker_enabled: bool = False
    local_llm_path: str = "./models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
    local_llm_type: str = "llama"

    # ── Groq ────────────────────────────────────────────────────────────────────
    groq_api_key: Optional[str] = None

    # ── Qdrant Vector Database ──────────────────────────────────────────────────
    qdrant_url: Optional[str] = None
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_path: str = "./storage/qdrant_db"

    # ── Neo4j Graph Database ────────────────────────────────────────────────────
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: str = "password"

    # ── RAG ─────────────────────────────────────────────────────────────────────
    retrieval_top_k: int = 25
    context_top_k: int = 8
    similarity_threshold: float = 0.25
    chunk_size: int = 1500
    chunk_overlap: int = 200

    # ── Feature Flags ───────────────────────────────────────────────────────────
    contextual_enabled: bool = True
    crag_enabled: bool = True

    # ── Free-tier limits ────────────────────────────────────────────────────────
    max_storage_mb: float = 50.0
    max_docs: int = 5
    max_questions_per_day: int = 50

    # ── Redis & Celery ──────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # ── Groq Resilience ────────────────────────────────────────────────────────
    groq_rate_limit_rpm: int = 30
    groq_retry_max_attempts: int = 4
    groq_circuit_breaker_threshold: int = 5
    groq_circuit_breaker_recovery_timeout: int = 60

    # ── CORS ────────────────────────────────────────────────────────────────────
    allowed_origins: str = ""

    # ── Upload Limits ───────────────────────────────────────────────────────────
    max_upload_size_mb: int = 50

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache()
def get_settings() -> Settings:
    return Settings()
