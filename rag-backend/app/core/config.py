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

    # ── Auth & OAuth ─────────────────────────────────────────────────────────────
    secret_key: str = "dev-secret-key-change-in-prod"
    access_token_expire_minutes: int = 10080
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    google_redirect_uri: str = "http://localhost:8000/api/auth/google/callback"
    frontend_url: str = "http://localhost:3000"

    # ── Storage & Media ─────────────────────────────────────────────────────────
    storage_dir: str = "./storage"
    model_cache_dir: str = "./models"
    cloudinary_url: Optional[str] = None

    # ── Models ──────────────────────────────────────────────────────────────────
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    reranker_model: str = "BAAI/bge-reranker-base"
    reranker_enabled: bool = False
    local_llm_path: str = "./models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
    local_llm_type: str = "llama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model_name: str = "qwen2.5-coder:3b"

    # ── Groq Multi-Key Pool ─────────────────────────────────────────────────────
    groq_api_key: Optional[str] = None
    groq_api_keys: Optional[str] = None  # Comma-separated list of multiple Groq API keys for pool rotation

    # ── Multi-Provider Cloud LLM Fallbacks ──────────────────────────────────────
    gemini_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None

    # ── Qdrant Vector Database ──────────────────────────────────────────────────
    qdrant_url: Optional[str] = None
    qdrant_api_key: Optional[str] = None
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_path: str = "./storage/qdrant_db"

    # ── Neo4j Graph Database ────────────────────────────────────────────────────
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: str = "password"
    neo4j_database: str = "neo4j"

    # ── Upstash Redis Cloud ─────────────────────────────────────────────────────
    upstash_redis_rest_url: Optional[str] = None
    upstash_redis_rest_token: Optional[str] = None

    # ── Observability & Monitoring (Langfuse & Sentry) ─────────────────────────
    langfuse_secret_key: Optional[str] = None
    langfuse_public_key: Optional[str] = None
    langfuse_base_url: str = "https://us.cloud.langfuse.com"
    sentry_dsn: Optional[str] = None

    # ── RAG ─────────────────────────────────────────────────────────────────────
    retrieval_top_k: int = 15          # Reduced from 25 for faster reranking
    context_top_k: int = 5             # Reduced from 8 — fewer chunks → faster reranker + smaller context
    similarity_threshold: float = 0.25
    chunk_size: int = 1200             # Slightly smaller chunks for faster processing
    chunk_overlap: int = 150

    # ── Feature Flags ───────────────────────────────────────────────────────────
    contextual_enabled: bool = False
    crag_enabled: bool = False         # Disabled: CRAG adds 1–3 extra Groq API calls per query (major latency)

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
    groq_retry_max_attempts: int = 2   # Reduced from 4 — fail fast, don't wait on dead endpoints
    groq_circuit_breaker_threshold: int = 5
    groq_circuit_breaker_recovery_timeout: int = 30  # Reduced from 60s

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
