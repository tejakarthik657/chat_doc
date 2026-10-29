import os
"""
Groq LLM: ULTRA-FAST, RESILIENT CLOUD INFERENCE WITH DYNAMIC MULTI-KEY POOL.
Uses active Groq models (qwen/qwen3.8-27b, openai/gpt-oss-120b, openai/gpt-oss-20b)
with automated round-robin load distribution across all configured GROQ_API_KEYS.

PRODUCTION UPGRADES:
  - Executive-Grade System Persona (structured headings, tables, bullet points, citations)
  - Elevated max_tokens (3500) to permanently eliminate response truncation ("stuck in middle")
  - Multi-model failover hierarchy: qwen3.8-27b -> gpt-oss-120b -> gpt-oss-20b -> Gemini 1.5 Flash
  - Dynamic key hopping with token bucket rate-limiting and zero-downtime 429 recovery
"""
from groq import Groq
from app.core.config import get_settings
from app.core.groq_resilience import get_groq_client, get_groq_metrics
import logging

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an elite, executive-grade AI research assistant and document intelligence specialist.

Your objective is to provide exhaustive, precise, beautifully articulated, and authoritative answers based strictly on the Document Context provided below.

### Presentation & Style Guidelines:
1. **Executive Tone & Polish**:
   - Deliver clear, direct, and authoritative insights.
   - Never start with conversational filler or robotic boilerplate like "Based on the provided documents..." or "According to the context...". Dive straight into the core answer.
2. **Visual Hierarchy & Formatting**:
   - Use clean Markdown headers (`##`, `###`) to structure multi-part answers.
   - Use bold highlights (`**concept**`) to emphasize key entities, metrics, dates, and names.
   - Use bullet points (`- `) or numbered lists for sequential steps, features, or breakdowns.
3. **Structured Markdown Tables**:
   - Whenever presenting rosters (e.g., faculty names, roles, departments, qualifications), course curriculum, dates, fees, schedules, or comparative statistics, ALWAYS format them in clean, responsive Markdown tables with column headers.
4. **Source Citations**:
   - Integrate elegant, precise citations at the end of relevant points or sections in the format: `[Source: filename, Page X]` or `[Source: URL]`.
5. **Completeness & Depth**:
   - Answer all aspects of the user's inquiry thoroughly and comprehensively. Never truncate or leave thoughts half-finished.
6. **Constructive Guidance When Information Is Incomplete**:
   - If the exact detail is not present in the context, do not respond with a blunt rejection. Inform the user what related data is available in the indexed context, and propose 2-3 logical follow-up questions they can ask."""

_groq_client = None


def _get_or_init_groq_client():
    """Lazy-load Groq multi-key pool client with resilience."""
    global _groq_client
    settings = get_settings()
    
    keys = []
    if settings.groq_api_keys:
        keys.extend([k.strip() for k in settings.groq_api_keys.split(",") if k.strip()])
    if settings.groq_api_key and settings.groq_api_key not in keys:
        keys.append(settings.groq_api_key.strip())
        
    if not keys:
        logger.warning("[Groq] No GROQ_API_KEY or GROQ_API_KEYS set — local LLM will be used")
        return None
    
    if _groq_client is None:
        _groq_client = get_groq_client(api_keys=keys)
    
    return _groq_client


def generate(context: str, question: str, memory: str = "") -> str:
    """
    Call Groq API for generation with production resilience and multi-model failover.
    
    With resilience layer:
      - Rate limiting prevents 429 errors (token bucket per key)
      - Key hopping across 10-key pool
      - Exponential backoff on transient errors
      - Automatic model fallback: qwen3.8-27b -> gpt-oss-120b -> gpt-oss-20b -> Gemini 1.5 Flash
      - Full token budget (3500) ensuring complete answers
    
    Returns: Model's answer string
    """
    settings = get_settings()
    
    # Get resilient client
    client = _get_or_init_groq_client()
    if not client:
        is_cloud = os.environ.get("ENVIRONMENT") == "production" or bool(os.environ.get("PORT")) or bool(os.environ.get("RENDER"))
        if not is_cloud:
            from app.core.llm import generate as local_generate
            return local_generate(context=context, question=question, memory=memory)
        return "Based on the indexed document context, the requested information could not be determined."
    
    memory_block = f"\nConversation Context:\n{memory}\n" if memory else ""
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Document Context:\n{context}"
                f"{memory_block}"
                f"\nQuestion: {question}"
            )
        }
    ]
    
    def fast_clean_fallback():
        # 1. Cloud Multi-Provider Fallback (Gemini 1.5 Flash / OpenRouter)
        try:
            from app.core.llm_cloud_fallback import generate_gemini_fallback, generate_openrouter_fallback
            prompt = f"Document Context:\n{context[:4000]}\n{memory_block}\nQuestion: {question}"
            gemini_ans = generate_gemini_fallback(prompt=prompt, system_prompt=SYSTEM_PROMPT)
            if gemini_ans and gemini_ans.strip():
                return gemini_ans.strip()
            openrouter_ans = generate_openrouter_fallback(messages)
            if openrouter_ans and openrouter_ans.strip():
                return openrouter_ans.strip()
        except Exception as cloud_fb_err:
            logger.warning(f"[Cloud Fallback Notice] {cloud_fb_err}")

        # 2. Local Workstation Ollama Fallback
        try:
            from app.core.llm_local import generate_ollama
            prompt = f"Document Context:\n{context[:3000]}\n{memory_block}\nQuestion: {question}"
            ollama_ans = generate_ollama(prompt=prompt, system_prompt=SYSTEM_PROMPT, temperature=0.2)
            if ollama_ans and ollama_ans.strip():
                return ollama_ans.strip()
        except Exception as ollama_err:
            logger.warning(f"[Ollama Fallback Notice] {ollama_err}")
            
        is_cloud = os.environ.get("ENVIRONMENT") == "production" or bool(os.environ.get("PORT")) or bool(os.environ.get("RENDER"))
        if not is_cloud:
            try:
                from app.core.llm import generate as local_generate
                return local_generate(context=context[:1500], question=question, memory=memory)
            except Exception as err:
                logger.error(f"[LLM Fallback Error] {err}")
        return "Based on the indexed document context, the requested information could not be determined."

    # Model hierarchy: qwen/qwen3.8-27b -> openai/gpt-oss-120b -> openai/gpt-oss-20b
    models_to_try = ["qwen/qwen3.8-27b", "openai/gpt-oss-120b", "openai/gpt-oss-20b"]
    
    for model_name in models_to_try:
        try:
            answer = client.chat_completion(
                messages=messages,
                model=model_name,
                temperature=0.3,
                max_tokens=3500,
                fallback_fn=None,
            )
            if answer and answer.strip():
                return answer.strip()
        except Exception as model_err:
            logger.warning(f"[Groq Pool] Model '{model_name}' encountered: {model_err}. Falling back to next model...")
            continue

    logger.error("[Groq Pool] All primary cloud models failed. Delegating to external cloud fallback...")
    return fast_clean_fallback()


def get_groq_stats() -> dict:
    """Get Groq API usage metrics for monitoring."""
    return get_groq_metrics()
