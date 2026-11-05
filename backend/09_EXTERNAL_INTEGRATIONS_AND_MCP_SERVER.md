# 09. External Integrations & Model Context Protocol (MCP) Server

> *"Modern AI systems do not live in isolation. They connect outward to Slack and webhooks, and they connect inward to external autonomous agents via open protocols like the Model Context Protocol (MCP)."*

---

## 1. Asynchronous HTTP with `httpx` (Never use `requests`!)

In standard Python scripts, developers frequently use the `requests` library. 

**Using `requests` inside a FastAPI application is a critical architectural mistake:**
- `requests.post(...)` is synchronous and blocking. It halts the entire ASGI worker thread while waiting for the remote server's response!
- Instead, always use **`httpx.AsyncClient`** or **`aiohttp`**:

```python
# THE CORRECT ARCHITECTURE: Non-blocking asynchronous HTTP
import httpx

async def send_outbound_webhook(url: str, payload: dict):
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(url, json=payload)
        return response.status_code
```

---

## 2. Outbound ActionMesh Dispatcher (`app/mcp/actions.py`)

When an emergency clinical contradiction or patient biomarker violation is detected, the Outbound ActionMesh formats and dispatches actionable webhooks:

### A. Slack Clinical Emergency Dispatcher:
```python
# rag-backend/app/mcp/actions.py
import httpx

async def dispatch_slack_alert(channel_webhook: str, alert_data: dict) -> bool:
    """Dispatches a formatted Slack Block Kit alert to the hospital safety team."""
    payload = {
        "text": f"🚨 CLINICAL SAFETY ALERT: {alert_data['title']}",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "🚨 Immediate Protocol Deviation Detected"}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Patient ID:*\n{alert_data['patient_id']}"},
                    {"type": "mrkdwn", "text": f"*Violation:*\n{alert_data['violation_description']}"},
                    {"type": "mrkdwn", "text": f"*Severity:*\n*{alert_data['severity']}*"}
                ]
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": "Dispatched autonomously via VeriDoc Synapse ActionMesh."}
                ]
            }
        ]
    }
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.post(channel_webhook, json=payload)
        return resp.status_code == 200
```

---

## 3. Building a Bidirectional Model Context Protocol (MCP) Server

VeriDoc Synapse implements the official open **Model Context Protocol (MCP 2024-11-05)** specification in [`rag-backend/app/api/routes/mcp.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/api/routes/mcp.py):

```
┌─────────────────────────────────────────────────────────────┐
│                    EXTERNAL AI AGENTS                       │
│           (Claude Desktop / Cursor IDE / AutoGen)           │
└──────────────────────────────┬──────────────────────────────┘
                               │ JSON-RPC 2.0 (POST /api/mcp/rpc)
                               │ SSE Stream   (GET  /api/mcp/sse)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│             VERIDOC SYNAPSE MCP SERVER ROUTER               │
├─────────────────────────────────────────────────────────────┤
│ 1. Method: `initialize`  ──► Handshakes client & returns capabilities
│ 2. Method: `tools/list`  ──► Returns JSON schema of available tools
│ 3. Method: `tools/call`  ──► Executes tool and returns structured result
└──────────────────────────────┬──────────────────────────────┘
                               │
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
┌──────────────────────────────┐       ┌──────────────────────────────┐
│ `query_clinical_database`    │       │ `trigger_compliance_action`  │
│ (Reads live EHR patient labs)│       │ (Dispatches Slack / EDC hold)│
└──────────────────────────────┘       └──────────────────────────────┘
```

---

## 4. The JSON-RPC 2.0 Endpoint Implementation (`/api/mcp/rpc`)

```python
# rag-backend/app/api/routes/mcp.py
from fastapi import APIRouter, Request
from app.mcp.registry import mcp_registry

router = APIRouter()

@router.post("/rpc")
async def handle_mcp_rpc(request: Request):
    payload = await request.json()
    jsonrpc_ver = payload.get("jsonrpc")
    method = payload.get("method")
    req_id = payload.get("id")

    # 1. Handle Handshake
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "VeriDoc-Synapse-MCP", "version": "1.0.0"},
                "capabilities": {"tools": {}}
            }
        }

    # 2. Handle Tool Discovery
    if method == "tools/list":
        tools = mcp_registry.list_tools()
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools}}

    # 3. Handle Tool Execution
    if method == "tools/call":
        params = payload.get("params", {})
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        try:
            result = await mcp_registry.call_tool(tool_name, arguments)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": str(result)}], "isError": False}
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": f"Error: {e}"}], "isError": True}
            }
```

---

## 5. Connecting External Agents (Claude Desktop Configuration)

Because our FastAPI backend adheres to the open standard, any Claude Desktop user can integrate our clinical verification engine by adding this to their `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "veridoc-synapse": {
      "url": "https://veridoc-api.hospital.org/api/mcp/rpc",
      "headers": {
        "Authorization": "Bearer YOUR_JWT_TOKEN"
      }
    }
  }
}
```
Now, when an auditor chats with Claude Desktop, Claude can natively query hospital patient records and trigger trial holds through our FastAPI gateway!
