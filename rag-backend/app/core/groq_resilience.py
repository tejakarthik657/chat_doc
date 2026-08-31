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

class ResilientGroqClient:
    """
    Wraps Groq client with resilience patterns.
    """

    def __init__(self, api_key: str, rate_limit_rpm: int = 30):
        self.client = Groq(api_key=api_key)
        
        # Token bucket: 30 RPM = 0.5 req/sec, we use 0.33 req/sec for safety
        self.rate_limiter = TokenBucket(
            capacity=5,
            refill_rate=(rate_limit_rpm / 60) * 0.66  # 66% of max rate
        )
        
        # Circuit breaker
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60
        )

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        retry=retry_if_exception_type((RateLimitError, APIConnectionError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    def _call_with_backoff(self, **kwargs):
        """Internal method with exponential backoff retry logic."""
        return self.client.chat.completions.create(**kwargs)

    def chat_completion(
        self,
        messages: list,
        model: str = "llama-3.3-70b-versatile",
        temperature: float = 0.7,
        max_tokens: int = 500,
        fallback_fn: Optional[callable] = None,
    ) -> str:
        """
        Make a Groq API call with full resilience.

        Args:
            messages: Chat messages
            model: Model name
            temperature: Sampling temperature
            max_tokens: Max tokens in response
            fallback_fn: Fallback function if Groq fails (e.g., local TinyLlama)

        Returns:
            Response text or fallback result
        """
        # Check circuit breaker first
        if self.circuit_breaker.is_open():
            logger.warning("Groq circuit breaker OPEN, using fallback")
            if fallback_fn:
                return fallback_fn(messages)
            raise APIError("Groq service unavailable, no fallback available")

        # Rate limiting: acquire token (wait if needed)
        self.rate_limiter.acquire(1, blocking=True)

        # Make request with exponential backoff
        try:
            response = self._call_with_backoff(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            self.circuit_breaker.record_success()
            return response.choices[0].message.content

        except RateLimitError as e:
            logger.error(f"Groq rate limit: {e}")
            self.circuit_breaker.record_failure()
            if fallback_fn:
                logger.info("Using fallback for rate-limited request")
                return fallback_fn(messages)
            raise

        except APIConnectionError as e:
            logger.error(f"Groq connection error: {e}")
            self.circuit_breaker.record_failure()
            if fallback_fn:
                logger.info("Using fallback for connection error")
                return fallback_fn(messages)
            raise

        except APIError as e:
            logger.error(f"Groq API error: {e}")
            self.circuit_breaker.record_failure()
            if fallback_fn:
                logger.info("Using fallback for API error")
                return fallback_fn(messages)
            raise


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


def get_groq_client(api_key: str) -> ResilientGroqClient:
    """Lazy-load resilient Groq client singleton."""
    global _groq_client
    if _groq_client is None:
        _groq_client = ResilientGroqClient(api_key)
    return _groq_client


def get_groq_metrics() -> Dict[str, Any]:
    """Get Groq API metrics for monitoring."""
    return _groq_metrics.get_stats()
