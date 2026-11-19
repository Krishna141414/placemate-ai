"""Agent executor: runs the plan step by step.

    start_run()   checks the company, creates the run and its plan
    execute_run() runs the steps; a generator of events for the UI
    approve_run() / reject_run()  the human decision at the gate

Rules:
- Every tool call counts against a budget (`AGENT_MAX_STEPS`, default 8).
  Retries count too, so a run cannot loop forever.
- A failing step is retried up to `AGENT_STEP_RETRIES` times. If it still
  fails, a required step uses its fallback, an optional step is skipped, and
  a required step without a fallback fails the run.
- State is saved after every step, so a run can be inspected or shown again.
- The only write (the plan and the application) happens in `approve_run`.
"""

from __future__ import annotations

import copy
import logging
import time
from collections.abc import Iterator
from datetime import date
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.agent.planner import make_plan
from app.agent.state import AgentState, StepRecord
from app.agent.steps import FALLBACKS, STEP_FUNCTIONS, StepContext, StepError
from app.config import get_settings
from app.errors import AppError
from app.models import AgentRun, Application, PrepPlan, User
from app.services import events
from app.tools.applications import track_application
from app.tools.catalog import Company, get_catalog
from app.tools.eligibility import StudentProfileData, check_all

logger = logging.getLogger("placemate.agent")

FINAL_STATUSES = ("approved", "rejected", "completed", "failed")


def _save(db: Session, run: AgentRun, state: AgentState) -> None:
    run.state = copy.deepcopy(state.to_dict())
    flag_modified(run, "state")
    db.commit()


def run_out(run: AgentRun) -> dict[str, Any]:
    return {
        "id": run.id,
        "company_id": run.company_id,
        "goal": run.goal,
        "status": run.status,
        "outcome": run.outcome,
        "state": run.state,
        "created_at": run.created_at,
        "updated_at": run.updated_at,
    }


def start_run(db: Session, user: User, company_id: str) -> AgentRun:
    """Validate and create the run. Raises 404 before anything is stored."""
    company = get_catalog().get(company_id)
    settings = get_settings()
    has_resume = bool(user.profile and user.profile.resume_text)
    state = AgentState(
        goal=f"Prepare me for {company.name}",
        company_id=company.id,
        company_name=company.name,
        max_steps=settings.agent_max_steps,
        retries=settings.agent_step_retries,
        steps=make_plan(company, has_resume=has_resume),
    )
    run = AgentRun(user_id=user.id, company_id=company.id, goal=state.goal, status="running", state=state.to_dict())
    db.add(run)
    db.commit()
    db.refresh(run)
    events.log_event(db, events.AGENT_RUN, user.id, run_id=run.id, company_id=company.id)
    return run


def _alternatives(user: User, exclude: str) -> list[dict[str, Any]]:
    """Companies the student is eligible for, highest CTC first."""
    profile = StudentProfileData.from_model(user.profile)
    catalog = get_catalog()
    results = [r for r in check_all(profile, catalog.all()) if r.eligible and r.company_id != exclude]
    results.sort(key=lambda r: -catalog.get(r.company_id).ctc_lpa[0])
    return [
        {"company_id": r.company_id, "company_name": r.company_name, "role": r.role, "ctc_label": r.ctc_label, "category": r.category}
        for r in results[:3]
    ]


def _event(kind: str, **data: Any) -> dict[str, Any]:
    return {"type": kind, **data}


def _step_event(record: StepRecord) -> dict[str, Any]:
    return _event("step", step=record.to_dict())


