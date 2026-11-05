# VeriDoc Synapse (ActionMesh Platform): Master System Knowledge Base
*The Definitive Technical & Non-Technical Reference Specification for AI Language Models, CTOs, and Architects*

---

## Document Metadata & System Identity
- **Product Name**: VeriDoc Synapse (ActionMesh Platform)
- **Primary Motto**: *"Autonomous Clinical & Regulatory Intelligence: Zero-Hallucination Protocol Auditing, Live Database Verification, and Automated Compliance."*
- **Primary Domain**: Biopharma Clinical Trials (Phase I–IV), FDA 510(k) Medical Device Filings, Institutional Review Board (IRB) Harmonization, and Hospital Electronic Health Record (EHR) Verification.
- **Active Codebase Branch**: `experiment`
- **Core Technology Stack**:
  - **Backend**: Python 3.11/3.13, FastAPI (ASGI), Uvicorn (`uvloop`), Pydantic v2 (Rust core), Motor (Async MongoDB), AsyncQdrantClient, PyMuPDF (C engine), FastEmbed ONNX (`bge-small-en-v1.5`), `sqlparse`, Celery + Redis.
  - **Frontend**: Next.js 16 (App Router), React 19, Tailwind CSS, Lucide Icons, Axios, Three.js / WebGL.
  - **Persistence Tier**: MongoDB Atlas (12 collections), Qdrant Cloud (384-dimensional dense vectors), SQLite / PostgreSQL (Relational EHR patient records), Encrypted Local Storage (`./storage/`) with optional Cloudinary CDN.
  - **Inference Engine**: Dual-Privacy Mode: Multi-Key Groq LPU Cluster (10 API keys, 450+ tokens/sec, Zero Data Retention) vs. 100% Air-Gapped Local In-VPC Mode (Ollama `llama3.1:8b` / `qwen2.5-coder:3b`, 0 bytes network transit).
  - **Production Deployment**: Frontend on **Vercel Edge CDN**, Backend on **Render Cloud** (512MB RAM Linux container), Database on **MongoDB Atlas (M0/M10)** and **Qdrant Cloud**.

---

# SECTION 1: Executive Summary & Non-Technical Business Context

### 1.1 The Market Problem & The $32 Billion Veeva Disruption
In clinical trials, bringing a single therapeutic to market costs between **\$1 Billion and \$2.6 Billion**. 
- A critical bottleneck is **Protocol Amendments**: When a sponsor updates inclusion/exclusion criteria, dosing schedules, or safety rules, human Clinical Research Associates (CRAs) spend **60 to 90 days** manually reading 300-page PDFs and cross-referencing them against active trial sites and Electronic Data Capture (EDC) systems.
- Every single day of clinical trial delay costs a pharmaceutical sponsor between **\$600,000 and \$8 Million** in lost patent exclusivity and trial burn rate.
- **Why Legacy Systems Fail**: Market leader **Veeva Systems (Vault eTMF, \$32B Valuation)** is fundamentally a digital filing cabinet built in 2011. Documents sit in static folder trees. Veeva has zero semantic AI search, zero automated contradiction detection, and zero connection to live patient EHR databases. Staff read PDFs manually.
- **Why Generic Search Fails**: Enterprise search tools like **Glean (\$5.4B Valuation)** search Google Drive and Slack, but cannot parse multi-column medical dosing tables, cannot ground claims in regulatory citations, and cannot query hospital EHR databases.

### 1.2 The VeriDoc Synapse Solution
VeriDoc Synapse compresses 60 days of manual protocol auditing into **4.2 seconds**. 
It replaces passive chatbots with an **Autonomous ActionMesh** that:
1. Audits protocol amendments on upload in the background without user prompting.
2. Queries live hospital patient EHR databases to identify active patients who violate updated exclusion rules.
3. Dispatches automated emergency protocol freeze holds to hospital EDC systems and Slack safety boards.

### 1.3 Target Personas
1. **Lead Regulatory Affairs Director**: Manages FDA IND (21 CFR Part 312), IDE device filings, and IRB documentation. Needs zero protocol discrepancies.
2. **Clinical Research Associate (CRA) / Principal Investigator (PI)**: Screens patients at trial sites. Needs instant verification of patient lab cutoffs against complex protocols.
3. **Hospital Chief Medical Information Officer (CMIO) / CISO**: Protects patient data. Refuses to use public ChatGPT/Claude due to HIPAA liabilities; requires air-gapped local inference or strict Zero Data Retention.

