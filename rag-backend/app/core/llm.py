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

SYSTEM_PROMPT = """You are a helpful document assistant, similar to ChatGPT.

Your goal: Answer questions about the provided document in a natural, conversational way.

Guidelines:
1. Answer based on the document context provided.
2. Be conversational and helpful—write like you're explaining to a friend.
3. Synthesize information across the document to give complete, useful answers.
4. If a question isn't directly answered in the document, say so naturally: "The document doesn't specifically mention this, but based on [related info], ..."
5. Cite page numbers when relevant, but don't overdo it: [Page 2] only for key claims.
6. Use clear formatting (short paragraphs, bullets if helpful) to make answers easy to read.
7. Ask clarifying follow-ups if the question is ambiguous.
8. Be confident but honest—don't make up information."""


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
            temperature=0.6,    # Balanced: factual but natural & conversational
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


def generate_raw(prompt: str) -> str:
    """
    Run raw prompt inference on the local LLM.
    """
    llm = get_llm()
    response = llm(prompt)
    return response.strip()

