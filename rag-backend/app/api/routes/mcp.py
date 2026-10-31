"""
mcp.py — REST & JSON-RPC API endpoints for Model Context Protocol (MCP) integrations.
Exposes MCP tool discovery, execution, live database telemetry, autonomous audits,
and Outbound ActionMesh dispatching. Conforms to MCP specification (2024-11-05).
"""

import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Body, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from app.core.security import get_current_user
from app.mcp.registry import mcp_registry
from app.mcp.db_connector import clinical_db_connector
from app.mcp.actions import outbound_dispatcher
from app.db.mongodb import compliance_audits_col, documents_col

router = APIRouter(prefix="/api/mcp", tags=["mcp"])


class ToolCallRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = {}


class SQLQueryRequest(BaseModel):
    query: str
    limit: Optional[int] = 50


class ActionDispatchRequest(BaseModel):
    action_type: str  # "slack_alert" | "edc_protocol_hold"
    channel: Optional[str] = None
    message: Optional[str] = None
    severity: Optional[str] = "HIGH"
    document_name: Optional[str] = "Clinical Trial Protocol"
    protocol_id: Optional[str] = None
    reason: Optional[str] = None
    affected_sites: Optional[List[str]] = None
    audit_id: Optional[str] = None


class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[Any] = 1


# ── Core MCP Discovery & Calling ─────────────────────────────────────────────

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


# ── Clinical Trial Inbound Database Endpoints ────────────────────────────────

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


# ── Phase 4: Autonomous Compliance Audit Endpoints ───────────────────────────

@router.get("/audits")
async def list_compliance_audits(
    limit: int = 20,
    user_id: str = Depends(get_current_user)
):
    """Retrieve recent autonomous compliance audit reports for the authenticated user."""
    cursor = compliance_audits_col().find({"user_id": user_id}).sort("created_at", -1).limit(limit)
    audits = await cursor.to_list(length=limit)
    return {
        "count": len(audits),
        "audits": audits
    }


@router.get("/audits/{doc_id}")
async def get_document_compliance_audit(
    doc_id: str,
    user_id: str = Depends(get_current_user)
):
    """Retrieve compliance audit findings for a specific document."""
    audit = await compliance_audits_col().find_one({"doc_id": doc_id, "user_id": user_id})
    if not audit:
        # Check if document exists
        doc = await documents_col().find_one({"_id": doc_id, "user_id": user_id})
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found.")
        return {
            "doc_id": doc_id,
            "audit_status": "CLEARED",
            "highest_severity": "CLEARED",
            "alert_count": 0,
            "summary": "Document passed ingestion checks with no protocol deviations.",
            "findings": []
        }
    return audit


# ── Phase 5: Outbound ActionMesh Dispatch Endpoints ──────────────────────────

@router.post("/actions/dispatch")
async def dispatch_outbound_action(
    payload: ActionDispatchRequest,
    user_id: str = Depends(get_current_user)
):
    """
    Dispatches an outbound action (e.g. user approved Slack notification or EDC protocol hold)
    and logs the audit trace.
    """
    if payload.action_type == "slack_alert":
        result = outbound_dispatcher.dispatch_slack_alert_sync(
            channel=payload.channel,
            message=payload.message or "Protocol deviation identified by VeriDoc Synapse.",
            severity=payload.severity or "HIGH",
            document_name=payload.document_name or "Clinical Protocol"
        )
    elif payload.action_type == "edc_protocol_hold":
        result = outbound_dispatcher.dispatch_edc_protocol_hold_sync(
            protocol_id=payload.protocol_id or "PROTOCOL-GENERIC",
            reason=payload.reason or "Protocol discrepancy requires IRB confirmation.",
            affected_sites=payload.affected_sites
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported action_type '{payload.action_type}'")

    # If linked to an audit record, mark it as dispatched
    if payload.audit_id:
        await compliance_audits_col().update_one(
            {"_id": payload.audit_id},
            {"$set": {"action_dispatched": True, "dispatched_at": result.get("dispatched_at")}}
        )

    return {
        "status": "success",
        "action_result": result
    }


# ── Phase 6: Expose VeriDoc as a Standard MCP Server (JSON-RPC 2.0 & SSE) ────

@router.post("/rpc")
async def mcp_json_rpc(request: JSONRPCRequest):
    """
    Standard MCP JSON-RPC 2.0 endpoint for external AI clients
    (Anthropic Claude Desktop, Cursor, or external Autonomous Agents).
    """
    req_id = request.id
    method = request.method
    params = request.params or {}

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": False}
                },
                "serverInfo": {
                    "name": "VeriDoc-Synapse-MCP",
                    "version": "1.0.0"
                }
            }
        }
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": mcp_registry.list_tools()
            }
        }
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        call_res = mcp_registry.call_tool(tool_name, arguments)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": call_res
        }
    elif method == "ping":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {}
        }
    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32601,
                "message": f"Method '{method}' not found."
            }
        }


@router.get("/sse")
async def mcp_server_sent_events(request: Request):
    """
    Standard MCP Server-Sent Events (SSE) stream endpoint.
    Notifies external MCP clients of endpoint URL for message dispatch.
    """
    async def event_generator():
        # First event: endpoint declaration
        endpoint_event = {
            "event": "endpoint",
            "data": "/api/mcp/rpc"
        }
        yield f"event: {endpoint_event['event']}\ndata: {endpoint_event['data']}\n\n"
        
        # Keepalive pulse
        while True:
            if await request.is_disconnected():
                break
            await asyncio.sleep(15)
            yield ": keepalive\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
