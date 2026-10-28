import os
import uuid
import aiofiles
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from bson import ObjectId

from app.core.security import get_current_user
from app.core.config import get_settings
from app.core.embeddings import delete_faiss_index
from app.db.mongodb import documents_col, chunks_col, users_col
from app.models.schemas import DocumentOut, DocumentList
try:
    from app.tasks import ingest_document_task  # Use Celery task instead
except Exception:
    ingest_document_task = None

router = APIRouter(prefix="/api/documents", tags=["documents"])
settings = get_settings()


def _uploads_dir(user_id: str) -> str:
    path = os.path.join(settings.storage_dir, "uploads", user_id)
    os.makedirs(path, exist_ok=True)
    return path


@router.post("/upload", response_model=DocumentOut, status_code=202)
async def upload_document(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    user_id: str = Depends(get_current_user)
):
    """
    Upload document for indexing (async).
    
    Returns 202 Accepted immediately. Document indexing happens in background Celery worker.
    Frontend should poll GET /api/documents/{id} to check status.
    
    Status progression:
      - processing → indexed (success)
      - processing → failed (error)
    """
    # ── Validate file type ───────────────────────────────────────────────────
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    # ── Check user limits ────────────────────────────────────────────────────
    user = await users_col().find_one({"_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    doc_count = await documents_col().count_documents({"user_id": user_id, "status": {"$ne": "error"}})
    if doc_count >= settings.max_docs:
        raise HTTPException(status_code=429, detail=f"Document limit reached ({settings.max_docs} docs on free plan).")

    if user.get("storage_used_mb", 0) >= settings.max_storage_mb:
        raise HTTPException(status_code=429, detail=f"Storage limit reached ({settings.max_storage_mb}MB on free plan).")

    # ── Save file to disk & upload to Cloudinary ─────────────────────────────
    doc_id = str(ObjectId())
    filename = f"{doc_id}_{file.filename}"
    file_path = os.path.join(_uploads_dir(user_id), filename)

    content = await file.read()
    size_mb = round(len(content) / (1024 * 1024), 2)

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    # Cloudinary Cloud Storage (Lifetime-free CDN hosting)
    cloudinary_url = None
    try:
        from app.core.storage_cloudinary import upload_pdf_to_cloudinary
        c_res = await asyncio.to_thread(upload_pdf_to_cloudinary, file_path, doc_id)
        if c_res:
            cloudinary_url = c_res.get("secure_url")
    except Exception as c_err:
        print(f"[Cloudinary Upload Notice] {c_err}")

    # ── Create DB record (status=processing) ─────────────────────────────────
    now = datetime.utcnow()
    await documents_col().insert_one({
        "_id": doc_id,
        "user_id": user_id,
        "filename": file.filename,
        "stored_filename": filename,
        "file_path": file_path,
        "file_url": cloudinary_url or file_path,
        "size_mb": size_mb,
        "page_count": 0,
        "status": "processing",
        "uploaded_at": now
    })

    # Update user storage usage
    await users_col().update_one(
        {"_id": user_id},
        {"$inc": {"storage_used_mb": size_mb}}
    )

    # ── Queue Task (Upstash Redis Queue, Celery, or FastAPI BackgroundTasks) ──
    import json
    from app.db.upstash import get_upstash_client
    upstash = get_upstash_client()
    enqueued_cloud = False

    if upstash.enabled:
        try:
            await upstash.push_event("nexus_ingest_queue", json.dumps({
                "doc_id": doc_id,
                "file_path": file_path,
                "filename": file.filename,
                "user_id": user_id
            }))
            print("[Upstash Queue] Enqueued PDF ingestion task to Upstash Redis Cloud.")
            enqueued_cloud = True
        except Exception as q_err:
            print(f"[Upstash Queue Warning] {q_err}")

    from app.celery_app import is_celery_worker_active
    if is_celery_worker_active() and ingest_document_task:
        try:
            ingest_document_task.delay(doc_id, file_path, user_id)
            print("[Celery] Successfully enqueued document ingestion task.")
        except Exception as celery_err:
            print(f"[Celery] Connection failed, falling back to BackgroundTasks: {celery_err}")
            if not enqueued_cloud:
                from app.ingestion.pipeline import ingest_document
                if background_tasks:
                    background_tasks.add_task(ingest_document, file_path, file.filename, doc_id, user_id)
    elif not enqueued_cloud:
        print("[In-Process Fallback] No external worker detected, running via FastAPI BackgroundTasks.")
        from app.ingestion.pipeline import ingest_document
        if background_tasks:
            background_tasks.add_task(ingest_document, file_path, file.filename, doc_id, user_id)

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

    # Delete file from disk
    if os.path.exists(doc.get("file_path", "")):
        os.remove(doc["file_path"])

    # Delete FAISS index
    delete_faiss_index(doc_id)

    # Delete from MongoDB
    await documents_col().delete_one({"_id": doc_id})
    await chunks_col().delete_many({"doc_id": doc_id})

    # Update user storage
    await users_col().update_one(
        {"_id": user_id},
        {"$inc": {"storage_used_mb": -doc.get("size_mb", 0)}}
    )
