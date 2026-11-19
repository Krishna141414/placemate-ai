"""One function per agent step, plus fallbacks for the required steps.

Every step function takes a `StepContext` and returns `(output, detail)`.
A step signals failure by raising `StepError`; the executor decides whether
to retry, fall back or skip.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.agent.plan_builder import build_prep_plan, template_summary
from app.agent.state import AgentState
from app.llm import router
from app.llm.base import LLMRequest, Passage, ProviderError
from app.models import StudentProfile, User
from app.rag.index import get_index
from app.rag.prompts import NOT_IN_DOCUMENTS, SYSTEM_PROMPT, build_prompt
from app.rag.retriever import retrieve
from app.security.injection import filter_output, scan_user_input
from app.tools.catalog import Company
from app.tools.eligibility import StudentProfileData, check_eligibility
from app.tools.resume import match_resume

_TIP_SECTION_RE = re.compile(r"tip|learn|differently|advice", re.IGNORECASE)
_BULLET_RE = re.compile(r"^\s*[-*]\s+(.+)$")


class StepError(Exception):
    """A step failed. The message is shown to the student, so keep it plain."""


@dataclass
class StepContext:
    db: Session
    user: User
    profile: StudentProfile | None
    company: Company
    state: AgentState
    faults: dict[str, int] = field(default_factory=dict)
    today: date | None = None

    def maybe_fault(self, step: str) -> None:
        """Simulated failure for demos and tests: fail this step N times."""
        if self.faults.get(step, 0) > 0:
            self.faults[step] -= 1
            raise StepError("Simulated failure (demo fault injection).")


def _source(item) -> dict[str, Any]:
    chunk = item.chunk
    return {
        "doc_key": chunk.doc_key,
        "title": chunk.title,
        "section": chunk.section,
        "snippet": " ".join(chunk.text.split())[:240],
        "text": chunk.text,
        "score": round(float(item.score), 3),
    }


# --- steps ------------------------------------------------------------------


def step_check_eligibility(ctx: StepContext) -> tuple[dict[str, Any], str]:
    ctx.maybe_fault("check_eligibility")
    result = check_eligibility(StudentProfileData.from_model(ctx.profile), ctx.company)
    data = result.to_dict()
    if result.eligible:
        detail = f"Eligible: all {len(result.criteria)} criteria pass."
    else:
        detail = "Not eligible: " + result.reasons_text
    return data, detail


def step_match_resume(ctx: StepContext) -> tuple[dict[str, Any], str]:
    ctx.maybe_fault("match_resume")
    resume = ctx.profile.resume_text if ctx.profile else None
    if not resume:
        raise StepError("No resume found in the profile.")
    result = match_resume(resume, ctx.company).to_dict()
    redacted = result["redaction"]["total"]
    detail = f"{result['match_pct']}% match; {len(result['missing_required'])} required skill(s) missing."
    if redacted:
        detail += f" {redacted} contact detail(s) removed before matching."
    return result, detail


def step_retrieve_process(ctx: StepContext) -> tuple[dict[str, Any], str]:
    ctx.maybe_fault("retrieve_process")
    query = f"{ctx.company.name} selection process rounds"
    result = retrieve(query, mode="final", company_id=ctx.company.id, doc_types=["company"], top_k=3)
    if not result.results:
        raise StepError("No company document matched the query.")
    sources = [_source(item) for item in result.results]
    return {"sources": sources, "rounds": ctx.company.rounds, "used_fallback": False}, (
        f"Found {len(sources)} passages from the {ctx.company.name} profile; {len(ctx.company.rounds)} rounds."
    )


def fallback_retrieve_process(ctx: StepContext) -> tuple[dict[str, Any], str]:
    """Use the rounds listed in the company profile's structured data."""
    return {"sources": [], "rounds": ctx.company.rounds, "used_fallback": True}, (
        f"Search failed, so the {len(ctx.company.rounds)} rounds were read from the company profile instead."
    )


def _tips_for(company_id: str) -> list[dict[str, str]]:
    """Bullet points from the "Tips" / "What I learned" sections of this company's write-ups."""
    tips: list[dict[str, str]] = []
    for chunk in get_index().chunks:
        if chunk.company_id != company_id or chunk.doc_type != "interview" or not _TIP_SECTION_RE.search(chunk.section):
            continue
        for line in chunk.text.split("\n"):
            match = _BULLET_RE.match(line)
            if match and not scan_user_input(match.group(1)).blocked:
                tips.append({"text": match.group(1).strip(), "source": chunk.title})
    return tips


