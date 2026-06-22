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
    password: str = Field(..., min_length=8, max_length=64)


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
    error_message: Optional[str] = None


class DocumentList(BaseModel):
    documents: List[DocumentOut]
    total_storage_mb: float
    storage_limit_mb: float


# ── Chat ──────────────────────────────────────────────────────────────────────

class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    strict_mode: bool = False
    scoped_sources: Optional[List[str]] = None


class SourceCitation(BaseModel):
    page: int
    chunk_id: str
    snippet: str  # first 200 chars of the chunk
    url: Optional[str] = None
    source_name: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceCitation]
    grounded: bool          # False if we refused due to low similarity
    doc_id: str
    timestamp: datetime
    support_label: Optional[str] = None
    support_confidence: Optional[float] = None
    support_snippet: Optional[str] = None


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


class RecentActivityItem(BaseModel):
    id: str
    question: str
    document_filename: str
    timestamp: datetime
    citation_count: int


class AnalyticsSummary(BaseModel):
    total_documents: int
    total_questions: int
    questions_today: int
    daily_limit: int
    top_clusters: List[ClusterSummary]
    storage_used_mb: float
    questions_by_day: List[dict] = []      # List of {"day": str, "count": int}
    questions_by_document: List[dict] = [] # List of {"name": str, "count": int}
    recent_activity: List[RecentActivityItem] = []


# ── Feature Intelligence ─────────────────────────────────────────────────────

class DocumentInsightsResponse(BaseModel):
    doc_id: str
    filename: str
    document_type: str
    document_type_confidence: float
    summary: str
    keyphrases: List[str]
    entities: dict
    readability_band: str
    outlier_sections: List[dict]
    suggested_questions: List[str]


class VerifyAnswerRequest(BaseModel):
    answer: str = Field(..., min_length=3, max_length=4000)


class VerifyAnswerResponse(BaseModel):
    label: str
    confidence: float
    best_snippet: str


class RewriteRequest(BaseModel):
    text: str = Field(..., min_length=3, max_length=8000)
    style: str = "simple"  # simple | professional


class RewriteResponse(BaseModel):
    rewritten_text: str


# ── Projects & Crawlers ──────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    website_url: str = Field(..., min_length=5, max_length=2000)
    max_pages: int = Field(50, ge=1, le=500)  # Safe default limit for safety
    use_dynamic_crawl: bool = Field(False)
    sitemap_url: Optional[str] = None
    login_url: Optional[str] = None
    login_username: Optional[str] = None
    login_password: Optional[str] = None


class ProjectOut(BaseModel):
    id: str
    name: str
    website_url: str
    created_at: datetime
    status: str  # "active" | "crawling" | "indexing" | "error"
    pages_crawled: int
    docs_found: int
    use_dynamic_crawl: bool = False
    sitemap_url: Optional[str] = None
    login_url: Optional[str] = None
    login_username: Optional[str] = None
    login_password: Optional[str] = None


class ProjectList(BaseModel):
    projects: List[ProjectOut]


class CrawlJobOut(BaseModel):
    id: str
    project_id: str
    status: str  # "pending" | "running" | "completed" | "failed"
    urls_found: int
    urls_processed: int
    pages_crawled: int = 0
    docs_found: int = 0
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

