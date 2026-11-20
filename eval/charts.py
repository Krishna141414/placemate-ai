"""Charts for the evaluation report (static PNGs for README and docs).

    python eval/charts.py [--provider gemini]

Two series, always in the same colours: baseline (teal) and final (brand
blue). The pair was checked with the dataviz palette validator (lightness,
chroma, colour-blind separation and contrast all pass on white).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "eval" / "results"

SERIES = {"baseline": ("Baseline", "#0E8F86"), "final": ("Final", "#1D4ED8")}
INK, MUTED, GRID, SURFACE = "#0B1F3A", "#475569", "#E2E8F0", "#FFFFFF"

plt.rcParams.update(
    {
        "font.family": ["Segoe UI", "DejaVu Sans", "sans-serif"],
        "font.size": 10,
        "axes.edgecolor": GRID,
        "axes.labelcolor": MUTED,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "text.color": INK,
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
    }
)


def grouped_bars(title: str, subtitle: str, labels: list[str], values: dict[str, list[float | None]], path: Path, *, percent: bool = True, unit: str = "") -> None:
    fig, ax = plt.subplots(figsize=(7.2, 3.6), dpi=160)
    n = len(labels)
    group = 0.62
    width = group / 2
    gap = 0.012  # surface gap between the two touching bars
    for i, key in enumerate(("baseline", "final")):
        name, colour = SERIES[key]
        xs = [x + (i - 0.5) * width for x in range(n)]
        ys = [v if v is not None else 0 for v in values[key]]
        ax.bar(xs, ys, width=width - gap, color=colour, label=name, zorder=3)
        for x, y, raw in zip(xs, ys, values[key]):
            text = "n/a" if raw is None else (f"{raw * 100:.0f}%" if percent else f"{raw:.1f}{unit}")
            ax.text(x, y + (0.02 if percent else max(ys + [1]) * 0.02), text, ha="center", va="bottom", fontsize=8.5, color=INK)

    ax.set_xticks(range(n), labels)
    if percent:
        ax.set_ylim(0, 1.12)
        ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0], ["0%", "25%", "50%", "75%", "100%"])
    else:
        top = max(v for series in values.values() for v in series if v is not None)
        ax.set_ylim(0, top * 1.18)
        ax.set_ylabel(unit.strip())
    ax.yaxis.grid(True, color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", length=0)

    fig.suptitle(title, x=0.02, y=0.98, ha="left", fontsize=12, fontweight="semibold", color=INK)
    ax.set_title(subtitle, loc="left", fontsize=9, color=MUTED, pad=10)
    ax.legend(loc="upper right", bbox_to_anchor=(1.0, 1.16), ncol=2, frameon=False, fontsize=9, handlelength=1.2)
    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", default="gemini")
    args = parser.parse_args()

    summary = json.loads((RESULTS / args.provider / "summary.json").read_text(encoding="utf-8"))
    modes = summary["modes"]
    out = RESULTS / args.provider
    provider = args.provider

    def pick(*keys):
        return {mode: [modes[mode].get(k) for k in keys] for mode in ("baseline", "final")}

    grouped_bars(
        "Retrieval",
        f"Answerable questions with a known source ({modes['final']['counts']['with_relevant_docs']} cases)",
        ["Hit@3", "MRR"],
        pick("hit_at_3", "mrr"),
        out / "retrieval.png",
    )
    grouped_bars(
        "Answer quality",
        f"Provider setting: {provider}. Higher is better.",
        ["Correct answer", "Groundedness", "Citation accuracy", "Refusal accuracy"],
        pick("answer_quality", "groundedness", "citation_accuracy", "refusal_accuracy"),
        out / "answers.png",
    )
    traps_refused = {m: [None if modes[m]["hallucination_rate"] is None else 1 - modes[m]["hallucination_rate"]] for m in ("baseline", "final")}
    safety = pick("injection_block_rate", "agent_task_success")
    grouped_bars(
        "Safety and agent",
        "Injections blocked, trap questions refused, agent tasks completed as expected",
        ["Injection blocked", "Traps refused", "Agent task success"],
        {m: [safety[m][0], traps_refused[m][0], safety[m][1]] for m in ("baseline", "final")},
        out / "safety.png",
    )
    to_s = lambda v: None if v is None else v / 1000  # noqa: E731
    grouped_bars(
        "Latency per question",
        "Seconds, end to end, on a laptop CPU. Lower is better.",
        ["Median (p50)", "p95"],
        {m: [to_s(modes[m]["latency_p50_ms"]), to_s(modes[m]["latency_p95_ms"])] for m in ("baseline", "final")},
        out / "latency.png",
        percent=False,
        unit=" s",
    )
    print(f"charts written to {out}")


if __name__ == "__main__":
    main()
