# Phase 2: Architecture & System Design (VeriDoc Synapse)

> *"System architecture is the set of decisions you make that are hard to change later. In VeriDoc Synapse, architecture balances low latency, extreme memory constraints, regulatory auditability, and data privacy."*

---

## 6. Software Architecture
*Monolith, modular monolith, microservices, layered architecture, clean architecture, hexagonal architecture.*

### Architectural Pattern: The Hexagonal Modular Core
Instead of an over-engineered distributed microservice cluster (which adds network latency and operational overhead) or an unmaintainable monolithic script, VeriDoc Synapse uses an **Asynchronous Hexagonal Architecture (Ports and Adapters)** inside a modular FastAPI ASGI core:

```mermaid
graph TD
    subgraph DRIVING_ADAPTERS["Driving Adapters (Input Ports)"]
        A1["Next.js Web Client (REST / SSE)"]
        A2["External MCP Clients (Claude / Cursor over JSON-RPC 2.0)"]
        A3["Async Webhook Listeners"]
    end

    subgraph APPLICATION_CORE["Hexagonal Application Core"]
        CORE_LOGIC["Clinical Intelligence Domain Services"]
        PORT_IN["Inbound Port: ClinicalDBPort"]
        PORT_RAG["Inbound Port: DocumentRetrievalPort"]
        PORT_OUT["Outbound Port: ActionDispatchPort"]
        PORT_LLM["Inbound Port: LLMInferencePort"]
    end

    subgraph DRIVEN_ADAPTERS["Driven Adapters (Output Ports)"]
        AD_DB["SQLite / PostgreSQL EHR Adapter (db_connector.py)"]
        AD_VEC["Qdrant Cloud HNSW Adapter (db/qdrant.py)"]
        AD_ACT["Slack & EDC Webhook Adapter (mcp/actions.py)"]
        AD_LLM["Groq LPU / Local Ollama Adapter (core/llm_*.py)"]
    end

    A1 --> CORE_LOGIC
    A2 --> CORE_LOGIC
    A3 --> CORE_LOGIC

    CORE_LOGIC --> PORT_IN --> AD_DB
    CORE_LOGIC --> PORT_RAG --> AD_VEC
    CORE_LOGIC --> PORT_OUT --> AD_ACT
    CORE_LOGIC --> PORT_LLM --> AD_LLM
```

### Why Hexagonal Architecture Wins for Healthcare AI:
- **Testability**: We can test our entire clinical contradiction reasoning domain by mocking the `ClinicalDBPort` and `LLMInferencePort` without needing live hospital databases or active cloud credits.
- **Provider Agnosticism**: Switching from Groq LPU to local Ollama or Anthropic Claude requires zero changes to core domain logic—only swapping the adapter behind `LLMInferencePort`.

---

## 7. System Design (HLD & LLD)
*High-level design, low-level design, scalability, availability, reliability.*

### High-Level Design (HLD)
The platform is organized into 5 tiers:
1. **Edge & Client Tier**: Next.js 16 App Router on Vercel Edge with client-side token buffering.
2. **Ingress Security Gateway**: FastAPI ASGI with custom middlewares (HSTS, Correlation ID, RequestSizeLimit).
3. **Dual Execution Engine**:
   - *Ingestion Engine*: PyMuPDF extractor, Hierarchical Chunker, Autonomous Compliance Watcher.
   - *Retrieval Engine*: HyDE intent router, parallel Qdrant/BM25 search, Reciprocal Rank Fusion, Cross-Encoder reranker.
4. **Model Context Protocol (MCP) Hub**: Bidirectional server exposing AST-guarded Inbound EHR tools and Outbound ActionMesh dispatchers.
5. **Polyglot Persistence**: MongoDB Atlas (metadata/audits), Qdrant Cloud (dense vectors), and Encrypted Local NVMe / Cloudinary (binary PDFs).

### Low-Level Design (LLD): Component Class Diagram

```mermaid
classDiagram
    class RAGEngine {
        +query(question: str, session_id: str) EventStream
        -route_intent(query: str) Intent
        -retrieve_hybrid(query: str) List~Chunk~
        -rerank_candidates(query: str, chunks: List) List~Chunk~
    }

    class MCPRegistry {
        -tools: Dict~str, Callable~
        +register_tool(name: str, schema: dict, handler: Callable)
        +call_tool(name: str, args: dict) dict
        +list_tools() List~dict~
    }

    class ClinicalDBConnector {
        -db_path: str
        +execute_clinical_query(sql: str) List~dict~
        +get_patient_biomarkers(patient_id: int) dict
        -validate_ast_safety(sql: str) bool
    }

    class GroqResilienceManager {
        -workers: List~KeyWorker~
        -active_index: int
        +execute_with_failover(prompt: str) AsyncGenerator
        -hop_next_key()
    }

    RAGEngine --> MCPRegistry : uses
    MCPRegistry --> ClinicalDBConnector : invokes
    RAGEngine --> GroqResilienceManager : routes inference
```

---

## 8. Component & Module Architecture
*Module boundaries, dependencies, interfaces, separation of concerns.*

