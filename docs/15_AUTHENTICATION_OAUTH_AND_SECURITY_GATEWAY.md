# 15. Authentication, OAuth & Security Gateway

## 1. Authentication Handshake & Cold-Start Warmup Sequence

```mermaid
sequenceDiagram
    autonumber
    actor User as Client Browser
    participant FE as veridoc-frontend (Next.js)
    participant API as rag-backend (FastAPI)
    participant Google as Google Identity Services
    participant DB as MongoDB Atlas (users_col)

    Note over User,API: Cold-Start Mitigation Ping
    User->>FE: Views /login or /register page
    FE->>API: GET /health (Background Ping)
    API-->>FE: 200 OK {"status": "ok", "version": "2.3.4"} (Awakened Container)

    alt Local Credentials
        User->>FE: Submits Email + Password
        FE->>API: POST /api/auth/login {"email", "password"}
        API->>DB: Query user by email
        DB-->>API: User Document
        API->>API: passlib.bcrypt.verify(password, hashed_password)
        API->>API: Issue JWT Access Token (HS256)
        API-->>FE: HTTP 200 {"access_token"}
        FE->>User: Route to /dashboard
    else Google OAuth 2.0
        User->>FE: Clicks "Sign in with Google"
        FE->>API: GET /api/auth/google
        API-->>FE: Redirect URL to accounts.google.com with State
        FE->>Google: Authenticate & Authorize Scopes
        Google-->>FE: Redirect /auth/callback?code=CODE&state=STATE
        FE->>API: GET /api/auth/google/callback?code=CODE&state=STATE
        API->>Google: Exchange code for id_token
        Google-->>API: User Profile
        API->>DB: Upsert user document
        API->>API: Issue JWT Access Token (HS256)
        API-->>FE: Redirect to /dashboard with JWT
    end
```

---

## 2. Security Middleware Specifications (`core/security_headers.py`)

- `X-Content-Type-Options`: `nosniff` (Prevents MIME-sniffing).
- `X-Frame-Options`: `DENY` (Prevents clickjacking attacks).
- `Strict-Transport-Security`: `max-age=31536000; includeSubDomains` (Enforces HTTPS).
- `Content-Security-Policy`: Restricts scripts, styles, and frames to trusted origins.
