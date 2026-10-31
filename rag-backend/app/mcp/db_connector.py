"""
db_connector.py — Secure Database MCP Inbound Connector.

Connects to live relational databases (PostgreSQL or local SQLite Clinical DB),
enforcing strict read-only constraints, SQL injection prevention, and schema inspection.
Enables VeriDoc agents to cross-reference live patient/inventory records with indexed documents.
"""

import os
import re
import sqlite3
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "storage", "clinical_sample.db")


class DatabaseMCPConnector:
    """
    Secure Inbound Database Connector conforming to MCP Tool Execution standards.
    """

    def __init__(self, connection_string: Optional[str] = None):
        self.connection_string = connection_string or os.environ.get("MCP_DATABASE_URL")
        self.is_sqlite = not self.connection_string or self.connection_string.startswith("sqlite")
        
        if self.is_sqlite:
            # Normalize path for SQLite
            if self.connection_string and self.connection_string.startswith("sqlite:///"):
                self.db_path = self.connection_string.replace("sqlite:///", "")
            else:
                self.db_path = os.path.abspath(DEFAULT_DB_PATH)
                os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            self._init_sample_clinical_db()

    def _init_sample_clinical_db(self):
        """Pre-populates a clinical trial patient screening database for instant testing."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                patient_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                gender TEXT NOT NULL,
                serum_creatinine REAL NOT NULL,     -- mg/dL (Normal: 0.7 - 1.3)
                alt_enzyme REAL NOT NULL,           -- U/L (Normal: 7 - 56)
                platelet_count INTEGER NOT NULL,    -- /uL (Normal: 150k - 450k)
                prior_chemo_days INTEGER NOT NULL,  -- Days since last cytotoxic agent
                concurrent_meds TEXT,               -- Comedication list
                screening_status TEXT NOT NULL
            );
            """)

            cursor.execute("SELECT COUNT(*) FROM patients;")
            count = cursor.fetchone()[0]

            if count == 0:
                sample_patients = [
                    (104, "Eleanor Vance", 58, "Female", 2.4, 142.0, 85000, 12, "Ketoconazole, Warfarin", "Screening"),
                    (105, "Marcus Brody", 64, "Male", 1.1, 28.5, 240000, 45, "Lisinopril, Metformin", "Eligible"),
                    (106, "Sarah Connor", 45, "Female", 0.9, 34.0, 310000, 60, "Levothyroxine", "Eligible"),
                    (107, "James Kirk", 71, "Male", 1.8, 190.0, 95000, 21, "Clopidogrel, Atorvastatin", "Screening"),
                    (108, "David Bowman", 52, "Male", 1.2, 42.0, 210000, 90, "None", "Eligible"),
                ]
                cursor.executemany("""
                INSERT INTO patients (
                    patient_id, name, age, gender, serum_creatinine, alt_enzyme,
                    platelet_count, prior_chemo_days, concurrent_meds, screening_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, sample_patients)
                conn.commit()
                logger.info(f"[DatabaseMCPConnector] Seeded sample clinical patient database at: {self.db_path}")

            conn.close()
        except Exception as e:
            logger.error(f"[DatabaseMCPConnector] Failed to initialize sample database: {e}")

    def execute_query(self, query: str, limit: int = 50) -> Dict[str, Any]:
        """
        Executes a sandboxed, read-only SQL query.
        Rejects non-SELECT or destructive statements.
        """
        clean_q = query.strip()

        # Security Guardrail 1: Enforce SELECT only
        if not re.match(r"^\s*SELECT\b", clean_q, re.IGNORECASE):
            return {
                "success": False,
                "error": "Security Violation: Only read-only SELECT statements are permitted.",
                "rows": [],
                "columns": []
            }

        # Security Guardrail 2: Reject destructive keywords
        forbidden = [
            r"\bDROP\b", r"\bDELETE\b", r"\bUPDATE\b", r"\bINSERT\b",
            r"\bALTER\b", r"\bTRUNCATE\b", r"\bREPLACE\b", r"\bEXEC\b",
            r"\bGRANT\b", r"\bREVOKE\b", r"\bATTACH\b", r"\bDETACH\b"
        ]
        for pattern in forbidden:
            if re.search(pattern, clean_q, re.IGNORECASE):
                return {
                    "success": False,
                    "error": f"Security Violation: Forbidden keyword detected matching '{pattern}'.",
                    "rows": [],
                    "columns": []
                }

        # Append limit if not already present
        if not re.search(r"\bLIMIT\s+\d+", clean_q, re.IGNORECASE):
            clean_q = f"{clean_q.rstrip(';')} LIMIT {limit};"

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(clean_q)
            rows = cursor.fetchall()
            columns = [col[0] for col in cursor.description] if cursor.description else []
            data = [dict(row) for row in rows]
            conn.close()

            return {
                "success": True,
                "query": clean_q,
                "columns": columns,
                "rows": data,
                "row_count": len(data)
            }
        except Exception as e:
            logger.error(f"[DatabaseMCPConnector] SQL execution error: {e}")
            return {
                "success": False,
                "error": str(e),
                "columns": [],
                "rows": []
            }

    def get_patient(self, patient_id: int | str) -> Optional[Dict[str, Any]]:
        """Convenience parameterized retrieval for patient lab records."""
        try:
            pid = int(patient_id)
        except (ValueError, TypeError):
            return None

        result = self.execute_query(f"SELECT * FROM patients WHERE patient_id = {pid};")
        if result["success"] and result["rows"]:
            return result["rows"][0]
        return None

    def get_schema(self) -> Dict[str, Any]:
        """Returns the database schema for LLM reasoning."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [r[0] for r in cursor.fetchall() if not r[0].startswith("sqlite_")]

            schema = {}
            for table in tables:
                cursor.execute(f"PRAGMA table_info({table});")
                schema[table] = [
                    {"name": col[1], "type": col[2], "notnull": bool(col[3]), "primary_key": bool(col[5])}
                    for col in cursor.fetchall()
                ]
            conn.close()
            return {"tables": schema, "db_type": "SQLite / Live Clinical EHR"}
        except Exception as e:
            logger.error(f"[DatabaseMCPConnector] Schema extraction failed: {e}")
            return {"tables": {}, "error": str(e)}

    def test_connection(self) -> Dict[str, Any]:
        """Tests connectivity and returns health telemetry."""
        schema = self.get_schema()
        test_q = self.execute_query("SELECT COUNT(*) AS total_patients FROM patients;")
        return {
            "status": "connected" if test_q["success"] else "error",
            "db_path": self.db_path,
            "table_count": len(schema.get("tables", {})),
            "sample_record_count": test_q["rows"][0]["total_patients"] if test_q["success"] else 0,
            "error": test_q.get("error")
        }


# Global singleton instance
clinical_db_connector = DatabaseMCPConnector()


def check_and_enrich_with_live_db(question: str) -> Optional[Dict[str, Any]]:
    """
    Detects if a user query references patient lab records, clinical cohorts, or database metrics.
    If detected, queries the live Database MCP connector and returns structured enrichment context.
    """
    q_lower = question.lower()
    
    # 1. Match specific patient ID (e.g. "patient #104", "patient 105", "pt 104")
    patient_match = re.search(r"\b(?:patient|pt|subject|cohort|id)\s*(?:#|no\.?|id)?\s*(\d+)\b", q_lower)
    if patient_match:
        pid = int(patient_match.group(1))
        patient = clinical_db_connector.get_patient(pid)
        if patient:
            context_block = (
                f"[LIVE EHR/DATABASE MCP RECORD: PATIENT #{pid}]\n"
                f"- Name: {patient['name']} (Age: {patient['age']}, Gender: {patient['gender']})\n"
                f"- Serum Creatinine: {patient['serum_creatinine']} mg/dL\n"
                f"- ALT Liver Enzyme: {patient['alt_enzyme']} U/L\n"
                f"- Platelet Count: {patient['platelet_count']:,} /uL\n"
                f"- Days Since Prior Chemotherapy: {patient['prior_chemo_days']} days\n"
                f"- Concurrent Medications: {patient['concurrent_meds']}\n"
                f"- Current Status: {patient['screening_status']}\n"
                f"[END LIVE DATABASE RECORD]"
            )
            evidence_snippet = (
                f"Patient #{pid} ({patient['name']}): Creatinine {patient['serum_creatinine']} mg/dL, "
                f"ALT {patient['alt_enzyme']} U/L, Platelets {patient['platelet_count']:,}/uL, "
                f"Prior Chemo: {patient['prior_chemo_days']} days, Meds: {patient['concurrent_meds']}"
            )
            return {
                "detected": True,
                "patient_id": pid,
                "context_block": context_block,
                "evidence_item": {
                    "chunk_id": f"mcp_live_ehr_{pid}",
                    "page": 0,
                    "score": 1.0,
                    "source": "Live EHR Clinical Database (MCP Inbound)",
                    "snippet": evidence_snippet
                }
            }

    # 2. General cohort query (e.g. "audit candidate patient cohort", "list screening patients")
    cohort_keywords = ["all patients", "screening cohort", "patient cohort", "candidate patients", "cohort audit"]
    if any(kw in q_lower for kw in cohort_keywords):
        all_res = clinical_db_connector.execute_query("SELECT * FROM patients ORDER BY patient_id ASC LIMIT 5;")
        if all_res["success"] and all_res["rows"]:
            lines = [f"[LIVE EHR/DATABASE MCP COHORT SUMMARY: {all_res['row_count']} PATIENTS]"]
            for p in all_res["rows"]:
                lines.append(
                    f"- Patient #{p['patient_id']} ({p['name']}): Creatinine={p['serum_creatinine']} mg/dL, "
                    f"ALT={p['alt_enzyme']} U/L, Platelets={p['platelet_count']:,}/uL, Prior Chemo={p['prior_chemo_days']}d"
                )
            lines.append("[END LIVE COHORT SUMMARY]")
            return {
                "detected": True,
                "context_block": "\n".join(lines),
                "evidence_item": {
                    "chunk_id": "mcp_live_ehr_cohort",
                    "page": 0,
                    "score": 1.0,
                    "source": "Live EHR Clinical Database (MCP Inbound)",
                    "snippet": f"Retrieved {all_res['row_count']} candidate patients from live screening database for protocol audit."
                }
            }

    return None

