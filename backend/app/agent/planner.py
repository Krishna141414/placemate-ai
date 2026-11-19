"""Planner: the step list for "Prepare me for <company>".

The goal has a known shape, so the plan is built by rules rather than by a
model. That keeps it testable and makes it work the same with every LLM
provider, including the extractive fallback. The planner still adapts to
the student: without a resume, the resume step is planned as skipped.
"""

from __future__ import annotations

from app.agent.state import StepRecord
from app.tools.catalog import Company


def make_plan(company: Company, *, has_resume: bool) -> list[StepRecord]:
    steps = [
        StepRecord(
            name="check_eligibility",
            label="Check eligibility",
            kind="tool",
            tool="check_eligibility",
            required=True,
            description=f"Compare your CGPA, backlogs, branch and batch with {company.name}'s criteria.",
            input={"company_id": company.id},
        ),
        StepRecord(
            name="match_resume",
            label="Match resume",
            kind="tool",
            tool="match_resume",
            required=False,
            description="Find the required skills your resume shows and the ones it is missing. Contact details are removed first.",
            input={"company_id": company.id, "resume": "from profile (redacted)"},
        ),
        StepRecord(
            name="retrieve_process",
            label="Retrieve selection process",
            kind="retrieval",
            tool="retrieve",
            required=True,
            description=f"Search the documents for {company.name}'s rounds and what each one tests.",
            input={"query": f"{company.name} selection process rounds", "filter": "company profile"},
        ),
        StepRecord(
            name="retrieve_experiences",
            label="Retrieve interview experiences",
            kind="retrieval",
            tool="retrieve",
            required=False,
            description="Search seniors' interview write-ups for this company for questions and tips.",
            input={"query": f"{company.name} interview experience questions tips", "filter": "interview experiences"},
        ),
        StepRecord(
            name="build_plan",
            label="Draft week-by-week plan",
            kind="llm",
            tool="build_prep_plan",
            required=True,
            description="Turn the gaps, the rounds and the tips into a weekly plan, with a short cited summary.",
            input={"company_id": company.id},
        ),
        StepRecord(
            name="approval",
            label="Your approval",
            kind="gate",
            tool="approval",
            required=True,
            description="Nothing is saved until you approve. Approve saves the plan and adds the application to your tracker.",
        ),
    ]
    if not has_resume:
        resume = steps[1]
        resume.status = "skipped"
        resume.recovery = "skip"
        resume.detail = "No resume in your profile, so this optional step is skipped. Add one on the Resume Match page."
        resume.input = {"company_id": company.id, "resume": "none"}
    return steps