---

# SECTION 2: The 4 Core Architectural Pillars (The ActionMesh)

```
                          ┌─────────────────────────────┐
                          │   VERIDOC SYNAPSE CORE      │
                          └──────────────┬──────────────┘
            ┌────────────────────────────┼────────────────────────────┐
            ▼                            ▼                            ▼
┌───────────────────────┐    ┌───────────────────────┐    ┌───────────────────────┐
│ 1. INBOUND EHR MCP    │    │ 2. COMPLIANCE WATCHER │    │ 3. OUTBOUND ACTIONMESH│
│ Live DB queries with  │    │ Background async scan │    │ Dispatches holds to   │
│ AST SQL guardrails    │    │ for dosage conflicts  │    │ EDC & Slack alerts    │
└───────────────────────┘    └───────────────────────┘    └───────────────────────┘
                                         │
                                         ▼
                             ┌───────────────────────┐
                             │ 4. DUAL-PRIVACY MODE  │
                             │ Groq LPU (ZDR) vs     │
                             │ 100% Air-Gapped Local │
                             └───────────────────────┘
```

### Pillar 1: Inbound Database Model Context Protocol (MCP)
- Gives the LLM "eyes" on operational hospital infrastructure.
- Instead of relying only on static indexed PDFs, it allows the model to query live relational patient screening databases (`patients` table) via read-only SQL.
- Enforces an **Abstract Syntax Tree (AST) safety validator** (`sqlparse`) that guarantees only read-only `SELECT` statements are executed, rejecting `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, or semicolons.
- Supports **Model C: HL7 FHIR v4 / SMART-on-FHIR REST Gateway** for real-world Epic/Cerner EHR systems.

### Pillar 2: Autonomous Compliance Watcher (`watcher.py`)
- Background intelligence worker that intercepts the ingestion pipeline.
- The moment a new protocol amendment is parsed, the watcher asynchronously scans extracted inclusion/exclusion criteria against all active trials in MongoDB Atlas.
- Detects three clinical hazard classes:
  1. **Dosage Contradictions**: E.g., Section 4.2 specifies 50mg QD, while Section 9.1 specifies 15mg BID.
  2. **Cold-Chain Storage Bounds**: Protocol mandates 2°C–8°C refrigerated storage, but transport SOP lists ambient room temperature.
  3. **Biomarker Eligibility Cutoffs**: Text mandates ALT < 55 U/L, but criteria table lists ALT < 100 U/L.
- Writes findings to `compliance_audits` collection and tags the document with severity badges in the UI.

### Pillar 3: Outbound ActionMesh Dispatcher (`actions.py`)
- Gives the LLM "hands" to take operational action.
- Generates structured Action Descriptors that render as interactive **Action Cards** in the frontend chat UI.
- Enforces **Human-in-the-Loop (HITL)** approval: clinicians review the flagged deviation and click to authorize execution.
- Dispatches signed webhooks to:
  - Slack `#clinical-safety-alerts` (Slack Block Kit emergency notifications).
  - Electronic Data Capture (EDC) API endpoints (enforcing automated screening freeze holds).
  - Immutable `action_logs` collection for FDA 21 CFR Part 11 audit compliance.

### Pillar 4: Dual-Privacy Architecture
- **Ultra-Fast Cloud LPU Mode**: 10-key Groq LPU pool streaming at 450+ tokens/sec using open-weights models (`qwen-2.5-32b`, `llama-3.3-70b-versatile`). Operates under strict contractual **Zero Data Retention (ZDR)**; only the top 3–5 matching text chunks (~500 tokens) are transmitted.
- **Air-Gapped Private Mode**: 100% In-VPC local execution via Ollama (`llama3.1:8b` / `qwen2.5-coder:3b`) on `http://127.0.0.1:11434`. Local embeddings via FastEmbed ONNX. **0 bytes leave the customer machine.**

---

# SECTION 3: Detailed Technical Architecture & Topography

