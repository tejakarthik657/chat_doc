"""
ocr_space.py — Free Cloud OCR.space API Client with Circuit-Breaker.
"""
import io
import os
import time
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

OCR_SPACE_API_KEY = os.environ.get("OCR_SPACE_API_KEY", "helloworld")
OCR_SPACE_ENDPOINT = "https://api.ocr.space/parse/image"

_ocr_space_blocked_until = 0

def parse_image_ocr_space(image_bytes: bytes, filename: str = "page.png") -> Optional[str]:
    """
    Perform cloud OCR via OCR.space API with circuit-breaker protection on 429.
    """
    global _ocr_space_blocked_until

    # If circuit breaker active (rate limited), skip immediately without waiting
    if time.time() < _ocr_space_blocked_until:
        return None

    try:
        payload = {
            "apikey": OCR_SPACE_API_KEY,
            "language": "eng",
            "isOverlayRequired": False,
            "OCREngine": 2,
            "detectOrientation": True,
            "scale": True,
        }
        files = {
            "filename": (filename, io.BytesIO(image_bytes), "image/png")
        }

        response = requests.post(OCR_SPACE_ENDPOINT, data=payload, files=files, timeout=4)
        
        if response.status_code == 429:
            logger.warning("[OCR.space] Rate limit exceeded (429). Circuit-breaker activated for 1 hour.")
            _ocr_space_blocked_until = time.time() + 3600
            return None

        if response.status_code != 200:
            logger.warning(f"[OCR.space] HTTP {response.status_code}: {response.text[:200]}")
            return None

        result_json = response.json()
        if result_json.get("IsErroredOnProcessing", False):
            return None

        parsed_results = result_json.get("ParsedResults", [])
        if not parsed_results:
            return None

        extracted_text = parsed_results[0].get("ParsedText", "")
        return extracted_text.strip() if extracted_text else None

    except Exception:
        return None
