"""
tenants.py — Multi-Tenant Hospital & Organization API Endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any, Optional
from app.core.security import get_current_user
from app.tenants.tenant_service import tenant_service
from app.models.schemas import (
    TenantCreate,
    TenantOut,
    HospitalIntegrationCreate,
    HospitalIntegrationOut,
)

router = APIRouter(prefix="/api/tenants", tags=["tenants"])


@router.get("", response_model=List[TenantOut])
async def list_registered_tenants(user_id: str = Depends(get_current_user)):
    """List all registered hospital tenants in VeriDoc Synapse."""
    tenants = await tenant_service.list_tenants()
    return tenants


@router.get("/{tenant_id}", response_model=TenantOut)
async def get_tenant_details(tenant_id: str, user_id: str = Depends(get_current_user)):
    """Retrieve details for a specific hospital tenant."""
    tenant = await tenant_service.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found."
        )
    return tenant


@router.post("", response_model=TenantOut)
async def create_hospital_tenant(body: TenantCreate, user_id: str = Depends(get_current_user)):
    """Register a new hospital tenant."""
    res = await tenant_service.register_tenant(
        tenant_id=body.id,
        name=body.name,
        status=body.status,
        integration_type=body.integration_type,
    )
    return res


@router.get("/{tenant_id}/integration", response_model=HospitalIntegrationOut)
async def get_tenant_integration(tenant_id: str, user_id: str = Depends(get_current_user)):
    """Get FHIR integration configuration for hospital tenant."""
    integration = await tenant_service.get_integration(tenant_id)
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"FHIR integration configuration not found for tenant '{tenant_id}'."
        )
    return integration


@router.post("/{tenant_id}/integration", response_model=HospitalIntegrationOut)
async def configure_tenant_integration(
    tenant_id: str,
    body: HospitalIntegrationCreate,
    user_id: str = Depends(get_current_user),
):
    """Configure FHIR v4 endpoint and SMART authentication for a hospital tenant."""
    res = await tenant_service.register_integration(
        tenant_id=tenant_id,
        hospital_name=body.hospital_name,
        fhir_base_url=body.fhir_base_url,
        identifier_system=body.identifier_system,
        client_id=body.client_id,
        authentication_type=body.authentication_type,
        token_endpoint=body.token_endpoint,
        mpi_endpoint=body.mpi_endpoint,
        enabled=body.enabled,
    )
    return res
