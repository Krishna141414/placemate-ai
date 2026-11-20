"""Application tracker and saved prep plans (student only)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import AppError
from app.models import PrepPlan, User
from app.schemas import ApplicationCreate, ApplicationOut, ApplicationUpdate, PlanProgressUpdate, PrepPlanOut
from app.security.auth import require_student
from app.services import events
from app.tools.applications import get_own_application, list_applications, track_application

router = APIRouter(prefix="/api", tags=["applications"])


@router.get("/applications", response_model=list[ApplicationOut], summary="The student's applications, soonest deadline first")
def applications(user: User = Depends(require_student), db: Session = Depends(get_db)) -> list[ApplicationOut]:
    return [ApplicationOut.model_validate(a) for a in list_applications(db, user.id)]


@router.post("/applications", response_model=ApplicationOut, summary="Track an application (creates or updates)")
def create_application(
    body: ApplicationCreate, response: Response, user: User = Depends(require_student), db: Session = Depends(get_db)
) -> ApplicationOut:
    kwargs = {"status": body.status, "notes": body.notes}
    if body.deadline is not None:
        kwargs["deadline"] = body.deadline
    application, created = track_application(db, user.id, body.company_id, **kwargs)
    response.status_code = 201 if created else 200
    events.log_event(
        db, events.APPLICATION, user.id, company_id=application.company_id, status=application.status,
        action="created" if created else "updated",
    )
    return ApplicationOut.model_validate(application)


@router.patch("/applications/{application_id}", response_model=ApplicationOut, summary="Update status, deadline or notes")
def update_application(
    application_id: int, body: ApplicationUpdate, user: User = Depends(require_student), db: Session = Depends(get_db)
) -> ApplicationOut:
    application = get_own_application(db, user.id, application_id)
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        raise AppError(422, "nothing_to_update", "Send at least one of status, deadline or notes.")
    application, _ = track_application(db, user.id, application.company_id, **changes)
    events.log_event(db, events.APPLICATION, user.id, company_id=application.company_id, status=application.status, action="updated")
    return ApplicationOut.model_validate(application)


@router.delete("/applications/{application_id}", status_code=204, summary="Remove an application from the tracker")
def delete_application(application_id: int, user: User = Depends(require_student), db: Session = Depends(get_db)) -> Response:
    application = get_own_application(db, user.id, application_id)
    db.delete(application)
    db.commit()
    return Response(status_code=204)


@router.get("/prep-plans", response_model=list[PrepPlanOut], summary="The student's approved prep plans")
def prep_plans(user: User = Depends(require_student), db: Session = Depends(get_db)) -> list[PrepPlanOut]:
    rows = db.query(PrepPlan).filter(PrepPlan.user_id == user.id).order_by(PrepPlan.id.desc()).all()
    return [PrepPlanOut.model_validate(row) for row in rows]


def _own_plan(db: Session, user: User, plan_id: int) -> PrepPlan:
    plan = db.get(PrepPlan, plan_id)
    if plan is None or plan.user_id != user.id:
        raise AppError(404, "plan_not_found", "That plan does not exist.")
    return plan


@router.get("/prep-plans/{plan_id}", response_model=PrepPlanOut, summary="One approved prep plan")
def prep_plan(plan_id: int, user: User = Depends(require_student), db: Session = Depends(get_db)) -> PrepPlanOut:
    return PrepPlanOut.model_validate(_own_plan(db, user, plan_id))


@router.patch("/prep-plans/{plan_id}", response_model=PrepPlanOut, summary="Mark plan tasks as done")
def update_plan_progress(
    plan_id: int, body: PlanProgressUpdate, user: User = Depends(require_student), db: Session = Depends(get_db)
) -> PrepPlanOut:
    plan = _own_plan(db, user, plan_id)
    valid = {f"w{week['week']}-t{i}" for week in plan.plan.get("weeks", []) for i in range(len(week.get("tasks", [])))}
    unknown = [key for key in body.done if key not in valid]
    if unknown:
        raise AppError(422, "unknown_task", f"These task ids are not in the plan: {', '.join(unknown[:5])}.")
    plan.plan = {**plan.plan, "done": sorted(set(body.done))}
    db.commit()
    db.refresh(plan)
    return PrepPlanOut.model_validate(plan)
