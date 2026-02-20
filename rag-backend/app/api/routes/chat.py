from fastapi import APIRouter, Depends, HTTPException
from app.core.security import get_current_user
from app.db.mongodb import documents_col, chat_history_col
from app.rag.engine import answer_question
from app.analytics.engine import count_questions_today
from app.core.config import get_settings
from app.models.schemas import QuestionRequest, ChatResponse, ChatHistoryItem

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
            user_id=user_id
        )
        return response
    except Exception as e:
        print(f"[CHAT ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")


@router.get("/{doc_id}/history", response_model=list[ChatHistoryItem])
async def get_chat_history(
    doc_id: str,
    limit: int = 20,
    user_id: str = Depends(get_current_user)
):
    doc = await documents_col().find_one({"_id": doc_id, "user_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

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
