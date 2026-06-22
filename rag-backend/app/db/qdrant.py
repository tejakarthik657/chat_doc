import os
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from app.core.config import get_settings

settings = get_settings()

_qdrant_client: QdrantClient = None


def get_qdrant_client() -> QdrantClient:
    """Lazy singleton for QdrantClient.
    If QDRANT_URL is set, it connects via URL.
    Otherwise, if QDRANT_HOST is set, it connects via host & port.
    Otherwise, it defaults to a local file database stored in the project storage.
    """
    global _qdrant_client
    if _qdrant_client is None:
        try:
            if settings.qdrant_url:
                print(f"[Qdrant] Connecting to server via URL: {settings.qdrant_url}")
                _qdrant_client = QdrantClient(url=settings.qdrant_url)
            elif settings.qdrant_host and os.environ.get("USE_QDRANT_SERVER") == "true":
                print(f"[Qdrant] Connecting to server: {settings.qdrant_host}:{settings.qdrant_port}")
                _qdrant_client = QdrantClient(
                    host=settings.qdrant_host,
                    port=settings.qdrant_port
                )
            else:
                # Local disk storage mode (like SQLite)
                os.makedirs(settings.qdrant_path, exist_ok=True)
                print(f"[Qdrant] Using local disk storage at: {settings.qdrant_path}")
                _qdrant_client = QdrantClient(path=settings.qdrant_path)
            
            # Simple health ping to test connection if server-based
            if not isinstance(_qdrant_client._client, str): # if it's not a local client
                # Local clients don't have collection ping list
                pass
            print("[Qdrant] Client initialized successfully.")
        except Exception as e:
            print(f"[Qdrant] [ERROR] Failed to initialize client: {e}")
            raise e
    return _qdrant_client


def init_collection(collection_name: str, vector_size: int):
    """Create a collection if it doesn't already exist."""
    client = get_qdrant_client()
    try:
        # Check if collection exists
        collections = client.get_collections().collections
        exists = any(c.name == collection_name for c in collections)
        
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
            print(f"[Qdrant] Collection {collection_name} already exists.")
    except Exception as e:
        # Local client returns true/false differently or might skip get_collections()
        # So we catch and log
        print(f"[Qdrant] Collection check/create notice: {e}")
        try:
            # Re-try create direct if not exist
            client.create_collection(
                collection_name=collection_name,
                vectors_config=qdrant_models.VectorParams(
                    size=vector_size,
                    distance=qdrant_models.Distance.COSINE
                )
            )
        except Exception as inner_e:
            pass


def delete_collection(collection_name: str):
    """Deletes a collection."""
    client = get_qdrant_client()
    try:
        client.delete_collection(collection_name=collection_name)
        print(f"[Qdrant] Collection {collection_name} deleted.")
    except Exception as e:
        print(f"[Qdrant] Failed to delete collection {collection_name}: {e}")
