import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock
from app.main import app


# ── Image analysis tests ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_analyze_image_sends_image_to_vision_model():
    from app.core.security import get_current_user

    mock_client = MagicMock()
    mock_client.chat_completion.return_value = "## Overview\nA screenshot of a coding exercise."
    app.dependency_overrides[get_current_user] = lambda: "test-user"

    try:
        with patch("app.core.llm_groq._get_or_init_groq_client", return_value=mock_client):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/api/features/analyze-image",
                    files={"file": ("screen.png", b"image-bytes", "image/png")},
                    data={"prompt": "What can you see?"},
                )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 200
    assert response.json()["description"] == "## Overview\nA screenshot of a coding exercise."
    messages = mock_client.chat_completion.call_args.kwargs["messages"]
    user_content = messages[1]["content"]
    assert user_content[0]["text"].endswith("Question: What can you see?")
    assert user_content[1]["type"] == "image_url"
    assert user_content[1]["image_url"]["url"].startswith("data:image/png;base64,")
    assert mock_client.chat_completion.call_args.kwargs["model"] == "qwen/qwen3.8-27b"
    assert mock_client.chat_completion.call_args.kwargs["max_tokens"] == 1800


@pytest.mark.asyncio
async def test_analyze_image_returns_clear_error_when_vision_service_is_unavailable():
    from app.core.security import get_current_user

    app.dependency_overrides[get_current_user] = lambda: "test-user"
    try:
        with patch("app.core.llm_groq._get_or_init_groq_client", return_value=None):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/api/features/analyze-image",
                    files={"file": ("screen.png", b"image-bytes", "image/png")},
                )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 503
    assert "no vision service is configured" in response.json()["detail"]


@pytest.mark.asyncio
async def test_analyze_image_reports_vision_provider_failure():
    from app.core.security import get_current_user

    mock_client = MagicMock()
    mock_client.chat_completion.side_effect = RuntimeError("provider unavailable")
    app.dependency_overrides[get_current_user] = lambda: "test-user"
    try:
        with patch("app.core.llm_groq._get_or_init_groq_client", return_value=mock_client):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/api/features/analyze-image",
                    files={"file": ("screen.png", b"image-bytes", "image/png")},
                )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 502
    assert "vision service could not analyze" in response.json()["detail"]


@pytest.mark.asyncio
async def test_transcribe_rejects_audio_above_configured_limit():
    from app.core.security import get_current_user

    app.dependency_overrides[get_current_user] = lambda: "test-user"
    try:
        with patch("app.api.routes.features.MAX_AUDIO_UPLOAD_BYTES", 3):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    "/api/features/transcribe",
                    files={"file": ("sample.wav", b"four", "audio/wav")},
                )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 413
    assert "25 MB or smaller" in response.json()["detail"]


# ── Universal capture tests ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_capture_text_creates_searchable_document_and_schedules_indexing():
    from fastapi import BackgroundTasks
    from app.api.routes.documents import capture_text
    from app.models.schemas import TextCaptureRequest

    documents = MagicMock()
    documents.count_documents = AsyncMock(return_value=0)
    documents.insert_one = AsyncMock()
    users = MagicMock()
    users.find_one = AsyncMock(return_value={"_id": "test-user", "storage_used_mb": 0})
    users.update_one = AsyncMock()
    background_tasks = BackgroundTasks()

    with patch("app.api.routes.documents.documents_col", return_value=documents), \
         patch("app.api.routes.documents.users_col", return_value=users):
        response = await capture_text(
            TextCaptureRequest(title="  Notes  ", content="  A short note to save.  "),
            background_tasks,
            "test-user",
        )

    assert response.status == "processing"
    assert response.filename == "Notes"
    assert documents.insert_one.await_args.args[0]["source_type"] == "text"
    assert users.update_one.await_args.args[1]["$inc"]["storage_used_mb"] >= 0
    assert len(background_tasks.tasks) == 1
    assert background_tasks.tasks[0].args[0] == "A short note to save."


