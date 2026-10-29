"""
Analytics Engine
────────────────
Offline clustering of question embeddings using KMeans.
No real-time plotting. Run as a cron job or on-demand.
"""
import numpy as np
from datetime import datetime, timedelta

from app.db.mongodb import analytics_col, documents_col
from app.core.config import get_settings

settings = get_settings()


async def get_user_analytics(user_id: str, days: int = 30) -> dict:
    """
    Returns question stats + topic clusters for a user.
    Clustering only runs when there are enough questions.
    """
    since = datetime.utcnow() - timedelta(days=days)

    # Pull all question records for this user
    records = await analytics_col().find(
        {"user_id": user_id, "timestamp": {"$gte": since}}
    ).to_list(length=500)

    total = len(records)

    # Questions asked today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_records = [r for r in records if r["timestamp"] >= today_start]
    today_count = len(today_records)

    # Build cluster summary
    clusters = []
    if total >= 5:  # Need at least 5 questions to cluster meaningfully
        clusters = _cluster_questions(records)

    # Recent Activity
    recent_docs = []
    
    # We want the last 5 questions, sorted by timestamp desc
    last_5 = await analytics_col().find(
        {"user_id": user_id}
    ).sort("timestamp", -1).limit(5).to_list(length=5)

    for r in last_5:
        recent_docs.append({
            "id": str(r["_id"]),
            "question": r["question"],
            "document_filename": r.get("document_filename", "Unknown Doc"),
            "timestamp": r["timestamp"],
            "citation_count": len(r.get("sources", []))
        })

    # ── Questions by Day (Last 7 Days) ───────────────────────────────────────
    days_data = []
    for i in range(6, -1, -1):
        dt = (datetime.utcnow() - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = dt + timedelta(days=1)
        count = len([r for r in records if dt <= r["timestamp"] < end_dt])
        days_data.append({
            "day": dt.strftime("%a"),
            "count": count,
            "isToday": i == 0
        })

    # ── Questions by Document ────────────────────────────────────────────────
    doc_counts = {}
    for r in records:
        doc_name = r.get("document_filename", "Unknown")
        doc_counts[doc_name] = doc_counts.get(doc_name, 0) + 1
    
    # Sort and take top 5
    sorted_docs = sorted(doc_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    doc_breakdown = [{"name": name, "count": count} for name, count in sorted_docs]

    total_docs = await documents_col().count_documents({"user_id": user_id})

    return {
        "total_documents": total_docs,
        "total_questions": total,
        "questions_today": today_count,
        "daily_limit": settings.max_questions_per_day,
        "top_clusters": clusters,
        "storage_used_mb": 0.0,  # Will be filled by router
        "questions_by_day": days_data,
        "questions_by_document": doc_breakdown,
        "recent_activity": recent_docs
    }


def _cluster_questions(records: list[dict], n_clusters: int = 4) -> list[dict]:
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import normalize
    """
    KMeans clustering on question embeddings.
    Returns cluster summaries with sample questions.
    """
    # Filter records that have valid embeddings
    valid = [r for r in records if r.get("embedding") and len(r["embedding"]) > 0]
    if len(valid) < n_clusters:
        n_clusters = max(1, len(valid))

    vectors = np.array([r["embedding"] for r in valid], dtype=np.float32)
    vectors = normalize(vectors)  # normalize for cosine-like clustering

    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(vectors)

    clusters = []
    for cluster_id in range(n_clusters):
        cluster_records = [valid[i] for i, l in enumerate(labels) if l == cluster_id]
        questions = [r["question"] for r in cluster_records]

        clusters.append({
            "cluster_id": cluster_id,
            "label": _auto_label_cluster(questions),
            "question_count": len(questions),
            "sample_questions": questions[:3]
        })

    # Sort by size
    clusters.sort(key=lambda x: x["question_count"], reverse=True)
    return clusters


def _auto_label_cluster(questions: list[str]) -> str:
    """
    Simple heuristic label without calling LLM (free-tier safe).
    In production: call LLM once per cluster and cache the label.
    """
    text = " ".join(questions).lower()
    keywords = {
        "diagnosis": ["diagnos", "symptom", "condition", "disease"],
        "treatment": ["treat", "medication", "drug", "therapy", "dose"],
        "lab results": ["lab", "test", "result", "blood", "level", "value"],
        "procedures": ["procedure", "surgery", "operation", "perform"],
        "prognosis": ["prognos", "outlook", "survival", "recovery"],
        "dosage": ["dose", "dosage", "mg", "frequency", "how much"],
    }
    for label, kws in keywords.items():
        if any(kw in text for kw in kws):
            return label
    return "general queries"


async def count_questions_today(user_id: str) -> int:
    """Used by rate limiter before answering a question."""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    count = await analytics_col().count_documents({
        "user_id": user_id,
        "timestamp": {"$gte": today_start}
    })
    return count
