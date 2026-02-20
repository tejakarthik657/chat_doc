"""
Tests for the RAG backend.
Run: pytest tests/ -v
"""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock
from app.main import app


# ── Auth tests ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# ── Ingestion tests ───────────────────────────────────────────────────────────

def test_chunking_preserves_page_numbers():
    from app.ingestion.pipeline import chunk_pages
    pages = [
        {"page": 1, "text": "This is page one content. " * 50},
        {"page": 2, "text": "This is page two content. " * 50},
    ]
    chunks = chunk_pages(pages, "test_doc_id", "test.pdf")
    assert len(chunks) > 0
    page_nums = {c["page"] for c in chunks}
    assert 1 in page_nums
    assert 2 in page_nums


def test_chunking_assigns_sequential_embedding_ids():
    from app.ingestion.pipeline import chunk_pages
    pages = [{"page": i, "text": "Content " * 100} for i in range(1, 4)]
    chunks = chunk_pages(pages, "test_doc_id", "test.pdf")
    embedding_ids = [c["embedding_id"] for c in chunks]
    assert embedding_ids == list(range(len(chunks)))


# ── BM25 tests ────────────────────────────────────────────────────────────────

def test_bm25_tokenizer():
    from app.core.bm25 import _tokenize
    tokens = _tokenize("What is the recommended dosage of metformin?")
    assert "metformin" in tokens
    assert "dosage" in tokens
    assert "what" not in tokens   # stop word removed
    assert "the" not in tokens    # stop word removed


def test_bm25_search_returns_ranked_results():
    from rank_bm25 import BM25Okapi
    from app.core.bm25 import _tokenize, bm25_search

    # Mock a small BM25 index
    corpus_texts = [
        "metformin 500mg twice daily with meals",
        "blood pressure monitoring weekly",
        "ACE inhibitors for hypertension treatment"
    ]
    corpus = [_tokenize(t) for t in corpus_texts]
    index = BM25Okapi(corpus)

    results = bm25_search(index, "metformin dosage", top_k=3)
    assert len(results) > 0
    # Top result should be chunk 0 (metformin content)
    top_id, top_score = results[0]
    assert top_id == 0
    assert 0.0 < top_score <= 1.0


# ── RRF Fusion tests ──────────────────────────────────────────────────────────

def test_rrf_fusion_combines_results():
    from app.core.fusion import reciprocal_rank_fusion

    faiss_results = [(0, 0.95), (1, 0.80), (3, 0.60)]
    bm25_results  = [(2, 1.00), (0, 0.85), (1, 0.70)]

    fused = reciprocal_rank_fusion(faiss_results, bm25_results, top_k=5)
    fused_ids = [emb_id for emb_id, _ in fused]

    # ID 0 appears in both lists → should rank highly
    assert fused_ids[0] == 0

    # All IDs should be present
    assert set(fused_ids) == {0, 1, 2, 3}


def test_rrf_bm25_only_result_included():
    from app.core.fusion import reciprocal_rank_fusion

    faiss_results = [(0, 0.9), (1, 0.7)]
    bm25_results  = [(5, 1.0)]  # chunk 5 only found by BM25

    fused = reciprocal_rank_fusion(faiss_results, bm25_results, top_k=5)
    fused_ids = [emb_id for emb_id, _ in fused]
    assert 5 in fused_ids   # BM25-only result should be included


# ── HyDE tests ────────────────────────────────────────────────────────────────

def test_hyde_triggers_on_short_questions():
    from app.rag.hyde import should_use_hyde
    assert should_use_hyde("What is the dose?") is True
    assert should_use_hyde("What?") is True


def test_hyde_skips_long_keyword_rich_questions():
    from app.rag.hyde import should_use_hyde
    long_q = "According to section 3, what are the contraindications for patients with renal impairment taking metformin?"
    assert should_use_hyde(long_q) is False


# ── RAG Engine tests ──────────────────────────────────────────────────────────