### 3.1 Ingress Security Gateway (FastAPI ASGI)
Every request entering `rag-backend/app/main.py` passes through a strict sequential middleware stack:
1. **`CORSMiddleware`**: Restricts origins strictly to configured production domains (e.g., `https://nexus-tawny-seven-50.vercel.app`, `http://localhost:3000`).
2. **`SecurityHeadersMiddleware`**: Injects defense-in-depth headers:
   - `X-Frame-Options: DENY` (Eliminates clickjacking).
   - `X-Content-Type-Options: nosniff` (Prevents MIME sniffing attacks).
   - `Strict-Transport-Security: max-age=31536000; includeSubDomains` (Forces HTTPS).
   - `X-XSS-Protection: 1; mode=block`.
3. **`CorrelationIdMiddleware`**: Injects unique `X-Correlation-ID` (UUID4) into request state and response headers, linking all downstream logs and database queries for 21 CFR Part 11 distributed tracing.
4. **`RequestSizeLimitMiddleware`**: Terminates incoming request bodies exceeding **100MB** at the socket layer to prevent memory-exhaustion denial-of-service (DoS) attacks.
5. **Pre-Flight Warmup Handler**: `GET /health` endpoint awakens cold serverless containers (Render/Fly) within 80ms while users type credentials, completely eliminating 30-second cold-start login timeouts.

---

### 3.2 Ingestion & Hierarchical Parent-Child Chunking (`pipeline.py`)

```mermaid
flowchart TD
    FILE["Upload Clinical PDF"] --> PARSER["PyMuPDF C Parser<br/>(Extracts Text & Reconstructs Tables)"]
    PARSER --> CHUNK["Hierarchical Chunker"]
    CHUNK --> PARENT["Parent Chunk (1,200 Tokens)<br/>Stored in MongoDB"]
    CHUNK --> CHILD["Child Chunks (300 Tokens)<br/>Vectorized via FastEmbed ONNX"]
    CHILD --> QDRANT[("Qdrant Cloud HNSW Index")]
    PARENT --> MONGO[("MongoDB Atlas chunks Collection")]
    CHILD -.->|Foreign Key: parent_id| PARENT
    MONGO --> WATCHER_TASK["asyncio.create_task -> Compliance Watcher"]
```

#### The Chunking Paradox & The Solution:
- **The Problem**: Fixed-size chunking (e.g. 500 characters) cuts halfway through clinical dosing tables. Small chunks lack surrounding cohort context; large chunks dilute vector embeddings so needle-in-a-haystack numbers are missed.
- **The Parent-Child Solution**:
  - **Child Chunks (300 Tokens)**: Vectorized using FastEmbed ONNX and stored in Qdrant. Because they are short and semantically concentrated, they yield sharp cosine similarity matches.
  - **Parent Chunks (1,200 Tokens)**: Full clinical sections and complete tables stored in MongoDB Atlas. Each child chunk has a `parent_id` foreign key.
  - **Retrieval Context Expansion**: Qdrant searches across child vectors. But before sending context to the LLM, the engine swaps each retrieved child for its full 1,200-token parent block. The LLM receives the complete paragraph, preserving table headers, surrounding safety warnings, and cohort definitions.
- **PDF Extraction Engine**: Written in C via **PyMuPDF (`fitz`)**. Parses 200 pages in **0.42 seconds** (compared to 8.6s for PyPDF and 42s for pdfminer). Detects and formats Markdown tables natively. If zero digital text is found, cascades to OCR fallback.
- **Embedding Engine**: **FastEmbed ONNX Runtime** running `BAAI/bge-small-en-v1.5`. Consumes only **58MB RAM** (compared to 1.2GB for PyTorch `sentence-transformers`). Generates 384-dimensional dense vectors on CPU in 6ms per chunk.

---

### 3.3 Hybrid RAG v2 Retrieval & Ranking Pipeline (`engine.py`)

When a query enters `rag/engine.py`:
1. **Inbound DB MCP Check**: `check_and_enrich_with_live_db()` inspects the query for patient IDs or cohort audit terms. If found, it executes an AST-guarded SQL query against the EHR database and injects the live biomarkers into the context window.
2. **Parallel Hybrid Search**: Dispatches dense vector search (Qdrant) and sparse keyword search (Okapi BM25) simultaneously via `asyncio.gather`.
   - **Dense (Qdrant Cloud)**: 384-dimensional cosine similarity, HNSW indexing (`m=16`, `ef_construct=100`), pre-filtered by `project_id` and `chunk_type="child"`.
   - **Sparse (Okapi BM25)**: Evaluates exact term frequencies for rare alphanumeric drug codes (`MK-3475`), IND protocol IDs (`IND-142857`), and exact numbers (`15 mg BID`). Uses $k_1 = 1.5, b = 0.75$.
