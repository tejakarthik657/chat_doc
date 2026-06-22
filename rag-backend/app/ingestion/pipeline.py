import os
import uuid
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


def extract_pages_with_ocr(file_path: str) -> list[dict]:
    """
    Extracts text from a PDF, page-by-page.
    If a page has less than 50 characters, it falls back to OCR via pytesseract.
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
        
        # Fallback to OCR if page has little text (scanned PDF detection) and tesseract is available
        if len(text) < 50 and tesseract_available:
            print(f"[OCR] [WARNING] Page {page_num} has very little text ({len(text)} chars). Trying OCR fallback...")
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
                print(f"[OCR] [WARNING] Fallback failed on page {page_num}: {ocr_err}")
                # Fall back to original minimal text
        
        # Reconstruct tables as Markdown if enabled
        if enable_table_extraction:
            table_md = extract_tables_as_markdown(page)
            if table_md:
                text = f"{text}{table_md}"
            
        if text:
            pages.append({"page": page_num, "text": text})
            
    doc.close()
    return pages


# ── Step 2: Semantic Chunking ──────────────────────────────────────────────────

def semantic_chunking(text: str, source_name: str, url: str, page_num: int = 1) -> list[dict]:
    """
    Splits text by paragraphs to keep logical structure (including tables and headers) intact.
    If a paragraph exceeds chunk_size, it splits it by sentence.
    """
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = []
    current_length = 0
    
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
            "text": c_text.strip()
        })
    return result


def chunk_pages(pages: list[dict], doc_id: str, filename: str) -> list[dict]:
    """
    Splits each page's text with overlap.
    Returns chunk dicts ready for MongoDB + FAISS.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ".", " ", ""]
    )

    chunks = []
    embedding_counter = 0

    for page_data in pages:
        splits = splitter.split_text(page_data["text"])
        for split in splits:
            if len(split.strip()) < 30:  # drop micro-chunks
                continue
            chunks.append({
                "chunk_id": str(uuid.uuid4()),
                "doc_id": doc_id,
                "filename": filename,
                "page": page_data["page"],
                "text": split.strip(),
                "embedding_id": embedding_counter,  # maps to FAISS row
            })
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

        # Step 1: Extract (attempt with OCR fallback)
        pages = extract_pages_with_ocr(file_path)
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

        # Step 5: Persist chunk metadata to MongoDB
        await chunks_col().insert_many(chunks)

        # Step 6: Mark document as ready
        size_mb = round(os.path.getsize(file_path) / (1024 * 1024), 2)
        await documents_col().update_one(
            {"_id": doc_id},
            {"$set": {
                "status": "ready",
                "page_count": page_count,
                "chunk_count": len(chunks),
                "size_mb": size_mb
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
            
            # extract_pages_with_ocr is blocking and CPU-bound, run it in a thread pool
            pdf_pages = await asyncio.to_thread(extract_pages_with_ocr, file_path)
            
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


async def process_project_crawled_data(project_id: str, user_id: str):
    """
    Processes all 'pending' pages for a project in parallel:
      1. Performs PDF OCR fallback or text extraction
      2. Performs Semantic Chunking
      3. Generates Embeddings
      4. Upserts vectors + payloads to Qdrant collection
    """
    import asyncio
    import time
    try:
        start_time = time.time()
        print(f"[Ingestion] Processing crawled data for Project {project_id}")
        
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

        print(f"[Ingestion] Total chunks to index: {len(all_chunks)}")
        
        # Generate Embeddings
        chunk_texts = [c["text"] for c in all_chunks]
        vectors = embed_texts(chunk_texts)
        vector_dim = vectors.shape[1]
        
        # Initialize Qdrant collection
        collection_name = f"project_{project_id}"
        init_collection(collection_name, vector_dim)
        
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
                    "text": chunk["text"]
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
        
        # Update Project Status to ready/active
        from datetime import datetime
        await projects_col().update_one(
            {"_id": project_id},
            {"$set": {
                "status": "active",
                "indexed_at": datetime.utcnow()
            }}
        )
        
        elapsed_time = time.time() - start_time
        print(
            f"""
            =========================================
            INGESTION METRICS: Project {project_id}
            -----------------------------------------
            Pages/PDFs processed: {len(pending_pages)}
            Chunks generated:     {len(all_chunks)}
            Embeddings created:   {len(points)}
            Time taken:           {elapsed_time:.2f} seconds
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

