"""`match_resume`: skill extraction, scoring, and PII never reaching a model."""

from __future__ import annotations

import pytest

from app.config import get_settings
from app.models import Event, StudentProfile, User
from app.seed import DEMO_STUDENT_EMAIL
from app.tools import resume as resume_module
from app.tools.catalog import get_catalog
from app.tools.resume import FORMULA, match_resume
from app.tools.skills import extract_skills


def demo_resume(name: str = "ananya_rao") -> str:
    return (get_settings().data_dir / "resumes" / f"{name}.txt").read_text(encoding="utf-8")


# --- skills -----------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Python, SQL and Git", {"python", "sql", "git"}),
        ("Strong in DSA", {"data structures", "algorithms"}),
        ("Worked with MySQL and PostgreSQL", {"mysql", "postgresql", "sql"}),
        ("Built a RESTful service", {"rest api"}),
        ("React.js front end", {"react", "javascript"}),
        ("C, C++ and Embedded C", {"c", "c++", "embedded c"}),
        ("OOP concepts", {"object oriented programming"}),
        ("Arduino and ESP32 projects", {"microcontrollers"}),
        ("Spring Boot microservices", {"spring boot", "java", "microservices"}),
    ],
)
def test_skill_extraction(text, expected):
    assert expected <= extract_skills(text)


@pytest.mark.parametrize(
    "text,absent",
    [
        ("JavaScript developer", "java"),
        ("C# and .NET", "c"),
        ("B.Tech, Electronics and Communication Engineering", "communication"),
        ("I like to rest on Sundays", "rest api"),
        ("Clubs: chess, music", "c"),
        ("Grade C in chemistry", "c++"),
    ],
)
def test_skill_extraction_avoids_false_positives(text, absent):
    assert absent not in extract_skills(text)


def test_no_skills_in_empty_text():
    assert extract_skills("") == set()


# --- matching ---------------------------------------------------------------


def test_strong_match_for_the_right_role():
    result = match_resume(demo_resume(), get_catalog().get("nimbusware"))
    assert result.missing_required == []
    assert set(result.matched_required) == {"python", "sql", "data structures"}
    assert result.skill_score == 1.0
    assert result.match_pct >= 80
    assert result.formula == FORMULA


def test_weak_match_for_an_unrelated_role():
    result = match_resume(demo_resume(), get_catalog().get("ferrowind"))
    assert result.matched_required == []
    assert set(result.missing_required) == {"autocad", "solidworks", "thermodynamics", "manufacturing processes"}
    assert result.match_pct < 30
    assert any("Weak match" in tip for tip in result.advice)


def test_scores_rank_roles_sensibly():
    catalog = get_catalog()
    ananya = {cid: match_resume(demo_resume(), catalog.get(cid)).match_pct for cid in ("nimbusware", "veltrix", "ferrowind")}
    assert ananya["nimbusware"] > ananya["veltrix"] > ananya["ferrowind"]
    sneha = {cid: match_resume(demo_resume("sneha_kulkarni"), catalog.get(cid)).match_pct for cid in ("halcyon", "brightpath")}
    assert sneha["halcyon"] > sneha["brightpath"] + 30


def test_score_follows_the_published_formula():
    result = match_resume(demo_resume(), get_catalog().get("brightpath"))
    expected = round(100 * (0.6 * result.skill_score + 0.4 * result.semantic_score))
    assert abs(result.match_pct - expected) <= 1
    assert 0 <= result.semantic_score <= 1 and 0 <= result.skill_score <= 1


def test_missing_skill_advice_points_to_a_guide():
    result = match_resume("Python developer. Built Django sites with Git.", get_catalog().get("nimbusware"))
    assert "sql" in result.missing_required
    assert any("SQL Preparation Guide" in tip for tip in result.advice)


def test_extra_skills_are_reported():
    result = match_resume(demo_resume(), get_catalog().get("nimbusware"))
    assert "flask" in result.extra_skills and "python" not in result.extra_skills


def test_contact_details_never_reach_the_embedding_model(monkeypatch):
    seen: list[str] = []
    real_embed = resume_module.embed

    def spy(texts):
        seen.extend(texts)
        return real_embed(texts)

    monkeypatch.setattr(resume_module, "embed", spy)
    result = match_resume(demo_resume(), get_catalog().get("nimbusware"))
    joined = "\n".join(seen)
    assert seen
    assert "ananya.rao@krit.example" not in joined
    assert "90000 12345" not in joined
    assert "570017" not in joined and "Lakeview" not in joined
    assert result.redaction["counts"] == {"email": 1, "phone": 1, "address": 1, "link": 1}
    assert "[EMAIL REDACTED]" in result.redaction["preview"]


# --- API --------------------------------------------------------------------


def test_resume_match_uses_the_profile_resume(student_client, db):
    response = student_client.post("/api/tools/resume-match", json={"company_id": "nimbusware"})
    assert response.status_code == 200
    body = response.json()
    assert body["match_pct"] >= 80
    assert body["redaction"]["total"] == 4
    event = db.query(Event).filter(Event.type == "resume_match").one()
    assert event.payload["match_pct"] == body["match_pct"]
    assert "resume" not in str(event.payload).lower().replace("resume_match", "")
    assert "ananya" not in str(event.payload).lower()


def test_resume_match_with_pasted_text(student_client):
    text = "Java developer. Spring Boot REST APIs, SQL, data structures and algorithms. Call 9876543210."
    body = student_client.post("/api/tools/resume-match", json={"company_id": "orbitpay", "resume_text": text}).json()
    assert body["missing_required"] == []
    assert body["redaction"]["counts"]["phone"] == 1
    assert "9876543210" not in body["redaction"]["preview"]


def test_resume_can_be_saved_to_the_profile(student_client, db):
    user = db.query(User).filter(User.email == DEMO_STUDENT_EMAIL).one()
    original = user.profile.resume_text
    text = "Kotlin and Python developer with SQL experience and data structures practice."
    try:
        response = student_client.post(
            "/api/tools/resume-match", json={"company_id": "nimbusware", "resume_text": text, "save_to_profile": True}
        )
        assert response.status_code == 200
        db.expire_all()
        assert db.get(StudentProfile, user.id).resume_text == text
    finally:
        db.get(StudentProfile, user.id).resume_text = original
        db.commit()


def test_resume_match_without_any_resume_is_a_clear_400(student_client, db):
    user = db.query(User).filter(User.email == DEMO_STUDENT_EMAIL).one()
    original = user.profile.resume_text
    user.profile.resume_text = None
    db.commit()
    try:
        response = student_client.post("/api/tools/resume-match", json={"company_id": "nimbusware"})
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "no_resume"
    finally:
        db.get(StudentProfile, user.id).resume_text = original
        db.commit()


def test_resume_text_length_limit(student_client):
    response = student_client.post("/api/tools/resume-match", json={"company_id": "nimbusware", "resume_text": "x" * 20001})
    assert response.status_code == 422


def test_resume_extract_reads_text_files(student_client):
    files = {"file": ("my resume.txt", demo_resume().encode("utf-8"), "text/plain")}
    body = student_client.post("/api/tools/resume-extract", files=files).json()
    assert body["filename"] == "my-resume.txt"
    assert "Django" in body["text"]


def test_resume_extract_rejects_other_types(student_client):
    files = {"file": ("resume.docx", b"PK\x03\x04fake", "application/octet-stream")}
    response = student_client.post("/api/tools/resume-extract", files=files)
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_file_type"