def execute_run(
    db: Session,
    run: AgentRun,
    *,
    faults: dict[str, int] | None = None,
    today: date | None = None,
) -> Iterator[dict[str, Any]]:
    user = db.get(User, run.user_id)
    company: Company = get_catalog().get(run.company_id)
    state = AgentState.from_dict(run.state)
    ctx = StepContext(db=db, user=user, profile=user.profile, company=company, state=state, faults=dict(faults or {}), today=today)

    yield _event("run", run={"id": run.id, "goal": state.goal, "status": run.status, "company_id": company.id})
    yield _event("plan", steps=[record.to_dict() for record in state.steps], max_steps=state.max_steps)

    def finish(status: str, outcome: str, message: str) -> Iterator[dict[str, Any]]:
        run.status, run.outcome = status, outcome
        state.outcome, state.message = outcome, message
        _save(db, run, state)
        logger.info("agent_run_finished", extra={"run_id": run.id, "status": status, "outcome": outcome, "tool_calls": state.tool_calls})
        yield _event("final", run=run_out(run))

    for record in state.steps:
        if record.kind == "gate":
            continue
        if record.status == "skipped":  # planned as skipped
            yield _step_event(record)
            continue

        succeeded = False
        started = time.perf_counter()
        while True:
            if state.tool_calls >= state.max_steps:
                record.status = "failed"
                record.detail = f"Stopped: the run reached its limit of {state.max_steps} tool calls."
                _mark_rest(state, record, "Not run: the step limit was reached.")
                yield _step_event(record)
                yield from finish("failed", "step_limit", record.detail)
                return

            state.tool_calls += 1
            record.attempts += 1
            record.status = "running"
            _save(db, run, state)
            yield _step_event(record)
            try:
                output, detail = STEP_FUNCTIONS[record.name](ctx)
                record.output, record.detail = output, detail
                succeeded = True
                break
            except StepError as exc:
                record.errors.append(f"Attempt {record.attempts}: {exc}")
                if record.attempts <= state.retries:
                    record.detail = f"Attempt {record.attempts} failed ({exc}). Retrying."
                    yield _step_event(record)
                    continue
                break
            except Exception as exc:  # an unexpected bug in a step is a failure, not a crash
                logger.exception("agent_step_crashed", extra={"run_id": run.id, "step": record.name})
                record.errors.append(f"Attempt {record.attempts}: unexpected error ({type(exc).__name__})")
                if record.attempts <= state.retries:
                    record.detail = f"Attempt {record.attempts} hit an unexpected error. Retrying."
                    yield _step_event(record)
                    continue
                break

        if succeeded:
            if record.attempts > 1:
                record.status, record.recovery = "recovered", "retry"
                record.detail = f"Recovered after {record.attempts - 1} retry. {record.detail}"
            else:
                record.status = "done"
        elif record.name in FALLBACKS:
            output, detail = FALLBACKS[record.name](ctx)
            record.status, record.recovery, record.output = "fallback", "fallback", output
            record.detail = f"Failed {record.attempts} times; used the fallback. {detail}"
        elif not record.required:
            record.status, record.recovery = "skipped", "skip"
            record.detail = f"Failed {record.attempts} times; this step is optional, so it was skipped."
        else:
            record.status = "failed"
            record.detail = f"Failed {record.attempts} times and has no fallback."
            record.duration_ms = round((time.perf_counter() - started) * 1000, 1)
            _mark_rest(state, record, "Not run: an earlier required step failed.")
            yield _step_event(record)
            yield from finish("failed", "step_failed", f"{record.label} failed, so the run stopped. Nothing was saved.")
            return

        record.duration_ms = round((time.perf_counter() - started) * 1000, 1)
        _save(db, run, state)
        yield _step_event(record)

        if record.name == "check_eligibility" and not record.output.get("eligible", False):
            state.alternatives = _alternatives(user, company.id)
            _mark_rest(state, record, "Not run: you are not eligible for this company.")
            for later in state.steps[state.steps.index(record) + 1 :]:
                yield _step_event(later)
            message = record.output.get("summary", "Not eligible.")
            if state.alternatives:
                message += " You are eligible for: " + ", ".join(a["company_name"] for a in state.alternatives) + "."
            yield from finish("completed", "not_eligible", message)
            return

    # Every step done: stop at the gate.
    plan = state.output("build_plan")["plan"]
    application = {
        "company_id": company.id,
        "company_name": company.name,
        "role_title": company.role,
        "status": "planned",
        "deadline": company.apply_by.isoformat() if company.apply_by else None,
    }
    state.pending = {"plan": plan, "application": application}
    gate = state.step("approval")
    gate.status, gate.detail = "waiting", "Waiting for your decision. Nothing has been saved yet."
    run.status = "awaiting_approval"
    state.message = "The plan is ready. Approve to save it and add the application to your tracker, or reject to discard it."
    _save(db, run, state)
    yield _step_event(gate)
    yield _event("approval_required", run_id=run.id, pending=state.pending)
    yield _event("final", run=run_out(run))


