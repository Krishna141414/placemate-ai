"""Health check and reference data."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from app.config import get_settings
from app.models import User
from app.schemas import CompanyOut
from app.security.auth import get_current_user
from app.security.pii import redact_pii
from app.tools.catalog import Company, get_catalog

router = APIRouter(tags=["meta"])


def company_out(company: Company) -> CompanyOut:
    return CompanyOut(
        id=company.id,
        name=company.name,
        role=company.role,
        ctc_label=company.ctc_label,
        category=company.category,
        min_cgpa=company.min_cgpa,
        max_active_backlogs=company.max_active_backlogs,
        allowed_branches=company.allowed_branches,
        batch=company.batch,
        required_skills=company.required_skills,
        preferred_skills=company.preferred_skills,
        rounds=company.rounds,
        apply_by=company.apply_by,
    )


@router.get("/health", summary="Liveness check")
def health() -> dict:
    from app.rag import index as index_module

    settings = get_settings()
    store = index_module._current
    return {
        "status": "ok",
        "version": settings.app_version,
        "env": settings.app_env,
        "index": {"ready": store is not None, "documents": store.document_count if store else 0, "chunks": len(store) if store else 0},
    }


@router.get("/api/meta/providers", summary="LLM providers and which one is configured")
def providers(_user: User = Depends(get_current_user)) -> list[dict]:
    from app.llm.router import provider_status

    return provider_status()


@router.get("/api/meta/companies", response_model=list[CompanyOut], summary="Companies visiting campus")
def list_companies(_user: User = Depends(get_current_user)) -> list[CompanyOut]:
    return [company_out(company) for company in get_catalog().all()]


@router.get("/api/meta/ping", summary="Tightly rate-limited endpoint used by the Security page demo")
def ping(_user: User = Depends(get_current_user)) -> dict:
    return {"pong": True}


class RedactPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=2000)


@router.post("/api/meta/redact-preview", summary="Show what PII redaction removes from a piece of text (nothing is stored or logged)")
def redact_preview(body: RedactPreviewRequest, _user: User = Depends(get_current_user)) -> dict:
    result = redact_pii(body.text)
    return {"text": result.text, "counts": result.counts, "total": result.total}
