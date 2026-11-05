# Master FastAPI Backend Engineering Curriculum: From Beginner to Core Architect

Welcome to **`backend/`** — the comprehensive, engineer-to-engineer mastery guide for the backend framework and systems architecture powering **VeriDoc Synapse**.

If you are coming from an **Express.js (Node.js)** background or are new to Python's asynchronous ecosystem, this curriculum is designed to teach you how modern, high-performance, asynchronous Python backend systems are built, optimized, and deployed in production.

---

## Why FastAPI Over Express.js for Modern AI & Healthcare Backends?

| Architectural Parameter | Express.js (Node.js) | FastAPI (Python ASGI) in VeriDoc |
| :--- | :--- | :--- |
| **Concurrency Model** | Single-threaded Event Loop (V8) | Asyncio Event Loop on C-based `uvloop` |
| **Type Safety & Validation** | Requires third-party libraries (Zod, Joi) | **Native Pydantic v2** compiled in Rust (blazing fast) |
| **API Documentation** | Manual Swagger/JSDoc configuration | **Automatic OpenAPI 3.1 & Swagger UI** (`/docs`) |
| **Machine Learning Interop** | Requires child processes or HTTP hops to Python | **Zero-Copy In-Process Execution** (FastEmbed ONNX, PyMuPDF) |
| **Dependency Injection** | Manual middleware wiring or heavy IoC containers | **Native `Depends()` injection** with dependency graphs |
| **Hardware Performance** | Fast I/O, slow numerical processing | **Fast I/O + C/C++ bindings** for vector math & PDF parsing |

---

## The 10 Mastery Chapters in This Folder

1. **[`01_FASTAPI_AND_PYTHON_ASYNC_FOUNDATIONS.md`](./01_FASTAPI_AND_PYTHON_ASYNC_FOUNDATIONS.md)**  
   *Python Asyncio, ASGI vs WSGI, Uvicorn, Event Loop mechanics, and the application Lifespan context manager (`app/main.py`).*
2. **[`02_MIDDLEWARE_PIPELINE_AND_REQUEST_LIFECYCLE.md`](./02_MIDDLEWARE_PIPELINE_AND_REQUEST_LIFECYCLE.md)**  
   *The anatomy of Starlette/FastAPI middleware: SecurityHeaders, CorrelationId tracing, RequestSizeLimit DoS defense, and CORS.*
3. **[`03_PYDANTIC_V2_DATA_VALIDATION_AND_SCHEMAS.md`](./03_PYDANTIC_V2_DATA_VALIDATION_AND_SCHEMAS.md)**  
   *BaseModels, Field validators, type coercion, JSON serialization, and schema definition in `app/models/schemas.py`.*
4. **[`04_DEPENDENCY_INJECTION_AND_SECURITY.md`](./04_DEPENDENCY_INJECTION_AND_SECURITY.md)**  
   *Mastering `Depends()`, sub-dependencies, OAuth2PasswordBearer, stateless JWT validation, and RBAC in `app/core/security.py`.*
5. **[`05_ROUTING_CONTROLLERS_AND_URL_DESIGN.md`](./05_ROUTING_CONTROLLERS_AND_URL_DESIGN.md)**  
   *APIRouter modularization, URL parameter design, multipart file uploads, and solving the famous route masking bug.*
6. **[`06_DATABASE_DRIVERS_AND_ASYNC_POOLS.md`](./06_DATABASE_DRIVERS_AND_ASYNC_POOLS.md)**  
   *Motor Async MongoDB pooling, Qdrant vector client management, and SQLite/PostgreSQL relational EHR access.*
7. **[`07_SERVER_SENT_EVENTS_AND_STREAMING_APIS.md`](./07_SERVER_SENT_EVENTS_AND_STREAMING_APIS.md)**  
   *Async generators, chunked transfer encoding, `StreamingResponse`, SSE protocol formatting, and client disconnect handling.*
8. **[`08_BACKGROUND_WORKERS_ASYNCIO_AND_CELERY.md`](./08_BACKGROUND_WORKERS_ASYNCIO_AND_CELERY.md)**  
   *When to use `asyncio.create_task` vs FastAPI `BackgroundTasks` vs distributed Celery Redis workers (`celery_app.py`, `tasks.py`).*
9. **[`09_EXTERNAL_INTEGRATIONS_AND_MCP_SERVER.md`](./09_EXTERNAL_INTEGRATIONS_AND_MCP_SERVER.md)**  
   *Asynchronous HTTP with `httpx`, Slack Block Kit webhooks, EDC integrations, and building a JSON-RPC 2.0 MCP server.*
10. **[`10_PRODUCTION_OPTIMIZATION_AND_MEMORY_MANAGEMENT.md`](./10_PRODUCTION_OPTIMIZATION_AND_MEMORY_MANAGEMENT.md)**  
    *CPython memory fragmentation, `pymalloc` heap behavior, `malloc_trim(0)`, Docker multi-stage builds, and surviving 512MB RAM constraints.*
