"""Authentication, sessions and role checks."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt

from app.config import get_settings
from app.models import User
from app.security.auth import ALGORITHM, hash_password, verify_password
from app.seed import DEMO_STUDENT_EMAIL, DEMO_STUDENT_PASSWORD

COOKIE = "pm_session"


def test_login_success_sets_httponly_cookie(client):
    response = client.post(
        "/api/auth/login", json={"email": DEMO_STUDENT_EMAIL, "password": DEMO_STUDENT_PASSWORD}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "student"
    assert body["profile"]["branch"] == "CSE"
    assert "password" not in str(body).lower()

    set_cookie = response.headers["set-cookie"]
    assert set_cookie.startswith(f"{COOKIE}=")
    assert "HttpOnly" in set_cookie
    assert "samesite=lax" in set_cookie.lower()


def test_wrong_password_and_unknown_email_look_identical(client):
    wrong_password = client.post(
        "/api/auth/login", json={"email": DEMO_STUDENT_EMAIL, "password": "not-the-password"}
    )
    unknown_email = client.post(
        "/api/auth/login", json={"email": "nobody@placemate.demo", "password": "not-the-password"}
    )
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json()["error"]["code"] == unknown_email.json()["error"]["code"] == "invalid_credentials"
    assert wrong_password.json()["error"]["message"] == unknown_email.json()["error"]["message"]
    assert "set-cookie" not in wrong_password.headers


def test_email_is_case_insensitive(client):
    response = client.post(
        "/api/auth/login", json={"email": DEMO_STUDENT_EMAIL.upper(), "password": DEMO_STUDENT_PASSWORD}
    )
    assert response.status_code == 200


def test_me_requires_a_session(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


def test_me_returns_the_logged_in_user(student_client):
    response = student_client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == DEMO_STUDENT_EMAIL
    assert response.json()["profile"]["has_resume"] is True


def test_session_is_null_for_a_visitor(client):
    response = client.get("/api/auth/session")
    assert response.status_code == 200
    assert response.json() == {"user": None}


def test_session_is_null_for_a_tampered_token(client):
    client.cookies.set(COOKIE, "not.a.real-token")
    response = client.get("/api/auth/session")
    assert response.status_code == 200
    assert response.json()["user"] is None


def test_session_returns_the_logged_in_user(student_client):
    response = student_client.get("/api/auth/session")
    assert response.status_code == 200
    assert response.json()["user"]["email"] == DEMO_STUDENT_EMAIL


def test_tampered_token_is_rejected(client):
    client.cookies.set(COOKIE, "not.a.real-token")
    assert client.get("/api/auth/me").status_code == 401


def test_token_signed_with_another_key_is_rejected(client):
    forged = jwt.encode({"sub": "1", "role": "coordinator", "exp": 9999999999}, "attacker-key" * 4, algorithm=ALGORITHM)
    client.cookies.set(COOKIE, forged)
    assert client.get("/api/auth/me").status_code == 401


def test_expired_token_is_rejected(client):
    settings = get_settings()
    expired = jwt.encode(
        {"sub": "1", "role": "student", "exp": int((datetime.now(timezone.utc) - timedelta(minutes=1)).timestamp())},
        settings.resolve_secret_key(),
        algorithm=ALGORITHM,
    )
    client.cookies.set(COOKIE, expired)
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert "expired" in response.json()["error"]["message"].lower()


def test_role_in_token_is_not_trusted_over_the_database(client, db):
    """A student token that claims to be a coordinator still gets a 403."""
    settings = get_settings()
    student = db.query(User).filter(User.email == DEMO_STUDENT_EMAIL).one()
    token = jwt.encode(
        {"sub": str(student.id), "role": "coordinator", "exp": 9999999999},
        settings.resolve_secret_key(),
        algorithm=ALGORITHM,
    )
    client.cookies.set(COOKIE, token)
    assert client.get("/api/_test/coordinator-only").status_code == 403


def test_logout_clears_the_cookie(student_client):
    response = student_client.post("/api/auth/logout")
    assert response.status_code == 204
    assert f'{COOKIE}=""' in response.headers["set-cookie"] or f"{COOKIE}=;" in response.headers["set-cookie"]
    assert student_client.get("/api/auth/me").status_code == 401


def test_student_cannot_use_a_coordinator_route(student_client):
    response = student_client.get("/api/_test/coordinator-only")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_anonymous_cannot_use_a_coordinator_route(client):
    assert client.get("/api/_test/coordinator-only").status_code == 401


def test_coordinator_can_use_a_coordinator_route(coordinator_client):
    assert coordinator_client.get("/api/_test/coordinator-only").status_code == 200


def test_passwords_are_stored_as_argon2id_hashes(db):
    user = db.query(User).filter(User.email == DEMO_STUDENT_EMAIL).one()
    assert user.password_hash.startswith("$argon2id$")
    assert DEMO_STUDENT_PASSWORD not in user.password_hash


def test_hash_and_verify_round_trip():
    hashed = hash_password("S3cret!pass")
    assert hashed != hash_password("S3cret!pass")  # salted
    assert verify_password("S3cret!pass", hashed)
    assert not verify_password("wrong", hashed)
    assert not verify_password("anything", "not-a-hash")


def test_login_validation_errors_are_readable(client):
    response = client.post("/api/auth/login", json={"email": "not-an-email", "password": ""})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    fields = {detail["field"] for detail in error["details"]}
    assert {"email", "password"} <= fields
    assert "not-an-email" not in response.text  # submitted values are not echoed


def test_unknown_fields_are_rejected(client):
    response = client.post(
        "/api/auth/login",
        json={"email": DEMO_STUDENT_EMAIL, "password": DEMO_STUDENT_PASSWORD, "role": "coordinator"},
    )
    assert response.status_code == 422


def test_student_can_update_own_profile(student_client):
    response = student_client.patch("/api/auth/profile", json={"cgpa": 8.1, "branch": "it"})
    assert response.status_code == 200
    assert response.json()["profile"]["cgpa"] == 8.1
    assert response.json()["profile"]["branch"] == "IT"
    # restore for other tests
    student_client.patch("/api/auth/profile", json={"cgpa": 7.8, "branch": "CSE"})


def test_profile_rejects_impossible_values(student_client):
    assert student_client.patch("/api/auth/profile", json={"cgpa": 11}).status_code == 422
    assert student_client.patch("/api/auth/profile", json={"active_backlogs": -1}).status_code == 422


def test_companies_require_login(client, student_client):
    assert client.get("/api/meta/companies").status_code == 401
    response = student_client.get("/api/meta/companies")
    assert response.status_code == 200
    companies = response.json()
    assert len(companies) == 12
    nimbusware = next(c for c in companies if c["id"] == "nimbusware")
    assert nimbusware["category"] == "Standard"
    assert nimbusware["min_cgpa"] == 7.0
