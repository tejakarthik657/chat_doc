from fastapi import APIRouter, Depends, HTTPException

from app.core.security import get_current_user
from app.core.feature_models import (
    extract_entities,
    extract_keyphrases,
    classify_document_type,
    summarize_document,
    detect_outlier_sections,
    verify_answer_support,
    rewrite_plain_language,
)
from app.db.mongodb import documents_col, chunks_col
from app.models.schemas import (
    DocumentInsightsResponse,
    VerifyAnswerRequest,
    VerifyAnswerResponse,
    RewriteRequest,
    RewriteResponse,
)

router = APIRouter(prefix="/api/features", tags=["features"])


async def _load_document_text(doc_id: str, user_id: str) -> tuple[dict, list[dict], str]:
    doc = await documents_col().find_one({"_id": doc_id, "user_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if doc.get("status") != "ready":
        raise HTTPException(status_code=400, detail=f"Document is not ready (status: {doc.get('status')}).")

    chunks = await chunks_col().find({"doc_id": doc_id}).sort([("page", 1), ("embedding_id", 1)]).to_list(length=5000)
    if not chunks:
        raise HTTPException(status_code=404, detail="No chunks found for this document.")

    full_text = "\n\n".join(c.get("text", "") for c in chunks)
    return doc, chunks, full_text


@router.get("/{doc_id}/insights", response_model=DocumentInsightsResponse)
async def get_document_insights(doc_id: str, user_id: str = Depends(get_current_user)):
    doc, chunks, full_text = await _load_document_text(doc_id, user_id)
    text_for_analysis = full_text[:40000]

    summary = summarize_document(text_for_analysis, max_sentences=5)
    keyphrases = extract_keyphrases(text_for_analysis, top_k=12)
    entities = extract_entities(text_for_analysis)
    doc_type = classify_document_type(text_for_analysis)
    outliers = detect_outlier_sections(text_for_analysis, top_k=3)

    # Simple readability estimate from average sentence length.
    words = text_for_analysis.split()
    sentences = max(1, len([s for s in summary.split(".") if s.strip()]))
    avg_sentence_len = len(words) / max(1, sentences)
    if avg_sentence_len < 14:
        readability_band = "easy"
    elif avg_sentence_len < 20:
        readability_band = "medium"
    else:
        readability_band = "advanced"

    suggested_questions = [
        f"Can you summarize the key idea behind '{k}'?" for k in keyphrases[:3]
    ]

    return DocumentInsightsResponse(
        doc_id=doc_id,
        filename=doc.get("filename", "Unknown"),
        document_type=doc_type["label"],
        document_type_confidence=doc_type["confidence"],
        summary=summary,
        keyphrases=keyphrases,
        entities=entities,
        readability_band=readability_band,
        outlier_sections=outliers,
        suggested_questions=suggested_questions,
    )


@router.post("/{doc_id}/verify", response_model=VerifyAnswerResponse)
async def verify_answer(doc_id: str, body: VerifyAnswerRequest, user_id: str = Depends(get_current_user)):
    _, chunks, _ = await _load_document_text(doc_id, user_id)
    snippets = [c.get("text", "") for c in chunks[:80]]
    verdict = verify_answer_support(body.answer, snippets)

    return VerifyAnswerResponse(
        label=verdict["label"],
        confidence=verdict["confidence"],
        best_snippet=verdict["best_snippet"],
    )


@router.post("/rewrite", response_model=RewriteResponse)
async def rewrite_text(body: RewriteRequest, user_id: str = Depends(get_current_user)):
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    max_sentences = 5 if body.style == "professional" else 4
    rewritten = rewrite_plain_language(body.text, max_sentences=max_sentences)

    if body.style == "professional":
        rewritten = rewritten.replace("you", "the reader")

    return RewriteResponse(rewritten_text=rewritten)
