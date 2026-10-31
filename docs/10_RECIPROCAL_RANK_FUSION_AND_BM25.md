# 10. Reciprocal Rank Fusion & BM25

## 1. Why Linear Weighted Sums Fail in Hybrid Search
Linear score combinations ($\alpha \cdot S_{\text{dense}} + (1-\alpha) \cdot S_{\text{bm25}}$) encounter cross-distribution calibration failures:
- **Cosine Similarity**: Bounded $[-1.0, 1.0]$.
- **BM25 Scores**: Unbounded $[0, \infty)$, fluctuating with term frequency, document length, and corpus size.
- Min-Max scaling is sensitive to outliers and query variance.

---

## 2. Reciprocal Rank Fusion (RRF) Mathematical Formula

$$\text{RRF\_Score}(d \in D) = \sum_{m \in M} \frac{1}{k + r_m(d)}$$

Where:
- $M = \{\text{Qdrant Dense Vector Search}, \text{Okapi BM25 Keyword Search}\}$.
- $r_m(d)$ is the 1-based rank position of chunk $d$ in retrieval system $m$.
- $k = 60$ is the smoothing constant that balances top-ranked hits and suppresses noise from lower-ranked matches.

---

## 3. Implementation Code (`core/fusion.py`)

```python
def reciprocal_rank_fusion(
    faiss_results: list[tuple[int, float]],
    bm25_results: list[tuple[int, float]],
    top_k: int = 25,
    k: int = 60
) -> list[tuple[int, float]]:
    scores: dict[int, float] = {}

    for rank, (doc_id, _) in enumerate(faiss_results, start=1):
        scores[doc_id] = scores.get(doc_id, 0.0) + (1.0 / (k + rank))

    for rank, (doc_id, _) in enumerate(bm25_results, start=1):
        scores[doc_id] = scores.get(doc_id, 0.0) + (1.0 / (k + rank))

    return sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
```
