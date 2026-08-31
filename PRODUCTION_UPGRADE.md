# Production Architecture Upgrade Guide
## Phase 1 & 2: Celery + Redis + Groq Resilience

**Status**: ✅ Implemented & Ready for Testing
**Date**: 2026-07-01
**Target Systems**: Solves 3 critical bottlenecks preventing production deployment

---

## What Changed? (Executive Summary)

### Before (Monolithic, Fragile)
```
User uploads PDF → FastAPI event loop blocks → embedding inference freezes →
HTTP timeouts for other users → Groq 429 errors → fallback to slow local TinyLlama →
backend crashes
```

### After (Decoupled, Resilient)
```
User uploads PDF → FastAPI returns 202 Accepted immediately →
Redis queue picks up task → Celery worker processes in isolation →
Groq API calls with token bucket + exponential backoff →
status updates to MongoDB → frontend polls for completion
```

---

## Phase 1: Celery + Redis (Decouple Event Loop)

### What It Solves
- **Problem**: FastAPI BackgroundTasks run in same process as web server
- **Impact**: Large crawls (100+ pages) saturate CPU → HTTP timeouts for other users
- **Solution**: Celery workers in isolated processes, Redis as task broker

### New Architecture
```
┌─────────────┐
│ FastAPI Web │ (receives requests, queues tasks, returns 202)
└──────┬──────┘
       │ task.delay()
       ▼
┌──────────────┐
│ Redis Broker │ (message queue)
└──────┬───────┘
       │
       ├─────────┬──────────┬──────────┐
       ▼         ▼          ▼          ▼
   ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
   │Worker1 │ │Worker2 │ │Worker3 │ │Worker4 │
   │(index) │ │(crawl) │ │(ocr)   │ │(clean) │
   └────────┘ └────────┘ └────────┘ └────────┘
```

### Key Files Added
- `app/celery_app.py` — Celery configuration + app initialization
- `app/tasks.py` — Background task definitions:
  - `ingest_document_task` — PDF upload & indexing
  - `crawl_website_task` — Website crawling
  - `cleanup_stale_ingestions` — Daily maintenance
- `docker-compose.yml` (updated) — Added Redis, Celery Worker, Celery Beat
- `scripts/dev.sh` — Local development setup

### Key Files Modified
- `requirements.txt` — Added Celery, Redis, Tenacity (resilience)
- `app/core/config.py` — Added Celery & Redis settings
- `app/api/routes/documents.py` — Changed from BackgroundTasks to `task.delay()`

### API Changes
**Before:**
```python
@router.post("/upload", status_code=201)
async def upload_document(background_tasks: BackgroundTasks, ...):
    background_tasks.add_task(ingest_document, ...)  # Blocks event loop
    return DocumentOut(status="processing")
```

**After:**
```python
@router.post("/upload", status_code=202)  # 202 = Accepted
async def upload_document(...):
    ingest_document_task.delay(doc_id, file_path, user_id)  # Non-blocking
    return DocumentOut(status="processing")
```

### Status Workflow (Frontend Polling)

**Document Upload Flow:**
```
1. User uploads PDF → returns 202 Accepted + document_id
2. GET /api/documents/{id} → {"status": "processing"}
3. Celery worker processes in background...
4. GET /api/documents/{id} → {"status": "indexed", "page_count": 42}
5. Frontend shows "Ready to query" ✓
```

**Database Updates:**
```
documents collection:
{
  "_id": "doc_id",
  "status": "processing" → "indexed" OR "failed",
  "ingestion_started_at": ...,
  "ingestion_completed_at": ...,
  "error_message": "..." (if failed)
}
```

---

## Phase 2: Groq Resilience Layer (Handle Rate Limits)

### What It Solves
- **Problem**: Groq free tier = 30 RPM. Hit limit → 429 error → fallback to slow CPU TinyLlama → backend crashes
- **Impact**: With contextual retrieval (20+ chunks per query), hits 429 within minutes
- **Solution**: Token bucket rate limiter + exponential backoff + circuit breaker

### New Architecture
```
┌──────────────────────────────────────────┐
│ Groq API Call (with resilience layer)    │
└──────────────────┬───────────────────────┘
                   │
         ┌─────────┴─────────┐
         ▼                   ▼
    ┌──────────┐        ┌──────────────┐
    │ Rate     │        │ Circuit      │
    │ Limiter  │        │ Breaker      │
    │(token    │        │(fail fast)   │
    │bucket)   │        │              │
    └─────┬────┘        └──────┬───────┘
          │                    │
          └────────┬───────────┘
                   ▼
        ┌──────────────────────┐
        │ Exponential Backoff  │
        │ (tenacity)           │
        │ Retry: 4x            │
        │ Delay: 2s → 60s      │
        └────────┬─────────────┘
                 ▼
        ┌─────────────────┐
        │ Fallback Fn     │
        │ (local TinyLlama)│
        └─────────────────┘
```

