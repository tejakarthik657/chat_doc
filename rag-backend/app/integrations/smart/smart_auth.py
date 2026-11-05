"""
smart_auth.py — SMART-on-FHIR OAuth 2.0 Authenticator.

Handles backend-to-backend token exchange using asymmetric client assertions.
"""

import httpx
import logging
from typing import Dict, Any, Optional
from app.integrations.smart.jwt_assertion import generate_client_assertion
from app.integrations.smart.token_manager import token_manager

logger = logging.getLogger(__name__)


class SMARTAuthenticator:
    """Manages SMART-on-FHIR Backend Services authentication."""

    async def get_access_token(
        self,
        tenant_id: str,
        client_id: str,
        token_endpoint: Optional[str] = None,
        private_key_pem: Optional[str] = None,
        scopes: str = "system/Patient.read system/Observation.read",
    ) -> str:
        """
        Retrieves a valid bearer token for the specified hospital tenant.
        Uses cached token if available; otherwise performs client assertion exchange.
        """
        cached = token_manager.get_token(tenant_id)
        if cached:
            return cached

        if not token_endpoint or "example" in token_endpoint:
            # Staging/Dev/Sandbox mode: Generate deterministic scoped mock bearer token
            token = f"smart_bearer_{tenant_id}_{client_id[:8]}_session"
            token_manager.set_token(tenant_id, token, expires_in=900)
            return token

        # Production SMART Backend Services token exchange
        assertion = generate_client_assertion(
            client_id=client_id,
            token_url=token_endpoint,
            private_key_pem=private_key_pem,
        )

        data = {
            "grant_type": "client_credentials",
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "client_assertion": assertion,
            "scope": scopes,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(token_endpoint, data=data)
            if resp.status_code != 200:
                raise RuntimeError(
                    f"SMART-on-FHIR token negotiation failed for {tenant_id}: {resp.status_code} {resp.text}"
                )
            result = resp.json()
            access_token = result.get("access_token")
            expires_in = result.get("expires_in", 900)
            token_manager.set_token(tenant_id, access_token, expires_in=expires_in)
            return access_token


smart_authenticator = SMARTAuthenticator()
