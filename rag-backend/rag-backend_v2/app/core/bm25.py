"""
BM25 Index Manager
──────────────────
Keyword-based retrieval to complement FAISS semantic search.
Uses rank_bm25 (pure Python, CPU, no cost).

Why BM25 alongside FAISS?
  - FAISS is great at meaning ("what treats high blood pressure?")
  - BM25 is great at exact terms ("ACE inhibitor", "metformin 500mg", "ICD-10 I10")
  - Together they catch what either alone misses (Hybrid Search)

Storage: BM25 indexes are pickled to disk, one per document.
"""
import os
import pickle
import re
from app.core.config import get_settings

settings = get_settings()


def _bm25_path(doc_id: str) -> str:
    path = os.path.join(settings.storage_dir, "bm25")
    os.makedirs(path, exist_ok=True)
    return os.path.join(path, f"{doc_id}.pkl")


def _tokenize(text: str) -> list[str]:
    """
    Simple but effective tokenizer for BM25.
    Lowercases, splits on non-alphanumeric, removes stop words.
    """
    STOP_WORDS = {
        "the", "a", "an", "is", "it", "in", "on", "at", "to", "for",
        "of", "and", "or", "but", "with", "this", "that", "are", "was",
        "be", "as", "by", "from", "has", "have", "had", "not", "what",
        "which", "who", "how", "when", "where", "can", "do", "does"
    }
    tokens = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return [t for t in tokens if t not in STOP_WORDS and len(t) > 1]


def build_bm25_index(chunks: list[dict], doc_id: str):
    """
    Build and persist a BM25 index from chunk texts.
    Called during ingestion alongside FAISS.
    """
    from rank_bm25 import BM25Okapi

    corpus = [_tokenize(c["text"]) for c in chunks]
    index = BM25Okapi(corpus)

    with open(_bm25_path(doc_id), "wb") as f:
        pickle.dump({"index": index, "chunk_count": len(chunks)}, f)

    print(f"[BM25] Built index for {doc_id}: {len(chunks)} chunks")


def load_bm25_index(doc_id: str):
    """Load a persisted BM25 index. Returns None if not found."""
    path = _bm25_path(doc_id)
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        data = pickle.load(f)
    return data["index"]


def delete_bm25_index(doc_id: str):
    path = _bm25_path(doc_id)
    if os.path.exists(path):
        os.remove(path)


def bm25_search(
    index,
    query: str,
    top_k: int = 10
) -> list[tuple[int, float]]:
    """
    Search BM25 index.
    Returns list of (embedding_id, normalized_score) sorted descending.
    embedding_id maps directly to chunk position (same order as ingestion).
    """
    tokens = _tokenize(query)
    if not tokens:
        return []

    scores = index.get_scores(tokens)

    # Normalize to 0–1 range (min-max)
    max_score = max(scores) if max(scores) > 0 else 1.0
    normalized = scores / max_score

    # Return top_k as (index, score) pairs
    ranked = sorted(enumerate(normalized), key=lambda x: x[1], reverse=True)
    return [(idx, float(score)) for idx, score in ranked[:top_k] if score > 0.0]
