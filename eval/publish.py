"""Merge the evaluation runs and the latest test results into one file.

    python eval/publish.py

Writes eval/results/summary.json and copies it to
frontend/public/eval-summary.json, which the landing and Evaluation pages
read. Every number there comes from a run's own output files.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "eval" / "results"
PUBLIC = ROOT / "frontend" / "public"
ORDER = ("gemini", "local", "extractive")


def main() -> None:
    runs = {}
    for provider in ORDER:
        path = RESULTS / provider / "summary.json"
        if path.exists():
            runs[provider] = json.loads(path.read_text(encoding="utf-8"))
    if not runs:
        raise SystemExit("No evaluation results found. Run eval/run_eval.py first.")

    tests_path = RESULTS / "tests.json"
    tests = json.loads(tests_path.read_text(encoding="utf-8")) if tests_path.exists() else None

    primary = next(p for p in ORDER if p in runs)
    merged = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "primary": primary,
        "runs": runs,
        "tests": tests,
        "cases_file": "eval/cases.json",
    }
    out = RESULTS / "summary.json"
    out.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    PUBLIC.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(out, PUBLIC / "eval-summary.json")
    print(f"published {', '.join(runs)} (primary: {primary}) to {out} and frontend/public/eval-summary.json")


if __name__ == "__main__":
    main()
