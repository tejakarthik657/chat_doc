import asyncio
import json
import logging
import os
import shutil
import tempfile
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from bson import ObjectId
from urllib.parse import parse_qs, urlparse

from app.core.security import get_current_user
from app.core.config import get_settings
from app.core.embeddings import delete_faiss_index
from app.core.bm25 import delete_bm25_index
from app.core.storage_cloudinary import upload_pdf_to_cloudinary, delete_pdf_from_cloudinary
from app.db.mongodb import documents_col, chunks_col, users_col
from app.db.upstash import get_upstash_client
from app.models.schemas import DocumentOut, DocumentList, TextCaptureRequest, YouTubeCaptureRequest

router = APIRouter(prefix="/api/documents", tags=["documents"])
settings = get_settings()
logger = logging.getLogger(__name__)


def _youtube_video_id(url: str) -> str:
    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower()
    video_id = ""
    if host in {"youtube.com", "www.youtube.com", "m.youtube.com", "youtube-nocookie.com", "www.youtube-nocookie.com"}:
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
        else:
            parts = [part for part in parsed.path.split("/") if part]
            if len(parts) == 2 and parts[0] in {"embed", "shorts", "live"}:
                video_id = parts[1]
    elif host in {"youtu.be", "www.youtu.be"}:
        video_id = parsed.path.strip("/").split("/")[0]

    if not video_id or len(video_id) != 11 or not all(char.isalnum() or char in "-_" for char in video_id):
        raise HTTPException(status_code=400, detail="Enter a valid YouTube video link.")
    return video_id


def _select_youtube_transcript(transcripts):
    available = list(transcripts)
    if not available:
        raise ValueError("No captions are available for this video.")
    return next(
        (
            item for item in available
            if item.language_code.lower().startswith("en")
        ),
        available[0],
    )


async def _create_text_source(
    title: str,
    content: str,
    user_id: str,
    background_tasks: BackgroundTasks,
    source_url: str | None = None,
) -> DocumentOut:
    title = title.strip()
    content = content.strip()
    if not title or not content:
        raise HTTPException(status_code=400, detail="A title and searchable content are required.")
    if len(title) > 200:
        raise HTTPException(status_code=400, detail="Source titles must be 200 characters or fewer.")
    if len(content) > 200000:
        raise HTTPException(status_code=413, detail="Captured text must be 200,000 characters or fewer.")

    user = await users_col().find_one({"_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    doc_count = await documents_col().count_documents(
        {"user_id": user_id, "status": {"$ne": "error"}}
    )
    if doc_count >= settings.max_docs:
        raise HTTPException(
            status_code=429,
            detail=f"Document limit reached ({settings.max_docs} docs on free plan).",
        )

    size_bytes = len(content.encode("utf-8"))
    size_mb = round(size_bytes / (1024 * 1024), 4)
    if user.get("storage_used_mb", 0) + size_mb > settings.max_storage_mb:
        raise HTTPException(
            status_code=429,
            detail=f"Storage limit reached ({settings.max_storage_mb}MB on free plan).",
        )

    doc_id = str(ObjectId())
    now = datetime.utcnow()
    await documents_col().insert_one({
        "_id": doc_id,
        "user_id": user_id,
        "filename": title,
        "source_url": source_url,
        "source_type": "youtube" if source_url else "text",
        "size_mb": size_mb,
        "page_count": 0,
        "status": "processing",
        "uploaded_at": now,
    })
    await users_col().update_one({"_id": user_id}, {"$inc": {"storage_used_mb": size_mb}})

    from app.ingestion.pipeline import ingest_text_document
    background_tasks.add_task(
        ingest_text_document,
        content,
        title,
        doc_id,
        user_id,
        source_url,
    )
    return DocumentOut(
        id=doc_id,
        filename=title,
        size_mb=size_mb,
        page_count=0,
        uploaded_at=now,
        status="processing",
    )


@router.post("/capture/text", response_model=DocumentOut, status_code=202)
async def capture_text(
    body: TextCaptureRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user),
):
    return await _create_text_source(body.title, body.content, user_id, background_tasks)


@router.post("/capture/youtube", response_model=DocumentOut, status_code=202)
async def capture_youtube(
    body: YouTubeCaptureRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user),
):
    video_id = _youtube_video_id(body.url)
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        transcript_list = await asyncio.to_thread(YouTubeTranscriptApi().list, video_id)
        transcript_source = _select_youtube_transcript(transcript_list)
        transcript = await asyncio.to_thread(transcript_source.fetch)
        content = " ".join(
            snippet.text for snippet in transcript.snippets if snippet.text.strip()
        ).strip()
    except Exception as exc:
        logger.exception("Could not retrieve YouTube captions for video %s", video_id)
        raise HTTPException(
            status_code=422,
            detail=(
                "We couldn't retrieve captions. The video may not have captions, or YouTube "
                "may be temporarily blocking access. Paste the transcript to capture it manually."
            ),
        ) from exc

    if not content:
        raise HTTPException(status_code=422, detail="This video has no usable captions to index.")

    title = f"YouTube video {video_id}"
    return await _create_text_source(
        title,
        content,
        user_id,
        background_tasks,
        source_url=body.url,
    )