### Key Files Added
- `app/core/groq_resilience.py` — Complete resilience implementation:
  - `TokenBucket` — Rate limiting algorithm (prevents 429 before it happens)
  - `CircuitBreaker` — Fail-fast pattern (don't hammer failing service)
  - `ResilientGroqClient` — Wrapper with full resilience
  - `GroqMetrics` — Track API performance

### Key Files Modified
- `app/core/llm_groq.py` — Updated `generate()` to use ResilientGroqClient
- `requirements.txt` — Added `tenacity==9.0.0` (retry library)
- `app/core/config.py` — Added Groq resilience settings

### How It Works (Example)

**Without Resilience:**
```
Request 1 → Groq ✓ (9 more allowed in this minute)
Request 2 → Groq ✓ (8 more allowed)
...
Request 10 → Groq ✗ 429 Rate Limit Hit!
           → Fallback to TinyLlama (15-30s per chunk) → CRASH
```

**With Resilience:**
```
Request 1 → TokenBucket.acquire(1) ✓ → Groq ✓
Request 2 → TokenBucket.acquire(1) ✓ → Groq ✓
...
Request 15 → TokenBucket.acquire(1) ⏸️ (waiting for next token) → wait 2s
Request 16 → TokenBucket.acquire(1) ✓ → Groq ✓
...
(No 429 errors!)
```

**If Groq Goes Down:**
```
Request 1 → Groq timeout → Circuit breaker records failure
Request 2 → Groq timeout → Circuit breaker records failure
Request 5 → Circuit breaker threshold hit → OPEN
Request 6 → Circuit breaker is OPEN → immediately use fallback (fast fail)
```

### Metrics Monitoring

**Access Groq API stats via new endpoint:**
```python
@app.get("/api/health/groq")
async def get_groq_stats():
    return get_groq_stats()
```

**Response:**
```json
{
  "total_calls": 42,
  "total_errors": 2,
  "error_rate": 0.048,
  "rate_limit_hits": 0,
  "avg_latency_sec": 1.23,
  "uptime_sec": 3600
}
```

---

## Installation & Setup

### Option 1: Docker (Recommended for Production)

```bash
# Start all services (includes Redis, Celery workers, Beat)
docker-compose up -d

# Check logs
docker-compose logs -f celery-worker
docker-compose logs -f backend

# Verify Redis is working
docker-compose exec redis redis-cli ping  # Should return PONG

# Verify Celery workers
docker-compose exec celery-worker celery -A app.celery_app inspect active
```

### Option 2: Local Development

**Prerequisites:**
- Python 3.11+
- Redis (installed via `brew install redis` or `apt-get install redis-server`)
- MongoDB (local or Atlas)

**Setup:**
```bash
cd rag-backend

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Copy .env template
cp .env.example .env
# Edit .env with your Groq API key, MongoDB URL, etc.

# Start Redis (in separate terminal)
redis-server

# Start services (use provided script or manual)
bash ../scripts/dev.sh

# OR manually:
# Terminal 1: FastAPI
uvicorn app.main:app --reload

# Terminal 2: Celery Worker
celery -A app.celery_app worker --loglevel=info --concurrency=2

# Terminal 3: Celery Beat (scheduled tasks)
celery -A app.celery_app beat --loglevel=info
```

### Configuration

**Required environment variables:**
```bash
# Groq (free tier: 30 RPM)
GROQ_API_KEY=your-key-from-https://console.groq.com/keys

# Redis
REDIS_URL=redis://:password@localhost:6379/0
CELERY_BROKER_URL=redis://:password@localhost:6379/1
CELERY_RESULT_BACKEND=redis://:password@localhost:6379/2

# MongoDB
MONGODB_URL=mongodb://localhost:27017
DB_NAME=rag_db
```

**Groq Resilience Settings (defaults are good):**
```bash
GROQ_RATE_LIMIT_RPM=30                          # Free tier limit
GROQ_RETRY_MAX_ATTEMPTS=4                       # Exponential backoff retries
GROQ_CIRCUIT_BREAKER_THRESHOLD=5                # Failures before circuit opens
GROQ_CIRCUIT_BREAKER_RECOVERY_TIMEOUT=60        # Seconds before retry
```

---

## Testing the Upgrades

### Test 1: Celery Task Queueing (No Event Loop Blocking)

```python
# In Python REPL
import requests

# Upload large PDF
with open("large.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/documents/upload",
        files={"file": f},
        headers={"Authorization": "Bearer your_token"}
    )

# Should return 202 immediately (not wait for ingestion)
print(response.status_code)  # 202
doc_id = response.json()["id"]

# Check status (polling)
import time
for i in range(60):
    status = requests.get(f"http://localhost:8000/api/documents/{doc_id}").json()
    print(f"[{i}s] Status: {status['status']}")
    if status["status"] in ["indexed", "failed"]:
        break
    time.sleep(1)
```

### Test 2: Groq Resilience (Rate Limiting)

```python
# Simulate multiple concurrent requests
import asyncio
from app.core.groq_resilience import get_groq_client

client = get_groq_client(api_key="your-key")

async def make_requests():
    for i in range(50):  # Would hit 429 without resilience
        try:
            response = client.chat_completion(
                messages=[{"role": "user", "content": "Hello"}],
                fallback_fn=lambda msgs: "Fallback response"
            )
            print(f"{i}: ✓ {response[:30]}...")
        except Exception as e:
            print(f"{i}: ✗ {e}")

# Run
asyncio.run(make_requests())

# Check metrics
print(get_groq_stats())
```

### Test 3: Circuit Breaker (Fail Fast on Outage)

```python
# Simulate Groq being down
# (just disconnect from internet or mock the client)

client.circuit_breaker.record_failure()
client.circuit_breaker.record_failure()
client.circuit_breaker.record_failure()
client.circuit_breaker.record_failure()
client.circuit_breaker.record_failure()  # Threshold = 5

# Now circuit breaker should be OPEN
if client.circuit_breaker.is_open():
    print("✓ Circuit breaker is OPEN (fail fast mode)")
    # Next requests will immediately use fallback without waiting
```

---

## Monitoring & Debugging

### Check Celery Worker Status

```bash
# While Celery worker is running
celery -A app.celery_app inspect active    # Show active tasks
celery -A app.celery_app inspect stats     # Worker statistics
celery -A app.celery_app inspect registered  # Registered tasks
```

### Monitor Redis

```bash
redis-cli

> DBSIZE                          # Number of keys
> KEYS "celery*"                  # See task keys
> INFO stats                      # Connection stats
> MONITOR                         # Watch real-time commands
> FLUSHDB                         # Clear database (careful!)
```

### View Logs

```bash
# Docker
docker-compose logs -f celery-worker
docker-compose logs -f backend
docker-compose logs -f redis

# Local
tail -f ~/.redis/redis.log
```

### Groq API Metrics Endpoint

```bash
curl http://localhost:8000/api/health/groq

# Response:
{
  "total_calls": 42,
  "total_errors": 2,
  "error_rate": 0.048,
  "rate_limit_hits": 0,
  "avg_latency_sec": 1.23,
  "uptime_sec": 3600
}
```

---

## Next Steps (Phase 3)

### Planned: HuggingFace TEI (Text Embeddings Inference)

**Current Bottleneck:**
- sentence-transformers (Python + NumPy + PyTorch) runs in FastAPI process
- CPU/GPU bound → embedding 1000 chunks = 5-10 minutes
- With 10 concurrent users = event loop freeze

**Solution:**
- Deploy separate TEI container (Rust-based, 10x faster)
- FastAPI makes HTTP calls to TEI instead of in-process inference
- TEI handles batching + GPU acceleration automatically

**Files to create:**
- `Dockerfile.tei` — TEI container image
- `docker-compose.yml` (update) — Add TEI service
- `app/core/embeddings.py` (update) — Use HTTP client for TEI

---

## Troubleshooting

### Redis Connection Error
```
Error: ConnectionError: Error -2 Name or service not known
```
**Solution:**
```bash
# Make sure Redis is running
redis-server
# Or via Docker
docker-compose up redis
```

### Celery Worker Not Processing Tasks
```bash
# Check if worker is listening to queue
celery -A app.celery_app inspect active

# If empty, restart worker
celery -A app.celery_app worker --loglevel=info --concurrency=2
```

### Groq 429 Rate Limit Still Hitting
```
Error: RateLimitError: 429 Too Many Requests
```
**Debug:**
```bash
# Check token bucket
from app.core.groq_resilience import get_groq_client
client = get_groq_client(api_key="...")
print(f"Tokens available: {client.rate_limiter.tokens}")
print(f"Refill rate: {client.rate_limiter.refill_rate} tokens/sec")

# Verify it's respecting rate limit
# Make 100 requests and time it — should take ~3-5 minutes
```

---

## Performance Expectations

### Before Production Upgrade
- Document upload → blocks event loop for 5-15 minutes
- Multiple uploads → timeouts for all users
- Groq 429 errors → fallback to 15-30s per chunk → crashes

### After Phase 1 & 2
- Document upload → returns 202 immediately, processes in background
- Multiple uploads → parallel processing, no blocking
- Groq 429 errors → token bucket prevents them + exponential backoff handles transients
- **Result**: System handles 10-50 concurrent users without crashing

### After Phase 3 (TEI)
- Embedding generation → 10x faster (TEI vs Python)
- Chunking 100-page document → 30-60 seconds (vs 5-15 minutes)
- **Result**: System handles 100+ concurrent users

---

## Production Checklist

- [ ] Update `.env` with Groq API key
- [ ] Update `.env` with MongoDB URL (ideally Atlas for HA)
- [ ] Set up Redis (use managed service like Heroku Redis or AWS ElastiCache for production)
- [ ] Update `.env` with secure Redis password
- [ ] Test Celery workers: `celery -A app.celery_app inspect active`
- [ ] Test Groq API: call `/api/health/groq` endpoint
- [ ] Monitor logs: `docker-compose logs -f`
- [ ] Run test suite: `pytest tests/`
- [ ] Set up monitoring (LangSmith for Phase 5)
- [ ] Document deployment procedure

---

## Questions?

See [implementation_plan.md](../implementation_plan.md) for the original architectural problems and full upgrade roadmap.
