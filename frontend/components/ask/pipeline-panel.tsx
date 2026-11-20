"use client";

import { CircleSlash, Filter, Layers, PenLine, Search, ShieldAlert, ShieldCheck, Workflow } from "lucide-react";

import { ChainOfThought, ChainOfThoughtContent, ChainOfThoughtHeader, ChainOfThoughtStep } from "@/components/ai-elements/chain-of-thought";
import { ProviderBadge, ToneBadge } from "@/components/shared/badges";
import { seconds } from "@/lib/format";
import type { PipelineStep } from "@/lib/types";

const ICONS: Record<string, typeof Search> = {
  guard: ShieldCheck,
  retrieve: Search,
  rerank: Layers,
  grounding: Filter,
  generate: PenLine,
  output_guard: ShieldCheck,
};

const TONE: Record<string, "success" | "warning" | "error" | "neutral" | "info"> = {
  done: "success",
  fallback: "warning",
  skipped: "neutral",
  blocked: "error",
  refused: "warning",
  running: "info",
};

const LABEL: Record<string, string> = {
  done: "Done",
  fallback: "Fallback",
  skipped: "Skipped",
  blocked: "Blocked",
  refused: "Refused",
  running: "Running",
};

/** "How this was answered": the pipeline steps, revealed as they happen. */
export function PipelinePanel({
  steps,
  provider,
  latencyMs,
  running,
  defaultOpen = false,
}: {
  steps: PipelineStep[];
  provider?: string;
  latencyMs?: number;
  running: boolean;
  defaultOpen?: boolean;
}) {
  return (
    <ChainOfThought defaultOpen={defaultOpen} className="mt-4 rounded-lg border bg-muted/40 px-4 py-3" data-tour="pipeline-panel">
      <ChainOfThoughtHeader className="text-sm">
        <span className="flex items-center gap-2">
          How this was answered
          {provider && <ProviderBadge provider={provider} />}
          {latencyMs !== undefined && !running && <span className="text-xs text-muted-foreground num">{seconds(latencyMs)}</span>}
        </span>
      </ChainOfThoughtHeader>
      <ChainOfThoughtContent>
        {steps.map((step, index) => {
          const Icon = step.status === "blocked" ? ShieldAlert : step.status === "skipped" ? CircleSlash : ICONS[step.name] ?? Workflow;
          const last = index === steps.length - 1;
          return (
            <ChainOfThoughtStep
              key={`${step.name}-${index}`}
              icon={Icon}
              status={running && last ? "active" : "complete"}
              label={
                <span className="flex flex-wrap items-center gap-2">
                  <span className="font-medium text-foreground">{step.label}</span>
                  <ToneBadge tone={TONE[step.status] ?? "neutral"}>{LABEL[step.status] ?? step.status}</ToneBadge>
                  {step.duration_ms > 0 && <span className="text-xs text-muted-foreground num">{seconds(step.duration_ms)}</span>}
                </span>
              }
              description={step.detail}
            />
          );
        })}
      </ChainOfThoughtContent>
    </ChainOfThought>
  );
}
