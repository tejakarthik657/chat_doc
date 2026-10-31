# 11. Cross-Encoder Reranking & CRAG

## 1. Bi-Encoder vs. Cross-Encoder Comparison

```mermaid
graph TD
    subgraph BI_ENCODER["Bi-Encoder (Fast Retrieval Stage)"]
        Q1["Query"] --> E1["Embedding Model"] --> V1["Vector Q"]
        D1["Chunk"] --> E2["Embedding Model"] --> V2["Vector D"]
        V1 & V2 --> COSINE["Cosine Similarity: sim(Q, D)"]
    end

    subgraph CROSS_ENCODER["Cross-Encoder (Precision Reranker Stage)"]
        Q2["Query"] & D2["Chunk"] --> CONCAT["Concatenate [CLS] Q [SEP] D"]
        CONCAT --> ATTENTION["Full Self-Attention Layers"]
        ATTENTION --> LOGIT["Relevance Score: Attention(Q, D)"]
    end
```

---

## 2. Corrective RAG (CRAG) Workflow (`rag/crag.py`)

1. **Relevance Grading**: Evaluates the top reranked chunks using an LLM or small classifier (`High`, `Medium`, `Low`).
2. **Confidence Thresholding**:
   - If $\ge 1$ chunk has `High` or `Medium` relevance $\rightarrow$ proceeds directly to LLM prompt assembly.
   - If **all** chunks are `Low` relevance $\rightarrow$ triggers query rewrite loop.
3. **Query Rewriting Loop**: Strips extraneous filler words and queries Qdrant with an expanded query variation.
4. **Abstention**: If re-retrieval also yields zero relevant chunks, the engine returns a grounded abstention message rather than hallucinating an answer.
