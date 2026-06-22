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
from app.core.feature_models import verify_answer_support
from app.rag.hyde import generate_hypothetical_document, should_use_hyde
# Use Groq for FAST & FREE responses (1-2 sec, 100% free tier)
from app.core.llm_groq import generate
# from app.core.llm_openai import generate  # Uncomment to use OpenAI (paid)
# from app.core.llm import generate  # Uncomment to use local TinyLlama (20+ min on CPU)
from app.core.config import get_settings
from app.db.mongodb import chunks_col, chat_history_col, memory_col, analytics_col, documents_col
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

def deduplicate_chunks(chunks: list[dict], scores: list[float]) -> list[tuple[dict, float]]:
    """Keep only the highest scoring chunk per page to ensure diverse context."""
    best_per_page = {}
    for chunk, score in zip(chunks, scores):
        page = chunk.get("page", 1)
        if page not in best_per_page or score > best_per_page[page][1]:
            best_per_page[page] = (chunk, score)
    
    # Sort by score descending
    sorted_ranked = sorted(best_per_page.values(), key=lambda x: x[1], reverse=True)
    return sorted_ranked


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
    debug: bool = False,
    strict_mode: bool = False
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

    doc = await documents_col().find_one({"_id": doc_id, "user_id": user_id}, {"filename": 1})
    doc_filename = doc.get("filename", "Unknown") if doc else "Unknown"

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
        await log_question(user_id, doc_id, doc_filename, question, raw_vector.tolist())
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

    verification = verify_answer_support(
        answer,
        [chunk["text"] for chunk, _ in reranked]
    )

    if strict_mode and verification["label"] in {"weak_support", "insufficient"}:
        answer = "I cannot provide a confident answer from this document in strict mode. Try asking a more specific question or disable strict mode."

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
    await log_question(user_id, doc_id, doc_filename, question, raw_vector.tolist())

    return ChatResponse(
        answer=answer,
        sources=sources,
        grounded=True,
        doc_id=doc_id,
        timestamp=datetime.utcnow(),
        support_label=verification["label"],
        support_confidence=verification["confidence"],
        support_snippet=verification["best_snippet"],
    )


