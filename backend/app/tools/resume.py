"""`match_resume`: a resume against one company's job description.

1. Remove contact details (`redact_pii`). Nothing after this step sees them.
2. Skill match: canonical skills found in the resume versus the company's
   required and preferred skills.
3. Semantic match: embedding similarity between resume sections and job
   description sections, so related experience counts even when the exact
   keyword is missing.
4. Score: match % = 60% skill score + 40% semantic score.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

import numpy as np

from app.rag.models import embed
from app.security.pii import RedactionResult, redact_pii
from app.tools.catalog import Company
from app.tools.skills import extract_skills

SKILL_WEIGHT = 0.6
SEMANTIC_WEIGHT = 0.4
REQUIRED_WEIGHT = 0.75
PREFERRED_WEIGHT = 0.25
# MiniLM cosine similarity between a resume section and a job description
# section rarely goes above 0.7 even for a strong match, or below 0.1 for an
# unrelated one. This range is mapped onto 0 to 1.
SIM_FLOOR = 0.15
SIM_CEILING = 0.60
CHUNK_WORDS = 90
PREVIEW_CHARS = 420
JD_SECTIONS = ("role", "skills they look for", "selection process", "about the company")

FORMULA = (
    "match % = 60% skill score + 40% semantic score. "
    "Skill score = 75% of required skills found + 25% of preferred skills found. "
    "Semantic score = how closely your resume sections match the job description (embedding similarity)."
)

GUIDE_FOR_SKILL = {
    "data structures": "Data Structures and Algorithms Preparation Guide",
    "algorithms": "Data Structures and Algorithms Preparation Guide",
    "sql": "SQL Preparation Guide",
    "dbms": "SQL Preparation Guide",
    "system design": "System Design Basics Guide",
    "aptitude": "Aptitude Test Preparation Guide",
    "communication": "HR Interview Preparation Guide",
}


@dataclass
class ResumeMatch:
    company_id: str
    company_name: str
    role: str
    match_pct: int
    skill_score: float
    semantic_score: float
    matched_required: list[str]
    missing_required: list[str]
    matched_preferred: list[str]
    missing_preferred: list[str]
    extra_skills: list[str]
    redaction: dict
    formula: str
    advice: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def _chunks(text: str, size: int = CHUNK_WORDS) -> list[str]:
    """Paragraph-ish pieces of about `size` words."""
    pieces: list[str] = []
    current: list[str] = []
    for block in re.split(r"\n\s*\n", text):
        words = block.split()
        if not words:
            continue
        if current and len(current) + len(words) > size:
            pieces.append(" ".join(current))
            current = []
        current.extend(words)
        while len(current) > size:
            pieces.append(" ".join(current[:size]))
            current = current[size:]
    if current:
        pieces.append(" ".join(current))
    return pieces


def job_description(company: Company) -> list[str]:
    """The parts of a company file that describe the job, as chunks."""
    sections = re.split(r"\n(?=## )", company.description)
    chosen = [s for s in sections if s.lstrip("# ").split("\n", 1)[0].strip().lower() in JD_SECTIONS]
    header = (
        f"{company.role} at {company.name}. Required skills: {', '.join(company.required_skills)}. "
        f"Preferred skills: {', '.join(company.preferred_skills)}."
    )
    return [header, *[chunk for section in chosen for chunk in _chunks(section)]]


def semantic_similarity(resume_text: str, company: Company) -> float:
    """For each JD chunk, its best-matching resume chunk; averaged and rescaled."""
    resume_chunks = _chunks(resume_text)
    jd_chunks = job_description(company)
    if not resume_chunks or not jd_chunks:
        return 0.0
    vectors = embed(resume_chunks + jd_chunks)
    resume_vecs, jd_vecs = vectors[: len(resume_chunks)], vectors[len(resume_chunks):]
    best_per_jd = (jd_vecs @ resume_vecs.T).max(axis=1)
    raw = float(np.mean(best_per_jd))
    return max(0.0, min(1.0, (raw - SIM_FLOOR) / (SIM_CEILING - SIM_FLOOR)))


def _advice(company: Company, missing_required: list[str], missing_preferred: list[str], match_pct: int) -> list[str]:
    tips: list[str] = []
    for skill in missing_required:
        guide = GUIDE_FOR_SKILL.get(skill)
        line = f"{company.name} requires {skill}, and your resume does not show it."
        line += f" Start with the {guide}." if guide else " If you have used it, add a project line that shows it."
        tips.append(line)
    if missing_preferred:
        tips.append(f"Good to have for this role: {', '.join(missing_preferred)}.")
    if match_pct >= 75:
        tips.append("Strong match. Put the most relevant project first and be ready to explain every line of it.")
    elif match_pct >= 50:
        tips.append("Reasonable match. Close the required-skill gaps first; they carry the most weight.")
    else:
        tips.append("Weak match for now. Consider companies whose required skills you already have, and use this role as a target.")
    return tips


def redaction_summary(result: RedactionResult) -> dict:
    preview = result.text[:PREVIEW_CHARS]
    if len(result.text) > PREVIEW_CHARS:
        preview = preview.rsplit("\n", 1)[0] + "\n..."
    return {"counts": result.counts, "total": result.total, "preview": preview}


def match_resume(resume_text: str, company: Company) -> ResumeMatch:
    redacted = redact_pii(resume_text)
    text = redacted.text  # from here on, only redacted text is used

    skills = extract_skills(text)
    required, preferred = company.required_skills, company.preferred_skills
    matched_required = [s for s in required if s in skills]
    missing_required = [s for s in required if s not in skills]
    matched_preferred = [s for s in preferred if s in skills]
    missing_preferred = [s for s in preferred if s not in skills]

    required_cov = len(matched_required) / len(required) if required else 1.0
    if preferred:
        skill_score = REQUIRED_WEIGHT * required_cov + PREFERRED_WEIGHT * (len(matched_preferred) / len(preferred))
    else:
        skill_score = required_cov
    semantic = semantic_similarity(text, company)
    match_pct = round(100 * (SKILL_WEIGHT * skill_score + SEMANTIC_WEIGHT * semantic))

    wanted = set(required) | set(preferred)
    extra = sorted(skills - wanted)[:12]

    return ResumeMatch(
        company_id=company.id,
        company_name=company.name,
        role=company.role,
        match_pct=int(match_pct),
        skill_score=round(skill_score, 3),
        semantic_score=round(semantic, 3),
        matched_required=matched_required,
        missing_required=missing_required,
        matched_preferred=matched_preferred,
        missing_preferred=missing_preferred,
        extra_skills=extra,
        redaction=redaction_summary(redacted),
        formula=FORMULA,
        advice=_advice(company, missing_required, missing_preferred, int(match_pct)),
    )
