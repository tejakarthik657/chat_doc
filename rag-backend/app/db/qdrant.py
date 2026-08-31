import os
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from app.core.config import get_settings

settings = get_settings()

_qdrant_client: QdrantClient = None


def get_qdrant_client() -> QdrantClient:
    """Lazy singleton for QdrantClient.
    Priority:
      1. QDRANT_URL (Qdrant Cloud or remote) - uses API key if provided
      2. USE_QDRANT_SERVER=true with host/port (self-hosted)
      3. Local disk storage (development only)
    """
    global _qdrant_client
    if _qdrant_client is None:
        try:
            if settings.qdrant_url:
                client_kwargs = {"url": settings.qdrant_url}
                if os.environ.get("QDRANT_API_KEY"):
                    client_kwargs["api_key"] = os.environ.get("QDRANT_API_KEY")
                print(f"[Qdrant] Connecting to server via URL: {settings.qdrant_url}")
                _qdrant_client = QdrantClient(**client_kwargs)
            elif settings.qdrant_host and os.environ.get("USE_QDRANT_SERVER") == "true":
                print(f"[Qdrant] Connecting to server: {settings.qdrant_host}:{settings.qdrant_port}")
                _qdrant_client = QdrantClient(
                    host=settings.qdrant_host,
                    port=settings.qdrant_port,
                )
            else:
                os.makedirs(settings.qdrant_path, exist_ok=True)
                print(f"[Qdrant] Using local disk storage at: {settings.qdrant_path}")
                _qdrant_client = QdrantClient(path=settings.qdrant_path)

            print("[Qdrant] Client initialized successfully.")
        except Exception as e:
            print(f"[Qdrant] [ERROR] Failed to initialize client: {e}")
            raise e
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
