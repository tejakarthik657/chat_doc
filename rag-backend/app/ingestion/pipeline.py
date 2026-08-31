import os
import uuid
# pyrefly: ignore [missing-import]
import fitz  # PyMuPDF
from datetime import datetime
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client.http import models as qdrant_models

from app.core.config import get_settings
from app.core.embeddings import embed_texts, build_faiss_index
from app.core.bm25 import build_bm25_index
from app.db.mongodb import documents_col, chunks_col, projects_col, crawled_pages_col
from app.db.qdrant import get_qdrant_client, init_collection

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
    enable_table_extraction = file_size_mb < 10.0
    
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
    """Uses Groq's Vision models to OCR a scanned page with fallback support."""
    import base64
    import time
    from groq import Groq
    
    api_key = settings.groq_api_key
    if not api_key:
        return ""
    
    # Render page to pixmap
    pix = page.get_pixmap(dpi=150)
    img_data = pix.tobytes("png")
    base64_image = base64.b64encode(img_data).decode("utf-8")
    
    client = Groq(api_key=api_key)
    
    # List of models to try in order of preference
    models_to_try = [
        "meta-llama/llama-4-maverick-17b-128e-instruct",
        "llama-3.2-90b-vision-preview"
    ]
    
    for model_name in models_to_try:
        max_retries = 3
        retry_delay = 5
        for attempt in range(max_retries):
            try:
                completion = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Extract all text and tabular information from this document page image. Transcribe tables as markdown. Keep layout structure clean and readable. Output only the transcription, no greetings or explanations."},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{base64_image}"
                                    }
                                }
                            ]
                        }
                    ],
                    temperature=0.1
                )
                res = completion.choices[0].message.content.strip()
                print(f"[Groq Vision OCR] Successfully extracted text from page using {model_name}.")
                return res
            except Exception as e:
                err_str = str(e).lower()
                # If rate limit (429), tokens per minute (TPM), or daily limit (TPD) is hit
                if "rate" in err_str or "limit" in err_str or "429" in err_str or "tpm" in err_str or "tpd" in err_str:
                    # If daily token limit (TPD) was exceeded, switch model immediately
                    if "tpd" in err_str or "daily" in err_str or "day" in err_str:
                        print(f"[Groq Vision OCR] Daily limit exceeded for {model_name}. Switching to next model...")
                        break
                    
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (attempt + 1)
                        print(f"[Groq Vision OCR] Rate limit hit for {model_name}. Waiting {wait_time}s before retry (attempt {attempt+1}/{max_retries})...")
                        time.sleep(wait_time)
                        continue
                
                print(f"[Groq Vision OCR] [WARNING] Failed with {model_name}: {e}")
                break # Try next model in list
                
    return ""


def extract_pages_with_ocr(file_path: str) -> list[dict]:
    """
    Extracts text from a PDF, page-by-page.
    If a page has less than 50 characters, it falls back to OCR via pytesseract or Groq Vision.
    """
    # Check if Tesseract is installed and configure it
    tesseract_available = False
    try:
        import pytesseract
        tesseract_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"
        ]
        tesseract_cmd_to_use = None
        for path in tesseract_paths:
            if os.path.exists(path):
                tesseract_cmd_to_use = path
                break
        if tesseract_cmd_to_use:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd_to_use
            tesseract_available = True
    except Exception:
        tesseract_available = False

    doc = fitz.open(file_path)
    pages = []
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    enable_table_extraction = file_size_mb < 10.0
    
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()
        
        # Fallback to OCR if page has little text (scanned PDF detection)
        if len(text) < 50:
            if tesseract_available:
                print(f"[OCR] [WARNING] Page {page_num} has very little text ({len(text)} chars). Trying Tesseract OCR fallback...")
                try:
                    # Render page to pixmap
                    pix = page.get_pixmap(dpi=150)
                    import io
                    from PIL import Image
                    import pytesseract
                    
                    img_data = pix.tobytes("png")
                    img = Image.open(io.BytesIO(img_data))
                    
                    # Perform OCR
                    ocr_text = pytesseract.image_to_string(img).strip()
                    if ocr_text:
                        text = ocr_text
                        print(f"[OCR] Extracted text from page {page_num} using Tesseract.")
                    else:
                        print(f"[OCR] [WARNING] OCR completed but no text was extracted from page {page_num}.")
                except Exception as ocr_err:
                    print(f"[OCR] [WARNING] Tesseract fallback failed on page {page_num}: {ocr_err}")
            elif settings.groq_api_key:
                print(f"[OCR] [WARNING] Page {page_num} has very little text ({len(text)} chars) and Tesseract is unavailable. Trying Groq Vision OCR fallback...")
                ocr_text = groq_vision_ocr(page)
                if ocr_text:
                    text = ocr_text
        
        # Reconstruct tables as Markdown if enabled
        if enable_table_extraction:
            table_md = extract_tables_as_markdown(page)
            if table_md:
                text = f"{text}{table_md}"
            
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

