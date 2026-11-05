"""
fhir_observation_service.py — Retrieval and Normalization of FHIR Observations.

Queries patient lab results and clinical observations from the authorized
hospital FHIR endpoint using verified FHIR resource references.
"""

import logging
from typing import Dict, Any, List, Optional
from app.integrations.fhir.fhir_client import fhir_client
from app.integrations.fhir.fhir_normalizer import fhir_normalizer
from app.integrations.smart.smart_auth import smart_authenticator

logger = logging.getLogger(__name__)

# Standard Clinical Trial Biomarker LOINC / SNOMED codes
PROTOCOL_LOINC_CODES = [
    "1742-6",     # ALT (Alanine aminotransferase)
    "2160-0",     # Serum Creatinine
    "777-3",      # Platelet count
    "367336001",  # Prior Chemotherapy (SNOMED)
]


class FHIRObservationService:
    """Service to fetch lab observations for a verified patient resource ID."""

    async def get_patient_panel(
        self,
        tenant_id: str,
        fhir_base_url: str,
        fhir_patient_id: str,
        client_id: str,
        token_endpoint: Optional[str] = None,
        codes: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves and normalizes observation bundle for verified patient.
        """
        token = await smart_authenticator.get_access_token(
            tenant_id=tenant_id,
            client_id=client_id,
            token_endpoint=token_endpoint,
        )

        query_codes = codes or PROTOCOL_LOINC_CODES

        bundle = await fhir_client.get_patient_observations(
            tenant_id=tenant_id,
            fhir_base_url=fhir_base_url,
            patient_id=fhir_patient_id,
            codes=query_codes,
            access_token=token,
        )

        return fhir_normalizer.normalize_observations(bundle)


fhir_observation_service = FHIRObservationService()