def _mark_rest(state: AgentState, current: StepRecord, detail: str) -> None:
    for record in state.steps[state.steps.index(current) + 1 :]:
        if record.status == "pending":
            record.status, record.detail = "skipped", detail


def run_agent(
    db: Session, user: User, company_id: str, *, faults: dict[str, int] | None = None, today: date | None = None
) -> Iterator[dict[str, Any]]:
    run = start_run(db, user, company_id)
    yield from execute_run(db, run, faults=faults, today=today)


def _own_run(db: Session, user: User, run_id: int) -> AgentRun:
    run = db.get(AgentRun, run_id)
    if run is None or run.user_id != user.id:
        raise AppError(404, "run_not_found", "That agent run does not exist.")
    return run


def get_run(db: Session, user: User, run_id: int) -> AgentRun:
    return _own_run(db, user, run_id)


def _check_pending(run: AgentRun) -> AgentState:
    if run.status != "awaiting_approval":
        raise AppError(409, "run_not_awaiting_approval", f"This run is {run.status.replace('_', ' ')}, so there is nothing to approve or reject.")
    state = AgentState.from_dict(run.state)
    if not state.pending:
        raise AppError(409, "run_not_awaiting_approval", "This run has nothing waiting for approval.")
    return state


def approve_run(db: Session, user: User, run_id: int) -> dict[str, Any]:
    """Save the plan and the application in one transaction."""
    run = _own_run(db, user, run_id)
    state = _check_pending(run)
    plan, pending_app = state.pending["plan"], state.pending["application"]

    existing = (
        db.query(Application).filter(Application.user_id == user.id, Application.company_id == run.company_id).one_or_none()
    )
    prep_plan = PrepPlan(user_id=user.id, company_id=run.company_id, title=plan["title"], plan=plan, agent_run_id=run.id)
    db.add(prep_plan)
    application, created = track_application(
        db,
        user.id,
        run.company_id,
        notes=None if existing else f"Added by the prep agent (run {run.id}).",
        commit=False,
    )
    db.flush()

    gate = state.step("approval")
    gate.status, gate.detail = "approved", "Approved. The plan and the application were saved."
    state.saved = {"prep_plan_id": prep_plan.id, "application_id": application.id, "application_created": created}
    state.message = "Saved. You can find the plan on your dashboard and the application in your tracker."
    run.status, run.outcome = "approved", "saved"
    run.state = copy.deepcopy(state.to_dict())
    flag_modified(run, "state")
    db.commit()
    events.log_event(db, events.AGENT_APPROVED, user.id, run_id=run.id, company_id=run.company_id)
    return {"run": run_out(run), "prep_plan_id": prep_plan.id, "application_id": application.id, "application_created": created, "deadline": pending_app.get("deadline")}


def reject_run(db: Session, user: User, run_id: int) -> dict[str, Any]:
    run = _own_run(db, user, run_id)
    state = _check_pending(run)
    gate = state.step("approval")
    gate.status, gate.detail = "rejected", "Rejected. Nothing was saved."
    state.message = "Discarded. Nothing was saved."
    run.status, run.outcome = "rejected", "discarded"
    run.state = copy.deepcopy(state.to_dict())
    flag_modified(run, "state")
    db.commit()
    events.log_event(db, events.AGENT_REJECTED, user.id, run_id=run.id, company_id=run.company_id)
    return {"run": run_out(run)}
