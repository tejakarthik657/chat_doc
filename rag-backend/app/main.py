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
from typing import Optional, List, Dict, Any

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

# In Linux cloud environments (Render/Docker), preserve OS /etc/resolv.conf for container networking.
import platform
if platform.system() == "Windows":
    try:
        import dns.resolver
        dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
        dns.resolver.default_resolver.nameservers = ['8.8.8.8', '8.8.4.4', '1.1.1.1']
    except Exception:
        pass

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.core.logging import setup_logging, set_correlation_id, get_correlation_id, log_with_data
from app.core.security_headers import SecurityHeadersMiddleware
from app.core.embeddings import get_embedding_model
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

    # Warm up embedding model in background so uvicorn binds to $PORT instantly (<1s)
    async def _warmup_models():
        try:
            await asyncio.to_thread(get_embedding_model)
            logger.info("[STARTUP] Embedding model ready in background.")
        except Exception as e:
            logger.warning(f"[STARTUP] Non-fatal background warmup note: {e}")

    asyncio.create_task(_warmup_models())

    # Pre-load cross-encoder reranker if enabled
    if settings.reranker_enabled:
        try:
            from app.core.reranker import get_reranker
            get_reranker()
        except Exception as e:
            logger.warning(f"[STARTUP] Non-fatal reranker load notice: {e}")
    else:
        logger.info("[STARTUP] Cross-encoder reranker is disabled.")

    # Create MongoDB indexes in background so uvicorn binds to PORT instantly in <0.1s
    async def _init_indexes():
        try:
            await create_indexes()
            logger.info("[STARTUP] MongoDB indexes verified in background.")
        except Exception as e:
            logger.warning(f"[STARTUP] Non-fatal index initialization note: {e}")

    asyncio.create_task(_init_indexes())

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

    try:
        from app.db.upstash import get_upstash_client
        upstash_c = get_upstash_client()
        await upstash_c.aclose()
        upstash_c.close()
        logger.info("[SHUTDOWN] Upstash Redis client connections closed")
    except Exception as e:
        logger.warning(f"[SHUTDOWN] Error closing Upstash client: {e}")


# ── Observability & Monitoring Setup ──────────────────────────────────────────

if settings.sentry_dsn:
    try:
        import sentry_sdk
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            traces_sample_rate=1.0,
            profiles_sample_rate=1.0,
            environment=settings.environment,
            send_default_pii=False,
        )
        print(f"[Sentry] Initialized cloud error monitoring & profiling (env={settings.environment}).")
    except Exception as sentry_err:
        print(f"[Sentry Warning] Failed to initialize Sentry: {sentry_err}")

if settings.langfuse_public_key and settings.langfuse_secret_key:
    os.environ["LANGFUSE_PUBLIC_KEY"] = settings.langfuse_public_key
    os.environ["LANGFUSE_SECRET_KEY"] = settings.langfuse_secret_key
    os.environ["LANGFUSE_HOST"] = settings.langfuse_base_url
    print(f"[Langfuse] Initialized cloud LLM observability tracing via {settings.langfuse_base_url}.")


# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="NEXUS AI Enterprise RAG API",
    description="Source-grounded autonomous intelligence & workspace platform.",
    version="2.0.0",
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
    "https://nexus-tawny-seven-50.vercel.app",
]

_env_origins = os.environ.get("ALLOWED_ORIGINS", "")
if _env_origins:
    _ALLOWED_ORIGINS.extend(
        [o.strip() for o in _env_origins.split(",") if o.strip()]
    )

# ── Middleware Stack ───────────────────────────────────────────────────────────

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(RequestSizeLimitMiddleware, max_size=50 * 1024 * 1024)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add CORSMiddleware LAST so it runs FIRST as the outermost layer
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_origin_regex=r"https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Correlation-ID"],
)


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
            "detail": f"Internal server error: {exc}",
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


# ── Google OAuth Aliases (Handles /auth/google, /api/auth/google, and /api/api/auth/google) ──

