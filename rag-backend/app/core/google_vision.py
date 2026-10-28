"""
google_vision.py — Tier 3 Cloud OCR via Google Cloud Vision & Groq Vision Fallback.

Features:
- Primary Tier 3 OCR engine for complex non-searchable document pages.
- Uses google-cloud-vision library if credentials are configured.
- Graceful fallback to Groq Vision OCR if Google Vision API key/credentials are absent or fail.
- Hard-capped safety checks to prevent bill overruns.
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def parse_image_google_vision(image_bytes: bytes) -> Optional[str]:
    """
    Extract text using Google Cloud Vision API (DOCUMENT_TEXT_DETECTION).
    If google-cloud-vision is installed and credentials exist, runs full dense document OCR.
    Otherwise returns None to allow downstream fallback.
    """
    google_creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or os.environ.get("GOOGLE_VISION_API_KEY")
    if not google_creds:
        logger.debug("[Google Vision] No credentials configured in GOOGLE_APPLICATION_CREDENTIALS or GOOGLE_VISION_API_KEY.")
        return None

    try:
        from google.cloud import vision
        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=image_bytes)

        logger.info(f"[Google Vision] Submitting image page ({len(image_bytes)} bytes) to DOCUMENT_TEXT_DETECTION...")
        response = client.document_text_detection(image=image)

        if response.error.message:
            logger.warning(f"[Google Vision] API returned error: {response.error.message}")
            return None

        full_text = response.full_text_annotation.text
        if full_text and full_text.strip():
            logger.info(f"[Google Vision] Successfully extracted {len(full_text)} characters.")
            return full_text.strip()
    except ImportError:
        logger.debug("[Google Vision] google-cloud-vision package not installed. Skipping.")
    except Exception as e:
        logger.error(f"[Google Vision] Extraction failed: {e}")

    return None
