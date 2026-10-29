"""
Cloud LLM Failover Provider (Google Gemini 1.5 Flash & OpenRouter)
──────────────────────────────────────────────────────────────────
Lightweight REST-based fallbacks for when Groq API keys are exhausted,
rate-limited (429), or unavailable.
Zero local RAM footprint (uses lightweight HTTP calls, no PyTorch / CTransformers).
"""
import os
import logging
import httpx
from typing import Optional
from app.core.config import get_settings

logger = logging.getLogger(__name__)


def generate_gemini_fallback(prompt: str, system_prompt: str = "") -> Optional[str]:
    """
    Call Google Gemini 1.5 Flash via direct REST API.
    Fast (<2s), high quota (15 RPM free tier), 1M token context.
    """
    settings = get_settings()
    api_key = settings.gemini_api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 800,
        }
    }
    if system_prompt:
        payload["systemInstruction"] = {
            "parts": [{"text": system_prompt}]
        }

    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts and "text" in parts[0]:
                        ans = parts[0]["text"].strip()
                        logger.info("[Gemini Fallback] Successfully answered using Gemini 1.5 Flash.")
                        return ans
            else:
                logger.warning(f"[Gemini Fallback Notice] HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"[Gemini Fallback Error] {e}")

    return None


def generate_openrouter_fallback(messages: list[dict]) -> Optional[str]:
    """
    Call OpenRouter Free Tier (e.g. meta-llama/llama-3.1-8b-instruct:free).
    """
    settings = get_settings()
    api_key = settings.openrouter_api_key or os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return None

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://nexus-tawny-seven-50.vercel.app",
        "X-Title": "Nexus VeriDocs",
    }
    payload = {
        "model": "meta-llama/llama-3.1-8b-instruct:free",
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 800,
    }

    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "")
                    if content:
                        logger.info("[OpenRouter Fallback] Successfully answered using OpenRouter free tier.")
                        return content.strip()
            else:
                logger.warning(f"[OpenRouter Fallback Notice] HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"[OpenRouter Fallback Error] {e}")

    return None
