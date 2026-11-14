"""Append-only event log, the source for analytics and the audit view."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import Event

# Event types
ASK = "ask"
ASK_REFUSED = "ask_refused"
ASK_BLOCKED = "ask_blocked"
ELIGIBILITY = "eligibility_check"
RESUME_MATCH = "resume_match"
AGENT_RUN = "agent_run"
AGENT_APPROVED = "agent_approved"
AGENT_REJECTED = "agent_rejected"
APPLICATION = "application_update"
UPLOAD = "document_upload"
UPLOAD_REJECTED = "document_upload_rejected"
DOCUMENT_DELETED = "document_deleted"
REINDEX = "reindex"
LOGIN = "login"
LOGIN_FAILED = "login_failed"


def log_event(db: Session, event_type: str, user_id: int | None = None, **payload: Any) -> Event:
    """Store one event. Payloads hold summaries only, never resume text."""
    event = Event(type=event_type, user_id=user_id, payload=payload)
    db.add(event)
    db.commit()
    return event
