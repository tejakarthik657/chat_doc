"""
mcp.py — REST API endpoints for Model Context Protocol (MCP) integrations.
Exposes MCP tool discovery, execution, and live database telemetry.
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from app.core.security import get_current_user
from app.mcp.registry import mcp_registry
from app.mcp.db_connector import clinical_db_connector

router = APIRouter(prefix="/api/mcp", tags=["mcp"])


class ToolCallRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = {}


class SQLQueryRequest(BaseModel):
    query: str
    limit: Optional[int] = 50


@router.get("/tools")
async def list_mcp_tools(user_id: str = Depends(get_current_user)):
    """List all available Inbound and Outbound MCP Tools (MCP tools/list)."""
    return {
        "tools": mcp_registry.list_tools(),
        "protocol_version": "2024-11-05",
        "total_tools": len(mcp_registry.tools)
    }


@router.post("/tools/call")
async def call_mcp_tool(
    body: ToolCallRequest,
    user_id: str = Depends(get_current_user)
):
    """Execute an MCP tool (MCP tools/call) within the security sandbox."""
    result = mcp_registry.call_tool(body.tool_name, body.arguments)
    if result.get("isError"):
        raise HTTPException(status_code=400, detail=result["content"][0]["text"])
    return result


@router.get("/status")
async def get_mcp_status(user_id: str = Depends(get_current_user)):
    """Check connectivity and telemetry for all registered MCP connectors."""
    db_status = clinical_db_connector.test_connection()
    return {
        "status": "active",
        "connectors": {
            "database_ehr": db_status,
            "mcp_tools_active": len(mcp_registry.tools)
        }
    }


@router.post("/database/query")
async def execute_sandboxed_sql(
    body: SQLQueryRequest,
    user_id: str = Depends(get_current_user)
):
    """Execute a sandboxed, read-only SELECT query through the Database MCP connector."""
    result = clinical_db_connector.execute_query(body.query, limit=body.limit or 50)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Database query failed."))
    return result


@router.get("/database/patients")
async def get_sample_patients(user_id: str = Depends(get_current_user)):
    """Retrieve sample clinical trial screening cohort for instant cross-reference testing."""
    result = clinical_db_connector.execute_query("SELECT * FROM patients ORDER BY patient_id ASC;")
    return {
        "count": result["row_count"],
        "patients": result["rows"]
    }
