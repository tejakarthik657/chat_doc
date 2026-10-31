# 12. Multi-Key Groq LPU Cluster Resilience

## 1. Resilience State Machine

```mermaid
stateDiagram-v2
    [*] --> KeyWorker_Available : 10 Keys Loaded from Environment

    state KeyWorker_Available {
        Check_Cooldown : Is current time >= cooldown_until?
        Check_Circuit : Is Circuit CLOSED?
    }

    KeyWorker_Available --> TokenBucket_Acquire : Request Dispatched
    
    state TokenBucket_Acquire {
        Check_Tokens : tokens >= 1?
        Refill_Math : tokens = min(capacity, tokens + elapsed * refill_rate)
    }

    TokenBucket_Acquire --> Execute_Call : Token Acquired
    
    Execute_Call --> Success_200 : HTTP 200 OK
    Success_200 --> Reset_Failure : Reset failure_count = 0
    Reset_Failure --> [*] : Return Full Response

    Execute_Call --> RateLimit_429 : HTTP 429 RateLimitError
    RateLimit_429 --> Set_Cooldown : worker.cooldown_until = now + 20.0s
    Set_Cooldown --> Rotate_Next : Rotate to (idx + 1) % 10
    Rotate_Next --> TokenBucket_Acquire : Immediate Key-Hop

    Execute_Call --> Network_Error : APIConnectionError
    Network_Error --> Check_Threshold : consecutive_errors >= 3?
    Check_Threshold --> Trip_Circuit : Circuit OPEN
    Check_Threshold --> Rotate_Next : Try Next Key

    Trip_Circuit --> Fallback_REST : All Circuits OPEN
    Fallback_REST --> [*] : Delegate to Gemini 1.5 Flash
```

---

## 2. Technical Implementation Specifications (`core/groq_resilience.py`)

- **`TokenBucket`**: Capacity: $50$, Refill Rate: $10.0\text{ tokens/sec}$. Prevents burst spikes.
- **`CircuitBreaker`**: Failure threshold: $3$, Recovery timeout: $20.0\text{ s}$. Protects against hanging TCP sockets.
- **`KeyWorker`**: Wraps individual Groq client instances, their private token bucket, and circuit breaker.
- **`ResilientGroqClient`**: Implements round-robin key acquisition across all parsed keys in `GROQ_API_KEYS`.