@pytest.mark.parametrize(
    ("url", "expected_id"),
    [
        ("https://www.youtube.com/watch?v=abcdefghijk", "abcdefghijk"),
        ("https://youtu.be/abcdefghijk?t=30", "abcdefghijk"),
        ("https://youtube.com/shorts/abcdefghijk", "abcdefghijk"),
        ("https://youtube.com/embed/abcdefghijk", "abcdefghijk"),
    ],
)
def test_youtube_capture_extracts_supported_video_ids(url, expected_id):
    from app.api.routes.documents import _youtube_video_id

    assert _youtube_video_id(url) == expected_id


def test_youtube_capture_rejects_non_video_or_untrusted_urls():
    from fastapi import HTTPException
    from app.api.routes.documents import _youtube_video_id

    with pytest.raises(HTTPException) as error:
        _youtube_video_id("https://example.com/watch?v=abcdefghijk")
    assert error.value.status_code == 400


@pytest.mark.asyncio
async def test_youtube_capture_saves_transcript_as_a_searchable_document():
    from fastapi import BackgroundTasks
    from types import SimpleNamespace
    from app.api.routes.documents import capture_youtube
    from app.models.schemas import YouTubeCaptureRequest

    documents = MagicMock()
    documents.count_documents = AsyncMock(return_value=0)
    documents.insert_one = AsyncMock()
    users = MagicMock()
    users.find_one = AsyncMock(return_value={"_id": "test-user", "storage_used_mb": 0})
    users.update_one = AsyncMock()
    transcript_api = MagicMock()
    transcript_api.fetch.return_value = SimpleNamespace(
        snippets=[SimpleNamespace(text="First caption."), SimpleNamespace(text="Second caption.")]
    )
    background_tasks = BackgroundTasks()

    with patch("youtube_transcript_api.YouTubeTranscriptApi", return_value=transcript_api), \
         patch("app.api.routes.documents.documents_col", return_value=documents), \
         patch("app.api.routes.documents.users_col", return_value=users):
        response = await capture_youtube(
            YouTubeCaptureRequest(url="https://youtu.be/abcdefghijk"),
            background_tasks,
            "test-user",
        )

    assert response.status == "processing"
    assert response.filename == "YouTube video abcdefghijk"
    transcript_api.fetch.assert_called_once_with("abcdefghijk", languages=["en"])
    assert documents.insert_one.await_args.args[0]["source_url"] == "https://youtu.be/abcdefghijk"
    assert background_tasks.tasks[0].args[0] == "First caption. Second caption."


@pytest.mark.asyncio
async def test_text_ingestion_indexes_short_notes_and_marks_document_ready():
    from app.ingestion.pipeline import ingest_text_document

    documents = MagicMock()
    documents.find_one_and_update = AsyncMock(return_value={"_id": "short-note"})
    documents.update_one = AsyncMock()
    chunks = MagicMock()
    chunks.insert_many = AsyncMock()

    with patch("app.ingestion.pipeline.documents_col", return_value=documents), \
         patch("app.ingestion.pipeline.chunks_col", return_value=chunks), \
         patch("app.ingestion.pipeline.build_index", new=AsyncMock()):
        result = await ingest_text_document(
            "Short note.",
            "Note",
            "short-note",
            "test-user",
        )

    assert result["status"] == "ready"
    assert result["chunks"] == 1
    assert chunks.insert_many.await_args.args[0][0]["text"] == "Short note."
    assert documents.update_one.await_args.args[1]["$set"]["status"] == "ready"


def test_text_chunking_keeps_short_pasted_notes():
    from app.ingestion.pipeline import chunk_pages

    chunks = chunk_pages(
        [{"page": 1, "text": "Short note."}],
        "short-note-id",
        "Short note",
        min_chunk_length=1,
    )

    assert len(chunks) == 1
    assert chunks[0]["text"] == "Short note."


