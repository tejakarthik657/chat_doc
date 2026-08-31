"""
Query Router
─────────────
Classifies incoming questions and routes them to the optimal retrieval strategy.
Routes: faculty, placement, admission, naac, research, facilities, general
Each route applies different metadata filters, retrieval parameters, and prompt augmentations.
"""
from app.core.config import get_settings

settings = get_settings()


# Keyword sets for classification
_FACULTY_KW = [
    "faculty", "professor", "teacher", "staff", "hod", "lecturer",
    "profile", "qualification", "experience", "designation", "biodata",
    "bio-data", "resume", "members", "who teaches", "who is",
    "dr. ", "principal", "director", "dean"
]
_PLACEMENT_KW = [
    "placement", "recruit", "salary", "package", "offer", "company",
    "companies", "placed", "recruiter", "highest package", "average package",
    "median", "recruitment"
]
_ADMISSION_KW = [
    "admission", "admissions", "eligibility", "fee structure", "fees",
    "entrance", "how to apply", "apply", "cutoff", "cut-off",
    "seat", "reservation", "scholarship"
]
_NAAC_KW = [
    "naac", "nba", "accreditation", "iqa", "iqac", "grade", "accredited",
    "accreditation", "cgpa", "score card"
]
_RESEARCH_KW = [
    "research", "publication", "patent", "journal", "conference paper",
    "phd", "doctoral", "research area", "consultancy"
]
_FACILITIES_KW = [
    "facilities", "infrastructure", "campus", "hostel", "library",
    "sports", "gym", "laboratory", "lab ", "workshop"
]
_SYLLABUS_KW = [
    "syllabus", "curriculum", "course", "subject", "credit", "regulation",
    "scheme", "semester", "curriculum", "schem"
]


def _matches_any(query: str, keywords: list[str]) -> bool:
    q = query.lower()
    return any(kw in q for kw in keywords)


def classify_query(query: str) -> str:
    """
    Return one of: faculty | placement | admission | naac | research | facilities | syllabus | general
    Uses keyword matching — fast, no LLM call needed at query time.
    Order matters: faculty checked first because "staff" overlaps with "facilities".
    """
    if _matches_any(query, _FACULTY_KW):
        return "faculty"
    if _matches_any(query, _PLACEMENT_KW):
        return "placement"
    if _matches_any(query, _ADMISSION_KW):
        return "admission"
    if _matches_any(query, _NAAC_KW):
        return "naac"
    if _matches_any(query, _RESEARCH_KW):
        return "research"
    if _matches_any(query, _FACILITIES_KW):
        return "facilities"
    if _matches_any(query, _SYLLABUS_KW):
        return "syllabus"
    return "general"


def get_route_config(query: str) -> dict:
    """
    Returns routing config: metadata filter, boost hints, and prompt augmentation.
    """
    route = classify_query(query)

    configs = {
        "faculty": {
            "document_type": "faculty",
            "department": None,
            "top_k_multiplier": 1.0,
            "retrieval_pool": 35,
            "context_top_k": 10,
            "prompt_hint": (
                "This is a faculty lookup. Prioritize name, designation, qualification, "
                "and experience. Present as a clear list if multiple faculty are found."
            ),
        },
        "placement": {
            "document_type": "placement",
            "department": None,
            "top_k_multiplier": 1.0,
            "retrieval_pool": 30,
            "context_top_k": 8,
            "prompt_hint": (
                "This is a placement query. Prioritize company names, packages, "
                "number of students placed, and statistics. Present numbers clearly."
            ),
        },
        "admission": {
            "document_type": None,
            "department": None,
            "top_k_multiplier": 1.0,
            "retrieval_pool": 25,
            "context_top_k": 6,
            "prompt_hint": (
                "This is an admissions query. Prioritize eligibility criteria, "
                "fee structure, and application process."
            ),
        },
        "naac": {
            "document_type": "naac",
            "department": None,
            "top_k_multiplier": 0.8,
            "retrieval_pool": 25,
            "context_top_k": 6,
            "prompt_hint": (
                "This is an accreditation query. Prioritize grades, scores, "
                "and official accreditation status."
            ),
        },
        "research": {
            "document_type": "research",
            "department": None,
            "top_k_multiplier": 1.0,
            "retrieval_pool": 25,
            "context_top_k": 6,
            "prompt_hint": (
                "This is a research query. Prioritize publications, patents, "
                "research areas, and projects."
            ),
        },
        "facilities": {
            "document_type": "facilities",
            "department": None,
            "top_k_multiplier": 0.8,
            "retrieval_pool": 20,
            "context_top_k": 5,
            "prompt_hint": (
                "This is a facilities query. Prioritize infrastructure, labs, "
                "hostel, and campus amenities."
            ),
        },
        "syllabus": {
            "document_type": "syllabus",
            "department": None,
            "top_k_multiplier": 1.0,
            "retrieval_pool": 25,
            "context_top_k": 6,
            "prompt_hint": (
                "This is a syllabus/curriculum query. Prioritize courses, credits, "
                "schemes, and regulation details."
            ),
        },
        "general": {
            "document_type": None,
            "department": None,
            "top_k_multiplier": 1.0,
            "retrieval_pool": 20,
            "context_top_k": 5,
            "prompt_hint": "",
        },
    }

    return {
        "route": route,
        **configs.get(route, configs["general"])
    }
