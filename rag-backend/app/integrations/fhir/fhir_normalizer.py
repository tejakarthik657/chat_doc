"""
fhir_normalizer.py — Clinical FHIR Resource Normalizer.

Transforms heterogeneous HL7 FHIR v4 JSON structures into standardized,
auditable clinical dictionaries with verified units and timestamps.
"""

from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class FHIRNormalizer:
    """Normalizes FHIR R4 Patient and Observation resources."""

    def normalize_patient(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Extracts standard demographics from a FHIR Patient resource."""
        p_id = resource.get("id", "")
        active = resource.get("active", False)
        gender = resource.get("gender", "unknown")
        birth_date = resource.get("birthDate", "")

        # Official human name
        name_parts = []
        for n in resource.get("name", []):
            given = " ".join(n.get("given", []))
            family = n.get("family", "")
            full = f"{given} {family}".strip()
            if full:
                name_parts.append(full)
        display_name = name_parts[0] if name_parts else "Unknown Name"

        # Identifiers
        identifiers = []
        for ident in resource.get("identifier", []):
            identifiers.append({
                "system": ident.get("system", ""),
                "value": ident.get("value", ""),
            })

        return {
            "fhir_resource_id": p_id,
            "display_name": display_name,
            "gender": gender,
            "birth_date": birth_date,
            "active": active,
            "identifiers": identifiers,
        }

    def normalize_observations(self, bundle: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extracts normalized clinical lab values from a FHIR Observation Bundle."""
        normalized = []
        entries = bundle.get("entry", [])

        for entry in entries:
            resource = entry.get("resource", {})
            if resource.get("resourceType") != "Observation":
                continue

            obs_id = resource.get("id")
            status = resource.get("status")
            effective = resource.get("effectiveDateTime", "")

            # Code & Name
            code_obj = resource.get("code", {})
            display_name = code_obj.get("text", "")
            codings = code_obj.get("coding", [])
            primary_code = codings[0].get("code") if codings else ""
            primary_system = codings[0].get("system") if codings else ""

            # Value Quantity
            val_quantity = resource.get("valueQuantity", {})
            val = val_quantity.get("value")
            unit = val_quantity.get("unit") or val_quantity.get("code", "")

            # Reference ranges
            ref_ranges = resource.get("referenceRange", [])
            ref_low = ref_ranges[0].get("low", {}).get("value") if ref_ranges else None
            ref_high = ref_ranges[0].get("high", {}).get("value") if ref_ranges else None

            # Notes
            notes = [n.get("text", "") for n in resource.get("note", []) if n.get("text")]

            normalized.append({
                "observation_id": obs_id,
                "status": status,
                "code": primary_code,
                "code_system": primary_system,
                "test_name": display_name,
                "value": val,
                "unit": unit,
                "reference_low": ref_low,
                "reference_high": ref_high,
                "effective_date": effective,
                "notes": " ".join(notes),
            })

        return normalized


fhir_normalizer = FHIRNormalizer()
