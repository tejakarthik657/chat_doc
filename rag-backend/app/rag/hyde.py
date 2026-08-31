"""
HyDE — Hypothetical Document Embeddings
────────────────────────────────────────
Gao et al., 2022 (https://arxiv.org/abs/2212.10496)

The Problem:
  Short user questions often embed poorly because their vector
  doesn't resemble the long, detail-rich chunks in the index.
  Example: "What's the dose?" vs a chunk saying "The recommended
  dosage of metformin is 500mg twice daily with meals."

  The question vector and answer vector live in very different
  parts of the embedding space → poor retrieval.

The Fix (HyDE):
  1. Use the LLM to generate a FAKE plausible answer to the question.
  2. Embed the FAKE answer (not the question).
  3. Search FAISS with the fake-answer vector.

  The fake answer is written in the same style as real document chunks,
  so its embedding lands much closer to the real answer in vector space.

When to use HyDE:
  - Short / vague questions (< 8 words)
  - Questions with no obvious keywords for BM25
  - When pure FAISS retrieval returns low similarity scores

Cost: One extra local LLM call per query (cheap, ~0.5s on CPU).
Fallback: If HyDE generation fails → silently fall back to raw question.
"""
from groq import Groq
from app.core.config import get_settings

settings = get_settings()

# Short prompt that generates a document-style hypothetical answer.
# Kept minimal so TinyLlama can handle it on CPU without drift.
HYDE_PROMPT_TEMPLATE = """<|system|>
You are a document assistant. Write a SHORT, factual passage (2-3 sentences)
that would ANSWER the following question. Write as if you are an excerpt from
a technical document. Do not ask for clarification. Do not say you don't know.
Just write the most plausible answer passage.
</s>
<|user|>
Question: {question}
</s>
<|assistant|>
"""


def generate_hypothetical_document(question: str) -> str:
    """
    Generate a hypothetical answer passage using Groq (fast cloud LLM).
    Returns the fake passage, or the original question on failure.
    """
    try:
        api_key = settings.groq_api_key
        if not api_key:
            raise RuntimeError("GROQ_API_KEY not set in environment")

        client = Groq(api_key=api_key)
        
        # Simplified prompt for Groq
        system_msg = "You are a document assistant. Write a SHORT, factual passage (2-3 sentences) that would ANSWER the question. Write as if you are an excerpt from a technical document."
        
        response = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": f"Question: {question}"}
            ],
            temperature=0.5,
            max_tokens=150
        )
        
        hypothesis = response.choices[0].message.content.strip()

        # Sanity check — if output is garbage, fall back
        if len(hypothesis) < 20 or "?" in hypothesis[:30]:
            return question

        return hypothesis

    except Exception as e:
        print(f"[HyDE] Generation failed, falling back to raw question: {e}")
        return question


def should_use_hyde(question: str) -> bool:
    """
    Heuristic: use HyDE for short/vague questions that BM25 can't help with.
    Skip HyDE for long, keyword-rich questions (BM25 handles those well).
    """
    word_count = len(question.split())

    # Short question: high chance of poor direct embedding
    if word_count < 8:
        return True

    # Question contains mostly stop words / no domain terms
    domain_signals = [
        "dose", "dosage", "mg", "treatment", "diagnosis", "symptom",
        "procedure", "contraindication", "side effect", "medication",
        "section", "chapter", "according", "define", "explain", "describe"
    ]
    has_domain_signal = any(sig in question.lower() for sig in domain_signals)
    if not has_domain_signal and word_count < 12:
        return True

    return False
