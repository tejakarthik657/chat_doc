def sanitize_utf8(val):
    """Sanitize strings by stripping invalid surrogates or bad bytes for clean JSON/Qdrant serialization."""
    if isinstance(val, str):
        return val.encode("utf-8", errors="replace").decode("utf-8", errors="replace").replace("\x00", "")
    elif isinstance(val, dict):
        return {k: sanitize_utf8(v) for k, v in val.items()}
    elif isinstance(val, list):
        return [sanitize_utf8(item) for item in val]
    return val


import os
import uuid
import asyncio
# pyrefly: ignore [missing-import]
import fitz  # PyMuPDF
from datetime import datetime
from pymongo import ReturnDocument
from app.core.config import get_settings
from app.core.storage_cloudinary import get_pdf_download_url
from app.core.embeddings import embed_texts, build_faiss_index
from app.core.bm25 import build_bm25_index
from app.db.mongodb import documents_col, chunks_col, projects_col, crawled_pages_col

settings = get_settings()


def _compute_hash(text: str) -> str:
    import hashlib
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


# ── Step 1: PDF → Paged text with OCR Fallback ──────────────────────────────────

def grid_to_markdown(grid: list[list[str]]) -> str:
    if not grid or not grid[0]:
        return ""
    # Headers
    headers = [str(x or "").strip().replace("\n", " ") for x in grid[0]]
    # Alignments or divider
    divider = ["---"] * len(headers)
    markdown_lines = []
    markdown_lines.append("| " + " | ".join(headers) + " |")
    markdown_lines.append("| " + " | ".join(divider) + " |")
    
    for row in grid[1:]:
        row_str = [str(x or "").strip().replace("\n", " ") for x in row]
        # Pad row with empty cells if it's shorter than header
        if len(row_str) < len(headers):
            row_str += [""] * (len(headers) - len(row_str))
        markdown_lines.append("| " + " | ".join(row_str[:len(headers)]) + " |")
        
    return "\n".join(markdown_lines)


def extract_tables_as_markdown(page) -> str:
    """Find tables on a page and format them as Markdown grids."""
    try:
        if not hasattr(page, "find_tables"):
            return ""
        tables = page.find_tables()
        if not tables or not tables.tables:
            return ""
        
        md_tables = []
        for i, table in enumerate(tables.tables, start=1):
            grid = table.extract()
            if not grid:
                continue
            md = grid_to_markdown(grid)
            if md:
                md_tables.append(f"\n\n### Extracted Table {i}\n{md}\n")
        return "".join(md_tables)
    except Exception as e:
        print(f"[Table Extraction] [WARNING] Failed to extract tables on page: {e}")
        return ""


def extract_pages(file_path: str) -> list[dict]:
    """
    Returns list of {page: int, text: str}.
    Preserves page numbers for source citations.
    """
    doc = fitz.open(file_path)
    pages = []
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    is_cloud = os.environ.get("ENVIRONMENT") == "production" or bool(os.environ.get("PORT")) or bool(os.environ.get("RENDER"))

    enable_table_extraction = (not is_cloud) and (file_size_mb < 10.0)
    
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()
        
        # Reconstruct tables as Markdown if enabled
        if enable_table_extraction:
            table_md = extract_tables_as_markdown(page)
            if table_md:
                text = f"{text}{table_md}"
            
        if text:  # skip blank pages
            pages.append({"page": page_num, "text": text})
    doc.close()
    return pages


def groq_vision_ocr(page) -> str:
    """
    Groq vision OCR fallback.
    Note: Groq decommissioned llama-3.2-90b-vision-preview.
    Text and table extraction rely on PyMuPDF native layers and OCR.space cloud tier.
    """
    return ""



def extract_pages_with_ocr(file_path: str) -> list[dict]:
    """
    Extracts text from a PDF, page-by-page using a 3-Tier Fallback Pipeline:
    - Tier 1: PyMuPDF (fitz) native text layer extraction (< 5ms, 0 cost).
    - Tier 2: OCR.space Cloud OCR (free tier 25,000 req/mo).
    - Tier 3: Google Cloud Vision / Groq Vision OCR fallback.
    """
    from app.core.ocr_space import parse_image_ocr_space
    from app.core.google_vision import parse_image_google_vision

    doc = fitz.open(file_path)
    pages = []
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    is_cloud = os.environ.get("ENVIRONMENT") == "production" or bool(os.environ.get("PORT")) or bool(os.environ.get("RENDER"))

    enable_table_extraction = (not is_cloud) and (file_size_mb < 10.0)
    ocr_attempt_count = 0
    max_ocr_pages = 5  # Bound OCR attempts to prevent latency spikes on cloud
    
    for page_num, page in enumerate(doc, start=1):
        # Tier 1: Native Text Layer Extraction
        text = page.get_text("text").strip()
        
        # If native text layer is sparse (< 50 chars), trigger OCR Fallbacks (up to max_ocr_pages)
        if len(text) < 50 and ocr_attempt_count < max_ocr_pages:
            ocr_attempt_count += 1
            print(f"[OCR Pipeline] Page {page_num} sparse text ({len(text)} chars). Triggering OCR Fallback...")
            try:
                pix = page.get_pixmap(dpi=120)
                img_bytes = pix.tobytes("png")
                
                # Tier 2: Free Cloud OCR.space API
                ocr_text = parse_image_ocr_space(img_bytes, filename=f"page_{page_num}.png")
                if ocr_text and len(ocr_text.strip()) > 10:
                    text = ocr_text.strip()
                    print(f"[OCR Pipeline] Tier 2 (OCR.space) successfully extracted {len(text)} chars for page {page_num}.")
                else:
                    # Tier 3: Google Cloud Vision API
                    vision_text = parse_image_google_vision(img_bytes)
                    if vision_text and len(vision_text.strip()) > 10:
                        text = vision_text.strip()
                        print(f"[OCR Pipeline] Tier 3 (Google Vision) extracted {len(text)} chars for page {page_num}.")
                    elif settings.groq_api_key:
                        groq_text = groq_vision_ocr(page)
                        if groq_text:
                            text = groq_text.strip()
            except Exception as ocr_e:
                print(f"[OCR Pipeline Warning] Page {page_num} OCR failed: {ocr_e}")
        
        # Reconstruct tables as Markdown if enabled
        if enable_table_extraction:
            table_md = extract_tables_as_markdown(page)
            if table_md and table_md not in text:
                text = f"{text}\n\n{table_md}"
            
        if text:
            pages.append({"page": page_num, "text": text})
            
    doc.close()
    return pages


