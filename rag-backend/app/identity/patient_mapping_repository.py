"""
patient_mapping_repository.py — Patient Identity & Clinical Trial Subject Mapping Repository.

Stores explicit, verified bindings between VeriDoc Internal IDs, Hospital MRNs,
FHIR Patient Resource IDs, and Clinical Trial Subject IDs.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Built-in verified seed mappings for Apollo, Yashoda, and KIMS
SEED_PATIENT_MAPPINGS = [
    {
        "id": "map-apollo-104",
        "veridoc_patient_id": "VD-P-00104",
        "tenant_id": "apollo-001",
        "identifier_system": "https://apollo.example/mrn",
        "identifier_value": "AP-104",
        "fhir_resource_type": "Patient",
        "fhir_resource_id": "patient-783",
        "mapping_status": "verified",
        "verification_method": "authoritative_identifier",
    },
    {
        "id": "map-apollo-290",
        "veridoc_patient_id": "VD-P-00290",
        "tenant_id": "apollo-001",
        "identifier_system": "https://apollo.example/mrn",
        "identifier_value": "AP-290",
        "fhir_resource_type": "Patient",
        "fhir_resource_id": "patient-290",
        "mapping_status": "verified",
        "verification_method": "authoritative_identifier",
    },
    {
        "id": "map-yashoda-104",
        "veridoc_patient_id": "VD-P-00921",
        "tenant_id": "yashoda-001",
        "identifier_system": "https://yashoda.example/mrn",
        "identifier_value": "YS-104",
        "fhir_resource_type": "Patient",
        "fhir_resource_id": "patient-921",
        "mapping_status": "verified",
        "verification_method": "authoritative_identifier",
    },
    {
        "id": "map-yashoda-290",
        "veridoc_patient_id": "VD-P-00920",
        "tenant_id": "yashoda-001",
        "identifier_system": "https://yashoda.example/mrn",
        "identifier_value": "YS-290",
        "fhir_resource_type": "Patient",
        "fhir_resource_id": "patient-920",
        "mapping_status": "verified",
        "verification_method": "authoritative_identifier",
    },
    {
        "id": "map-kims-104",
        "veridoc_patient_id": "VD-P-00456",
        "tenant_id": "kims-001",
        "identifier_system": "https://kims.example/mrn",
        "identifier_value": "KM-104",
        "fhir_resource_type": "Patient",
        "fhir_resource_id": "patient-456",
        "mapping_status": "verified",
        "verification_method": "authoritative_identifier",
    },
]

SEED_SUBJECT_MAPPINGS = [
    {
        "id": "subject-map-apollo-104",
        "tenant_id": "apollo-001",
        "trial_id": "NB-204",
        "site_id": "site-apollo-01",
        "subject_id": "NB204-AP-0042",
        "veridoc_patient_id": "VD-P-00104",
        "mapping_status": "verified",
    },
    {
        "id": "subject-map-yashoda-104",
        "tenant_id": "yashoda-001",
        "trial_id": "NB-204",
        "site_id": "site-yashoda-sec",
        "subject_id": "NB204-YS-0018",
        "veridoc_patient_id": "VD-P-00921",
        "mapping_status": "verified",
    },
]


class PatientMappingRepository:
    """Repository managing patient identity and trial subject mappings."""

    def __init__(self):
        self._memory_patient_mappings: List[Dict[str, Any]] = [dict(m) for m in SEED_PATIENT_MAPPINGS]
        self._memory_subject_mappings: List[Dict[str, Any]] = [dict(s) for s in SEED_SUBJECT_MAPPINGS]

    async def get_by_hospital_mrn(
        self,
        tenant_id: str,
        identifier_system: str,
        identifier_value: str,
    ) -> Optional[Dict[str, Any]]:
        """Look up verified mapping by tenant + identifier system + MRN value."""
        try:
            from app.db.mongodb import patient_identity_mappings_col
            query = {
                "tenant_id": tenant_id,
                "identifier_value": identifier_value,
            }
            if identifier_system:
                query["identifier_system"] = identifier_system
            doc = await patient_identity_mappings_col().find_one(query)
            if doc:
                doc["id"] = str(doc.pop("_id"))
                return doc
        except Exception:
            pass

        for m in self._memory_patient_mappings:
            if m["tenant_id"] == tenant_id and m["identifier_value"] == identifier_value:
                if not identifier_system or m["identifier_system"] == identifier_system:
                    return m
        return None

    async def get_by_veridoc_id(self, veridoc_patient_id: str) -> Optional[Dict[str, Any]]:
        """Look up mapping by VeriDoc internal patient ID."""
        try:
            from app.db.mongodb import patient_identity_mappings_col
            doc = await patient_identity_mappings_col().find_one({"veridoc_patient_id": veridoc_patient_id})
            if doc:
                doc["id"] = str(doc.pop("_id"))
                return doc
        except Exception:
            pass

        for m in self._memory_patient_mappings:
            if m["veridoc_patient_id"] == veridoc_patient_id:
                return m
        return None

    async def get_by_fhir_resource(
        self,
        tenant_id: str,
        fhir_resource_id: str,
        resource_type: str = "Patient",
    ) -> Optional[Dict[str, Any]]:
        """Look up mapping by tenant and FHIR resource reference."""
        try:
            from app.db.mongodb import patient_identity_mappings_col
            doc = await patient_identity_mappings_col().find_one({
                "tenant_id": tenant_id,
                "fhir_resource_id": fhir_resource_id,
                "fhir_resource_type": resource_type,
            })
            if doc:
                doc["id"] = str(doc.pop("_id"))
                return doc
        except Exception:
            pass

        for m in self._memory_patient_mappings:
            if (
                m["tenant_id"] == tenant_id
                and m["fhir_resource_id"] == fhir_resource_id
                and m.get("fhir_resource_type", "Patient") == resource_type
            ):
                return m
        return None

    async def get_by_trial_subject(
        self,
        tenant_id: str,
        subject_id: str,
        trial_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Look up mapping by clinical trial subject ID."""
        try:
            from app.db.mongodb import clinical_trial_subject_mappings_col
            query = {"tenant_id": tenant_id, "subject_id": subject_id}
            if trial_id:
                query["trial_id"] = trial_id
            doc = await clinical_trial_subject_mappings_col().find_one(query)
            if doc:
                doc["id"] = str(doc.pop("_id"))
                return doc
        except Exception:
            pass

        for s in self._memory_subject_mappings:
            if s["tenant_id"] == tenant_id and s["subject_id"] == subject_id:
                if not trial_id or s["trial_id"] == trial_id:
                    return s
        return None

    async def register_patient_mapping(
        self,
        veridoc_patient_id: str,
        tenant_id: str,
        identifier_system: str,
        identifier_value: str,
        fhir_resource_id: str,
        fhir_resource_type: str = "Patient",
        mapping_status: str = "verified",
        verification_method: str = "authoritative_identifier",
    ) -> Dict[str, Any]:
        """Save a new patient identity mapping."""
        record = {
            "id": f"map-{tenant_id}-{identifier_value}",
            "veridoc_patient_id": veridoc_patient_id,
            "tenant_id": tenant_id,
            "identifier_system": identifier_system,
            "identifier_value": identifier_value,
            "fhir_resource_type": fhir_resource_type,
            "fhir_resource_id": fhir_resource_id,
            "mapping_status": mapping_status,
            "verification_method": verification_method,
            "created_at": datetime.utcnow(),
        }
        self._memory_patient_mappings.append(record)
        try:
            from app.db.mongodb import patient_identity_mappings_col
            doc = dict(record)
            doc["_id"] = doc.pop("id")
            await patient_identity_mappings_col().update_one(
                {
                    "tenant_id": tenant_id,
                    "identifier_system": identifier_system,
                    "identifier_value": identifier_value,
                },
                {"$set": doc},
                upsert=True,
            )
        except Exception as e:
            logger.warning(f"Could not persist patient mapping: {e}")
        return record

    async def register_trial_subject_mapping(
        self,
        tenant_id: str,
        trial_id: str,
        site_id: str,
        subject_id: str,
        veridoc_patient_id: str,
        mapping_status: str = "verified",
    ) -> Dict[str, Any]:
        """Save a trial subject to VeriDoc patient mapping."""
        record = {
            "id": f"subject-map-{tenant_id}-{subject_id}",
            "tenant_id": tenant_id,
            "trial_id": trial_id,
            "site_id": site_id,
            "subject_id": subject_id,
            "veridoc_patient_id": veridoc_patient_id,
            "mapping_status": mapping_status,
            "created_at": datetime.utcnow(),
        }
        self._memory_subject_mappings.append(record)
        try:
            from app.db.mongodb import clinical_trial_subject_mappings_col
            doc = dict(record)
            doc["_id"] = doc.pop("id")
            await clinical_trial_subject_mappings_col().update_one(
                {"tenant_id": tenant_id, "trial_id": trial_id, "subject_id": subject_id},
                {"$set": doc},
                upsert=True,
            )
        except Exception as e:
            logger.warning(f"Could not persist trial subject mapping: {e}")
        return record


patient_mapping_repository = PatientMappingRepository()
