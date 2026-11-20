"use client";

import { CheckIcon, Loader2, Play, RotateCcw, XIcon } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import {
  Confirmation,
  ConfirmationAccepted,
  ConfirmationAction,
  ConfirmationActions,
  ConfirmationRejected,
  ConfirmationRequest,
} from "@/components/ai-elements/confirmation";
import { PlanPreview } from "@/components/agent/plan-preview";
import { StepCard } from "@/components/agent/step-card";
import { ToneBadge } from "@/components/shared/badges";
import { CompanySelect } from "@/components/shared/company-select";
import { EmptyState, ErrorState, PageHeader, Panel } from "@/components/shared/page";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api, errorMessage, streamSSE } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { sleep, useSpeed } from "@/lib/speed";
import type { AgentRun, AgentState, AgentStep } from "@/lib/types";

const FAULTS = [
  { value: "none", label: "No failure" },
  { value: "retrieve_process", label: "Process search fails once" },
  { value: "match_resume", label: "Resume match fails once" },
  { value: "retrieve_experiences", label: "Experience search fails once" },
  { value: "build_plan", label: "Plan writer fails once" },
] as const;

const RUN_STATUS: Record<AgentRun["status"], { label: string; tone: "success" | "warning" | "error" | "neutral" | "info" }> = {
  running: { label: "Running", tone: "info" },
  awaiting_approval: { label: "Waiting for your approval", tone: "warning" },
  approved: { label: "Approved and saved", tone: "success" },
  rejected: { label: "Rejected, nothing saved", tone: "neutral" },
  completed: { label: "Finished", tone: "neutral" },
  failed: { label: "Failed, nothing saved", tone: "error" },
};

interface View {
  runId: number | null;
  status: AgentRun["status"] | "idle";
  goal: string;
  steps: AgentStep[];
  state: AgentState | null;
}

const IDLE: View = { runId: null, status: "idle", goal: "", steps: [], state: null };