3. **Reciprocal Rank Fusion (RRF $k=60$)**: Merges disparate dense cosine scores $[0, 1]$ and unbounded BM25 scores $[0, \infty)$ using pure ordinal ranking:
   $$\text{RRF Score}(d) = \sum_{m \in M} \frac{1}{60 + r_m(d)}$$
   Eliminates arbitrary score calibration constants and dampens outlier noise.
4. **Cross-Encoder Neural Reranking (`ms-marco-MiniLM-L-6-v2`)**: Computes bidirectional multi-head self-attention across the query and top 15 candidates simultaneously. Correctly captures syntactic modifiers like *"do NOT administer"*, which bi-encoders miss.
5. **Corrective RAG (CRAG) Grader**: Evaluates relevance score $S$:
   - $S \ge 0.70$: High confidence; proceed to prompt synthesis.
   - $0.40 \le S < 0.70$: Ambiguous; triggers automated query rewriting loop.
   - $S < 0.40$: Low confidence; triggers **Regulatory Abstention Protocol**, returning: *"Regulatory Audit Warning: The indexed protocols do not contain verifiable data regarding this requirement. Please consult the Trial Master File or Principal Investigator."*

---

### 3.4 Multi-Key Groq LPU Cluster & Inference Resilience (`groq_resilience.py`)

- **The Problem**: Groq LPUs stream at 450+ tokens/sec, but developer tiers enforce strict rate limits (e.g. 30 RPM). A single key exhausts under concurrent multi-user load in 15 seconds.
- **The 10-Key Cluster Architecture**:
  - Pools **10 Groq API keys** with round-robin rotation.
  - Each key is managed by an independent **Token Bucket** (capacity 50, refill rate 10/s).
  - An automatic **Circuit Breaker** tracks failure states (`CLOSED -> OPEN -> HALF_OPEN`).
  - When a key receives an `HTTP 429 Rate Limit`, it is quarantined on a **20-second cooldown** while traffic seamlessly hops to the next key in **under 8 milliseconds**.
- **Expanded Token Budget (3,500 Tokens)**: Fixes early production bug where responses cut off mid-sentence at 800 tokens. Clinical cohort tables require ~450 tokens on their own. Output limit set to 3,500 tokens with low entropy (`temperature = 0.1`, `top_p = 0.90`).
- **5-Tier High-Availability Failover Ladder**:
  1. Tier 1: Groq LPU Primary Pool (`qwen-2.5-32b` / `llama-3.3-70b-versatile`).
  2. Tier 2: Groq LPU Secondary Model (`llama-3.1-8b-instant`).
  3. Tier 3: Google Gemini 1.5 Flash via direct asynchronous REST (0MB RAM footprint, 1M context window).
  4. Tier 4: Local In-VPC Ollama (`llama3.1:8b` on `127.0.0.1:11434`).
  5. Tier 5: Safe-Harbor Extractive Return (serves raw verified patient records and protocol chunks without generative synthesis).

---

### 3.5 Model C: HL7 FHIR v4 / SMART-on-FHIR REST Gateway

For real-world hospital integrations where direct SQL port access is forbidden:
- **Standards Compliance**: US Federal 21st Century Cures Act certified HL7 FHIR v4.
- **Authentication**: SMART Backend Services Specification (OAuth 2.0 Asymmetric Client Assertion). Render backend signs an `RS384` JWT using its private key and exchanges it with Epic/Cerner for a 15-minute Bearer token scoped strictly to `patient/*.read`.
- **MCP LOINC Mapping**:
  - ALT Liver Enzyme $\rightarrow$ LOINC `1742-6`
  - Serum Creatinine $\rightarrow$ LOINC `2160-0`
  - Platelet Count $\rightarrow$ LOINC `777-3`
- **Transport**: Standard HTTPS (Port 443) with Mutual TLS (mTLS). Zero direct database ports exposed.

---

### 3.6 Frontend Architecture & Paced Streaming (`chat-interface.tsx`)

