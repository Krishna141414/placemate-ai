"""`track_application`: create or update a student's application.

One row per student and company. Calling it again for the same company
updates that row instead of creating a duplicate.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.errors import AppError
from app.models import Application
from app.schemas import APPLICATION_STATUSES
from app.tools.catalog import get_catalog

_UNSET = object()


def track_application(
    db: Session,
    user_id: int,
    company_id: str,
    *,
    status: str | None = None,
    deadline: date | None | object = _UNSET,
    notes: str | None = None,
    commit: bool = True,
) -> tuple[Application, bool]:
    """Upsert an application. Returns (application, created)."""
    company = get_catalog().get(company_id)
    if status is not None and status not in APPLICATION_STATUSES:
        raise AppError(422, "invalid_status", f"Status must be one of: {', '.join(APPLICATION_STATUSES)}.")

    application = (
        db.query(Application).filter(Application.user_id == user_id, Application.company_id == company.id).one_or_none()
    )
    created = application is None
    if created:
        application = Application(
            user_id=user_id,
            company_id=company.id,
            company_name=company.name,
            role_title=company.role,
            status=status or "planned",
            deadline=company.apply_by if deadline is _UNSET else deadline,
            notes=notes or "",
        )
        db.add(application)
    else:
        if status is not None:
            application.status = status
        if deadline is not _UNSET:
            application.deadline = deadline
        if notes is not None:
            application.notes = notes

    if commit:
        db.commit()
        db.refresh(application)
    else:
        db.flush()
    return application, created


def get_own_application(db: Session, user_id: int, application_id: int) -> Application:
    application = db.get(Application, application_id)
    # Someone else's application is reported as missing, not forbidden.
    if application is None or application.user_id != user_id:
        raise AppError(404, "application_not_found", "That application does not exist.")
    return application


def list_applications(db: Session, user_id: int) -> list[Application]:
    rows = db.query(Application).filter(Application.user_id == user_id).all()
    # Soonest deadline first; rows without a deadline last.
    return sorted(rows, key=lambda a: (a.deadline is None, a.deadline or date.max, a.company_name.lower()))