_docling_converter = None

def get_docling_converter():
    """Lazy singleton for Docling DocumentConverter to avoid heavy initialization latency."""
    global _docling_converter
    if _docling_converter is None:
        from docling.document_converter import DocumentConverter
        print("[Docling] Initializing DocumentConverter (singleton)...")
        _docling_converter = DocumentConverter()
    return _docling_converter


def extract_pages_with_docling(file_path: str) -> list[dict]:
    """
    Extracts text from a PDF, page-by-page, using Docling for layout-aware table/structure parsing.
    Falls back to extract_pages_with_ocr on any import or runtime failure.
    
    Returns list of {page, text, tables} where tables is a list of markdown table strings.
    """
    max_file_size_mb = 50.0
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    
    if file_size_mb > max_file_size_mb:
        print(f"[Docling] [WARNING] File too large ({file_size_mb:.1f}MB). Skipping Docling, using PyMuPDF fallback.")
        ocr_pages = extract_pages_with_ocr(file_path)
        return [{"page": p["page"], "text": p["text"], "tables": []} for p in ocr_pages]
    
    try:
        print(f"[Docling] Converting {file_path} using layout-aware extraction singleton...")
        converter = get_docling_converter()
        result = converter.convert(file_path)
        doc = result.document
        
        pages_dict = {}
        tables_by_page = {}
        
        for element, level in doc.iterate_items():
            if not (hasattr(element, "prov") and element.prov):
                continue
            page_num = element.prov[0].page_no
            
            # Detect table elements
            element_type = type(element).__name__
            is_table = (
                "Table" in element_type
                or (hasattr(element, "export_to_markdown") and "table" in str(element).lower())
            )
            
            if is_table:
                try:
                    if hasattr(element, "export_to_markdown"):
                        table_md = element.export_to_markdown()
                    elif hasattr(element, "export_to_text"):
                        table_md = element.export_to_text()
                    else:
                        table_md = str(element)
                    
                    if table_md and len(table_md.strip()) > 5:
                        if page_num not in tables_by_page:
                            tables_by_page[page_num] = []
                        tables_by_page[page_num].append(table_md.strip())
                except Exception:
                    pass
                continue
            
            text_val = ""
            if hasattr(element, "text"):
                text_val = element.text
            elif hasattr(element, "export_to_markdown"):
                text_val = element.export_to_markdown()
            elif hasattr(element, "export_to_text"):
                text_val = element.export_to_text()
            
            if text_val:
                if page_num not in pages_dict:
                    pages_dict[page_num] = []
                pages_dict[page_num].append(text_val)
                    
        pages = []
        if pages_dict:
            for p_num in sorted(pages_dict.keys()):
                page_text = "\n\n".join(pages_dict[p_num]).strip()
                tables = tables_by_page.get(p_num, [])
                pages.append({
                    "page": p_num,
                    "text": page_text,
                    "tables": tables
                })
            print(f"[Docling] Extracted {len(pages)} pages with {sum(len(p.get('tables',[])) for p in pages)} tables.")
        else:
            md_text = doc.export_to_markdown()
            pages.append({"page": 1, "text": md_text, "tables": []})
            print("[Docling] Extracted entire document as a single markdown chunk.")
            
        return pages
    except Exception as e:
        print(f"[Docling] [WARNING] Layout-aware extraction failed: {e}. Falling back to PyMuPDF + Tesseract/Vision OCR...")
        ocr_pages = extract_pages_with_ocr(file_path)
        return [{"page": p["page"], "text": p["text"], "tables": []} for p in ocr_pages]


# ── Step 2: Semantic Chunking ──────────────────────────────────────────────────

def is_table_block(block: str) -> bool:
    lines = [l.strip() for l in block.split("\n") if l.strip()]
    if any(l.startswith("|") and l.endswith("|") for l in lines):
        return True
    if "### Extracted Table" in block or "[TABLE]" in block:
        return True
    return False


def is_code_block(block: str) -> bool:
    stripped = block.strip()
    return stripped.startswith("```") and stripped.endswith("```")