# ── Auth tests ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_check():
    with patch("app.db.mongodb.get_client") as mock_get_client, \
         patch("app.db.qdrant.check_qdrant_health", return_value=True):
        mock_client = MagicMock()
        mock_client.admin.command = AsyncMock()
        mock_get_client.return_value = mock_client

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_health_ready():
    with patch("app.db.mongodb.get_client") as mock_get_client, \
         patch("app.db.qdrant.check_qdrant_health", return_value=True):
        mock_client = MagicMock()
        mock_client.admin.command = AsyncMock()
        mock_get_client.return_value = mock_client

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["checks"]["mongodb"] == "ok"
    assert data["checks"]["qdrant"] == "ok"


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
    assert "Page 3" in context
    assert "Page 4" in context


# ── Analytics tests ───────────────────────────────────────────────────────────

def test_auto_label_cluster():
    from app.analytics.engine import _auto_label_cluster
    questions = ["What is the treatment?", "What medication should I take?", "What is the drug dosage?"]
    label = _auto_label_cluster(questions)
    assert label in ["treatment", "dosage"]


# ── Ingestion error handling tests ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_process_project_crawled_data_with_empty_pdf():
    from app.ingestion.pipeline import process_project_crawled_data
    
    mock_pages = [
        {
            "_id": "mock_page_id",
            "project_id": "test_proj",
            "url": "http://example.com/empty.pdf",
            "page_type": "pdf",
            "file_path": "dummy_path.pdf",
            "title": "Empty PDF"
        }
    ]
    
    # Mocking MongoDB collections
    mock_find_res = MagicMock()
    mock_find_res.to_list = AsyncMock(return_value=mock_pages)
    
    mock_crawled_pages = MagicMock()
    mock_crawled_pages.find.return_value = mock_find_res
    mock_crawled_pages.update_one = AsyncMock()
    
    mock_projects = MagicMock()
    mock_projects.update_one = AsyncMock()
    mock_projects.find_one = AsyncMock(return_value={"name": "Test Project"})
    
    with patch("app.ingestion.pipeline.crawled_pages_col", return_value=mock_crawled_pages), \
         patch("app.ingestion.pipeline.projects_col", return_value=mock_projects), \
         patch("app.ingestion.pipeline.extract_pages_with_docling", return_value=[]), \
         patch("app.ingestion.pipeline.extract_pages_with_ocr", return_value=[]), \
         patch("os.path.exists", return_value=True):
         
         # Execute
         await process_project_crawled_data("test_proj", "test_user")
         
         # Verify update_one was called to mark the page with "error" status
         mock_crawled_pages.update_one.assert_called_once()
         call_args = mock_crawled_pages.update_one.call_args[0]
         assert call_args[0] == {"_id": "mock_page_id"}
         update_fields = call_args[1]["$set"]
         assert update_fields["status"] == "error"
         assert "No extractable text found in PDF" in update_fields["error_message"]
         
         # Verify project status updated to active since no chunks were created
         mock_projects.update_one.assert_called_once_with(
             {"_id": "test_proj"},
             {"$set": {"status": "active"}}
         )


def test_parse_sitemap_urls():
    from app.ingestion.crawler import parse_sitemap_urls
    xml = """
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url>
            <loc>https://example.com/page1</loc>
            <lastmod>2026-06-21</lastmod>
        </url>
        <url>
            <loc>https://example.com/page2</loc>
        </url>
    </urlset>
    """
    urls = parse_sitemap_urls(xml)
    assert "https://example.com/page1" in urls
    assert "https://example.com/page2" in urls


def test_crawler_domain_helpers():
    from app.ingestion.crawler import get_domain, is_same_domain
    assert get_domain("https://sub.kitsw.ac.in/path") == "sub.kitsw.ac.in"
    assert is_same_domain("https://sub.kitsw.ac.in/path", "kitsw.ac.in") is True
    assert is_same_domain("https://google.com/path", "kitsw.ac.in") is False


# ── Fallback & health connectivity tests ─────────────────────────────────────

