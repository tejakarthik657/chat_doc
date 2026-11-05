"""
tenants package — Multi-Tenant Hospital & Organization Resolution.
"""
from app.tenants.tenant_service import TenantService, tenant_service
from app.tenants.tenant_resolver import TenantResolver, tenant_resolver

__all__ = ["TenantService", "tenant_service", "TenantResolver", "tenant_resolver"]
