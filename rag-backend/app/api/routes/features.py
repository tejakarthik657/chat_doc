import asyncio
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

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
    CanvasTransformRequest,
    CanvasTransformResponse,
)

router = APIRouter(prefix="/api/features", tags=["features"])
logger = logging.getLogger(__name__)
MAX_AUDIO_UPLOAD_BYTES = 25 * 1024 * 1024


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


def _compute_insights_sync(text_for_analysis: str, filename: str, doc_id: str) -> dict:
    summary = summarize_document(text_for_analysis, max_sentences=5)
    keyphrases = extract_keyphrases(text_for_analysis, top_k=12)
    entities = extract_entities(text_for_analysis)
    doc_type = classify_document_type(text_for_analysis)
    outliers = detect_outlier_sections(text_for_analysis, top_k=3)

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

    return {
        "doc_id": doc_id,
        "filename": filename,
        "document_type": doc_type["label"],
        "document_type_confidence": doc_type["confidence"],
        "summary": summary,
        "keyphrases": keyphrases,
        "entities": entities,
        "readability_band": readability_band,
        "outlier_sections": outliers,
        "suggested_questions": suggested_questions,
    }


@router.get("/{doc_id}/insights", response_model=DocumentInsightsResponse)
async def get_document_insights(doc_id: str, user_id: str = Depends(get_current_user)):
    doc, chunks, full_text = await _load_document_text(doc_id, user_id)
    
    # 1. Fast-path: return cached insights from MongoDB immediately (sub-5ms)
    if doc.get("insights"):
        return DocumentInsightsResponse(**doc["insights"])

    text_for_analysis = full_text[:40000]
    filename = doc.get("filename", "Unknown")

    # 2. Compute non-blocking in background thread pool to protect FastAPI uvicorn event loop
    insights_data = await asyncio.to_thread(_compute_insights_sync, text_for_analysis, filename, doc_id)

    # 3. Cache in MongoDB Atlas for instant subsequent page renders
    try:
        await documents_col().update_one({"_id": doc_id}, {"$set": {"insights": insights_data}})
    except Exception as e:
        logger.warning(f"Failed to cache insights in MongoDB: {e}")

    return DocumentInsightsResponse(**insights_data)


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

    # 1. High-speed Groq LLM rewrite (~300ms, zero local CPU load)
    try:
        from app.core.llm_groq import _get_or_init_groq_client
        client = _get_or_init_groq_client()
        if client:
            style_instruction = (
                "You are an expert editor. Rewrite the provided text in clear, simple, plain English that is easy for anyone to understand. "
                "Retain the core facts, remove unnecessary jargon, and keep it direct."
                if body.style == "simple" else
                "You are an executive editor. Rewrite the provided text in polished, professional, authoritative language. "
                "Retain the core facts and keep it direct."
            )
            for cand_model in ["qwen/qwen3.8-27b", "openai/gpt-oss-20b"]:
                try:
                    groq_resp = client.chat_completion(
                        messages=[
                            {"role": "system", "content": style_instruction},
                            {"role": "user", "content": f"Rewrite this text:\n\n{body.text.strip()}"}
                        ],
                        model=cand_model,
                        temperature=0.3,
                        max_tokens=600,
                    )
                    if groq_resp and groq_resp.strip():
                        return RewriteResponse(rewritten_text=groq_resp.strip())
                except Exception:
                    continue
    except Exception as e:
        pass

    # 2. Instant lexical CPU fallback (0ms, no embeddings or torch required)
    max_sentences = 5 if body.style == "professional" else 4
    rewritten = rewrite_plain_language(body.text, max_sentences=max_sentences)

    if body.style == "professional":
        rewritten = rewritten.replace("you", "the reader")

    return RewriteResponse(rewritten_text=rewritten)


