"""
Cross-Encoder Reranker
──────────────────────
Model: cross-encoder/ms-marco-MiniLM-L-6-v2
Size:  ~22MB — runs comfortably on CPU
Task:  Given (query, chunk) pairs → relevance score

Why reranking matters:
  Bi-encoder FAISS retrieves fast but coarsely (embedding similarity).
  Cross-encoder reads BOTH query AND chunk together → far more accurate.

Pipeline position:
  FAISS + BM25 retrieve top-12 candidates → Reranker picks best 3–5.
  This is the "precision layer" that eliminates the biggest source of
  bad answers: good retrieval, wrong chunks making it to the LLM.

Loaded ONCE at startup as singleton (same as embedding model).
"""
from app.core.config import get_settings

settings = get_settings()

RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
_reranker = None


def get_reranker():
    """Lazy singleton — loads cross-encoder once at startup."""
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder
        print(f"[Reranker] Loading {RERANKER_MODEL}...")
        _reranker = CrossEncoder(
            RERANKER_MODEL,
            max_length=512,          # keeps CPU inference fast
            device="cpu"
        )
        print("[Reranker] Model ready.")
    return _reranker


def rerank_chunks(
    query: str,
    chunks: list[dict],
    top_k: int = None
) -> list[tuple[dict, float]]:
    """
    Rerank retrieved chunks using the cross-encoder.

    Args:
        query:   The user's original question
        chunks:  Candidate chunks from FAISS + BM25 fusion
        top_k:   How many to keep (defaults to settings.context_top_k)

    Returns:
        List of (chunk, rerank_score) sorted best-first, capped at top_k.
    """
    if top_k is None:
        top_k = settings.context_top_k

    if not chunks:
        return []

    reranker = get_reranker()

    # Build (query, chunk_text) pairs for cross-encoder
    pairs = [(query, chunk["text"]) for chunk in chunks]

    # Score all pairs in one batch
    scores = reranker.predict(pairs, show_progress_bar=False)

    # Zip chunks with scores, sort descending
    ranked = sorted(
        zip(chunks, scores.tolist()),
        key=lambda x: x[1],
        reverse=True
    )

    return ranked[:top_k]
