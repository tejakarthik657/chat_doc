"""
main.py — FastAPI application entry point.
One process. One port. One mental model.
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.embeddings import get_embedding_model
from app.db.mongodb import create_indexes
from app.api.routes import auth, documents, chat, analytics

settings = get_settings()


# ── Startup / Shutdown ────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup: load embedding model into memory, create DB indexes.
    This ensures the first request isn't slow.
    """
    print("🚀 Starting RAG backend...")

    # Create storage directories
    os.makedirs(os.path.join(settings.storage_dir, "uploads"), exist_ok=True)
    os.makedirs(os.path.join(settings.storage_dir, "indexes"), exist_ok=True)
    os.makedirs(settings.model_cache_dir, exist_ok=True)

    # Pre-load embedding model (80MB, must be in memory before first request)
    get_embedding_model()

    # Pre-load cross-encoder reranker (~22MB, CPU)
    from app.core.reranker import get_reranker
    get_reranker()

    # Create MongoDB indexes
    await create_indexes()

    print("✅ Backend ready.")
    yield
    print("👋 Shutting down.")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="RAG Document Assistant API",
    description="Source-grounded document Q&A. No hallucinations.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS — adjust origins for your frontend domain in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global error handler ──────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"[ERROR] {request.method} {request.url} → {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again."}
    )


# ── Routes ────────────────────────────────────────────────────────────────────

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(analytics.router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
