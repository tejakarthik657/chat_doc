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
import time

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
RETRIEVAL_POOL_SIZE = 30


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


def classify_query_metadata(query: str) -> dict:
    """
    Classify query keywords to target specific departments or document types.
    """
    import re
    query_lower = query.lower()
    metadata_filter = {}
    
    # 1. Department Detection
    departments = ["cse", "ece", "eee", "it", "mech", "civil", "mba", "mca"]
    for dept in departments:
        if re.search(r'\b' + dept + r'\b', query_lower):
            metadata_filter["department"] = dept
            break
            
    # 2. Document Type Detection
    faculty_keywords = ["faculty", "professor", "teacher", "staff", "hod", "lecturer", "profile", "qualification", "experience"]
    placement_keywords = ["placement", "recruit", "job", "salary", "package", "offer", "company", "companies"]
    syllabus_keywords = ["syllabus", "curriculum", "course", "subject", "credit", "regulation"]
    
    if any(re.search(r'\b' + kw + r'\b', query_lower) for kw in faculty_keywords):
        metadata_filter["document_type"] = "faculty"
    elif any(re.search(r'\b' + kw + r'\b', query_lower) for kw in placement_keywords):
        metadata_filter["document_type"] = "placement"
    elif any(re.search(r'\b' + kw + r'\b', query_lower) for kw in syllabus_keywords):
         metadata_filter["document_type"] = "syllabus"
         
    return metadata_filter


def _generate_query_variations(query: str) -> list[str]:
    """
    Generate query variations for improved recall in multi-query retrieval.
    Creates rephrased versions of the question to capture different phrasings.
    """
    variations = [query]
    q_lower = query.lower().strip()
    
    # If query already looks like a detailed question, skip variation
    if len(query.split()) > 8:
        return variations
    
    # Reordering variations
    if not q_lower.startswith(("what", "who", "how", "when", "where", "why", "list", "give", "find")):
        variations.append(f"information about {query}")
        variations.append(f"details of {query}")
    
    # Named entity emphasis
    words = query.split()
    if len(words) >= 2:
        # Swap word order for name-like queries
        variations.append(" ".join(reversed(words[:3])) if len(words) >= 3 else query)
    
    # Faculty-specific variations
    faculty_signals = ["faculty", "professor", "hod", "staff", "qualification", "experience"]
    if any(sig in q_lower for sig in faculty_signals):
        variations.append(f"{query} - list of teachers")
        variations.append(f"all {query}")
    
    # Placements-specific variations
    placement_signals = ["placement", "package", "company", "recruit"]
    if any(sig in q_lower for sig in placement_signals):
        variations.append(f"{query} - statistics")
    
    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for v in variations:
        v_clean = v.strip().lower()
        if v_clean not in seen:
            seen.add(v_clean)
            deduped.append(v.strip())
    
    return deduped[:4]


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


