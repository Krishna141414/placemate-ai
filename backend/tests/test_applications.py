"""`track_application` and the tracker API."""

from __future__ import annotations

from datetime import date

import pytest

from app.errors import AppError
from app.models import Application, User
from app.seed import DEMO_STUDENT_EMAIL
from app.tools.applications import track_application


def demo_user(db) -> User:
    return db.query(User).filter(User.email == DEMO_STUDENT_EMAIL).one()


def test_create_uses_company_details_and_deadline(db):
    application, created = track_application(db, demo_user(db).id, "nimbusware")
    assert created is True
    assert application.company_name == "Nimbusware Technologies"
    assert application.role_title == "Software Engineer Trainee"
    assert application.status == "planned"
    assert application.deadline == date(2026, 12, 5)


def test_second_call_updates_instead_of_duplicating(db):
    user = demo_user(db)
    first, _ = track_application(db, user.id, "nimbusware")
    second, created = track_application(db, user.id, "nimbusware", status="applied", notes="OA on 9 Dec")
    assert created is False and second.id == first.id
    assert second.status == "applied" and second.notes == "OA on 9 Dec"
    assert db.query(Application).filter(Application.user_id == user.id, Application.company_id == "nimbusware").count() == 1


def test_update_keeps_fields_that_were_not_given(db):
    user = demo_user(db)
    track_application(db, user.id, "quantaleaf", status="applied", notes="keep me")
    application, _ = track_application(db, user.id, "quantaleaf", status="interview")
    assert application.notes == "keep me"


def test_deadline_can_be_cleared(db):
    application, _ = track_application(db, demo_user(db).id, "quantaleaf", deadline=None)
    assert application.deadline is None


def test_invalid_status_is_rejected(db):
    with pytest.raises(AppError) as info:
        track_application(db, demo_user(db).id, "nimbusware", status="hired")
    assert info.value.code == "invalid_status"


def test_unknown_company_is_rejected(db):
    with pytest.raises(AppError) as info:
        track_application(db, demo_user(db).id, "nobody")
    assert info.value.status_code == 404


# --- API ----------------------------------------------------------------------


def test_create_list_update_delete(student_client):
    created = student_client.post("/api/applications", json={"company_id": "nimbusware", "notes": "Revise SQL"})
    assert created.status_code == 201
    application = created.json()
    assert application["status"] == "planned" and application["deadline"] == "2026-12-05"

    again = student_client.post("/api/applications", json={"company_id": "nimbusware", "status": "applied"})
    assert again.status_code == 200 and again.json()["id"] == application["id"]

    updated = student_client.patch(f"/api/applications/{application['id']}", json={"status": "interview", "deadline": "2026-12-12"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "interview" and updated.json()["deadline"] == "2026-12-12"

    listing = student_client.get("/api/applications").json()
    assert [row["company_id"] for row in listing] == ["nimbusware"]

    assert student_client.delete(f"/api/applications/{application['id']}").status_code == 204
    assert student_client.get("/api/applications").json() == []


def test_list_is_sorted_by_deadline(student_client):
    student_client.post("/api/applications", json={"company_id": "lumengrid"})  # 18 Dec
    student_client.post("/api/applications", json={"company_id": "veltrix"})  # 25 Nov
    student_client.post("/api/applications", json={"company_id": "nimbusware"})  # 5 Dec
    assert [row["company_id"] for row in student_client.get("/api/applications").json()] == ["veltrix", "nimbusware", "lumengrid"]


@pytest.mark.parametrize(
    "payload",
    [
        {"company_id": "nimbusware", "status": "hired"},
        {"company_id": "nimbusware", "deadline": "not-a-date"},
        {"company_id": "nimbusware", "notes": "x" * 1001},
        {"status": "applied"},
    ],
)
def test_invalid_payloads_are_422(student_client, payload):
    assert student_client.post("/api/applications", json=payload).status_code == 422


def test_empty_patch_is_rejected(student_client):
    application = student_client.post("/api/applications", json={"company_id": "nimbusware"}).json()
    response = student_client.patch(f"/api/applications/{application['id']}", json={})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "nothing_to_update"


def test_applications_are_private(student_client, db):
    other = db.query(User).filter(User.email == "karthik.subramani@krit.example").one()
    foreign, _ = track_application(db, other.id, "veltrix")
    assert student_client.patch(f"/api/applications/{foreign.id}", json={"status": "offer"}).status_code == 404
    assert student_client.delete(f"/api/applications/{foreign.id}").status_code == 404
    assert all(row["id"] != foreign.id for row in student_client.get("/api/applications").json())
    db.refresh(foreign)
    assert foreign.status == "planned"


def test_tracker_is_for_students_only(coordinator_client, client):
    assert coordinator_client.get("/api/applications").status_code == 403
    assert client.get("/api/applications").status_code == 401
