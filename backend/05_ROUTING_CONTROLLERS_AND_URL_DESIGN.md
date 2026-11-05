# 05. Routing Controllers & URL Design

> *"In Express.js, you use `express.Router()`. In FastAPI, you use `APIRouter`. Organizing your routers cleanly prevents route precedence collisions, provides automatic OpenAPI documentation tags, and separates transport logic from business domains."*

---

## 1. Modular Router Architecture with `APIRouter`

In VeriDoc Synapse, we never write route definitions directly inside `main.py`. Instead, routes are organized into modular controller files inside [`rag-backend/app/api/routes/`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/api/routes/):

```
rag-backend/app/api/routes/
├── auth.py           # /api/auth/*       (Register, Login, Google OAuth)
├── chat.py           # /api/chat/*       (RAG Chat & Real-Time Streaming)
├── documents.py      # /api/documents/*  (Multipart PDF Uploads & Status)
├── mcp.py            # /api/mcp/*        (EHR DB Queries, Actions, JSON-RPC & SSE)
├── project.py        # /api/project/*    (Clinical Trial Workspaces)
├── features.py       # /api/features/*   (Canvas, Truth Lattice, Socratic Viva)
└── analytics.py      # /api/analytics/*  (Compliance Metrics & Latency)
```

### Defining a Router (`app/api/routes/documents.py`):
```python
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from app.core.security import get_current_user

# Create isolated router instance
router = APIRouter()

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(..., description="Multipart PDF file"),
    user: dict = Depends(get_current_user)
):
    ...
```

### Mounting Routers in `main.py`:
```python
# rag-backend/app/main.py
from fastapi import FastAPI
from app.api.routes import auth, chat, documents, mcp, project

app = FastAPI(...)

# Include modular sub-routers with prefixes and OpenAPI tags
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(chat.router, prefix="/api/chat", tags=["Conversational RAG"])
app.include_router(documents.router, prefix="/api/documents", tags=["Document Ingestion"])
app.include_router(mcp.router, prefix="/api/mcp", tags=["Model Context Protocol (MCP)"])
app.include_router(project.router, prefix="/api/project", tags=["Clinical Workspaces"])
```

---

## 2. URL Parameters, Query Strings & Multipart Files

FastAPI inspects Python function arguments to determine how data is delivered:

```python
@router.get("/search/{project_id}")
async def search_protocol_documents(
    project_id: str,                                    # 1. Path Parameter (in URL path)
    query: str,                                         # 2. Query Parameter (in ?query=...)
    limit: int = 10,                                    # 3. Optional Query Param with default
    page: int = 1,                                      # 4. Optional Query Param with default
    filter_type: Optional[str] = None,                  # 5. Nullable Query Param
    current_user: dict = Depends(get_current_user)      # 6. Injected Dependency
):
    ...
```

### Handling Multipart Form Uploads with `UploadFile`:
Unlike Express where you need `multer`, FastAPI natively handles multipart streaming with `UploadFile`:
```python
@router.post("/upload")
async def handle_pdf_upload(file: UploadFile = File(...)):
    # 1. Inspect file metadata without buffering
    filename = file.filename
    content_type = file.content_type
    
    # 2. Stream directly to encrypted disk storage
    file_path = f"./storage/{uuid.uuid4()}_{filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {"filename": filename, "saved_path": file_path}
```

---

## 3. The Route Masking War Story: Static vs. Wildcard Paths

A classic bug in FastAPI and Starlette is **Route Order Precedence**:
FastAPI matches incoming requests against routes in the exact order they are registered.

### The Bug We Faced in Production:
```python
# THE FATAL MISTAKE: Dynamic wildcard declared first!
@router.get("/{doc_id}")
async def get_document_by_id(doc_id: str):
    return await find_doc_in_mongo(doc_id)

@router.get("/general")
async def get_general_chat_history():
    return await fetch_general_chat()
```
When a client requested `GET /api/chat/general`:
1. FastAPI matched the first route: `/{doc_id}`.
2. It assigned `doc_id = "general"`.
3. It attempted to parse `"general"` as a MongoDB `ObjectId`, throwing an `HTTP 422 Unprocessable Entity` or `404 Not Found`!
4. The `/general` route was completely unreachable.

### The Golden Architectural Rule:
**Always declare all static, explicit routes BEFORE dynamic parameterized wildcard routes!**

```python
# THE CORRECT ARCHITECTURE:
@router.get("/general")
async def get_general_chat_history():
    return await fetch_general_chat()

@router.get("/{doc_id}")
async def get_document_by_id(doc_id: str):
    return await find_doc_in_mongo(doc_id)
```
Now `/general` matches cleanly, and any other path falls through to `/{doc_id}`.
