# 02. Middleware Pipeline & Request Lifecycle

> *"A middleware is the guardian of your application. It intercepts every incoming packet and outgoing response, enforcing security, distributed tracing, and resource limits before your route logic ever executes."*

---

## 1. The Onion Architecture of ASGI Middleware

In FastAPI (which inherits Starlette's middleware stack), middlewares wrap the application like layers of an onion. 

Every request passes through the middlewares from the outside in; every response travels back through them from the inside out:

```
[Inbound Client Request]
       │
       ▼
┌────────────────────────────────────────────────────────┐
│ 1. CORSMiddleware                                      │
│    (Checks Origin Header, rejects unauthorized domains)│
└──────────────────────┬─────────────────────────────────┘
                       │
                       ▼
┌────────────────────────────────────────────────────────┐
│ 2. SecurityHeadersMiddleware                           │
│    (Prepares HSTS, X-Frame-Options, CSP headers)       │
└──────────────────────┬─────────────────────────────────┘
                       │
                       ▼
┌────────────────────────────────────────────────────────┐
│ 3. CorrelationIdMiddleware                             │
│    (Injects UUID4 X-Correlation-ID for tracing)        │
└──────────────────────┬─────────────────────────────────┘
                       │
                       ▼
┌────────────────────────────────────────────────────────┐
│ 4. RequestSizeLimitMiddleware                          │
│    (Terminates payloads > 100MB to prevent OOM DoS)    │
└──────────────────────┬─────────────────────────────────┘
                       │
                       ▼
             [ FastAPI Route Handler ]
                       │
                       ▼
[Outbound Response flows back up through 4 ──► 3 ──► 2 ──► 1 ──► Client]
```

---

## 2. Writing Custom Middlewares with `BaseHTTPMiddleware`

Starlette provides `BaseHTTPMiddleware`, which allows you to intercept the request via `call_next(request)`:

```python
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response

class CustomLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Code executed BEFORE the route handler
        print(f"Incoming: {request.method} {request.url.path}")
        
        # 2. Pass request to next middleware or route handler
        response: Response = await call_next(request)
        
        # 3. Code executed AFTER the route handler (on the response)
        response.headers["X-Processed-By"] = "VeriDoc-Core"
        return response
```

---

## 3. The 4 Production Middlewares in VeriDoc Synapse

In [`rag-backend/app/main.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/main.py) and [`rag-backend/app/core/security_headers.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/core/security_headers.py), we enforce four critical production middlewares:

### 1. `SecurityHeadersMiddleware` (Healthcare Infosec)
```python
# rag-backend/app/core/security_headers.py
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        # Prevent Clickjacking (disallows rendering in iframes)
        response.headers["X-Frame-Options"] = "DENY"
        # Prevent MIME-type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        # Enforce HTTPS strictly for 1 year
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        # Cross-Site Scripting Protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response
```

---

### 2. `CorrelationIdMiddleware` (FDA 21 CFR Part 11 Audit Tracing)
Every log line in a clinical system must be traceable back to a specific request:
```python
# rag-backend/app/main.py
import uuid
from starlette.middleware.base import BaseHTTPMiddleware

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Read incoming correlation ID or generate a new UUID4
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response
```

---

### 3. `RequestSizeLimitMiddleware` (Preventing OOM DoS Attacks)
If an attacker or an uninformed user attempts to upload a 500MB video or massive file, Python would buffer the bytes into memory, instantly crashing a 512MB RAM container.
```python
# rag-backend/app/main.py
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100 MB Limit

class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_UPLOAD_SIZE:
            return JSONResponse(
                status_code=413,
                content={"detail": "Payload Too Large. Maximum allowed upload is 100MB."}
            )
        return await call_next(request)
```

---

### 4. `CORSMiddleware` (Strict Origin Protection)
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://nexus-tawny-seven-50.vercel.app",
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Correlation-ID"]
)
```

---

## 4. Middleware Execution Order Pitfalls

In FastAPI, **the order in which you call `app.add_middleware(...)` matters**:
- Middlewares are executed in **reverse order of registration** for the incoming request!
- Always add `CORSMiddleware` last so that it wraps around all other middlewares. This ensures that even if an inner middleware returns an error (such as a 413 Payload Too Large or a 500 Internal Server Error), CORS headers are still attached to the response, allowing the browser to read the error message properly.