@app.get("/auth/google")
@app.get("/api/auth/google")
@app.get("/api/api/auth/google")
async def google_login_alias(request: Request, state: Optional[str] = None):
    from app.api.routes.auth import login_google
    return await login_google(request, state=state)


@app.get("/auth/google/callback")
@app.get("/api/auth/google/callback")
@app.get("/api/api/auth/google/callback")
async def google_callback_alias(request: Request, code: Optional[str] = None, error: Optional[str] = None, state: Optional[str] = None):
    from app.api.routes.auth import google_callback
    return await google_callback(request, code=code, error=error, state=state)



# ── Health Endpoints ───────────────────────────────────────────────────────────

@app.get("/health")
@app.get("/api/health")
async def health():
    """Liveness probe — basic service availability."""
    return {"status": "ok", "version": "2.2.5", "env": os.environ.get("ENVIRONMENT", "development")}

@app.get("/api/debug/test-step/{step}")
async def test_step(step: str):
    import os
    out = {"step": step}
    try:
        import resource
        out["initial_rss_kb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    except Exception:
        pass
    try:
        if step == "info":
            from app.core.config import get_settings
            s = get_settings()
            masked_url = s.mongodb_url
            if "@" in masked_url:
                prefix, rest = masked_url.split("@", 1)
                scheme = prefix.split("://")[0]
                masked_url = f"{scheme}://***:***@{rest}"
            out["mongodb_url"] = masked_url
            out["db_name"] = s.db_name
            out["qdrant_url"] = bool(s.qdrant_url)
            out["groq_configured"] = bool(s.groq_api_key or s.groq_api_keys)
        elif step == "fastembed_load":
            from app.core.embeddings import get_embedding_model
            m = get_embedding_model()
            out["model"] = str(type(m))
        elif step == "fastembed_embed":
            from app.core.embeddings import embed_texts
            v = embed_texts(["Test sentence for embedding on Render cloud container"])
            out["shape"] = list(v.shape)
        elif step == "faiss_index":
            from app.core.embeddings import embed_texts, build_faiss_index
            v = embed_texts(["Test sentence for FAISS indexing"])
            idx = build_faiss_index(v, "debug_test_doc")
            out["faiss_ntotal"] = idx.ntotal
        elif step == "bm25_index":
            from app.core.bm25 import build_bm25_index
            build_bm25_index([{"text": "Test sentence for BM25"}], "debug_test_doc")
            out["bm25"] = "ok"
        elif step == "pymupdf_extract":
            import fitz
            doc = fitz.open()
            p = doc.new_page()
            p.insert_text((50, 60), "Hello world from PyMuPDF")
            text = p.get_text("text")
            doc.close()
            out["extracted_chars"] = len(text)
        elif step == "groq_summary":
            from app.core.llm_groq import generate
            res = generate("Summary test", "Summarize this test in 5 words")
            out["groq_res"] = res
        elif step == "full_ingest":
            from app.ingestion.pipeline import ingest_document
            import fitz
            test_path = "/tmp/debug_test.pdf" if os.name != "nt" else "debug_test.pdf"
            doc = fitz.open()
            p = doc.new_page()
            p.insert_text((50, 60), "Test PDF for full ingestion pipeline verification.")
            doc.save(test_path)
            doc.close()
            res = await ingest_document(test_path, "debug_test.pdf", "debug_doc_id", "debug_user_id")
            out["ingest_res"] = res
        else:
            out["error"] = f"Unknown step: {step}"
    except Exception as e:
        import traceback
        out["exception"] = str(e)
        out["traceback"] = traceback.format_exc()
    try:
        import resource
        out["final_rss_kb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    except Exception:
        pass
    return out


@app.get("/models")
@app.get("/v1/models")
async def list_models():
    """OpenAI-compatible models discovery endpoint."""
    return {
        "object": "list",
        "data": [
            {
                "id": "groq-llama-3.3-70b",
                "object": "model",
                "created": 1700000000,
                "owned_by": "groq",
                "permission": [],
            },
            {
                "id": "qwen2.5-coder:3b",
                "object": "model",
                "created": 1700000000,
                "owned_by": "ollama",
                "permission": [],
            },
        ],
    }


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
