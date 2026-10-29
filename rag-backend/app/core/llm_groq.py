import os
"""
Groq LLM: FREE and ULTRA FAST cloud LLM inference.
Uses Llama 3.1 70B - better than GPT-3.5, completely free.

Get free API key from: https://console.groq.com/keys
Free tier: 30 requests/minute (more than enough for your app)

PRODUCTION UPGRADES:
  - Integrated with ResilientGroqClient (exponential backoff + rate limiting)
  - Circuit breaker prevents cascading failures
  - Token bucket prevents hitting 429 errors
  - Fallback to local TinyLlama if Groq unavailable
"""
from groq import Groq
from app.core.config import get_settings
from app.core.groq_resilience import get_groq_client, get_groq_metrics
import logging

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a rigorous document assistant for an educational institution.

Your ONLY task: Answer the user's question using the provided document context.
- Use ONLY the information in the Document Context below.
- If the answer is not in the context, say: "I could not find this information in the indexed documents."
- DO NOT guess, infer, or use external knowledge.
- Always cite the source: [Source: filename, Page X]
- Be precise and factual — this is for institutional use.
- For lists (e.g., faculty), present them clearly with names and roles.
- Keep answers concise but complete."""

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
    Call Groq API for generation with production resilience.
    
    With resilience layer:
      - Rate limiting prevents 429 errors (token bucket)
      - Exponential backoff on transient errors
      - Circuit breaker fails fast if Groq is down
      - Fallback to local TinyLlama if all else fails
    
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
        try:
            from app.core.llm_local import generate_ollama
            prompt = f"Document Context:\n{context[:3000]}\n{memory_block}\nQuestion: {question}"
            ollama_ans = generate_ollama(prompt=prompt, system_prompt=SYSTEM_PROMPT, temperature=0.2)
            if ollama_ans:
                return ollama_ans
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

    try:
        # Primary: qwen/qwen3.8-27b on Groq resilient pool
        answer = client.chat_completion(
            messages=messages,
            model="qwen/qwen3.8-27b",
            temperature=0.3,
            max_tokens=800,
            fallback_fn=None,
        )
        return answer.strip()
    except Exception as primary_err:
        logger.warning(f"[Groq] qwen/qwen3.8-27b error: {primary_err}. Trying openai/gpt-oss-120b...")
        try:
            answer = client.chat_completion(
                messages=messages,
                model="openai/gpt-oss-120b",
                temperature=0.3,
                max_tokens=800,
                fallback_fn=None,
            )
            return answer.strip()
        except Exception as fallback_err:
            logger.error(f"[Groq] All cloud models failed: {fallback_err}.")
            return fast_clean_fallback()


def get_groq_stats() -> dict:
    """Get Groq API usage metrics for monitoring."""
    return get_groq_metrics()

