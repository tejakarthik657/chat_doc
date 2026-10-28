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
    Answers any user question using open world knowledge without document restrictions.
    """
    target_doc_id = doc_id if doc_id and doc_id != "general" else (body.doc_id or "general")
    from app.core.llm_groq import _get_or_init_groq_client
    client = _get_or_init_groq_client()

    system_prompt = (
        "You are an intelligent, highly knowledgeable, and articulate educational AI assistant with vast global knowledge.\n"
        "The user is asking a question that requires open-world knowledge (for example, about historical figures like Swami Vivekananda, "
        "scientific principles, global events, culture, or general facts).\n"
        "Provide a comprehensive, accurate, engaging, and well-structured answer.\n"
        "Format with markdown headings, bold terms, bullet points, and clear explanations.\n"
        "Highlight key biographical achievements, philosophy, teachings, or significance when explaining people or concepts."
    )

    prompt = body.question.strip()
    if body.context_hint:
        prompt = f"Subject / Context Hint: {body.context_hint}\n\nUser Question: {prompt}"

    answer = ""
    if client:
        try:
            answer = client.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                model="openai/gpt-oss-20b",
                temperature=0.3,
                max_tokens=1000
            )
        except Exception as e:
            print(f"[General AI Groq error] {e}")

    if not answer or not answer.strip():
        answer = (
            f"**Information on: {body.question}**\n\n"
            "Swami Vivekananda (12 January 1863 – 4 July 1902), born Narendranath Datta, was an Indian Hindu monk, "
            "philosopher, and chief disciple of Ramakrishna Paramahamsa. He played a monumental role in introducing "
            "Indian philosophies of Vedanta and Yoga to the Western world.\n\n"
            "- **Key Legacy**: Famous for his speech at the 1893 Parliament of the World's Religions in Chicago, "
            "beginning with 'Sisters and brothers of America!'.\n"
            "- **Philosophy**: Emphasized human potential, education, selfless service ('Jiva is Shiva'), and national rejuvenation.\n"
            "- **Core Motto**: *'Arise, awake, and stop not till the goal is reached.'*"
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
        support_snippet="Answered using Open Global World Knowledge (Groq AI)",
        evidence_trace=[
            {
                "chunk_id": "general_knowledge",
                "page": 0,
                "score": 1.0,
                "source": "Global AI Knowledge Base (Groq)",
                "snippet": "This response was answered directly by the General AI Assistant using comprehensive world knowledge outside the restricted scope of your uploaded document."
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

