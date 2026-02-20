# RAG Document Assistant — Backend

> Source-grounded document Q&A. No hallucinations. $0/month.

## Architecture

```
FastAPI
├── Auth (JWT)
├── Document Ingestion  →  PyMuPDF → Chunks → Embeddings → FAISS
├── RAG Query Engine    →  FAISS → Filter → Memory → TinyLlama
├── Analytics Engine    →  KMeans clustering on question embeddings
└── Guardrails          →  Similarity threshold → refuse, not hallucinate
```

**Stack:** FastAPI · PyMuPDF · sentence-transformers · FAISS-cpu · TinyLlama GGUF · MongoDB Atlas

---

## Quick Start

### 1. Setup environment

```bash
make setup
```

This creates a virtualenv, installs deps, and copies `.env.example` → `.env`.

### 2. Configure `.env`

Edit `.env` and set your MongoDB Atlas URL:

```
MONGODB_URL=mongodb+srv://<user>:<password>@cluster0.xxxxx.mongodb.net/...
```

Get a free MongoDB Atlas M0 cluster at https://cloud.mongodb.com

### 3. Download the LLM

```bash
make download-model
```

Downloads `tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf` (~700MB) into `models/`.

### 4. Run dev server

```bash
make dev
```

API is live at `http://localhost:8000`
Docs at `http://localhost:8000/docs`

**Troubleshooting CORS / 500 errors:** Use `make dev` (no reload). Avoid `make dev-reload` when debugging auth—reload restarts the server on file changes and can kill requests mid-flight, causing CORS-like failures.

---

## API Reference

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Create account |
| POST | `/api/auth/login` | Get JWT token |
| GET | `/api/auth/me` | Current user info |

### Documents
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/documents/upload` | Upload PDF (ingests in background) |
| GET | `/api/documents/` | List user's documents |
| GET | `/api/documents/{doc_id}` | Get document status |
| DELETE | `/api/documents/{doc_id}` | Delete document + index |

### Chat
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat/{doc_id}` | Ask a question |
| GET | `/api/chat/{doc_id}/history` | Get chat history |
| DELETE | `/api/chat/{doc_id}/memory` | Reset conversation memory |

### Analytics
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/analytics/` | Usage stats + topic clusters |

---

## Example: Ask a question

```bash
# 1. Register
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"password123"}' \
  | jq -r .access_token)

# 2. Upload PDF
DOC_ID=$(curl -s -X POST http://localhost:8000/api/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@./my_document.pdf" \
  | jq -r .id)

# 3. Wait for processing (poll status)
curl http://localhost:8000/api/documents/$DOC_ID \
  -H "Authorization: Bearer $TOKEN"

# 4. Ask a question
curl -X POST http://localhost:8000/api/chat/$DOC_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the recommended treatment?"}'
```

### Example response

```json
{
  "answer": "The recommended treatment includes ACE inhibitors and lifestyle modifications. [Page 4]",
  "sources": [
    {"page": 4, "chunk_id": "abc123", "snippet": "Treatment includes ACE inhibitors..."}
  ],
  "grounded": true,
  "doc_id": "...",
  "timestamp": "2024-01-15T10:30:00"
}
```

If the answer isn't in the document:

```json
{
  "answer": "I don't see this information in the uploaded documents.",
  "sources": [],
  "grounded": false
}
```

---

## Free-Tier Limits (configurable in `.env`)

| Limit | Default |
|-------|---------|
| Storage per user | 50 MB |
| Max documents | 5 |
| Questions per day | 50 |

---

## Deployment (Render.com — Free)

1. Push to GitHub
2. Create new **Web Service** on Render
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables from `.env`
6. Add a persistent disk (`/app/storage` + `/app/models`)

> ⚠️ TinyLlama requires ~1GB RAM. Render's free tier (512MB) may be tight.
> Upgrade to $7/month Starter plan for comfortable operation.

## Docker

```bash
make docker-build
make docker-run
```

---

## Project Structure

```
rag-backend/
├── app/
│   ├── main.py                  # FastAPI app + lifespan
│   ├── core/
│   │   ├── config.py            # Settings (env vars)
│   │   ├── security.py          # JWT auth
│   │   ├── embeddings.py        # FAISS + embedding model
│   │   └── llm.py               # TinyLlama wrapper + system prompt
│   ├── db/
│   │   └── mongodb.py           # Async MongoDB connection
│   ├── models/
│   │   └── schemas.py           # Pydantic models
│   ├── ingestion/
│   │   └── pipeline.py          # PDF → chunks → FAISS
│   ├── rag/
│   │   └── engine.py            # Full RAG query pipeline
│   ├── analytics/
│   │   └── engine.py            # KMeans clustering
│   └── api/routes/
│       ├── auth.py
│       ├── documents.py
│       ├── chat.py
│       └── analytics.py
├── tests/
│   └── test_backend.py
├── storage/                     # Runtime: uploads + FAISS indexes
├── models/                      # TinyLlama GGUF file
├── requirements.txt
├── Dockerfile
├── Makefile
└── .env.example
```
