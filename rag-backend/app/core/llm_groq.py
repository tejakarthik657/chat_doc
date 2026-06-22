"""
Groq LLM: FREE and ULTRA FAST cloud LLM inference.
Uses Llama 3.1 70B - better than GPT-3.5, completely free.

Get free API key from: https://console.groq.com/keys
Free tier: 30 requests/minute (more than enough for your app)
"""
from groq import Groq
from app.core.config import get_settings
from app.core.llm import generate as local_generate

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


def generate(context: str, question: str, memory: str = "") -> str:
    """
    Call Groq API for generation. ULTRA FAST and FREE.
    Returns the model's answer string.
    """
    settings = get_settings()
    api_key = settings.groq_api_key
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set in environment. Get free key from https://console.groq.com/keys")
    
    client = Groq(api_key=api_key)
    
    memory_block = f"\nConversation Context:\n{memory}\n" if memory else ""
    
    user_message = (
        f"Document Context:\n{context}"
        f"{memory_block}"
        f"\nQuestion: {question}"
    )
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",  # Updated model (Feb 2026)
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[Groq Error] {e}")
        print("[Groq] Falling back to local LLM.")
        return local_generate(context=context, question=question, memory=memory)
