# VeriDoc ActionMesh: Autonomous Clinical & Regulatory Intelligence Platform
## Master Strategy & Phase-by-Phase Implementation Plan

> **Git Branch**: `experiment`  
> **Status**: In Active Staged Development  
> **Primary Motto**: *"Autonomous Clinical & Regulatory Intelligence: Zero-Hallucination Protocol Auditing, Live Database Verification, and Automated Compliance."*

---

## 1. The Core Architectural Defense: Data Privacy & The Groq Cloud Reality

### The Fundamental Question
> *"If we use Groq API, documents leave our servers anyway. How does VeriDoc protect data privacy better than ChatGPT or Claude?"*

### The 3 Architectural Differentiators

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DATA PRIVACY MATRIX                                │
├──────────────────────────┬────────────────────────────┬─────────────────────┤
│ Feature                  │ Consumer ChatGPT / Claude  │ VeriDoc ActionMesh  │
├──────────────────────────┼────────────────────────────┼─────────────────────┤
│ Document Ingestion & OCR │ Cloud-processed on OpenAI  │ 100% In-VPC / Local │
│ Vector Embeddings        │ Stored on OpenAI servers   │ Local ONNX & Qdrant │
│ Training on Data         │ YES by default (Free/Plus) │ NO (ZDR Enforced)   │
│ Data Minimization        │ Full Document in Context   │ Top-5 Chunks ONLY   │
│ Air-Gapped / Offline     │ IMPOSSIBLE (Cloud only)    │ BUILT-IN (Ollama)   │
└──────────────────────────┴────────────────────────────┴─────────────────────┘
```

1. **Local-First Ingestion & Vector Storage**:
   - In consumer LLMs, the entire 500-page PDF is uploaded to third-party cloud servers where parsing, OCR, and vectorization take place.
   - In VeriDoc, PDF extraction (PyMuPDF), table reconstruction, OCR, semantic chunking, and ONNX vector embedding (`BAAI/bge-small-en-v1.5`) execute **100% locally on CPU/container**. The raw file and dense vectors never leave the customer's database.
2. **Data Minimization (Only 5 Chunks Transmitted)**:
   - When calling Groq LPU, VeriDoc **never transmits the document**. It only passes the top 3–5 matching text chunks ($\sim 500$ tokens total) needed to answer the query.
   - Groq API agreements enforce **Zero Data Retention (ZDR)** — prompts and completions are never logged or used to train foundation models.
3. **The True Air-Gapped Mode (100% Offline / HIPAA)**:
   - For hospitals or high-security clients whose data cannot cross the internet under any circumstances, VeriDoc features an offline fallback ladder ([app/core/llm_local.py](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/core/llm_local.py)) using **Local Ollama (`llama3.1:8b` / `qwen2.5-coder:3b`)** or CPU GGUF models. Zero network packets leave the server.

---

## 2. Competitive Landscape: Why This Has 10,000% Market Value

| Competitor / Platform | Current Valuation | What They Do | Where They Fail / VeriDoc's Moat |
| :--- | :--- | :--- | :--- |
| **Veeva Systems (Vault eTMF)** | **$32 Billion** | Cloud document archive for pharma and clinical trials. | **Legacy tech (2011)**: Static folder tree. No semantic search, no automated contradiction detection, and no live database querying. Staff read PDFs manually. |
| **Glean** | **$5.4 Billion** | Enterprise search across Slack, Google Drive, Jira. | **Generic knowledge workers**: Lacks medical table reconstruction, regulatory citation linkage, clinical inclusion/exclusion criteria verification, and EHR/FHIR connectors. |
| **Harvey AI** | **$1.5 Billion** | AI for contract analysis and law firms. | **Legal only**: Proved that citation-grounded, high-stakes document RAG creates massive enterprise value, but does not serve clinical or MedTech compliance. |
| **MasterControl / TrackWise** | **Multi-Billion** | Quality Management Systems (QMS) for FDA 510(k). | **Pure ticketing workflows**: Workflow routing and e-signatures only. Cannot read engineering specs and compare them against FDA filings to catch contradictions automatically. |

### The Market Gap
There is no modern platform that bridges **unstructured regulatory/clinical documents (Protocols, SOPs, 510(k) filings)** with **live operational databases (Postgres, EHR, Jira)** to autonomously audit contradictions and protocol violations.

---

## 3. Phased Implementation Roadmap

### Phase 1: Brand & Motto Transformation (Frontend)
- Update [hero.tsx](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/veridoc-frontend/src/components/landing/hero.tsx), [how-it-works.tsx](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/veridoc-frontend/src/components/landing/how-it-works.tsx), and navigation to reflect the new **Autonomous Clinical & Regulatory Intelligence Platform** motto.
- Add an interactive badge in the UI: **"Hybrid RAG + MCP ActionMesh: Air-Gapped Local or Zero-Retention LPU"**.

### Phase 2: Dual-Inference Privacy Mode Selector (Backend + Frontend)
- Expose an explicit inference toggle in `/dashboard/settings`:
  - **Ultra-Fast LPU Mode**: Groq LPU (Llama 3.1 8B, 800 tokens/sec, Zero Data Retention).
  - **Air-Gapped Private Mode**: 100% Local Ollama / CPU GGUF (0 bytes outbound transit).
- Display the privacy badge and execution telemetry directly in the Evidence Panel.

### Phase 3: Inbound MCP Connector Engine (Live Database Cross-Referencing)
- Build `rag-backend/app/mcp/` subsystem:
  - Database connector (PostgreSQL / SQLite / MySQL) via standard MCP protocol.
  - Parameterized read-only queries with SQL-injection protection.
- Update [agent_workflow.py](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/rag/agent_workflow.py) with joint reasoning:
  - Extract criteria from indexed document chunks.
  - Query live database records.
  - Produce a unified, citation-backed audit report.

### Phase 4: Autonomous Event-Driven Ingestion Watcher (Auto-Contradiction Auditing)
- Hook into [pipeline.py](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/ingestion/pipeline.py) indexing completion:
  - When a new document version is uploaded, automatically trigger [ContradictionsAgent](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/rag/agent_workflow.py#L89-L124).
  - Compare new chunks against historical versions in the project.
  - Flag discrepancies (e.g. dosage changes, temperature tolerances) without requiring user prompts.

### Phase 5: Outbound MCP Action & Interactive Chat Cards
- Implement Outbound **Slack / Webhook Dispatcher**.
- When the agent detects a contradiction or the user requests an alert:
  - Chat renders an interactive **Confirmation Card** (`[Confirm & Send to Slack] [Cancel]`).
  - Dispatches structured payload with source citation page numbers.

### Phase 6: VeriDoc as an MCP Server (Dual-Sided Protocol)
- Implement `/api/mcp/sse` endpoint:
  - Expose `veridoc_search_evidence` and `veridoc_audit_contradictions` as standard MCP tools.
  - Allows Claude Desktop, Cursor, or external custom agents to query VeriDoc's hybrid RAG directly.
