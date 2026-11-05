"""
fhir_client.py — HL7 FHIR v4 Async REST Client.

Speaks standard HL7 FHIR v4 endpoints over HTTPS with OAuth Bearer tokens.
Includes sandbox simulation for registered hospitals (Apollo, Yashoda, KIMS)
to support self-contained local testing and air-gapped clinical audits.
"""

import logging
import httpx
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# ── Realistic FHIR v4 Sandbox Datastore ──────────────────────────────────────
# Models Apollo, Yashoda, and KIMS with identical local MRN/Patient-IDs (104)
# proving identity namespace isolation.
FHIR_SANDBOX_PATIENTS = {
    "apollo-001": {
        "patient-783": {
            "resourceType": "Patient",
            "id": "patient-783",
            "active": True,
            "name": [{"use": "official", "family": "Vance", "given": ["Eleanor"]}],
            "gender": "female",
            "birthDate": "1968-06-12",
            "identifier": [
                {"system": "https://apollo.example/mrn", "value": "AP-104"},
                {"system": "https://apollo.example/internal", "value": "104"},
            ],
            "telecom": [{"system": "phone", "value": "919876500104"}],
        },
        "patient-290": {
            "resourceType": "Patient",
            "id": "patient-290",
            "active": True,
            "name": [{"use": "official", "family": "Kumar", "given": ["Rahul"]}],
            "gender": "male",
            "birthDate": "1998-04-15",
            "identifier": [
                {"system": "https://apollo.example/mrn", "value": "AP-290"},
            ],
            "telecom": [{"system": "phone", "value": "919876543210"}],
        },
    },
    "yashoda-001": {
        "patient-921": {
            "resourceType": "Patient",
            "id": "patient-921",
            "active": True,
            "name": [{"use": "official", "family": "Chandra", "given": ["Ramesh"]}],
            "gender": "male",
            "birthDate": "1984-11-20",
            "identifier": [
                {"system": "https://yashoda.example/mrn", "value": "YS-104"},
                {"system": "https://yashoda.example/internal", "value": "104"},
            ],
            "telecom": [{"system": "phone", "value": "919876500921"}],
        },
        "patient-920": {
            "resourceType": "Patient",
            "id": "patient-920",
            "active": True,
            "name": [{"use": "official", "family": "K", "given": ["Rahul"]}],
            "gender": "male",
            "birthDate": "1998-04-15",
            "identifier": [
                {"system": "https://yashoda.example/mrn", "value": "YS-290"},
            ],
            "telecom": [{"system": "phone", "value": "919876543210"}],
        },
    },
    "kims-001": {
        "patient-456": {
            "resourceType": "Patient",
            "id": "patient-456",
            "active": True,
            "name": [{"use": "official", "family": "Rao", "given": ["Sunita"]}],
            "gender": "female",
            "birthDate": "1963-02-14",
            "identifier": [
                {"system": "https://kims.example/mrn", "value": "KM-104"},
                {"system": "https://kims.example/internal", "value": "104"},
            ],
            "telecom": [{"system": "phone", "value": "919876500456"}],
        },
        "patient-711": {
            "resourceType": "Patient",
            "id": "patient-711",
            "active": True,
            "name": [{"use": "official", "family": "Kumar", "given": ["Rahul"]}],
            "gender": "male",
            "birthDate": "1998-04-15",
            "identifier": [
                {"system": "https://kims.example/mrn", "value": "KM-711"},
            ],
            "telecom": [{"system": "phone", "value": "919876543210"}],
        },
    },
}

