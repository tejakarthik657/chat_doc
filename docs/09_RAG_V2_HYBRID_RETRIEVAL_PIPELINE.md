# 09. RAG v2 Hybrid Retrieval Pipeline

## 1. Multi-Stage Retrieval Sequence

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Router as rag/router.py
    participant HyDE as rag/hyde.py
    participant Qdrant as db/qdrant.py
    participant BM25 as core/bm25.py
    participant RRF as core/fusion.py
    participant Rerank as core/reranker.py
    participant CRAG as rag/crag.py
    participant Groq as core/llm_groq.py

    User->>Router: Query String
    Router->>Router: Extract metadata filters (department, doc_type)
    opt Abstract / Vague Query
        Router->>HyDE: Generate Hypothetical Document
        HyDE-->>Router: Fictional context passage
    end
    par Parallel Retrieval
        Router->>Qdrant: Dense Vector Search (Top 30)
        Router->>BM25: Sparse Keyword Search (Top 30)
    end
    Qdrant-->>RRF: Dense Ranking List
    BM25-->>RRF: Sparse Ranking List
    RRF->>RRF: Compute RRF Scores: Sum( 1 / (60 + rank) )
    RRF-->>Rerank: Top 25 Fused Candidates
    Rerank->>Rerank: Cross-Encoder ms-marco-MiniLM Attention
    Rerank-->>CRAG: Precision Ranked Top 5 Chunks
    CRAG->>CRAG: Grade Chunk Relevance (High / Medium / Low)
    alt Zero Relevant Chunks
        CRAG->>Router: Query Rewrite & Single Re-Retrieval
    else Valid Relevance Verified
        CRAG->>Groq: Generate Grounded Answer (max_tokens=3500)
        Groq-->>User: Markdown Response with Inline Citations
    end
```

---

## 2. Component Directory Reference

- **Query Routing (`rag/router.py`)**: Classifies user query into departments (`cse`, `ece`, `eee`) and categories (`faculty`, `placement`, `syllabus`).
- **HyDE Engine (`rag/hyde.py`)**: For abstract questions (e.g., *"What is this document about?"*), generates a hypothetical paragraph to ground vector search in target terminology.
- **Context String Assembly (`rag/engine.py`)**: Deduplicates chunks by `parent_id` and checks total tokens against the prompt budget.
