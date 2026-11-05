# 03. Pydantic v2 Data Validation & Schemas

> *"In Express.js, you manually validate JSON payloads with libraries like Zod or Joi. In FastAPI, validation is built directly into Python types via Pydantic v2—compiled in Rust, enforcing strict runtime validation and automatic documentation."*

---

## 1. What is Pydantic v2 and Why Does It Matter?

**Pydantic** is the data validation backbone of FastAPI. With Pydantic v2, the core validation engine was completely rewritten in **Rust (`pydantic-core`)**, delivering a **5x to 20x performance improvement** over Pydantic v1.

When a client sends a JSON payload to a FastAPI route:
1. Pydantic parses the raw JSON bytes.
2. It validates every field against Python type annotations (`str`, `int`, `List[dict]`, `Optional[datetime]`).
3. It coerces compatible types (e.g., converting the string `"104"` into the integer `104`).
4. If validation succeeds, it hands a clean, typed Python object to your route function.
5. If validation fails, it automatically returns a structured **`HTTP 422 Unprocessable Entity`** error response detailing exactly which field failed and why.

---

## 2. Defining Schemas: The Core Concepts

```python
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime

class PatientScreeningCreate(BaseModel):
    # Required string with min/max length constraints
    name: str = Field(..., min_length=2, max_length=100, description="Full patient name")
    
    # Required integer with numerical bounds
    age: int = Field(..., ge=18, le=100, description="Patient age (must be adult >= 18)")
    
    # Float with positive value constraint
    serum_creatinine: float = Field(..., gt=0.0, description="Renal lab value in mg/dL")
    alt_enzyme: float = Field(..., gt=0.0, description="Liver enzyme value in U/L")
    
    # Optional field with default value
    trial_status: str = Field(default="Screening", description="Enrollment state")
    
    # Optional nested list
    prior_medications: Optional[List[str]] = Field(default_factory=list)
```

---

## 3. Concrete Schemas in VeriDoc Synapse (`app/models/schemas.py`)

In [`rag-backend/app/models/schemas.py`](file:///c:/Programming/Projects/01_Healthcare-MedTech/chat_base/rag-backend/app/models/schemas.py), we define schemas separating **Inbound Request DTOs** from **Outbound Response DTOs**:

### A. The Conversational Chat Request Schema
```python
# rag-backend/app/models/schemas.py
from pydantic import BaseModel, Field
from typing import Optional, Literal

class ChatRequestSchema(BaseModel):
    question: str = Field(..., min_length=1, description="Clinician inquiry or audit question")
    session_id: Optional[str] = Field(default=None, description="UUID session identifier")
    privacy_mode: Literal["fast_cloud", "air_gapped_local"] = Field(
        default="fast_cloud",
        description="Dual-privacy inference switch"
    )
    enable_live_db: bool = Field(
        default=True,
        description="Whether to allow Inbound MCP to query live hospital EHR tables"
    )
```

### B. The Compliance Audit Response Schema
```python
class AuditFinding(BaseModel):
    type: str = Field(..., description="E.g. Dosage Contradiction or Biomarker Mismatch")
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    section_or_source: str
    description: str
    regulatory_risk: str
    recommendation: str

class ComplianceAuditResponse(BaseModel):
    audit_id: str
    doc_id: str
    filename: str
    audit_status: str
    highest_severity: str
    alert_count: int
    summary: str
    findings: List[AuditFinding]
    action_dispatched: bool
    created_at: datetime
```

---

## 4. Custom Field & Model Validators (`@field_validator`)

Pydantic v2 provides powerful decorators for custom business rule validation:

```python
from pydantic import BaseModel, field_validator, model_validator

class ProtocolAmendmentCreate(BaseModel):
    protocol_code: str
    min_dosage_mg: float
    max_dosage_mg: float

    # Field-level validator
    @field_validator("protocol_code")
    @classmethod
    def validate_code_format(cls, v: str) -> str:
        if not v.startswith("PROTOCOL-"):
            raise ValueError("Protocol code must start with 'PROTOCOL-' prefix")
        return v.upper()

    # Model-level validator (evaluates cross-field rules)
    @model_validator(mode="after")
    def validate_dosage_bounds(self) -> "ProtocolAmendmentCreate":
        if self.max_dosage_mg < self.min_dosage_mg:
            raise ValueError("max_dosage_mg cannot be lower than min_dosage_mg!")
        return self
```

---

## 5. Serialization: `.model_dump()` vs `.model_dump_json()`

In Pydantic v1, you called `.dict()` and `.json()`. In Pydantic v2, these are replaced:

```python
audit_obj = ComplianceAuditResponse(...)

# Convert to Python Dictionary (for MongoDB insertion)
data_dict = audit_obj.model_dump()
await compliance_audits_col().insert_one(data_dict)

# Convert directly to fast JSON string (via Rust engine)
json_string = audit_obj.model_dump_json()
```

### Excluding None values or internal fields:
```python
clean_dict = audit_obj.model_dump(exclude_none=True, exclude={"internal_secret"})
```
This guarantees that internal backend flags never leak into external API responses.
