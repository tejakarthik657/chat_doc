"""
EmbeddingEngine: Ultra-low RAM embedding singleton.
Supports FastEmbed (ONNX engine: ~70MB RAM, optimal for Render 512MB free tier)
with graceful fallback to SentenceTransformers.
CPU-safe: BAAI/bge-small-en-v1.5 produces 384-dimensional dense vectors.
"""
import os
import numpy as np
import faiss
from app.core.config import get_settings

settings = get_settings()

_embedding_model = None
_fastembed_model = None


def get_embedding_model():
    """Ultra-low RAM singleton. Prefers FastEmbed (ONNX, ~70MB) over PyTorch (~550MB)."""
    global _embedding_model, _fastembed_model
    # 1. Try FastEmbed (ONNX engine: ideal for 512MB RAM cloud tiers like Render)
    try:
        if _fastembed_model is None:
            from fastembed import TextEmbedding
            _fastembed_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
            print("[Embeddings] FastEmbed ONNX engine loaded (RAM < 80MB).")
        return _fastembed_model
    except Exception:
        pass

    # 2. Fallback to SentenceTransformer (PyTorch)
    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _embedding_model = SentenceTransformer(
                settings.embedding_model,
                cache_folder=settings.model_cache_dir,
                device="cpu",
                trust_remote_code=True,
                local_files_only=True,
            )
            print(f"[Embeddings] Model loaded from local cache: {settings.embedding_model}")
        except Exception:
            try:
                from sentence_transformers import SentenceTransformer
                _embedding_model = SentenceTransformer(
                    settings.embedding_model,
                    cache_folder=settings.model_cache_dir,
                    device="cpu",
                    trust_remote_code=True,
                    local_files_only=False,
                )
                print(f"[Embeddings] Model downloaded and loaded: {settings.embedding_model}")
            except Exception as e:
                print(f"[Embeddings] [ERROR] Failed to load embedding model: {e}")
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
    """Batch embed a list of strings -> float32 numpy array. Supports FastEmbed and SentenceTransformers."""
    model = get_embedding_model()
    model_name = settings.embedding_model
    prefixed_texts = _bge_prefix(texts, is_query=is_query, model_name=model_name)

    if hasattr(model, "embed"):
        # FastEmbed ONNX generator
        embeddings = list(model.embed(prefixed_texts))
        return np.array(embeddings, dtype=np.float32)
    else:
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
    If nothing passes threshold -> returns ([], []) -> caller must refuse.
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