def test_build_context_string():
    from app.rag.engine import build_context_string
    chunks = [
        {"page": 3, "text": "ACE inhibitors reduce blood pressure.", "chunk_id": "x"},
        {"page": 4, "text": "Lifestyle changes include diet and exercise.", "chunk_id": "y"},
    ]
    ranked = [(c, 0.9) for c in chunks]
    context = build_context_string(ranked)
    assert "[Page 3]" in context
    assert "[Page 4]" in context
    assert "---" in context  # separator between chunks


# ── Analytics tests ───────────────────────────────────────────────────────────

def test_auto_label_cluster():
    from app.analytics.engine import _auto_label_cluster
    questions = ["What is the treatment?", "What medication should I take?", "What is the drug dosage?"]
    label = _auto_label_cluster(questions)
    assert label in ["treatment", "dosage"]

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock
from app.main import app


# ── Auth tests ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_register_and_login():
    """Test user registration and login flow."""
    mock_user = None

    async def mock_find_one(filter):
        return mock_user

    async def mock_insert_one(doc):
        nonlocal mock_user
        mock_user = doc
        return MagicMock(inserted_id=doc["_id"])

    async def mock_update_one(*args, **kwargs):
        return MagicMock()

    with patch("app.api.routes.auth.users_col") as mock_col:
        mock_col.return_value.find_one = mock_find_one
        mock_col.return_value.insert_one = mock_insert_one
        mock_col.return_value.update_one = mock_update_one

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Register
            r = await client.post("/api/auth/register", json={
                "email": "test@example.com",
                "password": "password123"
            })
            assert r.status_code == 201
            assert "access_token" in r.json()


# ── Ingestion tests ───────────────────────────────────────────────────────────

def test_chunking_preserves_page_numbers():
    from app.ingestion.pipeline import chunk_pages
    pages = [
        {"page": 1, "text": "This is page one content. " * 50},
        {"page": 2, "text": "This is page two content. " * 50},
    ]
    chunks = chunk_pages(pages, "test_doc_id", "test.pdf")
    assert len(chunks) > 0
    page_nums = {c["page"] for c in chunks}
    assert 1 in page_nums
    assert 2 in page_nums


def test_chunking_assigns_sequential_embedding_ids():
    from app.ingestion.pipeline import chunk_pages
    pages = [{"page": i, "text": "Content " * 100} for i in range(1, 4)]
    chunks = chunk_pages(pages, "test_doc_id", "test.pdf")
    embedding_ids = [c["embedding_id"] for c in chunks]
    assert embedding_ids == list(range(len(chunks)))


# ── RAG engine tests ──────────────────────────────────────────────────────────

def test_deduplicate_chunks():
    from app.rag.engine import deduplicate_chunks
    chunks = [
        {"page": 1, "text": "First chunk on page 1", "chunk_id": "a"},
        {"page": 1, "text": "Second chunk on page 1", "chunk_id": "b"},  # duplicate page
        {"page": 2, "text": "Chunk on page 2", "chunk_id": "c"},
    ]
    scores = [0.9, 0.7, 0.8]
    ranked = deduplicate_chunks(chunks, scores)
    # Should keep only the highest scoring chunk per page
    pages = [r[0]["page"] for r in ranked]
    assert len(set(pages)) == len(pages)  # no duplicate pages


def test_build_context_string():
    from app.rag.engine import build_context_string
    chunks = [
        {"page": 3, "text": "ACE inhibitors reduce blood pressure.", "chunk_id": "x"},
        {"page": 4, "text": "Lifestyle changes include diet and exercise.", "chunk_id": "y"},
    ]
    ranked = [(c, 0.9) for c in chunks]
    context = build_context_string(ranked)
    assert "[Page 3]" in context
    assert "[Page 4]" in context


# ── Analytics tests ───────────────────────────────────────────────────────────

def test_auto_label_cluster():
    from app.analytics.engine import _auto_label_cluster
    questions = ["What is the treatment?", "What medication should I take?", "What is the drug dosage?"]
    label = _auto_label_cluster(questions)
    assert label in ["treatment", "dosage"]
