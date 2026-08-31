"""
EmbeddingEngine: singleton that loads the model ONCE at startup.
All ingestion and query calls reuse the same in-memory model.
CPU-safe: all-MiniLM-L6-v2 is ~80MB and runs in <100ms per batch.
"""
import os
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from app.core.config import get_settings

settings = get_settings()

_embedding_model: SentenceTransformer = None


def get_embedding_model() -> SentenceTransformer:
    """Lazy singleton — loads only once."""
    global _embedding_model
    if _embedding_model is None:
        try:
            # We use local_files_only=False by default to allow first-time download
            # but device="cpu" for stability on this env.
            _embedding_model = SentenceTransformer(
                settings.embedding_model,
                cache_folder=settings.model_cache_dir,
                device="cpu",
                trust_remote_code=True
            )
            print(f"[Embeddings] Model loaded: {settings.embedding_model}")
        except Exception as e:
            print(f"[Embeddings] [ERROR] Failed to load embedding model: {e}")
            # Fallback or re-raise
            raise RuntimeError(f"Embedding model failed to load: {e}")
    return _embedding_model


def _is_bge_model(model_name: str) -> bool:
    """Check if the model is a BGE variant that requires prefix."""
    return "bge" in model_name.lower()


def _bge_prefix(texts: list[str], is_query: bool = False, model_name: str = "") -> list[str]:
    """Apply BGE-specific prefixes only for BGE models."""
    if not _is_bge_model(model_name):
        return texts
    if is_query:
        return [f"query: {t}" for t in texts]
    return [f"passage: {t}" for t in texts]


def embed_texts(texts: list[str], is_query: bool = False) -> np.ndarray:
    """Batch embed a list of strings → float32 numpy array.
    
    Args:
        texts: List of text strings to embed
        is_query: If True and model is BGE, applies 'query: ' prefix.
    """
    model = get_embedding_model()
    model_name = settings.embedding_model
    prefixed_texts = _bge_prefix(texts, is_query=is_query, model_name=model_name)
    vectors = model.encode(
        prefixed_texts,
        batch_size=32,
        show_progress_bar=False,
        normalize_embeddings=True
    )
    return vectors.astype(np.float32)


# ── FAISS Index Management ────────────────────────────────────────────────────

def _index_path(doc_id: str) -> str:
    path = os.path.join(settings.storage_dir, "indexes")
    os.makedirs(path, exist_ok=True)
    return os.path.join(path, f"{doc_id}.faiss")


def build_faiss_index(vectors: np.ndarray, doc_id: str) -> faiss.Index:
    """Build an L2 index (works with normalized vectors = cosine sim)."""
    dim = vectors.shape[1]
    index = faiss.IndexFlatIP(dim)   # Inner product = cosine when normalized
    index.add(vectors)
    faiss.write_index(index, _index_path(doc_id))
    print(f"[FAISS] Built index for {doc_id}: {index.ntotal} vectors")
    return index


def load_faiss_index(doc_id: str) -> faiss.Index:
    path = _index_path(doc_id)
    if not os.path.exists(path):
        raise FileNotFoundError(f"No FAISS index for doc_id={doc_id}")
    return faiss.read_index(path)


def delete_faiss_index(doc_id: str):
    path = _index_path(doc_id)
    if os.path.exists(path):
        os.remove(path)


def search_index(
    index: faiss.Index,
    query_vector: np.ndarray,
    top_k: int = 6,
    threshold: float | None = 0.35
) -> tuple[list[int], list[float]]:
    """
    Returns (embedding_ids, scores) filtered by threshold.
    If threshold is None, returns top_k results without filtering.
    If nothing passes threshold → returns ([], []) → caller must refuse.
    """
    scores, indices = index.search(query_vector.reshape(1, -1), top_k)
    scores = scores[0].tolist()
    indices = indices[0].tolist()

    if threshold is None:
        filtered = [
            (idx, score)
            for idx, score in zip(indices, scores)
            if idx != -1
        ]
    else:
        filtered = [
            (idx, score)
            for idx, score in zip(indices, scores)
            if idx != -1 and score >= threshold
        ]

    if not filtered:
        return [], []

    ids, scs = zip(*filtered)
    return list(ids), list(scs)
