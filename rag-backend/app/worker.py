"""
NEXUS AI Standalone Cloud Background Worker.
──────────────────────────────────────────────────────────────────────────────
Consumes crawling, PDF chunking, and knowledge graph jobs from Upstash Redis Cloud.
Runs in a dedicated OS process isolated from FastAPI, guaranteeing zero-latency
API responses (<15ms) for auth, chat, and dashboard queries.

Usage:
    python -m app.worker
"""
import os
import sys
import json
import time
import asyncio
import logging
import signal

# Ensure current working directory is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import get_settings
from app.db.upstash import get_upstash_client
from app.db.mongodb import get_client, create_indexes, documents_col

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [NEXUS WORKER] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("nexus_worker")
settings = get_settings()

_running = True


def handle_shutdown(signum, frame):
    global _running
    logger.info("Shutdown signal received. Finishing active jobs...")
    _running = False


async def run_worker():
    global _running
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    logger.info("=" * 65)
    logger.info("NEXUS AI Autonomous Ingestion Worker Initialized")
    logger.info(f"Connected to Upstash Redis Broker: {settings.upstash_redis_rest_url}")
    logger.info("=" * 65)

    # Verify DB connectivity
    await create_indexes()
    upstash = get_upstash_client()

    if not upstash.enabled:
        logger.error("Upstash Redis not configured. Set UPSTASH_REDIS_REST_URL & TOKEN.")
        return

    logger.info("Worker listening on queues: ['nexus_crawl_queue', 'nexus_ingest_queue']...")

    backoff = 2.5

    while _running:
        try:
            # 1. Check Crawl Queue
            raw_crawl = await upstash.pop_event("nexus_crawl_queue")
            if raw_crawl:
                backoff = 0.2  # Drain queue fast when items exist
                try:
                    payload = json.loads(raw_crawl) if isinstance(raw_crawl, str) else raw_crawl
                    project_id = payload.get("project_id")
                    job_id = payload.get("job_id")
                    user_id = payload.get("user_id")
                    logger.info(f"[JOB STARTED] Web Crawl for Project={project_id}, Job={job_id}")

                    from app.ingestion.crawler import crawl_website_task
                    await crawl_website_task(project_id, job_id, user_id)
                    logger.info(f"[JOB COMPLETED] Web Crawl for Project={project_id}")
                except Exception as crawl_err:
                    logger.error(f"[JOB ERROR] Crawl task failed: {crawl_err}", exc_info=True)
                continue

            # 2. Check Document Ingestion Queue (only if upstash had no connection errors on crawl queue)
            if upstash._consecutive_errors == 0:
                raw_ingest = await upstash.pop_event("nexus_ingest_queue")
                if raw_ingest:
                    backoff = 0.2  # Drain queue fast when items exist
                    try:
                        payload = json.loads(raw_ingest) if isinstance(raw_ingest, str) else raw_ingest
                        doc_id = payload.get("doc_id")
                        file_path = payload.get("file_path", "")
                        filename = payload.get("filename")
                        user_id = payload.get("user_id")
                        logger.info(f"[JOB STARTED] Document Ingestion for Doc={doc_id} ({filename})")

                        from app.ingestion.pipeline import ingest_document
                        try:
                            await asyncio.wait_for(
                                ingest_document(file_path, filename, doc_id, user_id),
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
                            logger.error(f"[JOB TIMEOUT] Document ingestion timed out for Doc={doc_id}")
                        logger.info(f"[JOB COMPLETED] Document Ingestion for Doc={doc_id}")
                    except Exception as ingest_err:
                        logger.error(f"[JOB ERROR] Ingestion task failed: {ingest_err}", exc_info=True)
                    continue

            # Adaptive polling interval:
            # If network/Upstash errors are occurring, back off exponentially up to 15s
            if upstash._consecutive_errors > 0:
                backoff = min(max(backoff * 1.5, 4.0), 15.0)
            else:
                # Normal idle polling: 3.0s keeps latency low while conserving socket & API limits
                backoff = 3.0

            await asyncio.sleep(backoff)

        except Exception as loop_err:
            logger.error(f"Worker main loop error: {loop_err}")
            await asyncio.sleep(4.0)

    try:
        await upstash.aclose()
    except Exception:
        pass
    logger.info("Worker process exited gracefully.")


if __name__ == "__main__":
    asyncio.run(run_worker())
