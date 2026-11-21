"""Timestamps keep their timezone through SQLite and the API."""

from datetime import datetime, timedelta, timezone

from app.models import Event


def test_stored_timestamps_come_back_as_utc(db):
    ist = timezone(timedelta(hours=5, minutes=30))
    event = Event(type="test_event", payload={}, created_at=datetime(2026, 11, 21, 20, 30, tzinfo=ist))
    db.add(event)
    db.commit()
    db.expire_all()
    loaded = db.get(Event, event.id)
    assert loaded.created_at.tzinfo is not None
    assert loaded.created_at == datetime(2026, 11, 21, 15, 0, tzinfo=timezone.utc)


def test_api_timestamps_carry_an_offset(student_client):
    response = student_client.post("/api/ask", json={"question": "What documents should I carry on the day of a drive?"})
    assert response.status_code == 200
    conversations = student_client.get("/api/conversations").json()
    assert conversations, "the question should have created a conversation"
    stamp = conversations[0]["updated_at"]
    assert stamp.endswith("+00:00") or stamp.endswith("Z"), stamp
