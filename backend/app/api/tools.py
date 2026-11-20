"""Deterministic tools: eligibility and resume match."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import AppError
from app.models import StudentProfile, User
from app.schemas import EligibilityAllOut, EligibilityOut, EligibilityRequest, ResumeMatchOut, ResumeMatchRequest
from app.security.auth import require_student
from app.security.uploads import read_limited, validate_bytes
from app.services import events
from app.tools.catalog import get_catalog
from app.tools.eligibility import StudentProfileData, check_all, check_eligibility
from app.tools.resume import match_resume

router = APIRouter(prefix="/api/tools", tags=["tools"])

RESUME_MAX_BYTES = 2 * 1024 * 1024


@router.post("/eligibility", response_model=EligibilityOut, summary="Check the student's eligibility for one company")
def eligibility(body: EligibilityRequest, user: User = Depends(require_student), db: Session = Depends(get_db)) -> EligibilityOut:
    company = get_catalog().get(body.company_id)
    result = check_eligibility(StudentProfileData.from_model(user.profile), company)
    events.log_event(
        db, events.ELIGIBILITY, user.id, company_id=company.id, eligible=result.eligible, failed=[c.name for c in result.failed]
    )
    return EligibilityOut(**result.to_dict())


@router.post("/eligibility/all", response_model=EligibilityAllOut, summary="Check eligibility for every company")
def eligibility_all(user: User = Depends(require_student), db: Session = Depends(get_db)) -> EligibilityAllOut:
    results = check_all(StudentProfileData.from_model(user.profile), get_catalog().all())
    eligible = sum(result.eligible for result in results)
    events.log_event(db, events.ELIGIBILITY, user.id, company_id="all", eligible=eligible, total=len(results))
    return EligibilityAllOut(eligible_count=eligible, total=len(results), results=[EligibilityOut(**r.to_dict()) for r in results])


@router.post("/resume-match", response_model=ResumeMatchOut, summary="Match a resume to a company's job description")
def resume_match(body: ResumeMatchRequest, user: User = Depends(require_student), db: Session = Depends(get_db)) -> ResumeMatchOut:
    company = get_catalog().get(body.company_id)
    resume = body.resume_text if body.resume_text and body.resume_text.strip() else None
    if resume is None:
        resume = user.profile.resume_text if user.profile else None
    if not resume or len(resume.strip()) < 40:
        raise AppError(400, "no_resume", "Paste your resume (at least a few lines) or save one to your profile first.")

    result = match_resume(resume, company)

    if body.save_to_profile and body.resume_text:
        profile = db.get(StudentProfile, user.id) or StudentProfile(user_id=user.id)
        profile.resume_text = body.resume_text
        db.add(profile)
        db.commit()

    # Scores and counts only. Resume text never goes into the event log.
    events.log_event(
        db, events.RESUME_MATCH, user.id, company_id=company.id, match_pct=result.match_pct, redacted=result.redaction["counts"]
    )
    return ResumeMatchOut(**result.to_dict())


@router.get("/resume", summary="The student's own saved resume text")
def own_resume(user: User = Depends(require_student)) -> dict:
    text = user.profile.resume_text if user.profile else None
    return {"text": text or "", "has_resume": bool(text)}


@router.post("/resume-extract", summary="Read the text of an uploaded resume (.txt, .md or .pdf)")
async def resume_extract(file: UploadFile = File(...), _user: User = Depends(require_student)) -> dict:
    data = await read_limited(file, RESUME_MAX_BYTES)
    upload = validate_bytes(file.filename or "resume", data, max_bytes=RESUME_MAX_BYTES)
    return {"filename": upload.safe_name, "text": upload.text[:20000], "characters": len(upload.text)}
