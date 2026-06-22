"""
main.py — FastAPI application entry point.
One process. One port. One mental model.
"""
# Avoid Intel/LLVM OpenMP conflict (sentence-transformers, numpy, torch)
# Reload trigger comment
import os
import warnings
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
# Suppress threadpoolctl OpenMP warning (cosmetic, not the cause of crashes)
warnings.filterwarnings("ignore", message="Found Intel OpenMP", module="threadpoolctl")
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.embeddings import get_embedding_model
from app.core.reranker import get_reranker
from app.db.mongodb import create_indexes
from app.api.routes.auth import router as auth_router
from app.api.routes.documents import router as documents_router
from app.api.routes.chat import router as chat_router
from app.api.routes.analytics import router as analytics_router
from app.api.routes.features import router as features_router
from app.api.routes.project import router as project_router

settings = get_settings()


# ── Startup / Shutdown ────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup: load embedding model into memory, create DB indexes.
    This ensures the first request isn't slow.
    """
    print("Starting RAG backend...")

    # Create storage directories
    os.makedirs(os.path.join(settings.storage_dir, "uploads"), exist_ok=True)
    os.makedirs(os.path.join(settings.storage_dir, "indexes"), exist_ok=True)
    os.makedirs(settings.model_cache_dir, exist_ok=True)

    # Pre-load embedding model (80MB, lazy-load on first request instead)
    # get_embedding_model()

    # Pre-load cross-encoder reranker (lazy-load)
    # get_reranker()

    # Create MongoDB indexes
    await create_indexes()

    print("Backend ready.")
    yield
    print("Shutting down.")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="RAG Document Assistant API",
    description="Source-grounded document Q&A. No hallucinations.",
    version="1.0.0",
    lifespan=lifespan
)

_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://192.168.1.19:3000",
]

# ── Global error handler ──────────────────────────────────────────────────────

def _cors_headers(request: Request) -> dict:
    """Add CORS headers to error responses so the frontend can read them."""
    origin = request.headers.get("origin", "http://localhost:3000")
    if origin in _ALLOWED_ORIGINS:
        return {"Access-Control-Allow-Origin": origin, "Access-Control-Allow-Credentials": "true"}
    return {}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Ensure HTTPException responses (e.g. 500 from auth) include CORS headers."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail} if isinstance(exc.detail, str) else exc.detail,
        headers=_cors_headers(request),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"[ERROR] {request.method} {request.url} → {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again."},
        headers=_cors_headers(request),
    )


# ── Routes ────────────────────────────────────────────────────────────────────

app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(analytics_router)
app.include_router(features_router)
app.include_router(project_router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}

# CORS — wrap at ASGI level so CORS headers are added to ALL responses,
# including 500 errors (which can bypass add_middleware)
from starlette.middleware.cors import CORSMiddleware as StarletteCORSMiddleware
app = StarletteCORSMiddleware(
    app=app,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
