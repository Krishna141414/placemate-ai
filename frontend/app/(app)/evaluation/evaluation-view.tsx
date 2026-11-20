"use client";

import { ExternalLink } from "lucide-react";
import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, LabelList, XAxis, YAxis } from "recharts";

import { CountUp } from "@/components/shared/count-up";
import { ErrorState, LoadingRows, PageHeader, Section } from "@/components/shared/page";
import { Button } from "@/components/ui/button";
import { ChartContainer, ChartLegend, ChartLegendContent, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { formatDateTime, pct, seconds } from "@/lib/format";
import { loadEvalSummary, REPO_URL, type EvalMetrics, type EvalSummary } from "@/lib/eval-summary";

const chartConfig = {
  baseline: { label: "Baseline", color: "var(--series-baseline)" },
  final: { label: "Final", color: "var(--series-final)" },
} satisfies ChartConfig;

type Row = { key: keyof EvalMetrics; label: string; kind: "pct" | "num" | "int" | "ms"; better: "higher" | "lower"; chart?: boolean };

const ROWS: Row[] = [
  { key: "hit_at_3", label: "Hit@3", kind: "pct", better: "higher", chart: true },
  { key: "mrr", label: "MRR", kind: "num", better: "higher", chart: true },
  { key: "answer_quality", label: "Answer quality", kind: "pct", better: "higher", chart: true },
  { key: "groundedness", label: "Groundedness", kind: "pct", better: "higher", chart: true },
  { key: "citation_accuracy", label: "Citation accuracy", kind: "pct", better: "higher", chart: true },
  { key: "refusal_accuracy", label: "Refusal accuracy", kind: "pct", better: "higher", chart: true },
  { key: "injection_block_rate", label: "Injection block rate", kind: "pct", better: "higher", chart: true },
  { key: "agent_task_success", label: "Agent task success", kind: "pct", better: "higher", chart: true },
  { key: "hallucination_rate", label: "Hallucination rate on traps", kind: "pct", better: "lower" },
  { key: "unsafe_outputs", label: "Unsafe outputs", kind: "int", better: "lower" },
  { key: "ambiguous_handled", label: "Ambiguous inputs handled", kind: "pct", better: "higher" },
  { key: "latency_p50_ms", label: "Latency, median", kind: "ms", better: "lower" },
  { key: "latency_p95_ms", label: "Latency, p95", kind: "ms", better: "lower" },
];

const CHART_LABELS: Partial<Record<keyof EvalMetrics, string>> = {
  hit_at_3: "Hit@3",
  mrr: "MRR",
  answer_quality: "Correct",
  groundedness: "Grounded",
  citation_accuracy: "Citations",
  refusal_accuracy: "Refusals",
  injection_block_rate: "Injection",
  agent_task_success: "Agent",
};

function fmt(value: unknown, kind: Row["kind"]): string {
  if (value === null || value === undefined) return "n/a";
  const v = Number(value);
  if (kind === "pct") return pct(v, 1);
  if (kind === "num") return v.toFixed(3);
  if (kind === "ms") return seconds(v);
  return String(v);
}

const HEADLINES: { key: keyof EvalMetrics; label: string }[] = [
  { key: "answer_quality", label: "Answers with the right facts" },
  { key: "refusal_accuracy", label: "Refused when it should, answered when it could" },
  { key: "injection_block_rate", label: "Injection attempts blocked" },
  { key: "agent_task_success", label: "Agent tasks completed as expected" },
];

export function EvaluationView() {
  const [summary, setSummary] = useState<EvalSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [provider, setProvider] = useState<string>("gemini");

  useEffect(() => {
    let alive = true;
    loadEvalSummary()
      .then((data) => {
        if (!alive) return;
        setSummary(data);
        setProvider(data.primary);
      })
      .catch((err: Error) => alive && setError(err.message));
    return () => {
      alive = false;
    };
  }, []);

  const run = summary?.runs[provider];
  const base = run?.modes.baseline;
  const final = run?.modes.final;
  const chartRows = ROWS.filter((row) => row.chart).map((row) => ({
    metric: CHART_LABELS[row.key] ?? row.label,
    baseline: Number(base?.[row.key] ?? 0),
    final: Number(final?.[row.key] ?? 0),
  }));

  return (
    <div>
      <PageHeader
        title="Evaluation"
        description="A fixed set of hand-written cases, run against a naive baseline and the final system. Every number here comes from the saved run files; nothing is typed in by hand."
        actions={
          <>
            <Button asChild variant="outline" size="sm">
              <a href={`${REPO_URL}/blob/main/docs/evaluation.md`} target="_blank" rel="noreferrer">
                Method and findings
                <ExternalLink aria-hidden="true" />
              </a>
            </Button>
            <Button asChild variant="outline" size="sm">
              <a href={`${REPO_URL}/blob/main/docs/test-evidence.md`} target="_blank" rel="noreferrer">
                Test evidence
                <ExternalLink aria-hidden="true" />
              </a>
            </Button>
          </>
        }
      />

      {error ? (
        <ErrorState message={error} />
      ) : !summary || !run || !base || !final ? (
        <LoadingRows rows={8} />
      ) : (
        <div className="space-y-12">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <ToggleGroup type="single" value={provider} onValueChange={(value) => value && setProvider(value)} variant="outline" data-tour="eval-provider">
              {Object.keys(summary.runs).map((key) => (
                <ToggleGroupItem key={key} value={key} className="px-3">
                  {key === "gemini" ? "With Gemini" : key === "extractive" ? "No API key" : key}
                </ToggleGroupItem>
              ))}
            </ToggleGroup>
            <p className="text-sm text-muted-foreground">
              {run.models.gemini ? `Model ${run.models.gemini}. ` : "Answers are sentences quoted from the documents. "}
              Run {formatDateTime(run.generated_at)}.
            </p>
          </div>

          <dl className="grid grid-cols-2 gap-x-6 gap-y-6 border-y py-6 lg:grid-cols-4" data-tour="eval-headlines">
            {HEADLINES.map((item) => {
              const value = final[item.key] as number | null;
              const before = base[item.key] as number | null;
              return (
                <div key={item.key} className="min-w-0">
                  <dt className="text-sm text-muted-foreground">{item.label}</dt>
                  <dd className="mt-1 text-3xl font-semibold tracking-tight">
                    {value === null ? "n/a" : <CountUp value={value * 100} decimals={0} suffix="%" />}
                  </dd>
                  <dd className="mt-0.5 text-xs text-muted-foreground num">baseline {before === null ? "n/a" : pct(before)}</dd>
                </div>
              );
            })}
          </dl>

          <Section title="Baseline and final, metric by metric" description="Higher is better for every metric in this chart." data-tour="eval-chart">
            <ChartContainer config={chartConfig} className="h-80 w-full" aria-label="Baseline and final scores for each metric">
              <BarChart data={chartRows} margin={{ left: 4, right: 8, top: 20 }} barGap={2}>
                <CartesianGrid vertical={false} stroke="var(--rule)" />
                <XAxis dataKey="metric" tickLine={false} axisLine={false} tickMargin={8} interval={0} fontSize={12} />
                <YAxis domain={[0, 1]} tickFormatter={(v: number) => `${Math.round(v * 100)}%`} tickLine={false} axisLine={false} width={48} />
                <ChartTooltip cursor={{ fill: "var(--muted)" }} content={<ChartTooltipContent formatter={(value, name) => `${chartConfig[name as "baseline" | "final"].label}: ${pct(Number(value), 1)}`} />} />
                <ChartLegend content={<ChartLegendContent />} />
                <Bar dataKey="baseline" fill="var(--color-baseline)" radius={[4, 4, 0, 0]} maxBarSize={22} />
                <Bar dataKey="final" fill="var(--color-final)" radius={[4, 4, 0, 0]} maxBarSize={22}>
                  <LabelList dataKey="final" position="top" formatter={(v: unknown) => `${Math.round(Number(v) * 100)}`} className="fill-foreground text-[10px]" />
                </Bar>
              </BarChart>
            </ChartContainer>
          </Section>

          <Section title="All metrics" description={`${final.cases} cases: ${final.counts.answerable} answerable, ${final.counts.traps} traps, ${final.counts.ambiguous} ambiguous, ${final.counts.injection} injection, ${final.counts.agent} agent.`}>
            <div className="overflow-x-auto">
              <Table data-tour="eval-table">
                <TableHeader>
                  <TableRow>
                    <TableHead>Metric</TableHead>
                    <TableHead className="text-right">Baseline</TableHead>
                    <TableHead className="text-right">Final</TableHead>
                    <TableHead className="hidden sm:table-cell">Better when</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {ROWS.map((row) => (
                    <TableRow key={row.key}>
                      <TableCell>{row.label}</TableCell>
                      <TableCell className="text-right num">{fmt(base[row.key], row.kind)}</TableCell>
                      <TableCell className="text-right font-medium num">{fmt(final[row.key], row.kind)}</TableCell>
                      <TableCell className="hidden text-muted-foreground sm:table-cell">{row.better}</TableCell>
                    </TableRow>
                  ))}
                  <TableRow>
                    <TableCell>Answers by provider</TableCell>
                    <TableCell className="text-right text-muted-foreground">
                      {Object.entries(base.providers)
                        .map(([k, v]) => `${k} ${v}`)
                        .join(", ")}
                    </TableCell>
                    <TableCell className="text-right text-muted-foreground">
                      {Object.entries(final.providers)
                        .map(([k, v]) => (k === "none" ? `no model needed ${v}` : `${k} ${v}`))
                        .join(", ")}
                    </TableCell>
                    <TableCell className="hidden sm:table-cell" />
                  </TableRow>
                </TableBody>
              </Table>
            </div>
            <p className="mt-3 max-w-3xl text-sm text-muted-foreground">
              The baseline uses vector search only, no reranking, no guards and no refusal threshold, and its agent has no retries or fallbacks.
              {(final.groundedness ?? 0) < (base.groundedness ?? 0)
                ? " Groundedness is slightly lower in the final run because it answers more questions, with longer answers that cite several passages."
                : ""}
              {(final.latency_p50_ms ?? 0) > (base.latency_p50_ms ?? 0)
                ? " The final pipeline is slower at the median: reranking and the extra checks add time, while blocked or refused questions return in milliseconds."
                : ""}
            </p>
          </Section>

          {summary.tests && (
            <Section title="Automated tests" description={`Backend pytest suite, run ${formatDateTime(summary.tests.run_at)}`} data-tour="eval-tests">
              <dl className="mb-6 grid grid-cols-2 gap-6 sm:grid-cols-4">
                <div>
                  <dt className="text-sm text-muted-foreground">Passed</dt>
                  <dd className="mt-1 text-2xl font-semibold num">
                    {summary.tests.passed} of {summary.tests.total}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm text-muted-foreground">Failed</dt>
                  <dd className="mt-1 text-2xl font-semibold num">{summary.tests.failed}</dd>
                </div>
                <div>
                  <dt className="text-sm text-muted-foreground">Line coverage</dt>
                  <dd className="mt-1 text-2xl font-semibold num">{summary.tests.coverage_pct ?? "n/a"}%</dd>
                </div>
                <div>
                  <dt className="text-sm text-muted-foreground">Run time</dt>
                  <dd className="mt-1 text-2xl font-semibold num">{Math.round(summary.tests.duration_s)} s</dd>
                </div>
              </dl>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Test file</TableHead>
                      <TableHead className="text-right">Tests</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {Object.entries(summary.tests.per_file).map(([file, count]) => (
                      <TableRow key={file}>
                        <TableCell className="text-sm">{file}.py</TableCell>
                        <TableCell className="text-right num">{count}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </Section>
          )}

          <Section title="Limits of this evaluation">
            <ul className="max-w-3xl list-disc space-y-1.5 pl-5 text-sm text-muted-foreground">
              <li>The cases were written by the same person who wrote the documents, and were used during development. There is no held-out set.</li>
              <li>34 documents make retrieval easy, so the baseline&apos;s retrieval scores are already high.</li>
              <li>Groundedness is measured by word overlap and embedding similarity, not by a person or another model.</li>
              <li>Latency was measured on one laptop CPU and depends on Gemini&apos;s response time on the day.</li>
            </ul>
          </Section>
        </div>
      )}
    </div>
  );
}
