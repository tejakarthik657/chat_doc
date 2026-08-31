"""
CRAG — Corrective / Self-Reflective RAG
─────────────────────────────────────────
After retrieval + reranking, grades whether the retrieved chunks actually
answer the user's question. If confidence is low, triggers query rewrite
and re-retrieval. If still low after retry, abstains (returns "not found").

Flow:
  Retrieval + Rerank
    │
    ▼
  Relevance Grader (LLM)
    │
    ├── High confidence → proceed to LLM answer
    │
    ├── Low confidence → rewrite query → re-retrieve → regrade
    │                          │
    │                          ├── High → proceed
    │                          └── Low  → "not found"
    │
    └── Grader fails (no API) → proceed (always allows)
"""
from groq import Groq
from app.core.config import get_settings

settings = get_settings()

_RELEVANCE_PROMPT = """You are a strict relevance grader for a RAG system.
Given a user question and a retrieved text excerpt, rate whether the excerpt
contains information that DIRECTLY helps answer the question.

Respond with ONLY a JSON object:
{"relevance": "high"|"medium"|"low", "reason": "brief explanation"}

Rules:
- "high": the excerpt directly answers the question or contains the specific fact requested.
- "medium": the excerpt is related but missing key details (e.g., talks about faculty but not the specific person asked about).
- "low": the excerpt is about the wrong topic entirely, or is just navigation/boilerplate.

Question: {question}

Retrieved excerpt:
---
{excerpt}
---

JSON response:"""


_BATCH_RELEVANCE_PROMPT = """You are a strict relevance grader for a RAG system.
Given a user question and a list of retrieved text excerpts, rate whether each excerpt
contains information that DIRECTLY helps answer the question.

You must respond with ONLY a JSON object containing a list under the key "results".
Each item in the "results" list must be a JSON object with:
- "index": integer representing the 0-based index of the excerpt
- "relevance": "high", "medium", or "low"
- "reason": a brief explanation (max 10 words)

Rules:
- "high": the excerpt directly answers the question or contains the specific fact requested.
- "medium": the excerpt is related but missing key details (e.g., talks about the general topic but not the specific detail asked about).
- "low": the excerpt is about the wrong topic entirely, or is just navigation/boilerplate.

Question: {question}

Retrieved excerpts:
{excerpts_formatted}

JSON response:"""


def _grade_chunk_relevance_local(question: str, excerpt: str) -> dict:
    try:
        from app.core.llm import generate_raw
        import json, re
        prompt = _RELEVANCE_PROMPT.format(question=question, excerpt=excerpt[:800])
        full_prompt = f"<|system|>\nYou are a strict relevance grader. Grader output must be JSON format ONLY.</s>\n<|user|>\n{prompt}</s>\n<|assistant|>\n"
        content = generate_raw(full_prompt)
        json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return {
                "relevance": result.get("relevance", "medium"),
                "reason": result.get("reason", "")
            }
        return {"relevance": "medium", "reason": "parse_failed"}
    except Exception as e:
        return {"relevance": "medium", "reason": f"local_error: {str(e)[:50]}"}


def _rewrite_query_local(question: str) -> str:
    try:
        from app.core.llm import generate_raw
        prompt = (
            "Rewrite the following question to be more specific and keyword-rich "
            "for a document search system. Add specific terms that would appear in "
            "college documents. Keep it concise (under 20 words).\n\n"
            f"Original: {question}\n\nRewritten:"
        )
        full_prompt = f"<|system|>\nYou are a search query optimizer. Output ONLY the rewritten question.</s>\n<|user|>\n{prompt}</s>\n<|assistant|>\n"
        rewritten = generate_raw(full_prompt)
        if len(rewritten) > 10 and "?" in rewritten or len(rewritten.split()) >= 3:
            return rewritten
        return question
    except Exception:
        return question


def grade_chunk_relevance(question: str, excerpt: str) -> dict:
    """
    Grade a single chunk's relevance to the query using Groq.
    Returns {"relevance": str, "reason": str} or fallback dict.
    """
    api_key = settings.groq_api_key
    if not api_key:
        return _grade_chunk_relevance_local(question, excerpt)

    try:
        client = Groq(api_key=api_key)
        prompt = _RELEVANCE_PROMPT.format(question=question, excerpt=excerpt[:800])

        response = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=60,
        )

        import json, re
        content = response.choices[0].message.content.strip()
        json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return {
                "relevance": result.get("relevance", "medium"),
                "reason": result.get("reason", "")
            }
        return {"relevance": "medium", "reason": "parse_failed"}
    except Exception as e:
        return _grade_chunk_relevance_local(question, excerpt)