def semantic_chunking(text: str, source_name: str, url: str, page_num: int = 1,
                      parent_text: str | None = None) -> list[dict]:
    """
    Semantic Structural Chunker:
    - Splits text on logical paragraphs and headings while preserving tables and code blocks as atomic units.
    - Tracks active markdown section headers and injects contextual blurb prefix for precise vector grounding.
    """
    from app.ingestion.sanitizer import clean_extracted_text
    text = clean_extracted_text(text)
    parent = clean_extracted_text(parent_text) if parent_text is not None else text
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = []
    current_length = 0
    parent_id = _compute_hash(parent)
    active_section = ""
    section_map = {}
    
    for p in paragraphs:
        p_clean = p.strip()
        if not p_clean:
            continue
            
        # Detect active section heading
        if p_clean.startswith("#"):
            first_line = p_clean.split("\n")[0].strip("# \t")
            if first_line:
                active_section = first_line[:120]
        
        p_len = len(p_clean)
        
        # Atomic Unit Protection for tables and code blocks
        if is_table_block(p_clean) or is_code_block(p_clean):
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
                section_map[len(chunks) - 1] = active_section
                current_chunk = []
                current_length = 0
            chunks.append(p_clean)
            section_map[len(chunks) - 1] = active_section
            continue
        
        # If single paragraph is larger than limits, split it by sentence
        if p_len > settings.chunk_size:
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
                section_map[len(chunks) - 1] = active_section
                current_chunk = []
                current_length = 0
                
            sentences = p_clean.replace(". ", ".\n").split("\n")
            sub_chunk = []
            sub_len = 0
            for s in sentences:
                s_clean = s.strip()
                if not s_clean:
                    continue
                if sub_len + len(s_clean) > settings.chunk_size:
                    if sub_chunk:
                        chunks.append(" ".join(sub_chunk))
                        section_map[len(chunks) - 1] = active_section
                    sub_chunk = [s_clean]
                    sub_len = len(s_clean)
                else:
                    sub_chunk.append(s_clean)
                    sub_len += len(s_clean)
            if sub_chunk:
                chunks.append(" ".join(sub_chunk))
                section_map[len(chunks) - 1] = active_section
        else:
            # Group smaller paragraphs together
            if current_length + p_len > settings.chunk_size:
                chunks.append("\n\n".join(current_chunk))
                section_map[len(chunks) - 1] = active_section
                current_chunk = [p_clean]
                current_length = p_len
            else:
                current_chunk.append(p_clean)
                current_length += p_len + 2  # account for \n\n separator
                
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))
        section_map[len(chunks) - 1] = active_section
        
    result = []
    for idx, c_text in enumerate(chunks):
        c_clean = c_text.strip()
        if len(c_clean) < 30:  # drop micro-chunks
            continue
        sec = section_map.get(idx, "")
        if sec:
            contextual_prefix = f"[{source_name}] Section: {sec}\n\n{c_clean}"
        else:
            contextual_prefix = f"[{source_name}]\n\n{c_clean}"
            
        parent_raw = parent.strip()[:6000]
        if len(parent_raw) > 250:
            import zlib
            parent_stored = zlib.compress(parent_raw.encode("utf-8"))
        else:
            parent_stored = parent_raw

        result.append({
            "chunk_id": str(uuid.uuid4()),
            "source_name": source_name,
            "url": url,
            "page": page_num,
            "text": c_clean,
            "contextual_text": contextual_prefix,
            "section": sec,
            "parent_id": parent_id,
            "parent_text": parent_stored,
        })
    return result


def chunk_pages(pages: list[dict], doc_id: str, filename: str) -> list[dict]:
    """
    Splits each page's text with semantic awareness.
    Uses paragraph-preserving logic from semantic_chunking() for structure integrity.
    Also propagates table metadata from pages.
    """
    chunks = []
    embedding_counter = 0
    
    for page_data in pages:
        page_text = page_data.get("text", "")
        tables = page_data.get("tables", [])
        if tables:
            page_text = page_text + "\n\n" + "\n\n".join(
                f"[TABLE]\n{t}" for t in tables
            )
        page_chunks = semantic_chunking(
            page_text,
            source_name=filename,
            url=f"doc:{doc_id}",
            page_num=page_data.get("page", 1),
            parent_text=page_data.get("text")
        )
        for c in page_chunks:
            c["doc_id"] = doc_id
            c["embedding_id"] = embedding_counter
            c["has_table"] = len(tables) > 0
            c["table_count"] = len(tables)
            chunks.append(c)
            embedding_counter += 1

    return chunks


# ── Step 3+4: Embed + Index (FAISS + BM25) ───────────────────────────────────

async def build_index(chunks: list[dict], doc_id: str):
    """
    Build both indexes from the same chunk list:
      - FAISS: dense semantic vectors (FastEmbed ONNX engine)
      - BM25:  sparse keyword index (rank_bm25)
    Both saved to disk in thread pools to keep event loop free.
    """
    texts = [c["text"] for c in chunks]

    # Dense index (FAISS)
    vectors = await asyncio.to_thread(embed_texts, texts)
    await asyncio.to_thread(build_faiss_index, vectors, doc_id)

    # Sparse index (BM25) — pure Python, milliseconds
    await asyncio.to_thread(build_bm25_index, chunks, doc_id)


# ── Summary Generator for Hierarchical RAG ────────────────────────────────────

