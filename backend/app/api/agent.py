"""Prep agent: start a run (JSON or SSE), inspect it, approve or reject it."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.agent import executor
from app.db import SessionLocal, get_db
from app.models import AgentRun, User
from app.schemas import AgentRunOut, AgentRunRequest
from app.security.auth import require_student

logger = logging.getLogger("placemate.agent.api")
router = APIRouter(prefix="/api/agent", tags=["agent"])

SSE_HEADERS = {"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no", "Connection": "keep-alive"}


def _faults(body: AgentRunRequest) -> dict[str, int]:
    return {body.demo_fault: 1} if body.demo_fault else {}


@router.post("/runs", response_model=AgentRunOut, summary="Run the prep agent to completion and return the run")
def create_run(body: AgentRunRequest, user: User = Depends(require_student), db: Session = Depends(get_db)) -> AgentRunOut:
    run = executor.start_run(db, user, body.company_id)
    final: dict[str, Any] = {}
    for event in executor.execute_run(db, run, faults=_faults(body)):
        if event["type"] == "final":
            final = event["run"]
    return AgentRunOut(**final)


def _json_default(value: Any) -> str:
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _stream(run_id: int, faults: dict[str, int]) -> Iterator[str]:
    with SessionLocal() as db:
        run = db.get(AgentRun, run_id)
        try:
            for event in executor.execute_run(db, run, faults=faults):
                kind = event.pop("type")
                yield f"event: {kind}\ndata: {json.dumps(event, default=_json_default, ensure_ascii=False)}\n\n"
        except Exception:
            logger.exception("agent_stream_failed", extra={"run_id": run_id})
            run.status, run.outcome = "failed", "error"
            db.commit()
            payload = {"code": "internal_error", "message": "The agent stopped because of an error. Nothing was saved."}
            yield f"event: error\ndata: {json.dumps(payload)}\n\n"


@router.post("/runs/stream", summary="Run the prep agent; steps arrive as server-sent events")
def create_run_stream(body: AgentRunRequest, user: User = Depends(require_student), db: Session = Depends(get_db)) -> StreamingResponse:
    # Created before streaming starts, so an unknown company is a plain 404.
    run = executor.start_run(db, user, body.company_id)
    return StreamingResponse(_stream(run.id, _faults(body)), media_type="text/event-stream", headers=SSE_HEADERS)


@router.get("/runs", response_model=list[AgentRunOut], summary="The student's recent agent runs")
def list_runs(user: User = Depends(require_student), db: Session = Depends(get_db)) -> list[AgentRunOut]:
    runs = db.query(AgentRun).filter(AgentRun.user_id == user.id).order_by(AgentRun.id.desc()).limit(20).all()
    return [AgentRunOut(**executor.run_out(run)) for run in runs]


@router.get("/runs/{run_id}", response_model=AgentRunOut, summary="One agent run with its full saved state")
def get_run(run_id: int, user: User = Depends(require_student), db: Session = Depends(get_db)) -> AgentRunOut:
    return AgentRunOut(**executor.run_out(executor.get_run(db, user, run_id)))


@router.post("/runs/{run_id}/approve", summary="Approve: save the plan and add the application")
def approve(run_id: int, user: User = Depends(require_student), db: Session = Depends(get_db)) -> dict:
    result = executor.approve_run(db, user, run_id)
    result["run"] = AgentRunOut(**result["run"]).model_dump(mode="json")
    return result


@router.post("/runs/{run_id}/reject", summary="Reject: discard the plan; nothing is saved")
def reject(run_id: int, user: User = Depends(require_student), db: Session = Depends(get_db)) -> dict:
    result = executor.reject_run(db, user, run_id)
    result["run"] = AgentRunOut(**result["run"]).model_dump(mode="json")
    return result