def build_context_string(ranked_chunks: list[tuple], max_tokens: int = 4000) -> str:
    """
    Format reranked chunks into the LLM context block.
    Uses parent text (full page/section) when available for richer context.
    Deduplicates by parent_id, respecting token budget.
    """
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
    except ImportError:
        enc = None
    
    parts = []
    seen_parents = set()
    total_tokens = 0
    
    for chunk, score in ranked_chunks:
        source_url = chunk.get("url", "")
        source_name = chunk.get("source_name", "")
        page = chunk.get("page", 1)
        parent_id = chunk.get("parent_id")
        parent_text = chunk.get("parent_text", "")
        
        dedup_key = parent_id or (source_url or source_name, page)
        
        if dedup_key in seen_parents:
            continue
        seen_parents.add(dedup_key)
        
        display_text = parent_text if parent_text else chunk["text"]
        
        source_lbl = f"Source: {source_name}"
        if source_url:
            source_lbl += f" | {source_url}"
        if page and page > 1:
            source_lbl += f" | Page {page}"
        
        formatted = f"[{source_lbl}]\n{display_text}"
        
        if enc:
            chunk_tokens = len(enc.encode(formatted))
        else:
            chunk_tokens = len(formatted) // 4
        
        if total_tokens + chunk_tokens > max_tokens:
            break
        
        parts.append(formatted)
        total_tokens += chunk_tokens
    
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
    Supports multi-query for improved recall.
    Returns (fused_embedding_ids, debug_info).
    """
    debug_info = {
        "hyde_used": False,
        "hyde_hypothesis": None,
        "faiss_hits": 0,
        "bm25_hits": 0,
        "fusion": None,
        "query_variations": 1
    }

    # ── A: Decide search text (HyDE or raw) ──────────────────────────────────
    search_text = question
    query_variations = [question]
    
    if should_use_hyde(question):
        hypothesis = generate_hypothetical_document(question)
        if hypothesis != question:
            search_text = hypothesis
            debug_info["hyde_used"] = True
            debug_info["hyde_hypothesis"] = hypothesis[:200]
            query_variations.append(hypothesis)
    
    # Generate query variations for better recall
    query_variations = _generate_query_variations(question)
    debug_info["query_variations"] = len(query_variations)
    
    # ── B: FAISS semantic search (multi-query) ────────────────────────────────
    all_faiss_results: dict[int, float] = {}
    for q_text in query_variations:
        q_vector = embed_texts([q_text], is_query=True)[0]
        threshold = 0.15 if allow_low_similarity else settings.similarity_threshold
        faiss_ids, faiss_scores = search_index(
            faiss_index,
            q_vector,
            top_k=RETRIEVAL_POOL_SIZE,
            threshold=threshold
        )
        for idx, score in zip(faiss_ids, faiss_scores):
            if idx not in all_faiss_results or score > all_faiss_results[idx]:
                all_faiss_results[idx] = score
    
    faiss_results = sorted(all_faiss_results.items(), key=lambda x: x[1], reverse=True)
    debug_info["faiss_hits"] = len(faiss_results)
    
    if allow_low_similarity and not faiss_results:
        all_faiss_results = {}
        for q_text in query_variations:
            q_vector = embed_texts([q_text], is_query=True)[0]
            faiss_ids, faiss_scores = search_index(
                faiss_index,
                q_vector,
                top_k=RETRIEVAL_POOL_SIZE,
                threshold=None
            )
            for idx, score in zip(faiss_ids, faiss_scores):
                if idx not in all_faiss_results or score > all_faiss_results[idx]:
                    all_faiss_results[idx] = score
        faiss_results = sorted(all_faiss_results.items(), key=lambda x: x[1], reverse=True)
        debug_info["faiss_hits"] = len(faiss_results)

    # ── C: BM25 keyword search (always use raw question + variations) ─────────
    bm25_results = []
    bm25_index = load_bm25_index(doc_id)
    if bm25_index is not None:
        all_bm25: dict[int, float] = {}
        for q_text in query_variations:
            bm25_hits = bm25_search(bm25_index, q_text, top_k=RETRIEVAL_POOL_SIZE)
            for idx, score in bm25_hits:
                if idx not in all_bm25 or score > all_bm25[idx]:
                    all_bm25[idx] = score
        bm25_results = sorted(all_bm25.items(), key=lambda x: x[1], reverse=True)
        debug_info["bm25_hits"] = len(bm25_results)

    # ── Guardrail ──────────────────────────────────────────────────────────
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
    All errors are caught and return a graceful response.
    """
    t_start = time.perf_counter()
    try:
        # Load FAISS index
        try:
            faiss_index = load_faiss_index(doc_id)
        except FileNotFoundError:
            return _not_found_response(doc_id)

        doc = await documents_col().find_one({"_id": doc_id, "user_id": user_id}, {"filename": 1, "summary": 1})
        doc_filename = doc.get("filename", "Unknown") if doc else "Unknown"

        # Step 1–4: Hybrid Retrieval
        t_retrieval_start = time.perf_counter()
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
        t_retrieval = time.perf_counter() - t_retrieval_start

        if not fused_embedding_ids:
            raw_vector = embed_texts([question], is_query=True)[0]
            await log_question(user_id, doc_id, doc_filename, question, raw_vector.tolist())
            return _not_found_response(doc_id)

        # Step 5: Fetch chunk metadata (preserve fusion order)
        t_mongodb_start = time.perf_counter()
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
        t_mongodb = time.perf_counter() - t_mongodb_start

        # Step 6: Cross-Encoder Reranking (precision layer)
        t_rerank_start = time.perf_counter()
        try:
            reranked = rerank_chunks(
                query=question,          # Always raw question — NOT HyDE hypothesis
                chunks=ordered_chunks,
                top_k=settings.context_top_k
            )
        except Exception as e:
            print(f"[Reranker] Failed, falling back to fusion order: {e}")
            reranked = [(c, 1.0) for c in ordered_chunks[:settings.context_top_k]]
        t_rerank = time.perf_counter() - t_rerank_start

        if not reranked:
            return _not_found_response(doc_id)

        # Step 7: Assemble context + inject memory (uses parent text when available)
        context = build_context_string(reranked)
        
        # Prepend global document summary if available to provide top-down hierarchical context
        doc_summary = doc.get("summary", "") if doc else ""
        if doc_summary:
            context = f"[GLOBAL DOCUMENT SUMMARY]\n{doc_summary}\n\n---\n\n" + context
            
        memory = await get_memory(doc_id, user_id)

        # Step 8: Generate grounded answer
        t_gen_start = time.perf_counter()
        answer = generate(context=context, question=question, memory=memory)
        t_gen = time.perf_counter() - t_gen_start

        t_verify_start = time.perf_counter()
        verification = verify_answer_support(
            answer,
            [chunk["text"] for chunk, _ in reranked]
        )

        if strict_mode and verification["label"] in {"weak_support", "insufficient"}:
            answer = "I cannot provide a confident answer from this document in strict mode. Try asking a more specific question or disable strict mode."
        t_verify = time.perf_counter() - t_verify_start

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
        t_db_start = time.perf_counter()
        raw_vector = embed_texts([question], is_query=True)[0]
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
        t_db = time.perf_counter() - t_db_start

        t_total = time.perf_counter() - t_start
        print(f"[RAG LATENCY (Single Doc)] Total: {t_total:.3f}s | Retrieval: {t_retrieval:.3f}s | MongoDB: {t_mongodb:.3f}s | Reranker: {t_rerank:.3f}s | Gen: {t_gen:.3f}s | Verify: {t_verify:.3f}s | DB Write: {t_db:.3f}s")

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

    except Exception as e:
        from app.core.logger import log_error
        log_error(f"Doc: {doc_id}, User: {user_id}, Question: {question[:200]}", exc=e)
        print(f"[CHAT ERROR] {type(e).__name__}: {e}")
        return ChatResponse(
            answer="I encountered an error while processing your question. Please try again or rephrase.",
            sources=[],
            grounded=False,
            doc_id=doc_id,
            timestamp=datetime.utcnow()
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
    t_start = time.perf_counter()
    from app.db.mongodb import projects_col
    
    # 1. Verify project exists
    project = await projects_col().find_one({"_id": project_id, "user_id": user_id})
    if not project:
        return ChatResponse(
            answer="Project not found or you do not have access to it.",
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



    # 2. Embed the question
    t_retrieval_start = time.perf_counter()
    q_vector = embed_texts([question], is_query=True)[0]
    
    # 3. Retrieve candidates using Hybrid Search (Qdrant + BM25) with Metadata Filtering
    from app.db.qdrant import get_qdrant_client, search_collection
    from qdrant_client.http import models as qdrant_models
    client = get_qdrant_client()
    collection_name = f"project_{project_id}"
    
    # ── Query Router ─────────────────────────────────────────────────────────
    from app.rag.router import get_route_config
    route_config = get_route_config(question)
    route_name = route_config["route"]
    print(f"[Router] Route={route_name}")

    # Router sets document_type; augment with department detection
    dept_meta = classify_query_metadata(question)
    metadata_filter = {}
    if dept_meta.get("department"):
        metadata_filter["department"] = dept_meta["department"]
    if route_config.get("document_type"):
        metadata_filter["document_type"] = route_config["document_type"]
    if metadata_filter:
        print(f"[Router] Metadata filters: {metadata_filter}")
    
    # Route-specific retrieval tuning
    retrieval_limit = route_config["retrieval_pool"]
    top_k_context = route_config["context_top_k"]
    prompt_hint = route_config.get("prompt_hint", "")

    if is_comparison:
        retrieval_limit = RETRIEVAL_POOL_SIZE * 2
        top_k_context = min(settings.context_top_k * 2, 10)
    conditions = []
    if scoped_sources:
        should_conditions = [
            qdrant_models.FieldCondition(
                key="url",
                match=qdrant_models.MatchValue(value=src)
            )
            for src in scoped_sources
        ]
        conditions.append(qdrant_models.Filter(should=should_conditions))
        
    query_filter = qdrant_models.Filter(must=conditions) if conditions else None
    
    # Generate query variations for multi-query retrieval
    query_variations = _generate_query_variations(question)
    print(f"[RAG Engine] Query variations: {len(query_variations)}")
    
    # Run Dense Vector Search in Qdrant (multi-query aggregation)
    all_qdrant: dict[int, float] = {}
    try:
        for q_var in query_variations:
            qv = embed_texts([q_var], is_query=True)[0]
            res = search_collection(
                collection_name=collection_name,
                query_vector=qv.tolist(),
                query_filter=query_filter,
                limit=retrieval_limit,
            )
            
            for hit in res:
                emb_id = hit.payload.get("embedding_id")
                if emb_id is not None:
                    eid = int(emb_id)
                    score = float(hit.score)
                    
                    # Apply soft metadata boosting in Python (add 0.15 boost for matches)
                    if metadata_filter.get("department") and hit.payload.get("department") == metadata_filter["department"]:
                        score += 0.15
                    if metadata_filter.get("document_type") and hit.payload.get("document_type") == metadata_filter["document_type"]:
                        score += 0.15
                        
                    if eid not in all_qdrant or score > all_qdrant[eid]:
                        all_qdrant[eid] = score
    except Exception as e:
        print(f"[Qdrant] Search failed (maybe collection does not exist): {e}")
        return ChatResponse(
            answer="No document chunks or crawled pages indexed in this project yet. Please verify that the crawler is done.",
            sources=[],
            grounded=False,
            doc_id=project_id,
            timestamp=datetime.utcnow()
        )
    
    qdrant_results = sorted(all_qdrant.items(), key=lambda x: x[1], reverse=True)
    
    if not qdrant_results:
        return ChatResponse(
            answer="I couldn't find any relevant information for your question in the project's knowledge base.",
            sources=[],
            grounded=False,
            doc_id=project_id,
            timestamp=datetime.utcnow()
        )
    
    # Run Sparse Keyword Search (BM25)  
    bm25_results = []
    bm25_index = load_bm25_index(project_id)
    if bm25_index is not None:
        bm25_results = bm25_search(bm25_index, question, top_k=retrieval_limit)
        print(f"[RAG Engine] Hybrid search BM25 hits: {len(bm25_results)}")
    t_retrieval = time.perf_counter() - t_retrieval_start
        
    # Perform RRF Fusion to combine Dense (Qdrant) and Sparse (BM25) results
    t_fusion_start = time.perf_counter()
    fused = reciprocal_rank_fusion(qdrant_results, bm25_results, top_k=retrieval_limit)
    fused_ids = [emb_id for emb_id, _ in fused]
    t_fusion = time.perf_counter() - t_fusion_start
    
    # Retrieve chunk details from MongoDB
    t_mongodb_start = time.perf_counter()
    if fused_ids:
        raw_chunks = await chunks_col().find(
            {"doc_id": project_id, "embedding_id": {"$in": fused_ids}}
        ).to_list(length=len(fused_ids))
        
        # Sort chunks in RRF order
        id_to_chunk = {c["embedding_id"]: c for c in raw_chunks}
        candidates = []
        for emb_id in fused_ids:
            if emb_id in id_to_chunk:
                chunk_doc = id_to_chunk[emb_id]
                candidates.append({
                    "chunk_id": chunk_doc["chunk_id"],
                    "text": chunk_doc["text"],
                    "source_name": chunk_doc["filename"],
                    "url": chunk_doc.get("url"),
                    "page": chunk_doc.get("page", 1)
                })
    else:
        # Fallback: use Qdrant result payloads directly
        all_raw_hits = []
        try:
            for q_var in query_variations:
                qv = embed_texts([q_var], is_query=True)[0]
                raw_hits = search_collection(
                    collection_name=collection_name,
                    query_vector=qv.tolist(),
                    limit=retrieval_limit,
                )
                all_raw_hits.extend(raw_hits)
        except Exception:
            pass
        
        seen_ids = set()
        candidates = []
        for hit in all_raw_hits:
            cid = hit.payload.get("chunk_id")
            if cid and cid not in seen_ids:
                seen_ids.add(cid)
                candidates.append({
                    "chunk_id": cid,
                    "text": hit.payload["text"],
                    "source_name": hit.payload["source_name"],
                    "url": hit.payload["url"],
                    "page": hit.payload["page"]
                })
    t_mongodb = time.perf_counter() - t_mongodb_start
    
    # 4. Cross-Encoder Reranking
    t_rerank_start = time.perf_counter()
    try:
        reranked = rerank_chunks(
            query=question,
            chunks=candidates,
            top_k=top_k_context
        )
    except Exception as e:
        print(f"[Reranker] Project search rerank failed, using original retrieval order: {e}")
        reranked = [(c, 1.0) for c in candidates[:top_k_context]]
    t_rerank = time.perf_counter() - t_rerank_start
        
    if not reranked:
        return ChatResponse(
            answer="I couldn't find any relevant information for your question in the project's knowledge base.",
            sources=[],
            grounded=False,
            doc_id=project_id,
            timestamp=datetime.utcnow()
        )
    
    # ── CRAG: Corrective RAG — graded relevance check before LLM ────────────
    t_crag_start = time.perf_counter()
    t_crag = 0.0
    if settings.crag_enabled:
        top_chunks = [c for c, _ in reranked]
        crag_error = None
        try:
            from app.rag.crag import grade_chunk_relevance, grade_chunks_relevance_batch, rewrite_query
        except ImportError as _crag_import_err:
            crag_error = str(_crag_import_err)
            grade_chunk_relevance = None
            grade_chunks_relevance_batch = None
            rewrite_query = None

        high_count = 0
        medium_count = 0
        if grade_chunks_relevance_batch:
            try:
                grades = grade_chunks_relevance_batch(question, [ch.get("text", "") for ch in top_chunks[:settings.context_top_k]])
                for g in grades:
                    rel = g.get("relevance")
                    if rel == "high":
                        high_count += 1
                    elif rel == "medium":
                        medium_count += 1
            except Exception as batch_err:
                print(f"[CRAG Batch] Error in batch relevance grading: {batch_err}. Falling back to sequential.")
                if grade_chunk_relevance:
                    for ch in top_chunks[:settings.context_top_k]:
                        grade = grade_chunk_relevance(question, ch.get("text", ""))
                        rel = grade.get("relevance")
                        if rel == "high":
                            high_count += 1
                        elif rel == "medium":
                            medium_count += 1
        elif grade_chunk_relevance:
            for ch in top_chunks[:settings.context_top_k]:
                grade = grade_chunk_relevance(question, ch.get("text", ""))
                rel = grade.get("relevance")
                if rel == "high":
                    high_count += 1
                elif rel == "medium":
                    medium_count += 1
        
        # Proceed to generation if we have high or medium relevance chunks.
        # Only rewrite and retry if we have absolutely zero high/medium relevance chunks.
        passing_count = high_count + medium_count
        if passing_count == 0 and len(top_chunks) >= settings.context_top_k and rewrite_query:
            # All reranked chunks are low relevance — try one rewrite + re-retrieval
            print(f"[CRAG] Low relevance detected (passing_count=0). Rewriting query...")
            rewritten_q = rewrite_query(question)
            if rewritten_q != question:
                print(f"[CRAG] Rewritten query: {rewritten_q}")
                # Re-run retrieval with rewritten query
                retry_limit = top_k_context * 2
                retry_qv = embed_texts([rewritten_q], is_query=True)[0]
                rewritten_variations = _generate_query_variations(rewritten_q)
                
                retry_hits = {}
                try:
                    for rv in rewritten_variations:
                        rvv = embed_texts([rv], is_query=True)[0]
                        retry_res = search_collection(
                            collection_name=collection_name,
                            query_vector=rvv.tolist(),
                            limit=retry_limit,
                        )
                        for hit in retry_res:
                            eid = hit.payload.get("embedding_id")
                            if eid is not None:
                                eidi = int(eid)
                                if eidi not in retry_hits or hit.score > retry_hits[eidi]:
                                    retry_hits[eidi] = float(hit.score)
                except Exception as e:
                    print(f"[CRAG] Re-retrieval failed: {e}")
                
                if retry_hits:
                    sorted_retry = sorted(retry_hits.items(), key=lambda x: x[1], reverse=True)
                    retry_ids = [eid for eid, _ in sorted_retry]
                    retry_chunks = await chunks_col().find(
                        {"doc_id": project_id, "embedding_id": {"$in": retry_ids}}
                    ).to_list(length=len(retry_ids))
                    id_map = {c["embedding_id"]: c for c in retry_chunks}
                    retry_candidates = []
                    for eid in retry_ids:
                        if eid in id_map:
                            cd = id_map[eid]
                            retry_candidates.append({
                                "chunk_id": cd["chunk_id"],
                                "text": cd["text"],
                                "source_name": cd["filename"],
                                "url": cd.get("url"),
                                "page": cd.get("page", 1)
                            })
                    if retry_candidates:
                        retry_reranked = rerank_chunks(
                            query=rewritten_q,
                            chunks=retry_candidates,
                            top_k=top_k_context
                        )
                        if retry_reranked:
                            retry_high = 0
                            retry_medium = 0
                            if grade_chunks_relevance_batch:
                                try:
                                    rgrades = grade_chunks_relevance_batch(rewritten_q, [ch.get("text", "") for ch, _ in retry_reranked])
                                    for rg in rgrades:
                                        rel = rg.get("relevance")
                                        if rel == "high":
                                            retry_high += 1
                                        elif rel == "medium":
                                            retry_medium += 1
                                except Exception as batch_err:
                                    print(f"[CRAG Batch Retry] Error in batch relevance grading: {batch_err}. Falling back to sequential.")
                                    if grade_chunk_relevance:
                                        for ch, _ in retry_reranked:
                                            rgrade = grade_chunk_relevance(rewritten_q, ch.get("text", ""))
                                            rel = rgrade.get("relevance")
                                            if rel == "high":
                                                retry_high += 1
                                            elif rel == "medium":
                                                retry_medium += 1
                            elif grade_chunk_relevance:
                                for ch, _ in retry_reranked:
                                    rgrade = grade_chunk_relevance(rewritten_q, ch.get("text", ""))
                                    rel = rgrade.get("relevance")
                                    if rel == "high":
                                        retry_high += 1
                                    elif rel == "medium":
                                        retry_medium += 1
 
                            if (retry_high + retry_medium) > 0:
                                print(f"[CRAG] Retry succeeded: {retry_high} high, {retry_medium} medium relevance chunks")
                                reranked = retry_reranked
                            else:
                                print(f"[CRAG] Retry also low relevance. Abstaining.")
                                t_crag = time.perf_counter() - t_crag_start
                                return ChatResponse(
                                    answer="I couldn't find sufficiently relevant information for your question in the indexed pages. Please try rephrasing or asking a more specific question.",
                                    sources=[],
                                    grounded=False,
                                    doc_id=project_id,
                                    timestamp=datetime.utcnow()
                                )
                    else:
                        print(f"[CRAG] Re-retrieval returned no results. Proceeding with original.")
                else:
                    print(f"[CRAG] Re-retrieval returned no results. Proceeding with original.")
            else:
                print(f"[CRAG] Query rewrite failed. Proceeding with original results.")
        
        if crag_error:
            print(f"[CRAG] Initialization skipped: {crag_error}")
    t_crag = time.perf_counter() - t_crag_start
         
    # 5. Assemble context string — uses parent text, dedup, and token budget
    context = build_context_string(reranked, max_tokens=4000)
    
    # Prepend global project summary if available to provide top-down hierarchical context
    project_summary = project.get("summary", "") if project else ""
    if project_summary:
        context = f"[GLOBAL PROJECT SUMMARY]\n{project_summary}\n\n---\n\n" + context
    
    # 6. Retrieve conversation history memory
    memory = await get_memory(project_id, user_id)
    
    # 7. Generate answer via Groq
    t_gen_start = time.perf_counter()
    augmented_question = question
    route_instructions = []
    if is_comparison:
        route_instructions.append(
            "The user is requesting a comparison, trend, or multi-document synthesis. "
            "Synthesize and contrast facts across the different documents, sources, and pages. "
            "Structure your response with clear comparison sections, highlighting differences, similarities, and chronological timelines if applicable. "
            "Be sure to cite the specific sources (e.g., [Source Name] or [URL]) when referencing facts."
        )
    if prompt_hint:
        route_instructions.append(prompt_hint)

    if route_instructions:
        augmented_question = (
            f"{question}\n\n"
            f"[INSTRUCTION] {' '.join(route_instructions)}"
        )
    answer = generate(context=context, question=augmented_question, memory=memory)
    t_gen = time.perf_counter() - t_gen_start
    
    # 8. Verify answer support
    t_verify_start = time.perf_counter()
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
    t_verify = time.perf_counter() - t_verify_start
        
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
    t_db_start = time.perf_counter()
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
    t_db = time.perf_counter() - t_db_start
    
    t_total = time.perf_counter() - t_start
    print(f"[RAG LATENCY (Project)] Total: {t_total:.3f}s | Retrieval: {t_retrieval:.3f}s | Fusion: {t_fusion:.3f}s | MongoDB: {t_mongodb:.3f}s | Reranker: {t_rerank:.3f}s | CRAG: {t_crag:.3f}s | Gen: {t_gen:.3f}s | Verify: {t_verify:.3f}s | DB Write: {t_db:.3f}s")
    
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

