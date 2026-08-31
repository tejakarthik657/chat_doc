"""
Extraction Quality Metrics
───────────────────────────
Tracks and reports extraction quality metrics for the RAG pipeline.
Used to monitor PDF quality, HTML extraction, OCR utilization, and
overall ingestion health.
"""
from datetime import datetime
from typing import Dict, Any
import os


class ExtractionMetrics:
    """Collects and reports extraction quality metrics."""

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.start_time = datetime.utcnow()
        self.stats = {
            "total_pages_processed": 0,
            "quality_passes": 0,        # Pages with high quality content
            "navigation_text": 0,       # Pages detected as navigation only
            "playwright_re_extractions": 0,  # Times Playwright was used for quality recovery
            "docling_success": 0,       # PDFs successfully extracted by Docling
            "ocr_fallbacks": 0,         # PDFs requiring OCR fallback
            "ocr_failures": 0,          # PDFs where OCR also failed
            "tables_extracted": 0,      # Tables found and extracted
            "chunks_created": 0,        # Total chunks generated
            "micro_chunks_dropped": 0,  # Chunks dropped due to size
            "metadata_enriched": 0,     # Chunks with metadata
        }
        self.quality_issues: list[Dict[str, Any]] = []

    def record_page_processed(self):
        self.stats["total_pages_processed"] += 1

    def record_quality_pass(self):
        self.stats["quality_passes"] += 1

    def record_navigation_text(self, url: str):
        self.stats["navigation_text"] += 1
        self.quality_issues.append({
            "type": "navigation_text",
            "url": url,
            "timestamp": datetime.utcnow().isoformat()
        })

    def record_playwright_re_extraction(self, url: str, improved: bool, before_chars: int, after_chars: int):
        self.stats["playwright_re_extractions"] += 1
        if improved:
            self.quality_issues.append({
                "type": "playwright_recovery",
                "url": url,
                "before_chars": before_chars,
                "after_chars": after_chars,
                "timestamp": datetime.utcnow().isoformat()
            })

    def record_docling_success(self, pages: int):
        self.stats["docling_success"] += 1
        self.stats["pages_extracted"] = self.stats.get("pages_extracted", 0) + pages

    def record_ocr_fallback(self):
        self.stats["ocr_fallbacks"] += 1

    def record_ocr_failure(self):
        self.stats["ocr_failures"] += 1

    def record_table_extracted(self, count: int):
        self.stats["tables_extracted"] += count

    def record_chunks_created(self, chunks: list):
        self.stats["chunks_created"] += len(chunks)
        for c in chunks:
            if len(c.get("text", "")) < 30:
                self.stats["micro_chunks_dropped"] += 1
            else:
                self.stats["metadata_enriched"] += 1

    def get_quality_score(self) -> float:
        total = self.stats["total_pages_processed"]
        if total == 0:
            return 0.0
        return round((self.stats["quality_passes"] / total) * 100, 2)

    def get_summary(self) -> Dict[str, Any]:
        elapsed = (datetime.utcnow() - self.start_time).total_seconds()
        return {
            "project_id": self.project_id,
            "elapsed_seconds": round(elapsed, 2),
            "quality_score": f"{self.get_quality_score()}%",
            "stats": self.stats,
            "quality_issues_count": len(self.quality_issues),
            "quality_issues": self.quality_issues[:10],  # Top 10 issues
        }

    def log_summary(self):
        """Print a formatted summary of extraction quality metrics."""
        summary = self.get_summary()
        print(
            f"""
            =========================================
            EXTRACTION QUALITY METRICS
            -----------------------------------------
            Project:       {summary['project_id']}
            Time:          {summary['elapsed_seconds']}s
            Quality Score: {summary['quality_score']}
            -----------------------------------------
            Pages Processed:    {self.stats['total_pages_processed']}
            Content Quality:    {self.stats['quality_passes']}
            Navigation Only:    {self.stats['navigation_text']}
            Playwright Re-ex:   {self.stats['playwright_re_extractions']}
            Docling OK:         {self.stats['docling_success']}
            OCR Fallbacks:      {self.stats['ocr_fallbacks']}
            OCR Failures:       {self.stats['ocr_failures']}
            Tables Extracted:   {self.stats['tables_extracted']}
            Chunks Created:     {self.stats['chunks_created']}
            Metadata Enriched:  {self.stats['metadata_enriched']}
            Quality Issues:     {len(self.quality_issues)}
            =========================================
            """
        )