FHIR_SANDBOX_OBSERVATIONS = {
    # Apollo Patient AP-104 (Violates protocol: ALT 142.0 > 2.5x ULN, Creatinine 2.4 > 1.5, Chemo 12d < 28d)
    "patient-783": [
        {
            "resourceType": "Observation",
            "id": "obs-783-alt",
            "status": "final",
            "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "laboratory"}]}],
            "code": {
                "coding": [{"system": "http://loinc.org", "code": "1742-6", "display": "Alanine aminotransferase [Enzymatic activity/volume] in Serum or Plasma"}],
                "text": "ALT Liver Enzyme",
            },
            "subject": {"reference": "Patient/patient-783"},
            "effectiveDateTime": "2026-10-24T09:30:00Z",
            "valueQuantity": {"value": 142.0, "unit": "U/L", "system": "http://unitsofmeasure.org", "code": "U/L"},
            "referenceRange": [{"low": {"value": 7.0, "unit": "U/L"}, "high": {"value": 56.0, "unit": "U/L"}}],
        },
        {
            "resourceType": "Observation",
            "id": "obs-783-cr",
            "status": "final",
            "code": {
                "coding": [{"system": "http://loinc.org", "code": "2160-0", "display": "Creatinine [Mass/volume] in Serum or Plasma"}],
                "text": "Serum Creatinine",
            },
            "subject": {"reference": "Patient/patient-783"},
            "effectiveDateTime": "2026-10-24T09:30:00Z",
            "valueQuantity": {"value": 2.4, "unit": "mg/dL", "system": "http://unitsofmeasure.org", "code": "mg/dL"},
            "referenceRange": [{"low": {"value": 0.7, "unit": "mg/dL"}, "high": {"value": 1.3, "unit": "mg/dL"}}],
        },
        {
            "resourceType": "Observation",
            "id": "obs-783-plt",
            "status": "final",
            "code": {
                "coding": [{"system": "http://loinc.org", "code": "777-3", "display": "Platelets [#/volume] in Blood by Automated count"}],
                "text": "Platelet Count",
            },
            "subject": {"reference": "Patient/patient-783"},
            "effectiveDateTime": "2026-10-24T09:30:00Z",
            "valueQuantity": {"value": 85000, "unit": "/uL", "system": "http://unitsofmeasure.org", "code": "/uL"},
            "referenceRange": [{"low": {"value": 150000, "unit": "/uL"}, "high": {"value": 450000, "unit": "/uL"}}],
        },
        {
            "resourceType": "Observation",
            "id": "obs-783-chemo",
            "status": "final",
            "code": {
                "coding": [{"system": "http://snomed.info/sct", "code": "367336001", "display": "Chemotherapy administration"}],
                "text": "Prior Chemotherapy Washout",
            },
            "subject": {"reference": "Patient/patient-783"},
            "effectiveDateTime": "2026-10-12T10:00:00Z",
            "valueQuantity": {"value": 12, "unit": "days", "code": "d"},
            "note": [{"text": "Patient received cytotoxic infusion 12 days ago. Washout incomplete."}],
        },
    ],
    # Yashoda Patient YS-104 (Fully Eligible: ALT 24.0, Creatinine 0.9, Platelets 220,000, Prior chemo 90d)
    "patient-921": [
        {
            "resourceType": "Observation",
            "id": "obs-921-alt",
            "status": "final",
            "code": {
                "coding": [{"system": "http://loinc.org", "code": "1742-6", "display": "Alanine aminotransferase"}],
                "text": "ALT Liver Enzyme",
            },
            "subject": {"reference": "Patient/patient-921"},
            "effectiveDateTime": "2026-10-28T08:15:00Z",
            "valueQuantity": {"value": 24.0, "unit": "U/L", "code": "U/L"},
            "referenceRange": [{"low": {"value": 7.0, "unit": "U/L"}, "high": {"value": 56.0, "unit": "U/L"}}],
        },
        {
            "resourceType": "Observation",
            "id": "obs-921-cr",
            "status": "final",
            "code": {
                "coding": [{"system": "http://loinc.org", "code": "2160-0", "display": "Serum Creatinine"}],
                "text": "Serum Creatinine",
            },
            "subject": {"reference": "Patient/patient-921"},
            "effectiveDateTime": "2026-10-28T08:15:00Z",
            "valueQuantity": {"value": 0.9, "unit": "mg/dL", "code": "mg/dL"},
            "referenceRange": [{"low": {"value": 0.7, "unit": "mg/dL"}, "high": {"value": 1.3, "unit": "mg/dL"}}],
        },
        {
            "resourceType": "Observation",
            "id": "obs-921-plt",
            "status": "final",
            "code": {
                "coding": [{"system": "http://loinc.org", "code": "777-3", "display": "Platelet Count"}],
                "text": "Platelet Count",
            },
            "subject": {"reference": "Patient/patient-921"},
            "effectiveDateTime": "2026-10-28T08:15:00Z",
            "valueQuantity": {"value": 220000, "unit": "/uL", "code": "/uL"},
            "referenceRange": [{"low": {"value": 150000, "unit": "/uL"}, "high": {"value": 450000, "unit": "/uL"}}],
        },
        {
            "resourceType": "Observation",
            "id": "obs-921-chemo",
            "status": "final",
            "code": {
                "coding": [{"system": "http://snomed.info/sct", "code": "367336001", "display": "Chemotherapy administration"}],
                "text": "Prior Chemotherapy Washout",
            },
            "subject": {"reference": "Patient/patient-921"},
            "effectiveDateTime": "2026-07-20T10:00:00Z",
            "valueQuantity": {"value": 90, "unit": "days", "code": "d"},
            "note": [{"text": "Washout period satisfied (>28 days)."}],
        },
    ],
    # KIMS Patient KM-104
    "patient-456": [
        {
            "resourceType": "Observation",
            "id": "obs-456-alt",
            "status": "final",
            "code": {
                "coding": [{"system": "http://loinc.org", "code": "1742-6"}],
                "text": "ALT Liver Enzyme",
            },
            "subject": {"reference": "Patient/patient-456"},
            "effectiveDateTime": "2026-10-22T11:00:00Z",
            "valueQuantity": {"value": 35.0, "unit": "U/L", "code": "U/L"},
        },
        {
            "resourceType": "Observation",
            "id": "obs-456-cr",
            "status": "final",
            "code": {
                "coding": [{"system": "http://loinc.org", "code": "2160-0"}],
                "text": "Serum Creatinine",
            },
            "subject": {"reference": "Patient/patient-456"},
            "effectiveDateTime": "2026-10-22T11:00:00Z",
            "valueQuantity": {"value": 1.2, "unit": "mg/dL", "code": "mg/dL"},
        },
    ],
}


