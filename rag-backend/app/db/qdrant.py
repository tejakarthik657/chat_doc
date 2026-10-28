import os
import shutil
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from app.core.config import get_settings

settings = get_settings()

_qdrant_client: QdrantClient = None


def get_qdrant_client() -> QdrantClient:
    """Lazy singleton for QdrantClient.
    Priority:
      1. QDRANT_URL or USE_QDRANT_SERVER=true (Remote/Docker Qdrant Server)
      2. Local disk storage (with automatic metadata error recovery)
      3. In-memory storage (fallback if disk storage is inaccessible)
    """
    global _qdrant_client
    if _qdrant_client is None:
        use_server = os.environ.get("USE_QDRANT_SERVER", "false").lower() == "true" or bool(settings.qdrant_url)
        
        if use_server:
            q_url = settings.qdrant_url or f"http://{settings.qdrant_host}:{settings.qdrant_port}"
            try:
                client_kwargs = {"url": q_url, "timeout": 3.0}
                api_key = settings.qdrant_api_key or os.environ.get("QDRANT_API_KEY")
                if api_key:
                    client_kwargs["api_key"] = api_key
                print(f"[Qdrant] Connecting to Qdrant Cloud/Server at {q_url}...")
                temp_client = QdrantClient(**client_kwargs)
                temp_client.get_collections()
                _qdrant_client = temp_client
                print("[Qdrant] Connected to Qdrant Server successfully.")
                return _qdrant_client
            except Exception as remote_err:
                print(f"[Qdrant] [WARNING] Could not connect to Qdrant Server at {q_url}: {remote_err}")
                if os.environ.get("ENVIRONMENT") == "production":
                    raise remote_err

        # Local disk storage initialization with self-healing recovery
        try:
            os.makedirs(settings.qdrant_path, exist_ok=True)
            print(f"[Qdrant] Initializing local disk storage at: {settings.qdrant_path}")
            temp_client = QdrantClient(path=settings.qdrant_path)
            temp_client.get_collections()
            _qdrant_client = temp_client
            print("[Qdrant] Local disk client initialized.")
        except Exception as local_err:
            err_str = str(local_err).lower()
            if "already accessed" in err_str or "lock" in err_str:
                print(f"[Qdrant] Local directory is locked by another running process. Using in-memory client for this process.")
                _qdrant_client = QdrantClient(":memory:")
            else:
                print(f"[Qdrant] [WARNING] Local disk metadata issue ({local_err}). Falling back to in-memory mode...")
                _qdrant_client = QdrantClient(":memory:")

    return _qdrant_client


def init_collection(collection_name: str, vector_size: int, force_recreate: bool = False):
    """Create or recreate a collection."""
    client = get_qdrant_client()
    try:
        collections = client.get_collections().collections
        exists = any(c.name == collection_name for c in collections)

        if exists and force_recreate:
            print(f"[Qdrant] Dropping existing collection for re-ingest: {collection_name}")
            try:
                client.delete_collection(collection_name=collection_name)
            except Exception:
                pass
            exists = False

        if not exists:
            print(f"[Qdrant] Creating collection: {collection_name} (dim={vector_size})")
            client.create_collection(
                collection_name=collection_name,
                vectors_config=qdrant_models.VectorParams(
                    size=vector_size,
                    distance=qdrant_models.Distance.COSINE
                )
            )
            print(f"[Qdrant] Collection {collection_name} created.")
        else:
            print(f"[Qdrant] Collection {collection_name} already exists (reusing).")
    except Exception as e:
        print(f"[Qdrant] Collection init notice: {e}")
        try:
            client.create_collection(
                collection_name=collection_name,
                vectors_config=qdrant_models.VectorParams(
                    size=vector_size,
                    distance=qdrant_models.Distance.COSINE
                )
            )
        except Exception:
            pass


def search_collection(
    collection_name: str,
    query_vector: list[float],
    limit: int = 10,
    query_filter=None,
) -> list:
    """Vector similarity search."""
    client = get_qdrant_client()
    response = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        query_filter=query_filter,
        limit=limit,
        with_payload=True,
    )
    return response.points


def check_qdrant_health() -> bool:
    """Return True if Qdrant client can list collections."""
    try:
        client = get_qdrant_client()
        client.get_collections()
        return True
    except Exception as e:
        print(f"[Qdrant] Health check failed: {e}")
        return False


def delete_collection(collection_name: str):
    """Deletes a collection."""
    client = get_qdrant_client()
    try:
        client.delete_collection(collection_name=collection_name)
        print(f"[Qdrant] Collection {collection_name} deleted.")
    except Exception as e:
        print(f"[Qdrant] Failed to delete collection {collection_name}: {e}")
