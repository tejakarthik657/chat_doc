# 20. CTO Interview & System Pitch Playbook

## 1. 60-Second Executive Pitch Script

> *"Nexus VeriDocs is an enterprise-scale document intelligence platform built around a self-healing, multi-store RAG architecture. Instead of relying on a single vector database and an unmanaged LLM endpoint, we engineered a polyglot persistence system with a hybrid retrieval pipeline. We combine dense semantic vectors in Qdrant with durable Okapi BM25 indices in MongoDB using Reciprocal Rank Fusion ($k=60$) and Cross-Encoder reranking.*
> 
> *To eliminate inference latency and rate limits in production, we built a 10-key dynamic Groq LPU cluster managed by individual token buckets and circuit breakers. If a key hits a 429 limit, the pool rotates immediately to the next healthy key with zero user downtime, falling back to Google Gemini 1.5 Flash via REST if necessary.*
> 
> *By decoupling binary storage to Cloudinary and tuning heap memory with `malloc_trim`, our backend operates comfortably within strict 512MB RAM container constraints without out-of-memory crashes. The frontend is built on Next.js 16 with paced streaming and custom Markdown table rendering, delivering structured, executive-grade answers backed by exact source citations."*

---

## 2. Senior Leadership & CTO Interview Questions & Answers

### Q1: "Why did you choose Reciprocal Rank Fusion (RRF) instead of a simple weighted average of vector similarity and BM25 scores?"
> **Verbatim Answer**:
> *"Cosine similarity produces normalized scores between -1 and 1, whereas BM25 scores are unbounded term frequencies that vary with document length and corpus size. Normalizing BM25 using Min-Max scaling is brittle because it is sensitive to outliers and query variance. RRF sidesteps score calibration entirely by operating strictly on ordinal rank positions ($\frac{1}{60 + r}$). It consistently outperforms linear weighted combinations across heterogeneous retrieval systems without requiring hyperparameter tuning on every new document corpus."*

### Q2: "How does your system enforce source grounding and eliminate hallucinations in mission-critical institutional documents?"
> **Verbatim Answer**:
> *"We enforce grounding at three distinct layers: First, at the retrieval layer, we use Cross-Encoder reranking and Corrective RAG (CRAG) to filter out low-confidence chunks before the LLM sees them. Second, at the prompt layer, the Executive System Prompt explicitly forbids extrapolation, mandates inline citations in the format `[Source: filename, Page X]`, and instructs the model to state what is present rather than guessing. Third, at the evaluation layer, our `verify_answer_support` engine parses the generated answer against the input context chunks, assigning a confidence score and flagging unverified claims."*

### Q3: "How does your backend survive running sentence-transformers and heavy RAG workloads on a 512MB RAM cloud container?"
> **Verbatim Answer**:
> *"We enforce zero-RAM architecture principles: First, we do not store raw PDF binaries or FAISS indices in Python heap memory; binaries are decoupled to Cloudinary and vectors are offloaded to Qdrant Cloud. Second, when local embeddings or BM25 indices are processed, we process them in strict micro-batches. Third, we explicitly call `ctypes.CDLL('libc.so.6').malloc_trim(0)` alongside Python's garbage collector (`gc.collect()`). This releases freed memory back to the Linux OS immediately, preventing the memory fragmentation that causes container SIGKILLs."*

### Q4: "How does your multi-key Groq pool achieve high availability without leaking API secrets?"
> **Verbatim Answer**:
> *"The backend reads comma-separated keys from the environment into a protected `KeyWorker` pool. Each worker wraps an independent `Groq` client instance paired with a `TokenBucket` rate limiter and a `CircuitBreaker`. Incoming requests are routed round-robin. If any key receives an HTTP 429, that specific worker enters a 20-second cooldown while the pool seamlessly routes the request to the next available worker in the same turn. If the entire Groq cluster is down, the pool trips its circuit and immediately delegates to Google Gemini 1.5 Flash via REST."*

### Q5: "How would you scale this architecture from 10,000 to 1,000,000 daily active users?"
> **Verbatim Answer**:
> *"Scaling to 1M DAU requires three architectural steps: First, decouple the web crawler and document ingestion from the web server into an asynchronous worker queue (Celery or ARQ backed by Redis). Second, replace local disk caches with a distributed Redis cluster for BM25 serialization and living memory caches. Third, transition Qdrant from single-node cloud instances to a distributed cluster with HNSW index sharding and read replicas, placing an Envoy or Cloudflare edge cache in front of static document responses."*
