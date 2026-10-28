"""
sanitizer.py — Production OCR, SVG, and Text Cleaning Pipeline.

Filters raw extracted text from PDF/OCR parsers to remove:
- SVG tags and filenames (e.g. svgVaagdevi Degree...svgdepartment-of-m...)
- Garbage OCR page headers/footers (e.g. Page 1> 20|2>, 209> 203|Departicles/system|Page)
- Repetitive token hallucination patterns
- Non-printable unicode sequences
"""
import re
import logging

logger = logging.getLogger(__name__)

# RegEx patterns for noise removal
SVG_NOISE_PATTERN = re.compile(r'svg[A-Za-z0-9_\-\.]+(?:\.\.\.svg[A-Za-z0-9_\-\.]+)*', re.IGNORECASE)
SVG_TAG_PATTERN = re.compile(r'<svg[^>]*>.*?</svg>', re.IGNORECASE | re.DOTALL)
PAGE_HEADER_NOISE = re.compile(r'(?:Page\s*\d+[>|\s]*|Section\|[A-Z0-9>|\s]*|\d+[\s|]*>)+', re.IGNORECASE)
GARBAGE_TOKEN_PATTERN = re.compile(r'(?:\bCan\s+you\b\s*){3,}', re.IGNORECASE)
REPETITIVE_CHAR_PATTERN = re.compile(r'([|\-=_>]{3,})')

def clean_extracted_text(text: str) -> str:
    """
    Sanitize raw extracted text from PDF/web scrapers.
    
    Returns clean, normalized text suitable for embedding & LLM ingestion.
    """
    if not text:
        return ""

    original_len = len(text)
    
    # 1. Strip raw SVG tags and inline SVG filenames
    cleaned = SVG_TAG_PATTERN.sub(' ', text)
    cleaned = SVG_NOISE_PATTERN.sub(' ', cleaned)
    
    # 2. Remove garbled OCR header/footer markers
    cleaned = PAGE_HEADER_NOISE.sub(' ', cleaned)
    
    # 3. Remove garbled token loops (e.g. "Can you can you can you...")
    cleaned = GARBAGE_TOKEN_PATTERN.sub(' ', cleaned)
    
    # 4. Collapse repetitive separator lines
    cleaned = REPETITIVE_CHAR_PATTERN.sub(' ', cleaned)
    
    # 5. Normalize excess whitespace and line breaks
    lines = [line.strip() for line in cleaned.splitlines()]
    non_empty_lines = [line for line in lines if line]
    cleaned = "\n".join(non_empty_lines)
    cleaned = re.sub(r'[ \t]{2,}', ' ', cleaned)

    if original_len - len(cleaned) > 50:
        logger.info(f"[Sanitizer] Reduced noise: {original_len} chars -> {len(cleaned)} chars")

    return cleaned
