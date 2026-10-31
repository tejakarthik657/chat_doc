# 06. Vector Store & Embeddings Architecture

## 1. Vector Space & Dimension Specifications

```
Model: sentence-transformers/all-MiniLM-L6-v2 (or FastEmbed BAAI/bge-small-en-v1.5)
Vector Dimension: 384 dimensions
Distance Metric: Cosine Similarity
Vector Space: [-1.0, 1.0] Normalized
Qdrant HNSW Settings: m=16, ef_construct=100
```

---

## 2. Qdrant Cloud Cluster Configuration (`db/qdrant.py`)

Vectors are isolated in **Qdrant Cloud**, ensuring zero local vector storage on the API host:
- **Collection Naming**: Partitioned per project: `project_{project_id}`.
- **Payload Schema & Pre-Filtering**:
  ```json
  {
    "chunk_id": "doc_6722_c4",
    "embedding_id": 4,
    "doc_id": "6ae305868d044a0b1ca8f528",
    "source_name": "KITSW Alumni Network",
    "url": "https://kitsw.ac.in/funds",
    "page": 1,
    "department": "cse",
    "document_type": "faculty"
  }
  ```

---

## 3. FastEmbed vs. SentenceTransformers Dual-Engine (`core/embeddings.py`)

- **Cloud Mode (`FastEmbed`)**: Runs ONNX-runtime quantizations (`bge-small-en-v1.5`). Bypasses heavy PyTorch runtime, consuming $< 60\text{ MB}$ RAM on Render containers.
- **Local Mode (`SentenceTransformers`)**: Full PyTorch transformer models for local development and fine-tuning.
