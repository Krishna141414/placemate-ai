"""Company catalogue.

Each company is one markdown file. Its YAML front matter holds the structured
criteria that the tools use, and its body is what the RAG pipeline indexes.
Reading both from the same file means they cannot drift apart.
"""

from __future__ import annotations

import logging
import threading
from datetime import date
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.config import get_settings
from app.errors import AppError
from app.rag.loader import parse_front_matter

logger = logging.getLogger("placemate.catalog")


class Company(BaseModel):
    id: str
    name: str
    role: str
    ctc_lpa: list[float] = Field(min_length=2, max_length=2)
    min_cgpa: float
    max_active_backlogs: int
    allowed_branches: list[str]
    batch: int
    required_skills: list[str] = []
    preferred_skills: list[str] = []
    rounds: list[str] = []
    apply_by: date | None = None
    description: str = ""  # markdown body, used as the job description text

    @field_validator("allowed_branches")
    @classmethod
    def _upper_branches(cls, value: list[str]) -> list[str]:
        return [branch.strip().upper() for branch in value]

    @field_validator("required_skills", "preferred_skills")
    @classmethod
    def _lower_skills(cls, value: list[str]) -> list[str]:
        return [skill.strip().lower() for skill in value]

    @property
    def category(self) -> str:
        """Placement-policy category, decided by the lower CTC figure."""
        low = self.ctc_lpa[0]
        if low >= 10:
            return "Dream"
        if low >= 6:
            return "Standard"
        return "Regular"

    @property
    def ctc_label(self) -> str:
        low, high = self.ctc_lpa
        if low == high:
            return f"{low:g} LPA"
        return f"{low:g} to {high:g} LPA"


class Catalog:
    def __init__(self, companies: dict[str, Company]) -> None:
        self._companies = companies

    def all(self) -> list[Company]:
        return sorted(self._companies.values(), key=lambda c: c.name.lower())

    def find(self, company_id: str) -> Company | None:
        return self._companies.get((company_id or "").strip().lower())

    def get(self, company_id: str) -> Company:
        company = self.find(company_id)
        if company is None:
            raise AppError(404, "company_not_found", "That company is not in the placement list.")
        return company

    def __len__(self) -> int:
        return len(self._companies)


def load_catalog(companies_dir: Path) -> Catalog:
    companies: dict[str, Company] = {}
    for path in sorted(companies_dir.glob("*.md")):
        meta, body = parse_front_matter(path.read_text(encoding="utf-8"))
        if meta.get("doc_type") != "company":
            continue
        try:
            company = Company(**{k: v for k, v in meta.items() if k != "doc_type"}, description=body.strip())
        except ValidationError as exc:
            logger.warning("company_file_skipped", extra={"file": path.name, "errors": exc.error_count()})
            continue
        companies[company.id.lower()] = company
    return Catalog(companies)


_catalog: Catalog | None = None
_lock = threading.Lock()


def get_catalog() -> Catalog:
    global _catalog
    if _catalog is None:
        with _lock:
            if _catalog is None:
                _catalog = load_catalog(get_settings().data_dir / "companies")
    return _catalog


def reload_catalog() -> Catalog:
    global _catalog
    with _lock:
        _catalog = load_catalog(get_settings().data_dir / "companies")
    return _catalog
