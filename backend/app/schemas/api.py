from datetime import datetime
from pydantic.networks import EmailStr
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


class QueryIn(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    session_id: str | None = None
    file_ids: list[str] = Field(default_factory=list, max_length=50)
    query_type: str = Field(default="qa", pattern="^(qa|summary|compare|risks|keywords|charts|actions|contract|invoice|meeting)$")
    top_k: int = Field(default=6, ge=1, le=20)


class Citation(BaseModel):
    number: int
    file_id: str
    file_name: str
    chunk_id: str
    location: str
    excerpt: str
    score: float


class QueryOut(BaseModel):
    session_id: str
    answer: str
    citations: list[Citation]
    confidence: str
    grounded: bool


class SearchHit(Citation):
    modality: str
