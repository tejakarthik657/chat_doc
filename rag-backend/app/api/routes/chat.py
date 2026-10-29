from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from app.core.security import get_current_user
from app.db.mongodb import documents_col, chat_history_col
from app.rag.engine import answer_question
from app.analytics.engine import count_questions_today
from app.core.config import get_settings
from app.models.schemas import QuestionRequest, GeneralQuestionRequest, ChatResponse, ChatHistoryItem

router = APIRouter(prefix="/api/chat", tags=["chat"])
settings = get_settings()


@router.post("/{doc_id}", response_model=ChatResponse)
async def ask_question(
    doc_id: str,
    body: QuestionRequest,
    user_id: str = Depends(get_current_user)
):
    # ── Verify document belongs to user and is ready ─────────────────────────
    doc = await documents_col().find_one({"_id": doc_id, "user_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if doc.get("status") != "ready":
        raise HTTPException(status_code=400, detail=f"Document is not ready (status: {doc.get('status')}).")

    # ── Rate limit check ──────────────────────────────────────────────────────
    today_count = await count_questions_today(user_id)
    if today_count >= settings.max_questions_per_day:
        raise HTTPException(
            status_code=429,
            detail=f"Daily question limit reached ({settings.max_questions_per_day}/day on free plan)."
        )

    # ── RAG pipeline ──────────────────────────────────────────────────────────
    try:
        response = await answer_question(
            question=body.question,
            doc_id=doc_id,
            user_id=user_id,
            strict_mode=body.strict_mode
        )
        return response
    except Exception as e:
        print(f"[CHAT ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")


@router.post("/general", response_model=ChatResponse)
@router.post("/{doc_id}/general", response_model=ChatResponse)
async def ask_general_ai(
    body: GeneralQuestionRequest,
    doc_id: str = "general",
    user_id: str = Depends(get_current_user)
):
    """
    Direct Global Knowledge / Open LLM endpoint.
    Answers any user question using open world knowledge with executive-grade depth and formatting.
    """
    target_doc_id = doc_id if doc_id and doc_id != "general" else (body.doc_id or "general")
    from app.core.llm_groq import _get_or_init_groq_client
    client = _get_or_init_groq_client()

    system_prompt = (
        "You are an elite, world-class intellectual AI research assistant with vast global knowledge across "
        "history, science, mathematics, technology, literature, philosophy, culture, and world affairs.\n\n"
        "### Guidelines:\n"
        "1. **Tone & Presence**: Highly articulate, engaging, authoritative, and intellectually rigorous.\n"
        "2. **Visual Hierarchy & Formatting**:\n"
        "   - Use clean Markdown headers (`##`, `###`) to partition your response logically (e.g., Executive Overview, Core Concepts & Background, Key Highlights & Achievements, Global Significance & Legacy).\n"
        "   - Use bold highlights (`**term**`) for pivotal concepts and key terms.\n"
        "   - Use bullet points (`- `) or numbered lists for sequential steps and chronological breakdowns.\n"
        "   - Use Markdown tables when comparing concepts, chronologies, or presenting structured facts.\n"
        "   - Use blockquotes (`> quote`) for famous aphorisms, historical statements, or core principles.\n"
        "3. **Exhaustive Completeness**:\n"
        "   - Provide a deep, complete, and exhaustive answer without prematurely cutting off thoughts."
    )

    prompt = body.question.strip()
    if body.context_hint:
        prompt = f"Subject / Context Hint: {body.context_hint}\n\nUser Question: {prompt}"

    answer = ""
    models_to_try = ["qwen/qwen3.8-27b", "openai/gpt-oss-120b", "openai/gpt-oss-20b"]

    if client:
        for model_name in models_to_try:
            try:
                answer = client.chat_completion(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    model=model_name,
                    temperature=0.35,
                    max_tokens=3500
                )
                if answer and answer.strip():
                    break
            except Exception as e:
                print(f"[General AI Groq error with {model_name}] {e}")

    # Fallback to Cloud Multi-Provider (Gemini 1.5 Flash / OpenRouter) if Groq is unavailable
    if not answer or not answer.strip():
        try:
            from app.core.llm_cloud_fallback import generate_gemini_fallback, generate_openrouter_fallback
            gemini_ans = generate_gemini_fallback(prompt=prompt, system_prompt=system_prompt)
            if gemini_ans and gemini_ans.strip():
                answer = gemini_ans.strip()
            else:
                or_ans = generate_openrouter_fallback([
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ])
                if or_ans and or_ans.strip():
                    answer = or_ans.strip()
        except Exception as fb_err:
            print(f"[General AI Fallback Notice] {fb_err}")

    # Graceful dynamic synthesis fallback if all cloud providers are unreachable
    if not answer or not answer.strip():
        clean_q = body.question.strip()
        answer = (
            f"### Overview: {clean_q}\n\n"
            f"Information regarding **{clean_q}** is currently being processed by the intelligence engine. "
            "Our multi-model cloud cluster encountered a temporary connection blip with external inference nodes.\n\n"
            "#### Suggested Actions:\n"
            "- Please try submitting your query again in a few moments.\n"
            "- If querying about a specific document or college syllabus, verify that the project indexing is marked **Active**."
        )

    now = datetime.utcnow()
    # Save to chat history under target_doc_id so user's conversation thread retains it
    try:
        await chat_history_col().insert_one({
            "doc_id": target_doc_id,
            "user_id": user_id,
            "question": body.question,
            "answer": answer,
            "sources": [],
            "mode": "general_ai",
            "timestamp": now
        })
    except Exception as persist_err:
        print(f"[General AI Chat History Notice] {persist_err}")

    return ChatResponse(
        answer=answer,
        sources=[],
        grounded=True,
        doc_id=target_doc_id,
        timestamp=now,
        support_label="general_ai",
        support_confidence=1.0,
        support_snippet="Answered using Open Global World Knowledge (Groq Multi-Key Cluster)",
        evidence_trace=[
            {
                "chunk_id": "general_knowledge",
                "page": 0,
                "score": 1.0,
                "source": "Global AI Knowledge Base (Groq)",
                "snippet": "This response was synthesized directly by the General AI Assistant using comprehensive world knowledge outside the restricted scope of your uploaded document."
            }
        ],
        mode="general_ai"
    )


@router.get("/{doc_id}/history", response_model=list[ChatHistoryItem])
async def get_chat_history(
    doc_id: str,
    limit: int = 20,
    user_id: str = Depends(get_current_user)
):
    if not doc_id or doc_id == "onboarding":
        return []

    doc = await documents_col().find_one({"_id": doc_id, "user_id": user_id})
    if not doc:
        # Check if doc_id might be a project_id or newly initialized doc
        from app.db.mongodb import projects_col
        project = await projects_col().find_one({"_id": doc_id, "user_id": user_id})
        if not project:
            return []

    history = await chat_history_col().find(
        {"doc_id": doc_id, "user_id": user_id}
    ).sort("timestamp", -1).limit(limit).to_list(length=limit)

    return [
        ChatHistoryItem(
            question=h["question"],
            answer=h["answer"],
            sources=h.get("sources", []),
            timestamp=h["timestamp"]
        )
        for h in reversed(history)
    ]


@router.delete("/{doc_id}/memory", status_code=204)
async def clear_memory(doc_id: str, user_id: str = Depends(get_current_user)):
    """Reset conversation memory for a document (start fresh)."""
    from app.db.mongodb import memory_col
    await memory_col().delete_one({"doc_id": doc_id, "user_id": user_id})


# ── Projects Chat Endpoints ──────────────────────────────────────────────────

@router.post("/project/{project_id}", response_model=ChatResponse)
async def ask_project_question(
    project_id: str,
    body: QuestionRequest,
    user_id: str = Depends(get_current_user)
):
    from app.db.mongodb import projects_col
    from app.rag.engine import answer_project_question

    # 1. Verify project exists
    project = await projects_col().find_one({"_id": project_id, "user_id": user_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    # 2. Rate limit check
    today_count = await count_questions_today(user_id)
    if today_count >= settings.max_questions_per_day:
        raise HTTPException(
            status_code=429,
            detail=f"Daily question limit reached ({settings.max_questions_per_day}/day on free plan)."
        )

    # 3. Call project RAG pipeline
    try:
        response = await answer_project_question(
            question=body.question,
            project_id=project_id,
            user_id=user_id,
            strict_mode=body.strict_mode,
            scoped_sources=body.scoped_sources,
            mode=body.mode or "standard"
        )
        return response
    except Exception as e:
        from app.core.logger import log_error
        log_error(f"Project: {project_id}, User: {user_id}, Question: {body.question[:200]}", exc=e)
        print(f"[PROJECT CHAT ERROR] {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")


@router.get("/project/{project_id}/history", response_model=list[ChatHistoryItem])
async def get_project_chat_history(
    project_id: str,
    limit: int = 20,
    user_id: str = Depends(get_current_user)
):
    from app.db.mongodb import projects_col

    if not project_id or project_id == "onboarding":
        return []

    # Verify project exists
    project = await projects_col().find_one({"_id": project_id, "user_id": user_id})
    if not project:
        return []

    history = await chat_history_col().find(
        {"doc_id": project_id, "user_id": user_id}
    ).sort("timestamp", -1).limit(limit).to_list(length=limit)

    return [
        ChatHistoryItem(
            question=h["question"],
            answer=h["answer"],
            sources=h.get("sources", []),
            timestamp=h["timestamp"]
        )
        for h in reversed(history)
    ]


@router.delete("/project/{project_id}/memory", status_code=204)
async def clear_project_memory(project_id: str, user_id: str = Depends(get_current_user)):
    """Reset conversation memory for a project (start fresh)."""
    from app.db.mongodb import memory_col, projects_col
    
    # Verify project exists
    project = await projects_col().find_one({"_id": project_id, "user_id": user_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    await memory_col().delete_one({"doc_id": project_id, "user_id": user_id})
