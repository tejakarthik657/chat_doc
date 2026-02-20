"""
RAG Query Engine v2 — Upgraded Pipeline
────────────────────────────────────────

OLD pipeline:
  Question → Embed → FAISS → Threshold filter → Deduplicate → LLM

NEW pipeline:
  Question
    │
    ├─[HyDE]─► Hypothetical doc → Embed (if vague question)
    │           └─► FAISS Search ──────────────────────────┐
    │                                                       │
    └─[Raw]──► Embed question directly                     │
                └─► FAISS Search ──────────────────────────┤
                                                           │
                └─► BM25 Search  ──────────────────────────┤
                                                           │
                          RRF Fusion ◄─────────────────────┘
                               │
                          Fetch chunks from MongoDB
                               │
                          Cross-Encoder Reranker
                               │
                          Top-K context assembly
                               │
                          Memory injection
                               │
                          LLM Generation
                               │
                          Grounded Response + Citations

Each upgrade is independently fallback-safe.
If BM25 index missing → FAISS-only.
If HyDE fails → raw question.
If reranker fails → use fusion order.
"""
import numpy as np
from datetime import datetime

from app.core.embeddings import embed_texts, load_faiss_index, search_index
from app.core.bm25 import load_bm25_index, bm25_search
from app.core.fusion import reciprocal_rank_fusion, explain_fusion
from app.core.reranker import rerank_chunks
from app.rag.hyde import generate_hypothetical_document, should_use_hyde
# Use Groq for FAST & FREE responses (1-2 sec, 100% free tier)
from app.core.llm_groq import generate
# from app.core.llm_openai import generate  # Uncomment to use OpenAI (paid)
# from app.core.llm import generate  # Uncomment to use local TinyLlama (20+ min on CPU)
from app.core.config import get_settings
from app.db.mongodb import chunks_col, chat_history_col, memory_col, analytics_col
from app.models.schemas import ChatResponse, SourceCitation

settings = get_settings()

# Wider retrieval pool before reranking narrows it down
RETRIEVAL_POOL_SIZE = 12


def _is_overview_question(question: str) -> bool:
    q = question.lower().strip()
    overview_phrases = [
        "what is this document about",
        "what is this doc about",
        "what is the document about",
        "document summary",
        "summary",
        "summarize",
        "overview",
        "high level",
        "gist",
        "purpose of this document",
        "document is about",
        "document about",
    ]
    return any(phrase in q for phrase in overview_phrases)


# ── Context Assembly ──────────────────────────────────────────────────────────

def build_context_string(ranked_chunks: list[tuple]) -> str:
    """Format reranked chunks into the LLM context block."""
    parts = []
    for chunk, score in ranked_chunks:
        parts.append(f"[Page {chunk['page']}]\n{chunk['text']}")
    return "\n\n---\n\n".join(parts)


def _not_found_response(doc_id: str) -> ChatResponse:
    return ChatResponse(
        answer="I don't see this information in the uploaded documents.",
        sources=[],
        grounded=False,
        doc_id=doc_id,
        timestamp=datetime.utcnow()
    )


# ── Memory ────────────────────────────────────────────────────────────────────

async def get_memory(doc_id: str, user_id: str) -> str:
    mem = await memory_col().find_one({"doc_id": doc_id, "user_id": user_id})
    return mem.get("memory_summary", "") if mem else ""


async def update_memory(doc_id: str, user_id: str, question: str, answer: str):
    existing = await get_memory(doc_id, user_id)
    new_memory = f"{existing}\nUser asked: {question[:100]}" if existing else f"User asked: {question[:100]}"
    new_memory = new_memory[-500:]
    await memory_col().update_one(
        {"doc_id": doc_id, "user_id": user_id},
        {"$set": {"memory_summary": new_memory, "updated_at": datetime.utcnow()}},
        upsert=True
    )


# ── Analytics ─────────────────────────────────────────────────────────────────

async def log_question(user_id: str, doc_id: str, filename: str, question: str, embedding: list):
    await analytics_col().insert_one({
        "user_id": user_id,
        "doc_id": doc_id,
        "document_filename": filename,
        "question": question,
        "embedding": embedding,
        "timestamp": datetime.utcnow()
    })


# ── Hybrid Retrieval ──────────────────────────────────────────────────────────