def semantic_chunking(text: str, source_name: str, url: str, page_num: int = 1,
                      parent_text: str | None = None) -> list[dict]:
    """
    Splits text by paragraphs to keep logical structure (including tables and headers) intact.
    If a paragraph exceeds chunk_size, it splits it by sentence.

    Args:
        text: The text to chunk
        source_name: Document/filename name
        url: Source URL
        page_num: Page number (1-based)
        parent_text: Optional full page text. If not provided, uses the input text.
    """
    parent = parent_text if parent_text is not None else text
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = []
    current_length = 0
    parent_id = _compute_hash(parent)
    
    for p in paragraphs:
        p_clean = p.strip()
        if not p_clean:
            continue
        p_len = len(p_clean)
        
        # If single paragraph is larger than limits, split it by sentence
        if p_len > settings.chunk_size:
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
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
                    sub_chunk = [s_clean]
                    sub_len = len(s_clean)
                else:
                    sub_chunk.append(s_clean)
                    sub_len += len(s_clean)
            if sub_chunk:
                chunks.append(" ".join(sub_chunk))
        else:
            # Group smaller paragraphs together
            if current_length + p_len > settings.chunk_size:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = [p_clean]
                current_length = p_len
            else:
                current_chunk.append(p_clean)
                current_length += p_len + 2  # account for \n\n separator
                
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))
        
    result = []
    for idx, c_text in enumerate(chunks):
        if len(c_text.strip()) < 30:  # drop micro-chunks
            continue
        result.append({
            "chunk_id": str(uuid.uuid4()),
            "source_name": source_name,
            "url": url,
            "page": page_num,
            "text": c_text.strip(),
            "parent_id": parent_id,
            "parent_text": parent.strip()[:8000],
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
      - FAISS: dense semantic vectors (sentence-transformers)
      - BM25:  sparse keyword index (rank_bm25)
    Both saved to disk. Neither recomputed at query time.
    """
    texts = [c["text"] for c in chunks]

    # Dense index (FAISS)
    vectors = embed_texts(texts)
    build_faiss_index(vectors, doc_id)

    # Sparse index (BM25) — pure Python, milliseconds
    build_bm25_index(chunks, doc_id)


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
    Updates the document record with status and page count.
    """
    try:
        # Mark as processing
        await documents_col().update_one(
            {"_id": doc_id},
            {"$set": {"status": "processing"}}
        )

        # Step 1: Extract. Fast-path PyMuPDF + Tesseract/Vision OCR first!
        # Only fall back to Docling singleton if PyMuPDF yields almost no text.
        pages = []
        try:
            print(f"[Ingestion] Attempting fast PyMuPDF extraction for {file_path}...")
            ocr_pages = extract_pages_with_ocr(file_path)
            total_chars = sum(len(p.get("text", "")) for p in ocr_pages)
            if total_chars > 200:
                print(f"[Ingestion] Fast PyMuPDF extraction succeeded ({total_chars} chars). Bypassing Docling.")
                pages = ocr_pages
        except Exception as fast_err:
            print(f"[Ingestion] Fast-path PyMuPDF failed: {fast_err}. Falling back to Docling...")

        if not pages:
            pages = extract_pages_with_docling(file_path)
            
        page_count = len(pages)

        # Step 2: Chunk
        chunks = chunk_pages(pages, doc_id, filename)

        if not chunks:
            # Let's inspect if Tesseract-OCR is missing
            tesseract_installed = False
            try:
                import pytesseract
                # Configure command path if exists
                tesseract_paths = [
                    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"
                ]
                for path in tesseract_paths:
                    if os.path.exists(path):
                        pytesseract.pytesseract.tesseract_cmd = path
                        break
                pytesseract.get_tesseract_version()
                tesseract_installed = True
            except Exception:
                pass

            if not tesseract_installed:
                raise ValueError(
                    "No extractable text found in PDF. Note: Tesseract-OCR is not installed "
                    "on your system. Please install Tesseract-OCR on your computer to enable "
                    "OCR fallback for scanned/image-only documents."
                )
            else:
                raise ValueError("No extractable text found in PDF, even after attempting OCR fallback.")

        # Step 3+4: Embed + Index
        await build_index(chunks, doc_id)

        # Generate Document Summary for hierarchical RAG
        summary = ""
        try:
            summary = generate_document_summary(filename, pages)
        except Exception as sum_err:
            print(f"[Summary] Summary generation skipped or failed: {sum_err}")

        # Step 5: Persist chunk metadata to MongoDB in batches
        chunk_batch_size = 500
        for i in range(0, len(chunks), chunk_batch_size):
            await chunks_col().insert_many(chunks[i:i + chunk_batch_size])

        # Step 6: Mark document as ready
        size_mb = round(os.path.getsize(file_path) / (1024 * 1024), 2)
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

        return {"status": "ready", "pages": page_count, "chunks": len(chunks)}

    except Exception as e:
        await documents_col().update_one(
            {"_id": doc_id},
            {"$set": {"status": "error", "error_message": str(e)}}
        )
        raise


async def process_single_page(page) -> tuple[list[dict], str, str, str | None]:
    import asyncio
    page_type = page.get("page_type", "html")
    url = page["url"]
    title = page.get("title", url)
    
    try:
        if page_type == "html":
            text = page["text_content"]
            chunks = semantic_chunking(text, source_name=title, url=url, page_num=1)
            return chunks, page["_id"], "indexed", None
            
        elif page_type == "pdf":
            file_path = page["file_path"]
            if not os.path.exists(file_path):
                return [], page["_id"], "error", f"PDF file not found: {file_path}"
            
            # Use PyMuPDF with OCR fallback directly to avoid Docling dependency issues/deadlocks
            def extract_pdf_direct():
                try:
                    return extract_pages_with_ocr(file_path)
                except Exception as e:
                    print(f"[Ingestion] [WARNING] Direct PDF extraction failed: {e}")
                    return []
                
            pdf_pages = await asyncio.to_thread(extract_pdf_direct)
            
            if not pdf_pages:
                # Check if Tesseract-OCR is installed
                tesseract_installed = False
                try:
                    import pytesseract
                    tesseract_paths = [
                        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"
                    ]
                    for path in tesseract_paths:
                        if os.path.exists(path):
                            pytesseract.pytesseract.tesseract_cmd = path
                            break
                    pytesseract.get_tesseract_version()
                    tesseract_installed = True
                except Exception:
                    pass
                
                if not tesseract_installed:
                    error_msg = (
                        "No extractable text found in PDF. Note: Tesseract-OCR is not installed "
                        "on your system. Please install Tesseract-OCR on your computer to enable "
                        "OCR fallback for scanned/image-only documents."
                    )
                else:
                    error_msg = "No extractable text found in PDF, even after attempting OCR fallback."
                return [], page["_id"], "error", error_msg

            chunks = []
            for pdf_page in pdf_pages:
                page_chunks = semantic_chunking(
                    pdf_page["text"],
                    source_name=title,
                    url=url,
                    page_num=pdf_page["page"]
                )
                chunks.extend(page_chunks)
            return chunks, page["_id"], "indexed", None
            
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
        
        # Get all crawled pages for the project that are pending
        pending_pages = await crawled_pages_col().find({
            "project_id": project_id,
            "status": "pending"
        }).to_list(length=1000)
        
        if not pending_pages:
            print(f"[Ingestion] No pending pages to index for Project {project_id}")
            await projects_col().update_one(
                {"_id": project_id},
                {"$set": {"status": "active"}}
            )
            return

        print(f"[Ingestion] Found {len(pending_pages)} pages to extract/OCR...")
        
        # Process pages concurrently using a semaphore to limit CPU saturation (e.g. max 5 concurrent threads/tasks)
        semaphore = asyncio.Semaphore(5)
        
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
                
                if status == "indexed":
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
        results = await asyncio.gather(*tasks)
        
        for chunks in results:
            if chunks:
                all_chunks.extend(chunks)

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
        
        # Batch insert chunks to prevent MongoDB write timeouts on large crawls
        chunk_batch_size = 500
        for i in range(0, len(all_chunks), chunk_batch_size):
            await chunks_col().insert_many(all_chunks[i:i + chunk_batch_size])

        # Build BM25 index on the project chunks (uses raw text)
        build_bm25_index(all_chunks, project_id)

        print(f"[Ingestion] Total chunks to index: {len(all_chunks)}")
        
        # ── Contextual Retrieval: generate context blurbs for embedding ─────────
        if settings.contextual_enabled:
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
                payload={
                    "chunk_id": chunk["chunk_id"],
                    "project_id": project_id,
                    "source_name": chunk["source_name"],
                    "url": chunk["url"],
                    "page": chunk["page"],
                    "text": chunk["text"],
                    "source_type": chunk.get("source_type", "html"),
                    "department": chunk.get("department"),
                    "document_type": chunk.get("document_type"),
                    "embedding_id": chunk.get("embedding_id"),
                    "parent_id": chunk.get("parent_id"),
                    "parent_text": chunk.get("parent_text", "")[:8000],
                    "contextual_text": chunk.get("contextual_text", chunk["text"])[:2000]
                }
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
    
    try:
        raw_output = generate(context=merged_text[:12000], question=prompt)
        # Clean potential markdown backticks
        clean_json = re.sub(r"^```json\s*|```$", "", raw_output.strip(), flags=re.MULTILINE)
        data = json.loads(clean_json)
        
        entities = data.get("entities", [])
        relations = data.get("relations", [])
        
        print(f"[Neo4j Graph] Extracted {len(entities)} entities and {len(relations)} relationships.")
        
        # Write to Neo4j in a session
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
                    
        print(f"[Neo4j Graph] Successfully written graph for project: {project_id}")
    except Exception as graph_err:
        print(f"[Neo4j Graph] [WARNING] Failed to extract or write graph data: {graph_err}")