export function AgentView() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const company = params.get("company") ?? undefined;
  const runParam = params.get("run");
  const { t } = useSpeed();

  const [fault, setFault] = useState<string>("none");
  const [view, setView] = useState<View>(IDLE);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deciding, setDeciding] = useState<"approve" | "reject" | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const loadedRun = useRef<number | null>(null);

  const setQuery = useCallback(
    (query: Record<string, string | undefined>) => {
      const next = new URLSearchParams();
      for (const [key, value] of Object.entries(query)) if (value) next.set(key, value);
      router.replace(`${pathname}?${next.toString()}`, { scroll: false });
    },
    [pathname, router],
  );

  const applyRun = useCallback((run: AgentRun) => {
    setView({ runId: run.id, status: run.status, goal: run.goal, steps: run.state.steps, state: run.state });
  }, []);

  // Reopen a run named in the URL (after a refresh, or from the guided tour).
  useEffect(() => {
    if (!runParam || running) return;
    const id = Number(runParam);
    if (loadedRun.current === id) return;
    loadedRun.current = id;
    api<AgentRun>(`/api/agent/runs/${id}`)
      .then(applyRun)
      .catch((err) => toast.error(errorMessage(err)));
  }, [runParam, running, applyRun]);

  useEffect(() => () => abortRef.current?.abort(), []);

  async function start() {
    if (!company || running) return;
    setRunning(true);
    setError(null);
    setDialogOpen(false);
    setView({ ...IDLE, status: "running" });

    const queue: { event: string; data: Record<string, unknown> }[] = [];
    let finished = false;
    let streamError: unknown = null;
    let wake: (() => void) | null = null;
    const push = (event: string, data: unknown) => {
      queue.push({ event, data: data as Record<string, unknown> });
      wake?.();
      wake = null;
    };
    const next = async () => {
      while (!queue.length) {
        if (finished) return null;
        await new Promise<void>((resolve) => (wake = resolve));
      }
      return queue.shift()!;
    };

    const controller = new AbortController();
    abortRef.current = controller;
    streamSSE("/api/agent/runs/stream", { company_id: company, demo_fault: fault === "none" ? null : fault }, push, controller.signal)
      .catch((err) => (streamError = err))
      .finally(() => {
        finished = true;
        wake?.();
      });

    let started = 0;
    try {
      for (let item = await next(); item; item = await next()) {
        const { event, data } = item;
        if (event === "run") {
          const run = data.run as { id: number; goal: string };
          loadedRun.current = run.id;
          setView((v) => ({ ...v, runId: run.id, goal: run.goal }));
          setQuery({ company, run: String(run.id) });
        } else if (event === "plan") {
          setView((v) => ({ ...v, steps: data.steps as AgentStep[] }));
        } else if (event === "step") {
          const step = data.step as AgentStep;
          // Pause before each new step starts, so the timeline can be followed.
          if (step.status === "running" && step.attempts === 1) {
            if (started > 0) await sleep(t.step);
            started += 1;
          }
          setView((v) => ({ ...v, steps: v.steps.map((s) => (s.name === step.name ? step : s)) }));
        } else if (event === "approval_required") {
          await sleep(t.reveal);
          setDialogOpen(true);
        } else if (event === "final") {
          applyRun(data.run as AgentRun);
        } else if (event === "error") {
          setError(String(data.message));
        }
      }
      if (streamError) throw streamError;
    } catch (err) {
      if ((err as Error)?.name !== "AbortError") setError(errorMessage(err));
      setView((v) => (v.status === "running" ? { ...v, status: "failed" } : v));
    } finally {
      setRunning(false);
    }
  }

  async function decide(decision: "approve" | "reject") {
    if (!view.runId) return;
    setDeciding(decision);
    try {
      const result = await api<{ run: AgentRun }>(`/api/agent/runs/${view.runId}/${decision}`, { method: "POST" });
      applyRun(result.run);
      setDialogOpen(false);
      toast.success(decision === "approve" ? "Plan saved and application added to your tracker." : "Plan discarded. Nothing was saved.");
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setDeciding(null);
    }
  }

  const reset = () => {
    abortRef.current?.abort();
    loadedRun.current = null;
    setView(IDLE);
    setError(null);
    setQuery({ company });
  };

  const state = view.state;
  const pending = state?.pending;
  const statusInfo = view.status !== "idle" ? RUN_STATUS[view.status] : null;
  const toolCalls = state?.tool_calls ?? view.steps.reduce((n, s) => n + s.attempts, 0);
  const maxSteps = state?.max_steps ?? 8;
  const recoveries = view.steps.filter((s) => s.recovery && s.status !== "pending");
  const decided = view.status === "approved" || view.status === "rejected";

  return (
    <div>
      <PageHeader
        title="Prep agent"
        description="Give it a company. It checks eligibility, matches your resume, reads the company's process and seniors' write-ups, and drafts a weekly plan. Nothing is saved until you approve."
      />

      <div className="mb-6 flex flex-col gap-3 rounded-xl border bg-muted/40 p-4 lg:flex-row lg:items-end">
        <div className="grid gap-1.5">
          <Label htmlFor="agent-company">Prepare me for</Label>
          <CompanySelect id="agent-company" value={company} onChange={(id) => setQuery({ company: id })} disabled={running} data-tour="agent-company" />
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="agent-fault">Recovery demo</Label>
          <Select value={fault} onValueChange={setFault} disabled={running}>
            <SelectTrigger id="agent-fault" className="w-full sm:w-64" data-tour="agent-fault">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {FAULTS.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex gap-2 lg:ml-auto">
          {view.status !== "idle" && !running && (
            <Button type="button" variant="outline" onClick={reset}>
              <RotateCcw aria-hidden="true" />
              New run
            </Button>
          )}
          <Button type="button" onClick={() => void start()} disabled={!company || running} data-tour="agent-start">
            {running ? <Loader2 className="animate-spin" aria-hidden="true" /> : <Play aria-hidden="true" />}
            {running ? "Running" : "Start"}
          </Button>
        </div>
      </div>

      {error && (
        <div className="mb-6">
          <ErrorState message={error} onRetry={() => void start()} />
        </div>
      )}

      {view.status === "idle" ? (
        <EmptyState
          title="No run yet"
          message="Choose a company and press Start. Try Nimbusware for a full plan, or Veltrix to see what happens when you are not eligible."
          action={
            <div className="flex flex-wrap justify-center gap-2">
              <Button type="button" size="sm" variant="secondary" onClick={() => setQuery({ company: "nimbusware" })}>
                Nimbusware
              </Button>
              <Button type="button" size="sm" variant="secondary" onClick={() => setQuery({ company: "veltrix" })}>
                Veltrix (not eligible)
              </Button>
            </div>
          }
        />
      ) : (
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_20rem]">
          <div className="min-w-0 space-y-3" data-tour="agent-timeline">
            {view.goal && <p className="text-sm font-medium">Goal: {view.goal}</p>}
            <AnimatePresence initial={false}>
              {view.steps.map((step, index) => (
                <motion.div key={step.name} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: t.reveal / 1000 }}>
                  <StepCard step={step} index={index} />
                </motion.div>
              ))}
            </AnimatePresence>

            {pending && view.runId && (
              <Confirmation
                approval={decided ? { id: String(view.runId), approved: view.status === "approved" } : { id: String(view.runId) }}
                state={decided ? "approval-responded" : "approval-requested"}
                className="mt-4"
                data-tour="agent-confirmation"
              >
                <ConfirmationRequest>
                  <p className="text-sm">
                    The plan is ready. Approving saves it and adds {pending.application.company_name} to your applications as planned.
                  </p>
                </ConfirmationRequest>
                <ConfirmationAccepted>
                  <p className="text-sm">
                    <CheckIcon className="mr-1.5 inline size-4 align-[-3px] text-success" aria-hidden="true" />
                    Approved. The plan is on your{" "}
                    <Link href="/dashboard" className="text-link underline underline-offset-4">
                      dashboard
                    </Link>{" "}
                    and the application is in your{" "}
                    <Link href="/applications" className="text-link underline underline-offset-4">
                      tracker
                    </Link>
                    .
                  </p>
                </ConfirmationAccepted>
                <ConfirmationRejected>
                  <p className="text-sm">
                    <XIcon className="mr-1.5 inline size-4 align-[-3px] text-muted-foreground" aria-hidden="true" />
                    Rejected. Nothing was saved.
                  </p>
                </ConfirmationRejected>
                <ConfirmationActions>
                  {!decided && (
                    <ConfirmationAction variant="outline" onClick={() => setDialogOpen(true)}>
                      Review the plan
                    </ConfirmationAction>
                  )}
                </ConfirmationActions>
              </Confirmation>
            )}

            {view.status === "completed" && state?.outcome === "not_eligible" && (
              <Panel className="mt-4 border-warning/30" data-tour="agent-not-eligible">
                <p className="font-medium">No plan: you are not eligible for {state.company_name}</p>
                <p className="mt-1 text-sm text-muted-foreground">{state.message}</p>
                {state.alternatives.length > 0 && (
                  <div className="mt-4 flex flex-wrap gap-2">
                    {state.alternatives.map((alt) => (
                      <Button
                        key={alt.company_id}
                        type="button"
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          loadedRun.current = null;
                          setView(IDLE);
                          setQuery({ company: alt.company_id });
                        }}
                      >
                        Prepare for {alt.company_name}
                        <span className="text-muted-foreground">{alt.ctc_label}</span>
                      </Button>
                    ))}
                  </div>
                )}
              </Panel>
            )}

            {view.status === "failed" && state?.message && (
              <div className="mt-4">
                <ErrorState message={state.message} onRetry={() => void start()} />
              </div>
            )}
          </div>

          <aside className="min-w-0" aria-label="Run state" data-tour="agent-state">
            <Panel className="space-y-5 xl:sticky xl:top-20">
              <div>
                <p className="text-sm text-muted-foreground">Status</p>
                <div className="mt-1">{statusInfo && <ToneBadge tone={statusInfo.tone}>{statusInfo.label}</ToneBadge>}</div>
              </div>
              <div>
                <div className="flex items-baseline justify-between text-sm">
                  <span className="text-muted-foreground">Tool calls used</span>
                  <span className="font-medium num">
                    {toolCalls} of {maxSteps}
                  </span>
                </div>
                <Progress value={(toolCalls / maxSteps) * 100} className="mt-2 h-1.5" aria-label="Tool call budget used" />
                <p className="mt-1.5 text-xs text-muted-foreground">The run stops if it reaches the limit. Retries count.</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Recovery</p>
                {recoveries.length ? (
                  <ul className="mt-1 space-y-1 text-sm">
                    {recoveries.map((step) => (
                      <li key={step.name}>
                        {step.label}: {step.recovery === "retry" ? "retried and recovered" : step.recovery === "fallback" ? "used its fallback" : "skipped (optional)"}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-1 text-sm">None needed</p>
                )}
              </div>
              {view.runId && (
                <p className="text-xs text-muted-foreground">
                  Run {view.runId}, saved after every step
                </p>
              )}
            </Panel>
          </aside>
        </div>
      )}

      <Dialog open={dialogOpen && Boolean(pending) && !decided} onOpenChange={setDialogOpen}>
        <DialogContent className="max-h-[90dvh] overflow-y-auto sm:max-w-2xl" data-tour="approval-dialog">
          <DialogHeader>
            <DialogTitle>Save this plan?</DialogTitle>
            <DialogDescription>Approving writes two things. Rejecting writes nothing.</DialogDescription>
          </DialogHeader>
          {pending && (
            <div className="space-y-5">
              <PlanPreview plan={pending.plan} />
              <div className="rounded-lg border p-4 text-sm">
                <p className="font-medium">Added to your applications</p>
                <dl className="mt-2 grid grid-cols-2 gap-2">
                  <dt className="text-muted-foreground">Company</dt>
                  <dd>{pending.application.company_name}</dd>
                  <dt className="text-muted-foreground">Role</dt>
                  <dd>{pending.application.role_title}</dd>
                  <dt className="text-muted-foreground">Status</dt>
                  <dd>Planned</dd>
                  <dt className="text-muted-foreground">Deadline</dt>
                  <dd className="num">{formatDate(pending.application.deadline)}</dd>
                </dl>
              </div>
            </div>
          )}
          <DialogFooter className="gap-2">
            <Button type="button" variant="outline" onClick={() => void decide("reject")} disabled={deciding !== null} data-tour="approval-reject">
              {deciding === "reject" && <Loader2 className="animate-spin" aria-hidden="true" />}
              Reject
            </Button>
            <Button type="button" onClick={() => void decide("approve")} disabled={deciding !== null} data-tour="approval-approve">
              {deciding === "approve" && <Loader2 className="animate-spin" aria-hidden="true" />}
              Approve and save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
