"""
BM25 Index Manager (Hybrid Storage: Fast-Path Local Disk Cache + Durable MongoDB Collection)
─────────────────────────────────────────────────────────────────────────────────────────────
Keyword-based retrieval to complement dense vector search.
Uses rank_bm25 (pure Python, CPU, zero cost).

Durable Storage:
  - Local Disk: /storage/bm25/{doc_id}.pkl (sub-millisecond hot cache)
  - MongoDB Atlas: bm25_indexes collection (compressed binary, zero loss across container restarts/redeploys)
"""
import os
import pickle
import re
import zlib
from datetime import datetime
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


async def build_bm25_index(chunks: list[dict], doc_id: str):
    """
    Build BM25 index from chunk texts and persist to both:
    1. Local filesystem cache for fast reads
    2. MongoDB bm25_indexes collection for container restart durability
    """
    from rank_bm25 import BM25Okapi

    corpus = [_tokenize(c["text"]) for c in chunks]
    index = BM25Okapi(corpus)
    pickled = pickle.dumps({"index": index, "chunk_count": len(chunks)})

    # Fast-path local write
    try:
        with open(_bm25_path(doc_id), "wb") as f:
            f.write(pickled)
    except Exception as e:
        print(f"[BM25] Local write notice: {e}")

    # Durable MongoDB write
    try:
        from app.db.mongodb import bm25_indexes_col
        compressed = zlib.compress(pickled)
        await bm25_indexes_col().update_one(
            {"doc_id": doc_id},
            {"$set": {
                "doc_id": doc_id,
                "data": compressed,
                "chunk_count": len(chunks),
                "updated_at": datetime.utcnow()
            }},
            upsert=True
        )
        print(f"[BM25] Persisted durable index for {doc_id}: {len(chunks)} chunks ({len(compressed)/1024:.1f} KB in MongoDB)")
    except Exception as mongo_err:
        print(f"[BM25] MongoDB persist notice: {mongo_err}")


async def load_bm25_index(doc_id: str):
    """
    Load BM25 index.
    Checks local disk first. If missing (e.g. Render redeploy/restart), restores
    immediately from durable MongoDB storage and rehydrates the local cache.
    """
    path = _bm25_path(doc_id)
    if os.path.exists(path):
        try:
            with open(path, "rb") as f:
                data = pickle.load(f)
            return data["index"]
        except Exception:
            pass

    # Durable restore from MongoDB Atlas
    try:
        from app.db.mongodb import bm25_indexes_col
        doc = await bm25_indexes_col().find_one({"doc_id": doc_id})
        if doc and doc.get("data"):
            decompressed = zlib.decompress(doc["data"])
            data = pickle.loads(decompressed)
            # Rehydrate local cache
            try:
                with open(path, "wb") as f:
                    f.write(decompressed)
            except Exception:
                pass
            print(f"[BM25] Restored index for {doc_id} from MongoDB Atlas ({doc.get('chunk_count', 0)} chunks).")
            return data["index"]
    except Exception as e:
        print(f"[BM25] MongoDB restore notice for {doc_id}: {e}")

    return None


async def delete_bm25_index(doc_id: str):
    """Delete index from both local disk and MongoDB collection."""
    path = _bm25_path(doc_id)
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass
    try:
        from app.db.mongodb import bm25_indexes_col
        await bm25_indexes_col().delete_one({"doc_id": doc_id})
    except Exception:
        pass


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
