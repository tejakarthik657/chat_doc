"""
token_manager.py — In-Memory & Redis Token Cache for SMART-on-FHIR.

Manages short-lived bearer tokens (typically 15-minute TTL) per hospital tenant,
preventing redundant OAuth handshakes on every clinical chat query.
"""

import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class TokenManager:
    """Caches and rotates hospital-specific FHIR access tokens."""

    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}

    def get_token(self, tenant_id: str) -> Optional[str]:
        """Returns valid unexpired token for tenant, or None if expired/missing."""
        entry = self._cache.get(tenant_id)
        if not entry:
            return None

        # Expire 60s ahead of time to account for network skew
        if time.time() >= (entry["expires_at"] - 60):
            logger.info(f"[TokenManager] Cached token for tenant {tenant_id} has expired.")
            self._cache.pop(tenant_id, None)
            return None

        return entry["access_token"]

    def set_token(self, tenant_id: str, access_token: str, expires_in: int = 900):
        """Stores token with calculated expiry timestamp."""
        self._cache[tenant_id] = {
            "access_token": access_token,
            "expires_at": time.time() + expires_in,
            "created_at": time.time(),
        }
        logger.info(f"[TokenManager] Cached fresh SMART token for tenant {tenant_id} (valid {expires_in}s).")

    def invalidate(self, tenant_id: str):
        """Explicitly evict tenant's cached token upon 401 Unauthorized response."""
        self._cache.pop(tenant_id, None)


token_manager = TokenManager()
