"""Agent run state. Saved to `agent_runs.state` after every step."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

# pending -> running -> done | recovered (retry worked) | fallback | skipped | failed
# The approval gate uses: pending -> waiting -> approved | rejected
STEP_STATUSES = ("pending", "running", "done", "recovered", "fallback", "skipped", "failed", "waiting", "approved", "rejected")


@dataclass
class StepRecord:
    name: str
    label: str
    kind: str  # tool | retrieval | llm | gate
    tool: str  # what is called, shown in the tool-call card
    required: bool
    description: str
    status: str = "pending"
    attempts: int = 0
    detail: str = ""
    input: dict[str, Any] = field(default_factory=dict)
    output: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    recovery: str | None = None  # retry | fallback | skip
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AgentState:
    goal: str
    company_id: str
    company_name: str
    max_steps: int
    retries: int
    steps: list[StepRecord]
    tool_calls: int = 0
    outcome: str = ""
    message: str = ""
    pending: dict[str, Any] | None = None  # what approval would save
    alternatives: list[dict[str, Any]] = field(default_factory=list)
    saved: dict[str, Any] | None = None  # ids written after approval

    def step(self, name: str) -> StepRecord:
        return next(record for record in self.steps if record.name == name)

    def output(self, name: str) -> dict[str, Any]:
        return self.step(name).output

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["steps"] = [record.to_dict() for record in self.steps]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentState":
        data = dict(data)
        data["steps"] = [StepRecord(**record) for record in data.get("steps", [])]
        return cls(**data)
