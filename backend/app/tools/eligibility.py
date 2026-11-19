"""`check_eligibility`: a student's profile against a company's criteria.

Deterministic on purpose. Each criterion returns pass or fail with the
required value, the student's value and a reason, so the verdict can be
checked by hand. A missing profile field fails that criterion with a clear
message instead of being guessed.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from app.models import StudentProfile
from app.tools.catalog import Company

CRITERIA = ("cgpa", "backlogs", "branch", "batch")
LABELS = {"cgpa": "CGPA", "backlogs": "Active backlogs", "branch": "Branch", "batch": "Batch"}


@dataclass
class StudentProfileData:
    branch: str | None = None
    cgpa: float | None = None
    active_backlogs: int | None = None
    batch: int | None = None

    @classmethod
    def from_model(cls, profile: StudentProfile | None) -> "StudentProfileData":
        if profile is None:
            return cls()
        return cls(
            branch=profile.branch, cgpa=profile.cgpa, active_backlogs=profile.active_backlogs, batch=profile.batch
        )


@dataclass
class Criterion:
    name: str
    label: str
    passed: bool
    required: str
    actual: str
    reason: str


@dataclass
class EligibilityResult:
    company_id: str
    company_name: str
    role: str
    ctc_label: str
    category: str
    eligible: bool
    criteria: list[Criterion]

    @property
    def failed(self) -> list[Criterion]:
        return [criterion for criterion in self.criteria if not criterion.passed]

    @property
    def summary(self) -> str:
        if self.eligible:
            return f"You meet all {len(self.criteria)} criteria for {self.company_name}."
        return f"Not eligible for {self.company_name}: {self.reasons_text}"

    @property
    def reasons_text(self) -> str:
        """Failed reasons as one sentence: "a; b; c." """
        return "; ".join(criterion.reason.rstrip(".") for criterion in self.failed) + "."

    def to_dict(self) -> dict:
        data = asdict(self)
        data["summary"] = self.summary
        return data


def _missing(name: str, required: str) -> Criterion:
    return Criterion(
        name=name,
        label=LABELS[name],
        passed=False,
        required=required,
        actual="not set",
        reason=f"Your profile has no {LABELS[name].lower()}. Add it to your profile to check this criterion.",
    )


def _fmt(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".") if value != int(value) else f"{value:.1f}"


def _check_cgpa(profile: StudentProfileData, company: Company) -> Criterion:
    required = f"at least {_fmt(company.min_cgpa)}"
    if profile.cgpa is None:
        return _missing("cgpa", required)
    # Compare at two decimals so 7.0 versus 6.999999 float noise cannot flip a verdict.
    passed = round(profile.cgpa, 2) >= round(company.min_cgpa, 2)
    if passed:
        reason = f"Your CGPA {_fmt(profile.cgpa)} meets the minimum of {_fmt(company.min_cgpa)}."
    else:
        gap = round(company.min_cgpa - profile.cgpa, 2)
        reason = f"Your CGPA {_fmt(profile.cgpa)} is {gap:g} below the minimum of {_fmt(company.min_cgpa)}."
    return Criterion("cgpa", LABELS["cgpa"], passed, required, _fmt(profile.cgpa), reason)


def _check_backlogs(profile: StudentProfileData, company: Company) -> Criterion:
    limit = company.max_active_backlogs
    required = "none allowed" if limit == 0 else f"at most {limit}"
    if profile.active_backlogs is None:
        return _missing("backlogs", required)
    count = profile.active_backlogs
    passed = count <= limit
    if passed:
        reason = "You have no active backlogs." if count == 0 else f"{count} active backlog(s) is within the limit of {limit}."
    elif limit == 0:
        reason = f"You have {count} active backlog(s); {company.name} allows none."
    else:
        reason = f"You have {count} active backlogs; {company.name} allows at most {limit}."
    return Criterion("backlogs", LABELS["backlogs"], passed, required, str(count), reason)


def _check_branch(profile: StudentProfileData, company: Company) -> Criterion:
    allowed = company.allowed_branches
    required = ", ".join(allowed)
    if not profile.branch:
        return _missing("branch", required)
    branch = profile.branch.strip().upper()
    passed = branch in allowed
    reason = (
        f"{branch} is one of the eligible branches."
        if passed
        else f"{branch} is not eligible; {company.name} accepts {required}."
    )
    return Criterion("branch", LABELS["branch"], passed, required, branch, reason)


def _check_batch(profile: StudentProfileData, company: Company) -> Criterion:
    required = f"{company.batch} graduates"
    if profile.batch is None:
        return _missing("batch", required)
    passed = profile.batch == company.batch
    reason = (
        f"You graduate in {profile.batch}, the batch this drive is for."
        if passed
        else f"This drive is for the {company.batch} batch; you graduate in {profile.batch}."
    )
    return Criterion("batch", LABELS["batch"], passed, required, str(profile.batch), reason)


def check_eligibility(profile: StudentProfileData, company: Company) -> EligibilityResult:
    criteria = [
        _check_cgpa(profile, company),
        _check_backlogs(profile, company),
        _check_branch(profile, company),
        _check_batch(profile, company),
    ]
    return EligibilityResult(
        company_id=company.id,
        company_name=company.name,
        role=company.role,
        ctc_label=company.ctc_label,
        category=company.category,
        eligible=all(criterion.passed for criterion in criteria),
        criteria=criteria,
    )


def check_all(profile: StudentProfileData, companies: list[Company]) -> list[EligibilityResult]:
    """Every company, eligible ones first, then by name."""
    results = [check_eligibility(profile, company) for company in companies]
    return sorted(results, key=lambda result: (not result.eligible, result.company_name.lower()))