def step_retrieve_experiences(ctx: StepContext) -> tuple[dict[str, Any], str]:
    ctx.maybe_fault("retrieve_experiences")
    query = f"{ctx.company.name} interview experience questions tips"
    result = retrieve(query, mode="final", company_id=ctx.company.id, doc_types=["interview"], top_k=4)
    sources = [_source(item) for item in result.results]
    tips = _tips_for(ctx.company.id)
    if not sources:
        return {"sources": [], "tips": []}, f"No interview experiences on file for {ctx.company.name}; the plan uses the guides only."
    writeups = len({source["doc_key"] for source in sources})
    return {"sources": sources, "tips": tips}, f"Found {len(sources)} passages from {writeups} write-up(s) and {len(tips)} tips."


def _missing_skills(ctx: StepContext) -> list[str]:
    resume = ctx.state.step("match_resume")
    if resume.status in ("done", "recovered") and resume.output:
        return resume.output.get("missing_required", [])
    return []


def _base_plan(ctx: StepContext) -> dict[str, Any]:
    process = ctx.state.output("retrieve_process")
    experiences = ctx.state.output("retrieve_experiences") or {}
    return build_prep_plan(
        ctx.company,
        missing_skills=_missing_skills(ctx),
        process_rounds=process.get("rounds", ctx.company.rounds),
        tips=experiences.get("tips", []),
        today=ctx.today,
    )


def step_build_plan(ctx: StepContext) -> tuple[dict[str, Any], str]:
    ctx.maybe_fault("build_plan")
    plan = _base_plan(ctx)

    process = ctx.state.output("retrieve_process").get("sources", [])
    experiences = (ctx.state.output("retrieve_experiences") or {}).get("sources", [])
    sources = (process[:2] + experiences[:3])[:5]
    if not sources:
        raise StepError("No passages to base the summary on.")

    passages = [
        Passage(n=n, title=s["title"], section=s["section"], text=s["text"], score=s["score"])
        for n, s in enumerate(sources, start=1)
    ]
    question = (
        f"How should a student prepare for the {ctx.company.name} {ctx.company.role} selection process? "
        "Name the rounds and what each one tests."
    )
    request = LLMRequest(
        system=SYSTEM_PROMPT, prompt=build_prompt(question, passages), question=question, passages=passages, max_tokens=400
    )
    allowed = "\n".join(p.text for p in passages)

    def accept(text: str) -> str | None:
        if NOT_IN_DOCUMENTS in text:
            return "no answer in sources"
        return None if filter_output(text, len(passages), allowed)[1] else "no valid citation"

    try:
        llm = router.generate(request, accept=accept)
    except ProviderError as exc:
        raise StepError("No model could write the summary.") from exc
    text, citations, _ = filter_output(llm.text, len(passages), allowed)
    if not text or NOT_IN_DOCUMENTS in text:
        raise StepError("The summary was empty after checks.")

    plan.update(
        summary=text,
        summary_citations=citations,
        summary_sources=[{k: s[k] for k in ("doc_key", "title", "section", "snippet")} for s in sources],
        summary_provider=llm.provider,
    )
    detail = f"{plan['weeks_count']} weeks, {sum(len(w['tasks']) for w in plan['weeks'])} tasks; summary by {llm.provider}."
    return {"plan": plan, "provider": llm.provider, "fallbacks": llm.fallbacks}, detail


def fallback_build_plan(ctx: StepContext) -> tuple[dict[str, Any], str]:
    """The rule-based plan with a template summary. Needs no model."""
    plan = _base_plan(ctx)
    plan.update(summary=template_summary(ctx.company, plan["focus_skills"], plan["rounds"]), summary_provider="template")
    return {"plan": plan, "provider": "template", "fallbacks": []}, (
        f"Summary written from a template; {plan['weeks_count']}-week plan built from rules."
    )


STEP_FUNCTIONS = {
    "check_eligibility": step_check_eligibility,
    "match_resume": step_match_resume,
    "retrieve_process": step_retrieve_process,
    "retrieve_experiences": step_retrieve_experiences,
    "build_plan": step_build_plan,
}

FALLBACKS = {
    "retrieve_process": fallback_retrieve_process,
    "build_plan": fallback_build_plan,
}