def _grade_chunks_relevance_local_batch(question: str, excerpts: list[str]) -> list[dict]:
    """
    Local LLM fallback for batch relevance grading.
    """
    # Since TinyLlama is tiny and CPU-based, it's safer and less error-prone to grade individually
    # to avoid JSON parsing issues on large batch prompts.
    return [grade_chunk_relevance(question, exc) for exc in excerpts]


def grade_chunks_relevance_batch(question: str, excerpts: list[str]) -> list[dict]:
    """
    Grade multiple chunks' relevance to the query in a single API call (batch) using Groq.
    Returns a list of dicts: [{"relevance": str, "reason": str}, ...] matching the inputs.
    """
    if not excerpts:
        return []

    api_key = settings.groq_api_key
    if not api_key:
        return _grade_chunks_relevance_local_batch(question, excerpts)

    try:
        client = Groq(api_key=api_key)
        
        # Format the excerpts
        excerpts_formatted = ""
        for i, exc in enumerate(excerpts):
            excerpts_formatted += f"Excerpt {i}:\n---\n{exc[:800]}\n---\n\n"

        prompt = _BATCH_RELEVANCE_PROMPT.format(question=question, excerpts_formatted=excerpts_formatted)

        response = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"},
            max_tokens=600,
        )

        import json, re
        content = response.choices[0].message.content.strip()
        result = json.loads(content)
        results_list = result.get("results", [])
        
        # Map the results to their respective indices
        grades = [{"relevance": "low", "reason": "batch_missing"} for _ in range(len(excerpts))]
        for item in results_list:
            idx = item.get("index")
            if idx is not None and 0 <= idx < len(excerpts):
                grades[idx] = {
                    "relevance": item.get("relevance", "low"),
                    "reason": item.get("reason", "")
                }
        
        # Verify if any index was not successfully graded, and fallback to individual grading for those
        for i, grade in enumerate(grades):
            if grade["reason"] == "batch_missing":
                print(f"[CRAG Batch] Index {i} missing from batch response. Falling back to individual grading.")
                grades[i] = grade_chunk_relevance(question, excerpts[i])
                
        return grades
    except Exception as e:
        print(f"[CRAG Batch] Batch grading failed: {e}. Falling back to individual grading.")
        # Fallback: grade individually
        return [grade_chunk_relevance(question, exc) for exc in excerpts]


def rewrite_query(question: str) -> str:
    """
    Rewrite a vague or failed query into a more specific one.
    Uses Groq to rephrase with more keywords/detail.
    """
    api_key = settings.groq_api_key
    if not api_key:
        return _rewrite_query_local(question)

    try:
        client = Groq(api_key=api_key)
        prompt = (
            "Rewrite the following question to be more specific and keyword-rich "
            "for a document search system. Add specific terms that would appear in "
            "college documents. Keep it concise (under 20 words).\n\n"
            f"Original: {question}\n\nRewritten:"
        )
        response = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=60,
        )
        rewritten = response.choices[0].message.content.strip()
        if len(rewritten) > 10 and "?" in rewritten or len(rewritten.split()) >= 3:
            return rewritten
        return question
    except Exception:
        return _rewrite_query_local(question)


def should_retry(question: str, chunks: list[dict], threshold: str = "medium") -> bool:
    """
    Decide if retrieval should be retried based on relevance grading.
    Returns True if retry is needed.
    """
    if not chunks:
        return True

    high = 0
    medium = 0
    low = 0

    for chunk in chunks[:5]:
        grade = grade_chunk_relevance(question, chunk.get("text", ""))
        rel = grade.get("relevance", "low")
        if rel == "high":
            high += 1
        elif rel == "medium":
            medium += 1
        else:
            low += 1

    total = len(chunks[:5])
    if total == 0:
        return True

    if low / total > 0.6:
        return True
    if threshold == "high" and (high / total) < 0.4:
        return True

    return False
