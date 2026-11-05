# 01. FastAPI & Python Async Foundations

> *"To be a core backend engineer, you must understand how your server actually runs on the operating system: how the event loop schedules coroutines, how ASGI handles concurrent sockets, and how the application lifespan manages resources."*

---

## 1. The Concurrency Evolution: WSGI vs. ASGI vs. Express.js

If you come from an **Express.js (Node.js)** background, you are accustomed to JavaScript's single-threaded event loop powered by libuv. 

In Python, the web ecosystem historically used **WSGI (Web Server Gateway Interface)**—a synchronous, blocking standard where each HTTP request occupied an entire thread or worker process (e.g., Flask or Django with Gunicorn). If a request made a 2-second database call or LLM streaming call, that worker thread was completely frozen and could not service other users.

```
WSGI (Synchronous, 1 Thread per Request):
Request 1 ──► [Worker Thread 1: BLOCKS on LLM API Call] ──► (Occupied for 3.5s!)
Request 2 ──► [Worker Thread 2: BLOCKS on PDF Parsing]   ──► (Occupied for 2.0s!)
Request 3 ──► [QUEUED / WAITING FOR FREE THREAD...]     ──► Latency Spikes!

ASGI (Asynchronous Server Gateway Interface - FastAPI):
Request 1 ──► [Event Loop: Dispatches async I/O socket] ──┐
Request 2 ──► [Event Loop: Dispatches async I/O socket] ──┼─► [Single Worker Thread handles
Request 3 ──► [Event Loop: Dispatches async I/O socket] ──┘    1,000s of concurrent streams!]
```

**FastAPI** is built on the modern **ASGI (Asynchronous Server Gateway Interface)** specification, powered by **Starlette** and **Pydantic**. Running on **Uvicorn** with the C-based **`uvloop`** library, FastAPI achieves throughput comparable to Go and Node.js while giving you access to Python's machine learning libraries.

---

## 2. Asynchronous Programming in Python (`async` & `await`)

Understanding Python's `asyncio` is mandatory for FastAPI development:

```python
# A synchronous blocking function (FREEZES THE ENTIRE EVENT LOOP!)
import time
def bad_blocking_query():
    time.sleep(2) # NEVER DO THIS IN FASTAPI! Blocks all concurrent users!

# An asynchronous non-blocking coroutine (YIELDS CONTROL TO EVENT LOOP)
import asyncio
async def good_async_query():
    await asyncio.sleep(2) # Non-blocking! Event loop can process 500 other chats while waiting!
```

### The Rule of Thumb:
- If a function performs **I/O** (network HTTP requests, database queries, reading disk files), use `async def` and `await`.
- If a library is purely synchronous and CPU-bound (like PyMuPDF parsing or heavy math), run it inside a threadpool using `asyncio.to_thread(func, *args)` so you never block the main ASGI event loop.

---

## 3. The Modern Application Lifespan Context Manager

In older FastAPI codebases, you will see `@app.on_event("startup")` and `@app.on_event("shutdown")`. **These are deprecated.**

In [`rag-backend/app/main.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/main.py), we implement the modern Python **`@asynccontextmanager` Lifespan protocol**:

```python
# rag-backend/app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.db.mongodb import init_db_client, close_db_client
from app.db.qdrant import init_qdrant_client
from app.core.logger import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the lifecycle of the application:
    Code BEFORE yield runs on startup.
    Code AFTER yield runs on graceful shutdown.
    """
    logger.info("[LIFESPAN] Initializing VeriDoc Synapse Backend...")
    
    # 1. Initialize Async MongoDB Connection Pool
    await init_db_client()
    logger.info("[LIFESPAN] MongoDB Atlas connection pool established.")
    
    # 2. Initialize Qdrant Vector Client & Ensure Collections Exist
    await init_qdrant_client()
    logger.info("[LIFESPAN] Qdrant Cloud client initialized.")
    
    # Application is now ready to receive HTTP traffic!
    yield
    
    # Graceful Shutdown Phase
    logger.info("[LIFESPAN] Shutting down application gracefully...")
    await close_db_client()
    logger.info("[LIFESPAN] MongoDB connection pools closed cleanly.")

# Instantiate FastAPI App with Lifespan
app = FastAPI(
    title="VeriDoc Synapse API",
    version="2.3.4",
    lifespan=lifespan
)
```

### Why Lifespan Management Matters:
1. **Zero Connection Leaks**: When a container is restarted or updated, database sockets and vector client connections are cleanly closed, preventing lingering zombie connections on MongoDB Atlas.
2. **Deterministic Startup**: The application will not bind to port 8000 until the database connection and vector collections are verified healthy. If MongoDB credentials are wrong, the server fails fast immediately rather than serving 500 errors to users.

---

## 4. Booting the Server with Uvicorn

In development and production, FastAPI applications are served using **Uvicorn**:

```bash
# Development (with auto-reload on file changes)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Production (single worker for 512MB RAM bounds)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --no-access-log
```

- `app.main:app`: Points to the file `app/main.py` and the FastAPI instance named `app`.
- `--workers 1`: Keeps memory footprint low on 512MB containers. Because of Python's async event loop, a single worker can handle hundreds of concurrent streaming connections.
