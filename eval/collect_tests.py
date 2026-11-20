"""Summarise the latest pytest run into eval/results/tests.json.

Reads the JUnit XML and coverage JSON written by scripts/test.ps1, so the
Evaluation page and the docs quote the real numbers from the last run.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "docs" / "evidence"
RESULTS = ROOT / "eval" / "results"


def main() -> None:
    junit = EVIDENCE / "pytest-junit.xml"
    coverage = EVIDENCE / "coverage.json"
    if not junit.exists():
        raise SystemExit("No JUnit file found. Run scripts/test.ps1 first.")

    tree = ET.parse(junit)
    suites = tree.getroot()
    suite = suites if suites.tag == "testsuite" else suites.find("testsuite")
    per_file: Counter[str] = Counter()
    failed_names = []
    for case in suite.iter("testcase"):
        module = case.get("classname", "").split(".")[-1]
        per_file[module] += 1
        if case.find("failure") is not None or case.find("error") is not None:
            failed_names.append(f"{module}::{case.get('name')}")

    total = int(suite.get("tests", 0))
    failures = int(suite.get("failures", 0)) + int(suite.get("errors", 0))
    skipped = int(suite.get("skipped", 0))
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "run_at": suite.get("timestamp"),
        "total": total,
        "passed": total - failures - skipped,
        "failed": failures,
        "skipped": skipped,
        "duration_s": round(float(suite.get("time", 0)), 1),
        "per_file": dict(sorted(per_file.items())),
        "failed_tests": failed_names,
    }

    if coverage.exists():
        data = json.loads(coverage.read_text(encoding="utf-8"))
        summary["coverage_pct"] = round(data["totals"]["percent_covered"], 1)
        summary["coverage_lines"] = {"covered": data["totals"]["covered_lines"], "statements": data["totals"]["num_statements"]}
        files = {
            re.sub(r"^app[\\/]", "", name).replace("\\", "/"): round(info["summary"]["percent_covered"], 1)
            for name, info in data["files"].items()
        }
        summary["coverage_by_file"] = dict(sorted(files.items()))

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "tests.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"tests: {summary['passed']}/{total} passed, {failures} failed, {skipped} skipped; coverage {summary.get('coverage_pct')}%")


if __name__ == "__main__":
    main()
