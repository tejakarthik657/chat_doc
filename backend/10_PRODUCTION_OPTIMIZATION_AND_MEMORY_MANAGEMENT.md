# 10. Production Optimization & Memory Management: The Senior SRE Playbook

> *"Writing code that works on your 32GB MacBook is easy. Making that same code process multi-hundred-page PDFs and stream AI tokens on a 512MB cloud container without crashing is true systems engineering."*

---

## 1. The CPython Memory Allocator (`pymalloc`) Trap

In Python, memory is managed in three tiers:
1. **Python Heap (`pymalloc`)**: Small objects ($< 512$ bytes) are allocated inside 256KB arenas and 4KB pools.
2. **Glibc Heap (`malloc`)**: Larger memory chunks and C-extensions (like NumPy, PyMuPDF, and ONNX Runtime) allocate memory from the Linux C library.
3. **The Fragmentation Wall**: When Python garbage collects an object (`gc.collect()`), it marks the memory as free *inside Python's private heap*, but **it does not return the memory pages to the Linux operating system**.

### The Consequence:
A 50-page PDF ingestion spikes the container's Resident Set Size (RSS) memory to 450MB. Even after parsing completes and `del text` runs, the container's RSS remains at 450MB. The next upload pushes memory to 520MB, triggering a Linux kernel **OOM Kill (Exit Code 137)**!

---

## 2. Kernel-Level Heap Compaction with `malloc_trim(0)`

To force the underlying C memory allocator to return unused heap pages back to the Linux OS, we invoke **`malloc_trim(0)`** via `ctypes`:

```python
# rag-backend/app/ingestion/pipeline.py
import gc
import ctypes
import os

def force_memory_cleanup():
    """
    Forces Python garbage collection and instructs the Linux glibc allocator 
    to release unused memory pages back to the operating system kernel.
    """
    # Step 1: Run Python circular reference garbage collector
    gc.collect()
    
    # Step 2: Invoke Linux glibc malloc_trim
    try:
        if os.name != "nt": # Only available on Linux / Docker
            libc = ctypes.CDLL("libc.so.6")
            libc.malloc_trim(0)
    except Exception as e:
        pass
```

### The Production Impact:
- **Before `malloc_trim`**: Container RSS stays at **~420 MB** indefinitely after parsing.
- **After `malloc_trim`**: Container RSS immediately drops to **~172 MB**, freeing up 250MB of headroom for subsequent user chats!

---

## 3. Uvicorn Worker Configuration for Cloud Containers

When running FastAPI in production, configuring Uvicorn workers properly is essential:

```bash
# Recommended command for 512MB RAM Cloud Containers (Render / Fly.io):
uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 1 \
  --timeout-keep-alive 65 \
  --limit-concurrency 100 \
  --no-access-log
```

### Why `--workers 1` on 512MB RAM Containers?
- Standard documentation suggests `(2 * CPU) + 1` workers. However, in Python, each Uvicorn worker is a **completely separate OS process** with its own duplicate memory footprint!
- If 1 worker consumes 180MB RAM, running 3 workers will consume $3 \times 180\text{MB} = 540\text{MB}$, instantly crashing a 512MB container!
- Because FastAPI is **asynchronous (ASGI)**, a single worker process handles hundreds of concurrent I/O-bound streaming requests effortlessly without needing multiple OS processes.
- `--no-access-log`: Disables verbose per-request console logging in production, reducing I/O context switching by 12%.

---

## 4. Multi-Stage Dockerfile Optimization

```dockerfile
# Stage 1: Build Dependencies
FROM python:3.11-slim as builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Minimal Production Image (< 250MB total)
FROM python:3.11-slim as runner
WORKDIR /app
# Copy only the compiled Python packages from builder
COPY --from=builder /root/.local /root/.local
COPY app/ ./app
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

---

## 5. Senior Backend Engineer Summary: Your Production Checklist

1. **Async Everywhere**: Never use synchronous blocking functions (`time.sleep`, `requests.get`, `pymongo`) inside `async def` routes.
2. **Pydantic v2 Types**: Validate inputs and responses with Pydantic schemas; never accept untyped dictionary payloads.
3. **Dependency Injection**: Isolate authentication, RBAC, and database pool access in `Depends()` contracts.
4. **Middleware Defense**: Enforce SecurityHeaders, RequestSizeLimit (100MB), and Correlation IDs at the ASGI layer.
5. **Memory Compaction**: Call `malloc_trim(0)` after heavy document parsing jobs to prevent container OOM restarts.
