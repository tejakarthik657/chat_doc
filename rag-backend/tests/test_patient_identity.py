"""
test_patient_identity.py — Unit & Integration Tests for Multi-Tenant Patient Resolution.

Validates the core architectural requirements of VeriDoc Synapse:
1. Multi-Tenant Namespace Isolation (Patient 104 at Apollo vs Yashoda vs KIMS)
2. Four-layer Identifier Resolution (VD ID, MRN, FHIR Resource ID, Trial Subject ID)
3. Safety Guards (No silent guessing, rejection of cross-tenant attempts, inactive records)
4. Clinical Trial Protocol Eligibility Evaluation (ALT, Creatinine, Platelets, Washout)
5. Master Patient Index (MPI) deterministic & probabilistic matching
6. MCP Inbound Enrichment & Provenance Auditing
"""

import pytest
import asyncio
from app.tenants.tenant_service import tenant_service
from app.tenants.tenant_resolver import tenant_resolver, HospitalTenantContext
from app.identity.patient_mapping_repository import patient_mapping_repository
from app.identity.patient_identity_service import patient_identity_service
from app.integrations.fhir.fhir_patient_service import fhir_patient_service
from app.integrations.fhir.fhir_observation_service import fhir_observation_service
from app.clinical.eligibility_engine import eligibility_engine
from app.clinical.audit_service import audit_service
from app.identity.mpi_adapter import mpi_adapter
from app.mcp.clinical_tools import clinical_mcp_tools
from app.mcp.db_connector import check_and_enrich_with_live_db


@pytest.mark.asyncio
async def test_multi_tenant_namespace_isolation():
    """
    Core Problem Test:
    Patient 104 exists at Apollo, Yashoda, and KIMS.
    Verifies that VeriDoc resolves 3 completely distinct identities and FHIR resources.
    """
    # 1. Apollo Context
    apollo_ctx = await tenant_resolver.resolve_from_user(
        user_id="user-apollo",
        explicit_tenant_id="apollo-001",
    )
    apollo_p = await patient_identity_service.resolve_patient(apollo_ctx, "104")
    assert apollo_p.tenant_id == "apollo-001"
    assert apollo_p.hospital_mrn == "AP-104"
    assert apollo_p.fhir_resource_id == "patient-783"
    assert "Eleanor" in (apollo_p.patient_name or "")

    # 2. Yashoda Context
    yashoda_ctx = await tenant_resolver.resolve_from_user(
        user_id="user-yashoda",
        explicit_tenant_id="yashoda-001",
    )
    yashoda_p = await patient_identity_service.resolve_patient(yashoda_ctx, "104")
    assert yashoda_p.tenant_id == "yashoda-001"
    assert yashoda_p.hospital_mrn == "YS-104"
    assert yashoda_p.fhir_resource_id == "patient-921"
    assert "Ramesh" in (yashoda_p.patient_name or "")

    # 3. KIMS Context
    kims_ctx = await tenant_resolver.resolve_from_user(
        user_id="user-kims",
        explicit_tenant_id="kims-001",
    )
    kims_p = await patient_identity_service.resolve_patient(kims_ctx, "104")
    assert kims_p.tenant_id == "kims-001"
    assert kims_p.hospital_mrn == "KM-104"
    assert kims_p.fhir_resource_id == "patient-456"
    assert "Sunita" in (kims_p.patient_name or "")

    # Crucial Assertion: Identifiers are NOT conflated
    assert apollo_p.fhir_resource_id != yashoda_p.fhir_resource_id
    assert yashoda_p.fhir_resource_id != kims_p.fhir_resource_id
    assert apollo_p.patient_name != yashoda_p.patient_name


@pytest.mark.asyncio
async def test_clinical_trial_subject_id_resolution():
    """
    Verifies that a Clinical Trial Subject ID (NB204-AP-0042)
    correctly resolves to VeriDoc ID VD-P-00104 and Apollo FHIR patient-783.
    """
    apollo_ctx = await tenant_resolver.resolve_from_user(
        user_id="user-apollo",
        explicit_tenant_id="apollo-001",
    )
    resolved = await patient_identity_service.resolve_patient(
        tenant_context=apollo_ctx,
        raw_identifier="NB204-AP-0042",
        trial_id="NB-204",
    )
    assert resolved.veridoc_patient_id == "VD-P-00104"
    assert resolved.hospital_mrn == "AP-104"
    assert resolved.fhir_resource_id == "patient-783"
    assert resolved.trial_subject_id == "NB204-AP-0042"


