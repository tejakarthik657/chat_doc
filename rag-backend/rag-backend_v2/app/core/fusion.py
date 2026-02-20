"""
Hybrid Search — Reciprocal Rank Fusion (RRF)
─────────────────────────────────────────────
Merges FAISS (semantic) and BM25 (keyword) result lists into
a single unified ranking without needing to tune score scales.

RRF Formula:
    score(d) = Σ 1 / (k + rank(d))   where k=60 (standard constant)

Why RRF instead of score averaging?
  - FAISS scores (cosine, 0–1) and BM25 scores (arbitrary) live on
    different scales. Averaging them directly distorts results.
  - RRF only uses rank positions, making it scale-invariant and robust.
  - Used in production by Elasticsearch, Cohere, and most hybrid RAG systems.

No ML required. Pure math. Zero cost.
"""


def reciprocal_rank_fusion(
    faiss_results: list[tuple[int, float]],   # (embedding_id, score)
    bm25_results: list[tuple[int, float]],    # (embedding_id, score)
    k: int = 60,
    top_k: int = 12
) -> list[tuple[int, float]]:
    """
    Fuse two ranked lists using Reciprocal Rank Fusion.

    Args:
        faiss_results:  Ranked list from FAISS semantic search
        bm25_results:   Ranked list from BM25 keyword search
        k:              RRF constant (60 is standard, reduces impact of top rank)
        top_k:          Number of fused results to return

    Returns:
        Fused list of (embedding_id, rrf_score) sorted descending.
    """
    rrf_scores: dict[int, float] = {}

    # Score from FAISS ranking
    for rank, (emb_id, _) in enumerate(faiss_results):
        rrf_scores[emb_id] = rrf_scores.get(emb_id, 0.0) + 1.0 / (k + rank + 1)

    # Score from BM25 ranking
    for rank, (emb_id, _) in enumerate(bm25_results):
        rrf_scores[emb_id] = rrf_scores.get(emb_id, 0.0) + 1.0 / (k + rank + 1)

    # Sort by fused score
    fused = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    return fused[:top_k]


def explain_fusion(
    faiss_results: list[tuple[int, float]],
    bm25_results: list[tuple[int, float]],
    fused: list[tuple[int, float]]
) -> dict:
    """
    Debug helper — shows which results came from which retriever.
    Useful during development/tuning.
    """
    faiss_ids = {emb_id for emb_id, _ in faiss_results}
    bm25_ids = {emb_id for emb_id, _ in bm25_results}

    breakdown = []
    for emb_id, score in fused:
        source = []
        if emb_id in faiss_ids:
            source.append("FAISS")
        if emb_id in bm25_ids:
            source.append("BM25")
        breakdown.append({
            "embedding_id": emb_id,
            "rrf_score": round(score, 4),
            "found_in": source,
            "overlap": len(source) == 2  # True = both retrievers agreed
        })

    overlap_count = sum(1 for b in breakdown if b["overlap"])
    return {
        "total_candidates": len(fused),
        "faiss_only": len(faiss_ids - bm25_ids),
        "bm25_only": len(bm25_ids - faiss_ids),
        "overlap": overlap_count,
        "breakdown": breakdown
    }
