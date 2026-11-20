"""Prep agent: happy path, recovery, step limit, approval gate, API."""

from __future__ import annotations

import json
from datetime import date

import pytest

from app.agent.executor import approve_run, execute_run, reject_run, run_agent, start_run
from app.agent.plan_builder import build_prep_plan, weeks_until
from app.agent.planner import make_plan
from app.config import get_settings
from app.errors import AppError
from app.models import AgentRun, Application, PrepPlan, StudentProfile, User
from app.seed import DEMO_STUDENT_EMAIL
from app.tools.catalog import get_catalog

TODAY = date(2026, 11, 19)


@pytest.fixture
def student(db) -> User:
    return db.query(User).filter(User.email == DEMO_STUDENT_EMAIL).one()


@pytest.fixture
def without_resume(db, student):
    original = student.profile.resume_text
    student.profile.resume_text = None
    db.commit()
    yield student
    db.get(StudentProfile, student.id).resume_text = original
    db.commit()


def run(db, user, company_id="nimbusware", faults=None):
    events = list(run_agent(db, user, company_id, faults=faults, today=TODAY))
    final = events[-1]
    assert final["type"] == "final"
    return events, final["run"]


def steps_of(run_out):
    return {step["name"]: step for step in run_out["state"]["steps"]}


# --- planner and plan builder ------------------------------------------------


def test_plan_has_the_five_steps_and_a_gate():
    plan = make_plan(get_catalog().get("nimbusware"), has_resume=True)
    assert [s.name for s in plan] == [
        "check_eligibility", "match_resume", "retrieve_process", "retrieve_experiences", "build_plan", "approval",
    ]
    assert [s.required for s in plan] == [True, False, True, False, True, True]
    assert all(s.status == "pending" for s in plan)


def test_planner_skips_resume_step_without_a_resume():
    plan = make_plan(get_catalog().get("nimbusware"), has_resume=False)
    assert plan[1].status == "skipped" and "No resume" in plan[1].detail


@pytest.mark.parametrize(
    "deadline,weeks", [(date(2026, 11, 25), 2), (date(2026, 12, 5), 3), (date(2027, 3, 1), 4), (date(2026, 1, 1), 4), (None, 4)]
)
def test_plan_length_follows_the_deadline(deadline, weeks):
    assert weeks_until(deadline, TODAY) == weeks


def test_plan_puts_skill_gaps_first_and_mock_interviews_last():
    company = get_catalog().get("orbitpay")
    plan = build_prep_plan(company, missing_skills=["java"], process_rounds=company.rounds, tips=[], today=TODAY)
    assert plan["weeks_count"] == 3
    assert plan["weeks"][0]["focus"].startswith("Close the gap: java")
    assert plan["weeks"][-1]["focus"] == "Mock interviews and HR"
    focus = " ".join(week["focus"] for week in plan["weeks"])
    assert "System design basics" in focus and "Data structures" in focus
    assert all(1 <= len(week["tasks"]) <= 6 for week in plan["weeks"])


def test_aptitude_company_gets_aptitude_and_communication():
    company = get_catalog().get("tessera")
    plan = build_prep_plan(company, missing_skills=[], process_rounds=company.rounds, tips=[], today=TODAY)
    focus = " ".join(week["focus"] for week in plan["weeks"])
    assert "Aptitude" in focus and "Communication" in focus and "Data structures" not in focus


# --- happy path ---------------------------------------------------------------


def test_happy_path_stops_at_approval_and_writes_nothing(db, student):
    events, out = run(db, student)
    assert out["status"] == "awaiting_approval"
    steps = steps_of(out)
    assert [steps[n]["status"] for n in ("check_eligibility", "match_resume", "retrieve_process", "retrieve_experiences", "build_plan")] == ["done"] * 5
    assert steps["approval"]["status"] == "waiting"
    assert out["state"]["tool_calls"] == 5

    pending = out["state"]["pending"]
    assert pending["application"] == {
        "company_id": "nimbusware", "company_name": "Nimbusware Technologies", "role_title": "Software Engineer Trainee",
        "status": "planned", "deadline": "2026-12-05",
    }
    plan = pending["plan"]
    assert plan["weeks_count"] == 3 and len(plan["weeks"]) == 3
    assert plan["summary"] and plan["summary_citations"]
    assert plan["summary_provider"] == "extractive"
    assert plan["tips"]

    # Approval required: nothing saved yet.
    assert db.query(PrepPlan).count() == 0
    assert db.query(Application).filter(Application.user_id == student.id).count() == 0

    kinds = [event["type"] for event in events]
    assert kinds[:2] == ["run", "plan"] and kinds[-2:] == ["approval_required", "final"]


