# 16. API Specification & REST Endpoints

## 1. REST Endpoints Overview

| Method | Route Path | Description | Access Scope |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Basic service liveness probe | Public |
| `POST` | `/api/auth/register` | Register new user account | Public |
| `POST` | `/api/auth/login` | Authenticate and obtain JWT access token | Public |
| `GET` | `/api/auth/google` | Initiate Google OAuth 2.0 flow | Public |
| `GET` | `/api/auth/google/callback` | Exchange OAuth code for JWT session | Public |
| `POST` | `/api/documents/upload` | Upload PDF file and dispatch ingestion | Authenticated |
| `GET` | `/api/documents` | List user's indexed documents | Authenticated |
| `GET` | `/api/documents/{doc_id}` | Fetch document metadata & summary | Authenticated |
| `POST` | `/api/projects` | Create autonomous web crawling workspace | Authenticated |
| `GET` | `/api/projects` | List user's project workspaces | Authenticated |
| `GET` | `/api/projects/{project_id}`| Get crawl status, metrics, and page counts | Authenticated |
| `POST` | `/api/chat/general` | Query Open Global Knowledge Base | Authenticated |
| `POST` | `/api/chat/{doc_id}` | Query single document RAG engine | Authenticated |
| `POST` | `/api/chat/project/{proj_id}`| Query multi-document project knowledge base | Authenticated |
| `GET` | `/api/chat/{doc_id}/history` | Fetch message history & citations | Authenticated |
| `DELETE`| `/api/chat/{doc_id}/memory` | Reset conversation memory buffer | Authenticated |
| `POST` | `/api/features/truth-lattice`| Run adversarial cross-model audit | Authenticated |
| `POST` | `/api/features/execute-code` | Execute Python script in sandbox | Authenticated |

---

## 2. Core Request & Response Contracts (`models/schemas.py`)

### `ChatResponse` Contract
```json
{
  "answer": "## Executive Overview\n\nThe Department of CSE...",
  "sources": [
    {
      "page": 1,
      "chunk_id": "doc_6722_c4",
      "snippet": "Highest Package: 31 LPA...",
      "source_name": "KITSW Alumni Network",
      "url": "https://kitsw.ac.in/funds"
    }
  ],
  "grounded": true,
  "doc_id": "6ae305868d044a0b1ca8f528",
  "timestamp": "2026-10-31T23:30:00.000Z",
  "support_label": "supported",
  "support_confidence": 0.98,
  "evidence_trace": [
    {
      "chunk_id": "doc_6722_c4",
      "score": 0.892,
      "source": "KITSW Alumni Network",
      "snippet": "Placement Statistics 2023-2024..."
    }
  ],
  "mode": "standard"
}
```
