"""
watcher.py — Autonomous Event-Driven Compliance Watcher (Phase 4).
Automatically triggers upon document ingestion to inspect clinical trial protocols,
investigator brochures, and regulatory filings for contradictions, dosage discrepancies,
storage bounds, and GCP/FDA 21 CFR Part 11 deviations.
"""

import logging
import re
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from bson import ObjectId

from app.db.mongodb import chunks_col, documents_col, compliance_audits_col
from app.core.llm import generate

logger = logging.getLogger("mcp.watcher")


class AutonomousComplianceWatcher:
    """
    Autonomous Watcher that runs in the background immediately after a document
    is marked 'ready' in the ingestion pipeline.
    """

    # Heuristic clinical pattern rules for deterministic fallback audit
    CLINICAL_PATTERNS = [
        {
            "category": "Dosage Inconsistency",
            "regex": r"(?:dose|dosage|administered|titrated)\s+(?:at|of)?\s*(\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml))",
            "description": "Found multiple differing dosage mentions that may indicate titration or protocol conflict.",
            "severity": "HIGH",
            "regulatory_risk": "FDA 21 CFR 312.23 protocol discrepancy risk"
        },
        {
            "category": "Storage Temperature Bounds",
            "regex": r"(-?\d+(?:\.\d+)?\s*°?[CF]\s*(?:to|-)\s*-?\d+(?:\.\d+)?\s*°?[CF]|room temperature|refrigerat\w*|frozen)",
            "description": "Identified drug product storage temperature specifications.",
            "severity": "MEDIUM",
            "regulatory_risk": "ICH Q1A(R2) Stability Testing adherence"
        },
        {
            "category": "Liver Function Biomarker Bounds (ALT/AST)",
            "regex": r"(?:ALT|AST|bilirubin|serum creatinine)\s*(?:>|>=|greater than)\s*(\d+(?:\.\d+)?)\s*(?:x\s*ULN|times upper limit)",
            "description": "Patient exclusion threshold based on hepatic/renal biomarkers.",
            "severity": "CRITICAL",
            "regulatory_risk": "GCP E6(R2) Patient Safety & Exclusion Protocol"
        }
    ]

    async def audit_document_on_ingest(
        self,
        doc_id: str,
        user_id: str,
        filename: str,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main entry point called asynchronously by the ingestion pipeline.
        Fetches document chunks, analyzes semantic contradictions, and persists
        the resulting Compliance Audit.
        """
        logger.info(f"[Watcher] Starting Autonomous Compliance Audit for doc: {filename} ({doc_id})")

        try:
            # Step 1: Fetch all chunks for this newly ingested document
            cursor = chunks_col().find({"doc_id": doc_id}).limit(60)
            chunks = await cursor.to_list(length=60)

            if not chunks:
                logger.warning(f"[Watcher] No chunks found in chunks_col for doc_id {doc_id}.")
                return {"status": "SKIPPED", "reason": "No chunks found"}

            # Also find other prior documents in the same project or user workspace for cross-document audit
            prior_chunks = []
            if project_id:
                prior_cursor = chunks_col().find(
                    {"project_id": project_id, "doc_id": {"$ne": doc_id}}
                ).limit(30)
                prior_chunks = await prior_cursor.to_list(length=30)
            else:
                # Get chunks from user's other documents to cross-reference
                prior_cursor = chunks_col().find(
                    {"user_id": user_id, "doc_id": {"$ne": doc_id}}
                ).limit(20)
                prior_chunks = await prior_cursor.to_list(length=20)

            # Step 2: Run AI contradiction & compliance analysis
            audit_result = await self._analyze_chunks_for_contradictions(
                filename=filename,
                current_chunks=chunks,
                prior_chunks=prior_chunks
            )

            # Step 3: Determine audit status and highest severity
            findings = audit_result.get("findings", [])
            has_conflicts = len(findings) > 0
            severities = [f.get("severity", "LOW") for f in findings]

            if "CRITICAL" in severities:
                max_severity = "CRITICAL"
            elif "HIGH" in severities:
                max_severity = "HIGH"
            elif "MEDIUM" in severities:
                max_severity = "MEDIUM"
            elif has_conflicts:
                max_severity = "LOW"
            else:
                max_severity = "CLEARED"

            audit_status = "FLAGGED" if has_conflicts else "CLEARED"
            audit_id = str(ObjectId())

            # Step 4: Persist to compliance_audits collection
            audit_record = {
                "_id": audit_id,
                "doc_id": doc_id,
                "user_id": user_id,
                "project_id": project_id,
                "filename": filename,
                "audit_status": audit_status,
                "highest_severity": max_severity,
                "alert_count": len(findings),
                "summary": audit_result.get("summary", "Automated audit completed."),
                "findings": findings,
                "cross_referenced_documents_count": 1 if prior_chunks else 0,
                "created_at": datetime.utcnow().isoformat(),
                "action_dispatched": False
            }

            await compliance_audits_col().insert_one(audit_record)

            # Step 5: Update document record in documents_col
            await documents_col().update_one(
                {"_id": doc_id},
                {"$set": {
                    "has_compliance_alerts": has_conflicts,
                    "compliance_audit_id": audit_id,
                    "compliance_severity": max_severity,
                    "compliance_alert_count": len(findings),
                    "compliance_audited_at": datetime.utcnow().isoformat()
                }}
            )

            logger.info(
                f"[Watcher] Audit finished for {filename}: Status={audit_status}, "
                f"Severity={max_severity}, Findings={len(findings)}"
            )

            return audit_record

        except Exception as e:
            logger.error(f"[Watcher Error] Audit failed for doc_id {doc_id}: {e}", exc_info=True)
            return {"status": "ERROR", "error": str(e)}

    async def _analyze_chunks_for_contradictions(
        self,
        filename: str,
        current_chunks: List[Dict[str, Any]],
        prior_chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Combines current and prior document chunks into a unified context and invokes
        LLM spec contradiction verification. Falls back gracefully to heuristic checks.
        """
        # Format text snippets
        current_text = "\n\n".join([
            f"[Current Doc: {filename} | Page {c.get('page', 1)}]: {c.get('text', '')}"
            for c in current_chunks[:25]
        ])

        prior_text = ""
        if prior_chunks:
            prior_text = "\n\n".join([
                f"[Prior Doc: {c.get('source_name', 'Previous Version')} | Page {c.get('page', 1)}]: {c.get('text', '')}"
                for c in prior_chunks[:15]
            ])

        combined_context = f"{current_text}\n\n{prior_text}".strip()

        prompt = (
            "You are the VeriDoc Autonomous Clinical & Regulatory Compliance Auditor.\n"
            "Analyze the provided document text for any direct contradictions, conflicting specifications, "
            "or regulatory safety discrepancies.\n"
            "Focus specifically on:\n"
            "1. Dosage and titration contradictions (e.g. initial dose vs max dose conflicts).\n"
            "2. Inclusion / exclusion criteria conflicts (e.g. ALT/AST thresholds, age limits).\n"
            "3. Drug storage, temperature bounds, or handling requirements.\n"
            "4. Version discrepancies between current document and prior versions.\n\n"
            "Return ONLY a valid JSON object matching this schema:\n"
            "{\n"
            "  \"summary\": \"Concise 1-2 sentence executive audit summary\",\n"
            "  \"findings\": [\n"
            "    {\n"
            "      \"type\": \"Dosage Contradiction / Exclusion Criteria / Temperature Bound / Version Drift\",\n"
            "      \"severity\": \"CRITICAL | HIGH | MEDIUM | LOW\",\n"
            "      \"section_or_source\": \"Sections or page numbers involved\",\n"
            "      \"description\": \"Detailed explanation of what conflicts\",\n"
            "      \"regulatory_risk\": \"Relevant FDA 21 CFR, ICH GCP, or clinical risk\",\n"
            "      \"recommendation\": \"Actionable resolution\"\n"
            "    }\n"
            "  ]\n"
            "}\n"
            "If no contradictions or safety risks are found, return {\"summary\": \"No compliance contradictions detected.\", \"findings\": []}."
        )

        try:
            raw_response = generate(context=combined_context[:8000], question=prompt)
            clean_json = re.sub(r"^```json\s*|```$", "", raw_response.strip(), flags=re.MULTILINE)
            parsed = json.loads(clean_json)
            if isinstance(parsed, dict) and "findings" in parsed:
                return parsed
        except Exception as e:
            logger.warning(f"[Watcher LLM] LLM audit extraction failed or invalid JSON: {e}. Executing heuristic checks.")

        # Fallback heuristic clinical analysis
        findings = []
        full_doc_string = " ".join([c.get("text", "") for c in current_chunks])

        # 1. Dosage Contradiction Detection (e.g. 50 mg vs 15 mg)
        dosage_matches = re.findall(r"\b(\d+(?:\.\d+)?)\s*(mg|mcg|g|ml)\b", full_doc_string, re.IGNORECASE)
        if dosage_matches:
            formatted_dosages = [f"{val} {unit.lower()}" for val, unit in dosage_matches]
            unique_dosages = list(dict.fromkeys(formatted_dosages))
            if len(unique_dosages) >= 2:
                findings.append({
                    "type": "Dosage Contradiction",
                    "severity": "CRITICAL",
                    "section_or_source": f"{filename} (Protocol Dosage Specifications)",
                    "description": f"Multiple conflicting dosage specifications identified ({', '.join(unique_dosages[:4])}). Requires clinical harmonization.",
                    "regulatory_risk": "FDA 21 CFR 312.23 Protocol Deviation Risk",
                    "recommendation": "Harmonize starting and maximum dosage titration schedules prior to patient enrollment."
                })

        # 2. Temperature Storage Discrepancy Detection
        temp_matches = re.findall(
            r"(-?\d+\s*(?:°|deg|degrees)?\s*[CF]\s*(?:to|-)\s*-?\d+\s*(?:°|deg|degrees)?\s*[CF]|room\s+temperature|refrigerat\w*|frozen)",
            full_doc_string,
            re.IGNORECASE
        )
        if temp_matches:
            unique_temps = list(dict.fromkeys([t.strip().lower() for t in temp_matches]))
            if len(unique_temps) >= 2:
                findings.append({
                    "type": "Temperature Bound Discrepancy",
                    "severity": "HIGH",
                    "section_or_source": f"{filename} (Storage & Handling)",
                    "description": f"Conflicting storage specifications detected ({', '.join(unique_temps[:3])}).",
                    "regulatory_risk": "ICH Q1A(R2) Stability Testing adherence",
                    "recommendation": "Confirm cold chain (2-8 deg C) vs ambient room temperature handling guidelines."
                })

        # 3. Biomarker Exclusion Discrepancy
        bio_matches = re.findall(
            r"(?:ALT|AST|bilirubin|serum creatinine)\s*(?:>|>=|greater than)\s*(\d+(?:\.\d+)?\s*(?:x\s*ULN|times upper limit|mg/dL|U/L)?)",
            full_doc_string,
            re.IGNORECASE
        )
        if bio_matches and len(set(bio_matches)) >= 2:
            findings.append({
                "type": "Exclusion Criteria Mismatch",
                "severity": "HIGH",
                "section_or_source": f"{filename} (Eligibility Criteria)",
                "description": f"Conflicting biomarker exclusion thresholds specified ({', '.join(set(bio_matches))}).",
                "regulatory_risk": "GCP E6(R2) Patient Safety Protocol",
                "recommendation": "Align lab exclusion cutoffs with Principal Investigator criteria."
            })

        summary = (
            f"Automated heuristic audit detected {len(findings)} potential clinical protocol conflict(s)."
            if findings else "Document cleared. No protocol contradictions detected."
        )

        return {
            "summary": summary,
            "findings": findings
        }


# Singleton instance
compliance_watcher = AutonomousComplianceWatcher()