def test_state_is_saved_to_the_database(db, student):
    _, out = run(db, student)
    saved = db.get(AgentRun, out["id"])
    db.refresh(saved)
    assert saved.status == "awaiting_approval"
    assert saved.state["tool_calls"] == 5
    assert saved.state["steps"][0]["output"]["eligible"] is True
    assert saved.state["pending"]["plan"]["company_id"] == "nimbusware"


def test_approve_saves_plan_and_application_once(db, student):
    _, out = run(db, student)
    result = approve_run(db, student, out["id"])
    assert result["run"]["status"] == "approved"
    assert result["application_created"] is True
    plan = db.get(PrepPlan, result["prep_plan_id"])
    assert plan.user_id == student.id and plan.agent_run_id == out["id"]
    application = db.get(Application, result["application_id"])
    assert application.company_id == "nimbusware" and application.status == "planned"
    assert "prep agent" in application.notes
    assert steps_of(result["run"])["approval"]["status"] == "approved"


def test_double_approve_conflict(db, student):
    """Review focus 5: a second approve writes nothing."""
    _, out = run(db, student)
    approve_run(db, student, out["id"])
    with pytest.raises(AppError) as info:
        approve_run(db, student, out["id"])
    assert info.value.status_code == 409
    assert db.query(PrepPlan).count() == 1


def test_approve_keeps_an_existing_application(db, student):
    from app.tools.applications import track_application

    existing, _ = track_application(db, student.id, "nimbusware", status="online_test", notes="mine")
    _, out = run(db, student)
    result = approve_run(db, student, out["id"])
    assert result["application_created"] is False and result["application_id"] == existing.id
    db.refresh(existing)
    assert existing.status == "online_test" and existing.notes == "mine"


def test_reject_saves_nothing(db, student):
    _, out = run(db, student)
    result = reject_run(db, student, out["id"])
    assert result["run"]["status"] == "rejected"
    assert db.query(PrepPlan).count() == 0
    assert db.query(Application).filter(Application.user_id == student.id).count() == 0
    with pytest.raises(AppError) as info:
        approve_run(db, student, out["id"])
    assert info.value.status_code == 409


def test_cannot_approve_foreign_run(db, student):
    """Review focus 5: someone else's run is reported as missing."""
    _, out = run(db, student)
    other = db.query(User).filter(User.email == "karthik.subramani@krit.example").one()
    with pytest.raises(AppError) as info:
        approve_run(db, other, out["id"])
    assert info.value.status_code == 404
    assert db.query(PrepPlan).count() == 0


# --- not eligible ---------------------------------------------------------------


def test_ineligible_student_gets_reasons_and_alternatives(db, student):
    _, out = run(db, student, "veltrix")
    assert out["status"] == "completed" and out["outcome"] == "not_eligible"
    steps = steps_of(out)
    assert steps["check_eligibility"]["status"] == "done"
    assert all(steps[n]["status"] == "skipped" for n in ("match_resume", "retrieve_process", "build_plan", "approval"))
    assert out["state"]["pending"] is None
    alternatives = out["state"]["alternatives"]
    assert 1 <= len(alternatives) <= 3
    assert {a["company_id"] for a in alternatives} <= {"nimbusware", "quantaleaf", "kairoscloud", "brightpath", "tessera"}
    assert out["state"]["tool_calls"] == 1
    with pytest.raises(AppError):
        approve_run(db, student, out["id"])


# --- recovery -------------------------------------------------------------------


def test_failed_step_is_retried_and_marked_recovered(db, student):
    _, out = run(db, student, faults={"retrieve_process": 1})
    step = steps_of(out)["retrieve_process"]
    assert step["status"] == "recovered" and step["recovery"] == "retry"
    assert step["attempts"] == 2 and len(step["errors"]) == 1
    assert out["status"] == "awaiting_approval"
    assert out["state"]["tool_calls"] == 6


