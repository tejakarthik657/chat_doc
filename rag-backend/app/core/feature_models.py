import re
from typing import Any

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.feature_extraction.text import TfidfVectorizer

from app.core.embeddings import embed_texts


DEFAULT_DOC_TYPES = [
    "resume or profile",
    "invoice or receipt",
    "report or whitepaper",
    "contract or legal agreement",
    "academic paper",
    "manual or technical guide",
    "policy or compliance document",
    "meeting notes or minutes",
    "research notes",
    "email or communication thread",
]


def _split_sentences(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in sentences if len(s.strip()) > 20]


def _split_paragraphs(text: str) -> list[str]:
    parts = re.split(r"\n\s*\n", text)
    cleaned = [p.strip() for p in parts if len(p.strip()) > 60]
    if cleaned:
        return cleaned
    return [s for s in _split_sentences(text) if len(s) > 60]


def extract_keyphrases(text: str, top_k: int = 12) -> list[str]:
    """
    Lightweight keyphrase extraction with TF-IDF n-grams.
    """
    sentences = _split_sentences(text)
    if not sentences:
        return []

    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 3),
        min_df=1,
        max_features=2000,
    )
    matrix = vectorizer.fit_transform(sentences)
    scores = np.asarray(matrix.sum(axis=0)).ravel()
    terms = np.array(vectorizer.get_feature_names_out())

    ranked_idx = np.argsort(scores)[::-1]
    phrases: list[str] = []
    for i in ranked_idx:
        phrase = terms[i].strip()
        if len(phrase) < 3:
            continue
        if any(phrase in existing for existing in phrases):
            continue
        phrases.append(phrase)
        if len(phrases) >= top_k:
            break
    return phrases


def classify_document_type(text: str, labels: list[str] | None = None) -> dict[str, Any]:
    """
    Semantic zero-shot style classification using MiniLM embeddings.
    """
    candidate_labels = labels or DEFAULT_DOC_TYPES
    probe = text[:4000] if text else ""
    if not probe:
        return {"label": "unknown", "confidence": 0.0, "scores": []}

    embeddings = embed_texts([probe] + candidate_labels)
    doc_vec = embeddings[0]
    label_vecs = embeddings[1:]

    scores = label_vecs @ doc_vec
    ranked = sorted(
        [
            {"label": label, "score": float(score)}
            for label, score in zip(candidate_labels, scores)
        ],
        key=lambda x: x["score"],
        reverse=True,
    )

    best = ranked[0] if ranked else {"label": "unknown", "score": 0.0}
    confidence = float((best["score"] + 1) / 2)  # normalize cosine-ish range to ~0..1
    return {
        "label": best["label"],
        "confidence": round(max(0.0, min(1.0, confidence)), 3),
        "scores": ranked[:5],
    }


def summarize_document(text: str, max_sentences: int = 5) -> str:
    """
    Embedding-based extractive summarization on CPU.
    """
    sentences = _split_sentences(text)
    if not sentences:
        return ""
    if len(sentences) <= max_sentences:
        return " ".join(sentences)

    sent_vecs = embed_texts(sentences)
    centroid = np.mean(sent_vecs, axis=0)
    scores = sent_vecs @ centroid

    top_idx = np.argsort(scores)[::-1][:max_sentences]
    ordered = sorted(top_idx.tolist())
    return " ".join(sentences[i] for i in ordered)


def extract_entities(text: str) -> dict[str, list[str]]:
    """
    Generic pattern entities that work for any domain.
    """
    patterns = {
        "emails": r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b",
        "urls": r"\bhttps?://[^\s]+",
        "dates": r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})\b",
        "percentages": r"\b\d+(?:\.\d+)?%\b",
        "currency": r"\b(?:USD|EUR|INR|GBP|\$|€|£)\s?\d+(?:,\d{3})*(?:\.\d{1,2})?\b",
        "ids": r"\b[A-Z]{2,}-?\d{3,}\b",
    }
    found: dict[str, list[str]] = {}
    for name, pattern in patterns.items():
        values = re.findall(pattern, text)
        unique = list(dict.fromkeys(values))[:15]
        found[name] = unique
    return found


def detect_outlier_sections(text: str, top_k: int = 3) -> list[dict[str, Any]]:
    """
    Isolation Forest over paragraph TF-IDF vectors to highlight unusual sections.
    """
    paragraphs = _split_paragraphs(text)
    if len(paragraphs) < 4:
        return []

    vectorizer = TfidfVectorizer(stop_words="english", max_features=1500)
    matrix = vectorizer.fit_transform(paragraphs)

    model = IsolationForest(contamination=0.2, random_state=42)
    model.fit(matrix.toarray())
    scores = -model.score_samples(matrix.toarray())

    ranked_idx = np.argsort(scores)[::-1][:top_k]
    outliers = []
    for i in ranked_idx:
        snippet = paragraphs[int(i)][:240].replace("\n", " ").strip()
        outliers.append(
            {
                "section_index": int(i),
                "anomaly_score": round(float(scores[int(i)]), 4),
                "snippet": snippet,
            }
        )
    return outliers


def verify_answer_support(answer: str, candidate_snippets: list[str]) -> dict[str, Any]:
    """
    Embedding-based support check for answer grounding.
    """
    if not answer.strip() or not candidate_snippets:
        return {"label": "insufficient", "confidence": 0.0, "best_snippet": ""}

    snippets = [s for s in candidate_snippets if s.strip()][:8]
    vectors = embed_texts([answer] + snippets)
    answer_vec = vectors[0]
    snippet_vecs = vectors[1:]

    sims = snippet_vecs @ answer_vec
    best_idx = int(np.argmax(sims))
    best_sim = float(sims[best_idx])

    if best_sim >= 0.62:
        label = "supported"
    elif best_sim >= 0.48:
        label = "partially_supported"
    else:
        label = "weak_support"

    return {
        "label": label,
        "confidence": round((best_sim + 1) / 2, 3),
        "best_snippet": snippets[best_idx][:280],
    }


def rewrite_plain_language(text: str, max_sentences: int = 4) -> str:
    """
    CPU-safe plain language rewrite via extractive + lexical simplification.
    """
    summary = summarize_document(text, max_sentences=max_sentences)
    if not summary:
        return ""

    replacements = {
        "utilize": "use",
        "approximately": "about",
        "demonstrate": "show",
        "methodology": "method",
        "subsequent": "next",
        "prior to": "before",
        "in order to": "to",
        "commence": "start",
        "terminate": "end",
        "therefore": "so",
    }
    rewritten = summary
    for src, dst in replacements.items():
        rewritten = re.sub(rf"\b{re.escape(src)}\b", dst, rewritten, flags=re.IGNORECASE)

    return rewritten
