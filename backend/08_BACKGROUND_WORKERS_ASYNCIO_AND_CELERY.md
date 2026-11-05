# 08. Background Workers: Asyncio Tasks vs. Celery

> *"In web architecture, never make a user wait for work they don't immediately need to see. Return an HTTP response in milliseconds, and offload heavy processing to background workers."*

---

## 1. The Three Tiers of Background Processing

When an operation takes more than 500ms (such as parsing a 200-page PDF, running an autonomous compliance audit, or sending Slack webhooks), running it synchronously inside the route handler will cause client timeouts.

FastAPI applications have three distinct patterns for background execution:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    BACKGROUND PROCESSING SPECTRUM                           │
├────────────────────┬──────────────────────┬─────────────────────────────────┤
│ Pattern            │ Operational Model    │ Ideal Use Case                  │
├────────────────────┼──────────────────────┼─────────────────────────────────┤
│ **`asyncio.create_task`** │ In-Process Non-Blocking Coroutine │ Fast async tasks (< 5s),   │
│                    │ (Zero extra infrastructure required)│ Watcher analysis, log writes│
├────────────────────┼──────────────────────┼─────────────────────────────────┤
│ **FastAPI `BackgroundTasks`** │ Post-Response Task Function │ Simple email sending,        │
│                    │ (Executes after HTTP socket closes)│ temp file deletion          │
├────────────────────┼──────────────────────┼─────────────────────────────────┤
│ **Distributed Celery** │ Out-of-Process Worker Cluster │ Heavy CPU jobs (OCR, heavy   │
│                    │ (Powered by Redis / RabbitMQ broker)│ crawling, batch ingestion)  │
└────────────────────┴──────────────────────┴─────────────────────────────────┘
```

---

## 2. In-Process Concurrency with `asyncio.create_task`

In [`rag-backend/app/ingestion/pipeline.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/ingestion/pipeline.py), when a clinician uploads a document, the system extracts the text, indexes the chunks in Qdrant, and returns `HTTP 201 Created` immediately.

The **Autonomous Compliance Watcher** is launched in the background without making the user wait:

```python
# rag-backend/app/ingestion/pipeline.py
import asyncio
from app.mcp.watcher import compliance_watcher

# Return response to client immediately!
# Launch watcher analysis as an independent background task on the event loop:
asyncio.create_task(
    compliance_watcher.analyze_document_async(
        document_id=doc_id,
        project_id=project_id,
        content=extracted_text
    )
)
```

### The Silent Exception Trap:
If an error occurs inside an `asyncio.create_task` that is not wrapped in `try/except`, Python's event loop will log an unhandled exception, but the caller will never know.
**Best Practice**: Always wrap background coroutines in a defensive `try/except` block with structured logging!

---

## 3. Distributed Background Workers with Celery (`rag-backend/app/celery_app.py`)

For multi-container deployments where heavy PDF OCR or multi-hour web crawls must be distributed across worker machines without consuming the API container's memory, we provide a complete **Celery + Redis** configuration:

### A. Celery App Factory (`rag-backend/app/celery_app.py`):
```python
# rag-backend/app/celery_app.py
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "veridoc_worker",
    broker=settings.redis_url,          # Redis Message Broker
    backend=settings.redis_url,         # Task Results Store
    include=["app.tasks"]               # Register Task Modules
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,               # Hard task kill after 1 hour
    task_soft_time_limit=3300           # Soft timeout to allow clean exit
)
```

### B. Defining Asynchronous Tasks (`rag-backend/app/tasks.py`):
```python
# rag-backend/app/tasks.py
from app.celery_app import celery_app
from app.ingestion.pipeline import process_pdf_full

@celery_app.task(bind=True, max_retries=3)
def process_pdf_task(self, file_path: str, project_id: str):
    """Distributed task for heavy document OCR and chunking."""
    try:
        result = process_pdf_full(file_path, project_id)
        return {"status": "SUCCESS", "chunks_indexed": result["count"]}
    except Exception as exc:
        # Retry with exponential backoff if worker encounters a temporary glitch
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
```

### C. Booting Dedicated Worker Processes (`rag-backend/app/worker.py`):
```bash
# In production, workers run in dedicated containers separate from the FastAPI web server:
celery -A app.celery_app worker --loglevel=info --concurrency=2
```

---

## 4. Architectural Decision: When to Choose Which?

1. **Use `asyncio.create_task`** when:
   - The task is I/O-bound (e.g., calling Groq API, sending a Slack webhook, saving a Mongo document).
   - You want zero infrastructure overhead (no Redis server required).
2. **Use Celery** when:
   - The task is heavily CPU-bound (e.g., OpenCV image preprocessing, Tesseract OCR, processing 1,000 files in parallel).
   - You need tasks to survive server restarts (tasks are persisted in Redis queue).
