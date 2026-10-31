"""
test_phase4_5_6.py — Automated Test Suite for Phases 4, 5, and 6:
1. Autonomous Event-Driven Watcher (Contradiction & Protocol Audit)
2. Outbound ActionMesh Dispatcher (Slack & EDC Protocol Hold)
3. VeriDoc Standard MCP Server (JSON-RPC 2.0 Tools List & Call)
"""

import sys
import os
import asyncio
import json

# Add backend directory to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "rag-backend"))

from app.mcp.watcher import compliance_watcher
from app.mcp.actions import outbound_dispatcher
from app.mcp.registry import mcp_registry


async def run_tests():
    print("=" * 70)
    print("[TEST SUITE] Phase 4, 5 & 6: ActionMesh, Watcher & MCP Server")
    print("=" * 70)

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 1: Autonomous Compliance Watcher (Phase 4)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n[TEST 1] Testing Autonomous Compliance Watcher on Contradictory Chunks...")
    conflicting_chunks = [
        {
            "doc_id": "test_doc_001",
            "page": 4,
            "text": "Section 4.1: Initial therapeutic dosage of Compound VX-409 is established at 50 mg daily."
        },
        {
            "doc_id": "test_doc_001",
            "page": 9,
            "text": "Section 9.2: Strict contraindication: Maximum tolerated starting dose shall not exceed 15 mg daily due to cardiotoxicity."
        },
        {
            "doc_id": "test_doc_001",
            "page": 14,
            "text": "Storage specifications: Maintain drug vial refrigerated at 2 deg C to 8 deg C. Alternative handling at room temperature 15 deg C to 25 deg C is prohibited."
        }
    ]

    analysis = await compliance_watcher._analyze_chunks_for_contradictions(
        filename="Clinical_Protocol_VX409_Amendment.pdf",
        current_chunks=conflicting_chunks,
        prior_chunks=[]
    )

    findings = analysis.get("findings", [])
    print(f"[PASS] Watcher Summary: {analysis.get('summary')}")
    print(f"[PASS] Total Findings Detected: {len(findings)}")

    has_dosage_or_critical = any(
        "dosage" in f.get("type", "").lower() or f.get("severity") == "CRITICAL"
        for f in findings
    )
    assert len(findings) > 0, "Autonomous Watcher must detect at least 1 contradiction!"
    print(f"[PASS] Finding #1 Type: {findings[0].get('type')} | Severity: {findings[0].get('severity')}")
    print(f"       Recommendation: {findings[0].get('recommendation')}")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 2: Outbound Slack Action Dispatcher (Phase 5)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n[TEST 2] Testing Outbound Slack Alert Dispatcher...")
    slack_res = outbound_dispatcher.dispatch_slack_alert_sync(
        channel="#clinical-trials-safety",
        message="Critical dosage discrepancy detected between Section 4.1 (50mg) and Section 9.2 (15mg).",
        severity="CRITICAL",
        document_name="Clinical_Protocol_VX409_Amendment.pdf",
        findings=findings
    )

    assert slack_res["action"] == "slack_alert"
    assert slack_res["severity"] == "CRITICAL"
    assert slack_res["status"] == "SENT"
    assert slack_res["channel"] == "#clinical-trials-safety"
    print(f"[PASS] Outbound Slack Alert: Dispatched successfully to {slack_res['channel']} (Status: {slack_res['status']})")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 3: Outbound EDC Protocol Hold Dispatcher (Phase 5)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n[TEST 3] Testing Outbound Electronic Data Capture (EDC) Protocol Hold...")
    edc_res = outbound_dispatcher.dispatch_edc_protocol_hold_sync(
        protocol_id="PROTOCOL-VX-409",
        reason="Severe dosage contradiction in protocol draft.",
        affected_sites=["Site 101 (Johns Hopkins)", "Site 104 (Mayo Clinic)"]
    )

    assert edc_res["action"] == "edc_protocol_hold"
    assert edc_res["status"] == "RECOMMENDED"
    assert len(edc_res["affected_sites"]) == 2
    print(f"[PASS] EDC Protocol Hold: Protocol {edc_res['protocol_id']} flagged for review across {len(edc_res['affected_sites'])} sites.")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 4: MCP Registry Outbound Tool Invocation (Phase 5)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n[TEST 4] Testing MCP Tool Registry Invocation for Outbound Actions...")
    tool_call_res = mcp_registry.call_tool(
        tool_name="send_slack_alert",
        arguments={
            "channel": "#regulatory-affairs",
            "message": "Protocol discrepancy resolved after investigator meeting.",
            "severity": "LOW",
            "document_name": "Protocol_VX409_Final.pdf"
        }
    )

    assert not tool_call_res.get("isError"), f"Tool call failed: {tool_call_res}"
    print("[PASS] MCP Tool 'send_slack_alert' executed with zero errors.")
    print(f"       Payload returned: {tool_call_res['data']['status']}")

    # ─────────────────────────────────────────────────────────────────────────
    # TEST 5: Standard MCP JSON-RPC 2.0 Server Interface (Phase 6)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n[TEST 5] Testing VeriDoc Standard MCP Server JSON-RPC 2.0 Protocol...")
    
    # Simulate Claude / Cursor calling "initialize"
    from app.api.routes.mcp import mcp_json_rpc, JSONRPCRequest

    init_req = JSONRPCRequest(jsonrpc="2.0", method="initialize", id="req-1")
    init_res = await mcp_json_rpc(init_req)
    assert init_res["result"]["protocolVersion"] == "2024-11-05"
    assert init_res["result"]["serverInfo"]["name"] == "VeriDoc-Synapse-MCP"
    print(f"[PASS] JSON-RPC 'initialize' passed. Server: {init_res['result']['serverInfo']['name']} v{init_res['result']['serverInfo']['version']}")

    # Simulate Claude / Cursor calling "tools/list"
    tools_req = JSONRPCRequest(jsonrpc="2.0", method="tools/list", id="req-2")
    tools_res = await mcp_json_rpc(tools_req)
    tool_names = [t["name"] for t in tools_res["result"]["tools"]]
    print(f"[PASS] JSON-RPC 'tools/list' passed. Discovered {len(tool_names)} tools: {tool_names}")
    assert "query_clinical_database" in tool_names
    assert "get_patient_lab_record" in tool_names
    assert "send_slack_alert" in tool_names
    assert "dispatch_edc_protocol_hold" in tool_names

    # Simulate Claude / Cursor executing a live tool call over JSON-RPC
    call_req = JSONRPCRequest(
        jsonrpc="2.0",
        method="tools/call",
        params={"name": "get_patient_lab_record", "arguments": {"patient_id": 104}},
        id="req-3"
    )
    call_res = await mcp_json_rpc(call_req)
    patient_data = call_res["result"]["data"]["patient"]
    assert patient_data["patient_id"] == 104
    assert patient_data["alt_enzyme"] == 142.0
    print(f"[PASS] JSON-RPC 'tools/call' passed. Queried Patient #{patient_data['patient_id']} (ALT: {patient_data['alt_enzyme']} U/L)")

    print("\n" + "=" * 70)
    print("[SUCCESS] ALL TESTS COMPLETED WITH 100% SUCCESS!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_tests())
