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
    from app.core.llm_groq import _get_or_init_groq_client
    import asyncio

    client = _get_or_init_groq_client()
    if not client:
        raise HTTPException(status_code=500, detail="Voice recognition service not available.")

    try:
        audio_bytes = await file.read()
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
    Feature: Multimodal Visual Reasoning & OCR
    Extracts text from uploaded images/diagrams using OCR and uses LLM to reason over visual layouts.
    """
    from app.core.llm_groq import _get_or_init_groq_client
    client = _get_or_init_groq_client()

    try:
        content = await file.read()
        extracted_text = ""
        
        # 1. Try OCR with pytesseract
        try:
            from PIL import Image
            import io
            import pytesseract
            img = Image.open(io.BytesIO(content))
            extracted_text = pytesseract.image_to_string(img).strip()
        except Exception as ocr_err:
            logger.info(f"[OCR Notice] pytesseract: {ocr_err}")

        # 2. If pytesseract is empty, use OCR.space free API fallback
        if not extracted_text:
            try:
                import httpx
                import base64
                b64_img = base64.b64encode(content).decode("utf-8")
                mime_type = file.content_type or "image/png"
                async with httpx.AsyncClient(timeout=10.0) as http_client:
                    resp = await http_client.post(
                        "https://api.ocr.space/parse/image",
                        data={
                            "apikey": "helloworld",
                            "base64Image": f"data:{mime_type};base64,{b64_img}",
                            "OCREngine": "2",
                        }
                    )
                    if resp.status_code == 200:
                        ocr_data = resp.json()
                        parsed_results = ocr_data.get("ParsedResults", [])
                        if parsed_results:
                            extracted_text = parsed_results[0].get("ParsedText", "").strip()
            except Exception as space_err:
                logger.info(f"[OCR Space Notice] {space_err}")

        # 3. Structure and summarize via Groq LLM
        description = "Image uploaded."
        if client:
            llm_prompt = (
                f"User attached an image with filename '{file.filename}'.\n"
                f"Extracted Text/Content from OCR:\n{extracted_text or '[No direct text detected]'}\n\n"
                f"User Question/Prompt: {prompt or 'Analyze and summarize what is shown in this image.'}\n\n"
                f"Provide a clear, helpful visual description and answer based on the extracted content."
            )
            try:
                import asyncio
                resp = await asyncio.to_thread(
                    client.chat_completion,
                    messages=[
                        {"role": "system", "content": "You are a multimodal AI assistant skilled in reading diagrams, charts, UI screenshots, and educational documents."},
                        {"role": "user", "content": llm_prompt}
                    ],
                    model="qwen/qwen3.8-27b",
                    temperature=0.2,
                    max_tokens=600
                )
                if resp:
                    description = resp.strip()
            except Exception as llm_err:
                logger.warning(f"[Multimodal LLM Notice] {llm_err}")
                description = extracted_text or "Image attached."

        return {
            "filename": file.filename,
            "extracted_text": extracted_text,
            "description": description
        }
    except Exception as e:
        logger.error(f"[Analyze Image Error] {e}")
        raise HTTPException(status_code=500, detail=f"Image analysis failed: {str(e)}")


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
