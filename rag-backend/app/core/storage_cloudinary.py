"""
Cloudinary Media Storage Integration.
Handles persistent, lifetime-free cloud hosting for user-uploaded PDF documents.
Ensures zero binary blobs are stored in MongoDB Atlas, preserving the 512MB free tier forever.
"""
import os
import logging
from typing import Optional, Dict, Any, Union
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

from urllib.parse import urlparse

_configured = False
_cloudinary = None


def init_cloudinary():
    global _configured, _cloudinary
    if not _configured and settings.cloudinary_url:
        try:
            import cloudinary
            import cloudinary.uploader
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
            _cloudinary = cloudinary
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
    if not _configured or _cloudinary is None:
        logger.warning("[Cloudinary] Not configured. Durable document storage is unavailable.")
        return None

    try:
        options = {
            "resource_type": "raw",
            "folder": "nexus_documents",
            "overwrite": True,
            "type": "private",
        }
        if public_id:
            options["public_id"] = public_id

        result = _cloudinary.uploader.upload(file_path_or_bytes, **options)
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


def delete_pdf_from_cloudinary(public_id: str) -> bool:
    """Delete a raw PDF from Cloudinary after its document is removed."""
    init_cloudinary()
    if not _configured or _cloudinary is None or not public_id:
        return False

    try:
        result = _cloudinary.uploader.destroy(public_id, resource_type="raw")
        return result.get("result") in {"ok", "not found"}
    except Exception as delete_err:
        logger.error(f"[Cloudinary Delete Error] {delete_err}", exc_info=True)
        return False


def get_pdf_download_url(public_id: str) -> Optional[str]:
    """Create a signed URL for downloading a raw PDF from Cloudinary."""
    init_cloudinary()
    if not _configured or _cloudinary is None or not public_id:
        return None

    try:
        from cloudinary.utils import cloudinary_url

        url, _ = cloudinary_url(
            public_id,
            resource_type="raw",
            type="private",
            format="pdf",
            secure=True,
            sign_url=True,
        )
        if not url:
            logger.error("[Cloudinary URL Error] SDK returned an empty signed URL")
            return None
        return url
    except Exception as download_err:
        logger.error(f"[Cloudinary URL Error] {download_err}", exc_info=True)
        return None