@pytest.mark.asyncio
async def test_health_check_db_integration():
    """Test health check with mocked DB success."""
    with patch("app.db.mongodb.get_client") as mock_get_client, \
         patch("app.db.qdrant.check_qdrant_health", return_value=True):
        mock_client = MagicMock()
        mock_client.admin.command = AsyncMock()
        mock_get_client.return_value = mock_client

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_health_check_db_failure():
    """Test health check with database failure (should return 503)."""
    with patch("app.db.mongodb.get_client") as mock_get_client, \
         patch("app.db.qdrant.check_qdrant_health", return_value=False):
        mock_client = MagicMock()
        mock_client.admin.command = AsyncMock(side_effect=Exception("Connection refused"))
        mock_get_client.return_value = mock_client

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health/ready")
        assert response.status_code == 503
        assert response.json()["status"] == "degraded"


def test_crag_local_fallback():
    """Test CRAG grading falls back to local LLM on missing key."""
    from app.rag.crag import grade_chunk_relevance
    from app.core.config import get_settings
    
    settings = get_settings()
    with patch.object(settings, "groq_api_key", None), \
         patch("app.rag.crag._grade_chunk_relevance_local") as mock_local:
        mock_local.return_value = {"relevance": "high", "reason": "local mock response"}
        res = grade_chunk_relevance("test question", "test chunk content")
        assert res["relevance"] == "high"
        mock_local.assert_called_once_with("test question", "test chunk content")


def test_contextual_local_fallback():
    """Test contextual description batching falls back to local LLM on missing key."""
    from app.rag.contextual import generate_context_batch
    from app.core.config import get_settings
    
    settings = get_settings()
    with patch.object(settings, "groq_api_key", None), \
         patch("app.rag.contextual._generate_context_batch_local") as mock_local:
        mock_local.return_value = ["mock description"]
        res = generate_context_batch("source.pdf", ["chunk text"])
        assert res == ["mock description"]
        mock_local.assert_called_once_with("source.pdf", ["chunk text"])


def test_crag_batch_grading():
    """Test CRAG batch grading with mocked Groq client."""
    from app.rag.crag import grade_chunks_relevance_batch
    from app.core.config import get_settings
    
    settings = get_settings()
    
    mock_choices = [
        MagicMock(
            message=MagicMock(
                content='{"results": [{"index": 0, "relevance": "high", "reason": "direct answer"}, {"index": 1, "relevance": "low", "reason": "irrelevant"}]}'
            )
        )
    ]
    mock_response = MagicMock(choices=mock_choices)
    
    with patch.object(settings, "groq_api_key", "test_key"), \
         patch("app.rag.crag.Groq") as mock_groq:
        
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq.return_value = mock_client
        
        excerpts = ["excerpt 1 content", "excerpt 2 content"]
        res = grade_chunks_relevance_batch("test question", excerpts)
        
        assert len(res) == 2
        assert res[0]["relevance"] == "high"
        assert res[0]["reason"] == "direct answer"
        assert res[1]["relevance"] == "low"
        assert res[1]["reason"] == "irrelevant"


def test_crag_batch_local_fallback():
    """Test CRAG batch grading falls back to local when Groq key is absent."""
    from app.rag.crag import grade_chunks_relevance_batch
    from app.core.config import get_settings
    
    settings = get_settings()
    
    with patch.object(settings, "groq_api_key", None), \
         patch("app.rag.crag._grade_chunks_relevance_local_batch") as mock_local_batch:
        
        mock_local_batch.return_value = [
            {"relevance": "high", "reason": "local 1"},
            {"relevance": "medium", "reason": "local 2"}
        ]
        
        excerpts = ["chunk 1", "chunk 2"]
        res = grade_chunks_relevance_batch("test question", excerpts)
        
        assert len(res) == 2
        assert res[0]["relevance"] == "high"
        assert res[1]["relevance"] == "medium"
        mock_local_batch.assert_called_once_with("test question", excerpts)
