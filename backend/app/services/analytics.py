"""Coordinator analytics, computed from the event log and current profiles."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models import AgentRun, Event, PrepPlan, StudentProfile, User
from app.services import events
from app.tools.catalog import get_catalog
from app.tools.eligibility import StudentProfileData, check_eligibility

ASK_TYPES = (events.ASK, events.ASK_REFUSED, events.ASK_BLOCKED)


def _normalise_question(text: str) -> str:
    text = re.sub(r"[^\w\s]", " ", text.lower())
    return " ".join(text.split())


def _group_questions(rows: list[Event], limit: int) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    display: dict[str, str] = {}
    last_seen: dict[str, datetime] = {}
    for event in rows:
        question = (event.payload or {}).get("question", "")
        if not question:
            continue
        key = _normalise_question(question)
        counts[key] += 1
        display.setdefault(key, question)
        last_seen[key] = max(last_seen.get(key, event.created_at), event.created_at)
    return [
        {"question": display[key], "count": count, "last_asked": last_seen[key]}
        for key, count in counts.most_common(limit)
    ]


def eligibility_stats(db: Session) -> list[dict[str, Any]]:
    """For each company: how many students are eligible, and the most common blocker."""
    profiles = [
        StudentProfileData.from_model(profile)
        for profile in db.query(StudentProfile).join(User).filter(User.role == "student").all()
    ]
    stats = []
    for company in get_catalog().all():
        eligible = 0
        blockers: Counter[str] = Counter()
        for profile in profiles:
            result = check_eligibility(profile, company)
            if result.eligible:
                eligible += 1
            for criterion in result.failed:
                blockers[criterion.label] += 1
        top = blockers.most_common(1)
        stats.append(
            {
                "company_id": company.id,
                "company_name": company.name,
                "category": company.category,
                "eligible": eligible,
                "total": len(profiles),
                "top_blocker": top[0][0] if top else None,
                "top_blocker_count": top[0][1] if top else 0,
            }
        )
    return sorted(stats, key=lambda row: (-row["eligible"], row["company_name"]))


def summary(db: Session, days: int = 14) -> dict[str, Any]:
    ask_rows = db.query(Event).filter(Event.type.in_(ASK_TYPES)).order_by(Event.created_at).all()
    by_type = Counter(event.type for event in ask_rows)
    answered = [e for e in ask_rows if e.type == events.ASK]

    provider_counts: Counter[str] = Counter()
    latency: dict[str, list[float]] = defaultdict(list)
    for event in answered:
        provider = (event.payload or {}).get("provider") or "unknown"
        provider_counts[provider] += 1
        if (event.payload or {}).get("latency_ms") is not None:
            latency[provider].append(float(event.payload["latency_ms"]))

    topic_counts: Counter[str] = Counter(
        (event.payload or {}).get("top_title") for event in answered if (event.payload or {}).get("top_title")
    )

    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=days - 1)).date()
    per_day = {start + timedelta(days=i): {"answered": 0, "refused": 0, "blocked": 0} for i in range(days)}
    for event in ask_rows:
        created = event.created_at if event.created_at.tzinfo else event.created_at.replace(tzinfo=timezone.utc)
        day = created.date()
        if day in per_day:
            key = {events.ASK: "answered", events.ASK_REFUSED: "refused", events.ASK_BLOCKED: "blocked"}[event.type]
            per_day[day][key] += 1

    eligibility_events = db.query(Event).filter(Event.type == events.ELIGIBILITY).count()
    total_asks = len(ask_rows)
    return {
        "totals": {
            "questions": total_asks,
            "answered": by_type[events.ASK],
            "unanswered": by_type[events.ASK_REFUSED],
            "blocked": by_type[events.ASK_BLOCKED],
            "answer_rate": round(by_type[events.ASK] / total_asks, 3) if total_asks else None,
            "active_students": len({e.user_id for e in ask_rows if e.user_id}),
            "eligibility_checks": eligibility_events,
            "resume_matches": db.query(Event).filter(Event.type == events.RESUME_MATCH).count(),
            "agent_runs": db.query(AgentRun).count(),
            "plans_approved": db.query(PrepPlan).count(),
            "documents_uploaded": db.query(Event).filter(Event.type == events.UPLOAD).count(),
        },
        "top_questions": _group_questions(answered, 8),
        "unanswered_questions": _group_questions([e for e in ask_rows if e.type == events.ASK_REFUSED], 8),
        "blocked_attempts": [
            {"question": (e.payload or {}).get("question", ""), "reasons": (e.payload or {}).get("reasons", []), "at": e.created_at}
            for e in reversed([e for e in ask_rows if e.type == events.ASK_BLOCKED][-5:])
        ],
        "top_documents": [{"title": title, "count": count} for title, count in topic_counts.most_common(6)],
        "provider_usage": [
            {
                "provider": provider,
                "count": count,
                "avg_latency_ms": round(sum(latency[provider]) / len(latency[provider]), 1) if latency[provider] else None,
            }
            for provider, count in provider_counts.most_common()
        ],
        "questions_per_day": [{"date": day.isoformat(), **counts} for day, counts in per_day.items()],
        "eligibility": eligibility_stats(db),
    }


def describe_event(event: Event, email: str | None) -> str:
    """One readable line for the log table."""
    p = event.payload or {}
    descriptions = {
        events.ASK: lambda: f'Asked "{p.get("question", "")}" (answered by {p.get("provider", "?")})',
        events.ASK_REFUSED: lambda: f'Asked "{p.get("question", "")}" (not in the documents)',
        events.ASK_BLOCKED: lambda: f'Blocked message: {"; ".join(p.get("reasons", [])) or "injection pattern"}',
        events.ELIGIBILITY: lambda: f'Eligibility for {p.get("company_id")}: {"eligible" if p.get("eligible") else "not eligible"}',
        events.RESUME_MATCH: lambda: f'Resume match for {p.get("company_id")}: {p.get("match_pct")}%',
        events.AGENT_RUN: lambda: f'Started prep agent for {p.get("company_id")} (run {p.get("run_id")})',
        events.AGENT_APPROVED: lambda: f'Approved prep plan for {p.get("company_id")} (run {p.get("run_id")})',
        events.AGENT_REJECTED: lambda: f'Rejected prep plan for {p.get("company_id")} (run {p.get("run_id")})',
        events.APPLICATION: lambda: f'Application {p.get("action", "updated")} for {p.get("company_id")}: {p.get("status", "")}',
        events.UPLOAD: lambda: f'Uploaded "{p.get("filename")}" ({p.get("chunks", 0)} chunks)',
        events.UPLOAD_REJECTED: lambda: f'Rejected upload "{p.get("filename")}": {p.get("code")}',
        events.DOCUMENT_DELETED: lambda: f'Deleted document "{p.get("title")}"',
        events.REINDEX: lambda: f'Rebuilt the index ({p.get("chunks", 0)} chunks)',
        events.LOGIN: lambda: f'Logged in as {p.get("role", "")}',
        events.LOGIN_FAILED: lambda: "Failed login attempt",
    }
    describe = descriptions.get(event.type)
    return describe() if describe else event.type
