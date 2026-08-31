# Implementation Plan - Enhanced RAG & Crawler Pipeline

This implementation plan addresses critical issues in the current RAG (Retrieval-Augmented Generation) system, specifically regarding web scraping/crawling quality, slow indexing times, and failures to answer user questions when information is present.

---

## 1. Project Analysis (Current Flow & Technologies)

Our system is structured as a dual-component platform:
1. **Frontend (`veridoc-frontend`)**: A React/Next.js UI.
2. **Backend (`rag-backend`)**: A FastAPI application.

### Backend Tech Stack
* **Web Scraping & Crawling**: `BeautifulSoup4`, `trafilatura` (HTML text parsing), `playwright` (dynamic JS crawling), and `httpx` (HTTP clients).
* **Document Extraction**: `PyMuPDF` (`fitz`) for fast text/table parsing, `pytesseract` for OCR fallback, and `docling` for layout-aware structure and table parsing.
* **Vector Store & Retrieval**: `Qdrant` (dense vector search) and `FAISS` (local CPU dense search), coupled with `sentence-transformers` (`all-MiniLM-L6-v2`) for embeddings, and `rank-bm25` (sparse keyword search) for hybrid retrieval.
* **Reranking**: `BAAI/bge-reranker-base` via Cross-Encoders.
* **Core Databases**: `MongoDB` (metadata, crawled text content, chat history, BM25 indices).
* **LLM Engine**: `Groq API` (`llama-3.3-70b-versatile` / `llama-3.1-8b-instant`) with local `TinyLlama` CPU fallback.

---

## 2. Identified Issues & Solutions

### A. Web Crawling & Content Extraction
* **The Problem**: 
  1. The crawler relies heavily on `trafilatura`, which frequently discards main body text (like faculty tables or syllabus regulations) on university/MedTech web layouts because it mistakes structured lists for header/boilerplate links.
  2. Dynamic SPA (Single Page Application) sites are crawled via `httpx` fast-path, which only fetches empty `<div id="root"></div>` shells.
  3. Playwright is configured but does not fall back correctly, or times out.
* **Proposed Solution**:
  * **Improved Extraction Heuristics**: If `trafilatura` extracts less than 200 characters, fall back aggressively to `BeautifulSoup` parsing with improved cleaning filters (preserving `<table>`, `<ul>`, and grid structures).
  * **Configurable Dynamic Crawling**: Expose a clear selector in the frontend/backend to enforce Playwright-based rendering on SPA websites, and ensure Playwright runs headlessly with automated waits for target selectors.
  * **PDF Link Extraction**: Improve link extraction from PDFs using PyMuPDF to follow documents hosted on the site automatically.

### B. Long Indexing Latency
* **The Problem**: 
  1. `Docling`'s `DocumentConverter()` is instantiated inside the extraction loop. Initializing PyTorch weights and layout models on CPU takes **5–15 seconds per PDF**, leaking memory and CPU cycles.
  2. Anthropic's **Contextual Retrieval** runs LLM prefix generation for *every single chunk* (20-chunk batches). With 100 chunks, this calls Groq 20+ times, hitting the free tier's **30 RPM rate limits**.
  3. Upon hitting a Groq 429 error, it falls back to the **local TinyLlama model on CPU** sequentially, which takes **15-30 seconds per chunk**, freezing the backend for 15+ minutes.
* **Proposed Solution**:
  * **Docling Lazy Singleton**: Cache the `DocumentConverter` instance at the module level so it loads only once at startup.
  * **Fast-Path PyMuPDF First**: Use PyMuPDF (`fitz`) first. If it yields high-quality text and tables, bypass `Docling` entirely. Only use `Docling` if PyMuPDF extracts no text (scanned page) or if the user requests "High-Precision Layout Parsing" in the UI.
  * **Optimized Contextual Retrieval**: 
    * If Groq returns a rate limit (429) or fails, **bypass local TinyLlama CPU generation** entirely—simply proceed with a fast rule-based layout context (e.g., `"[Source: {filename} | Page {page}]"`) or cache the context generation.
    * Optionally, transition from *per-chunk* contextual prompts to *per-page* or *document-level* summaries to reduce API requests by 95%.

