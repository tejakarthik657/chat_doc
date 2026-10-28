"""
Celery configuration and app initialization.
Decouples background tasks (crawling, indexing, OCR) from FastAPI event loop.
"""
import os
from app.core.config import get_settings

settings = get_settings()

try:
    from celery import Celery
    from celery.schedules import crontab
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    Celery = None
    crontab = None

if CELERY_AVAILABLE and Celery:
    celery_app = Celery(
        "rag_backend",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend,
    )

    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=100,
        task_soft_time_limit=1800,
        task_time_limit=3600,
        task_autoretry_for=(Exception,),
        task_max_retries=3,
        task_default_retry_delay=60,
        broker_connection_retry=True,
        broker_connection_retry_on_startup=True,
        broker_connection_max_retries=10,
        worker_pool="prefork",
    )

    try:
        celery_app.autodiscover_tasks(["app"])
    except Exception:
        pass
else:
    class DummyCelery:
        def task(self, *args, **kwargs):
            def decorator(f):
                f.delay = f
                return f
            return decorator
        def autodiscover_tasks(self, *args, **kwargs):
            pass
    celery_app = DummyCelery()


def is_celery_worker_active() -> bool:
    """
    Check if the Redis broker is online and at least one Celery worker is active.
    Used for graceful fallback to FastAPI BackgroundTasks if the worker is not running.
    """
    if not CELERY_AVAILABLE or not hasattr(celery_app, "control"):
        return False
    try:
        inspect = celery_app.control.inspect(timeout=0.5)
        stats = inspect.stats()
        return bool(stats)
    except Exception:
        return False


if __name__ == "__main__":
    if CELERY_AVAILABLE and hasattr(celery_app, "start"):
        celery_app.start()
