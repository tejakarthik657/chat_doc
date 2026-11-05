# 03. Directory & File Walkthrough: The Codebase Anatomy

> *"A great engineer knows their codebase the way a surgeon knows human anatomy: where every nerve runs, why every organ exists, and exactly what happens if one is severed."*

---

## 1. The High-Level Repository Topography

The VeriDoc Synapse repository is bifurcated into two high-performance domains:
- **`rag-backend/`**: An asynchronous Python FastAPI application handling ingestion, ONNX embeddings, hybrid retrieval, resilient multi-key Groq inference, the Model Context Protocol (MCP) server, and background compliance auditing.
- **`veridoc-frontend/`**: A Next.js 16 (React 19) App Router web client featuring paced word-streaming, interactive ActionMesh confirmation cards, a markdown citation renderer, and an interactive Canvas workspace.

```
chat_base/
├── docs/                             # The 20 Master Engineering Handbook chapters
├── rag-backend/                      # FastAPI ASGI Backend Core
│   ├── app/
│   │   ├── main.py                   # ASGI Gateway, Lifespan & Middlewares
│   │   ├── api/routes/               # HTTP & JSON-RPC REST Controllers
│   │   ├── core/                     # Resilience, Multi-Key Pool, Embeddings, Security
│   │   ├── db/                       # Motor Mongo, Qdrant Cloud & Polyglot Connectors
│   │   ├── ingestion/                # PyMuPDF Dual-Mode Parser, Scrapers & Crawlers
│   │   ├── mcp/                      # Inbound EHR DB, Compliance Watcher & ActionMesh
│   │   ├── models/                   # Pydantic Schemas & Data Transfer Objects
│   │   └── rag/                      # Hybrid RRF, Cross-Encoder & CRAG Routing
├── veridoc-frontend/                 # Next.js 16 App Router Frontend
│   └── src/
│       ├── app/                      # Page routes (Dashboard, Chat, Documents, Auth)
│       ├── components/               # UI components (Chat, Canvas, ActionMesh, 3D Hero)
│       └── lib/                      # Axios client, auth helpers & state utilities
```

---

## 2. Backend Deep Dive: File-by-File Anatomy (`rag-backend/app/`)

### A. The Gateway & Ingress Layer

#### [`main.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/main.py) — The ASGI Command Center
- **What it does**: Initializes the FastAPI ASGI application, defines the async `lifespan` context manager (connecting and disconnecting MongoDB and Qdrant pools cleanly), mounts the CORS, `CorrelationIdMiddleware`, `SecurityHeadersMiddleware`, and `RequestSizeLimitMiddleware`, and registers all sub-routers.
- **Key Functions**: `lifespan(app: FastAPI)`, `health_check()`.
- **What happens if you delete it**: The backend cannot boot. Uvicorn has no ASGI entrypoint to bind to.

---

### B. The MCP & ActionMesh Subsystem (`app/mcp/`)

#### [`mcp/db_connector.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/mcp/db_connector.py) — Inbound Clinical Database MCP
- **What it does**: Connects the AI to operational hospital databases (SQLite or PostgreSQL). It inspects schemas, generates parameterized queries, and passes them through an **Abstract Syntax Tree (AST) guard** to guarantee only read-only `SELECT` statements are executed. Automatically seeds test patient EHR data (ALT/AST liver enzymes, creatinine, trial status) if tables are empty.
- **Key Functions**: `execute_clinical_query(sql_query: str)`, `get_clinical_schema()`, `seed_demo_patients()`.
- **Failure Mode**: If missing, the model reverts to passive document-only reading and cannot verify patient biomarkers.

#### [`mcp/watcher.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/mcp/watcher.py) — Autonomous Compliance Watcher
- **What it does**: The background intelligence engine that watches document ingestion. Whenever a new protocol is parsed, this worker scans extracted inclusion/exclusion criteria against historical active trials in MongoDB, running zero-shot contradiction audits without requiring human prompts.
- **Key Functions**: `analyze_document_async(document_id, project_id, content)`, `detect_protocol_contradictions()`.
- **Failure Mode**: Disables background auditing. Contradictions are only found if a human manually crafts a query.

#### [`mcp/actions.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/mcp/actions.py) — Outbound ActionMesh Dispatcher
- **What it does**: Dispatches operational side-effects to external hospital infrastructure. Sends formatted emergency webhooks to Slack channels (`#clinical-safety-alerts`), triggers simulated EDC patient protocol enrollment freezes, and records immutable audit records in MongoDB.
- **Key Functions**: `dispatch_slack_alert(message, severity)`, `trigger_edc_protocol_hold(patient_id, reason)`.
- **Failure Mode**: The AI can identify protocol risks, but cannot notify safety boards or halt dangerous clinical operations.

#### [`mcp/registry.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/mcp/registry.py) — Open MCP Tool Catalog
- **What it does**: Implements the standardized Anthropic Model Context Protocol registry. Maps tool names (`query_clinical_ehr`, `audit_protocol_compliance`, `trigger_compliance_action`) to Python callable functions, validating inputs with Pydantic JSON schemas.
- **Key Functions**: `MCPRegistry.register_tool()`, `MCPRegistry.call_tool()`, `MCPRegistry.list_tools()`.

