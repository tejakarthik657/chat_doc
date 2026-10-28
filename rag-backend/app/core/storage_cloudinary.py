"""
Cloudinary Media Storage Integration.
Handles persistent, lifetime-free cloud hosting for user-uploaded PDF documents.
Ensures zero binary blobs are stored in MongoDB Atlas, preserving the 512MB free tier forever.
"""
import os
import logging
from typing import Optional, Dict, Any, Union
import cloudinary
import cloudinary.uploader
import cloudinary.api
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

from urllib.parse import urlparse

_configured = False


def init_cloudinary():
    global _configured
    if not _configured and settings.cloudinary_url:
        try:
            parsed = urlparse(settings.cloudinary_url)
            cloud_name = parsed.hostname
            api_key = parsed.username
            api_secret = parsed.password
            cloudinary.config(
                cloud_name=cloud_name,
                api_key=api_key,
                api_secret=api_secret,
                secure=True
            )
            _configured = True
            logger.info(f"[Cloudinary] Configured media storage for cloud: {cloud_name}")
        except Exception as e:
            logger.error(f"[Cloudinary] Configuration failed: {e}")


def upload_pdf_to_cloudinary(file_path_or_bytes: Union[str, bytes], public_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Upload a PDF document to Cloudinary (resource_type='raw').
    Returns dict with 'secure_url', 'public_id', 'bytes', or None on failure.
    """
    init_cloudinary()
    if not _configured:
        logger.warning("[Cloudinary] Not configured. Using local disk fallback.")
        return None

    try:
        options = {
            "resource_type": "raw",
            "folder": "nexus_documents",
            "overwrite": True
        }
        if public_id:
            options["public_id"] = public_id

        result = cloudinary.uploader.upload(file_path_or_bytes, **options)
        secure_url = result.get("secure_url") or result.get("url")
        logger.info(f"[Cloudinary] Successfully uploaded document: {secure_url}")
        return {
            "secure_url": secure_url,
            "public_id": result.get("public_id"),
            "bytes": result.get("bytes", 0)
        }
    except Exception as upload_err:
        logger.error(f"[Cloudinary Upload Error] {upload_err}", exc_info=True)
        return None