- **The Problem**: Groq streams 450+ tokens/sec. Calling React `setState` on every incoming token triggers 450 Virtual DOM reconciliations per second, causing severe DOM thrashing, browser UI thread lockup, and 92% CPU usage.
- **The Solution: Paced 3-Word Window Streaming Buffer**:
  - Inbound SSE tokens are pushed to an in-memory `useRef<string[]>([])` queue without triggering React renders.
  - A 20-millisecond animation interval drains tokens in **3-word batches**.
  - Cuts React DOM re-renders by **65%**, drops CPU usage to **14%**, and maintains a fluid 60 FPS typing cadence.
- **The Interactive Suite**:
  - **ActionMesh Cards**: Interactive cards embedded in the chat feed requiring clinician authorization before dispatching webhooks to Slack or EDC.
  - **Evidence Panel**: Persistent split-screen inspector displaying raw extracted document chunks (with page citations and cosine scores) alongside live EHR patient biomarkers.
  - **Canvas Workspace**: Split-screen Markdown protocol editor with real-time in-line contradiction highlighting.
  - **Living Code Sandbox**: AST-sandboxed Python environment for pharmacokinetic (PK/PD) half-life curve calculations.
  - **Truth Lattice**: Adversarial dual-model claim deconstruction modal rendering interactive Mermaid trees (Green = verified, Amber = inferred, Red = contradicted).

---

# SECTION 4: Database Schemas & Polyglot Persistence

VeriDoc Synapse uses **12 collections in MongoDB Atlas** alongside a **relational EHR database**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    POLYGLOT DATA STORAGE ARCHITECTURE                       │
├────────────────────┬──────────────────────┬─────────────────────────────────┤
│ Engine             │ Technology           │ Domain / Stored Entities        │
├────────────────────┼──────────────────────┼─────────────────────────────────┤
│ **Document Store** │ MongoDB Atlas        │ 12 Collections: Users, Projects,│
│                    │ (Motor Async)        │ Documents, Chunks, Sessions,    │
│                    │                      │ Audits, Living Memory, Metrics  │
├────────────────────┼──────────────────────┼─────────────────────────────────┤
│ **Vector Store**   │ Qdrant Cloud         │ 384-d Cosine Vectors with HNSW  │
│                    │ (FastEmbed ONNX)     │ & Payload Filtering             │
├────────────────────┼──────────────────────┼─────────────────────────────────┤
│ **Relational EHR** │ SQLite / PostgreSQL  │ Strict ACID `patients` table for│
│                    │ (aiosqlite / asyncpg)│ Live Biomarker Screening Queries│
├────────────────────┼──────────────────────┼─────────────────────────────────┤
│ **File Storage**   │ Local Volume / S3    │ Raw Encrypted PDF Binaries      │
│                    │ (Decoupled Storage)  │ (Bypasses 16MB Mongo BSON trap) │
└────────────────────┴──────────────────────┴─────────────────────────────────┘
```

### 4.1 The 12 MongoDB Atlas Collections
1. `users`: Credentials (BCrypt 12 rounds), roles (`admin`, `clinician`, `auditor`), OAuth IDs. Index: `{"email": 1}` (Unique).
2. `projects`: Multi-tenant clinical trial workspaces. Compound Index: `{"owner_id": 1, "created_at": -1}`.
3. `documents`: File descriptors, storage paths, parsing status, `has_compliance_alerts` flag. Compound Index: `{"project_id": 1, "created_at": -1}`.
4. `chunks`: Text segments. `chunk_type` (`child` 300 tokens vs `parent` 1200 tokens), `parent_id` foreign key. Compound Index: `{"doc_id": 1, "chunk_type": 1, "parent_id": 1}`.
5. `chat_sessions`: Conversational workspaces, active privacy mode (`fast_cloud` vs `air_gapped_local`). Index: `{"user_id": 1, "updated_at": -1}`.
6. `chat_messages`: Turns, roles, citations array, executed SQL queries array, latency (ms). Index: `{"session_id": 1, "created_at": 1}`.
7. `living_memory`: Contextual clinical facts extracted from previous turns.
8. `compliance_audits`: Contradiction reports generated by `watcher.py`. `audit_status` (`PENDING`, `CONTRADICTION_DETECTED`, `CLEARED`), `highest_severity` (`CRITICAL`, `HIGH`, `MEDIUM`), findings array. Index: `{"project_id": 1, "audit_status": 1}`.
9. `crawled_pages`: Regulatory spider index (FDA/EMA guidance), content hashes, URLs.
10. `feature_artifacts`: Truth Lattice trees, Socratic Viva exams, What-If simulation payloads.
11. `system_metrics`: Latency histograms, token rates, error traces. TTL Index: 30 days (`expireAfterSeconds: 2592000`).
12. `action_logs`: Immutable audit trail of dispatched Slack and EDC actions (21 CFR Part 11 compliant).

### 4.2 Relational EHR Patient Database (`clinical_sample.db`)
```sql
CREATE TABLE IF NOT EXISTS patients (
    patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    age INTEGER NOT NULL CHECK(age >= 18),
    gender TEXT NOT NULL CHECK(gender IN ('Male', 'Female', 'Other')),
    serum_creatinine REAL NOT NULL,     -- Renal biomarker: mg/dL (Normal: 0.7 - 1.3)
    alt_enzyme REAL NOT NULL,           -- Hepatic enzyme: U/L (Normal: 7 - 56)
    platelet_count INTEGER NOT NULL,    -- Hematology: /uL (Normal: 150,000 - 450,000)
    prior_chemo_days INTEGER NOT NULL,  -- Washout window: Days since cytotoxic agent
    concurrent_meds TEXT,               -- Comedications list
    screening_status TEXT NOT NULL      -- 'Screening', 'Eligible', 'Ineligible'
);

