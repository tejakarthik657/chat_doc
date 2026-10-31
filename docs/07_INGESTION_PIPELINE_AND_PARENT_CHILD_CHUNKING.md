# 07. Ingestion Pipeline & Parent-Child Chunking

## 1. Parent-Child Chunking Architecture

```mermaid
graph TD
    DOC["Input Document (PDF / HTML)"] --> SPLIT["Hierarchical Splitter"]
    SPLIT --> P1["Parent Block 1 (1200 tokens)"]
    SPLIT --> P2["Parent Block 2 (1200 tokens)"]

    P1 --> C1_1["Child Chunk 1 (300 tokens)"]
    P1 --> C1_2["Child Chunk 2 (300 tokens)"]
    P1 --> C1_3["Child Chunk 3 (300 tokens)"]

    C1_1 -->|Dense Vector Index| QDRANT[("Qdrant Cloud")]
    C1_1 -->|Sparse Inverted Matrix| BM25[("Okapi BM25 Index")]

    subgraph RETRIEVAL["Retrieval Resolution"]
        QUERY["Query Hits Child C1_1"] --> RESOLVE["Lookup parent_id: P1"]
        RESOLVE --> PROMPT["Inject Complete 1200-Token Parent Context into LLM Prompt"]
    end
```

---

## 2. Ingestion Technical Pipeline (`ingestion/pipeline.py`)

1. **Extraction**:
   - Digital Native: PyMuPDF (`fitz`) handles digital PDFs at $> 100\text{ pages/sec}$.
   - Scanned PDF Fallback: If extracted characters per page $< 50$, invokes Cloud Vision / OCR.Space.
2. **Text Sanitization & Normalization (`ingestion/sanitizer.py`)**:
   - Removes repeated headers/footers, form-feed characters, and hyphenated word breaks.
3. **Hierarchical Child Generation**:
   - Rolling token windows: $300\text{ tokens}$ with $50\text{ token}$ overlap.
4. **Parent Block Compression**:
   - Compresses $1200\text{ token}$ parent contexts using `zlib` to reduce MongoDB payload sizes.