---

### C. The API Routing Tier (`app/api/routes/`)

| File Path | HTTP Route Prefix | Technical Purpose & Responsibilities |
| :--- | :--- | :--- |
| [`api/routes/chat.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/api/routes/chat.py) | `/api/chat` | Handles conversational turns, Server-Sent Events (SSE) streaming responses, citation binding, and living memory extraction. |
| [`api/routes/mcp.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/api/routes/mcp.py) | `/api/mcp` | Dual-purpose: REST endpoints for EHR queries/actions, and official MCP JSON-RPC 2.0 (`/api/mcp/rpc`) & SSE endpoints (`/api/mcp/sse`). |
| [`api/routes/documents.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/api/routes/documents.py) | `/api/documents` | Multipart document uploads, local encrypted filesystem storage, deletion cascading across Mongo and Qdrant, and status polling. |
| [`api/routes/auth.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/api/routes/auth.py) | `/api/auth` | User registration, login with bcrypt password verification, stateless JWT issuance, and Google OAuth2 exchange. |
| [`api/routes/project.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/api/routes/project.py) | `/api/project` | Multi-tenant clinical trial project workspace CRUD, metadata tagging, and role-based access assignment. |
| [`api/routes/features.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/api/routes/features.py) | `/api/features` | Powers interactive features: Truth Lattice tree building, Socratic Viva examination generation, and What-If hypothesis simulations. |
| [`api/routes/analytics.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/api/routes/analytics.py) | `/api/analytics` | Aggregates document ingestion volume, query latency histograms, and compliance violation frequency metrics. |

---

### D. The AI & Core Resilience Engine (`app/core/`)

#### [`core/groq_resilience.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/core/groq_resilience.py) — 10-Key LPU Load Balancer
- **What it does**: Manages a round-robin pool of 10 Groq API keys. Implements a thread-safe **Token Bucket rate limiter** and an automatic **Circuit Breaker** state machine (`CLOSED -> OPEN -> HALF_OPEN`). When a key hits HTTP 429 (Rate Limit Exceeded), it is quarantined for a 20-second cooldown while traffic seamlessly hops to the next key.
- **Key Classes**: `KeyWorker`, `TokenBucket`, `CircuitBreaker`, `GroqResilienceManager`.

#### [`core/llm_groq.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/core/llm_groq.py) — Clinical Auditor Inference
- **What it does**: Houses the specialized System Prompt for the Senior Clinical & Regulatory Protocol Auditor. Enforces an expanded **`max_tokens=3500`** output budget (fixing the previous 800-token truncation bug) and handles model cascades from `qwen-2.5-32b` to `llama-3.3-70b-versatile`.
- **Key Functions**: `stream_groq_completion()`, `generate_groq_response()`.

#### [`core/llm_local.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/core/llm_local.py) — Air-Gapped Private Engine
- **What it does**: The offline inference runtime. Connects directly to local Ollama instances (`http://127.0.0.1:11434`) running `llama3.1:8b` or `qwen2.5-coder:3b`. Streams tokens locally over standard HTTP without transmitting a single byte outside the VPC.

#### [`core/llm_cloud_fallback.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/core/llm_cloud_fallback.py) — Cloud Failover Provider
- **What it does**: When local models are unavailable and Groq is degraded, this module invokes Google Gemini 1.5 Flash via raw REST calls (`aiohttp`), bypassing heavy client libraries to keep container RAM usage below 50MB.

#### [`core/embeddings.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/core/embeddings.py) — FastEmbed ONNX Engine
- **What it does**: Generates dense 384-dimensional vector embeddings using FastEmbed's ONNX runtime (`bge-small-en-v1.5`). Operates 100% on CPU without requiring PyTorch or CUDA dependencies, consuming less than 60MB of RAM.

#### [`core/bm25.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/core/bm25.py) — Okapi BM25 Sparse Index
- **What it does**: Builds and queries an exact keyword inverted index using the Okapi BM25 algorithm ($k_1=1.5, b=0.75$). Serializes the index to disk using gzip compression for instant cold-start boots.

#### [`core/fusion.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/core/fusion.py) — Reciprocal Rank Fusion (RRF)
- **What it does**: Merges ranked lists from dense vector search (Qdrant) and sparse keyword search (BM25) using the formula:
  $$\text{RRF Score}(d) = \sum_{m \in M} \frac{1}{60 + r_m(d)}$$
  Normalizes disparate score distributions without needing arbitrary calibration constants.

#### [`core/reranker.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/core/reranker.py) — Cross-Encoder Neural Reranker
- **What it does**: Computes cross-attention between the query and candidate passages to eliminate semantic false positives before assembling the final LLM prompt context.

---

### E. Ingestion & Retrieval Orchestration

