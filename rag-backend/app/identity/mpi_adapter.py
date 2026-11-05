"""
mpi_adapter.py — Master Patient Index (MPI) Adapter & Cross-Hospital Matcher.

Supports HL7 FHIR Patient/$match and deterministic/probabilistic matching
across heterogeneous hospital tenants (e.g. Apollo, Yashoda, KIMS).
Never silently merges ambiguous records — enforces adjudication flags.
"""

import logging
from typing import Dict, Any, List, Optional
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class MPIAdapter:
    """
    Adapter to query Master Patient Index (MPI) systems and calculate
    identity match confidence across multiple hospital EHRs.
    """

    MATCH_AUTO_THRESHOLD = 0.95        # Strict threshold for automated resolution
    MATCH_ADJUDICATION_THRESHOLD = 0.70  # Flagged for human review

    def calculate_probabilistic_score(
        self,
        candidate_a: Dict[str, Any],
        candidate_b: Dict[str, Any],
    ) -> float:
        """
        Calculates demographic similarity across:
        - Family & Given Name
        - Date of Birth (DOB)
        - Gender
        - Phone / Telecom
        """
        score = 0.0
        weights = {
            "name": 0.35,
            "dob": 0.35,
            "gender": 0.10,
            "phone": 0.20,
        }

        # 1. Name matching
        name_a = candidate_a.get("name", "").lower().strip()
        name_b = candidate_b.get("name", "").lower().strip()
        if name_a and name_b:
            name_sim = SequenceMatcher(None, name_a, name_b).ratio()
            score += name_sim * weights["name"]

        # 2. Date of Birth matching (strict exact date match)
        dob_a = candidate_a.get("birth_date", "")
        dob_b = candidate_b.get("birth_date", "")
        if dob_a and dob_b:
            if dob_a == dob_b:
                score += weights["dob"]

        # 3. Gender matching
        gen_a = candidate_a.get("gender", "").lower()
        gen_b = candidate_b.get("gender", "").lower()
        if gen_a and gen_b and gen_a == gen_b:
            score += weights["gender"]

        # 4. Telecom / Phone matching
        phone_a = candidate_a.get("phone", "")
        phone_b = candidate_b.get("phone", "")
        if phone_a and phone_b:
            # Strip non-digits
            digits_a = "".join(filter(str.isdigit, phone_a))[-10:]
            digits_b = "".join(filter(str.isdigit, phone_b))[-10:]
            if digits_a and digits_b and digits_a == digits_b:
                score += weights["phone"]

        return round(score, 3)

    async def execute_patient_match(
        self,
        demographics: Dict[str, Any],
        candidate_pool: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Executes FHIR R4 Patient/$match style candidate evaluation.
        Categorizes matches into:
        - 'verified': score >= 0.95
        - 'needs_adjudication': 0.70 <= score < 0.95
        - 'no_match': score < 0.70
        """
        evaluated_candidates = []

        for candidate in candidate_pool:
            score = self.calculate_probabilistic_score(demographics, candidate)
            evaluated_candidates.append({
                "candidate": candidate,
                "confidence_score": score,
                "status": (
                    "verified" if score >= self.MATCH_AUTO_THRESHOLD
                    else "needs_adjudication" if score >= self.MATCH_ADJUDICATION_THRESHOLD
                    else "low_confidence"
                ),
            })

        # Sort descending by match confidence score
        evaluated_candidates.sort(key=lambda c: c["confidence_score"], reverse=True)

        if not evaluated_candidates:
            return {
                "match_found": False,
                "best_candidate": None,
                "confidence": 0.0,
                "resolution": "no_match",
                "message": "No matching patient identity found in MPI pool.",
            }

        top = evaluated_candidates[0]
        if top["confidence_score"] >= self.MATCH_AUTO_THRESHOLD:
            return {
                "match_found": True,
                "best_candidate": top["candidate"],
                "confidence": top["confidence_score"],
                "resolution": "verified",
                "message": f"High confidence match ({top['confidence_score']:.2f}) verified.",
                "all_candidates": evaluated_candidates,
            }
        elif top["confidence_score"] >= self.MATCH_ADJUDICATION_THRESHOLD:
            return {
                "match_found": False,
                "best_candidate": top["candidate"],
                "confidence": top["confidence_score"],
                "resolution": "needs_adjudication",
                "message": (
                    f"Ambiguous identity match ({top['confidence_score']:.2f}). "
                    "Automatic resolution halted. Requires human adjudication before clinical audit."
                ),
                "all_candidates": evaluated_candidates,
            }
        else:
            return {
                "match_found": False,
                "best_candidate": None,
                "confidence": top["confidence_score"],
                "resolution": "no_match",
                "message": "Top candidate score fell below clinical confidence threshold.",
                "all_candidates": evaluated_candidates,
            }


mpi_adapter = MPIAdapter()
