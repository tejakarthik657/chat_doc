import asyncio
import json
import os
import shutil
import tempfile
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from bson import ObjectId

from app.core.security import get_current_user
from app.core.config import get_settings
from app.core.embeddings import delete_faiss_index
from app.core.bm25 import delete_bm25_index
from app.core.storage_cloudinary import upload_pdf_to_cloudinary, delete_pdf_from_cloudinary
from app.db.mongodb import documents_col, chunks_col, users_col
from app.db.upstash import get_upstash_client
from app.models.schemas import DocumentOut, DocumentList

router = APIRouter(prefix="/api/documents", tags=["documents"])
settings = get_settings()


@router.post("/upload", response_model=DocumentOut, status_code=202)
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user)
):
    """
    Upload document for indexing (async).
    
    Returns 202 Accepted immediately. Document indexing happens in background.
    Frontend polls GET /api/documents/{id} to check status.
    
    Status progression:
      - processing → ready (success in <2 seconds)
      - processing → error (failure)
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

    # ── Upload to durable object storage ─────────────────────────────────────
    doc_id = str(ObjectId())
    stored_filename = f"{doc_id}_{file.filename}"
    temp_path = ""
    cloudinary_file = None
    try:
        with tempfile.NamedTemporaryFile(prefix=f"{doc_id}_", suffix=".pdf", delete=False) as temp_file:
            temp_path = temp_file.name
            shutil.copyfileobj(file.file, temp_file)

        size_bytes = os.path.getsize(temp_path)
        size_mb = round(size_bytes / (1024 * 1024), 2)
        if size_bytes == 0:
            raise HTTPException(status_code=400, detail="The uploaded PDF is empty.")
        if size_bytes > settings.max_upload_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File is too large. Maximum size is {settings.max_upload_size_mb}MB."
            )

        cloudinary_file = await asyncio.to_thread(
            upload_pdf_to_cloudinary,
            temp_path,
            f"{user_id}/{doc_id}"
        )
        if not cloudinary_file:
            raise HTTPException(
                status_code=503,
                detail="Document storage is unavailable. Please try again."
            )
    except HTTPException:
        raise
    except Exception as upload_error:
        raise HTTPException(status_code=503, detail=f"Could not store document: {upload_error}")
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

    # ── Create DB record (metadata only; never store raw PDF bytes) ───────────
    now = datetime.utcnow()
    doc_data = {
        "_id": doc_id,
        "user_id": user_id,
        "filename": file.filename,
        "stored_filename": stored_filename,
        "file_url": cloudinary_file["secure_url"],
        "storage_provider": "cloudinary",
        "storage_public_id": cloudinary_file["public_id"],
        "size_mb": size_mb,
        "page_count": 0,
        "status": "processing",
        "uploaded_at": now
    }
    try:
        await documents_col().insert_one(doc_data)
    except Exception:
        await asyncio.to_thread(delete_pdf_from_cloudinary, cloudinary_file["public_id"])
        raise

    # Update user storage usage
    await users_col().update_one(
        {"_id": user_id},
        {"$inc": {"storage_used_mb": size_mb}}
    )

    # ── Queue ingestion; use in-process fallback if the queue is unavailable ──
    from app.ingestion.pipeline import ingest_document
    queue_payload = json.dumps({
        "doc_id": doc_id,
        "filename": file.filename,
        "user_id": user_id,
    })
    queued = False
    try:
        queued = await get_upstash_client().push_event("nexus_ingest_queue", queue_payload)
    except Exception as queue_error:
        print(f"[Document Upload] Queue unavailable, using local fallback: {queue_error}")

    # Always start a web-process fallback as well. The atomic claim inside
    # ingest_document prevents duplicate work when the queue worker receives
    # the same document first, and prevents documents from hanging forever if
    # the separate Render worker is unavailable.
    async def run_ingestion_with_timeout():
        try:
            await asyncio.wait_for(
                ingest_document("", file.filename, doc_id, user_id),
                timeout=300,
            )
        except asyncio.TimeoutError:
            await documents_col().update_one(
                {"_id": doc_id, "status": "processing"},
                {
                    "$set": {
                        "status": "error",
                        "error_message": "Document processing timed out after 5 minutes. Please retry the upload.",
                    }
                },
            )
            print(f"[Document Upload] Background indexing timed out for {doc_id}")
        except Exception as ingestion_error:
            print(f"[Document Upload] Background indexing failed for {doc_id}: {ingestion_error}")

    task = asyncio.create_task(run_ingestion_with_timeout())
    task.add_done_callback(
        lambda completed_task: print(
            f"[Document Upload] Background indexing supervisor failed for {doc_id}: {completed_task.exception()}"
        ) if not completed_task.cancelled() and completed_task.exception() else None
    )

    print(
        f"[Document Upload] Scheduled durable background indexing for "
        f"{file.filename} ({doc_id}); queue_enqueued={queued}"
    )

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
    delete_bm25_index(doc_id)
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
