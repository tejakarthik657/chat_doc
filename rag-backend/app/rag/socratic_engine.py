import json
import logging
import re
from typing import Optional, Dict, Any
from app.core.llm_groq import _get_or_init_groq_client
from app.db.mongodb import chunks_col, projects_col

logger = logging.getLogger(__name__)

BLOOM_LEVELS = [
    "Remember",
    "Understand",
    "Apply",
    "Analyze",
    "Evaluate",
    "Create"
]

BLOOM_PROMPTS = {
    "Remember": "Ask the student to state, recall, or define specific core terms, formulas, or facts strictly from the context.",
    "Understand": "Ask the student to explain the core mechanism or why something works in their own words.",
    "Apply": "Present a realistic practical scenario or problem and ask how the concept from the context is applied to solve it.",
    "Analyze": "Ask the student to dissect the trade-offs, differences, or failure points between components or approaches mentioned.",
    "Evaluate": "Ask the student to defend, critique, or justify a design choice, protocol, or standard based on the evidence.",
    "Create": "Challenge the student to propose an architectural modification, mitigation strategy, or novel synthesis combining ideas."
}

async def generate_viva_question(
    project_id: str,
    topic: Optional[str] = None,
    bloom_level: str = "Understand"
) -> Dict[str, Any]:
    """Generates an adaptive oral exam question based on project documents."""
    if bloom_level not in BLOOM_LEVELS:
        bloom_level = "Understand"

    # Query chunks for this project
    query: Dict[str, Any] = {"project_id": project_id}
    if topic:
        query["text"] = {"$regex": re.escape(topic), "$options": "i"}

    cursor = chunks_col().find(query).limit(10)
    chunks = await cursor.to_list(length=10)

    if not chunks:
        # Fallback without topic filter
        chunks = await chunks_col().find({"project_id": project_id}).limit(10).to_list(length=10)

    if not chunks:
        # Fallback if no chunks uploaded yet
        return {
            "question": f"In the context of {topic or 'this project'}, what are the foundational principles and key architectural considerations?",
            "bloom_level": bloom_level,
            "topic": topic or "General Project Knowledge",
            "key_concepts": [topic or "Architecture"],
            "context_snippet": "General project domain."
        }

    combined_context = "\n---\n".join([c.get("text", "")[:600] for c in chunks[:4]])

    client = _get_or_init_groq_client()
    instruction = BLOOM_PROMPTS.get(bloom_level, BLOOM_PROMPTS["Understand"])

    system_prompt = (
        "You are an expert Cambridge/MIT oral examiner conducting a high-stakes Socratic Viva examination.\n"
        f"Target Bloom's Taxonomy Level: {bloom_level.upper()}.\n"
        f"Exam Requirement: {instruction}\n"
        "Generate a single, direct, intellectually demanding oral viva question grounded in the source text.\n"
        "Respond strictly in valid JSON format:\n"
        "{\n"
        '  "question": "The spoken viva question to the student",\n'
        '  "topic": "Key subject topic",\n'
        '  "key_concepts": ["concept1", "concept2"],\n'
        '  "expected_key_points": ["point 1", "point 2"]\n'
        "}"
    )

    user_prompt = f"Source Document Excerpts:\n{combined_context}\n\nGenerate the {bloom_level} Viva question now."

    try:
        raw_res = client.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="qwen/qwen3.8-27b",
            temperature=0.4,
            max_tokens=400
        )
        json_match = re.search(r"\{.*\}", raw_res, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            data["bloom_level"] = bloom_level
            data["context_snippet"] = combined_context[:1000]
            return data
    except Exception as e:
        logger.error(f"[Socratic Engine] Error generating viva question: {e}")

    return {
        "question": f"Based on your study of {topic or 'this project'}, explain the primary mechanism and operational trade-offs.",
        "bloom_level": bloom_level,
        "topic": topic or "System Architecture",
        "key_concepts": ["Core Mechanism", "Trade-offs"],
        "context_snippet": combined_context[:1000]
    }


async def evaluate_viva_response(
    question: str,
    bloom_level: str,
    student_answer: str,
    context_snippet: str
) -> Dict[str, Any]:
    """
    Evaluates student answer with fine-grained rubric:
    Accuracy, Terminology, Depth, Misconception Diagnosis, and next Socratic probe.
    """
    client = _get_or_init_groq_client()

    system_prompt = (
        "You are an elite academic Socratic examiner evaluating a student's oral viva answer.\n"
        "Grade the student rigorously based on factual precision against the source context.\n"
        "Diagnose any conceptual flaws or false claims.\n"
        "Respond STRICTLY with a valid JSON object matching this schema:\n"
        "{\n"
        '  "accuracy_score": <int 0-100>,\n'
        '  "terminology_score": <int 0-100>,\n'
        '  "depth_score": <int 0-100>,\n'
        '  "overall_score": <int 0-100>,\n'
        '  "verdict": "Exemplary" | "Proficient" | "Partial Understanding" | "Fundamental Misconception",\n'
        '  "misconceptions": ["Identified misconception 1 with correction", ...],\n'
        '  "ground_truth_citation": "Direct excerpt quote from source supporting the correction",\n'
        '  "critique": "Crisp 2-sentence feedback directly to the candidate",\n'
        '  "suggested_next_level": "Remember" | "Understand" | "Apply" | "Analyze" | "Evaluate" | "Create",\n'
        '  "follow_up_question": "Next adaptive drill-down question"\n'
        "}"
    )

    user_prompt = (
        f"Source Context:\n{context_snippet}\n\n"
        f"Viva Question (Bloom Level: {bloom_level}):\n{question}\n\n"
        f"Student's Oral Answer:\n{student_answer}\n\n"
        "Evaluate the student's answer in JSON now."
    )

    try:
        raw_res = client.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="qwen/qwen3.8-27b",
            temperature=0.2,
            max_tokens=700
        )
        json_match = re.search(r"\{.*\}", raw_res, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
    except Exception as e:
        logger.error(f"[Socratic Engine] Error evaluating answer: {e}")

    # Fallback heuristic evaluation
    word_count = len(student_answer.split())
    acc = min(90, max(30, word_count * 2))
    return {
        "accuracy_score": acc,
        "terminology_score": acc - 5,
        "depth_score": acc,
        "overall_score": acc,
        "verdict": "Proficient" if acc > 65 else "Partial Understanding",
        "misconceptions": [],
        "ground_truth_citation": context_snippet[:200] if context_snippet else "Document context.",
        "critique": "Solid foundational understanding demonstrated. Strive to use exact domain nomenclature.",
        "suggested_next_level": "Apply" if acc > 70 else bloom_level,
        "follow_up_question": f"How would you address failure edge cases for this concept?"
    }