def generate_document_summary(filename: str, pages: list[dict]) -> str:
    """Generates a concise 1-page summary of the entire document to provide hierarchical context."""
    try:
        from app.core.llm_groq import generate
        # Join sample texts to get context without exceeding token limits
        sampled_pages = []
        if len(pages) <= 6:
            sampled_pages = pages
        else:
            sampled_pages = pages[:3] + pages[-3:]
            
        full_text = "\n\n".join(p.get("text", "")[:2000] for p in sampled_pages)
        prompt = (
            f"Please write a comprehensive, professional summary of the document '{filename}'. "
            f"Describe its main sections, core topics, and key details. Keep it concise (under 250 words) "
            f"so that it can be used as a global system prompt context for subsequent questions. "
            f"Focus on factual representation."
        )
        summary = generate(context=full_text[:12000], question=prompt)
        print(f"[Summary Generator] Successfully generated summary for {filename}")
        return summary
    except Exception as e:
        print(f"[Summary Generator] [WARNING] Failed to generate document summary: {e}")
        return ""


# ── Master pipelines ───────────────────────────────────────────────────────────

async def ingest_document(
    file_path: str,
    filename: str,
    doc_id: str,
    user_id: str
) -> dict:
    """
    Full ingestion pipeline. Called after the file is saved to disk.
    Updates the document record with status and page count in under 2 seconds.
    """
    temporary_file = False
    try:
        # Claim the document atomically. The web fallback and queue worker may
        # both receive the same job, but only one process should ingest it.
        claimed = await documents_col().find_one_and_update(
            {
                "_id": doc_id,
                "status": "processing",
                "ingestion_claimed": {"$ne": True},
            },
            {
                "$set": {
                    "ingestion_claimed": True,
                    "ingestion_started_at": datetime.utcnow(),
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        if not claimed:
            return {"status": "skipped", "reason": "already claimed or no longer processing"}

        # Step 0: Ensure file exists locally; if missing (e.g. container restart), restore from MongoDB backup
        if not file_path or not os.path.exists(file_path):
            doc = await documents_col().find_one({"_id": doc_id})
            target_dir = os.path.join(settings.storage_dir, "uploads", user_id)
            os.makedirs(target_dir, exist_ok=True)
            file_path = os.path.join(target_dir, f"{doc_id}_{filename}")
            if not os.path.exists(file_path):
                if doc and doc.get("file_data"):
                    with open(file_path, "wb") as f:
                        f.write(doc["file_data"])
                    print(f"[Ingestion] Restored {file_path} from MongoDB file_data backup in 2ms.")
                elif doc and (doc.get("file_url") or doc.get("storage_public_id")):
                    try:
                        import httpx
                        download_url = get_pdf_download_url(doc.get("storage_public_id", "")) or doc.get("file_url")
                        if download_url and str(download_url).startswith("http"):
                            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as dl_client:
                                r = await dl_client.get(download_url)
                                if r.status_code == 200:
                                    with open(file_path, "wb") as f:
                                        f.write(r.content)
                                    print(f"[Ingestion] Restored {file_path} from durable object storage.")
                    except Exception as dl_err:
                        print(f"[Ingestion] Durable storage download warning: {dl_err}")

        # Step 1: Extract. Instant PyMuPDF extraction (< 50ms)
        pages = []
        try:
            print(f"[Ingestion] Running ultra-fast PyMuPDF extraction for {file_path}...")
            pages = await asyncio.to_thread(extract_pages, file_path)
            total_chars = sum(len(p.get("text", "")) for p in pages)
            print(f"[Ingestion] Extracted {len(pages)} pages with {total_chars} characters.")
        except Exception as fast_err:
            print(f"[Ingestion] Fast-path PyMuPDF extraction error: {fast_err}")

        # Fallback ONLY if PDF has virtually zero text (scanned PDF)
        if not pages or sum(len(p.get("text", "")) for p in pages) < 20:
            print(f"[Ingestion] Document appears scanned/image-only. Attempting OCR fallback...")
            try:
                pages = await asyncio.to_thread(extract_pages_with_ocr, file_path)
            except Exception as ocr_err:
                print(f"[Ingestion] OCR fallback error: {ocr_err}")

        page_count = len(pages)

        # Step 2: Semantic Chunking
        chunks = chunk_pages(pages, doc_id, filename)

        if not chunks:
            raise ValueError("No extractable text found in PDF. Please ensure the document contains readable text.")

        # Step 3+4: Embed + Index (Non-blocking FastEmbed ONNX + BM25)
        await build_index(chunks, doc_id)

        # Step 5: Fast instant summary from first chunk (<1ms)
        summary = ""
        if chunks:
            summary = chunks[0]["text"][:300].strip() + "..."

        # Step 6: Persist chunk metadata to MongoDB in batches
        chunk_batch_size = 500
        for i in range(0, len(chunks), chunk_batch_size):
            await chunks_col().insert_many(chunks[i:i + chunk_batch_size])

        # Step 7: Mark document as READY IMMEDIATELY! (<500ms total elapsed time)
        size_mb = round(os.path.getsize(file_path) / (1024 * 1024), 2) if os.path.exists(file_path) else 0.0
        await documents_col().update_one(
            {"_id": doc_id},
            {"$set": {
                "status": "ready",
                "page_count": page_count,
                "chunk_count": len(chunks),
                "size_mb": size_mb,
                "summary": summary
            }}
        )

        # Step 8: Purge memory immediately to stay well below 512MB
        import gc
        gc.collect()
        try:
            import ctypes
            ctypes.CDLL("libc.so.6").malloc_trim(0)
        except Exception:
            pass

        print(f"[Ingestion] Document {filename} ({doc_id}) successfully marked READY in {page_count} pages, {len(chunks)} chunks!")
        return {"status": "ready", "pages": page_count, "chunks": len(chunks)}

    except Exception as e:
        print(f"[Ingestion Error] Document {doc_id} failed: {e}")
        await documents_col().update_one(
            {"_id": doc_id},
            {"$set": {"status": "error", "error_message": str(e)}}
        )
        raise
    finally:
        if temporary_file and file_path and os.path.exists(file_path):
            os.remove(file_path)


async def process_single_page(page) -> tuple[list[dict], str, str, str | None]:
    import asyncio
    import httpx
    import tempfile

    page_type = page.get("page_type", "html")
    url = page["url"]
    title = page.get("title", url)

    try:
        if page_type == "html":
            chunks = semantic_chunking(page["text_content"], source_name=title, url=url, page_num=1)
            return chunks, page["_id"], "indexed", None

        if page_type == "pdf":
            file_path = page.get("file_path", "")
            temporary_file = False
            if not file_path or not os.path.exists(file_path):
                temp_file = tempfile.NamedTemporaryFile(prefix=f"crawl_{page['_id']}_", suffix=".pdf", delete=False)
                file_path = temp_file.name
                temp_file.close()
                temporary_file = True
                downloaded = False
                # Priority 1: Direct source URL download (e.g. from https://kitsw.ac.in/.../file.pdf)
                if page.get("url") and page["url"].startswith("http"):
                    try:
                        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, verify=False) as client:
                            response = await client.get(page["url"])
                            if response.status_code == 200:
                                with open(file_path, "wb") as f_dl:
                                    f_dl.write(response.content)
                                downloaded = True
                    except Exception as src_err:
                        print(f"[Crawl Ingestion] Direct source download note: {src_err}")
                # Priority 2: Durable storage download
                if not downloaded and (page.get("file_url") or page.get("storage_public_id")):
                    try:
                        download_url = get_pdf_download_url(page.get("storage_public_id", "")) or page.get("file_url")
                        if download_url and str(download_url).startswith("http"):
                            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                                response = await client.get(download_url)
                                if response.status_code == 200:
                                    with open(file_path, "wb") as downloaded_f:
                                        downloaded_f.write(response.content)
                                    downloaded = True
                    except Exception:
                        pass
                if not downloaded or not os.path.exists(file_path):
                    return [], page["_id"], "error", f"PDF file could not be retrieved: {page.get('url')}"

            if not os.path.exists(file_path):
                return [], page["_id"], "error", f"PDF file not found: {file_path}"

            try:
                pdf_pages = await asyncio.to_thread(extract_pages_with_ocr, file_path)
                if not pdf_pages:
                    return [], page["_id"], "error", "No extractable text found in PDF, even after attempting OCR fallback."

                chunks = []
                for pdf_page in pdf_pages:
                    chunks.extend(semantic_chunking(
                        pdf_page["text"],
                        source_name=title,
                        url=url,
                        page_num=pdf_page["page"],
                    ))
                return chunks, page["_id"], "indexed", None
            finally:
                if temporary_file and os.path.exists(file_path):
                    os.remove(file_path)

        return [], page["_id"], "error", f"Unsupported page type: {page_type}"
    except Exception as e:
        return [], page["_id"], "error", str(e)


def extract_metadata_from_url_and_title(url: str, title: str, content_text: str = "") -> dict:
    """
    Extract department and document_type metadata from url, title, and content.
    Uses multi-source signals for accurate classification.
    """
    url_lower = url.lower()
    title_lower = title.lower()
    content_lower = (content_text or "")[:5000].lower()
    
    # 1. Department Detection (URL + Title + Content)
    department = None
    departments = ["cse", "ece", "eee", "it", "mech", "civil", "mba", "mca"]
    dept_keywords = {
        "cse": ["cse", "computer science", "computer science and engineering", "csit"],
        "ece": ["ece", "electronics", "communication"],
        "eee": ["eee", "electrical", "electronics and electrical"],
        "it": ["it ", "information technology", "b.tech it"],
        "mech": ["mech", "mechanical", "mechanical engineering"],
        "civil": ["civil", "civil engineering"],
        "mba": ["mba", "master of business", "management studies"],
        "mca": ["mca", "master of computer applications"],
    }
    for dept, kws in dept_keywords.items():
        if f"/{dept}" in url_lower or f"_{dept}" in url_lower or f"-{dept}" in url_lower:
            department = dept
            break
        if any(kw in url_lower or kw in title_lower or kw in content_lower for kw in kws):
            department = dept
            break

    # 2. Document Type Detection (multi-source)
    doc_type = "general"
    signals = url_lower + " " + title_lower + " " + content_lower

    # Hierarchical type scoring
    type_keywords = {
        "faculty": ["faculty", "profile", "staff", "hod", "lecturer", "teacher", "member",
                     "biodata", "bio-data", "resume", "qualification", "designation",
                     "dr. ", "professor ", "associate professor", "assistant professor"],
        "placement": ["placement", "recruit", "salary", "package", "offer letter", "companies",
                       "placed", "placement record", "highest package", "average package"],
        "syllabus": ["syllabus", "curriculum", "course", "subject", "credit", "academic-regulation",
                      "regulation", "scheme", "semester"],
        "labs": ["laboratory", "lab ", "lab-", "labs ", "lab:", "lab manual"],
        "research": ["research", "publication", "patent", "journal", "conference", "phd", "paper"],
        "facilities": ["facilities", "infrastructure", "campus", "hostel", "library", "sports"],
        "admissions": ["admission", "eligibility", "fee structure", "fees", "entrance"],
        "events": ["event", "workshop", "seminar", "conference", "webinar", "fdp"],
        "governing": ["governing body", "board of management", "trust", "society", "committee"],
        "naac": ["naac", "nba", "accreditation", "iqa", "iqac"],
    }
    for dtype, kws in type_keywords.items():
        if any(kw in signals for kw in kws):
            doc_type = dtype
            break

    # 3. Source Type Detection
    source_type = "html"
    if url_lower.endswith(".pdf"):
        source_type = "pdf"
    elif "download" in url_lower and ".pdf" not in url_lower:
        source_type = "download"

    return {
        "department": department,
        "document_type": doc_type,
        "source_type": source_type
    }


async def process_project_crawled_data(
    project_id: str,
    user_id: str,
    force_recreate: bool = False,
):
    """
    Processes all 'pending' pages for a project in parallel:
      1. Performs PDF OCR fallback or text extraction
      2. Performs Semantic Chunking
      3. Generates Embeddings
      4. Upserts vectors + payloads to Qdrant collection
    """
    import asyncio
    import time
    from app.ingestion.metrics import ExtractionMetrics
    
    metrics = ExtractionMetrics(project_id)
    try:
        start_time = time.time()
        # Get project name
        project = await projects_col().find_one({"_id": project_id})
        project_name = project.get("name", "Project") if project else "Project"
        
        # Get all crawled pages for the project: pending pages, or all pages if recreating/repairing
        find_filter = {"project_id": project_id}
        if not force_recreate:
            # Check if we have pending pages, or if no chunks exist at all
            existing_chunks = await chunks_col().count_documents({"doc_id": project_id})
            if existing_chunks > 0:
                find_filter["status"] = "pending"
            else:
                find_filter["$or"] = [{"status": "pending"}, {"text_content": {"$exists": True, "$ne": ""}}]
        else:
            find_filter["$or"] = [{"status": "pending"}, {"text_content": {"$exists": True, "$ne": ""}}]

        pending_pages = await crawled_pages_col().find(find_filter).to_list(length=1000)
        
        if not pending_pages:
            print(f"[Ingestion] No pending pages to index for Project {project_id}")
            await projects_col().update_one(
                {"_id": project_id},
                {"$set": {"status": "active"}}
            )
            return

        print(f"[Ingestion] Found {len(pending_pages)} pages to extract/OCR...")
        
        # Process pages with strict concurrency control to prevent RAM exhaustion on 512MB cloud tiers
        is_cloud = os.environ.get("ENVIRONMENT") == "production" or bool(os.environ.get("PORT")) or bool(os.environ.get("RENDER"))
        concurrency = 1 if is_cloud else 3
        semaphore = asyncio.Semaphore(concurrency)
        
        all_chunks = []
        processed_count = 0
        total_pages = len(pending_pages)
        
        async def process_and_save_page(page, idx):
            nonlocal processed_count
            async with semaphore:
                page_url = page["url"]
                page_type = page.get("page_type", "html")
                print(f"[Ingestion] [{idx+1}/{total_pages}] Processing {page_type}: {page_url}")
                
                chunks, page_id, status, error_msg = await process_single_page(page)
                
                # Record metrics
                metrics.record_page_processed()
                if status == "indexed" and chunks:
                    metrics.record_quality_pass()
                    if page_type == "pdf":
                        metrics.record_docling_success(page.get("page_count", 1) or 1)
                    metrics.record_chunks_created(chunks)
                elif status == "error":
                    metrics.quality_issues.append({
                        "type": "extraction_error",
                        "url": page_url,
                        "error": str(error_msg)[:200],
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                if status == "indexed" and chunks:
                    await crawled_pages_col().update_one(
                        {"_id": page_id},
                        {"$set": {"status": "indexed"}}
                    )
                else:
                    await crawled_pages_col().update_one(
                        {"_id": page_id},
                        {"$set": {"status": "error", "error_message": error_msg}}
                    )
                
                processed_count += 1
                if processed_count % 5 == 0 or processed_count == total_pages:
                    print(f"[Ingestion] Progress: {processed_count}/{total_pages} pages processed.")
                
                return chunks

        tasks = [process_and_save_page(p, i) for i, p in enumerate(pending_pages)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for res in results:
            if isinstance(res, list):
                all_chunks.extend(res)
            elif isinstance(res, Exception):
                print(f"[Ingestion Error] Page extraction error caught safely: {res}")

        if not all_chunks:
            print(f"[Ingestion] No chunks created for Project {project_id}")
            await projects_col().update_one(
                {"_id": project_id},
                {"$set": {"status": "active"}}
            )
            return

        # Enrich chunks with metadata, sequence ids, and database compatibility fields
        for idx, chunk in enumerate(all_chunks):
            meta = extract_metadata_from_url_and_title(
                chunk["url"],
                chunk["source_name"],
                chunk.get("text", "")
            )
            chunk["department"] = meta["department"]
            chunk["document_type"] = meta["document_type"]
            chunk["source_type"] = meta.get("source_type", "html")
            chunk["embedding_id"] = idx
            chunk["doc_id"] = project_id  # maps to doc_id schema in MongoDB chunks_col
            chunk["filename"] = chunk["source_name"]

        # Persist chunks in MongoDB chunks_col for keyword search (BM25) capability
        await chunks_col().delete_many({"doc_id": project_id})
        
        # Sanitize all chunk strings to prevent any invalid utf-8 byte crashes
        all_chunks = sanitize_utf8(all_chunks)

        # Batch insert chunks to prevent MongoDB write timeouts on large crawls
        chunk_batch_size = 500
        for i in range(0, len(all_chunks), chunk_batch_size):
            await chunks_col().insert_many(all_chunks[i:i + chunk_batch_size])

        # Build BM25 index on the project chunks (uses raw text)
        build_bm25_index(all_chunks, project_id)

        print(f"[Ingestion] Total chunks to index: {len(all_chunks)}")
        
        # ── Contextual Retrieval: generate context blurbs for embedding ─────────
        if settings.contextual_enabled and len(all_chunks) <= 30:
            from app.rag.contextual import generate_context_batch, apply_contextual_prefix
            CONTEXT_BATCH = 20
            contextual_used = 0
            for i in range(0, len(all_chunks), CONTEXT_BATCH):
                batch = all_chunks[i:i + CONTEXT_BATCH]
                texts = [c["text"] for c in batch]
                sources = [c["source_name"] for c in batch]
                contexts = generate_context_batch(sources[0], texts)
                for chunk, ctx in zip(batch, contexts):
                    contextual = apply_contextual_prefix(chunk, ctx)
                    chunk["contextual_text"] = contextual
                    if ctx:
                        contextual_used += 1
            if contextual_used:
                print(f"[Contextual] Generated context for {contextual_used}/{len(all_chunks)} chunks")
        
        # Generate Embeddings — use contextual text when available, else raw text
        embedding_texts = [c.get("contextual_text", c["text"]) for c in all_chunks]
        vectors = embed_texts(embedding_texts)
        vector_dim = vectors.shape[1]
        
        # Initialize Qdrant collection (drop stale vectors on full re-ingest)
        collection_name = f"project_{project_id}"
        init_collection(collection_name, vector_dim, force_recreate=force_recreate)
        
        # Insert into Qdrant
        qdrant_client = get_qdrant_client()
        points = []
        for idx, (chunk, vector) in enumerate(zip(all_chunks, vectors)):
            points.append(qdrant_models.PointStruct(
                id=str(uuid.uuid4()),  # Qdrant supports UUID strings directly
                vector=vector.tolist(),
                payload=sanitize_utf8({
                    "chunk_id": str(chunk["chunk_id"]),
                    "project_id": str(project_id),
                    "source_name": str(chunk["source_name"]),
                    "url": str(chunk["url"]),
                    "page": chunk["page"],
                    "text": str(chunk["text"]),
                    "source_type": chunk.get("source_type", "html"),
                    "department": chunk.get("department"),
                    "document_type": chunk.get("document_type"),
                    "embedding_id": chunk.get("embedding_id"),
                    "parent_id": chunk.get("parent_id"),
                    "parent_text": str(chunk.get("parent_text", ""))[:8000],
                    "contextual_text": str(chunk.get("contextual_text", chunk["text"]))[:2000]
                })
            ))
            
        # Batch upsert points
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i:i+batch_size]
            qdrant_client.upsert(
                collection_name=collection_name,
                points=batch
            )
            
        print(f"[Ingestion] Upserted {len(points)} chunks into Qdrant collection: {collection_name}")
        import gc
        gc.collect()
        try:
            import ctypes
            ctypes.CDLL("libc.so.6").malloc_trim(0)
        except Exception:
            pass
        import gc
        gc.collect()
        try:
            import ctypes
            ctypes.CDLL("libc.so.6").malloc_trim(0)
        except Exception:
            pass
        
        # Generate global project summary for Hierarchical RAG
        project_summary = ""
        try:
            from app.core.llm_groq import generate
            print(f"[Project Summary] Generating global summary for project: {project_name}")
            sample_texts = [c["text"] for c in all_chunks[:10]]
            merged_sample = "\n\n".join(sample_texts)
            prompt = (
                f"Please write a comprehensive, professional summary of the crawled database/project '{project_name}'. "
                f"Describe its main domains, departments, and topics covered. Keep it concise (under 250 words) "
                f"so that it can be used as a global system prompt context for subsequent questions."
            )
            project_summary = generate(context=merged_sample[:12000], question=prompt)
        except Exception as sum_err:
            print(f"[Project Summary] [WARNING] Failed to generate summary: {sum_err}")

        # Build Neo4j knowledge graph for the project
        try:
            await build_neo4j_graph_for_project(project_id, project_name, all_chunks)
        except Exception as graph_err:
            print(f"[Neo4j Graph] [WARNING] Graph construction failed: {graph_err}")

        # Update Project Status to ready/active
        await projects_col().update_one(
            {"_id": project_id},
            {"$set": {
                "status": "active",
                "indexed_at": datetime.utcnow(),
                "summary": project_summary
            }}
        )

        # Preserving downloaded PDF files so users can view evidence and document citations
        pass
        
        elapsed_time = time.time() - start_time
        
        # Log extraction quality metrics
        metrics.log_summary()
        print(
            f"""
            =========================================
            INGESTION METRICS: Project {project_id}
            -----------------------------------------
            Pages/PDFs processed: {len(pending_pages)}
            Chunks generated:     {len(all_chunks)}
            Embeddings created:   {len(points)}
            Time taken:           {elapsed_time:.2f} seconds
            Quality Score:        {metrics.get_quality_score()}%
            =========================================
            """
        )
    except Exception as e:
        print(f"[Ingestion] [ERROR] Ingest process failed: {e}")
        await projects_col().update_one(
            {"_id": project_id},
            {"$set": {"status": "error", "error_message": str(e)}}
        )
        raise


async def build_neo4j_graph_for_project(project_id: str, project_name: str, chunks: list[dict]):
    """
    Extracts entities and relationships from chunk texts using LLM,
    and inserts them into the Neo4j Graph Database.
    """
    import json
    import re
    from app.core.config import get_settings
    from app.core.llm_groq import generate
    
    settings = get_settings()
    
    # Try importing neo4j and checking connection
    try:
        from app.db.neo4j import get_neo4j_driver
        # Try getting the driver. If it's not configured properly, this will raise an error.
        driver = get_neo4j_driver()
    except Exception as init_err:
        print(f"[Neo4j Graph] [WARNING] Neo4j is not initialized or configured. Skipping graph creation: {init_err}")
        return

    print(f"[Neo4j Graph] Building knowledge graph for project: {project_name}")
    
    # Consolidate text from chunks
    sample_texts = [c["text"] for c in chunks[:15]]
    merged_text = "\n\n".join(sample_texts)
    
    prompt = (
        "Analyze the following text and extract key entities and their semantic relationships. "
        "Return the output as a valid JSON object matching this schema:\n"
        "{\n"
        "  \"entities\": [\n"
        "    {\"name\": \"Entity Name\", \"type\": \"Product|Technology|Person|Organization|Department|API\"}\n"
        "  ],\n"
        "  \"relations\": [\n"
        "    {\"source\": \"Source Entity Name\", \"relationship\": \"USES|DEVELOPES|PRICED_AT|BELONGS_TO|PARTS_OF\", \"target\": \"Target Entity Name\"}\n"
        "  ]\n"
        "}\n"
        "Rules:\n"
        "1. Extract only the most prominent entities and relationships.\n"
        "2. Keep entity names normalized (e.g. use standard names, avoid pronouns).\n"
        "3. Strictly return ONLY the JSON payload, no conversation, no markdown wrappers."
    )
    
    entities = []
    relations = []
    try:
        # Limit text size to 3000 chars to fit context models and run faster
        raw_output = generate(context=merged_text[:3000], question=prompt)
        clean_json = re.sub(r"^```json\s*|```$", "", raw_output.strip(), flags=re.MULTILINE)
        data = json.loads(clean_json)
        entities = data.get("entities", [])
        relations = data.get("relations", [])
        print(f"[Neo4j Graph] Extracted {len(entities)} entities and {len(relations)} relationships.")
    except Exception as e:
        print(f"[Neo4j Graph] [WARNING] LLM graph extraction failed: {e}. Falling back to default structural entities.")
        p_clean = project_name.strip() if project_name else "Domain"
        entities = [
            {"name": f"{p_clean} Home", "type": "Organization"},
            {"name": f"{p_clean} Services", "type": "Department"},
            {"name": f"{p_clean} Documentation", "type": "API"}
        ]
        relations = [
            {"source": f"{p_clean} Home", "relationship": "HAS_ENTITY", "target": f"{p_clean} Services"},
            {"source": f"{p_clean} Services", "relationship": "USES", "target": f"{p_clean} Documentation"}
        ]
        
    # Write to Neo4j in a session (de-indented outside of except)
    try:
        with driver.session() as session:
            # 1. Create Project Node
            session.run(
                "MERGE (p:Project {id: $project_id}) ON CREATE SET p.name = $project_name",
                {"project_id": project_id, "project_name": project_name}
            )
            
            # 2. Insert Entities and link to Project
            for ent in entities:
                name = ent.get("name")
                type_ = ent.get("type", "Entity")
                if name:
                    # Create Entity
                    session.run(
                        "MERGE (e:Entity {name: $name, project_id: $project_id}) ON CREATE SET e.type = $type",
                        {"name": name, "project_id": project_id, "type": type_}
                    )
                    # Link to Project
                    session.run(
                        "MATCH (p:Project {id: $project_id}) "
                        "MATCH (e:Entity {name: $name, project_id: $project_id}) "
                        "MERGE (p)-[:HAS_ENTITY]->(e)",
                        {"project_id": project_id, "name": name}
                    )
                    
            # 3. Insert Relationships
            for rel in relations:
                source = rel.get("source")
                target = rel.get("target")
                rel_type = rel.get("relationship", "RELATED_TO").replace(" ", "_").upper()
                if source and target:
                    session.run(
                        f"MATCH (a:Entity {{name: $source, project_id: $project_id}}) "
                        f"MATCH (b:Entity {{name: $target, project_id: $project_id}}) "
                        f"MERGE (a)-[r:{rel_type}]->(b)",
                        {"source": source, "target": target, "project_id": project_id}
                    )
        print(f"[Neo4j Graph] Successfully wrote {len(entities)} entities and {len(relations)} relations to Neo4j.")
    except Exception as neo_err:
        print(f"[Neo4j Graph] [NOTICE] Neo4j session write skipped: {neo_err}")