@router.post("/upload", response_model=DocumentOut, status_code=202)
async def upload_document(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    user_id: str = Depends(get_current_user)
):
    """
    Upload document for indexing (async).
    Returns 202 Accepted immediately. Ingestion happens in background in <1s.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    user = await users_col().find_one({"_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    doc_count = await documents_col().count_documents({"user_id": user_id, "status": {"$ne": "error"}})
    if doc_count >= settings.max_docs:
        raise HTTPException(status_code=429, detail=f"Document limit reached ({settings.max_docs} docs on free plan).")

    if user.get("storage_used_mb", 0) >= settings.max_storage_mb:
        raise HTTPException(status_code=429, detail=f"Storage limit reached ({settings.max_storage_mb}MB on free plan).")

    # 1. Save file to local uploads directory and prepare DB record
    doc_id = str(ObjectId())
    stored_filename = f"{doc_id}_{file.filename}"
    upload_dir = os.path.join(settings.storage_dir, "uploads", user_id)
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, stored_filename)

    content = await file.read()
    size_bytes = len(content)
    size_mb = round(size_bytes / (1024 * 1024), 2)
    if size_bytes == 0:
        raise HTTPException(status_code=400, detail="The uploaded PDF is empty.")
    if size_bytes > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File is too large. Maximum size is {settings.max_upload_size_mb}MB."
        )

    # Write file to local disk for instant sub-second extraction
    with open(file_path, "wb") as f:
        f.write(content)

    now = datetime.utcnow()
    doc_data = {
        "_id": doc_id,
        "user_id": user_id,
        "filename": file.filename,
        "stored_filename": stored_filename,
        "file_path": file_path,
        "file_url": file_path,
        "size_mb": size_mb,
        "page_count": 0,
        "status": "processing",
        "uploaded_at": now
    }
    # Decoupled storage: Binary is stored in Cloudinary CDN; MongoDB stores metadata only to preserve M0 512MB quota
    await documents_col().insert_one(doc_data)

    # Update user storage usage
    await users_col().update_one(
        {"_id": user_id},
        {"$inc": {"storage_used_mb": size_mb}}
    )

    # Optional non-blocking Cloudinary CDN upload in background
    async def upload_cloudinary_bg():
        try:
            c_res = await asyncio.to_thread(upload_pdf_to_cloudinary, file_path, f"{user_id}/{doc_id}")
            if c_res and c_res.get("secure_url"):
                await documents_col().update_one(
                    {"_id": doc_id},
                    {"$set": {"storage_public_id": c_res.get("public_id"), "file_url": c_res.get("secure_url")}}
                )
        except Exception:
            pass

    asyncio.create_task(upload_cloudinary_bg())

    # ── Launch Ingestion Immediately in background (<1s execution) ───────────
    from app.ingestion.pipeline import ingest_document

    async def run_ingest():
        try:
            await ingest_document(file_path, file.filename, doc_id, user_id)
        except Exception as e:
            print(f"[Document Upload] Ingestion error: {e}")

    if background_tasks is not None:
        background_tasks.add_task(run_ingest)
    else:
        asyncio.create_task(run_ingest())

    return DocumentOut(
        id=doc_id,
        filename=file.filename,
        size_mb=size_mb,
        page_count=0,
        uploaded_at=now,
        status="processing",
        error_message=None
    )


@router.get("/", response_model=DocumentList)
async def list_documents(user_id: str = Depends(get_current_user)):
    docs = await documents_col().find(
        {"user_id": user_id},
        {"_id": 1, "filename": 1, "size_mb": 1, "page_count": 1, "uploaded_at": 1, "status": 1, "error_message": 1}
    ).to_list(length=50)
    user = await users_col().find_one({"_id": user_id}, {"storage_used_mb": 1})

    return DocumentList(
        documents=[
            DocumentOut(
                id=d["_id"],
                filename=d["filename"],
                size_mb=d["size_mb"],
                page_count=d.get("page_count", 0),
                uploaded_at=d["uploaded_at"],
                status=d.get("status", "unknown"),
                error_message=d.get("error_message")
            )
            for d in docs
        ],
        total_storage_mb=user.get("storage_used_mb", 0),
        storage_limit_mb=settings.max_storage_mb
    )


@router.get("/{doc_id}", response_model=DocumentOut)
async def get_document(doc_id: str, user_id: str = Depends(get_current_user)):
    doc = await documents_col().find_one({"_id": doc_id, "user_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    return DocumentOut(
        id=doc["_id"],
        filename=doc["filename"],
        size_mb=doc["size_mb"],
        page_count=doc.get("page_count", 0),
        uploaded_at=doc["uploaded_at"],
        status=doc.get("status", "unknown"),
        error_message=doc.get("error_message")
    )


@router.delete("/{doc_id}", status_code=204)
async def delete_document(doc_id: str, user_id: str = Depends(get_current_user)):
    doc = await documents_col().find_one({"_id": doc_id, "user_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Delete the durable PDF from object storage.
    delete_pdf_from_cloudinary(doc.get("storage_public_id", ""))
    # Remove legacy local files created before durable object storage was enabled.
    legacy_file_path = doc.get("file_path", "")
    if legacy_file_path and os.path.exists(legacy_file_path):
        os.remove(legacy_file_path)

    # Delete FAISS index
    delete_faiss_index(doc_id)
    await delete_bm25_index(doc_id)
    from app.db.qdrant import delete_collection
    delete_collection(f"project_{doc_id}")

    # Delete from MongoDB
    await documents_col().delete_one({"_id": doc_id})
    await chunks_col().delete_many({"doc_id": doc_id})

    # Update user storage
    await users_col().update_one(
        {"_id": user_id},
        {"$inc": {"storage_used_mb": -doc.get("size_mb", 0)}}
    )
