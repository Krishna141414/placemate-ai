"""Health check and reference data."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.config import get_settings
from app.models import User
from app.schemas import CompanyOut
from app.security.auth import get_current_user
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
    settings = get_settings()
    return {"status": "ok", "version": settings.app_version, "env": settings.app_env}


@router.get("/api/meta/companies", response_model=list[CompanyOut], summary="Companies visiting campus")
def list_companies(_user: User = Depends(get_current_user)) -> list[CompanyOut]:
    return [company_out(company) for company in get_catalog().all()]


@router.get("/api/meta/ping", summary="Tightly rate-limited endpoint used by the Security page demo")
def ping(_user: User = Depends(get_current_user)) -> dict:
    return {"pong": True}
