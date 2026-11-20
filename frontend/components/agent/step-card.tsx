"use client";

import { BookOpenText, Check, CircleDashed, FileText, Hand, ListTree, PenLine, UserCheck, X } from "lucide-react";
import type { ToolUIPart } from "ai";

import { CodeBlock } from "@/components/ai-elements/code-block";
import { Tool, ToolContent, ToolHeader } from "@/components/ai-elements/tool";
import { ToneBadge } from "@/components/shared/badges";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { seconds } from "@/lib/format";
import type { AgentStep, Criterion } from "@/lib/types";

const ICONS: Record<string, typeof Check> = {
  check_eligibility: UserCheck,
  match_resume: FileText,
  retrieve_process: ListTree,
  retrieve_experiences: BookOpenText,
  build_plan: PenLine,
  approval: Hand,
};

type Tone = "success" | "warning" | "error" | "neutral" | "info";

const STATUS: Record<AgentStep["status"], { state: ToolUIPart["state"]; label: string; tone: Tone }> = {
  pending: { state: "input-streaming", label: "Waiting", tone: "neutral" },
  running: { state: "input-available", label: "Running", tone: "info" },
  done: { state: "output-available", label: "Done", tone: "success" },
  recovered: { state: "output-available", label: "Recovered after retry", tone: "warning" },
  fallback: { state: "output-available", label: "Fallback used", tone: "warning" },
  skipped: { state: "output-denied", label: "Skipped", tone: "neutral" },
  failed: { state: "output-error", label: "Failed", tone: "error" },
  waiting: { state: "approval-requested", label: "Needs your approval", tone: "warning" },
  approved: { state: "approval-responded", label: "Approved", tone: "success" },
  rejected: { state: "output-denied", label: "Rejected", tone: "neutral" },
};

function StepSummary({ step }: { step: AgentStep }) {
  const out = step.output as Record<string, unknown>;
  if (!out || !Object.keys(out).length) return null;

  if (step.name === "check_eligibility") {
    const criteria = (out.criteria as Criterion[]) ?? [];
    return (
      <ul className="grid gap-1.5 text-sm sm:grid-cols-2">
        {criteria.map((criterion) => (
          <li key={criterion.name} className="flex items-start gap-2">
            {criterion.passed ? (
              <Check className="mt-0.5 size-4 shrink-0 text-success" aria-label="met" />
            ) : (
              <X className="mt-0.5 size-4 shrink-0 text-error" aria-label="not met" />
            )}
            <span>
              <span className="font-medium">{criterion.label}:</span> {criterion.reason}
            </span>
          </li>
        ))}
      </ul>
    );
  }
  if (step.name === "match_resume") {
    const missing = (out.missing_required as string[]) ?? [];
    const redaction = out.redaction as { total: number } | undefined;
    return (
      <div className="space-y-1 text-sm">
        <p>
          <span className="font-semibold num">{String(out.match_pct)}%</span> match.{" "}
          {missing.length ? `Missing required skills: ${missing.join(", ")}.` : "Every required skill is on the resume."}
        </p>
        {redaction && redaction.total > 0 && (
          <p className="text-muted-foreground">{redaction.total} contact details were removed before matching.</p>
        )}
      </div>
    );
  }
  if (step.name === "retrieve_process" || step.name === "retrieve_experiences") {
    const sources = (out.sources as { title: string; section: string; snippet: string }[]) ?? [];
    const rounds = out.rounds as string[] | undefined;
    return (
      <div className="space-y-2 text-sm">
        {rounds && <p>Rounds: {rounds.join(", ")}</p>}
        {sources.length ? (
          <ul className="space-y-1.5">
            {sources.slice(0, 4).map((source, i) => (
              <li key={i} className="min-w-0">
                <span className="font-medium">{source.title}</span>
                {source.section && <span className="text-muted-foreground">, {source.section}</span>}
                <span className="line-clamp-1 text-muted-foreground">{source.snippet}</span>
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    );
  }
  if (step.name === "build_plan") {
    const plan = out.plan as { weeks_count: number; weeks: { focus: string }[] } | undefined;
    if (!plan) return null;
    return (
      <ol className="list-decimal space-y-0.5 pl-5 text-sm">
        {plan.weeks.map((week, i) => (
          <li key={i}>{week.focus}</li>
        ))}
      </ol>
    );
  }
  return null;
}

export function StepCard({ step, index }: { step: AgentStep; index: number }) {
  const meta = STATUS[step.status];
  const Icon = ICONS[step.name] ?? CircleDashed;
  const open = step.status === "running" || step.status === "recovered" || step.status === "fallback" || step.status === "failed";
  const hasOutput = step.output && Object.keys(step.output).length > 0;

  return (
    <Tool defaultOpen={open} className="mb-0 bg-card" data-tour={`agent-step-${step.name}`} data-status={step.status}>
      <ToolHeader
        type={`tool-${step.tool}` as ToolUIPart["type"]}
        state={meta.state}
        title={`${index + 1}. ${step.label}`}
        icon={<Icon className="size-4 text-muted-foreground" aria-hidden="true" />}
        badge={
          <span className="flex items-center gap-2">
            <ToneBadge tone={meta.tone}>{meta.label}</ToneBadge>
            {!step.required && <span className="hidden text-xs text-muted-foreground sm:inline">optional</span>}
            {step.attempts > 1 && <span className="text-xs text-muted-foreground num">{step.attempts} attempts</span>}
            {step.duration_ms > 0 && <span className="hidden text-xs text-muted-foreground sm:inline num">{seconds(step.duration_ms)}</span>}
          </span>
        }
      />
      <ToolContent className="space-y-3 pt-0">
        <p className="text-sm text-muted-foreground">{step.description}</p>
        {step.detail && <p className="text-sm">{step.detail}</p>}
        {step.errors.length > 0 && (
          <ul className="space-y-1 rounded-md bg-warning-soft px-3 py-2 text-sm text-warning">
            {step.errors.map((error) => (
              <li key={error}>{error}</li>
            ))}
          </ul>
        )}
        <StepSummary step={step} />
        {hasOutput && (
          <Collapsible>
            <CollapsibleTrigger className="text-xs text-link underline-offset-4 hover:underline">Raw tool output</CollapsibleTrigger>
            <CollapsibleContent className="mt-2 max-h-72 overflow-auto rounded-md text-xs">
              <CodeBlock code={JSON.stringify(step.output, null, 2)} language="json" />
            </CollapsibleContent>
          </Collapsible>
        )}
      </ToolContent>
    </Tool>
  );
}