### C. System Fails to Answer (Rigid Retrieval & Grader)
* **The Problem**:
  1. **Strict Query Routing & Metadata Filters**: The Query Router (`router.py`) classifies a query (e.g., "Who is Dr. Smith?") and sets a hard filter (`document_type = "faculty"`). During ingestion, however, the target document might have been classified as `"general"`. Qdrant filters out the true answer. Because *other* unrelated faculty chunks match the filter, the relaxed retry is never triggered.
  2. **Hyper-Strict CRAG Grading**: In `engine.py`, if **all** retrieved chunks are graded as `"medium"` relevance by the grader LLM, the pipeline assumes zero relevance, triggers a query rewrite, and ultimately returns "I couldn't find this information..."—even if those `"medium"` chunks contain the exact answer!
  3. **High Similarity Thresholds**: A hard FAISS/Qdrant cosine threshold of `0.25` or `0.35` filters out slightly paraphrased text.
* **Proposed Solution**:
  * **Soft Metadata Filtering (Relevance Boosting)**: Instead of hard `must` filters in Qdrant, pass the metadata as a `should` clause to boost matched documents, or use metadata filters *only* when explicitly requested by the user.
  * **Relaxed CRAG Threshold**: Allow generation if there is at least one `"medium"` or `"high"` chunk. Only rewrite/abstain if **all** chunks are graded `"low"`.
  * **Hierarchical Document Summaries**: Upon indexing, generate a global document summary using Groq. Store this summary in MongoDB and inject it as top-level guidance in the RAG prompt so the model always understands the "big picture" of the document.

---

## 3. Proposed Changes

Below is a file-by-file summary of proposed modifications.

```
chat_base/
├── rag-backend/
│   ├── app/
│   │   ├── ingestion/
│   │   │   ├── pipeline.py       # [MODIFY] Change extraction order, make Docling a singleton, optimize fallback
│   │   │   └── crawler.py        # [MODIFY] Enhance BeautifulSoup fallbacks, ensure dynamic crawls wait for content
│   │   ├── core/
│   │   │   └── config.py         # [MODIFY] Add settings for vision fallback, docling mode, and soft filtering
│   │   └── rag/
│   │       ├── engine.py         # [MODIFY] Relax CRAG grading, change metadata filter to soft-matching, inject doc summary
│   │       ├── router.py         # [MODIFY] Tune query classifications to be less aggressive
│   │       └── crag.py           # [MODIFY] Adjust grading thresholds and parse failures
```

### Component Details

#### [MODIFY] [pipeline.py](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/ingestion/pipeline.py)
* Wrap `DocumentConverter` in a lazy-loaded singleton `get_docling_converter()`.
* Swap ingestion order: Extract text with PyMuPDF first. If characters per page > 100, use PyMuPDF. Only use Docling if requested or if text density is extremely low.
* Add Vision OCR fallback using Groq's `llama-3.2-11b-vision-preview` if local Tesseract is not installed and page contains images/scanned text.
* In `process_project_crawled_data`, generate a global project/document summary at the end of extraction and save it to the database.

#### [MODIFY] [crawler.py](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/ingestion/crawler.py)
* Refactor text extraction fallback: if `trafilatura` fails or returns minimal layout, run an enhanced BeautifulSoup scraper that preserves tables and semantic headers.
* Increase Playwright timeouts and add explicit waits for common SPA mounting elements.

#### [MODIFY] [engine.py](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/rag/engine.py)
* Replace hard Qdrant metadata filters with soft filters (`should` matching) or relax them if search fails to yield high-relevance chunks.
* Modify CRAG block to proceed with generation if chunks have `"medium"` relevance.
* Retrieve the global document summary from MongoDB and prepend it to the LLM system prompt as context.

#### [MODIFY] [crag.py](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/rag/crag.py)
* Update grading prompt and mapping rules to prevent false negatives.
* Allow `"medium"` as a passing grade for RAG execution.

---

## 4. Verification Plan

### Automated Tests
* Run existing test suites:
  ```powershell
  cd rag-backend
  pytest tests/ -v
  ```
* Add unit tests in `tests/test_backend.py` to cover:
  * Docling lazy instantiation.
  * CRAG threshold relaxation.
  * Query router relaxed filtering.

### Manual Verification
1. **Scraping / Crawling Validation**: Crawl a test university page (e.g. syllabus/faculty portal) with JS rendering. Verify in MongoDB `crawled_pages` that tables and body content are cleanly extracted.
2. **Speed Benchmark**: Time the indexing of a 10-page PDF containing text and tables. The expected speedup should be > 5x (reducing time from minutes to under 15 seconds).
3. **Answering Accuracy**: Query a specific name or placement statistic. Confirm the engine returns a precise response instead of the "I couldn't find this information" fallback.