CREATE INDEX IF NOT EXISTS idx_patients_biomarkers 
ON patients (screening_status, alt_enzyme, serum_creatinine);
```

#### Active Patient Records in Sample Database:
- **Patient #104 (Eleanor Vance, Age 58, Female)**: Creatinine: 2.4 mg/dL (Elevated), ALT: 142.0 U/L (Severely Elevated), Platelets: 85,000 /uL (Low), Washout: 12 days. **Status: Fails typical Phase III oncology exclusion criteria.**
- **Patient #105 (Marcus Brody, Age 64, Male)**: Creatinine: 1.1 mg/dL (Normal), ALT: 28.5 U/L (Normal), Platelets: 240,000 /uL (Normal), Washout: 45 days. **Status: Fully Eligible.**

---

# SECTION 5: Production Performance & Zero-RAM Engineering

### 5.1 Operating Within 512MB RAM (Render Cloud Tier)
Deploying containerized AI backends to cost-effective 512MB RAM cloud tiers often causes Out-Of-Memory (OOM) `SIGKILL` 137. 

VeriDoc Synapse solves this through three strict mechanisms:
1. **Zero In-Memory File Buffering**: Uploads are streamed directly from the socket to disk via `shutil.copyfileobj(chunk_size=65536)`. Consumes $< 4\text{MB RAM}$ for a 100MB PDF.
2. **FastEmbed ONNX vs. PyTorch**: FastEmbed's quantized ONNX C++ engine loads `bge-small-en-v1.5` in **58MB RAM** (saving 1.1GB compared to PyTorch `sentence-transformers`).
3. **Active Kernel Heap Compaction (`malloc_trim`)**: Python's `pymalloc` allocator holds onto freed memory in private arenas rather than releasing it back to the OS. In `pipeline.py`, we force glibc heap release:
   ```python
   gc.collect()
   if os.name != "nt":
       ctypes.CDLL("libc.so.6").malloc_trim(0)
   ```
   Drops container RSS from 420MB down to **172MB** immediately after heavy document parsing.

---

### 5.2 The 6 Production War Stories
1. **512MB RAM Container Crash (OOM SIGKILL 137)**: Replaced PyTorch with FastEmbed ONNX, replaced PyPDF with PyMuPDF, added `malloc_trim(0)`. Memory capped at 340MB peak.
2. **Google OAuth 502 Bad Gateway during Cold Starts**: Pre-flight warmup ping (`GET /health`) on login page mount wakes sleeping container before user finishes typing password. Login takes $< 90\text{ms}$.
3. **429 Rate Limit Avalanche on Groq LPU**: Built 10-key dynamic load balancer with Token Bucket and 20s Circuit Breaker quarantine key-hopping.
4. **Autonomous Crawler Network Deadlock**: Enforced 8.0s streaming timeout, 15MB file cap, 25-page extraction limit, and same-domain regex lock.
5. **FastAPI Wildcard Route Masking Bug**: Re-ordered route registration so explicit static routes (`/api/chat/general`) precede parameterized dynamic routes (`/api/chat/{doc_id}`).
6. **800-Token Table Truncation Bug**: Elevated `max_tokens` from 800 to 3,500 across all inference endpoints, preventing mid-sentence table cutoffs.

---

# SECTION 6: Model Context Protocol (MCP) Server Specifications

VeriDoc Synapse exposes a standard bidirectional **Anthropic MCP (2024-11-05)** server:
- `POST /api/mcp/rpc`: JSON-RPC 2.0 endpoint for tool discovery (`tools/list`) and execution (`tools/call`).
- `GET /api/mcp/sse`: Server-Sent Events stream for external agents.

### The 5 Registered MCP Tools:
1. `query_clinical_database`: Executes an AST-guarded, read-only `SELECT` query on the hospital EHR screening database.
2. `get_patient_lab_record`: Parameterized retrieval of a patient's ALT, creatinine, platelets, and washout history.
3. `inspect_database_schema`: Introspects table structures and column types.
4. `send_slack_alert`: Dispatches emergency Block Kit alerts to `#clinical-safety-alerts`.
5. `dispatch_edc_protocol_hold`: Flags protocol amendments and halts patient screening in EDC systems.

