"use client";

import { AnswerText } from "@/components/ask/answer-text";
import { ProviderBadge } from "@/components/shared/badges";
import { formatDate } from "@/lib/format";
import type { PrepPlanBody, Source } from "@/lib/types";

/** The week-by-week plan, as shown before approval and after saving. */
export function PlanPreview({ plan, compact = false }: { plan: PrepPlanBody; compact?: boolean }) {
  const sources: Source[] = plan.summary_sources.map((source, index) => ({
    n: index + 1,
    doc_key: source.doc_key,
    title: source.title,
    doc_type: "company",
    section: source.section,
    snippet: source.snippet,
    score: 0,
  }));

  return (
    <div className="space-y-5" data-tour="plan-preview">
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <p className="font-semibold">{plan.title}</p>
          {plan.summary_provider && <ProviderBadge provider={plan.summary_provider} />}
        </div>
        <dl className="mt-2 flex flex-wrap gap-x-6 gap-y-1 text-sm">
          <div className="flex gap-1">
            <dt className="text-muted-foreground">Role:</dt>
            <dd>{plan.role}</dd>
          </div>
          <div className="flex gap-1">
            <dt className="text-muted-foreground">Apply by:</dt>
            <dd className="num">{formatDate(plan.apply_by)}</dd>
          </div>
          <div className="flex gap-1">
            <dt className="text-muted-foreground">Rounds:</dt>
            <dd>{plan.rounds.join(", ")}</dd>
          </div>
        </dl>
      </div>

      {plan.summary && (
        <div className="rounded-lg border bg-muted/40 p-4 text-sm">
          <AnswerText text={plan.summary} sources={sources} />
        </div>
      )}

      {plan.focus_skills.length > 0 && (
        <p className="text-sm">
          <span className="text-muted-foreground">Skill gaps it starts with: </span>
          {plan.focus_skills.join(", ")}
        </p>
      )}

      <ol className="space-y-4">
        {plan.weeks.map((week) => (
          <li key={week.week} className="grid gap-x-4 sm:grid-cols-[5rem_minmax(0,1fr)]">
            <p className="text-sm font-medium text-muted-foreground num">Week {week.week}</p>
            <div className="min-w-0">
              <p className="font-medium">{week.focus}</p>
              <ul className="mt-1.5 list-disc space-y-0.5 pl-5 text-sm">
                {(compact ? week.tasks.slice(0, 3) : week.tasks).map((task) => (
                  <li key={task}>{task}</li>
                ))}
              </ul>
              {!compact && week.guides.length > 0 && <p className="mt-1.5 text-xs text-muted-foreground">Guide: {week.guides.join(", ")}</p>}
            </div>
          </li>
        ))}
      </ol>

      {!compact && plan.tips.length > 0 && (
        <div>
          <p className="mb-2 text-sm font-medium">From seniors who interviewed there</p>
          <ul className="space-y-2 text-sm">
            {plan.tips.slice(0, 4).map((tip) => (
              <li key={tip.text} className="border-l-2 pl-3">
                {tip.text}
                <span className="block text-xs text-muted-foreground">{tip.source}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