```
rag-backend/app/
├── main.py                     # ASGI App Factory, Lifespan Hooks & Global Ingress
├── api/
│   └── routes/                 # HTTP Transport Layer (No business logic)
│       ├── chat.py             # Chat Controller (Validates DTOs, initiates SSE)
│       ├── documents.py        # Ingestion Controller (Receives multipart uploads)
│       └── mcp.py              # MCP Controller (Exposes JSON-RPC 2.0 & SSE)
├── core/                       # Cross-Cutting Technical Infrastructure
│   ├── groq_resilience.py      # Rate-limiting, token buckets, circuit breakers
│   ├── embeddings.py           # FastEmbed ONNX local embedding engine
│   ├── fusion.py               # Reciprocal Rank Fusion algorithm
│   └── security.py             # Cryptographic JWT & BCrypt functions
├── db/                         # Data Access Adapters
│   ├── mongodb.py              # Motor Async Mongo Client
│   └── qdrant.py               # Qdrant Vector Client
├── ingestion/                  # Document Processing Domain
│   ├── pipeline.py             # PyMuPDF parser & parent-child chunker
│   └── crawler.py              # Bounded asynchronous regulatory web crawler
├── mcp/                        # Operational ActionMesh Domain
│   ├── db_connector.py         # Inbound EHR SQL connector with AST guards
│   ├── watcher.py              # Autonomous post-ingestion contradiction detector
│   ├── actions.py              # Outbound Slack / EDC action dispatcher
│   └── registry.py             # Open MCP tool specification catalog
└── rag/                        # Search & Retrieval Domain
    ├── engine.py               # RAG v2 orchestrator
    └── crag.py                 # Corrective RAG evaluator
```

---

## 9. Distributed Systems Design
*Service communication, consistency, fault tolerance, distributed transactions.*

### Distributed Communication Modes
- **Synchronous Ingress (HTTP REST)**: Used for stateless operations (file upload start, auth login, project creation).
- **Asynchronous Event-Driven Ingestion**: The moment document chunks are committed, `pipeline.py` dispatches `asyncio.create_task(compliance_watcher.analyze_document_async(...))`. Ingestion completes in $< 1.2\text{s}$, while auditing runs in the background.
- **Persistent Streaming (SSE)**: Unidirectional event stream delivering tokens, citations, and action cards to the browser over standard HTTP/2.

### Consistency Model
- **Document Metadata**: Strong consistency within MongoDB Atlas replica sets (`w: "majority"`).
- **Vector Indexing**: Eventual consistency in Qdrant Cloud (HNSW graph construction converges within 200ms of upsert).
- **Relational EHR Records**: Strict ACID consistency in SQLite / PostgreSQL, ensuring lab cutoffs and screening records never exhibit dirty reads.

---

## 10. Data Flow Architecture
*Request lifecycle, event flows, state transitions, inter-service communication.*

```mermaid
sequenceDiagram
    autonumber
    actor Clinician as Clinician Browser
    participant Gateway as FastAPI Ingress Gateway
    participant Retrieval as RAG v2 Engine
    participant EHR as Inbound EHR Database
    participant LPU as Groq LPU Cluster
    participant Outbound as Outbound ActionMesh

    Clinician->>Gateway: POST /api/chat/project/1 (with query & session)
    Gateway->>Gateway: SecurityHeaders -> CorrelationId -> JWT Validation
    Gateway->>Retrieval: Execute Joint Retrieval
    
    par Inbound Database Check
        Retrieval->>EHR: AST-Guarded Query: SELECT alt_enzyme FROM patients WHERE patient_id=104
        EHR-->>Retrieval: Live Biomarker: ALT = 74.5 U/L (Elevated)
    and Hybrid Document Search
        Retrieval->>Retrieval: Qdrant (Dense) + BM25 (Sparse) -> RRF (k=60) -> Cross-Encoder
        Retrieval-->>Retrieval: Top Chunks (Protocol Section 5.2 ALT cutoff > 55 U/L)
    end

    Retrieval->>LPU: Synthesize Response (Context = Live EHR + Protocol Parent Chunks)
    LPU-->>Gateway: SSE Stream (Tokens + Citations + Action Needed)
    Gateway-->>Clinician: Paced 3-Word SSE Tokens to UI

    Note over Clinician,Outbound: Clinician clicks "Dispatch EDC Hold" on Action Card
    Clinician->>Gateway: POST /api/mcp/actions/dispatch
    Gateway->>Outbound: Trigger Webhook to Slack & Hospital EDC
    Outbound-->>Clinician: 200 OK (Action Dispatched & Logged in MongoDB)
```

---

## 11. Infrastructure Architecture
*Cloud architecture, networking, compute, storage, environments.*

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           INFRASTRUCTURE TOPOGRAPHY                         │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. Client Edge: Next.js 16 App Router hosted on Vercel Global Edge CDN.     │
│ 2. Backend Compute: Dockerized FastAPI container on Render (Linux 512MB RAM)│
│ 3. Managed Document Store: MongoDB Atlas M0/M10 Cluster (Virginia, us-east-1)│
│ 4. Managed Vector Store: Qdrant Cloud Managed Cluster (Frankfurt / US-East) │
│ 5. Inference Compute: Multi-Key Groq LPU Cloud (Ultra-Fast) + Local Host    │
│    Ollama Runtime (Air-Gapped Private Hospital Perimeter)                   │
│ 6. Binary PDF Storage: Encrypted NVMe local volume mount + Cloudinary CDN   │
└─────────────────────────────────────────────────────────────────────────────┘
```