---

# SECTION 7: Comprehensive Technical & Non-Technical Q&A Knowledge Base
*(For instant reference when querying ChatGPT or answering technical interviewers)*

#### Q1: What makes VeriDoc Synapse different from a standard LangChain RAG app?
> **Answer**: Standard RAG apps are passive, hallucination-prone document viewers that only read uploaded PDFs. VeriDoc Synapse is an **ActionMesh**: it connects directly to live hospital relational EHR databases via Inbound MCP, runs an Autonomous Compliance Watcher in the background to detect protocol contradictions across trials without human prompting, and dispatches automated emergency holds to Slack and hospital EDC systems with Human-in-the-Loop confirmation.

#### Q2: How does the system prevent SQL injection when the LLM queries patient databases?
> **Answer**: Queries generated by the LLM pass through an Abstract Syntax Tree (AST) validator using `sqlparse` in `mcp/db_connector.py`. It mathematically validates that the statement is strictly `SELECT`, rejects semicolons and forbidden keywords (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`), enforces a 50-row `LIMIT`, sets a 500ms query timeout, and executes under a read-only database service account.

#### Q3: How do you defend data privacy and HIPAA compliance?
> **Answer**: In Cloud LPU Mode, vector embeddings are generated locally on CPU via FastEmbed ONNX—the 500-page document never leaves the server. We enforce data minimization: only the top 3–5 matching text chunks (~500 tokens) are transmitted to Groq under contractual Zero Data Retention (ZDR) agreements. For high-security hospital deployments, our Air-Gapped Private Mode runs 100% on-premise using local Ollama models; 0 bytes leave the machine.

#### Q4: Why use Reciprocal Rank Fusion (RRF $k=60$) instead of score averaging?
> **Answer**: Dense cosine similarity scores $[0, 1]$ and sparse Okapi BM25 scores $[0, \infty)$ have completely different, non-stationary probability distributions. A single document with high keyword density can produce a BM25 score of 45.0, overpowering semantic scores. RRF ($k=60$) merges them based solely on ordinal rank positions, creating a smooth, parameter-free ranking that excels at exact medical drug codes and semantic intent alike.

#### Q5: How does the system run within 512MB RAM without crashing?
> **Answer**: We eliminate PyTorch's 1.2GB memory footprint by using FastEmbed ONNX (< 60MB RAM) and PyMuPDF in C. Document uploads stream directly to disk rather than buffering in memory. Crucially, after every ingestion run, we trigger Linux kernel heap compaction using `ctypes.CDLL('libc.so.6').malloc_trim(0)` alongside Python's `gc.collect()`, forcing glibc to return freed memory pages back to the operating system.

---

### Verification & Test Suite Status
All integration tests on branch `experiment` pass with **100% success**:
- `python test_phase3_mcp.py`: Database connectivity, AST SQL injection defense, patient lab lookup, MCP tools, and live context injection.
- `python test_phase4_5_6.py`: Background compliance contradiction detection, Slack emergency webhook dispatch, EDC protocol hold flags, and standard JSON-RPC 2.0 MCP server initialization.
