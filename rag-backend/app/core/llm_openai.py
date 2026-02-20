"""
OpenAI LLM: Fast cloud-based replacement for local TinyLlama.
Provides 2-3 second responses instead of 20+ minutes on CPU.

Set OPENAI_API_KEY in .env to use this.
"""
import os
from openai import OpenAI

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
    Call OpenAI API for generation. Fast (2-3 seconds).
    Returns the model's answer string.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set in environment. Add it to .env file.")
    
    client = OpenAI(api_key=api_key)
    
    memory_block = f"\nConversation Context:\n{memory}\n" if memory else ""
    
    user_message = (
        f"Document Context:\n{context}"
        f"{memory_block}"
        f"\nQuestion: {question}"
    )
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Fast and cheap ($0.002/1K tokens)
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[OpenAI Error] {e}")
        raise RuntimeError(f"OpenAI API call failed: {e}")