#### [`ingestion/pipeline.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/ingestion/pipeline.py) — Ingestion Pipeline
- **What it does**: Orchestrates document intake. Uses PyMuPDF for high-speed PDF text and table extraction. Implements hierarchical **Parent-Child Chunking** (300-token child chunks for Qdrant vector indexing; 1200-token parent chunks for context expansion). Upon completion, it fires an asynchronous event triggering `mcp/watcher.py`.

#### [`rag/engine.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/rag/engine.py) — RAG v2 Master Engine
- **What it does**: The central brain connecting user prompts to inference. Inspects the user's Privacy Mode (`fast_cloud` vs `air_gapped_local`), generates HyDE hypothetical documents, performs parallel Qdrant/BM25 retrieval, calls `db_connector.py` if clinical biomarkers are mentioned, applies RRF and reranking, and streams the synthesized response back to the client.

---

## 3. Frontend Deep Dive: File-by-File Anatomy (`veridoc-frontend/src/`)

### A. Next.js 16 App Router Pages (`app/`)
- [`app/layout.tsx`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/veridoc-frontend/src/app/layout.tsx): Injects global theme variables, Inter fonts, and sets the platform metadata (*"VeriDoc Synapse — Autonomous Clinical & Regulatory Intelligence"*).
- [`app/dashboard/chat/[id]/page.tsx`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/veridoc-frontend/src/app/dashboard/chat/[id]/page.tsx): The conversational hub. Handles dynamic session IDs, fetches chat history, and mounts the active workspace.
- [`app/dashboard/documents/upload/page.tsx`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/veridoc-frontend/src/app/dashboard/documents/upload/page.tsx): Document drop-zone supporting multi-file drag-and-drop, real-time chunking progress bars, and compliance scan status badges.
- [`app/dashboard/settings/page.tsx`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/veridoc-frontend/src/app/dashboard/settings/page.tsx): Houses configuration tabs, including API keys, notification webhooks, and the Dual-Privacy mode toggle.

---

### B. Core Interactive Components (`components/chat/` & `components/canvas/`)
- [`components/chat/chat-interface.tsx`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/veridoc-frontend/src/components/chat/chat-interface.tsx):
  The primary user interface. Handles user input, speech-to-text integration, and implements our custom **Paced Word-Streaming Buffer** (grouping incoming SSE tokens into 3-word chunks to reduce React DOM re-renders by 65%). Renders embedded Action Cards.
- [`components/chat/EvidencePanel.tsx`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/veridoc-frontend/src/components/chat/EvidencePanel.tsx):
  The clinical proof pane. Shows the exact document page, raw text chunk, cosine similarity score, and live EHR database rows used to generate the answer.
- [`components/canvas/CanvasWorkspace.tsx`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/veridoc-frontend/src/components/canvas/CanvasWorkspace.tsx):
  A split-screen interactive workspace where clinicians can edit protocol drafts, execute Python code snippets in real-time, and format regulatory submission tables side-by-side with the chat.

---

## 4. The Component Failure & Fallback Matrix

When asked in an interview: *"What happens if service X goes down?"*, reference this exact matrix:

| Component | Failure Condition | Graceful Fallback Mechanism |
| :--- | :--- | :--- |
| **Groq LPU API** | HTTP 429 Rate Limit or 503 Outage | Circuit breaker trips; hops to next key in 10-key pool. If all keys exhaust, cascades to Gemini 1.5 Flash REST, then local Ollama. |
| **Qdrant Vector DB** | Network timeout or Cloud outage | Engine gracefully degrades to pure Okapi BM25 keyword search. System continues functioning without crashing. |
| **Hospital EHR DB** | Connection refused / timeout | Returns a clear diagnostic error card in UI explaining DB is unreachable; continues answering regulatory questions from indexed PDFs. |
| **PyMuPDF Parser** | Corrupted or scanned image PDF | Automatically invokes Cloud OCR / Tesseract fallback parser to extract text from raw bitmap images. |
| **Local Ollama** | Daemon not running (`ConnectionRefused`) | Alerts user that Air-Gapped mode requires Ollama service on port 11434; offers one-click switch to Cloud LPU mode. |

---

## 5. CTO Interview Script: Explaining File Structure

When an interviewer asks: *"Why did you separate `mcp/` from `rag/` instead of bundling everything together?"*, answer:

> *"I deliberately separated `rag/` from `mcp/` to enforce strict architectural decoupling.
> 
> `rag/` is a pure information retrieval engine: it takes a query, computes embeddings, performs hybrid RRF search, reranks passages, and returns ground-truth citations. It is entirely read-only and stateless.
> 
> `mcp/`, on the other hand, is an operational ActionMesh: it holds stateful database connections to operational EHR tables, runs background contradiction monitors (`watcher.py`), and dispatches outward side-effects (`actions.py`) like Slack alerts and EDC protocol freezes. 
> 
> By decoupling them, our retrieval pipeline remains blistering fast and stateless, while our MCP layer can independently evolve to conform to the open Anthropic Model Context Protocol specification. Any external agent—like Claude Desktop or Cursor—can plug into our MCP server without touching our internal RAG implementation."*
