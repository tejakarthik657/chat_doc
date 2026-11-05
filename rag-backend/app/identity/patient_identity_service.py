"""
patient_identity_service.py — Unified Multi-Tenant Patient Resolution Service.

Resolves patient identity across the four healthcare identity layers:
1. VeriDoc Internal ID (VD-P-00104)
2. Hospital MRN (AP-104)
3. FHIR Patient Resource ID (Patient/patient-783)
4. Clinical Trial Subject ID (NB204-AP-0042)
"""

import re
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from app.tenants.tenant_resolver import HospitalTenantContext
from app.identity.patient_mapping_repository import patient_mapping_repository
from app.integrations.fhir.fhir_patient_service import fhir_patient_service

logger = logging.getLogger(__name__)


@dataclass
class ResolvedPatientIdentity:
    tenant_id: str
    hospital_name: str
    veridoc_patient_id: str
    hospital_mrn: str
    fhir_resource_id: str
    trial_subject_id: Optional[str] = None
    patient_name: Optional[str] = None
    identifier_system: Optional[str] = None
    verification_method: str = "authoritative_identifier"


class PatientIdentityService:
    """
    Unified Patient Resolution Engine for Multi-Hospital VeriDoc Deployments.
    """

    async def resolve_patient(
        self,
        tenant_context: HospitalTenantContext,
        raw_identifier: str,
        trial_id: Optional[str] = "NB-204",
    ) -> ResolvedPatientIdentity:
        """
        Resolves raw identifier in the context of the authenticated hospital tenant.
        """
        ident = raw_identifier.strip()
        tenant_id = tenant_context.tenant_id

        # ── Case 1: Clinical Trial Subject ID (e.g. NB204-AP-0042) ───────────
        trial_mapping = await patient_mapping_repository.get_by_trial_subject(
            tenant_id=tenant_id,
            subject_id=ident,
            trial_id=trial_id,
        )
        if trial_mapping:
            vd_id = trial_mapping["veridoc_patient_id"]
            patient_map = await patient_mapping_repository.get_by_veridoc_id(vd_id)
            if not patient_map or patient_map["tenant_id"] != tenant_id:
                raise ValueError(
                    f"Subject {ident} maps to VeriDoc ID {vd_id}, but no active mapping exists for tenant {tenant_id}."
                )

            return await self._verify_and_construct(
                tenant_context=tenant_context,
                mrn_value=patient_map["identifier_value"],
                veridoc_patient_id=vd_id,
                trial_subject_id=ident,
                cached_fhir_id=patient_map.get("fhir_resource_id"),
            )

        # ── Case 2: VeriDoc Patient ID (e.g. VD-P-00104) ──────────────────────
        if ident.startswith("VD-P-"):
            patient_map = await patient_mapping_repository.get_by_veridoc_id(ident)
            if not patient_map:
                raise ValueError(f"VeriDoc Patient ID '{ident}' not found in registry.")

            if patient_map["tenant_id"] != tenant_id:
                raise PermissionError(
                    f"Cross-Tenant Security Violation: Patient '{ident}' belongs to hospital "
                    f"'{patient_map['tenant_id']}', but session is authenticated for '{tenant_id}'."
                )

            # Check if there is an associated trial subject
            subject_map = await patient_mapping_repository.get_by_trial_subject(
                tenant_id=tenant_id,
                subject_id=patient_map.get("identifier_value"),
                trial_id=trial_id,
            )

            return await self._verify_and_construct(
                tenant_context=tenant_context,
                mrn_value=patient_map["identifier_value"],
                veridoc_patient_id=ident,
                trial_subject_id=subject_map["subject_id"] if subject_map else None,
                cached_fhir_id=patient_map.get("fhir_resource_id"),
            )

        # ── Case 3: Hospital MRN or Raw Numeric Patient ID ───────────────────
        # Normalize: If raw number e.g. "104", format to expected tenant MRN prefix or lookup
        mrn_value = ident
        if ident.isdigit():
            # Check tenant-specific prefixing
            if tenant_id == "apollo-001":
                mrn_value = f"AP-{ident}"
            elif tenant_id == "yashoda-001":
                mrn_value = f"YS-{ident}"
            elif tenant_id == "kims-001":
                mrn_value = f"KM-{ident}"

        # Look up existing verified mapping in repository
        patient_map = await patient_mapping_repository.get_by_hospital_mrn(
            tenant_id=tenant_id,
            identifier_system=tenant_context.identifier_system,
            identifier_value=mrn_value,
        )

        # Also search for trial subject mapping if present
        trial_subject_id = None
        vd_id = patient_map.get("veridoc_patient_id") if patient_map else f"VD-P-{ident.zfill(5)}"
        
        # Check trial subject mapping with verified internal ID
        if vd_id:
            try:
                from app.db.mongodb import clinical_trial_subject_mappings_col
                doc = await clinical_trial_subject_mappings_col().find_one({
                    "tenant_id": tenant_id,
                    "veridoc_patient_id": vd_id,
                })
                if doc:
                    trial_subject_id = doc.get("subject_id")
            except Exception:
                pass

        return await self._verify_and_construct(
            tenant_context=tenant_context,
            mrn_value=mrn_value,
            veridoc_patient_id=vd_id,
            trial_subject_id=trial_subject_id,
            cached_fhir_id=patient_map.get("fhir_resource_id") if patient_map else None,
        )

    async def _verify_and_construct(
        self,
        tenant_context: HospitalTenantContext,
        mrn_value: str,
        veridoc_patient_id: str,
        trial_subject_id: Optional[str] = None,
        cached_fhir_id: Optional[str] = None,
    ) -> ResolvedPatientIdentity:
        """
        Directly queries the hospital FHIR endpoint to verify the patient record is active and matches.
        """
        verified_patient = await fhir_patient_service.fetch_and_verify_patient(
            tenant_id=tenant_context.tenant_id,
            fhir_base_url=tenant_context.fhir_base_url,
            identifier_system=tenant_context.identifier_system,
            identifier_value=mrn_value,
            client_id=tenant_context.client_id,
            token_endpoint=tenant_context.token_endpoint,
        )

        fhir_id = verified_patient["fhir_resource_id"]
        patient_name = verified_patient.get("display_name")

        # If mapping didn't exist or was missing in DB, register it
        await patient_mapping_repository.register_patient_mapping(
            veridoc_patient_id=veridoc_patient_id,
            tenant_id=tenant_context.tenant_id,
            identifier_system=tenant_context.identifier_system,
            identifier_value=mrn_value,
            fhir_resource_id=fhir_id,
            mapping_status="verified",
            verification_method="authoritative_identifier",
        )

        return ResolvedPatientIdentity(
            tenant_id=tenant_context.tenant_id,
            hospital_name=tenant_context.hospital_name,
            veridoc_patient_id=veridoc_patient_id,
            hospital_mrn=mrn_value,
            fhir_resource_id=fhir_id,
            trial_subject_id=trial_subject_id,
            patient_name=patient_name,
            identifier_system=tenant_context.identifier_system,
            verification_method="authoritative_identifier",
        )


patient_identity_service = PatientIdentityService()
