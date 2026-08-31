"""
main.py — FastAPI application entry point.
Production-ready with structured logging, security headers, correlation IDs, and graceful shutdown.
"""
import os
import sys
import signal
import time
import uuid
import logging
import asyncio

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.core.logging import setup_logging, set_correlation_id, get_correlation_id, log_with_data
from app.core.security_headers import SecurityHeadersMiddleware
from app.core.embeddings import get_embedding_model
from app.core.reranker import get_reranker
from app.db.mongodb import create_indexes, get_client
from app.api.routes.auth import router as auth_router
from app.api.routes.documents import router as documents_router
from app.api.routes.chat import router as chat_router
from app.api.routes.analytics import router as analytics_router
from app.api.routes.features import router as features_router
from app.api.routes.project import router as project_router
from app.api.routes.intelligence import router as intelligence_router

settings = get_settings()

# Setup structured logging
logger = setup_logging()


# ── Correlation ID Middleware ───────────────────────────────────────────────────

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Assigns a unique correlation ID to every request for distributed tracing."""

    async def dispatch(self, request: Request, call_next):
        cid = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        set_correlation_id(cid)
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = get_correlation_id()
        return response


# ── Request Size Limit Middleware ──────────────────────────────────────────────

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Rejects requests with bodies exceeding the configured limit."""

    def __init__(self, app, max_size: int = 50 * 1024 * 1024):
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_size:
            return JSONResponse(
                status_code=413,
                content={"detail": f"Request body too large. Maximum size is {self.max_size // (1024*1024)}MB."},
            )
        return await call_next(request)


# ── Startup / Shutdown ─────────────────────────────────────────────────────────

shutdown_event = asyncio.Event()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: load models, create DB indexes. Shutdown: close connections."""
    startup_start = time.perf_counter()
    print("=" * 60)
    print(f"[STARTUP] Starting RAG backend (env={os.environ.get('ENVIRONMENT', 'development')})")
    print("=" * 60)

    # Create storage directories
    os.makedirs(os.path.join(settings.storage_dir, "uploads"), exist_ok=True)
    os.makedirs(os.path.join(settings.storage_dir, "indexes"), exist_ok=True)
    os.makedirs(settings.model_cache_dir, exist_ok=True)

    # Validate critical configuration
    if not settings.groq_api_key:
        logger.warning("[STARTUP] GROQ_API_KEY not set — local LLM fallback will be used")

    if not settings.qdrant_url and os.environ.get("USE_QDRANT_SERVER") != "true":
        logger.warning("[STARTUP] Qdrant running in local disk mode — data will be lost on restart in production")

    # Pre-load embedding model
    try:
        get_embedding_model()
    except Exception as e:
        logger.error(f"[STARTUP] Failed to load embedding model: {e}")
        raise RuntimeError(f"Embedding model failed to load: {e}")

    # Pre-load cross-encoder reranker if enabled
    if settings.reranker_enabled:
        try:
            get_reranker()
        except Exception as e:
            logger.error(f"[STARTUP] Failed to load reranker model: {e}")
            raise RuntimeError(f"Reranker model failed to load: {e}")
    else:
        logger.info("[STARTUP] Cross-encoder reranker is disabled (bypassing pre-load).")

    # Create MongoDB indexes
    try:
        await create_indexes()
    except Exception as e:
        logger.error(f"[STARTUP] Failed to create MongoDB indexes: {e}")
        raise

    elapsed = time.perf_counter() - startup_start
    logger.info(f"[STARTUP] Backend ready in {elapsed:.2f}s")
    print("=" * 60)

    yield

    # Shutdown
    logger.info("[SHUTDOWN] Closing connections...")
    try:
        client = get_client()
        client.close()
        logger.info("[SHUTDOWN] MongoDB connection closed")
    except Exception as e:
        logger.error(f"[SHUTDOWN] Error closing MongoDB: {e}")

    try:
        from app.db.neo4j import close_neo4j_driver
        close_neo4j_driver()
        logger.info("[SHUTDOWN] Neo4j connection closed")
    except Exception as e:
        logger.error(f"[SHUTDOWN] Error closing Neo4j: {e}")


# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="RAG Document Assistant API",
    description="Source-grounded document Q&A. No hallucinations.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.access_token_expire_minutes > 0 else None,
    redoc_url="/redoc" if settings.access_token_expire_minutes > 0 else None,
)

# ── CORS ───────────────────────────────────────────────────────────────────────

_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://192.168.1.19:3000",
]

_env_origins = os.environ.get("ALLOWED_ORIGINS", "")
if _env_origins:
    _ALLOWED_ORIGINS.extend(
        [o.strip() for o in _env_origins.split(",") if o.strip()]
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Correlation-ID"],
)

# ── Middleware Stack ───────────────────────────────────────────────────────────

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(RequestSizeLimitMiddleware, max_size=50 * 1024 * 1024)


# ── Exception Handlers ────────────────────────────────────────────────────────

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Ensure HTTPException responses include CORS headers."""
    log_with_data(logger, "warning", f"HTTP {exc.status_code}: {exc.detail}", {
        "path": request.url.path,
        "status": exc.status_code,
    })
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "correlation_id": get_correlation_id()},
        headers={"Access-Control-Allow-Origin": request.headers.get("origin", "*")},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all error handler with structured logging."""
    log_with_data(logger, "error", f"Unhandled exception on {request.method} {request.url.path}", {
        "path": request.url.path,
        "method": request.method,
        "error": str(exc),
    })
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error. Please try again.",
            "correlation_id": get_correlation_id(),
        },
        headers={"Access-Control-Allow-Origin": request.headers.get("origin", "*")},
    )


# ── Routes ─────────────────────────────────────────────────────────────────────

app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(analytics_router)
app.include_router(features_router)
app.include_router(project_router)
app.include_router(intelligence_router)


# ── Health Endpoints ───────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Liveness probe — basic service availability."""
    return {"status": "ok", "version": "1.0.0", "env": os.environ.get("ENVIRONMENT", "development")}


@app.get("/health/ready")
async def health_ready():
    """Readiness probe — verifies MongoDB and Qdrant connectivity."""
    from app.db.mongodb import get_client
    from app.db.qdrant import check_qdrant_health

    checks: dict[str, str] = {}
    overall = "ok"

    try:
        await get_client().admin.command("ping")
        checks["mongodb"] = "ok"
    except Exception as e:
        checks["mongodb"] = f"error: {e}"
        overall = "degraded"

    if check_qdrant_health():
        checks["qdrant"] = "ok"
    else:
        checks["qdrant"] = "error"
        overall = "degraded"

    status_code = 200 if overall == "ok" else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": overall, "checks": checks, "version": "1.0.0", "env": os.environ.get("ENVIRONMENT", "development")},
    )