def test_required_step_uses_its_fallback(db, student):
    _, out = run(db, student, faults={"retrieve_process": 99})
    step = steps_of(out)["retrieve_process"]
    assert step["status"] == "fallback" and step["recovery"] == "fallback"
    assert step["attempts"] == 1 + get_settings().agent_step_retries
    assert step["output"]["used_fallback"] is True and step["output"]["rounds"]
    assert out["status"] == "awaiting_approval"


def test_plan_builder_falls_back_to_a_template(db, student):
    _, out = run(db, student, faults={"build_plan": 99})
    step = steps_of(out)["build_plan"]
    assert step["status"] == "fallback"
    plan = out["state"]["pending"]["plan"]
    assert plan["summary_provider"] == "template"
    assert "rounds" in plan["summary"] and len(plan["weeks"]) == plan["weeks_count"]


def test_optional_step_is_skipped_after_retries(db, student):
    _, out = run(db, student, faults={"match_resume": 99})
    step = steps_of(out)["match_resume"]
    assert step["status"] == "skipped" and step["recovery"] == "skip"
    assert out["status"] == "awaiting_approval"
    assert out["state"]["pending"]["plan"]["focus_skills"] == []


def test_agent_skips_resume_when_missing(db, without_resume):
    """Review focus 3: no resume means the optional step is skipped, not failed."""
    _, out = run(db, without_resume)
    step = steps_of(out)["match_resume"]
    assert step["status"] == "skipped" and step["attempts"] == 0
    assert out["status"] == "awaiting_approval"
    assert out["state"]["tool_calls"] == 4


def test_required_step_without_fallback_fails_the_run(db, student):
    _, out = run(db, student, faults={"check_eligibility": 99})
    assert out["status"] == "failed" and out["outcome"] == "step_failed"
    steps = steps_of(out)
    assert steps["check_eligibility"]["status"] == "failed"
    assert all(steps[n]["status"] == "skipped" for n in ("match_resume", "build_plan", "approval"))
    assert "Nothing was saved" in out["state"]["message"]
    assert db.query(PrepPlan).count() == 0


def test_step_limit_is_enforced(db, student, monkeypatch):
    monkeypatch.setattr(get_settings(), "agent_max_steps", 4)
    _, out = run(db, student, faults={"retrieve_process": 2})
    assert out["status"] == "failed" and out["outcome"] == "step_limit"
    assert out["state"]["tool_calls"] == 4
    assert "limit of 4" in out["state"]["message"]


def test_unexpected_exception_in_a_step_is_contained(db, student, monkeypatch):
    from app.agent import executor

    calls = {"n": 0}
    original = executor.STEP_FUNCTIONS["retrieve_experiences"]

    def flaky(ctx):
        calls["n"] += 1
        if calls["n"] == 1:
            raise KeyError("bug")
        return original(ctx)

    monkeypatch.setitem(executor.STEP_FUNCTIONS, "retrieve_experiences", flaky)
    _, out = run(db, student)
    assert steps_of(out)["retrieve_experiences"]["status"] == "recovered"


def test_company_without_interview_writeups(db, student):
    """Halcyon has no write-ups on file: the optional step succeeds with nothing."""
    student.profile.branch = "ECE"
    db.commit()
    try:
        _, out = run(db, student, "halcyon")
    finally:
        db.get(StudentProfile, student.id).branch = "CSE"
        db.commit()
    step = steps_of(out)["retrieve_experiences"]
    assert step["status"] == "done"
    assert step["output"] == {"sources": [], "tips": []}
    assert "No interview experiences on file" in step["detail"]
    assert out["status"] == "awaiting_approval"
    assert out["state"]["pending"]["plan"]["tips"] == []


def test_unknown_company_creates_no_run(db, student):
    """Review focus 2: 404 before anything is stored."""
    with pytest.raises(AppError) as info:
        start_run(db, student, "nobody")
    assert info.value.status_code == 404
    assert db.query(AgentRun).count() == 0


# --- API ------------------------------------------------------------------------


