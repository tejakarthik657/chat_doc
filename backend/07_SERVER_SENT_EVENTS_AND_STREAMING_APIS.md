# 07. Server-Sent Events (SSE) & Streaming APIs

> *"In conversational AI, waiting 8 seconds for a complete JSON response feels broken. Streaming tokens word-by-word via Server-Sent Events gives users sub-second perceived latency and real-time interaction."*

---

## 1. What is Server-Sent Events (SSE)?

**Server-Sent Events (SSE)** is an HTTP/2 and HTTP/1.1 standard allowing a server to push an asynchronous, continuous stream of text chunks to a client over a single long-lived HTTP connection.

Unlike WebSockets (which require a separate bidirectional TCP protocol), SSE:
- Uses standard **HTTP/HTTPS (port 443)**, passing effortlessly through hospital firewalls and corporate proxies.
- Is natively supported by all modern browsers via the `EventSource` API.
- Reconnects automatically if a mobile connection or Wi-Fi drops.

---

## 2. Python Async Generators: The Engine of Streaming

In Python, an asynchronous generator is a function defined with `async def` that uses `yield` instead of `return`:

```python
import asyncio
from typing import AsyncGenerator

async def token_stream_generator() -> AsyncGenerator[str, None]:
    words = ["Based", "on", "Protocol", "Amendment", "3,", "Patient", "#104", "is", "ineligible."]
    for word in words:
        await asyncio.sleep(0.05) # Simulate LLM token arrival
        yield f"data: {word}\n\n" # The SSE wire format!
    yield "data: [DONE]\n\n"
```

### The SSE Wire Format Rule:
Every message sent over an SSE stream must start with `data: `, followed by your payload, and end with **two newlines (`\n\n`)**. The double-newline is the protocol signal that tells the client's browser to dispatch the event!

---

## 3. Streaming Responses in FastAPI with `StreamingResponse`

In [`rag-backend/app/api/routes/chat.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/api/routes/chat.py), we wrap our RAG engine in Starlette's `StreamingResponse`:

```python
# rag-backend/app/api/routes/chat.py
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from app.rag.engine import RAGEngine

router = APIRouter()

@router.post("/project/{project_id}")
async def stream_chat_turn(
    project_id: str,
    payload: ChatRequestSchema,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    rag_engine = RAGEngine()

    async def event_generator():
        try:
            # Connect to Groq LPU or Local Ollama stream
            async for chunk in rag_engine.stream_query(
                question=payload.question,
                project_id=project_id,
                privacy_mode=payload.privacy_mode,
                enable_live_db=payload.enable_live_db
            ):
                # 1. Detect if the client closed their browser tab!
                if await request.is_disconnected():
                    print("[SSE] Client disconnected; aborting token generation.")
                    break

                # 2. Yield formatted SSE event
                yield f"data: {chunk.model_dump_json()}\n\n"

            # 3. Emit termination signal
            yield "data: [DONE]\n\n"
        except Exception as e:
            error_payload = json.dumps({"error": str(e)})
            yield f"data: {error_payload}\n\n"

    # Return StreamingResponse with mandatory headers
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no" # Tells NGINX / Cloudflare not to buffer tokens!
        }
    )
```

---

## 4. Preventing Reverse Proxy Buffering (`X-Accel-Buffering: no`)

A frequent production bug when deploying streaming backends behind reverse proxies (like NGINX, Cloudflare, or Render) is **Response Buffering**:
- By default, NGINX tries to be helpful by buffering 4KB of data before sending it to the client to save network packets.
- If NGINX buffers your stream, the user waits 5 seconds seeing nothing, and then suddenly the entire answer appears all at once!
- Adding the header **`X-Accel-Buffering: no`** instructs NGINX and Cloudflare to flush every single byte to the client immediately.

---

## 5. Handling Client Disconnects (Cost & CPU Conservation)

If a user asks a complex question and then immediately closes their laptop or navigates to another page, you must not continue generating tokens on Groq or running cross-encoders on CPU.

We check client socket liveness via:
```python
if await request.is_disconnected():
    # Abort the LLM generator immediately!
    break
```
This single check saves thousands of wasted API tokens and frees the backend event loop instantly.
