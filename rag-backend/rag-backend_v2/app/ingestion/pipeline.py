"""
Ingestion Pipeline
─────────────────
PDF → Text (per page) → Chunks → Embeddings → FAISS + BM25 + MongoDB

Both FAISS and BM25 indexes are built during ingestion so query time
has zero extra cost — just load and search.
"""
import os
import uuid
import fitz  # PyMuPDF
from datetime import datetime
from langchain.text_splitter import RecursiveCharacterTextSplitter

from app.core.config import get_settings
from app.core.embeddings import embed_texts, build_faiss_index
from app.core.bm25 import build_bm25_index
from app.db.mongodb import documents_col, chunks_col

settings = get_settings()


# ── Step 1: PDF → Paged text ──────────────────────────────────────────────────

def extract_pages(file_path: str) -> list[dict]:
    """
    Returns list of {page: int, text: str}.
    Preserves page numbers for source citations.
    """
    doc = fitz.open(file_path)
    pages = []
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()
        if text:  # skip blank pages
            pages.append({"page": page_num, "text": text})
    doc.close()
    return pages


# ── Step 2: Chunking ──────────────────────────────────────────────────────────

def chunk_pages(pages: list[dict], doc_id: str, filename: str) -> list[dict]:
    """
    Splits each page's text with overlap.
    Returns chunk dicts ready for MongoDB + FAISS.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ".", " ", ""]
    )

    chunks = []
    embedding_counter = 0

    for page_data in pages:
        splits = splitter.split_text(page_data["text"])
        for split in splits:
            if len(split.strip()) < 30:  # drop micro-chunks
                continue
            chunks.append({
                "chunk_id": str(uuid.uuid4()),
                "doc_id": doc_id,
                "filename": filename,
                "page": page_data["page"],
                "text": split.strip(),
                "embedding_id": embedding_counter,  # maps to FAISS row
            })
            embedding_counter += 1

    return chunks


# ── Step 3+4: Embed + Index (FAISS + BM25) ───────────────────────────────────

async def build_index(chunks: list[dict], doc_id: str):
    """
    Build both indexes from the same chunk list:
      - FAISS: dense semantic vectors (sentence-transformers)
      - BM25:  sparse keyword index (rank_bm25)
    Both saved to disk. Neither recomputed at query time.
    """
    texts = [c["text"] for c in chunks]

    # Dense index (FAISS)
    vectors = embed_texts(texts)
    build_faiss_index(vectors, doc_id)

    # Sparse index (BM25) — pure Python, milliseconds
    build_bm25_index(chunks, doc_id)


# ── Master pipeline ───────────────────────────────────────────────────────────

async def ingest_document(
    file_path: str,
    filename: str,
    doc_id: str,
    user_id: str
) -> dict:
    """
    Full ingestion pipeline. Called after the file is saved to disk.
    Updates the document record with status and page count.
    """
    try:
        # Mark as processing
        await documents_col().update_one(
            {"_id": doc_id},
            {"$set": {"status": "processing"}}
        )

        # Step 1: Extract
        pages = extract_pages(file_path)
        page_count = len(pages)

        # Step 2: Chunk
        chunks = chunk_pages(pages, doc_id, filename)

        if not chunks:
            raise ValueError("No extractable text found in PDF.")

        # Step 3+4: Embed + Index
        await build_index(chunks, doc_id)

        # Step 5: Persist chunk metadata to MongoDB
        await chunks_col().insert_many(chunks)

        # Step 6: Mark document as ready
        size_mb = round(os.path.getsize(file_path) / (1024 * 1024), 2)
        await documents_col().update_one(
            {"_id": doc_id},
            {"$set": {
                "status": "ready",
                "page_count": page_count,
                "chunk_count": len(chunks),
                "size_mb": size_mb
            }}
        )

        return {"status": "ready", "pages": page_count, "chunks": len(chunks)}

    except Exception as e:
        await documents_col().update_one(
            {"_id": doc_id},
            {"$set": {"status": "error", "error_message": str(e)}}
        )
        raise
