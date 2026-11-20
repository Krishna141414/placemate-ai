// Shape of eval/results/summary.json, published to /eval-summary.json by eval/publish.py.

export interface EvalMetrics {
  cases: number;
  hit_at_3: number | null;
  mrr: number | null;
  answer_quality: number | null;
  groundedness: number | null;
  citation_accuracy: number | null;
  refusal_accuracy: number | null;
  false_refusals: number;
  hallucination_rate: number | null;
  injection_block_rate: number | null;
  unsafe_outputs: number;
  ambiguous_handled: number | null;
  agent_task_success: number | null;
  latency_p50_ms: number | null;
  latency_p95_ms: number | null;
  providers: Record<string, number>;
  counts: Record<string, number>;
}

export interface EvalRun {
  generated_at: string;
  regraded_at?: string;
  provider_setting: string;
  models: { gemini: string | null; local: string; embedding: string; reranker: string };
  modes: { baseline: EvalMetrics; final: EvalMetrics };
}

export interface TestSummary {
  run_at: string;
  total: number;
  passed: number;
  failed: number;
  skipped: number;
  duration_s: number;
  per_file: Record<string, number>;
  coverage_pct?: number;
  coverage_lines?: { covered: number; statements: number };
  coverage_by_file?: Record<string, number>;
}

export interface EvalSummary {
  generated_at: string;
  primary: string;
  runs: Record<string, EvalRun>;
  tests: TestSummary | null;
}

export const REPO_URL = "https://github.com/Krishna141414/placemate-ai";

export async function loadEvalSummary(): Promise<EvalSummary> {
  const response = await fetch("/eval-summary.json", { cache: "no-store" });
  if (!response.ok) throw new Error("The evaluation summary is missing. Run scripts\\eval.ps1 to create it.");
  return (await response.json()) as EvalSummary;
}
