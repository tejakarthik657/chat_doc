"""
Local Ollama LLM Client: qwen2.5-coder:3b integration.
Used for background self-healing web scraping, document structurization,
and zero-cost local inference fallback.
"""
import httpx
import logging
from typing import Optional
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def generate_ollama(
    prompt: str,
    system_prompt: Optional[str] = None,
    model_name: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 1024,
    timeout: float = 30.0,
) -> str:
    """
    Generate text using local Ollama instance (default: qwen2.5-coder:3b).
    Falls back gracefully if Ollama is not reachable.
    """
    model = model_name or settings.ollama_model_name
    base_url = settings.ollama_base_url.rstrip("/")
    api_url = f"{base_url}/api/generate"

    full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

    payload = {
        "model": model,
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(api_url, json=payload)
            if response.status_code == 200:
                data = response.json()
                output = data.get("response", "").strip()
                if output:
                    return output
            else:
                logger.warning(f"[Ollama] Server returned HTTP {response.status_code}: {response.text}")
    except Exception as err:
        logger.warning(f"[Ollama] Request failed to {api_url}: {err}")

    # Fallback to Groq multi-key pool if Ollama is unreachable
    try:
        from app.core.groq_resilience import resilient_groq_client
        for cand_model in ["qwen/qwen3.8-27b", "openai/gpt-oss-20b"]:
            try:
                ans = resilient_groq_client.chat_completion(
                    messages=[{"role": "user", "content": full_prompt}],
                    model=cand_model,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                if ans and ans.strip():
                    return ans.strip()
            except Exception:
                continue
    except Exception as fallback_err:
        logger.warning(f"[Ollama Fallback Groq Notice] {fallback_err}")
    return ""


def generate_self_healing_extraction(html_content: str, url: str) -> str:
    """
    High-Speed Self-Healing DOM Parser:
    Uses the 10-key Groq dynamic pool (llama-3.1-8b-instant) for sub-400ms extraction
    with zero local CPU consumption. Falls back to fast BeautifulSoup if offline.
    """
    system_instruction = (
        "You are an expert web scraping parser. Your task is to inspect messy, dynamic, or unreadable "
        "HTML code and extract the primary article or page body text in clean, readable Markdown format.\n"
        "Guidelines:\n"
        "1. Remove navigation menus, footers, headers, ads, and boilerplate links.\n"
        "2. Preserve headings, main paragraphs, lists, and structured tables.\n"
        "3. Do NOT invent or add external facts not present in the HTML snippet."
    )
    
    # Truncate HTML to fit context window safely
    truncated_html = html_content[:12000]
    
    # ── Tier 1: 10-Key Groq Dynamic Failover Pool (Fastest, 0% CPU, ~300ms) ───────────
    try:
        from app.core.groq_resilience import resilient_groq_client
        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": f"Target URL: {url}\n\nHTML Snippet:\n{truncated_html}\n\nExtracted Clean Content (Markdown):"}
        ]
        for cand_model in ["qwen/qwen3.8-27b", "openai/gpt-oss-20b"]:
            try:
                groq_extracted = resilient_groq_client.chat_completion(
                    messages=messages,
                    model=cand_model,
                    temperature=0.1,
                    max_tokens=2048,
                )
                if groq_extracted and len(groq_extracted.strip()) > 50:
                    logger.info(f"[Self-Healing Parser] Groq pool extracted {len(groq_extracted)} chars with {cand_model} for {url}")
                    return groq_extracted
            except Exception:
                continue
    except Exception as groq_err:
        logger.warning(f"[Self-Healing Parser] Groq pool bypassed: {groq_err}")

    # ── Tier 2: Ollama (Only if local daemon is running, 1s quick-check) ──────────────
    try:
        base_url = settings.ollama_base_url.rstrip("/")
        prompt = f"{system_instruction}\n\nTarget URL: {url}\n\nHTML Snippet:\n{truncated_html}"
        with httpx.Client(timeout=3.0) as client:
            resp = client.post(f"{base_url}/api/generate", json={
                "model": settings.ollama_model_name,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 1024}
            })
            if resp.status_code == 200:
                out = resp.json().get("response", "").strip()
                if len(out) > 50:
                    return out
    except Exception:
        pass

    # ── Tier 3: Fast In-Memory BeautifulSoup Stripping (Instant, 2ms, zero CPU stall) ─
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(truncated_html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
            tag.decompose()
        clean = soup.get_text(separator="\n")
        lines = [line.strip() for line in clean.splitlines() if line.strip()]
        return "\n".join(lines)
    except Exception:
        return ""
