from datetime import datetime
from pydantic.networks import EmailStr
from typing import Literal
from pydantic import BaseModel, Field


class Register(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class Login(BaseModel):
    email: EmailStr
    password: str


class Refresh(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    model_config = {"from_attributes": True}
    id: str
    email: str
    role: str


class FileOut(BaseModel):
    model_config = {"from_attributes": True}
    id: str
    name: str
    mime_type: str
    size: int
    status: str
    error: str | None
    tags: str
    created_at: datetime


class ShareIn(BaseModel):
    email: EmailStr


class QueryIn(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    session_id: str | None = None
    file_ids: list[str] = Field(default_factory=list, max_length=50)
    query_type: str = Field(default="qa", pattern="^(qa|summary|compare|risks|keywords|charts|actions|contract|invoice|meeting)$")
    top_k: int = Field(default=6, ge=1, le=20)
    response_language: Literal["auto", "en", "hi", "te"] = "auto"


class Citation(BaseModel):
    number: int
    file_id: str
    file_name: str
    chunk_id: str
    location: str
    excerpt: str
    score: float
    source_sha256: str | None = None
    available: bool = True
    source_state: str = "current"
    locator: dict = Field(default_factory=dict)
    quality: dict = Field(default_factory=dict)


class ClaimCheck(BaseModel):
    text: str
    citation_numbers: list[int]
    status: Literal["citation_checked", "blocked"]
    issues: list[str] = Field(default_factory=list)


class EvidenceAudit(BaseModel):
    status: Literal["source_excerpts", "citation_checked", "withheld", "insufficient"]
    abstained: bool
    checks: list[ClaimCheck] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class QueryOut(BaseModel):
    session_id: str
    answer: str
    citations: list[Citation]
    confidence: str
    grounded: bool
    audit: EvidenceAudit


class SearchHit(Citation):
    modality: str
