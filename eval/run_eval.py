"""Run the evaluation set: baseline versus final.

    python eval/run_eval.py                       # provider from LLM_PROVIDER (default gemini)
    python eval/run_eval.py --provider extractive # offline run, no API key needed

baseline: vector-only retrieval, no reranking, no input/output guards, no
          refusal threshold; the agent has no retries, no fallbacks and no
          optional-step skipping.
final:    the shipped pipeline: hybrid retrieval + RRF + rerank, guards,
          grounding check; the agent with retry / fallback / skip.

Each run uses its own scratch database and index under eval/.work/, so the
app's own data is never touched. Results go to eval/results/<provider>/.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVAL_DIR = ROOT / "eval"
TODAY = date(2026, 11, 19)  # fixed so plan lengths are reproducible


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--provider", choices=["gemini", "local", "extractive"], default=os.environ.get("LLM_PROVIDER", "gemini"))
    parser.add_argument("--modes", default="baseline,final")
    parser.add_argument("--delay", type=float, default=None, help="seconds between model calls (default 2 for gemini, 0 otherwise)")
    parser.add_argument("--only", default="", help="comma-separated case ids, for debugging")
    return parser.parse_args()


ARGS = parse_args()
WORK = EVAL_DIR / ".work" / ARGS.provider
os.environ.update(
    {
        "STORAGE_DIR": str(WORK),
        "DATABASE_URL": "",
        "LLM_PROVIDER": ARGS.provider,
        "APP_ENV": "eval",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
    }
)
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(EVAL_DIR))

from app.agent import executor  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.db import SessionLocal, init_db  # noqa: E402
from app.logging_conf import configure_logging  # noqa: E402
from app.models import AgentRun, Application, PrepPlan, User  # noqa: E402
from app.rag.index import IndexStore  # noqa: E402
from app.rag.pipeline import answer_question  # noqa: E402
from app.seed import DEMO_STUDENT_EMAIL, seed_demo_data  # noqa: E402
from metrics import SupportChecker, contains_all, contains_any, first_relevant_rank, grounding, summarise  # noqa: E402

RATE_LIMIT_MARKERS = ("API error 429", "API error 503")


def log(message: str) -> None:
    print(message, flush=True)


def ask_case(case: dict, mode: str, checker: SupportChecker, delay: float) -> dict:
    attempts = 0
    while True:
        attempts += 1
        result = answer_question(case["question"], mode=mode)
        limited = any(marker in f for f in result.fallbacks for marker in RATE_LIMIT_MARKERS)
        if not (limited and attempts < 3):
            break
        log(f"    rate limited, waiting 30 s (attempt {attempts})")
        time.sleep(30)

    called_model = result.provider not in ("none", "extractive")
    if delay and called_model:
        time.sleep(delay)

    doc_keys = result.retrieved_doc_keys
    relevant = case.get("relevant_docs", [])
    rank = first_relevant_rank(doc_keys, relevant) if relevant else None
    answered = not result.refused and not result.blocked
    ground = grounding(result.answer, result.sources, checker) if answered else {"sentences": 0, "supported": 0, "citations": 0, "correct_citations": 0}

    correct = answered and contains_all(result.answer, case.get("must_include", [])) if case["expect"] == "answer" else None
    unsafe = contains_any(result.answer, case.get("forbidden", [])) if case["expect"] == "block" else False
    handled = None
    if case["expect"] == "either":
        grounded = ground["sentences"] and ground["supported"] / ground["sentences"] >= 0.5 and ground["citations"] > 0
        handled = bool(result.refused or grounded)

    return {
        "id": case["id"],
        "category": case["category"],
        "expect": case["expect"],
        "question": case["question"],
        "answer": result.answer,
        "refused": result.refused,
        "blocked": result.blocked,
        "provider": result.provider,
        "fallbacks": result.fallbacks,
        "latency_ms": result.latency_ms,
        "top_score": result.top_score,
        "retrieved": doc_keys,
        "relevant_docs": relevant,
        "rank": rank,
        "citations": result.citations,
        "grounding": ground,
        "correct": correct,
        "unsafe": unsafe,
        "handled": handled,
        "attempts": attempts,
        "sources": [{k: s[k] for k in ("n", "doc_key", "title", "section", "text", "score")} for s in result.sources],
    }


class NaiveAgent:
    """Baseline agent: no retries, no fallbacks, every step required."""

    def __enter__(self):
        settings = get_settings()
        self._retries = settings.agent_step_retries
        self._fallbacks = executor.FALLBACKS
        self._make_plan = executor.make_plan
        settings.agent_step_retries = 0
        executor.FALLBACKS = {}

        def strict_plan(company, *, has_resume):
            steps = self._make_plan(company, has_resume=has_resume)
            for step in steps:
                step.required = True
            return steps

        executor.make_plan = strict_plan
        return self

    def __exit__(self, *exc):
        get_settings().agent_step_retries = self._retries
        executor.FALLBACKS = self._fallbacks
        executor.make_plan = self._make_plan


def agent_case(case: dict, mode: str, delay: float) -> dict:
    started = time.perf_counter()
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == DEMO_STUDENT_EMAIL).one()
        for model in (PrepPlan, AgentRun, Application):
            db.query(model).filter(model.user_id == user.id).delete()
        db.commit()

        def run():
            events = list(executor.run_agent(db, user, case["company_id"], faults=dict(case["faults"]), today=TODAY))
            return events[-1]["run"]

        if mode == "baseline":
            with NaiveAgent():
                out = run()
        else:
            out = run()

        steps = {s["name"]: s["status"] for s in out["state"]["steps"]}
        checks = {"status": out["status"] == case["expect_status"]}
        if "expect_outcome" in case:
            checks["outcome"] = out["outcome"] == case["expect_outcome"]
        for name, status in case.get("expect_steps", {}).items():
            checks[f"step:{name}"] = steps.get(name) == status
        if case.get("expect_alternatives"):
            checks["alternatives"] = bool(out["state"].get("alternatives"))
        if case.get("approve") and out["status"] == "awaiting_approval":
            saved = executor.approve_run(db, user, out["id"])
            checks["approve_saves"] = bool(
                db.get(PrepPlan, saved["prep_plan_id"]) and db.get(Application, saved["application_id"])
            )
        elif case.get("approve"):
            checks["approve_saves"] = False

    plan = (out["state"].get("pending") or {}).get("plan") or {}
    if delay and plan.get("summary_provider") not in (None, "", "extractive", "template"):
        time.sleep(delay)
    return {
        "id": case["id"],
        "category": "agent",
        "expect": "agent",
        "note": case.get("note", ""),
        "company_id": case["company_id"],
        "faults": case["faults"],
        "status": out["status"],
        "outcome": out["outcome"],
        "steps": steps,
        "tool_calls": out["state"]["tool_calls"],
        "summary_provider": plan.get("summary_provider"),
        "checks": checks,
        "success": all(checks.values()),
        "duration_ms": round((time.perf_counter() - started) * 1000, 1),
    }


def main() -> None:
    settings = get_settings()
    configure_logging(None, level="WARNING")
    init_db(settings.db_url)
    with SessionLocal() as db:
        seed_demo_data(db)
        IndexStore.ensure(db)

    delay = ARGS.delay if ARGS.delay is not None else (2.0 if ARGS.provider == "gemini" else 0.0)
    if ARGS.provider == "gemini" and not settings.gemini_api_key:
        log("GEMINI_API_KEY is not set: answers will come from the fallback providers. Use --provider extractive for an offline run.")

    cases = json.loads((EVAL_DIR / "cases.json").read_text(encoding="utf-8"))["cases"]
    if ARGS.only:
        wanted = set(ARGS.only.split(","))
        cases = [c for c in cases if c["id"] in wanted]

    checker = SupportChecker()
    out_dir = EVAL_DIR / "results" / ARGS.provider
    out_dir.mkdir(parents=True, exist_ok=True)
    summary: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "provider_setting": ARGS.provider,
        "models": {
            "gemini": settings.gemini_model if ARGS.provider == "gemini" else None,
            "local": settings.local_model,
            "embedding": settings.embedding_model,
            "reranker": settings.reranker_model,
        },
        "config": {
            "top_k": settings.top_k,
            "candidates_per_retriever": settings.retrieve_candidates,
            "rrf_k": settings.rrf_k,
            "rerank_refusal_threshold": settings.rerank_refusal_threshold,
        },
        "modes": {},
    }

    for mode in [m.strip() for m in ARGS.modes.split(",") if m.strip()]:
        log(f"\n=== {mode} ({ARGS.provider}) ===")
        results = []
        for case in cases:
            if case["category"] == "agent":
                result = agent_case(case, mode, delay)
                flag = "ok " if result["success"] else "FAIL"
                log(f"  {flag} {case['id']:9} {result['status']}/{result['outcome'] or '-'} {result['checks']}")
            else:
                result = ask_case(case, mode, checker, delay)
                state = "blocked" if result["blocked"] else "refused" if result["refused"] else "answered"
                log(f"  {case['id']:9} {state:8} {result['provider']:10} rank={result['rank']} correct={result['correct']} {result['latency_ms']:.0f}ms")
            results.append(result)

        (out_dir / f"cases_{mode}.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        metrics = summarise(results)
        summary["modes"][mode] = metrics
        log(json.dumps({k: v for k, v in metrics.items() if k not in ("providers", "counts")}, indent=1))

    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    log(f"\nSaved to {out_dir}")


if __name__ == "__main__":
    main()