async def hybrid_retrieve(
    question: str,
    doc_id: str,
    faiss_index,
    debug: bool = False,
    allow_low_similarity: bool = False
) -> tuple[list[int], dict]:
    """
    Run FAISS + BM25 + optional HyDE, fuse results with RRF.
    Returns (fused_embedding_ids, debug_info).
    """
    debug_info = {
        "hyde_used": False,
        "hyde_hypothesis": None,
        "faiss_hits": 0,
        "bm25_hits": 0,
        "fusion": None
    }

    # ── A: Decide search text (HyDE or raw) ──────────────────────────────────
    search_text = question
    if should_use_hyde(question):
        hypothesis = generate_hypothetical_document(question)
        if hypothesis != question:
            search_text = hypothesis
            debug_info["hyde_used"] = True
            debug_info["hyde_hypothesis"] = hypothesis[:200]

    # ── B: FAISS semantic search ──────────────────────────────────────────────
    q_vector = embed_texts([search_text])[0]
    threshold = 0.15 if allow_low_similarity else settings.similarity_threshold
    faiss_ids, faiss_scores = search_index(
        faiss_index,
        q_vector,
        top_k=RETRIEVAL_POOL_SIZE,
        threshold=threshold
    )
    faiss_results = list(zip(faiss_ids, faiss_scores))
    debug_info["faiss_hits"] = len(faiss_results)

    if allow_low_similarity and not faiss_results:
        faiss_ids, faiss_scores = search_index(
            faiss_index,
            q_vector,
            top_k=RETRIEVAL_POOL_SIZE,
            threshold=None
        )
        faiss_results = list(zip(faiss_ids, faiss_scores))
        debug_info["faiss_hits"] = len(faiss_results)

    # ── C: BM25 keyword search (raw question — always) ────────────────────────
    bm25_index = load_bm25_index(doc_id)
    bm25_results = []
    if bm25_index is not None:
        bm25_results = bm25_search(bm25_index, question, top_k=RETRIEVAL_POOL_SIZE)
        debug_info["bm25_hits"] = len(bm25_results)

    # ── Guardrail ─────────────────────────────────────────────────────────────
    if not faiss_results and not bm25_results:
        return [], debug_info

    # ── D: RRF Fusion ─────────────────────────────────────────────────────────
    fused = reciprocal_rank_fusion(faiss_results, bm25_results, top_k=RETRIEVAL_POOL_SIZE)

    if debug:
        debug_info["fusion"] = explain_fusion(faiss_results, bm25_results, fused)

    return [emb_id for emb_id, _ in fused], debug_info


# ── Main Entry Point ──────────────────────────────────────────────────────────

async def answer_question(
    question: str,
    doc_id: str,
    user_id: str,
    debug: bool = False
) -> ChatResponse:
    """
    Full upgraded RAG pipeline.
    Hybrid retrieval → Cross-encoder reranking → Grounded generation.
    """

    # Load FAISS index
    try:
        faiss_index = load_faiss_index(doc_id)
    except FileNotFoundError:
        return _not_found_response(doc_id)

    # Step 1–4: Hybrid Retrieval
    fused_embedding_ids, debug_info = await hybrid_retrieve(
        question,
        doc_id,
        faiss_index,
        debug=debug,
        allow_low_similarity=_is_overview_question(question)
    )

    if not fused_embedding_ids:
        fused_embedding_ids, debug_info = await hybrid_retrieve(
            question,
            doc_id,
            faiss_index,
            debug=debug,
            allow_low_similarity=True
        )

    if not fused_embedding_ids:
        raw_vector = embed_texts([question])[0]
        await log_question(user_id, doc_id, doc.get("filename", "Unknown"), question, raw_vector.tolist())
        return _not_found_response(doc_id)

    # Step 5: Fetch chunk metadata (preserve fusion order)
    raw_chunks = await chunks_col().find(
        {"doc_id": doc_id, "embedding_id": {"$in": fused_embedding_ids}}
    ).to_list(length=RETRIEVAL_POOL_SIZE)

    if not raw_chunks:
        return _not_found_response(doc_id)

    id_to_chunk = {c["embedding_id"]: c for c in raw_chunks}
    ordered_chunks = [
        id_to_chunk[emb_id]
        for emb_id in fused_embedding_ids
        if emb_id in id_to_chunk
    ]

    # Step 6: Cross-Encoder Reranking (precision layer)
    try:
        reranked = rerank_chunks(
            query=question,          # Always raw question — NOT HyDE hypothesis
            chunks=ordered_chunks,
            top_k=settings.context_top_k
        )
    except Exception as e:
        print(f"[Reranker] Failed, falling back to fusion order: {e}")
        reranked = [(c, 1.0) for c in ordered_chunks[:settings.context_top_k]]

    if not reranked:
        return _not_found_response(doc_id)

    # Step 7: Assemble context + inject memory
    context = build_context_string(reranked)
    memory = await get_memory(doc_id, user_id)

    # Step 8: Generate grounded answer
    answer = generate(context=context, question=question, memory=memory)

    # Step 9: Build citations
    sources = [
        SourceCitation(
            page=chunk["page"],
            chunk_id=chunk["chunk_id"],
            snippet=chunk["text"][:200]
        )
        for chunk, _ in reranked
    ]

    # Step 10: Persist
    raw_vector = embed_texts([question])[0]
    await chat_history_col().insert_one({
        "user_id": user_id,
        "doc_id": doc_id,
        "question": question,
        "answer": answer,
        "sources": [s.dict() for s in sources],
        "retrieval_debug": debug_info if debug else None,
        "timestamp": datetime.utcnow()
    })
    await update_memory(doc_id, user_id, question, answer)
    await log_question(user_id, doc_id, doc.get("filename", "Unknown"), question, raw_vector.tolist())

    return ChatResponse(
        answer=answer,
        sources=sources,
        grounded=True,
        doc_id=doc_id,
        timestamp=datetime.utcnow()
    )
