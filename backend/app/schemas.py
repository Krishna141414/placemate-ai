"""Request and response models (Pydantic).

Request models set explicit length and range limits, so oversized or
malformed input is rejected with a 422 before any logic runs.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

EMAIL_PATTERN = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
SLUG_PATTERN = r"^[a-z0-9][a-z0-9_-]{0,59}$"

APPLICATION_STATUSES = ("planned", "applied", "online_test", "interview", "offer", "rejected")
ApplicationStatus = Literal["planned", "applied", "online_test", "interview", "offer", "rejected"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# --- Auth -----------------------------------------------------------------


class LoginRequest(StrictModel):
    email: str = Field(min_length=3, max_length=254, pattern=EMAIL_PATTERN)
    password: str = Field(min_length=1, max_length=128)


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    branch: str | None = None
    cgpa: float | None = None
    active_backlogs: int | None = None
    batch: int | None = None
    has_resume: bool = False


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    role: str
    profile: ProfileOut | None = None


class ProfileUpdate(StrictModel):
    branch: str | None = Field(default=None, min_length=2, max_length=20)
    cgpa: float | None = Field(default=None, ge=0, le=10)
    active_backlogs: int | None = Field(default=None, ge=0, le=60)
    batch: int | None = Field(default=None, ge=2000, le=2100)
    resume_text: str | None = Field(default=None, max_length=20000)


# --- Companies ------------------------------------------------------------


class CompanyOut(BaseModel):
    id: str
    name: str
    role: str
    ctc_label: str
    category: str
    min_cgpa: float
    max_active_backlogs: int
    allowed_branches: list[str]
    batch: int
    required_skills: list[str]
    preferred_skills: list[str]
    rounds: list[str]
    apply_by: date | None = None


# --- Ask (RAG) ------------------------------------------------------------


class AskRequest(StrictModel):
    question: str = Field(min_length=1, max_length=2000)
    conversation_id: int | None = Field(default=None, ge=1)
    mode: Literal["final", "baseline"] = "final"

    @field_validator("question")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Question cannot be empty.")
        return value


class SourceOut(BaseModel):
    n: int
    doc_key: str
    title: str
    doc_type: str
    section: str
    snippet: str
    score: float


class StepOut(BaseModel):
    name: str
    label: str
    status: str
    detail: str = ""
    duration_ms: float = 0.0


class AnswerOut(BaseModel):
    conversation_id: int | None = None
    message_id: int | None = None
    question: str
    answer: str
    citations: list[int]
    sources: list[SourceOut]
    refused: bool
    blocked: bool
    block_reasons: list[str] = []
    provider: str
    model: str
    fallbacks: list[str] = []
    steps: list[StepOut]
    latency_ms: float
    mode: str


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    meta: dict[str, Any] = {}
    created_at: datetime


class ConversationOut(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageOut] = []


class ConversationSummary(BaseModel):
    id: int
    title: str
    updated_at: datetime
    message_count: int


# --- Tools ----------------------------------------------------------------


class EligibilityRequest(StrictModel):
    company_id: str = Field(pattern=SLUG_PATTERN)


class CriterionOut(BaseModel):
    name: str
    label: str
    passed: bool
    required: str
    actual: str
    reason: str


class EligibilityOut(BaseModel):
    company_id: str
    company_name: str
    role: str
    ctc_label: str
    category: str
    eligible: bool
    criteria: list[CriterionOut]
    summary: str


class EligibilityAllOut(BaseModel):
    eligible_count: int
    total: int
    results: list[EligibilityOut]


class ResumeMatchRequest(StrictModel):
    company_id: str = Field(pattern=SLUG_PATTERN)
    resume_text: str | None = Field(default=None, max_length=20000)
    save_to_profile: bool = False


class RedactionOut(BaseModel):
    counts: dict[str, int]
    total: int
    preview: str


class ResumeMatchOut(BaseModel):
    company_id: str
    company_name: str
    role: str
    match_pct: int
    skill_score: float
    semantic_score: float
    matched_required: list[str]
    missing_required: list[str]
    matched_preferred: list[str]
    missing_preferred: list[str]
    extra_skills: list[str]
    redaction: RedactionOut
    formula: str
    advice: list[str]


class ApplicationCreate(StrictModel):
    company_id: str = Field(pattern=SLUG_PATTERN)
    status: ApplicationStatus = "planned"
    deadline: date | None = None
    notes: str = Field(default="", max_length=1000)


class ApplicationUpdate(StrictModel):
    status: ApplicationStatus | None = None
    deadline: date | None = None
    notes: str | None = Field(default=None, max_length=1000)


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: str
    company_name: str
    role_title: str
    status: str
    deadline: date | None
    notes: str
    created_at: datetime
    updated_at: datetime


# --- Agent ----------------------------------------------------------------


class AgentRunRequest(StrictModel):
    company_id: str = Field(pattern=SLUG_PATTERN)
    # Demo control: make the named step fail once so recovery can be shown.
    demo_fault: Literal["match_resume", "retrieve_process", "retrieve_experiences", "build_plan"] | None = None


class AgentRunOut(BaseModel):
    id: int
    company_id: str
    goal: str
    status: str
    outcome: str
    state: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class PrepPlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: str
    title: str
    plan: dict[str, Any]
    agent_run_id: int | None
    created_at: datetime


# --- Coordinator ----------------------------------------------------------


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    doc_key: str
    title: str
    doc_type: str
    company_id: str | None
    source: str
    filename: str
    size_bytes: int
    chunk_count: int
    removed_lines: int
    created_at: datetime


class ReindexOut(BaseModel):
    documents: int
    chunks: int
    duration_ms: float


class UploadOut(BaseModel):
    document: DocumentOut
    reindex: ReindexOut
    removed_lines: list[str]


class EventOut(BaseModel):
    id: int
    type: str
    user: str | None
    summary: str
    created_at: datetime