class FHIRClient:
    """Async HL7 FHIR v4 REST API Client with multi-tenant routing."""

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    def _is_sandbox_url(self, base_url: str) -> bool:
        return "example" in base_url or "localhost" in base_url or not base_url

    async def search_patient_by_identifier(
        self,
        tenant_id: str,
        fhir_base_url: str,
        system: str,
        value: str,
        access_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes:
        GET {fhir_base_url}/Patient?identifier={system}|{value}
        """
        if self._is_sandbox_url(fhir_base_url):
            return self._sandbox_search_patient(tenant_id, system, value)

        headers = {"Accept": "application/fhir+json"}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"

        url = f"{fhir_base_url.rstrip('/')}/Patient"
        params = {"identifier": f"{system}|{value}"}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code != 200:
                raise RuntimeError(f"FHIR server error ({resp.status_code}): {resp.text}")
            return resp.json()

    async def get_patient_observations(
        self,
        tenant_id: str,
        fhir_base_url: str,
        patient_id: str,
        codes: Optional[List[str]] = None,
        access_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes:
        GET {fhir_base_url}/Observation?patient={patient_id}&code={codes}
        """
        if self._is_sandbox_url(fhir_base_url):
            return self._sandbox_get_observations(patient_id, codes)

        headers = {"Accept": "application/fhir+json"}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"

        url = f"{fhir_base_url.rstrip('/')}/Observation"
        params = {"patient": patient_id}
        if codes:
            params["code"] = ",".join(codes)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code != 200:
                raise RuntimeError(f"FHIR Observation query failed: {resp.status_code}")
            return resp.json()

    # ── Sandbox Handlers ───────────────────────────────────────────────────────

    def _sandbox_search_patient(self, tenant_id: str, system: str, value: str) -> Dict[str, Any]:
        hospital_store = FHIR_SANDBOX_PATIENTS.get(tenant_id, {})
        matches = []

        for p_id, resource in hospital_store.items():
            for ident in resource.get("identifier", []):
                # Match system & value (or fallback system if system is empty)
                if (not system or ident.get("system") == system) and ident.get("value") == value:
                    matches.append({"resource": resource})
                    break

        return {
            "resourceType": "Bundle",
            "type": "searchset",
            "total": len(matches),
            "entry": matches,
        }

    def _sandbox_get_observations(self, patient_id: str, codes: Optional[List[str]] = None) -> Dict[str, Any]:
        obs_list = FHIR_SANDBOX_OBSERVATIONS.get(patient_id, [])
        filtered = []

        for obs in obs_list:
            if not codes:
                filtered.append({"resource": obs})
                continue
            
            # Check if any observation coding matches requested codes
            obs_codings = [c.get("code") for c in obs.get("code", {}).get("coding", [])]
            if any(c in codes for c in obs_codings):
                filtered.append({"resource": obs})

        return {
            "resourceType": "Bundle",
            "type": "searchset",
            "total": len(filtered),
            "entry": filtered,
        }


fhir_client = FHIRClient()
