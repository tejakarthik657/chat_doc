"""
terminology_service.py — Healthcare Terminology (LOINC, SNOMED, RxNorm) Service.

Translates clinical biomarker names and queries to standardized semantic codes.
"""

from typing import Dict, Any, Optional

LOINC_REGISTRY = {
    "1742-6": {
        "name": "ALT (Alanine aminotransferase)",
        "unit": "U/L",
        "uln": 56.0,  # Upper Limit of Normal
        "category": "hepatic",
    },
    "2160-0": {
        "name": "Serum Creatinine",
        "unit": "mg/dL",
        "uln": 1.3,
        "category": "renal",
    },
    "777-3": {
        "name": "Platelet Count",
        "unit": "/uL",
        "lln": 150000.0,  # Lower Limit of Normal
        "category": "hematology",
    },
}

SNOMED_REGISTRY = {
    "367336001": {
        "name": "Chemotherapy administration",
        "category": "oncology_intervention",
    }
}


class TerminologyService:
    """Provides clinical semantic lookups."""

    def get_loinc_info(self, code: str) -> Optional[Dict[str, Any]]:
        return LOINC_REGISTRY.get(code)

    def get_snomed_info(self, code: str) -> Optional[Dict[str, Any]]:
        return SNOMED_REGISTRY.get(code)


terminology_service = TerminologyService()
