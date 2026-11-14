"""Seed and reset the demo data.

    python -m app.seed           # create demo accounts if they are missing
    python -m app.seed --reset   # wipe activity and restore the clean demo state
"""

from __future__ import annotations

import argparse
import json
import logging
import secrets
from datetime import date

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    AgentRun,
    Application,
    Conversation,
    Document,
    Event,
    Message,
    PrepPlan,
    StudentProfile,
    User,
)
from app.security.auth import ROLE_COORDINATOR, ROLE_STUDENT, hash_password

logger = logging.getLogger("placemate.seed")

DEMO_STUDENT_EMAIL = "student@placemate.demo"
DEMO_COORDINATOR_EMAIL = "coordinator@placemate.demo"
# Published demo credentials (README and login page). Not secrets.
DEMO_STUDENT_PASSWORD = "Student@123"
DEMO_COORDINATOR_PASSWORD = "Coord@123"

# Two tracker rows so the dashboard is not empty on first login.
DEMO_APPLICATIONS = [
    {"company_id": "tessera", "status": "applied", "notes": "Aptitude test on 4 December."},
    {"company_id": "quantaleaf", "status": "planned", "notes": "Revise window functions first."},
]


def _load_seed_file() -> dict:
    path = get_settings().data_dir / "students_seed.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _read_resume(filename: str | None) -> str | None:
    if not filename:
        return None
    path = get_settings().data_dir / "resumes" / filename
    return path.read_text(encoding="utf-8") if path.exists() else None


def _apply_profile(user: User, row: dict) -> None:
    profile = user.profile
    if profile is None:
        profile = StudentProfile()
        user.profile = profile
    profile.branch = row["branch"]
    profile.cgpa = row["cgpa"]
    profile.active_backlogs = row["active_backlogs"]
    profile.batch = row["batch"]
    profile.resume_text = _read_resume(row.get("resume_file"))


def _seed_demo_applications(db: Session, user: User) -> None:
    from app.tools.catalog import get_catalog

    catalog = get_catalog()
    for row in DEMO_APPLICATIONS:
        company = catalog.find(row["company_id"])
        if company is None:
            continue
        exists = (
            db.query(Application)
            .filter(Application.user_id == user.id, Application.company_id == company.id)
            .one_or_none()
        )
        if exists:
            continue
        db.add(
            Application(
                user_id=user.id,
                company_id=company.id,
                company_name=company.name,
                role_title=company.role,
                status=row["status"],
                deadline=company.apply_by if isinstance(company.apply_by, date) else None,
                notes=row["notes"],
            )
        )


def seed_demo_data(db: Session) -> dict[str, int]:
    """Create the demo accounts and profiles. Safe to run repeatedly."""
    data = _load_seed_file()
    created = 0

    coordinator_row = data["coordinator"]
    coordinator = db.query(User).filter(User.email == coordinator_row["email"]).one_or_none()
    if coordinator is None:
        db.add(
            User(
                email=coordinator_row["email"],
                name=coordinator_row["name"],
                role=ROLE_COORDINATOR,
                password_hash=hash_password(DEMO_COORDINATOR_PASSWORD),
            )
        )
        created += 1

    for row in data["students"]:
        user = db.query(User).filter(User.email == row["email"]).one_or_none()
        if user is None:
            # Only the demo student has a known password. The other students
            # exist to make analytics realistic and cannot be logged into.
            password = DEMO_STUDENT_PASSWORD if row["email"] == DEMO_STUDENT_EMAIL else secrets.token_urlsafe(24)
            user = User(
                email=row["email"],
                name=row["name"],
                role=ROLE_STUDENT,
                password_hash=hash_password(password),
            )
            _apply_profile(user, row)
            db.add(user)
            created += 1

    db.commit()

    demo = db.query(User).filter(User.email == DEMO_STUDENT_EMAIL).one_or_none()
    if demo is not None and created:
        _seed_demo_applications(db, demo)
        db.commit()

    total = db.query(User).count()
    logger.info("seed_complete", extra={"new_users": created, "users": total})
    return {"created": created, "users": total}


def reset_demo_data(db: Session) -> dict[str, int]:
    """Remove all activity and uploaded documents, then restore the demo state."""
    settings = get_settings()

    removed_uploads = 0
    for document in db.query(Document).filter(Document.source == "upload").all():
        stored = settings.upload_dir / document.filename
        if stored.exists():
            stored.unlink()
        db.delete(document)
        removed_uploads += 1

    for model in (Message, Conversation, PrepPlan, AgentRun, Application, Event):
        db.query(model).delete()
    db.commit()

    data = _load_seed_file()
    by_email = {row["email"]: row for row in data["students"]}
    for user in db.query(User).filter(User.role == ROLE_STUDENT).all():
        row = by_email.get(user.email)
        if row:
            _apply_profile(user, row)
    db.commit()

    seed_demo_data(db)
    demo = db.query(User).filter(User.email == DEMO_STUDENT_EMAIL).one_or_none()
    if demo is not None:
        _seed_demo_applications(db, demo)
        db.commit()

    logger.info("demo_reset", extra={"removed_uploads": removed_uploads})
    return {"removed_uploads": removed_uploads, "users": db.query(User).count()}


def main() -> None:
    from app.db import SessionLocal, init_db
    from app.logging_conf import configure_logging

    parser = argparse.ArgumentParser(description="Seed or reset PlaceMate demo data.")
    parser.add_argument("--reset", action="store_true", help="wipe activity and restore the clean demo state")
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(settings.log_dir)
    init_db(settings.db_url)
    with SessionLocal() as db:
        result = reset_demo_data(db) if args.reset else seed_demo_data(db)

    if args.reset:
        # Uploaded documents were removed, so the search index must be rebuilt.
        try:
            from app.rag.index import IndexStore

            with SessionLocal() as db:
                IndexStore.build(db)
        except ImportError:  # pragma: no cover - index module not present yet
            pass
    print(result)


if __name__ == "__main__":
    main()
