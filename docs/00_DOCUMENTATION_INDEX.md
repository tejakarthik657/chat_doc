# Nexus VeriDocs: Technical Documentation Suite (Index)

Welcome to the definitive technical documentation library for **Nexus VeriDocs**. This library is bifurcated into 20 modular, domain-specific engineering specifications covering system design, database schemas, retrieval algorithms, inference resilience, ingestion pipelines, frontend architecture, production operations, and interview preparation.

---

## Documentation Categories & Directory Index

### 1. System Overview & Architecture
- **[`01_SYSTEM_OVERVIEW_AND_VISION.md`](./01_SYSTEM_OVERVIEW_AND_VISION.md)**: High-level architectural philosophy, toy RAG vs. enterprise RAG v2, core technical pillars, and system mind map.
- **[`02_SYSTEM_DESIGN_AND_TOPOGRAPHY.md`](./02_SYSTEM_DESIGN_AND_TOPOGRAPHY.md)**: End-to-end component architecture, request/response dataflow blueprints, and network ingress topology.
- **[`03_DIRECTORY_AND_FILE_WALKTHROUGH.md`](./03_DIRECTORY_AND_FILE_WALKTHROUGH.md)**: Exhaustive, file-by-file audit of every single backend (`rag-backend/`) and frontend (`veridoc-frontend/`) module.

### 2. Database & Storage Architecture
- **[`04_DATABASE_SCHEMAS_AND_DATA_DICTIONARY.md`](./04_DATABASE_SCHEMAS_AND_DATA_DICTIONARY.md)**: Exhaustive data dictionary covering all 11 MongoDB Atlas collections, field types, constraints, and indexes.
- **[`05_POLYGLOT_PERSISTENCE_AND_STORAGE_DECOUPLING.md`](./05_POLYGLOT_PERSISTENCE_AND_STORAGE_DECOUPLING.md)**: Polyglot persistence design: MongoDB Atlas, Qdrant Cloud, Cloudinary CDN binary streaming, and durable BM25 serialization.
- **[`06_VECTOR_STORE_AND_EMBEDDINGS_ARCHITECTURE.md`](./06_VECTOR_STORE_AND_EMBEDDINGS_ARCHITECTURE.md)**: Qdrant Cloud cluster setup, 384-dimensional vector schemas, HNSW indexing parameters, and FastEmbed/SentenceTransformers.

### 3. Ingestion, Crawling & Chunking
- **[`07_INGESTION_PIPELINE_AND_PARENT_CHILD_CHUNKING.md`](./07_INGESTION_PIPELINE_AND_PARENT_CHILD_CHUNKING.md)**: Dual-mode extraction (PyMuPDF + OCR), 300-token child vs. 1200-token parent chunking, and memory compression.
- **[`08_AUTONOMOUS_WEB_SPIDER_AND_CRAWLER.md`](./08_AUTONOMOUS_WEB_SPIDER_AND_CRAWLER.md)**: Domain-locked recursive web crawler, robots.txt parsing, URL canonicalization, and 8.0s fast PDF stream timeouts.

### 4. RAG Intelligence & Retrieval Algorithms
- **[`09_RAG_V2_HYBRID_RETRIEVAL_PIPELINE.md`](./09_RAG_V2_HYBRID_RETRIEVAL_PIPELINE.md)**: End-to-end retrieval flow: Intent routing, HyDE, parallel Dense/Sparse retrieval, and context assembly.
- **[`10_RECIPROCAL_RANK_FUSION_AND_BM25.md`](./10_RECIPROCAL_RANK_FUSION_AND_BM25.md)**: Mathematical derivation of Reciprocal Rank Fusion ($k=60$), Okapi BM25 implementation, and score normalization elimination.
- **[`11_CROSS_ENCODER_RERANKING_AND_CRAG.md`](./11_CROSS_ENCODER_RERANKING_AND_CRAG.md)**: Neural cross-encoder attention reranking (`ms-marco-MiniLM`), Corrective RAG (CRAG) chunk grader, and query rewriting loops.

### 5. Inference & Resilience Engineering
- **[`12_MULTI_KEY_GROQ_LPU_CLUSTER_RESILIENCE.md`](./12_MULTI_KEY_GROQ_LPU_CLUSTER_RESILIENCE.md)**: 10-key dynamic Groq pool, TokenBucket rate limiter, CircuitBreaker state automaton, and automated 20s cooldown key-hopping.
- **[`13_EXECUTIVE_PROMPT_ENGINEERING_AND_TOKEN_EXPANSION.md`](./13_EXECUTIVE_PROMPT_ENGINEERING_AND_TOKEN_EXPANSION.md)**: Executive AI persona, Markdown table generation, 3500-token budget (truncation elimination), and inline source citation format.
- **[`14_CLOUD_MULTI_PROVIDER_FAILOVER.md`](./14_CLOUD_MULTI_PROVIDER_FAILOVER.md)**: Emergency failover hierarchy: Groq Qwen 27B $\rightarrow$ GPT OSS 120B $\rightarrow$ GPT OSS 20B $\rightarrow$ Google Gemini 1.5 Flash $\rightarrow$ OpenRouter.

### 6. Security, Networking & API Layer
- **[`15_AUTHENTICATION_OAUTH_AND_SECURITY_GATEWAY.md`](./15_AUTHENTICATION_OAUTH_AND_SECURITY_GATEWAY.md)**: Bcrypt password hashing, stateless JWT issuance, Google OAuth 2.0 handshake, and cold-start health warming pings.
- **[`16_API_SPECIFICATION_AND_REST_ENDPOINTS.md`](./16_API_SPECIFICATION_AND_REST_ENDPOINTS.md)**: Comprehensive REST API contract detailing request/response schemas for auth, documents, projects, chat, and feature endpoints.

### 7. Frontend, UX & Interactive Features
- **[`17_FRONTEND_ARCHITECTURE_STREAMING_AND_UX.md`](./17_FRONTEND_ARCHITECTURE_STREAMING_AND_UX.md)**: Next.js 16 App Router topography, 3-word batch window streaming buffer (65% DOM render reduction), and custom recursive GFM Markdown parser.
- **[`18_INTERACTIVE_FEATURES_AND_CANVAS_WORKSPACE.md`](./18_INTERACTIVE_FEATURES_AND_CANVAS_WORKSPACE.md)**: Architecture of Canvas Workspace, Truth Lattice adversarial red team auditor, Socratic Viva modal, and Living Code Sandbox.

### 8. Operations, Performance & Leadership
- **[`19_PRODUCTION_PERFORMANCE_ZERO_RAM_AND_TROUBLESHOOTING.md`](./19_PRODUCTION_PERFORMANCE_ZERO_RAM_AND_TROUBLESHOOTING.md)**: Operating within Render's 512MB RAM tier, `ctypes malloc_trim(0)` heap compaction, and analysis of 6 real production war stories.
- **[`20_CTO_INTERVIEW_AND_SYSTEM_PITCH_PLAYBOOK.md`](./20_CTO_INTERVIEW_AND_SYSTEM_PITCH_PLAYBOOK.md)**: Founder/CTO technical pitch script, computer science cross-walk, and 10 senior architecture interview questions with verbatim technical answers.