def _sse(text: str) -> list[tuple[str, dict]]:
    out = []
    for block in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.split("\n"))
        out.append((lines["event"], json.loads(lines["data"])))
    return out


def test_agent_api_full_flow(student_client):
    run_out = student_client.post("/api/agent/runs", json={"company_id": "nimbusware", "demo_fault": "retrieve_process"}).json()
    assert run_out["status"] == "awaiting_approval"
    assert steps_of(run_out)["retrieve_process"]["status"] == "recovered"

    fetched = student_client.get(f"/api/agent/runs/{run_out['id']}").json()
    assert fetched["state"]["pending"]["plan"]["company_id"] == "nimbusware"
    assert [r["id"] for r in student_client.get("/api/agent/runs").json()] == [run_out["id"]]

    approved = student_client.post(f"/api/agent/runs/{run_out['id']}/approve")
    assert approved.status_code == 200 and approved.json()["run"]["status"] == "approved"
    assert student_client.post(f"/api/agent/runs/{run_out['id']}/approve").status_code == 409
    assert student_client.post(f"/api/agent/runs/{run_out['id']}/reject").status_code == 409

    plans = student_client.get("/api/prep-plans").json()
    assert len(plans) == 1 and plans[0]["agent_run_id"] == run_out["id"]
    assert student_client.get(f"/api/prep-plans/{plans[0]['id']}").status_code == 200
    assert [a["company_id"] for a in student_client.get("/api/applications").json()] == ["nimbusware"]


def test_agent_stream(student_client):
    response = student_client.post("/api/agent/runs/stream", json={"company_id": "nimbusware"})
    assert response.status_code == 200
    events = _sse(response.text)
    names = [name for name, _ in events]
    assert names[:2] == ["run", "plan"]
    assert names[-2:] == ["approval_required", "final"]
    assert events[-1][1]["run"]["status"] == "awaiting_approval"
    running = [data["step"]["name"] for name, data in events if name == "step" and data["step"]["status"] == "running"]
    assert running == ["check_eligibility", "match_resume", "retrieve_process", "retrieve_experiences", "build_plan"]


def test_agent_stream_unknown_company_is_a_json_404(student_client, db):
    response = student_client.post("/api/agent/runs/stream", json={"company_id": "nobody"})
    assert response.status_code == 404 and response.json()["error"]["code"] == "company_not_found"
    assert db.query(AgentRun).count() == 0


def test_agent_rejects_unknown_demo_fault(student_client):
    response = student_client.post("/api/agent/runs", json={"company_id": "nimbusware", "demo_fault": "check_eligibility"})
    assert response.status_code == 422


def test_agent_runs_are_private_and_student_only(student_client, coordinator_client, client):
    run_id = student_client.post("/api/agent/runs", json={"company_id": "nimbusware"}).json()["id"]
    assert coordinator_client.get(f"/api/agent/runs/{run_id}").status_code == 403
    assert coordinator_client.post(f"/api/agent/runs/{run_id}/approve").status_code == 403
    assert client.post("/api/agent/runs", json={"company_id": "nimbusware"}).status_code == 401
    assert student_client.get("/api/agent/runs/99999").status_code == 404


def test_plan_progress_can_be_saved(student_client):
    run_id = student_client.post("/api/agent/runs", json={"company_id": "nimbusware"}).json()["id"]
    student_client.post(f"/api/agent/runs/{run_id}/approve")
    plan = student_client.get("/api/prep-plans").json()[0]
    updated = student_client.patch(f"/api/prep-plans/{plan['id']}", json={"done": ["w1-t0", "w1-t1", "w1-t0"]})
    assert updated.status_code == 200
    assert updated.json()["plan"]["done"] == ["w1-t0", "w1-t1"]
    bad = student_client.patch(f"/api/prep-plans/{plan['id']}", json={"done": ["w9-t9"]})
    assert bad.status_code == 422 and bad.json()["error"]["code"] == "unknown_task"
    assert student_client.patch("/api/prep-plans/99999", json={"done": []}).status_code == 404


def test_own_resume_endpoint(student_client, coordinator_client):
    body = student_client.get("/api/tools/resume").json()
    assert body["has_resume"] is True and "ANANYA RAO" in body["text"]
    assert coordinator_client.get("/api/tools/resume").status_code == 403