@pytest.mark.asyncio
async def test_cross_tenant_access_rejection():
    """
    Security Guard Test:
    Attempting to resolve a Yashoda patient record using an Apollo session
    must be rejected with PermissionError.
    """
    apollo_ctx = await tenant_resolver.resolve_from_user(
        user_id="user-apollo",
        explicit_tenant_id="apollo-001",
    )
    # VD-P-00921 is registered to Yashoda
    with pytest.raises(PermissionError) as exc_info:
        await patient_identity_service.resolve_patient(apollo_ctx, "VD-P-00921")
    assert "Cross-Tenant Security Violation" in str(exc_info.value)


@pytest.mark.asyncio
async def test_protocol_eligibility_evaluation():
    """
    Clinical Protocol Audit Test:
    - Apollo AP-104 has ALT=142 U/L, Creatinine=2.4 mg/dL, Platelets=85k, Chemo=12d -> VIOLATION
    - Yashoda YS-104 has ALT=24 U/L, Creatinine=0.9 mg/dL, Platelets=220k, Chemo=90d -> ELIGIBLE
    """
    # Test Apollo Patient (Violation Expected)
    apollo_audit = await clinical_mcp_tools.audit_patient_eligibility(
        identifier="AP-104",
        protocol_id="NB-204",
        tenant_id="apollo-001",
    )
    assert apollo_audit["success"] is True
    assert apollo_audit["eligible"] is False
    assert apollo_audit["violations_count"] >= 3
    # Check specific violations
    violation_text = " ".join(apollo_audit["violations"])
    assert "Hepatic Exclusion" in violation_text
    assert "Renal Exclusion" in violation_text
    assert "Hematologic Exclusion" in violation_text

    # Test Yashoda Patient (Eligible Expected)
    yashoda_audit = await clinical_mcp_tools.audit_patient_eligibility(
        identifier="YS-104",
        protocol_id="NB-204",
        tenant_id="yashoda-001",
    )
    assert yashoda_audit["success"] is True
    assert yashoda_audit["eligible"] is True
    assert yashoda_audit["violations_count"] == 0


@pytest.mark.asyncio
async def test_master_patient_index_matching():
    """
    MPI Test:
    Rahul Kumar visits both Apollo and Yashoda.
    Verifies that MPI calculates demographic similarity and returns candidate match.
    """
    # Query Rahul Kumar's demographic profile
    demographics = {
        "name": "Rahul Kumar",
        "birth_date": "1998-04-15",
        "gender": "male",
        "phone": "919876543210",
    }
    match_result = await clinical_mcp_tools.match_cross_hospital_mpi(demographics)
    assert match_result["match_found"] is True
    assert match_result["confidence"] >= 0.95
    assert match_result["resolution"] == "verified"

    # Ambiguous profile test (slightly differing DOB and phone)
    ambiguous_demographics = {
        "name": "Rahul Kumar",
        "birth_date": "1995-01-01",  # Different DOB
        "gender": "male",
        "phone": "919999999999",     # Different phone
    }
    ambig_result = await clinical_mcp_tools.match_cross_hospital_mpi(ambiguous_demographics)
    # Must NOT automatically verify ambiguous records
    assert ambig_result["resolution"] != "verified"


def test_mcp_db_connector_multi_tenant_enrichment():
    """
    MCP Inbound Test:
    Verifies that check_and_enrich_with_live_db automatically detects hospital context
    and injects verified multi-tenant FHIR records into RAG prompts.
    """
    # 1. Apollo Query
    res_apollo = check_and_enrich_with_live_db("Check whether Patient 104 at Apollo Hospital violates the protocol")
    assert res_apollo is not None
    assert res_apollo["detected"] is True
    assert res_apollo["tenant_id"] == "apollo-001"
    assert "VIOLATES PROTOCOL" in res_apollo["context_block"]
    assert "Eleanor" in res_apollo["context_block"]

    # 2. Yashoda Query
    res_yashoda = check_and_enrich_with_live_db("Check whether Patient 104 at Yashoda Hospital violates the protocol")
    assert res_yashoda is not None
    assert res_yashoda["detected"] is True
    assert res_yashoda["tenant_id"] == "yashoda-001"
    assert "ELIGIBLE" in res_yashoda["context_block"]
    assert "Ramesh" in res_yashoda["context_block"]

    # 3. Clinical Trial Subject Query
    res_subject = check_and_enrich_with_live_db("Audit Subject NB204-AP-0042 against protocol criteria")
    assert res_subject is not None
    assert res_subject["detected"] is True
    assert "NB204-AP-0042" in res_subject["context_block"]
    assert "apollo-001" in res_subject["context_block"]
