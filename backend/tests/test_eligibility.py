"""`check_eligibility`: boundary cases for every criterion, and the API."""

from __future__ import annotations

import pytest

from app.models import Event
from app.tools.catalog import Company, get_catalog
from app.tools.eligibility import StudentProfileData, check_all, check_eligibility


def company(**overrides) -> Company:
    data = {
        "id": "acme",
        "name": "Acme Corp",
        "role": "Engineer",
        "ctc_lpa": [7.0, 8.0],
        "min_cgpa": 7.0,
        "max_active_backlogs": 1,
        "allowed_branches": ["CSE", "IT"],
        "batch": 2027,
    }
    data.update(overrides)
    return Company(**data)


def student(**overrides) -> StudentProfileData:
    data = {"branch": "CSE", "cgpa": 8.0, "active_backlogs": 0, "batch": 2027}
    data.update(overrides)
    return StudentProfileData(**data)


def by_name(result):
    return {criterion.name: criterion for criterion in result.criteria}


def test_meets_everything():
    result = check_eligibility(student(), company())
    assert result.eligible is True
    assert [c.name for c in result.criteria] == ["cgpa", "backlogs", "branch", "batch"]
    assert all(c.passed for c in result.criteria)
    assert result.summary == "You meet all 4 criteria for Acme Corp."


@pytest.mark.parametrize(
    "cgpa,minimum,passed",
    [
        (7.0, 7.0, True),  # exactly at the cut-off passes
        (6.99, 7.0, False),
        (7.01, 7.0, True),
        (6.9999999, 7.0, True),  # float noise must not flip the verdict
        (8.5, 8.5, True),
        (8.49, 8.5, False),
    ],
)
def test_cgpa_boundaries(cgpa, minimum, passed):
    result = check_eligibility(student(cgpa=cgpa), company(min_cgpa=minimum))
    assert by_name(result)["cgpa"].passed is passed
    assert result.eligible is passed


def test_cgpa_failure_reason_names_the_gap():
    criterion = by_name(check_eligibility(student(cgpa=7.8), company(min_cgpa=8.5)))["cgpa"]
    assert criterion.reason == "Your CGPA 7.8 is 0.7 below the minimum of 8.5."
    assert criterion.required == "at least 8.5" and criterion.actual == "7.8"


@pytest.mark.parametrize(
    "backlogs,limit,passed",
    [(0, 0, True), (1, 0, False), (1, 1, True), (2, 1, False), (2, 2, True), (3, 2, False)],
)
def test_backlog_boundaries(backlogs, limit, passed):
    criterion = by_name(check_eligibility(student(active_backlogs=backlogs), company(max_active_backlogs=limit)))["backlogs"]
    assert criterion.passed is passed


def test_zero_backlog_rule_is_worded_clearly():
    criterion = by_name(check_eligibility(student(active_backlogs=1), company(max_active_backlogs=0)))["backlogs"]
    assert criterion.required == "none allowed"
    assert criterion.reason == "You have 1 active backlog(s); Acme Corp allows none."


@pytest.mark.parametrize("branch", ["cse", "CSE", " Cse ", "it"])
def test_branch_is_case_and_space_insensitive(branch):
    assert by_name(check_eligibility(student(branch=branch), company()))["branch"].passed


def test_wrong_branch_fails_with_the_allowed_list():
    criterion = by_name(check_eligibility(student(branch="MECH"), company()))["branch"]
    assert not criterion.passed
    assert criterion.reason == "MECH is not eligible; Acme Corp accepts CSE, IT."


def test_wrong_batch_fails():
    result = check_eligibility(student(batch=2027), company(batch=2026))
    criterion = by_name(result)["batch"]
    assert not criterion.passed and not result.eligible
    assert criterion.reason == "This drive is for the 2026 batch; you graduate in 2027."


def test_eligibility_incomplete_profile():
    """Review focus 3: missing fields are reported, never guessed."""
    result = check_eligibility(StudentProfileData(branch="CSE"), company())
    assert result.eligible is False
    missing = [c for c in result.criteria if c.actual == "not set"]
    assert {c.name for c in missing} == {"cgpa", "backlogs", "batch"}
    assert all("Add it to your profile" in c.reason for c in missing)
    assert by_name(result)["branch"].passed


def test_multiple_failures_are_all_reported_in_one_summary():
    result = check_eligibility(student(cgpa=6.0, active_backlogs=3, branch="EEE", batch=2026), company())
    assert len(result.failed) == 4
    assert result.summary.startswith("Not eligible for Acme Corp: ")
    assert ".;" not in result.summary and result.summary.endswith(".")


def test_check_all_lists_eligible_companies_first():
    results = check_all(student(cgpa=7.8, active_backlogs=1), get_catalog().all())
    flags = [result.eligible for result in results]
    assert flags == sorted(flags, reverse=True)
    assert len(results) == 12


def test_demo_student_against_the_real_catalog():
    """The sample data is built so each criterion fails for some company."""
    demo = student(cgpa=7.8, active_backlogs=1, branch="CSE", batch=2027)
    results = {r.company_id: r for r in check_all(demo, get_catalog().all())}
    assert {cid for cid, r in results.items() if r.eligible} == {"nimbusware", "quantaleaf", "kairoscloud", "brightpath", "tessera"}
    assert {c.name for c in results["orbitpay"].failed} == {"cgpa"}
    assert {c.name for c in results["veltrix"].failed} == {"cgpa", "backlogs"}
    assert {c.name for c in results["lumengrid"].failed} == {"backlogs"}
    assert {c.name for c in results["halcyon"].failed} == {"branch"}
    assert {c.name for c in results["zephyrnet"].failed} == {"batch"}


def test_company_categories_follow_the_policy():
    catalog = get_catalog()
    assert catalog.get("veltrix").category == "Dream"  # 12 LPA
    assert catalog.get("orbitpay").category == "Dream"  # exactly 10 LPA
    assert catalog.get("mosaicai").category == "Standard"  # 9 to 11: the lower figure decides
    assert catalog.get("tessera").category == "Regular"
    assert catalog.get("tessera").ctc_label == "4.25 LPA"


# --- API --------------------------------------------------------------------


def test_eligibility_api(student_client, db):
    response = student_client.post("/api/tools/eligibility", json={"company_id": "orbitpay"})
    assert response.status_code == 200
    body = response.json()
    assert body["eligible"] is False
    assert [c["name"] for c in body["criteria"] if not c["passed"]] == ["cgpa"]
    assert body["category"] == "Dream"
    event = db.query(Event).filter(Event.type == "eligibility_check").one()
    assert event.payload == {"company_id": "orbitpay", "eligible": False, "failed": ["cgpa"]}


def test_eligibility_all_api(student_client):
    body = student_client.post("/api/tools/eligibility/all").json()
    assert body["total"] == 12 and body["eligible_count"] == 5
    assert all(r["eligible"] for r in body["results"][:5])


def test_unknown_company_is_404(student_client):
    """Review focus 2."""
    response = student_client.post("/api/tools/eligibility", json={"company_id": "nonexistent"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "company_not_found"


@pytest.mark.parametrize("company_id", ["", "../etc", "A" * 100, "acme corp", "<script>"])
def test_malformed_company_id_is_422(student_client, company_id):
    assert student_client.post("/api/tools/eligibility", json={"company_id": company_id}).status_code == 422


def test_eligibility_is_for_students(coordinator_client, client):
    assert coordinator_client.post("/api/tools/eligibility", json={"company_id": "nimbusware"}).status_code == 403
    assert client.post("/api/tools/eligibility", json={"company_id": "nimbusware"}).status_code == 401
