"""
clinical.py — Clinical Protocol & Multi-Tenant Patient Resolution API Endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import Dict, Any, List, Optional
from app.core.security import get_current_user
from app.tenants.tenant_resolver import tenant_resolver
from app.identity.patient_identity_service import patient_identity_service
from app.integrations.fhir.fhir_observation_service import fhir_observation_service
from app.clinical.eligibility_engine import eligibility_engine
from app.clinical.audit_service import audit_service
from app.identity.mpi_adapter import mpi_adapter
from app.models.schemas import (
    PatientResolveRequest,
    PatientResolveResponse,
    ClinicalEligibilityEvaluationRequest,
    ClinicalEligibilityEvaluationResponse,
)

router = APIRouter(prefix="/api/clinical", tags=["clinical"])


@router.post("/resolve-patient", response_model=PatientResolveResponse)
async def resolve_patient(
    body: PatientResolveRequest,
    request: Request,
    user_id: str = Depends(get_current_user),
):
    """
    Resolves patient across 4 identity layers (VeriDoc ID, MRN, FHIR Resource ID, Trial Subject ID).
    Prevents cross-hospital identity collision.
    """
    try:
        tenant_context = await tenant_resolver.resolve_from_user(
            user_id=user_id,
            explicit_tenant_id=body.tenant_id or request.headers.get("X-Tenant-ID"),
        )
        resolved = await patient_identity_service.resolve_patient(
            tenant_context=tenant_context,
            raw_identifier=body.identifier,
            trial_id=body.trial_id or "NB-204",
        )
        return PatientResolveResponse(
            success=True,
            tenant_id=resolved.tenant_id,
            veridoc_patient_id=resolved.veridoc_patient_id,
            hospital_mrn=resolved.hospital_mrn,
            fhir_resource_id=resolved.fhir_resource_id,
            trial_subject_id=resolved.trial_subject_id,
            patient_name=resolved.patient_name,
            verification_method=resolved.verification_method,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/patients/{identifier}/observations")
async def get_patient_observations(
    identifier: str,
    tenant_id: Optional[str] = None,
    user_id: str = Depends(get_current_user),
):
    """Retrieves live normalized FHIR observations for resolved patient."""
    try:
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
            "patient_name": resolved.patient_name,
            "hospital_mrn": resolved.hospital_mrn,
            "fhir_resource_id": resolved.fhir_resource_id,
            "observations_count": len(obs_panel),
            "observations": obs_panel,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/evaluate-eligibility", response_model=ClinicalEligibilityEvaluationResponse)
async def evaluate_clinical_trial_eligibility(
    body: ClinicalEligibilityEvaluationRequest,
    request: Request,
    user_id: str = Depends(get_current_user),
):
    """
    Audits a patient against clinical trial exclusion criteria:
    - Resolves patient safely within tenant
    - Retrieves live FHIR observations
    - Evaluates protocol rules (ALT, Creatinine, Platelets, Washout)
    - Records immutable compliance audit
    """
    try:
        tenant_context = await tenant_resolver.resolve_from_user(
            user_id=user_id,
            explicit_tenant_id=body.tenant_id or request.headers.get("X-Tenant-ID"),
        )
        resolved = await patient_identity_service.resolve_patient(
            tenant_context=tenant_context,
            raw_identifier=body.identifier,
            trial_id=body.protocol_id,
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
            protocol_id=body.protocol_id,
            patient_summary=patient_summary,
            observations=obs_panel,
        )

        # Log audit
        audit_record = await audit_service.log_audit(
            tenant_id=resolved.tenant_id,
            hospital_name=resolved.hospital_name,
            veridoc_patient_id=resolved.veridoc_patient_id,
            hospital_mrn=resolved.hospital_mrn,
            fhir_resource_id=resolved.fhir_resource_id,
            protocol_id=body.protocol_id,
            eligible=eval_result["eligible"],
            violations=eval_result["violations"],
            user_id=user_id,
            trial_subject_id=resolved.trial_subject_id,
            biomarkers=eval_result["biomarkers"],
        )

        return ClinicalEligibilityEvaluationResponse(
            success=True,
            patient_id=resolved.veridoc_patient_id,
            tenant_id=resolved.tenant_id,
            protocol_id=body.protocol_id,
            eligible=eval_result["eligible"],
            violations=eval_result["violations"],
            warnings=eval_result["warnings"],
            biomarkers=eval_result["biomarkers"],
            provenance={
                "audit_id": audit_record["id"],
                "hospital_name": resolved.hospital_name,
                "fhir_endpoint": tenant_context.fhir_base_url,
                "fhir_resource_id": resolved.fhir_resource_id,
                "verification_method": resolved.verification_method,
            },
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/mpi/match")
async def execute_cross_hospital_mpi_match(
    demographics: Dict[str, Any],
    user_id: str = Depends(get_current_user),
):
    """
    Cross-hospital Master Patient Index matching for patients visiting multiple healthcare networks.
    """
    from app.mcp.clinical_tools import clinical_mcp_tools
    res = await clinical_mcp_tools.match_cross_hospital_mpi(demographics)
    return res


@router.get("/audits/{veridoc_patient_id}")
async def get_patient_audit_history(
    veridoc_patient_id: str,
    tenant_id: Optional[str] = "apollo-001",
    user_id: str = Depends(get_current_user),
):
    """Retrieve historical protocol audits for a patient."""
    history = await audit_service.get_audits_for_patient(
        tenant_id=tenant_id,
        veridoc_patient_id=veridoc_patient_id,
    )
    return {"audits": history, "count": len(history)}
