from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum


class Plan(str, Enum):
    FREE = "FREE"
    PRO = "PRO"


# ── Auth ──────────────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    email: str
    plan: Plan
    storage_used_mb: float
    created_at: datetime


# ── Documents ─────────────────────────────────────────────────────────────────

class DocumentOut(BaseModel):
    id: str
    filename: str
    size_mb: float
    page_count: int
    uploaded_at: datetime
    status: str  # "processing" | "ready" | "error"


class DocumentList(BaseModel):
    documents: List[DocumentOut]
    total_storage_mb: float
    storage_limit_mb: float


# ── Chat ──────────────────────────────────────────────────────────────────────

class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000)


class SourceCitation(BaseModel):
    page: int
    chunk_id: str
    snippet: str  # first 200 chars of the chunk


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceCitation]
    grounded: bool          # False if we refused due to low similarity
    doc_id: str
    timestamp: datetime


class ChatHistoryItem(BaseModel):
    question: str
    answer: str
    sources: List[SourceCitation]
    timestamp: datetime


# ── Analytics ─────────────────────────────────────────────────────────────────

class ClusterSummary(BaseModel):
    cluster_id: int
    label: str              # LLM-generated label for the cluster
    question_count: int
    sample_questions: List[str]


class AnalyticsSummary(BaseModel):
    total_questions: int
    questions_today: int
    daily_limit: int
    top_clusters: List[ClusterSummary]
    storage_used_mb: float
