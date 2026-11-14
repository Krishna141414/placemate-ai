"""Login, logout, current user and profile."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import AppError
from app.models import StudentProfile, User
from app.schemas import LoginRequest, ProfileOut, ProfileUpdate, UserOut
from app.security.auth import (
    authenticate,
    clear_session_cookie,
    create_token,
    get_current_user,
    require_student,
    set_session_cookie,
)
from app.services import events

router = APIRouter(prefix="/api/auth", tags=["auth"])


def user_out(user: User) -> UserOut:
    profile = None
    if user.profile is not None:
        profile = ProfileOut(
            branch=user.profile.branch,
            cgpa=user.profile.cgpa,
            active_backlogs=user.profile.active_backlogs,
            batch=user.profile.batch,
            has_resume=bool(user.profile.resume_text),
        )
    return UserOut(id=user.id, email=user.email, name=user.name, role=user.role, profile=profile)


@router.post("/login", response_model=UserOut, summary="Log in and receive the session cookie")
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)) -> UserOut:
    user = authenticate(db, body.email, body.password)
    if user is None:
        events.log_event(db, events.LOGIN_FAILED)
        # Same message for an unknown email and a wrong password.
        raise AppError(401, "invalid_credentials", "Email or password is incorrect.")
    set_session_cookie(response, create_token(user))
    events.log_event(db, events.LOGIN, user.id, role=user.role)
    return user_out(user)


@router.post("/logout", status_code=204, summary="Clear the session cookie")
def logout(response: Response) -> Response:
    clear_session_cookie(response)
    response.status_code = 204
    return response


@router.get("/me", response_model=UserOut, summary="The logged-in user")
def me(user: User = Depends(get_current_user)) -> UserOut:
    return user_out(user)


@router.patch("/profile", response_model=UserOut, summary="Update the student's own profile")
def update_profile(
    body: ProfileUpdate, user: User = Depends(require_student), db: Session = Depends(get_db)
) -> UserOut:
    user = db.get(User, user.id)
    profile = user.profile or StudentProfile(user_id=user.id)
    changes = body.model_dump(exclude_unset=True)
    if "branch" in changes and changes["branch"]:
        changes["branch"] = changes["branch"].upper()
    for key, value in changes.items():
        setattr(profile, key, value)
    user.profile = profile
    db.add(user)
    db.commit()
    db.refresh(user)
    return user_out(user)
