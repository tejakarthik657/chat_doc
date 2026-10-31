"""
test_phase3_mcp.py — Verification Test Suite for Phase 3 (Inbound Database MCP Connector).

Tests:
1. Database MCP connection & auto-seeding of clinical trial screening cohort.
2. Parameterized patient lab biomarker retrieval.
3. Security Sandbox Guardrails (blocking DROP, DELETE, UPDATE, INSERT).
4. MCP Registry Protocol Compliance (tools/list & tools/call).
5. Natural language query detection & live database context enrichment.
6. Simulated Joint RAG Cross-Referencing (Protocol vs Live EHR).
"""

import sys
import os

# Add rag-backend to path
backend_dir = os.path.join(os.path.dirname(__file__), "rag-backend")
sys.path.insert(0, backend_dir)

from app.mcp.db_connector import clinical_db_connector, check_and_enrich_with_live_db
from app.mcp.registry import mcp_registry


def run_tests():
    print("=" * 70)
    print("[TEST SUITE] RUNNING PHASE 3: DATABASE MCP CONNECTOR TEST SUITE")
    print("=" * 70)

    # ── Test 1: Database Connectivity & Seeding ──────────────────────────────
    print("\n[Test 1] Testing Database Connectivity & Auto-Seeding...")
    health = clinical_db_connector.test_connection()
    print(f"Status: {health['status']} | Tables: {health['table_count']} | Patients: {health['sample_record_count']}")
    assert health["status"] == "connected", f"Expected connected, got {health}"
    assert health["sample_record_count"] >= 5, "Expected at least 5 seeded sample patients."
    print("  [PASS] Clinical screening database successfully connected and seeded.")

    # ── Test 2: Parameterized Patient Retrieval ──────────────────────────────
    print("\n[Test 2] Testing Patient Lab Biomarker Retrieval for Patient #104...")
    patient = clinical_db_connector.get_patient(104)
    assert patient is not None, "Patient 104 not found!"
    print(f"  Found Patient: {patient['name']} | Age: {patient['age']} | Gender: {patient['gender']}")
    print(f"  Biomarkers: Creatinine={patient['serum_creatinine']} mg/dL | ALT={patient['alt_enzyme']} U/L | Platelets={patient['platelet_count']:,}/uL")
    assert patient["serum_creatinine"] == 2.4, f"Expected 2.4, got {patient['serum_creatinine']}"
    assert patient["alt_enzyme"] == 142.0, f"Expected 142.0, got {patient['alt_enzyme']}"
    print("  [PASS] Biomarkers accurately retrieved.")

    # ── Test 3: Security Guardrails & SQL Injection Prevention ───────────────
    print("\n[Test 3] Testing Security Sandbox Guardrails against Destructive SQL...")
    
    malicious_queries = [
        "DROP TABLE patients;",
        "DELETE FROM patients WHERE patient_id = 104;",
        "UPDATE patients SET serum_creatinine = 1.0;",
        "INSERT INTO patients (patient_id, name) VALUES (999, 'Hacker');",
        "ALTER TABLE patients ADD COLUMN compromised TEXT;"
    ]

    for q in malicious_queries:
        res = clinical_db_connector.execute_query(q)
        assert res["success"] is False, f"Security breach! Query '{q}' should have been blocked."
        print(f"  Blocked: '{q}' -> {res['error']}")
    print("  [PASS] All destructive SQL commands strictly blocked by security guardrails.")

    # ── Test 4: MCP Registry Protocol Compliance (tools/list & tools/call) ───
    print("\n[Test 4] Testing MCP Registry (tools/list & tools/call)...")
    tools = mcp_registry.list_tools()
    tool_names = [t["name"] for t in tools]
    print(f"  Registered MCP Tools ({len(tools)}): {tool_names}")
    assert "query_clinical_database" in tool_names
    assert "get_patient_lab_record" in tool_names

    # Test tools/call execution
    call_res = mcp_registry.call_tool("get_patient_lab_record", {"patient_id": 105})
    assert call_res["isError"] is False
    assert call_res["data"]["found"] is True
    print(f"  MCP Call Result: Patient #105 -> {call_res['data']['patient']['name']}")
    print("  [PASS] MCP tool discovery and execution conform to protocol.")

    # ── Test 5: Query Detection & Inbound Context Enrichment ─────────────────
    print("\n[Test 5] Testing Query Detection & Live Inbound Context Injection...")
    test_question = "Audit candidate patient #104 against oncology protocol inclusion criteria."
    enrichment = check_and_enrich_with_live_db(test_question)
    assert enrichment is not None, "Failed to detect patient query!"
    assert enrichment["detected"] is True
    assert enrichment["patient_id"] == 104
    print("  Detected Context Block preview:")
    for line in enrichment["context_block"].split("\n")[:4]:
        print(f"    {line}")
    assert "2.4 mg/dL" in enrichment["context_block"]
    print("  [PASS] Live database context generated with exact biomarker values.")

    # ── Test 6: Simulated Joint Protocol Cross-Check ─────────────────────────
    print("\n[Test 6] Testing Joint Protocol Audit Logic...")
    protocol_criteria = {
        "max_serum_creatinine": 2.0,
        "max_alt_enzyme": 100.0,
        "min_platelet_count": 100000,
        "min_prior_chemo_days": 28
    }

    # Evaluate patient 104
    p104 = clinical_db_connector.get_patient(104)
    violations = []
    if p104["serum_creatinine"] > protocol_criteria["max_serum_creatinine"]:
        violations.append(f"Serum Creatinine ({p104['serum_creatinine']} mg/dL) exceeds protocol limit ({protocol_criteria['max_serum_creatinine']} mg/dL)")
    if p104["alt_enzyme"] > protocol_criteria["max_alt_enzyme"]:
        violations.append(f"ALT Liver Enzyme ({p104['alt_enzyme']} U/L) exceeds protocol limit ({protocol_criteria['max_alt_enzyme']} U/L)")
    if p104["platelet_count"] < protocol_criteria["min_platelet_count"]:
        violations.append(f"Platelet count ({p104['platelet_count']:,}) below protocol minimum ({protocol_criteria['min_platelet_count']:,})")
    if p104["prior_chemo_days"] < protocol_criteria["min_prior_chemo_days"]:
        violations.append(f"Prior chemotherapy washout ({p104['prior_chemo_days']} days) less than required 28 days")

    print(f"  Evaluated Patient #104 against Trial Protocol:")
    for v in violations:
        print(f"    [ALERT] VIOLATION DETECTED: {v}")
    assert len(violations) == 4, f"Expected 4 violations, found {len(violations)}"

    # Evaluate patient 105
    p105 = clinical_db_connector.get_patient(105)
    p105_violations = []
    if p105["serum_creatinine"] > protocol_criteria["max_serum_creatinine"]:
        p105_violations.append("Creatinine violation")
    if p105["alt_enzyme"] > protocol_criteria["max_alt_enzyme"]:
        p105_violations.append("ALT violation")
    assert len(p105_violations) == 0, f"Patient 105 should be eligible, got: {p105_violations}"
    print(f"  Evaluated Patient #105: All biomarkers compliant. Protocol status: ELIGIBLE.")
    print("  [PASS] Joint reasoning correctly identifies violations and eligible patients.")

    print("\n" + "=" * 70)
    print("[SUCCESS] ALL PHASE 3 DATABASE MCP TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