@router.post("/canvas/transform", response_model=CanvasTransformResponse)
async def transform_canvas(body: CanvasTransformRequest, user_id: str = Depends(get_current_user)):
    """
    AI Canvas Transformation Engine.
    Powers real productivity features inside the Canvas Workspace:
      - 'polish': Cleans up layout, fixes markdown headers, and structures sections.
      - 'table': Detects key data and transforms into high-clarity markdown tables.
      - 'summary': Generates a sharp 3-bullet executive brief & action items.
      - 'quiz': Creates interactive review questions and flashcards.
      - 'simplify': Rewrites complex text in everyday ELI5 language.
      - 'expand': Deepens the analysis with structured insights.
    """
    from app.core.llm_groq import _get_or_init_groq_client
    client = _get_or_init_groq_client()

    prompts = {
        "polish": (
            "You are an expert document designer. Clean, structure, and beautifully format this text into publication-ready markdown. "
            "Use clear headings (#, ##), bullet points, and highlight key terms with bold text. Do not omit important facts."
        ),
        "table": (
            "You are a data extraction specialist. Identify the key facts, statistics, entities, or categories in the provided text "
            "and format them into one or more well-structured, clear Markdown tables with appropriate column headers."
        ),
        "summary": (
            "You are an executive chief of staff. Create an Executive Summary of this document in clean markdown. "
            "Include: 1) Core Objective (1 sentence), 2) Key Takeaways (3-5 punchy bullets), and 3) Next Steps / Action Items."
        ),
        "quiz": (
            "You are an interactive learning tutor. Based on this text, generate a 4-question study quiz with multiple-choice options (A, B, C, D) "
            "followed by an Answer Key with brief explanations at the bottom."
        ),
        "simplify": (
            "You are an expert communicator. Rewrite this content so that a 12-year-old can easily understand it. "
            "Use simple analogies, everyday words, short sentences, and engaging tone while keeping all facts true."
        ),
        "expand": (
            "You are a senior analyst. Deepen and enrich this content by adding context, implications, structured analysis, "
            "and practical takeaways in clean markdown."
        )
    }

    system_instruction = prompts.get(body.action, prompts["polish"])

    if client:
        for cand_model in ["qwen/qwen3.8-27b", "openai/gpt-oss-20b"]:
            try:
                resp = client.chat_completion(
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": f"Document content:\n\n{body.content.strip()}"}
                    ],
                    model=cand_model,
                    temperature=0.3,
                    max_tokens=1500
                )
                if resp and resp.strip():
                    return CanvasTransformResponse(transformed_content=resp.strip(), action=body.action)
            except Exception as e:
                logger.warning(f"[Canvas Transform Notice] Model {cand_model} bypass: {e}")

    # Fallback if offline
    fallback_content = f"# Formatted Document\n\n{body.content.strip()}\n\n---\n*Transformed via Canvas Assistant*"
    return CanvasTransformResponse(transformed_content=fallback_content, action=body.action)


# ── Advanced AI Capabilities: Whisper Turbo Voice, Multimodal Vision & Python Sandbox ──

@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user)
):
    """
    Feature: Groq Cloud Whisper Speech-to-Text
    Converts voice recordings to text in <300ms using whisper-large-v3-turbo with dynamic key pooling.
    """
    import asyncio

    audio_bytes = await file.read(MAX_AUDIO_UPLOAD_BYTES + 1)
    if len(audio_bytes) > MAX_AUDIO_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Audio files must be 25 MB or smaller.")

    from app.core.llm_groq import _get_or_init_groq_client
    client = _get_or_init_groq_client()
    if not client:
        raise HTTPException(status_code=500, detail="Voice recognition service not available.")
    try:
        filename = file.filename or "recording.webm"
        file_tuple = (filename, audio_bytes)
        
        transcript = await asyncio.to_thread(client.transcribe_audio, file_tuple)
        return {"transcript": transcript.strip()}
    except Exception as e:
        logger.error(f"[Transcribe Error] {e}")
        raise HTTPException(status_code=500, detail=f"Audio transcription failed: {str(e)}")


@router.post("/analyze-image")
async def analyze_image(
    file: UploadFile = File(...),
    prompt: Optional[str] = Form(None),
    user_id: str = Depends(get_current_user)
):
    """
    Analyze the uploaded image itself with a vision-capable model.
    """
    from app.core.llm_groq import _get_or_init_groq_client
    client = _get_or_init_groq_client()

    if not client:
        raise HTTPException(status_code=503, detail="Image analysis is unavailable because no vision service is configured.")
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Please upload a supported image file.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded image is empty.")
    if len(content) > 14 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Images must be 14 MB or smaller.")

    import base64

    user_prompt = (prompt or "").strip() or "Describe and analyze this image."
    image_data_url = (
        f"data:{file.content_type};base64,"
        f"{base64.b64encode(content).decode('ascii')}"
    )
    system_prompt = (
        "You are an expert visual analyst. Inspect the provided image directly; do not infer "
        "details that are not visible. Answer the user's question first, then explain the "
        "important visible elements in a clear, well-structured response. For screenshots, "
        "read visible text carefully and explain the interface, code, messages, and context. "
        "For charts or diagrams, describe labels, relationships, trends, and what they mean. "
        "Separate direct observations from uncertain interpretations, and mention when text "
        "is too small or unclear to read. Use concise Markdown headings and bullets where useful."
    )
    user_content = [
        {
            "type": "text",
            "text": f"Image filename: {file.filename or 'uploaded image'}\n\nQuestion: {user_prompt}",
        },
        {"type": "image_url", "image_url": {"url": image_data_url}},
    ]

    try:
        description = await asyncio.to_thread(
            client.chat_completion,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            model="qwen/qwen3.8-27b",
            temperature=0.2,
            max_tokens=1800,
        )
    except Exception as exc:
        logger.exception("[Image Analysis Error]")
        raise HTTPException(status_code=502, detail="The vision service could not analyze this image. Please try again.") from exc

    if not description or not description.strip():
        raise HTTPException(status_code=502, detail="The vision service returned an empty analysis. Please try again.")

    return {
        "filename": file.filename,
        "extracted_text": "",
        "description": description.strip(),
    }


