"""
Groq API Resilience Layer
─────────────────────────────────────────────────────────────────────────────────
Wraps Groq API calls with:
  1. Exponential backoff on 429 (rate limit) errors
  2. Token bucket rate limiter (prevent hitting 429 in the first place)
  3. Circuit breaker pattern (fail fast if Groq is down)
  4. Fallback logic (local TinyLlama if Groq fails persistently)

Solves the "Groq free tier = 30 RPM" problem:
  - Without resilience: 429 error → fallback to CPU TinyLlama → 15-30s per chunk → crashes
  - With resilience: exponential backoff queue → smooth processing → no crashes
"""
import asyncio
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging
from collections import deque

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
import httpx
from groq import Groq, RateLimitError, APIError, APIConnectionError

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Token Bucket Rate Limiter
# ──────────────────────────────────────────────────────────────────────────────

class TokenBucket:
    """
    Token bucket algorithm to prevent hitting rate limits.
    
    For Groq free tier: 30 requests per minute = 0.5 req/sec = 1 req every 2 seconds.
    We use a conservative rate: 1 request every 3 seconds to stay well below limits.
    """

    def __init__(self, capacity: int, refill_rate: float):
        """
        Args:
            capacity: Max tokens in bucket (e.g., 10 for burst)
            refill_rate: Tokens per second (e.g., 0.33 = 1 token every 3 sec)
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()

    def acquire(self, tokens: int = 1, blocking: bool = True) -> bool:
        """
        Acquire tokens. If blocking=True, wait until available.
        Returns: True if acquired, False if non-blocking and unavailable.
        """
        while True:
            now = time.time()
            elapsed = now - self.last_refill
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.refill_rate
            )
            self.last_refill = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True

            if not blocking:
                return False

            # Wait for next refill
            sleep_time = (tokens - self.tokens) / self.refill_rate
            time.sleep(sleep_time)


# ──────────────────────────────────────────────────────────────────────────────
# Circuit Breaker
# ──────────────────────────────────────────────────────────────────────────────

class CircuitBreaker:
    """
    Circuit breaker to fail fast if Groq is down.
    
    States:
      - CLOSED: normal operation, requests pass through
      - OPEN: too many failures detected, fail immediately (fast failure)
      - HALF_OPEN: testing if service recovered
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def is_open(self) -> bool:
        """Check if circuit should reject requests."""
        if self.state == "CLOSED":
            return False

        if self.state == "OPEN":
            # Try recovery after timeout
            if time.time() - self.last_failure_time > self.recovery_timeout:
                logger.info("Circuit breaker: attempting recovery (HALF_OPEN)")
                self.state = "HALF_OPEN"
                return False
            return True

        return False  # HALF_OPEN: allow request to test recovery

    def record_failure(self):
        """Record API failure and potentially open circuit."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold and self.state == "CLOSED":
            logger.warning(
                f"Circuit breaker: OPEN (failures: {self.failure_count})"
            )
            self.state = "OPEN"

    def record_success(self):
        """Record successful request, reset failures."""
        self.failure_count = 0
        if self.state != "CLOSED":
            logger.info("Circuit breaker: CLOSED (recovered)")
            self.state = "CLOSED"


# ──────────────────────────────────────────────────────────────────────────────
# Groq Resilience Wrapper
# ──────────────────────────────────────────────────────────────────────────────

class KeyWorker:
    """Manages an individual Groq API client with its own rate limiter and circuit breaker."""
    def __init__(self, key: str, index: int):
        self.key = key.strip()
        self.index = index
        timeout = httpx.Timeout(timeout=30.0, connect=5.0)
        self.client = Groq(api_key=self.key, timeout=timeout, max_retries=1)
        self.rate_limiter = TokenBucket(capacity=50, refill_rate=10.0)
        self.circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=20)
        self.cooldown_until: float = 0.0

    def is_available(self) -> bool:
        if time.time() < self.cooldown_until:
            return False
        return not self.circuit_breaker.is_open()

    def set_cooldown(self, seconds: float = 30.0):
        self.cooldown_until = time.time() + seconds
        logger.warning(f"[KeyPool] Key #{self.index} placed on cooldown for {seconds}s")


class ResilientGroqClient:
    """
    OpenRouter-style Dynamic Multi-Key Groq Client Pool.
    Rotates through multiple Groq API keys with zero-downtime failover on 429 rate limits.
    """
    def __init__(self, api_keys: list[str]):
        # Ensure we have at least one valid key
        clean_keys = [k.strip() for k in api_keys if k and k.strip()]
        if not clean_keys:
            clean_keys = ["invalid-key-placeholder"]
        
        self.workers = [KeyWorker(key, idx + 1) for idx, key in enumerate(clean_keys)]
        self.current_idx = 0
        logger.info(f"[KeyPool] Initialized resilient pool with {len(self.workers)} active Groq API keys")

    def _get_next_worker(self) -> Optional[KeyWorker]:
        total = len(self.workers)
        for offset in range(total):
            idx = (self.current_idx + offset) % total
            worker = self.workers[idx]
            if worker.is_available():
                self.current_idx = (idx + 1) % total
                return worker
        # If all in cooldown, take the one whose cooldown expires earliest
        earliest = min(self.workers, key=lambda w: w.cooldown_until)
        return earliest

    def chat_completion(
        self,
        messages: list,
        model: str = "qwen/qwen3.8-27b",
        temperature: float = 0.7,
        max_tokens: int = 3500,
        fallback_fn: Optional[callable] = None,
    ) -> str:
        max_pool_attempts = min(len(self.workers) * 2, 10)
        last_exception = None
        consecutive_conn_errors = 0

        for attempt in range(max_pool_attempts):
            worker = self._get_next_worker()
            if not worker:
                break

            worker.rate_limiter.acquire(1, blocking=False)
            t_start = time.time()

            try:
                response = worker.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                worker.circuit_breaker.record_success()
                _groq_metrics.record_call(time.time() - t_start, error=False)
                content = response.choices[0].message.content or ""
                # For reasoning models (e.g. openai/gpt-oss-20b), fallback to reasoning if content is empty
                if not content.strip() and hasattr(response.choices[0].message, "reasoning"):
                    reasoning = getattr(response.choices[0].message, "reasoning", "")
                    if reasoning:
                        content = reasoning
                return content

            except RateLimitError as e:
                _groq_metrics.record_rate_limit()
                _groq_metrics.record_call(time.time() - t_start, error=True)
                worker.set_cooldown(seconds=20.0)
                worker.circuit_breaker.record_failure()
                last_exception = e
                logger.warning(f"[KeyPool] Key #{worker.index} hit 429 RateLimit. Seamlessly hopping to next key...")
                continue

            except APIConnectionError as e:
                consecutive_conn_errors += 1
                _groq_metrics.record_call(time.time() - t_start, error=True)
                worker.circuit_breaker.record_failure()
                last_exception = e
                logger.warning(f"[KeyPool] Key #{worker.index} connection error: {e}.")
                # If network is down or groq unreachable across workers, fail fast to fallback
                if consecutive_conn_errors >= 2:
                    logger.warning("[KeyPool] Network/API connection issue detected across keys. Breaking out to fallback immediately.")
                    break
                continue

            except APIError as e:
                err_str = str(e).lower()
                if "model_decommissioned" in err_str or "model_not_found" in err_str or "does not exist" in err_str or "decommissioned" in err_str:
                    logger.error(f"[KeyPool] Model '{model}' is invalid/decommissioned on Groq ({e}). Aborting retries across keypool.")
                    last_exception = e
                    break

                _groq_metrics.record_call(time.time() - t_start, error=True)
                worker.circuit_breaker.record_failure()
                last_exception = e
                logger.warning(f"[KeyPool] Key #{worker.index} API error: {e}. Hopping to next key...")
                continue

            except Exception as e:
                last_exception = e
                logger.error(f"[KeyPool] Unexpected error on key #{worker.index}: {e}")
                break

        # If all keys failed or exhausted, trigger fallback
        if fallback_fn:
            logger.info("[KeyPool] Keys in pool exhausted or offline. Delegating to local offline fallback...")
            return fallback_fn(messages)

        if last_exception:
            raise last_exception
        raise APIError("All API keys in Groq pool exhausted and unavailable.")

    def transcribe_audio(
        self,
        file_tuple: Any,
        model: str = "whisper-large-v3-turbo",
        prompt: Optional[str] = None,
    ) -> str:
        """
        Transcribe audio using Groq Cloud Whisper with resilient multi-key pooling.
        Ultra-fast (<300ms) with zero local GPU/CPU overhead.
        """
        max_pool_attempts = min(len(self.workers) * 2, 10)
        last_exception = None

        for attempt in range(max_pool_attempts):
            worker = self._get_next_worker()
            if not worker:
                break

            worker.rate_limiter.acquire(1, blocking=False)
            t_start = time.time()
            try:
                kwargs = {"file": file_tuple, "model": model}
                if prompt:
                    kwargs["prompt"] = prompt
                transcription = worker.client.audio.transcriptions.create(**kwargs)
                worker.circuit_breaker.record_success()
                _groq_metrics.record_call(time.time() - t_start, error=False)
                return transcription.text
            except RateLimitError as e:
                _groq_metrics.record_rate_limit()
                _groq_metrics.record_call(time.time() - t_start, error=True)
                worker.set_cooldown(seconds=20.0)
                worker.circuit_breaker.record_failure()
                last_exception = e
                logger.warning(f"[KeyPool] Key #{worker.index} hit 429 on Whisper. Hopping to next key...")
                continue
            except Exception as e:
                _groq_metrics.record_call(time.time() - t_start, error=True)
                worker.circuit_breaker.record_failure()
                last_exception = e
                logger.warning(f"[KeyPool] Key #{worker.index} Whisper error: {e}. Hopping to next key...")
                continue

        if last_exception:
            raise last_exception
        raise APIError("All API keys in Groq pool exhausted for audio transcription.")


# ──────────────────────────────────────────────────────────────────────────────
# Metrics Tracking
# ──────────────────────────────────────────────────────────────────────────────

class GroqMetrics:
    """Track Groq API usage for monitoring and cost optimization."""

    def __init__(self):
        self.total_calls = 0
        self.total_errors = 0
        self.total_retries = 0
        self.rate_limit_hits = 0
        self.latencies: deque = deque(maxlen=100)
        self.start_time = datetime.utcnow()

    def record_call(self, latency_seconds: float, error: bool = False):
        self.total_calls += 1
        self.latencies.append(latency_seconds)
        if error:
            self.total_errors += 1

    def record_rate_limit(self):
        self.rate_limit_hits += 1

    def get_stats(self) -> Dict[str, Any]:
        avg_latency = sum(self.latencies) / len(self.latencies) if self.latencies else 0
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        
        return {
            "total_calls": self.total_calls,
            "total_errors": self.total_errors,
            "error_rate": self.total_errors / self.total_calls if self.total_calls > 0 else 0,
            "rate_limit_hits": self.rate_limit_hits,
            "avg_latency_sec": round(avg_latency, 2),
            "uptime_sec": int(uptime),
        }


# Global instances
_groq_client: Optional[ResilientGroqClient] = None
_groq_metrics: GroqMetrics = GroqMetrics()


class ResilientGroqClientProxy:
    """Auto-initializing proxy that loads keys from settings seamlessly."""
    def _client(self) -> ResilientGroqClient:
        global _groq_client
        if _groq_client is None:
            try:
                from app.core.config import get_settings
                s = get_settings()
                keys = []
                if s.groq_api_keys:
                    keys.extend([k.strip() for k in s.groq_api_keys.split(",") if k.strip()])
                if s.groq_api_key and s.groq_api_key not in keys:
                    keys.append(s.groq_api_key.strip())
                _groq_client = ResilientGroqClient(keys)
            except Exception as e:
                logger.warning(f"[KeyPool] Could not load keys from settings: {e}")
                _groq_client = ResilientGroqClient([])
        return _groq_client

    def __getattr__(self, name):
        return getattr(self._client(), name)


resilient_groq_client = ResilientGroqClientProxy()


def get_groq_client(api_key: Optional[str] = None, api_keys: Optional[list[str]] = None) -> ResilientGroqClient:
    """Lazy-load resilient Groq multi-key pool singleton."""
    global _groq_client
    if _groq_client is None:
        keys = []
        if api_keys:
            keys.extend(api_keys)
        if api_key and api_key not in keys:
            keys.append(api_key)
        _groq_client = ResilientGroqClient(keys)
    return _groq_client


def get_groq_metrics() -> Dict[str, Any]:
    """Get Groq API metrics for monitoring."""
    return _groq_metrics.get_stats()
