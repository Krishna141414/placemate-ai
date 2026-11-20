"""Re-grade saved answers after a metric change, without calling any model.

    python eval/regrade.py --provider gemini

The saved case files hold each answer and the document keys that were
retrieved. Retrieval is deterministic, so running it again gives back the
same passages; this script checks that (the document keys must match the
saved ones exactly) before recomputing groundedness and citation accuracy
with the current `metrics.py`. Answers, refusals and blocks are unchanged.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVAL_DIR = ROOT / "eval"

parser = argparse.ArgumentParser()
parser.add_argument("--provider", required=True)
ARGS = parser.parse_args()

os.environ.update({"STORAGE_DIR": str(EVAL_DIR / ".work" / ARGS.provider), "DATABASE_URL": "", "APP_ENV": "eval"})
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(EVAL_DIR))

from app.config import get_settings  # noqa: E402
from app.db import SessionLocal, init_db  # noqa: E402
from app.logging_conf import configure_logging  # noqa: E402
from app.rag.index import IndexStore  # noqa: E402
from app.rag.pipeline import _source_cards  # noqa: E402
from app.rag.retriever import retrieve  # noqa: E402
from app.security.injection import scan_user_input  # noqa: E402
from metrics import SupportChecker, grounding, summarise  # noqa: E402


def sources_for(question: str, mode: str) -> list[dict]:
    result = retrieve(question, mode=mode)
    items = result.results
    if mode == "final":  # the pipeline drops passages that contain instructions
        items = [item for item in items if not scan_user_input(item.chunk.text).blocked]
    return _source_cards(items)


def main() -> None:
    configure_logging(None, level="WARNING")
    init_db(get_settings().db_url)
    with SessionLocal() as db:
        IndexStore.ensure(db)

    checker = SupportChecker()
    out_dir = EVAL_DIR / "results" / ARGS.provider
    summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
    for mode in summary["modes"]:
        path = out_dir / f"cases_{mode}.json"
        rows = json.loads(path.read_text(encoding="utf-8"))
        changed = 0
        for row in rows:
            if row["category"] == "agent" or row["refused"] or row["blocked"]:
                continue
            sources = row.get("sources") or sources_for(row["question"], mode)
            keys = [s["doc_key"] for s in sources]
            if keys != row["retrieved"]:
                raise SystemExit(f"{row['id']} ({mode}): retrieval differs from the saved run; re-run the evaluation instead.")
            new = grounding(row["answer"], sources, checker)
            if new != row["grounding"]:
                changed += 1
            row["grounding"] = new
            row["sources"] = [{k: s[k] for k in ("n", "doc_key", "title", "section", "text", "score")} for s in sources]
            if row["expect"] == "either":
                g = new
                row["handled"] = bool(g["sentences"] and g["supported"] / g["sentences"] >= 0.5 and g["citations"] > 0)
        path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
        summary["modes"][mode] = summarise(rows)
        print(f"{ARGS.provider}/{mode}: re-graded, {changed} case(s) changed")

    summary["regraded_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
