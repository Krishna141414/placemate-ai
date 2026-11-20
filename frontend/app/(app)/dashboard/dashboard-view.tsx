"use client";

import { ArrowRight, Bot, CheckCircle2, Circle } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";

import { CategoryBadge, ToneBadge } from "@/components/shared/badges";
import { EmptyState, ErrorState, LoadingRows, Panel, Reveal, Section } from "@/components/shared/page";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api, errorMessage } from "@/lib/api";
import { useApi, type ApiState } from "@/lib/use-api";
import { useAuth } from "@/lib/auth";
import { daysUntil, dueLabel, formatDateTime, STATUS_LABELS } from "@/lib/format";
import type { Application, ConversationSummary, EligibilityAll, PrepPlan } from "@/lib/types";
import { cn } from "@/lib/utils";

function greeting() {
  const hour = new Date().getHours();
  return hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
}

export function DashboardView() {
  const { user } = useAuth();
  const eligibility = useApi<EligibilityAll>("/api/tools/eligibility/all", "POST");
  const applications = useApi<Application[]>("/api/applications");
  const conversations = useApi<ConversationSummary[]>("/api/conversations");
  const plans = useApi<PrepPlan[]>("/api/prep-plans");
  const profile = user?.profile;

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">
          {greeting()}, {user?.name.split(" ")[0]}
        </h1>
        {profile && (
          <dl className="mt-3 flex flex-wrap gap-x-8 gap-y-2 text-sm" data-tour="profile-summary">
            {[
              ["Branch", profile.branch],
              ["CGPA", profile.cgpa?.toFixed(1)],
              ["Active backlogs", profile.active_backlogs],
              ["Batch", profile.batch],
            ].map(([label, value]) => (
              <div key={label as string}>
                <dt className="text-muted-foreground">{label}</dt>
                <dd className="font-medium num">{value ?? "Not set"}</dd>
              </div>
            ))}
          </dl>
        )}
      </div>

      <div className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="min-w-0 space-y-8">
          <Section
            title="Companies you can apply to"
            description={eligibility.data ? `${eligibility.data.eligible_count} of ${eligibility.data.total} companies on campus this season` : undefined}
            actions={
              <Button asChild variant="ghost" size="sm">
                <Link href="/eligibility">
                  All criteria
                  <ArrowRight aria-hidden="true" />
                </Link>
              </Button>
            }
            data-tour="dashboard-eligibility"
          >
            {eligibility.loading ? (
              <LoadingRows rows={5} />
            ) : eligibility.error ? (
              <ErrorState message={eligibility.error} onRetry={eligibility.reload} />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Company</TableHead>
                    <TableHead className="hidden md:table-cell">Role</TableHead>
                    <TableHead>Category</TableHead>
                    <TableHead className="text-right">CTC</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {eligibility.data!.results
                    .filter((row) => row.eligible)
                    .map((row) => (
                      <TableRow key={row.company_id}>
                        <TableCell className="font-medium">{row.company_name}</TableCell>
                        <TableCell className="hidden text-muted-foreground md:table-cell">{row.role}</TableCell>
                        <TableCell>
                          <CategoryBadge category={row.category} />
                        </TableCell>
                        <TableCell className="text-right num">{row.ctc_label}</TableCell>
                      </TableRow>
                    ))}
                </TableBody>
              </Table>
            )}
          </Section>

          <PlanProgress plans={plans} />
        </div>

        <div className="min-w-0 space-y-8">
          <Section title="Upcoming deadlines" data-tour="dashboard-deadlines">
            {applications.loading ? (
              <LoadingRows rows={3} />
            ) : applications.error ? (
              <ErrorState message={applications.error} onRetry={applications.reload} />
            ) : !applications.data!.length ? (
              <EmptyState
                title="No applications tracked"
                message="Add the companies you are applying to and their deadlines show up here."
                action={
                  <Button asChild size="sm" variant="outline">
                    <Link href="/applications">Track an application</Link>
                  </Button>
                }
              />
            ) : (
              <ul className="divide-y rounded-xl border">
                {applications.data!.slice(0, 5).map((app) => {
                  const days = daysUntil(app.deadline);
                  return (
                    <li key={app.id} className="flex items-center justify-between gap-3 px-4 py-3">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium">{app.company_name}</p>
                        <p className="text-xs text-muted-foreground">{STATUS_LABELS[app.status]}</p>
                      </div>
                      <ToneBadge tone={days !== null && days >= 0 && days <= 7 ? "warning" : "neutral"}>{dueLabel(app.deadline)}</ToneBadge>
                    </li>
                  );
                })}
              </ul>
            )}
          </Section>

          <Section
            title="Recent questions"
            actions={
              <Button asChild variant="ghost" size="sm">
                <Link href="/ask">Ask</Link>
              </Button>
            }
          >
            {conversations.loading ? (
              <LoadingRows rows={3} />
            ) : conversations.error ? (
              <ErrorState message={conversations.error} onRetry={conversations.reload} />
            ) : !conversations.data!.length ? (
              <EmptyState title="Nothing asked yet" message="Questions you ask PlaceMate are saved here so you can reopen them." />
            ) : (
              <ul className="space-y-1">
                {conversations.data!.slice(0, 5).map((conversation) => (
                  <li key={conversation.id}>
                    <Link href={`/ask?c=${conversation.id}`} className="block rounded-lg px-3 py-2 hover:bg-muted active:bg-secondary">
                      <span className="line-clamp-1 text-sm">{conversation.title}</span>
                      <span className="text-xs text-muted-foreground">{formatDateTime(conversation.updated_at)}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Section>
        </div>
      </div>
    </div>
  );
}

function PlanProgress({ plans }: { plans: ApiState<PrepPlan[]> }) {
  const [saving, setSaving] = useState(false);
  const plan = plans.data?.[0];

  if (plans.loading) {
    return (
      <Section title="Your prep plan">
        <LoadingRows rows={3} />
      </Section>
    );
  }
  if (plans.error) {
    return (
      <Section title="Your prep plan">
        <ErrorState message={plans.error} onRetry={plans.reload} />
      </Section>
    );
  }
  if (!plan) {
    return (
      <Section title="Your prep plan" data-tour="dashboard-plan">
        <EmptyState
          title="No plan yet"
          message="The prep agent builds a week-by-week plan for one company. It is saved here once you approve it."
          action={
            <Button asChild size="sm">
              <Link href="/agent">
                <Bot aria-hidden="true" />
                Open the prep agent
              </Link>
            </Button>
          }
        />
      </Section>
    );
  }

  const done = new Set(plan.plan.done ?? []);
  const allKeys = plan.plan.weeks.flatMap((week) => week.tasks.map((_, i) => `w${week.week}-t${i}`));
  const progress = allKeys.length ? Math.round((allKeys.filter((key) => done.has(key)).length / allKeys.length) * 100) : 0;
  const currentWeek = plan.plan.weeks.find((week) => week.tasks.some((_, i) => !done.has(`w${week.week}-t${i}`))) ?? plan.plan.weeks.at(-1)!;

  async function toggle(key: string) {
    const nextDone = new Set(done);
    if (nextDone.has(key)) nextDone.delete(key);
    else nextDone.add(key);
    setSaving(true);
    try {
      const updated = await api<PrepPlan>(`/api/prep-plans/${plan!.id}`, { method: "PATCH", body: { done: [...nextDone] } });
      plans.setData([updated, ...(plans.data ?? []).slice(1)]);
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Section title="Your prep plan" description={plan.title} data-tour="dashboard-plan">
      <Panel>
        <div className="flex items-center gap-4">
          <Progress value={progress} className="h-2 flex-1" aria-label="Plan progress" />
          <span className="text-sm font-medium num">{progress}%</span>
        </div>
        <Reveal className="mt-5">
          <p className="text-sm font-medium">
            Week {currentWeek.week}: {currentWeek.focus}
          </p>
          <ul className="mt-3 space-y-1.5">
            {currentWeek.tasks.map((task, i) => {
              const key = `w${currentWeek.week}-t${i}`;
              const checked = done.has(key);
              return (
                <li key={key}>
                  <button
                    type="button"
                    role="checkbox"
                    aria-checked={checked}
                    disabled={saving}
                    onClick={() => void toggle(key)}
                    className={cn(
                      "flex w-full items-start gap-2.5 rounded-md px-2 py-1.5 text-left text-sm hover:bg-muted active:bg-secondary disabled:cursor-not-allowed disabled:opacity-55",
                      checked && "text-muted-foreground line-through",
                    )}
                  >
                    {checked ? (
                      <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-success" aria-hidden="true" />
                    ) : (
                      <Circle className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                    )}
                    {task}
                  </button>
                </li>
              );
            })}
          </ul>
        </Reveal>
      </Panel>
    </Section>
  );
}
