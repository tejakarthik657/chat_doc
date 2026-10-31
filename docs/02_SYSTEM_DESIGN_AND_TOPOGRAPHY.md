# 02. System Design & Topography

## 1. End-to-End System Topography

```mermaid
flowchart TD
    subgraph CLIENT["Client Edge Tier (Vercel Edge CDN)"]
        UI["Next.js 16 App Router (veridoc-frontend)"]
        AUTH_PAGE["Auth & Google OAuth Callback Handshake"]
        CHAT_UI["Interactive Streaming Chat & Markdown Parser"]
        CANVAS["Canvas Workspace (Live Editor & Python Exec)"]
    end

    subgraph INGRESS["API Gateway & Middleware Layer (FastAPI ASGI)"]
        FASTAPI["FastAPI Application (rag-backend/app/main.py)"]
        CORS_FILTER["Strict Origin CORS Middleware"]
        SEC_HEADERS["SecurityHeadersMiddleware (HSTS, CSP, X-Frame)"]
        CORR_ID["CorrelationIdMiddleware (UUID Distributed Tracing)"]
        SIZE_LIMIT["RequestSizeLimitMiddleware (50 MB Max Ingress)"]
        AUTH_GUARD["OAuth2 / JWT Verification Guard (security.py)"]
    end

    subgraph INGESTION["ETL & Autonomous Extraction Pipeline"]
        UPLOAD_ROUTER["Documents & Project Ingestion (documents.py / project.py)"]
        CRAWLER["Domain-Locked Async Web Spider (crawler.py)"]
        PDF_PARSER["PyMuPDF Dual-Mode Extractor (pipeline.py)"]
        PARENT_CHILD["Hierarchical Parent-Child Chunking Engine"]
        CLOUDINARY_GW["Cloudinary Binary Streaming (storage_cloudinary.py)"]
    end

    subgraph RETRIEVAL["RAG v2 Hybrid Retrieval Pipeline (rag/engine.py)"]
        QUERY_ROUTER["Intent & Metadata Classifier (router.py)"]
        HYDE["HyDE Hypothetical Document Expander (hyde.py)"]
        DENSE_RETRIEVAL["Dense Vector Retrieval (Qdrant Cloud)"]
        SPARSE_RETRIEVAL["Sparse Keyword Retrieval (Durable Okapi BM25)"]
        RRF["Reciprocal Rank Fusion k=60 (fusion.py)"]
        RERANKER["Cross-Encoder Neural Reranker (reranker.py)"]
        CRAG["Corrective RAG Relevance Grader (crag.py)"]
    end

    subgraph INFERENCE["Multi-Model Resilient LLM Pool"]
        RESILIENT_POOL["ResilientGroqClient (groq_resilience.py)"]
        KEY_WORKERS["10-Key TokenBucket & CircuitBreaker Worker Pool"]
        QWEN["Primary: Qwen 2.5 27B (qwen/qwen3.8-27b)"]
        GPT_120B["Secondary: GPT OSS 120B (openai/gpt-oss-120b)"]
        GPT_20B["Tertiary: GPT OSS 20B (openai/gpt-oss-20b)"]
        CLOUD_FALLBACK["Emergency REST: Gemini 1.5 Flash / OpenRouter"]
    end

    subgraph PERSISTENCE["Polyglot Persistence Tier"]
        MONGO[("MongoDB Atlas: Metadata, Chunks, Chat, BM25")]
        QDRANT[("Qdrant Cloud: Multi-Project Dense Vectors")]
        CLOUDINARY_CDN[("Cloudinary CDN: Raw PDF Binaries & Media Assets")]
    end

    CLIENT -->|HTTPS / REST| INGRESS
    INGRESS --> INGESTION
    INGRESS --> RETRIEVAL
    INGESTION --> CLOUDINARY_GW --> CLOUDINARY_CDN
    INGESTION --> MONGO
    INGESTION --> QDRANT
    RETRIEVAL --> DENSE_RETRIEVAL --> QDRANT
    RETRIEVAL --> SPARSE_RETRIEVAL --> MONGO
    RETRIEVAL --> RRF --> RERANKER --> CRAG --> INFERENCE
    INFERENCE --> RESILIENT_POOL --> KEY_WORKERS
    KEY_WORKERS --> QWEN
    KEY_WORKERS -.->|Failover| GPT_120B
    KEY_WORKERS -.->|Failover| GPT_20B
    KEY_WORKERS -.->|Emergency REST| CLOUD_FALLBACK
```

---

## 2. Ingress & Middleware Pipeline Execution Order

Every incoming HTTP request processed by `rag-backend/app/main.py` traverses a strict sequential middleware stack:

```
[Incoming HTTP Request from Vercel Edge]
                │
                ▼
1. SecurityHeadersMiddleware (rag-backend/app/core/security_headers.py)
   - Injects X-Content-Type-Options: nosniff
   - Injects X-Frame-Options: DENY
   - Injects Strict-Transport-Security (HSTS)
   - Injects Content-Security-Policy (CSP)
                │
                ▼
2. CorrelationIdMiddleware (rag-backend/app/main.py)
   - Inspects headers for incoming 'X-Correlation-ID'
   - Generates unique UUID4 if absent
   - Binds correlation ID to current task context for distributed log tracing
                │
                ▼
3. RequestSizeLimitMiddleware (rag-backend/app/main.py)
   - Inspects Content-Length header
   - Rejects payloads exceeding 50 MB (HTTP 413 Payload Too Large)
                │
                ▼
4. CORSMiddleware (FastAPI Standard)
   - Enforces origin whitelisting:
     * https://nexus-tawny-seven-50.vercel.app
     * http://localhost:3000 / http://127.0.0.1:3000
   - Configures Access-Control-Allow-Credentials: true
                │
                ▼
5. Route Handler Execution & Global Exception Handler (FastAPI)
   - Dispatches to /api/auth, /api/documents, /api/projects, /api/chat, /api/features
   - Catches unhandled exceptions, returning structured JSON with X-Correlation-ID
```
