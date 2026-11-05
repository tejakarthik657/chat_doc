"""
tenant_service.py — Multi-Tenant Hospital Management Service.

Maintains registered hospital tenants and their associated FHIR endpoints,
SMART credentials, and identifier systems.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Standard Built-in Hospital Tenants for Demo & Testing
SEED_TENANTS = {
    "apollo-001": {
        "id": "apollo-001",
        "name": "Apollo Hospital",
        "status": "active",
        "integration_type": "FHIR_R4",
        "trial_sites": ["site-apollo-01", "site-apollo-hyd"],
    },
    "yashoda-001": {
        "id": "yashoda-001",
        "name": "Yashoda Hospital",
        "status": "active",
        "integration_type": "FHIR_R4",
        "trial_sites": ["site-yashoda-sec"],
    },
    "kims-001": {
        "id": "kims-001",
        "name": "KIMS Hospital",
        "status": "active",
        "integration_type": "FHIR_R4",
        "trial_sites": ["site-kims-01"],
    },
}

SEED_INTEGRATIONS = {
    "apollo-001": {
        "id": "integ-apollo-01",
        "tenant_id": "apollo-001",
        "hospital_name": "Apollo Hospital",
        "fhir_base_url": "https://fhir.apollo.example/R4",
        "identifier_system": "https://apollo.example/mrn",
        "client_id": "apollo-veridoc-client",
        "authentication_type": "private_key_jwt",
        "token_endpoint": "https://auth.apollo.example/oauth2/token",
        "mpi_endpoint": "https://mpi.apollo.example/Patient/$match",
        "enabled": True,
    },
    "yashoda-001": {
        "id": "integ-yashoda-01",
        "tenant_id": "yashoda-001",
        "hospital_name": "Yashoda Hospital",
        "fhir_base_url": "https://fhir.yashoda.example/R4",
        "identifier_system": "https://yashoda.example/mrn",
        "client_id": "yashoda-veridoc-client",
        "authentication_type": "private_key_jwt",
        "token_endpoint": "https://auth.yashoda.example/oauth2/token",
        "mpi_endpoint": "https://mpi.yashoda.example/Patient/$match",
        "enabled": True,
    },
    "kims-001": {
        "id": "integ-kims-01",
        "tenant_id": "kims-001",
        "hospital_name": "KIMS Hospital",
        "fhir_base_url": "https://fhir.kims.example/R4",
        "identifier_system": "https://kims.example/mrn",
        "client_id": "kims-veridoc-client",
        "authentication_type": "private_key_jwt",
        "token_endpoint": "https://auth.kims.example/oauth2/token",
        "mpi_endpoint": "https://mpi.kims.example/Patient/$match",
        "enabled": True,
    },
}


class TenantService:
    """Service to create, lookup, and validate registered hospital tenants."""

    def __init__(self):
        self._memory_tenants: Dict[str, Dict[str, Any]] = dict(SEED_TENANTS)
        self._memory_integrations: Dict[str, Dict[str, Any]] = dict(SEED_INTEGRATIONS)

    async def get_tenant(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve tenant details by tenant_id."""
        try:
            from app.db.mongodb import tenants_col
            doc = await tenants_col().find_one({"_id": tenant_id})
            if doc:
                doc["id"] = doc.pop("_id")
                return doc
        except Exception:
            pass
        return self._memory_tenants.get(tenant_id)

    async def get_integration(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve FHIR integration configuration for a given tenant."""
        try:
            from app.db.mongodb import hospital_integrations_col
            doc = await hospital_integrations_col().find_one({"tenant_id": tenant_id})
            if doc:
                doc["id"] = str(doc.pop("_id"))
                return doc
        except Exception:
            pass
        return self._memory_integrations.get(tenant_id)

    async def list_tenants(self) -> List[Dict[str, Any]]:
        """List all active hospital tenants."""
        results = []
        try:
            from app.db.mongodb import tenants_col
            cursor = tenants_col().find({"status": "active"})
            async for doc in cursor:
                doc["id"] = doc.pop("_id")
                results.append(doc)
        except Exception:
            pass
        
        if not results:
            return list(self._memory_tenants.values())
        return results

    async def register_tenant(
        self,
        tenant_id: str,
        name: str,
        status: str = "active",
        integration_type: str = "FHIR_R4",
        trial_sites: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Register a new hospital tenant."""
        record = {
            "id": tenant_id,
            "name": name,
            "status": status,
            "integration_type": integration_type,
            "trial_sites": trial_sites or [],
            "created_at": datetime.utcnow(),
        }
        self._memory_tenants[tenant_id] = record
        try:
            from app.db.mongodb import tenants_col
            doc = dict(record)
            doc["_id"] = doc.pop("id")
            await tenants_col().update_one({"_id": tenant_id}, {"$set": doc}, upsert=True)
        except Exception as e:
            logger.warning(f"Could not persist tenant to MongoDB: {e}")
        return record

    async def register_integration(
        self,
        tenant_id: str,
        hospital_name: str,
        fhir_base_url: str,
        identifier_system: str,
        client_id: str,
        authentication_type: str = "private_key_jwt",
        token_endpoint: Optional[str] = None,
        mpi_endpoint: Optional[str] = None,
        enabled: bool = True,
    ) -> Dict[str, Any]:
        """Configure hospital FHIR endpoint and credentials."""
        record = {
            "id": f"integ-{tenant_id}",
            "tenant_id": tenant_id,
            "hospital_name": hospital_name,
            "fhir_base_url": fhir_base_url,
            "identifier_system": identifier_system,
            "client_id": client_id,
            "authentication_type": authentication_type,
            "token_endpoint": token_endpoint,
            "mpi_endpoint": mpi_endpoint,
            "enabled": enabled,
            "updated_at": datetime.utcnow(),
        }
        self._memory_integrations[tenant_id] = record
        try:
            from app.db.mongodb import hospital_integrations_col
            doc = dict(record)
            await hospital_integrations_col().update_one(
                {"tenant_id": tenant_id}, {"$set": doc}, upsert=True
            )
        except Exception as e:
            logger.warning(f"Could not persist integration to MongoDB: {e}")
        return record


tenant_service = TenantService()
