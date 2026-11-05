"""
eligibility_engine.py — Clinical Trial Protocol Eligibility Engine.

Evaluates normalized FHIR lab observations against trial protocol inclusion/exclusion criteria.
Specifically checks:
1. ALT <= 2.5x ULN (<= 140 U/L)
2. Serum Creatinine <= 1.5 mg/dL
3. Platelet Count >= 100,000 /uL
4. Cytotoxic chemotherapy washout >= 28 days
"""

import logging
from typing import Dict, Any, List
from app.clinical.terminology_service import terminology_service

logger = logging.getLogger(__name__)


class ClinicalEligibilityEngine:
    """Evaluates FHIR observations against protocol exclusion criteria."""

    PROTOCOL_RULES = {
        "NB-204": {
            "name": "Phase III Solid Tumor Immunotherapy Trial NB-204",
            "max_alt_uln_multiplier": 2.5,  # 2.5 * 56 = 140 U/L
            "max_serum_creatinine": 1.5,     # mg/dL
            "min_platelet_count": 100000,    # /uL
            "min_chemo_washout_days": 28,    # days
        }
    }

    def evaluate_protocol_eligibility(
        self,
        protocol_id: str,
        patient_summary: Dict[str, Any],
        observations: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Runs clinical deterministic verification against protocol rules.
        """
        rules = self.PROTOCOL_RULES.get(protocol_id, self.PROTOCOL_RULES["NB-204"])
        violations: List[str] = []
        warnings: List[str] = []
        extracted_biomarkers: Dict[str, Any] = {}

        for obs in observations:
            code = obs.get("code")
            val = obs.get("value")
            unit = obs.get("unit")

            # 1. ALT Liver Enzyme
            if code == "1742-6" and val is not None:
                extracted_biomarkers["alt_enzyme"] = {"value": val, "unit": unit}
                uln = 56.0
                cutoff = uln * rules["max_alt_uln_multiplier"]
                if val > cutoff:
                    violations.append(
                        f"Hepatic Exclusion: ALT level {val} {unit} exceeds protocol threshold of {cutoff} {unit} "
                        f"(2.5x ULN). FDA GCP Safety Violation."
                    )
                elif val > uln:
                    warnings.append(f"Borderline ALT: {val} {unit} is above normal reference range ({uln} {unit}).")

            # 2. Serum Creatinine
            elif code == "2160-0" and val is not None:
                extracted_biomarkers["serum_creatinine"] = {"value": val, "unit": unit}
                if val > rules["max_serum_creatinine"]:
                    violations.append(
                        f"Renal Exclusion: Serum creatinine {val} {unit} exceeds protocol limit of "
                        f"{rules['max_serum_creatinine']} {unit}."
                    )

            # 3. Platelet Count
            elif code == "777-3" and val is not None:
                extracted_biomarkers["platelet_count"] = {"value": val, "unit": unit}
                if val < rules["min_platelet_count"]:
                    violations.append(
                        f"Hematologic Exclusion: Platelet count {val:,} {unit} is below required protocol minimum "
                        f"of {rules['min_platelet_count']:,} {unit}."
                    )

            # 4. Chemotherapy Washout
            elif code == "367336001" and val is not None:
                extracted_biomarkers["prior_chemo_days"] = {"value": val, "unit": "days"}
                if val < rules["min_chemo_washout_days"]:
                    violations.append(
                        f"Therapeutic Washout Exclusion: Last cytotoxic chemotherapy was {val} days ago. "
                        f"Protocol requires a minimum {rules['min_chemo_washout_days']}-day washout period."
                    )

        eligible = len(violations) == 0

        return {
            "protocol_id": protocol_id,
            "protocol_name": rules.get("name"),
            "eligible": eligible,
            "violations_count": len(violations),
            "violations": violations,
            "warnings_count": len(warnings),
            "warnings": warnings,
            "biomarkers": extracted_biomarkers,
        }


eligibility_engine = ClinicalEligibilityEngine()
