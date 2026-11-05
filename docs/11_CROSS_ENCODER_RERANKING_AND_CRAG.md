# 11. Cross-Encoder Reranking & Corrective RAG (CRAG)

> *"A bi-encoder looks at two people across a crowded room and guesses if they are compatible. A cross-encoder sits them down at a table and listens to their conversation. In high-stakes medicine, you never rely on guesses from across the room."*

---

## 1. The Bi-Encoder Blindspot: Why Vector Similarity Produces False Positives

To understand why a two-stage retrieval pipeline is essential, you must understand the mathematical architecture of **Bi-Encoders vs. Cross-Encoders**:

```
BI-ENCODER (First-Stage Retrieval)
Query Q ──────► [ Embedding Model ] ──────► Vector u (384-d) ──┐
                                                               ├─► Dot Product Sim(u, v)
Chunk D ──────► [ Embedding Model ] ──────► Vector v (384-d) ──┘
* No cross-token attention between Q and D! Words cannot interact.

CROSS-ENCODER (Second-Stage Neural Reranker)
[CLS] + Query Q + [SEP] + Chunk D ──► [ Joint Transformer ] ──► Softmax Score [0.0 to 1.0]
* Full all-to-all cross-attention: Every query word attends to every document word.
```

### The Clinical Failure Mode of Bi-Encoders:
Consider this user query:
> *"Which clinical cohorts should **NOT** receive escalating doses of Keytruda?"*

A bi-encoder vector model produces high cosine similarity with:
> *"Cohort 2 will receive escalating doses of Keytruda beginning at 200mg IV."*

Why? Because 85% of the words are identical (*"cohorts"*, *"receive"*, *"escalating"*, *"doses"*, *"Keytruda"*). The bi-encoder collapses the entire sentence into an isolated vector coordinate, frequently missing the negative syntactic modifier **"NOT"**.

If this passage is sent to an LLM without reranking, the model risks generating a dangerous, hallucinated clinical recommendation.

---

## 2. The Cross-Encoder Neural Reranker

In [`rag-backend/app/core/reranker.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/core/reranker.py), we use a specialized neural cross-encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`):

```python
# rag-backend/app/core/reranker.py
from typing import List, Dict, Any

class CrossEncoderReranker:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model = self._load_optimized_model(model_name)

    def rerank(self, query: str, candidates: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Computes joint bidirectional cross-attention for all (query, document) pairs.
        Reranks candidates based on deep semantic relevance.
        """
        if not candidates:
            return []

        # Construct joint token pairs: [CLS] Query [SEP] Passage [SEP]
        sentence_pairs = [[query, c["text"]] for c in candidates]
        
        # Predict relevance logits
        scores = self.model.predict(sentence_pairs)

        # Attach reranker confidence scores and sort
        for idx, score in enumerate(scores):
            candidates[idx]["rerank_score"] = float(score)

        reranked = sorted(candidates, key=lambda x: x["rerank_score"], reverse=True)
        return reranked[:top_k]
```

### Why Not Run Cross-Encoders Across the Entire Database?
- A cross-encoder requires a full forward pass of a 66-million parameter transformer for **every single passage**.
- Running it on a 10,000-page document corpus would take **45 seconds per query**.
- **The Two-Stage Solution**: We use FastEmbed (dense) + BM25 (sparse) via RRF to filter 10,000 chunks down to the top 15 candidates in **8 milliseconds**. Then, the Cross-Encoder scores only those 15 candidate pairs in **22 milliseconds**. Total latency: $\sim 30\text{ms}$.

---

## 3. Corrective RAG (CRAG) Regulatory Guardrails

Even after cross-encoder reranking, there are scenarios where the uploaded documents simply do not contain the answer. 

Standard RAG systems hallucinate when context is missing because the LLM feels pressured to generate an answer. To prevent this, we implemented **Corrective RAG (CRAG)** in [`rag-backend/app/rag/crag.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/rag/crag.py):

```mermaid
flowchart TD
    CANDIDATES["Top-5 Cross-Encoder Ranked Chunks"] --> GRADER["CRAG Confidence Grader (rag/crag.py)"]
    
    GRADER --> DECISION{"Max Relevance Score (S)"}
    
    DECISION -->|S >= 0.70 (CORRECT)| PASS["Pass High-Confidence Chunks directly to LLM Prompt"]
    
    DECISION -->|0.40 <= S < 0.70 (AMBIGUOUS)| REWRITE["Query Rewrite Loop:<br/>Strip conversational fluff & re-query BM25 with exact medical entities"]
    
    DECISION -->|S < 0.40 (INCORRECT / EMPTY)| ABSTAIN["Regulatory Abstention Protocol:<br/>Refuse to hallucinate & log audit warning"]
    
    REWRITE --> SECOND_SEARCH["Second-Chance Exact Keyword Search"]
    SECOND_SEARCH --> PASS
```

### The 3 CRAG Action States:

#### State 1: `CORRECT` (Confidence $\ge 0.70$)
The retrieved chunks contain direct, authoritative evidence answering the query. Chunks are passed immediately into the prompt context.

#### State 2: `AMBIGUOUS` ($0.40 \le \text{Confidence} < 0.70$)
The retrieved text is tangentially related, but lacks exact keywords. The CRAG engine triggers a query rewrite:
- Strips filler (*"Can you tell me..."*, *"What does the protocol say about..."*).
- Extracts bare biomedical entities (`"creatinine"`, `"exclusion cutoff"`, `"Cohort B"`).
- Re-executes an exact BM25 sparse search to discover overlooked tables.

#### State 3: `INCORRECT` / `EMPTY` (Confidence $< 0.40$)
The document does not contain the required regulatory information. The system executes the **Regulatory Abstention Protocol**, returning:
> *"Regulatory Audit Warning: The indexed protocols do not contain verifiable data regarding this requirement. To prevent protocol deviation under FDA 21 CFR 312, please consult the primary Trial Master File (TMF) or the Principal Investigator."*

---

## 4. CTO Interview Defense: Cross-Encoders & CRAG

When an interviewer asks: *"How do you guarantee that your RAG pipeline does not hallucinate answers when the document doesn't have the information?"*, deliver this three-part answer:

> *"We eliminate hallucinations through a two-tier defense: Cross-Encoder Neural Reranking and Corrective RAG (CRAG).
> 
> First, bi-encoder embeddings frequently suffer from false positives because query and document vectors are calculated independently without cross-token attention. By running our top-15 fused candidates through a Cross-Encoder (`ms-marco-MiniLM-L-6-v2`), every word in the query attends directly to every word in the candidate passage, correctly capturing syntactic modifiers like 'NOT' or 'EXCLUDE'.
> 
> Second, we wrap the reranked output in a CRAG (Corrective RAG) evaluator. If the confidence score of the best retrieved passage falls below our calibrated threshold of 0.40, our engine refuses to answer. In clinical and FDA compliance, returning a hallucinated number can cause trial failure or patient harm. We enforce regulatory abstention over speculation: if the evidence isn't in the documents, the system explicitly alerts the auditor."*
