"""
LocalLLM: wraps CTransformers with TinyLlama GGUF.
Loaded ONCE at startup. CPU-only, no GPU required.

To download the model:
  mkdir -p models
  wget https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf -O models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf
"""
import os
from app.core.config import get_settings

settings = get_settings()

_llm = None

SYSTEM_PROMPT = """You are a document-grounded AI assistant.

Rules you MUST follow:
1. Answer ONLY using the provided document context below.
2. If the answer is not present in the context, say exactly:
   "I don't see this information in the uploaded documents."
3. Do NOT use any prior knowledge or make assumptions.
4. Cite the page number for every factual statement, like: [Page 4]
5. Be concise, precise, and factual. No filler sentences."""


def get_llm():
    """Lazy singleton — loads the GGUF model once."""
    global _llm
    if _llm is None:
        if not os.path.exists(settings.local_llm_path):
            raise RuntimeError(
                f"LLM model not found at {settings.local_llm_path}.\n"
                "Run: make download-model"
            )
        from ctransformers import AutoModelForCausalLM
        print(f"[LLM] Loading {settings.local_llm_path}...")
        _llm = AutoModelForCausalLM.from_pretrained(
            settings.local_llm_path,
            model_type=settings.local_llm_type,
            max_new_tokens=512,
            temperature=0.1,    # Low temp = factual, not creative
            context_length=2048
        )
        print("[LLM] Model ready.")
    return _llm


def build_prompt(context: str, memory: str, question: str) -> str:
    """Construct the full prompt with context injection."""
    memory_block = f"\nConversation Context:\n{memory}\n" if memory else ""

    return (
        f"<|system|>\n{SYSTEM_PROMPT}\n</s>\n"
        f"<|user|>\n"
        f"Document Context:\n{context}"
        f"{memory_block}"
        f"\nQuestion: {question}\n</s>\n"
        f"<|assistant|>\n"
    )


def generate(context: str, question: str, memory: str = "") -> str:
    """
    Run inference. Returns the model's answer string.
    Raises RuntimeError if LLM is unavailable.
    """
    llm = get_llm()
    prompt = build_prompt(context, memory, question)
    response = llm(prompt)
    return response.strip()
