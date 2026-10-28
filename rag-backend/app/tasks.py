"""
Celery tasks for background operations.
─────────────────────────────────────────────────────────────────────────────────
Decouples long-running operations from FastAPI event loop:
  - Document ingestion (PDF upload → extract → embed → index)
  - Web crawling (fetch pages → extract text → embed → index)
  - OCR processing (scanned pages → vision API → transcribe)
  - Cleanup tasks (stale records)

Each task:
  - Runs in isolated worker process
  - Can retry on failure
  - Tracks progress in MongoDB
  - Reports status back to API (polling from frontend)
"""
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

try:
    from celery import shared_task
    from app.celery_app import celery_app
except ImportError:
    def shared_task(*args, **kwargs):
        def decorator(f):
            f.delay = f
            return f
        return decorator
    class DummyCelery:
        def task(self, *args, **kwargs):
            def decorator(f):
                f.delay = f
                return f
            return decorator
    celery_app = DummyCelery()
from app.core.config import get_settings
from app.db.mongodb import (
    documents_col,
    chunks_col,
    projects_col,
    crawl_jobs_col,
)
from app.ingestion.pipeline import process_project_crawled_data, ingest_document

logger = logging.getLogger(__name__)
settings = get_settings()


# ──────────────────────────────────────────────────────────────────────────────
# Document Ingestion Tasks
# ──────────────────────────────────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    max_retries=2,
    soft_time_limit=1800,  # 30 min soft limit
    time_limit=3600,       # 60 min hard limit
)
def ingest_document_task(self, document_id: str, file_path: str, user_id: str):
    """
    Ingest a single document (PDF).
    """
    try:
        # Update status to "processing"
        asyncio.run(documents_col().update_one(
            {"_id": document_id},
            {
                "$set": {
                    "status": "processing",
                    "ingestion_started_at": datetime.utcnow(),
                }
            }
        ))

        logger.info(f"Starting ingestion: {document_id} ({file_path})")

        # Fetch document record to get the filename
        doc = asyncio.run(documents_col().find_one({"_id": document_id}))
        if not doc:
            raise ValueError(f"Document {document_id} not found in database.")
        filename = doc.get("filename", "Unknown")

        # Run synchronous ingestion
        asyncio.run(ingest_document(file_path, filename, document_id, user_id))

        # Update status to "indexed"
        asyncio.run(documents_col().update_one(
            {"_id": document_id},
            {
                "$set": {
                    "status": "indexed",
                    "ingestion_completed_at": datetime.utcnow(),
                }
            }
        ))

        logger.info(f"Completed ingestion: {document_id}")
        return {"status": "success", "document_id": document_id}

    except Exception as exc:
        logger.error(f"Ingestion failed: {document_id}, error: {exc}")

        # Update status to "failed"
        asyncio.run(documents_col().update_one(
            {"_id": document_id},
            {
                "$set": {
                    "status": "failed",
                    "error_message": str(exc),
                    "ingestion_failed_at": datetime.utcnow(),
                }
            }
        ))

        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

        return {"status": "failed", "document_id": document_id, "error": str(exc)}


@celery_app.task(
    bind=True,
    max_retries=2,
    soft_time_limit=1800,
    time_limit=3600,
)
def crawl_website_task(self, project_id: str, job_id: str, user_id: str):
    """
    Crawl a website recursively and ingest content.
    """
    try:
        from app.ingestion.crawler import crawl_website_task as run_crawler
        logger.info(f"Starting Celery crawl task: Project={project_id}, Job={job_id}")

        # Run crawler (which handles status updates and indexing internally)
        asyncio.run(run_crawler(project_id, job_id, user_id))

        logger.info(f"Completed Celery crawl task: Project={project_id}")
        return {"status": "success", "project_id": project_id, "job_id": job_id}

    except Exception as exc:
        logger.error(f"Celery crawl task failed: Project={project_id}, error: {exc}")

        # Update job status to failed if not already completed/paused
        asyncio.run(crawl_jobs_col().update_one(
            {"_id": job_id, "status": {"$in": ["pending", "running"]}},
            {
                "$set": {
                    "status": "failed",
                    "error_message": str(exc),
                    "completed_at": datetime.utcnow(),
                }
            }
        ))
        asyncio.run(projects_col().update_one(
            {"_id": project_id, "status": "crawling"},
            {"$set": {"status": "error"}}
        ))

        # Retry
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

        return {"status": "failed", "project_id": project_id, "error": str(exc)}


@celery_app.task(
    bind=True,
    max_retries=2,
    soft_time_limit=1800,
    time_limit=3600,
)
def process_project_crawled_data_task(self, project_id: str, user_id: str, force_recreate: bool = False):
    """
    Index crawled project pages.
    """
    try:
        logger.info(f"Starting Celery project indexing task: Project={project_id}")
        
        # Run indexing pipeline
        asyncio.run(process_project_crawled_data(project_id, user_id, force_recreate))

        logger.info(f"Completed Celery project indexing task: Project={project_id}")
        return {"status": "success", "project_id": project_id}

    except Exception as exc:
        logger.error(f"Celery project indexing task failed: Project={project_id}, error: {exc}")

        asyncio.run(projects_col().update_one(
            {"_id": project_id},
            {"$set": {"status": "error"}}
        ))

        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60)

        return {"status": "failed", "project_id": project_id, "error": str(exc)}


# ──────────────────────────────────────────────────────────────────────────────
# Cleanup Tasks
# ──────────────────────────────────────────────────────────────────────────────

@celery_app.task
def cleanup_stale_ingestions():
    """
    Daily cleanup: remove documents stuck in "processing" for > 2 hours.
    Scheduled daily via Beat.
    """
    try:
        from datetime import timedelta
        cutoff_time = datetime.utcnow() - timedelta(hours=2)

        result = asyncio.run(documents_col().delete_many({
            "status": "processing",
            "ingestion_started_at": {"$lt": cutoff_time}
        }))

        logger.info(f"Cleanup: removed {result.deleted_count} stale ingestions")
        return {"cleaned": result.deleted_count}

    except Exception as exc:
        logger.error(f"Cleanup failed: {exc}")
        return {"error": str(exc)}


# ──────────────────────────────────────────────────────────────────────────────
# Monitoring & Debug
# ──────────────────────────────────────────────────────────────────────────────

@celery_app.task
def check_ingestion_queue():
    """
    Debug task: count pending ingestions and queued tasks.
    """
    from app.celery_app import celery_app
    
    # Count pending documents
    pending_docs = asyncio.run(documents_col().count_documents({
        "status": "processing"
    }))

    # Get active tasks in worker
    inspect = celery_app.control.inspect()
    active_tasks = inspect.active()
    
    return {
        "pending_documents": pending_docs,
        "active_celery_tasks": len(active_tasks) if active_tasks else 0,
    }
