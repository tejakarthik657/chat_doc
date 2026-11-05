"""
clinical_tools.py — MCP Inbound Clinical Tools for Multi-Tenant Patient Resolution.

Exposes standard Model Context Protocol (MCP) tools for VeriDoc agents:
1. resolve_patient_identity
2. get_patient_fhir_observations
3. audit_patient_trial_eligibility
4. match_cross_hospital_patient (MPI)
"""

import logging
from typing import Dict, Any, Optional, List
from app.tenants.tenant_resolver import tenant_resolver
from app.identity.patient_identity_service import patient_identity_service
from app.integrations.fhir.fhir_observation_service import fhir_observation_service
from app.clinical.eligibility_engine import eligibility_engine
from app.clinical.audit_service import audit_service
from app.identity.mpi_adapter import mpi_adapter

logger = logging.getLogger(__name__)


class ClinicalMCPTools:
    """MCP Tools for secure multi-tenant patient identity and protocol auditing."""

    async def resolve_patient(
        self,
        identifier: str,
        tenant_id: Optional[str] = None,
        user_id: str = "clinician-001",
    ) -> Dict[str, Any]:
        """Resolves patient identity within authorized hospital tenant."""
        tenant_context = await tenant_resolver.resolve_from_user(
            user_id=user_id,
            explicit_tenant_id=tenant_id,
        )
        resolved = await patient_identity_service.resolve_patient(
            tenant_context=tenant_context,
            raw_identifier=identifier,
        )
        return {
            "success": True,
            "tenant_id": resolved.tenant_id,
            "hospital_name": resolved.hospital_name,
            "veridoc_patient_id": resolved.veridoc_patient_id,
            "hospital_mrn": resolved.hospital_mrn,
            "fhir_resource_id": resolved.fhir_resource_id,
            "trial_subject_id": resolved.trial_subject_id,
            "patient_name": resolved.patient_name,
            "verification_method": resolved.verification_method,
        }

    async def get_patient_observations(
        self,
        identifier: str,
        tenant_id: Optional[str] = None,
        user_id: str = "clinician-001",
    ) -> Dict[str, Any]:
        """Retrieves and normalizes FHIR observations for resolved patient."""
        tenant_context = await tenant_resolver.resolve_from_user(
            user_id=user_id,
            explicit_tenant_id=tenant_id,
        )
        resolved = await patient_identity_service.resolve_patient(
            tenant_context=tenant_context,
            raw_identifier=identifier,
        )
        obs_panel = await fhir_observation_service.get_patient_panel(
            tenant_id=tenant_context.tenant_id,
            fhir_base_url=tenant_context.fhir_base_url,
            fhir_patient_id=resolved.fhir_resource_id,
            client_id=tenant_context.client_id,
            token_endpoint=tenant_context.token_endpoint,
        )
        return {
            "success": True,
            "tenant_id": resolved.tenant_id,
            "hospital_name": resolved.hospital_name,
            "patient_name": resolved.patient_name,
            "hospital_mrn": resolved.hospital_mrn,
            "fhir_resource_id": resolved.fhir_resource_id,
            "observations_count": len(obs_panel),
            "observations": obs_panel,
        }

    async def audit_patient_eligibility(
        self,
        identifier: str,
        protocol_id: str = "NB-204",
        tenant_id: Optional[str] = None,
        user_id: str = "clinician-001",
    ) -> Dict[str, Any]:
        """Resolves patient and verifies eligibility against clinical trial protocol."""
        tenant_context = await tenant_resolver.resolve_from_user(
            user_id=user_id,
            explicit_tenant_id=tenant_id,
        )
        resolved = await patient_identity_service.resolve_patient(
            tenant_context=tenant_context,
            raw_identifier=identifier,
            trial_id=protocol_id,
        )
        obs_panel = await fhir_observation_service.get_patient_panel(
            tenant_id=tenant_context.tenant_id,
            fhir_base_url=tenant_context.fhir_base_url,
            fhir_patient_id=resolved.fhir_resource_id,
            client_id=tenant_context.client_id,
            token_endpoint=tenant_context.token_endpoint,
        )

        patient_summary = {
            "name": resolved.patient_name,
            "mrn": resolved.hospital_mrn,
            "fhir_id": resolved.fhir_resource_id,
        }
        eval_result = eligibility_engine.evaluate_protocol_eligibility(
            protocol_id=protocol_id,
            patient_summary=patient_summary,
            observations=obs_panel,
        )

        # Record immutable audit log
        audit_record = await audit_service.log_audit(
            tenant_id=resolved.tenant_id,
            hospital_name=resolved.hospital_name,
            veridoc_patient_id=resolved.veridoc_patient_id,
            hospital_mrn=resolved.hospital_mrn,
            fhir_resource_id=resolved.fhir_resource_id,
            protocol_id=protocol_id,
            eligible=eval_result["eligible"],
            violations=eval_result["violations"],
            user_id=user_id,
            trial_subject_id=resolved.trial_subject_id,
            biomarkers=eval_result["biomarkers"],
        )

        return {
            "success": True,
            "patient_id": resolved.veridoc_patient_id,
            "patient_name": resolved.patient_name,
            "tenant_id": resolved.tenant_id,
            "hospital_name": resolved.hospital_name,
            "hospital_mrn": resolved.hospital_mrn,
            "trial_subject_id": resolved.trial_subject_id,
            "protocol_id": protocol_id,
            "eligible": eval_result["eligible"],
            "violations_count": eval_result["violations_count"],
            "violations": eval_result["violations"],
            "warnings": eval_result["warnings"],
            "biomarkers": eval_result["biomarkers"],
            "provenance": {
                "audit_id": audit_record["id"],
                "fhir_endpoint": tenant_context.fhir_base_url,
                "fhir_resource_id": resolved.fhir_resource_id,
                "verification_method": resolved.verification_method,
            },
        }

    async def match_cross_hospital_mpi(
        self,
        demographics: Dict[str, Any],
        candidate_pool: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Cross-hospital Master Patient Index matching."""
        from app.integrations.fhir.fhir_client import FHIR_SANDBOX_PATIENTS
        if not candidate_pool:
            # Build pool from all registered hospital sandbox databases
            pool = []
            for t_id, patients in FHIR_SANDBOX_PATIENTS.items():
                for pid, p in patients.items():
                    name_parts = []
                    for n in p.get("name", []):
                        full = f"{' '.join(n.get('given', []))} {n.get('family', '')}".strip()
                        if full:
                            name_parts.append(full)
                    phone = p.get("telecom", [{}])[0].get("value", "")
                    pool.append({
                        "tenant_id": t_id,
                        "fhir_resource_id": pid,
                        "name": name_parts[0] if name_parts else "",
                        "birth_date": p.get("birthDate", ""),
                        "gender": p.get("gender", ""),
                        "phone": phone,
                        "identifiers": p.get("identifier", []),
                    })
            candidate_pool = pool

        return await mpi_adapter.execute_patient_match(demographics, candidate_pool)


clinical_mcp_tools = ClinicalMCPTools()
