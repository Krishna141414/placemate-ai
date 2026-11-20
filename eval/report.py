"""Write the evaluation tables into docs/evaluation.md from the result files.

    python eval/report.py

Replaces the text between `<!-- eval:<name>:start -->` and
`<!-- eval:<name>:end -->` markers, so every figure in the doc comes from
eval/results/ and never from hand-typed numbers.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "eval" / "results"
DOC = ROOT / "docs" / "evaluation.md"
EVIDENCE_DOC = ROOT / "docs" / "test-evidence.md"

ROWS = [
    ("Hit@3", "hit_at_3", "pct", "higher"),
    ("MRR", "mrr", "num", "higher"),
    ("Answer quality (correct facts)", "answer_quality", "pct", "higher"),
    ("Groundedness", "groundedness", "pct", "higher"),
    ("Citation accuracy", "citation_accuracy", "pct", "higher"),
    ("Refusal accuracy", "refusal_accuracy", "pct", "higher"),
    ("Hallucination rate on traps", "hallucination_rate", "pct", "lower"),
    ("Injection block rate", "injection_block_rate", "pct", "higher"),
    ("Unsafe outputs (attack succeeded)", "unsafe_outputs", "int", "lower"),
    ("Ambiguous inputs handled", "ambiguous_handled", "pct", "higher"),
    ("Agent task success", "agent_task_success", "pct", "higher"),
    ("Latency p50", "latency_p50_ms", "sec", "lower"),
    ("Latency p95", "latency_p95_ms", "sec", "lower"),
]


def fmt(value, kind: str) -> str:
    if value is None:
        return "n/a"
    if kind == "pct":
        return f"{value * 100:.1f}%"
    if kind == "num":
        return f"{value:.3f}"
    if kind == "sec":
        return f"{value / 1000:.2f} s"
    return str(value)


def metrics_table(summary: dict) -> str:
    base, final = summary["modes"]["baseline"], summary["modes"]["final"]
    lines = ["| Metric | Baseline | Final | Better when |", "|---|---:|---:|---|"]
    for label, key, kind, better in ROWS:
        lines.append(f"| {label} | {fmt(base.get(key), kind)} | {fmt(final.get(key), kind)} | {better} |")
    providers = lambda m: ", ".join(f"{k}: {v}" for k, v in sorted(summary["modes"][m]["providers"].items()))  # noqa: E731
    lines.append(f"| Answers by provider | {providers('baseline')} | {providers('final')} | |")
    return "\n".join(lines)


def counts_line(summary: dict) -> str:
    c = summary["modes"]["final"]["counts"]
    return (
        f"{summary['modes']['final']['cases']} cases: {c['answerable']} answerable "
        f"({c['with_relevant_docs']} with a labelled source), {c['traps']} traps, {c['ambiguous']} ambiguous, "
        f"{c['injection']} injection attempts, {c['agent']} agent tasks. Run at {summary['generated_at']} "
        f"with provider setting `{summary['provider_setting']}`"
        + (f" (`{summary['models']['gemini']}`)" if summary["models"].get("gemini") else "")
        + "."
    )


def misses_table(provider: str) -> str:
    rows = json.loads((RESULTS / provider / "cases_final.json").read_text(encoding="utf-8"))
    lines = ["| Case | Category | What happened |", "|---|---|---|"]
    found = False
    for r in rows:
        problem = None
        if r["category"] == "agent":
            if not r["success"]:
                problem = f"agent ended {r['status']}/{r['outcome'] or '-'}; checks {r['checks']}"
        elif r["expect"] == "answer" and not r["correct"]:
            problem = "refused" if r["refused"] else f"answered by {r['provider']} without a required fact: \"{_short(r['answer'])}\""
        elif r["expect"] == "refuse" and not r["refused"]:
            problem = f"trap answered by {r['provider']}: \"{_short(r['answer'])}\""
        elif r["expect"] == "block" and (not r["blocked"] or r["unsafe"]):
            problem = "injection not blocked" + (" and the output contained the attacker's target" if r["unsafe"] else "")
        elif r.get("fallbacks"):
            problem = f"answered after fallback ({'; '.join(r['fallbacks'])})"
        if problem:
            found = True
            lines.append(f"| `{r['id']}` | {r['category']} | {problem} |")
    return "\n".join(lines) if found else "No misses in the final run."


def _short(text: str, n: int = 110) -> str:
    text = " ".join(text.split()).replace("|", "/")
    return text if len(text) <= n else text[: n - 3].rsplit(" ", 1)[0] + "..."


def per_category(provider: str) -> str:
    lines = ["| Category | Cases | Baseline correct | Final correct |", "|---|---:|---:|---:|"]
    data = {m: json.loads((RESULTS / provider / f"cases_{m}.json").read_text(encoding="utf-8")) for m in ("baseline", "final")}

    def ok(r: dict) -> bool:
        if r["category"] == "agent":
            return r["success"]
        return {
            "answer": bool(r["correct"]),
            "refuse": r["refused"],
            "block": r["blocked"] and not r["unsafe"],
            "either": bool(r["handled"]),
        }[r["expect"]]

    order = ["policy", "company", "interview", "guide", "trap", "ambiguous", "injection", "agent"]
    for category in order:
        base = [r for r in data["baseline"] if r["category"] == category]
        final = [r for r in data["final"] if r["category"] == category]
        if base:
            lines.append(f"| {category} | {len(base)} | {sum(ok(r) for r in base)} | {sum(ok(r) for r in final)} |")
    return "\n".join(lines)


def tests_table() -> str:
    path = RESULTS / "tests.json"
    if not path.exists():
        return "No test run recorded yet."
    t = json.loads(path.read_text(encoding="utf-8"))
    lines = [
        f"**{t['passed']} passed, {t['failed']} failed, {t['skipped']} skipped** in {t['duration_s']} s "
        f"(run at {t['run_at']}). Line coverage of `backend/app`: **{t.get('coverage_pct', 'n/a')}%** "
        f"({t['coverage_lines']['covered']} of {t['coverage_lines']['statements']} statements).",
        "",
        "| Test file | Tests |",
        "|---|---:|",
    ]
    lines += [f"| `{name}.py` | {count} |" for name, count in t["per_file"].items()]
    return "\n".join(lines)


def coverage_table() -> str:
    path = RESULTS / "tests.json"
    if not path.exists():
        return ""
    files = json.loads(path.read_text(encoding="utf-8")).get("coverage_by_file", {})
    lowest = sorted(files.items(), key=lambda kv: kv[1])[:8]
    lines = ["| Module (lowest coverage first) | Coverage |", "|---|---:|"]
    lines += [f"| `app/{name}` | {pct}% |" for name, pct in lowest]
    return "\n".join(lines)


def replace_block(text: str, name: str, body: str) -> str:
    pattern = re.compile(rf"(<!-- eval:{name}:start -->\n).*?(<!-- eval:{name}:end -->)", re.DOTALL)
    if not pattern.search(text):
        raise SystemExit(f"marker eval:{name} not found")
    return pattern.sub(lambda m: m.group(1) + body.rstrip("\n") + "\n" + m.group(2), text)


def main() -> None:
    text = DOC.read_text(encoding="utf-8")
    for provider in ("gemini", "extractive"):
        path = RESULTS / provider / "summary.json"
        if not path.exists():
            continue
        summary = json.loads(path.read_text(encoding="utf-8"))
        text = replace_block(text, f"{provider}-counts", counts_line(summary))
        text = replace_block(text, f"{provider}-metrics", metrics_table(summary))
        text = replace_block(text, f"{provider}-categories", per_category(provider))
        text = replace_block(text, f"{provider}-misses", misses_table(provider))
    DOC.write_text(text, encoding="utf-8", newline="\n")
    print(f"updated {DOC}")

    if EVIDENCE_DOC.exists():
        evidence = EVIDENCE_DOC.read_text(encoding="utf-8")
        evidence = replace_block(evidence, "tests", tests_table())
        evidence = replace_block(evidence, "coverage", coverage_table())
        for provider in ("gemini", "extractive"):
            path = RESULTS / provider / "summary.json"
            if path.exists() and f"<!-- eval:{provider}-metrics:start -->" in evidence:
                summary = json.loads(path.read_text(encoding="utf-8"))
                evidence = replace_block(evidence, f"{provider}-metrics", metrics_table(summary))
        EVIDENCE_DOC.write_text(evidence, encoding="utf-8", newline="\n")
        print(f"updated {EVIDENCE_DOC}")


if __name__ == "__main__":
    main()
