# 08. Autonomous Web Spider & Crawler

## 1. Web Crawler Architecture Flowchart

```mermaid
flowchart TD
    START([User Seeds Domain URL & Limit]) --> INIT[Create Project & CrawlJob in MongoDB]
    INIT --> ROBOTS[Fetch & Parse robots.txt]
    ROBOTS --> QUEUE_SEED[Queue Normalized Seed URL]
    
    QUEUE_SEED --> CHECK_EMPTY{Queue Empty OR Limit Reached?}
    CHECK_EMPTY -->|Yes| FINISH[Update Status: 'indexing' -> 'active']
    CHECK_EMPTY -->|No| POP[Pop Next URL]
    
    POP --> DOMAIN_LOCK{Matches Same-Domain Regex?}
    DOMAIN_LOCK -->|No| DISCARD[Discard External URL] --> CHECK_EMPTY
    DOMAIN_LOCK -->|Yes| FETCH[Async HTTPX GET: Timeout 8.0s]
    
    FETCH --> CONTENT_TYPE{Content-Type Header?}
    CONTENT_TYPE -->|text/html| PARSE_DOM[BeautifulSoup HTML Parsing]
    PARSE_DOM --> CANON[Canonicalize Links & Push to Queue]
    PARSE_DOM --> SAVE_PAGE[Insert to crawled_pages_col]
    SAVE_PAGE --> CHECK_EMPTY
    
    CONTENT_TYPE -->|application/pdf| STREAM_PDF[Stream Download: Max 15MB]
    STREAM_PDF --> EXTRACT_PDF[PyMuPDF Extract: Cap 25 Pages]
    EXTRACT_PDF --> INGEST_CHUNK[Generate Chunks, Embed & Store]
    INGEST_CHUNK --> CLEAN_RAM[ctypes malloc_trim + gc.collect]
    CLEAN_RAM --> CHECK_EMPTY
```

---

## 2. Crawler Technical Specifications (`ingestion/crawler.py`)

- **Same-Domain Constraint**: Strict regex lock (`^https?:\/\/(www\.)?targetdomain\.com`) ensures the crawler never traverses outbound links.
- **URL Canonicalization Engine**:
  - Strips URL fragments (`#section`), trailing slashes, and tracking query parameters (`?utm_source=...`).
  - Converts protocol and host to lowercase.
- **Fast PDF Stream Timeout**:
  - Sets an **8.0-second HTTPX stream timeout** and a **15 MB size ceiling**.
  - Limits digital extraction to a **maximum of 25 pages**, preventing memory exhaustion on academic portals.
- **Kernel Memory Compaction**:
  - Every batch execution triggers:
    ```python
    import gc, ctypes
    gc.collect()
    try:
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except Exception:
        pass
    ```
