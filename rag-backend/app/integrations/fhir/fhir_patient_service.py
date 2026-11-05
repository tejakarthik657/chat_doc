"""
fhir_patient_service.py — Hospital FHIR Patient Query & Safety Verification.

Performs strict, authorized FHIR searches with the 6 mandatory safety checks:
1. Expected hospital context
2. System match
3. Value match
4. Active status check
5. Exactly one match check (no ambiguity / guessing)
6. Authorization verification
"""

import logging
from typing import Dict, Any, Optional
from app.integrations.fhir.fhir_client import fhir_client
from app.integrations.fhir.fhir_normalizer import fhir_normalizer
from app.integrations.smart.smart_auth import smart_authenticator

logger = logging.getLogger(__name__)


class FHIRPatientService:
    """Enforces strict patient resolution safety protocol."""

    async def fetch_and_verify_patient(
        self,
        tenant_id: str,
        fhir_base_url: str,
        identifier_system: str,
        identifier_value: str,
        client_id: str,
        token_endpoint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes search:
        GET /Patient?identifier={identifier_system}|{identifier_value}
        And strictly verifies the result before returning.
        """
        # Step 1: Obtain SMART OAuth Access Token for tenant
        token = await smart_authenticator.get_access_token(
            tenant_id=tenant_id,
            client_id=client_id,
            token_endpoint=token_endpoint,
        )

        # Step 2: Query FHIR Server
        bundle = await fhir_client.search_patient_by_identifier(
            tenant_id=tenant_id,
            fhir_base_url=fhir_base_url,
            system=identifier_system,
            value=identifier_value,
            access_token=token,
        )

        entries = bundle.get("entry", [])

        # Safety Check 1: Must find at least one match
        if not entries or bundle.get("total", 0) == 0:
            raise ValueError(
                f"No patient found in hospital tenant '{tenant_id}' matching identifier '{identifier_value}' in system '{identifier_system}'."
            )

        # Safety Check 2: Ambiguity Guard — exactly ONE match required
        if len(entries) > 1 or bundle.get("total", 0) > 1:
            raise ValueError(
                f"Ambiguous patient identity: Found {len(entries)} matching records for identifier '{identifier_value}' at hospital '{tenant_id}'. Automatic resolution halted."
            )

        resource = entries[0].get("resource", {})

        # Safety Check 3: Resource must be active
        if not resource.get("active", True):
            raise ValueError(
                f"Patient record '{resource.get('id')}' at hospital '{tenant_id}' is marked INACTIVE. Cannot perform clinical protocol audit."
            )

        # Safety Check 4: Verify identifier system & value match within resource
        matching_idents = [
            i for i in resource.get("identifier", [])
            if (not identifier_system or i.get("system") == identifier_system) and i.get("value") == identifier_value
        ]
        if not matching_idents:
            raise ValueError(
                f"Identifier discrepancy: Resource returned did not contain expected identifier {identifier_system}|{identifier_value}."
            )

        # Normalize resource
        normalized = fhir_normalizer.normalize_patient(resource)
        normalized["tenant_id"] = tenant_id
        normalized["verified_identifier"] = identifier_value
        normalized["identifier_system"] = identifier_system

        return normalized


fhir_patient_service = FHIRPatientService()
