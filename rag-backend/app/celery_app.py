"""
Celery configuration and app initialization.
Decouples background tasks (crawling, indexing, OCR) from FastAPI event loop.
"""
import os
from celery import Celery
from celery.schedules import crontab

# Get settings
from app.core.config import get_settings

settings = get_settings()

# ────────────────────────────────────────────────────────────────────────
# Celery App
# ──────────────────────────────────────────────────────────────────────────────

celery_app = Celery(
    "rag_backend",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────

celery_app.conf.update(
    # ─ Task Configuration
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # ─ Performance Tuning
    worker_prefetch_multiplier=1,      # Fetch 1 task at a time (fair scheduling)
    worker_max_tasks_per_child=100,    # Restart worker after 100 tasks (memory leak prevention)
    task_soft_time_limit=1800,         # 30 min soft limit (graceful shutdown)
    task_time_limit=3600,              # 60 min hard limit (kill task)

    # ─ Retry Policy
    task_autoretry_for=(Exception,),
    task_max_retries=3,
    task_default_retry_delay=60,       # 1 minute between retries

    # ─ Beat Scheduler (periodic tasks)
    beat_scheduler="celery.beat:PersistentScheduler",
    beat_schedule={
        # Example: cleanup stale ingestion records daily at 2 AM UTC
        "cleanup_stale_ingestions": {
            "task": "app.tasks.cleanup_stale_ingestions",
            "schedule": crontab(hour=2, minute=0),
        },
    },

    # ─ Result Backend (for task result tracking)
    result_expires=3600,               # Results expire after 1 hour
    result_backend_transport_options={
        "retry_on_timeout": True,
        "socket_connect_timeout": 5,
        "socket_timeout": 5,
    },

    # ─ Broker Connection Pooling
    broker_connection_retry=True,
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=10,

    # ─ Worker Pool Settings
    worker_pool="prefork",             # POSIX prefork (multiprocessing) for CPU-bound tasks
)


# ──────────────────────────────────────────────────────────────────────────────
# Auto-discover tasks
# ──────────────────────────────────────────────────────────────────────────────

celery_app.autodiscover_tasks(["app"])


# ──────────────────────────────────────────────────────────────────────────────
# Debug task
# ──────────────────────────────────────────────────────────────────────────────

@celery_app.task(bind=True)
def debug_task(self):
    """Echo task for testing Celery connectivity."""
    print(f"Request: {self.request!r}")
    return "Celery worker alive!"


def is_celery_worker_active() -> bool:
    """
    Check if the Redis broker is online and at least one Celery worker is active.
    Used for graceful fallback to FastAPI BackgroundTasks if the worker is not running.
    """
    try:
        # 0.5 second timeout to prevent blocking HTTP endpoints
        inspect = celery_app.control.inspect(timeout=0.5)
        stats = inspect.stats()
        return bool(stats)
    except Exception:
        return False


if __name__ == "__main__":
    celery_app.start()
