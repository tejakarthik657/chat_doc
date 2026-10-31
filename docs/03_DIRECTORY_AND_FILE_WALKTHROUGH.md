# 03. Directory & File Walkthrough

## 1. Backend Topography (`rag-backend/app/`)

| File Path | Functional Responsibility & Technical Purpose |
| :--- | :--- |
| [`main.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/main.py) | **ASGI App Entrypoint**: Configures middlewares (CORS, CorrelationId, SecurityHeaders), registers routers, handles lifespan lifecycle, and exposes `/health`. |
| [`core/config.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/core/config.py) | **Pydantic Settings**: Validates and parses environment variables, API keys, database connection strings, and default thresholds. |
| [`core/security.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/core/security.py) | **Security & JWT Engine**: Handles password hashing (`bcrypt`), JWT token generation and validation, and FastAPI user dependencies (`get_current_user`). |
| [`core/security_headers.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/core/security_headers.py) | **OWASP Security Middleware**: Injects strict HTTP response headers (`HSTS`, `X-Content-Type-Options`, `X-Frame-Options`, `Content-Security-Policy`). |
| [`core/groq_resilience.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/core/groq_resilience.py) | **Multi-Key Inference Pool**: Implements `KeyWorker`, `TokenBucket`, and `CircuitBreaker` across 10 Groq API keys with zero-downtime failover. |
| [`core/llm_groq.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/core/llm_groq.py) | **Inference Orchestrator**: Houses the Executive System Prompt, enforces `max_tokens=3500`, and manages model fallbacks (`qwen2.5` $\rightarrow$ `gpt-oss` $\rightarrow$ `gemini`). |
| [`core/llm_cloud_fallback.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/core/llm_cloud_fallback.py) | **REST Failover Provider**: Direct HTTP calls to Google Gemini 1.5 Flash and OpenRouter, bypassing local CPU/RAM limits. |
| [`core/embeddings.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/core/embeddings.py) | **Vector Generation & FAISS**: Dual support for FastEmbed and SentenceTransformers with automated normalization and FAISS indexing. |
| [`core/bm25.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/core/bm25.py) | **Durable Sparse Keyword Search**: Tokenizes queries and text chunks, computes Okapi BM25 scores, and serializes indices to MongoDB Atlas. |
| [`core/fusion.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/core/fusion.py) | **Reciprocal Rank Fusion (RRF)**: Implements score-agnostic rank combination ($k=60$) across dense and sparse result sets. |
| [`core/reranker.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/core/reranker.py) | **Cross-Encoder Precision Scorer**: Runs cross-attention re-scoring (`ms-marco-MiniLM-L-6-v2`) on candidate retrieval chunks. |
| [`core/storage_cloudinary.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/core/storage_cloudinary.py) | **Cloud CDN Storage**: Streams uploaded PDF binaries directly to Cloudinary, decoupling file storage from MongoDB. |
| [`db/mongodb.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/db/mongodb.py) | **Asynchronous Mongo Client**: Motor connection pool initialization, indexing, and collection accessor factories. |
| [`db/qdrant.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/db/qdrant.py) | **Vector Cloud Interface**: Qdrant Cloud client management, collection creation, point upserts, and payload metadata queries. |
| [`db/neo4j.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/db/neo4j.py) | **Graph Database Connector**: Graph model support for entity relationships, dependencies, and citation graphs. |
| [`ingestion/crawler.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/ingestion/crawler.py) | **Autonomous Async Spider**: Domain-locked web scraper with URL canonicalization, depth bounding, and PDF stream handling. |
| [`ingestion/pipeline.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/ingestion/pipeline.py) | **Extraction Pipeline**: PyMuPDF extraction, OCR fallbacks, and hierarchical Parent-Child chunk generation. |
| [`rag/engine.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/rag/engine.py) | **RAG v2 Orchestration Engine**: Central pipeline executing hybrid retrieval, RRF, reranking, memory assembly, and verification. |
| [`rag/router.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/rag/router.py) | **Semantic Query Router**: Identifies target departments, intent, and document types for targeted metadata filtering. |
| [`rag/hyde.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/rag/hyde.py) | **Hypothetical Document Embeddings**: Generates theoretical answer documents for low-context queries to improve vector recall. |
| [`rag/crag.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/rag/crag.py) | **Corrective RAG Grader**: Evaluates chunk relevance prior to generation and triggers query rewrites on low-confidence matches. |
| [`api/routes/auth.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/api/routes/auth.py) | **Auth Controller**: User registration, login, JWT token issuance, and Google OAuth 2.0 exchange. |
| [`api/routes/documents.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/api/routes/documents.py) | **Document Management Controller**: PDF upload, Cloudinary handoff, status polling, and chunk inspection. |
| [`api/routes/project.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/api/routes/project.py) | **Project Workspace Controller**: Crawl task lifecycle management, knowledge base status, and project configuration. |
| [`api/routes/chat.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/api/routes/chat.py) | **Chat Execution Controller**: Endpoints for single-doc RAG, project knowledge bases, and Open Global Knowledge (General AI). |
| [`api/routes/features.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/api/routes/features.py) | **Advanced Features Controller**: Endpoints for Truth Lattice audits, Socratic Viva sessions, and Canvas transforms. |

---

## 2. Frontend Topography (`veridoc-frontend/src/`)

| File Path | Functional Responsibility & Technical Purpose |
| :--- | :--- |
| [`app/layout.tsx`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/veridoc-frontend/src/app/layout.tsx) | **Root Application Layout**: Injects global styles, fonts, meta tags, and root React context providers. |
| [`app/login/page.tsx`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/veridoc-frontend/src/app/login/page.tsx) | **Login Interface**: User credential authentication with automated backend health warmup ping to prevent cold-start delays. |
| [`app/dashboard/projects/[project_id]/page.tsx`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/veridoc-frontend/src/app/dashboard/projects/[project_id]/page.tsx) | **Multi-Tab Project Workspace**: Main interface managing chat, inventory, knowledge graphs, and live crawl metrics. |
| [`components/chat/chat-interface.tsx`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/veridoc-frontend/src/components/chat/chat-interface.tsx) | **Chat Interface**: Manages message histories, inline citations, paced word streaming, and Markdown rendering. |
| [`components/canvas/CanvasWorkspace.tsx`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/veridoc-frontend/src/components/canvas/CanvasWorkspace.tsx) | **Canvas Workspace**: Side-by-side split screen for real-time Markdown document editing, note taking, and code execution. |
| [`components/features/TruthLatticeModal.tsx`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/veridoc-frontend/src/components/features/TruthLatticeModal.tsx) | **Truth Lattice Auditor**: Modal component running cross-model adversarial analysis to identify factual inconsistencies. |
| [`components/features/SocraticVivaModal.tsx`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/veridoc-frontend/src/components/features/SocraticVivaModal.tsx) | **Socratic Viva Examiner**: Interactive examination interface testing user understanding via multi-turn questioning. |
| [`components/features/LivingCodeSandbox.tsx`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/veridoc-frontend/src/components/features/LivingCodeSandbox.tsx) | **Interactive Code Runner**: Sandboxed Python execution interface for verifying formulas and data directly in the browser. |
| [`services/chat.service.ts`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/veridoc-frontend/src/services/chat.service.ts) | **Chat API Client**: Axios client handling queries to single documents, project knowledge bases, and General AI. |
| [`services/project.service.ts`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/veridoc-frontend/src/services/project.service.ts) | **Project API Client**: Handles project creation, crawl triggers, status polling, and memory resets. |