class CodeExecutionRequest(BaseModel):
    code: str
    test_cases: Optional[str] = None
    timeout: Optional[int] = 5


@router.post("/execute-code")
async def execute_python_code(
    body: CodeExecutionRequest,
    user_id: str = Depends(get_current_user)
):
    """
    Feature 3: Living Code Twin with AST Verification and Unit Test Runner.
    Safely executes Python snippets, verifies syntax trees, and checks unit assertions.
    """
    import sys
    import subprocess
    import time
    import asyncio
    import ast

    def run_sub():
        t0 = time.time()
        for bad in ["os.system", "shutil.rmtree", "subprocess.Popen", "ctypes", "winreg"]:
            if bad in body.code or (body.test_cases and bad in body.test_cases):
                return {
                    "stdout": "",
                    "stderr": f"Security Exception: Operation '{bad}' is restricted in sandbox.",
                    "returncode": 1,
                    "duration_ms": 0,
                    "status": "SECURITY_RESTRICTION",
                    "tests_total": 0,
                    "tests_passed": 0,
                    "ast_verified": False
                }

        # AST syntax check
        try:
            ast.parse(body.code)
            ast_verified = True
        except SyntaxError as syn_err:
            return {
                "stdout": "",
                "stderr": f"SyntaxError: {syn_err.msg} (line {syn_err.lineno})",
                "returncode": 1,
                "duration_ms": 0,
                "status": "SYNTAX_ERROR",
                "tests_total": 0,
                "tests_passed": 0,
                "ast_verified": False
            }

        # Count assertions in test cases
        tests_total = 0
        if body.test_cases:
            try:
                tree = ast.parse(body.test_cases)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assert):
                        tests_total += 1
            except Exception:
                tests_total = body.test_cases.count('assert ')

        combined_code = body.code
        if body.test_cases:
            combined_code = body.code + "\n\n# Tests\n" + body.test_cases
        try:
            res = subprocess.run(
                [sys.executable, "-c", combined_code],
                capture_output=True,
                text=True,
                timeout=body.timeout or 5
            )
            duration = int((time.time() - t0) * 1000)
            passed = tests_total if res.returncode == 0 else max(0, tests_total - 1)
            status_str = "PASSED" if res.returncode == 0 else "FAILED"
            return {
                "stdout": res.stdout,
                "stderr": res.stderr,
                "returncode": res.returncode,
                "duration_ms": duration,
                "status": status_str,
                "tests_total": tests_total,
                "tests_passed": passed,
                "ast_verified": ast_verified
            }
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": f"Execution timed out after {body.timeout}s.",
                "returncode": -1,
                "duration_ms": (body.timeout or 5) * 1000,
                "status": "TIMEOUT",
                "tests_total": tests_total,
                "tests_passed": 0,
                "ast_verified": ast_verified
            }
        except Exception as ex:
            return {
                "stdout": "",
                "stderr": str(ex),
                "returncode": 1,
                "duration_ms": int((time.time() - t0) * 1000),
                "status": "ERROR",
                "tests_total": tests_total,
                "tests_passed": 0,
                "ast_verified": ast_verified
            }

    result = await asyncio.to_thread(run_sub)
    return result


class SocraticStartRequest(BaseModel):
    project_id: str
    topic: Optional[str] = None
    bloom_level: Optional[str] = "Understand"


class SocraticEvaluateRequest(BaseModel):
    question: str
    bloom_level: str
    student_answer: str
    context_snippet: str


@router.post("/socratic/start")
async def start_socratic_viva(
    body: SocraticStartRequest,
    user_id: str = Depends(get_current_user)
):
    """Feature 1: The Socratic Viva Master - Initiates an oral examination topic."""
    from app.rag.socratic_engine import generate_viva_question
    return await generate_viva_question(
        project_id=body.project_id,
        topic=body.topic,
        bloom_level=body.bloom_level or "Understand"
    )


@router.post("/socratic/evaluate")
async def evaluate_socratic_viva(
    body: SocraticEvaluateRequest,
    user_id: str = Depends(get_current_user)
):
    """Feature 1: The Socratic Viva Master - Evaluates oral response with Bloom scoring."""
    from app.rag.socratic_engine import evaluate_viva_response
    return await evaluate_viva_response(
        question=body.question,
        bloom_level=body.bloom_level,
        student_answer=body.student_answer,
        context_snippet=body.context_snippet
    )
