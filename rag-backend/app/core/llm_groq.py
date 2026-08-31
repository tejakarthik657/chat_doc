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
from app.core.llm import generate as local_generate
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
    """Lazy-load Groq client with resilience."""
    global _groq_client
    settings = get_settings()
    
    if not settings.groq_api_key:
        logger.warning("[Groq] GROQ_API_KEY not set — local LLM will be used")
        return None
    
    if _groq_client is None:
        _groq_client = get_groq_client(settings.groq_api_key)
    
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
        logger.info("[Groq] Using local LLM (no API key)")
        return local_generate(context=context, question=question, memory=memory)
    
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
    
    try:
        # Call with full resilience (rate limiting + backoff + circuit breaker)
        answer = client.chat_completion(
            messages=messages,
            model="qwen/qwen3.8-27b",
            temperature=0.7,
            max_tokens=500,
            fallback_fn=lambda msgs: local_generate(
                context=context,
                question=question,
                memory=memory
            ),
        )
        return answer.strip()
    
    except Exception as e:
        logger.error(f"[Groq] Fatal error: {e}. Falling back to local LLM.")
        return local_generate(context=context, question=question, memory=memory)


def get_groq_stats() -> dict:
    """Get Groq API usage metrics for monitoring."""
    return get_groq_metrics()