async def answer_project_question(
    question: str,
    project_id: str,
    user_id: str,
    strict_mode: bool = False,
    scoped_sources: list[str] | None = None
) -> ChatResponse:
    """
    RAG pipeline for Projects.
    Retrieves candidate chunks from Qdrant, rerank with Cross-Encoder, and calls Groq.
    """
    from app.db.mongodb import projects_col
    
    # 1. Verify project exists
    project = await projects_col().find_one({"_id": project_id, "user_id": user_id})
    if not project:
        return ChatResponse(
            answer="Project not found or you do not have permission to view it.",
            sources=[],
            grounded=False,
            doc_id=project_id,
            timestamp=datetime.utcnow()
        )
        
    project_name = project.get("name", "Project")
    
    # Detect if comparison or multi-document analysis is requested
    lower_q = question.lower()
    comparison_keywords = {"compare", "comparison", "yearly", "trends", "difference", "similar", "progress", "accreditation", "vs", "versus"}
    is_comparison = any(kw in lower_q for kw in comparison_keywords)

    retrieval_limit = RETRIEVAL_POOL_SIZE
    top_k_context = settings.context_top_k
    if is_comparison:
        retrieval_limit = RETRIEVAL_POOL_SIZE * 2
        top_k_context = min(settings.context_top_k * 2, 10)

    # 2. Embed the question
    q_vector = embed_texts([question])[0]
    
    # 3. Retrieve from Qdrant
    from app.db.qdrant import get_qdrant_client
    client = get_qdrant_client()
    collection_name = f"project_{project_id}"
    
    # Build filter if scoped_sources is provided
    query_filter = None
    if scoped_sources:
        from qdrant_client.http import models as qdrant_models
        # Filter where payload["url"] is one of the scoped_sources
        query_filter = qdrant_models.Filter(
            should=[
                qdrant_models.FieldCondition(
                    key="url",
                    match=qdrant_models.MatchValue(value=src)
                )
                for src in scoped_sources
            ]
        )
    
    try:
        res = client.search(
            collection_name=collection_name,
            query_vector=q_vector.tolist(),
            query_filter=query_filter,
            limit=retrieval_limit
        )
    except Exception as e:
        print(f"[Qdrant] Search failed (maybe collection does not exist): {e}")
        return ChatResponse(
            answer="No document chunks or crawled pages indexed in this project yet. Please verify that the crawler is done.",
            sources=[],
            grounded=False,
            doc_id=project_id,
            timestamp=datetime.utcnow()
        )
        
    if not res:
        return ChatResponse(
            answer="I couldn't find any relevant information for your question in the project's knowledge base.",
            sources=[],
            grounded=False,
            doc_id=project_id,
            timestamp=datetime.utcnow()
        )
        
    # Convert hits to chunks for Reranker
    candidates = [
        {
            "chunk_id": hit.payload["chunk_id"],
            "text": hit.payload["text"],
            "source_name": hit.payload["source_name"],
            "url": hit.payload["url"],
            "page": hit.payload["page"]
        }
        for hit in res
    ]
    
    # 4. Cross-Encoder Reranking
    try:
        reranked = rerank_chunks(
            query=question,
            chunks=candidates,
            top_k=top_k_context
        )
    except Exception as e:
        print(f"[Reranker] Project search rerank failed, using original retrieval order: {e}")
        reranked = [(c, 1.0) for c in candidates[:top_k_context]]
        
    if not reranked:
        return ChatResponse(
            answer="I couldn't find any relevant information for your question in the project's knowledge base.",
            sources=[],
            grounded=False,
            doc_id=project_id,
            timestamp=datetime.utcnow()
        )
        
    # 5. Assemble context string
    parts = []
    for chunk, score in reranked:
        source_lbl = f"Source: {chunk['source_name']}"
        if chunk.get("url"):
            source_lbl += f" URL: {chunk['url']}"
        if chunk.get("page") and chunk["page"] > 1:
            source_lbl += f" Page: {chunk['page']}"
            
        parts.append(f"[{source_lbl}]\n{chunk['text']}")
    context = "\n\n---\n\n".join(parts)
    
    # 6. Retrieve conversation history memory
    memory = await get_memory(project_id, user_id)
    
    # 7. Generate answer via Groq
    augmented_question = question
    if is_comparison:
        augmented_question = (
            f"{question}\n\n"
            f"[INSTRUCTION] The user is requesting a comparison, trend, or multi-document synthesis. "
            f"Please synthesize and contrast facts across the different documents, sources, and pages in the context. "
            f"Structure your response with clear comparison sections, highlighting differences, similarities, and chronological timelines if applicable. "
            f"Be sure to cite the specific sources (e.g., [Source Name] or [URL]) when referencing facts."
        )
    answer = generate(context=context, question=augmented_question, memory=memory)
    
    # 8. Verify answer support
    verification = {"label": "supported", "confidence": 1.0, "best_snippet": ""}
    try:
        verification = verify_answer_support(
            answer,
            [chunk["text"] for chunk, _ in reranked]
        )
    except Exception as verify_err:
        print(f"[Verification] Answer verification skipped: {verify_err}")
        
    if strict_mode and verification.get("label") in {"weak_support", "insufficient"}:
        answer = "I cannot provide a confident answer from the indexed pages in strict mode. Try asking a more specific question."
        
    # 9. Format response citations
    sources = [
        SourceCitation(
            page=chunk["page"],
            chunk_id=chunk["chunk_id"],
            snippet=chunk["text"][:200],
            url=chunk.get("url"),
            source_name=chunk.get("source_name")
        )
        for chunk, _ in reranked
    ]
    
    # 10. Persist to MongoDB
    await chat_history_col().insert_one({
        "user_id": user_id,
        "doc_id": project_id,  # Use doc_id to maintain database schema compatibility with the history page
        "question": question,
        "answer": answer,
        "sources": [s.dict() for s in sources],
        "timestamp": datetime.utcnow()
    })
    await update_memory(project_id, user_id, question, answer)
    
    # Log analytics
    await log_question(user_id, project_id, project_name, question, q_vector.tolist())
    
    return ChatResponse(
        answer=answer,
        sources=sources,
        grounded=True,
        doc_id=project_id,
        timestamp=datetime.utcnow(),
        support_label=verification.get("label"),
        support_confidence=verification.get("confidence"),
        support_snippet=verification.get("best_snippet"),
    )

