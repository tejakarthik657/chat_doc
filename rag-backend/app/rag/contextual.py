"""
Contextual Retrieval
─────────────────────
Anthropic's technique: before embedding a chunk, prepend a short LLM-generated
context blurb describing what the chunk is about and where it sits in the document.

Example:
  Raw chunk:  "Dr. XYZ | Associate Professor | 12 years"
  Contextual: "[Context: CSE Faculty list from 2024 NAAC disclosure, listing Associate Professors]\nDr. XYZ | Associate Professor | 12 years"

This significantly improves retrieval because vectors are computed over richer text.
"""
import asyncio
from app.core.config import get_settings

settings = get_settings()


def _build_context_prompt(source_name: str, chunk_text: str) -> str:
    """Build a prompt for Groq to generate a context description for a chunk."""
    return (
        "Given the document source name and a text excerpt below, write ONE short sentence "
        "(max 30 words) describing what this excerpt is about and where it appears in the document. "
        "Do not repeat the text verbatim. Do not add opinions. Just describe the content.\n\n"
        f"Document: {source_name}\n"
        f"Excerpt:\n{chunk_text[:500]}\n\n"
        "Context description:"
    )


def _generate_context_batch_local(source_name: str, chunk_texts: list[str]) -> list[str]:
    """Generate context descriptions locally using TinyLlama."""
    from app.core.llm import generate_raw
    contexts = []
    for ct in chunk_texts:
        prompt = _build_context_prompt(source_name, ct)
        full_prompt = f"<|system|>\nYou are a metadata context generator. Describe the excerpt in 1 short sentence.</s>\n<|user|>\n{prompt}</s>\n<|assistant|>\n"
        try:
            res = generate_raw(full_prompt)
            contexts.append(res)
        except Exception:
            contexts.append("")
    return contexts


def generate_context_batch(source_name: str, chunk_texts: list[str],
                            max_parallel: int = 5) -> list[str]:
    """
    Generate context descriptions for a batch of chunks using Groq.
    Returns a list of context strings (same length as chunk_texts).
    Falls back to local LLM when Groq is unavailable.
    """
    if not chunk_texts:
        return []

    api_key = settings.groq_api_key
    if not api_key:
        return _generate_context_batch_local(source_name, chunk_texts)

    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        contexts = []

        for i in range(0, len(chunk_texts), max_parallel):
            batch = chunk_texts[i:i + max_parallel]
            prompts = [_build_context_prompt(source_name, ct) for ct in batch]

            try:
                responses = client.chat.completions.create(
                    model="qwen/qwen3.8-27b",
                    messages=[
                        {
                            "role": "user",
                            "content": "\n\n---\n\n".join(
                                f"[Chunk {j+1}]\n{p}" for j, p in enumerate(prompts)
                            )
                        }
                    ],
                    temperature=0.1,
                    max_tokens=200,
                )
                reply = responses.choices[0].message.content.strip()

                # Parse multi-chunk response (one line per chunk)
                lines = [l.strip() for l in reply.split("\n") if l.strip() and not l.strip().startswith("[Chunk")]
                if len(lines) >= len(batch):
                    contexts.extend(lines[:len(batch)])
                else:
                    # Fallback: use first line for all
                    first = lines[0] if lines else ""
                    contexts.extend([first] * len(batch))
            except Exception as e:
                print(f"[Contextual] [WARNING] Groq batch generation failed: {e}. Falling back to local.")
                # Fallback to local LLM for this batch on Groq error
                local_res = _generate_context_batch_local(source_name, batch)
                contexts.extend(local_res)

        # Pad if needed
        while len(contexts) < len(chunk_texts):
            contexts.append("")
        return contexts[:len(chunk_texts)]

    except Exception as e:
        print(f"[Contextual] [WARNING] Groq contextual generator failed: {e}. Falling back to local.")
        return _generate_context_batch_local(source_name, chunk_texts)


def apply_contextual_prefix(chunk: dict, context: str) -> str:
    """Prepend context description to chunk text for embedding."""
    if context and len(context.strip()) > 5:
        return f"[Context: {context.strip()}]\n{chunk['text']}"
    return chunk["text"]


# ── Falls back if Groq unavailable or batching fails
def generate_context_sync(source_name: str, chunk_text: str) -> str:
    """Generate a single context description. Returns empty string on failure."""
    try:
        api_key = settings.groq_api_key
        if not api_key:
            from app.core.llm import generate_raw
            prompt = _build_context_prompt(source_name, chunk_text)
            full_prompt = f"<|system|>\nYou are a metadata context generator. Describe the excerpt in 1 short sentence.</s>\n<|user|>\n{prompt}</s>\n<|assistant|>\n"
            return generate_raw(full_prompt)

        from groq import Groq
        client = Groq(api_key=api_key)
        prompt = _build_context_prompt(source_name, chunk_text)
        response = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=60,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        try:
            from app.core.llm import generate_raw
            prompt = _build_context_prompt(source_name, chunk_text)
            full_prompt = f"<|system|>\nYou are a metadata context generator. Describe the excerpt in 1 short sentence.</s>\n<|user|>\n{prompt}</s>\n<|assistant|>\n"
            return generate_raw(full_prompt)
        except Exception:
            return ""

