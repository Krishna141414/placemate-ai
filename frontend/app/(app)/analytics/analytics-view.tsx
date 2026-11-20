"use client";

import { FileStack, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";

import { CountUp } from "@/components/shared/count-up";
import { ProviderBadge, ToneBadge } from "@/components/shared/badges";
import { EmptyState, ErrorState, LoadingRows, PageHeader, Section } from "@/components/shared/page";
import { Button } from "@/components/ui/button";
import { ChartContainer, ChartLegend, ChartLegendContent, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDate, formatDateTime, plural, pct, seconds } from "@/lib/format";
import type { Analytics, EventRow } from "@/lib/types";
import { useApi } from "@/lib/use-api";

const dayChart = {
  answered: { label: "Answered", color: "var(--chart-1)" },
  refused: { label: "Not in the documents", color: "var(--warning)" },
  blocked: { label: "Blocked", color: "var(--error)" },
} satisfies ChartConfig;

const LOG_TYPES = [
  { value: "all", label: "All activity" },
  { value: "ask", label: "Questions answered" },
  { value: "ask_refused", label: "Questions not answered" },
  { value: "ask_blocked", label: "Blocked messages" },
  { value: "eligibility_check", label: "Eligibility checks" },
  { value: "resume_match", label: "Resume matches" },
  { value: "agent_run", label: "Prep agent runs" },
  { value: "agent_approved", label: "Plans approved" },
  { value: "document_upload", label: "Uploads" },
  { value: "document_upload_rejected", label: "Rejected uploads" },
  { value: "login_failed", label: "Failed logins" },
];

function Totals({ data }: { data: Analytics }) {
  const t = data.totals;
  const items: [string, number, string?][] = [
    ["Questions asked", t.questions],
    ["Answered", t.answered, t.answer_rate !== null ? `${pct(t.answer_rate)} of questions` : undefined],
    ["Not in the documents", t.unanswered, "candidates for a new document"],
    ["Blocked", t.blocked, "injection attempts stopped"],
    ["Students active", t.active_students],
    ["Plans approved", t.plans_approved, `${t.agent_runs} agent runs`],
  ];
  return (
    <dl className="grid grid-cols-2 gap-x-6 gap-y-6 border-y py-6 sm:grid-cols-3 xl:grid-cols-6" data-tour="analytics-totals">
      {items.map(([label, value, hint]) => (
        <div key={label} className="min-w-0">
          <dt className="text-sm text-muted-foreground">{label}</dt>
          <dd className="mt-1 text-2xl font-semibold tracking-tight">
            <CountUp value={value} startOnView={false} />
          </dd>
          {hint && <dd className="mt-0.5 text-xs text-muted-foreground">{hint}</dd>}
        </div>
      ))}
    </dl>
  );
}

function QuestionsChart({ data }: { data: Analytics }) {
  const rows = data.questions_per_day.map((day) => ({ ...day, label: formatDate(day.date, { day: "numeric", month: "short" }) }));
  const any = rows.some((r) => r.answered + r.refused + r.blocked > 0);
  if (!any) return <EmptyState title="No questions in the last 14 days" message="Questions students ask show up here by day." />;
  return (
    <ChartContainer config={dayChart} className="h-64 w-full" aria-label="Questions per day for the last 14 days">
      <BarChart data={rows} margin={{ left: -16, right: 8, top: 8 }}>
        <CartesianGrid vertical={false} strokeDasharray="0" stroke="var(--rule)" />
        <XAxis dataKey="label" tickLine={false} axisLine={false} tickMargin={8} interval="preserveStartEnd" />
        <YAxis tickLine={false} axisLine={false} allowDecimals={false} width={40} />
        <ChartTooltip cursor={{ fill: "var(--muted)" }} content={<ChartTooltipContent />} />
        <ChartLegend content={<ChartLegendContent />} />
        <Bar dataKey="answered" stackId="q" fill="var(--color-answered)" stroke="var(--background)" strokeWidth={2} maxBarSize={24} />
        <Bar dataKey="refused" stackId="q" fill="var(--color-refused)" stroke="var(--background)" strokeWidth={2} maxBarSize={24} />
        <Bar dataKey="blocked" stackId="q" fill="var(--color-blocked)" stroke="var(--background)" strokeWidth={2} maxBarSize={24} radius={[4, 4, 0, 0]} />
      </BarChart>
    </ChartContainer>
  );
}

function QuestionTable({ rows, empty }: { rows: Analytics["top_questions"]; empty: string }) {
  if (!rows.length) return <p className="py-6 text-sm text-muted-foreground">{empty}</p>;
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Question</TableHead>
          <TableHead className="text-right">Times</TableHead>
          <TableHead className="hidden text-right sm:table-cell">Last asked</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row) => (
          <TableRow key={row.question}>
            <TableCell className="max-w-md whitespace-normal">{row.question}</TableCell>
            <TableCell className="text-right num">{row.count}</TableCell>
            <TableCell className="hidden text-right text-muted-foreground sm:table-cell">{formatDateTime(row.last_asked)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function EligibilityTable({ data }: { data: Analytics }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Company</TableHead>
          <TableHead>Eligible students</TableHead>
          <TableHead className="hidden md:table-cell">Most common reason students miss out</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {data.eligibility.map((row) => (
          <TableRow key={row.company_id}>
            <TableCell>
              <p className="font-medium">{row.company_name}</p>
              <p className="text-xs text-muted-foreground">{row.category}</p>
            </TableCell>
            <TableCell className="min-w-44">
              <div className="flex items-center gap-3">
                <div className="h-2 w-28 overflow-hidden rounded-full bg-secondary" aria-hidden="true">
                  <div className="h-full rounded-full bg-primary" style={{ width: `${row.total ? (row.eligible / row.total) * 100 : 0}%` }} />
                </div>
                <span className="text-sm num">
                  {row.eligible} of {row.total}
                </span>
              </div>
            </TableCell>
            <TableCell className="hidden md:table-cell">
              {row.top_blocker ? (
                <span className="text-sm">
                  {row.top_blocker} <span className="text-muted-foreground num">({plural(row.top_blocker_count, "student")})</span>
                </span>
              ) : (
                <span className="text-sm text-muted-foreground">Everyone qualifies</span>
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function ActivityLog() {
  const [type, setType] = useState("all");
  const log = useApi<EventRow[]>(`/api/admin/logs?limit=50${type === "all" ? "" : `&type=${type}`}`);
  return (
    <Section
      title="Recent activity"
      description="Every question, check, upload and login, newest first. Contact details are scrubbed before anything is stored."
      actions={
        <Select value={type} onValueChange={setType}>
          <SelectTrigger className="h-8 w-52" aria-label="Filter activity">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {LOG_TYPES.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      }
      data-tour="analytics-log"
    >
      {log.loading ? (
        <LoadingRows rows={6} />
      ) : log.error ? (
        <ErrorState message={log.error} onRetry={log.reload} />
      ) : !log.data!.length ? (
        <EmptyState title="Nothing here yet" message="Activity of this kind shows up as soon as it happens." />
      ) : (
        <div className="max-h-[28rem] overflow-auto">
          <Table>
            <TableHeader className="sticky top-0 bg-background">
              <TableRow>
                <TableHead className="w-36">When</TableHead>
                <TableHead>What happened</TableHead>
                <TableHead className="hidden lg:table-cell">Who</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {log.data!.map((row) => (
                <TableRow key={row.id}>
                  <TableCell className="whitespace-nowrap text-muted-foreground num">{formatDateTime(row.created_at)}</TableCell>
                  <TableCell className="max-w-xl whitespace-normal">{row.summary}</TableCell>
                  <TableCell className="hidden text-muted-foreground lg:table-cell">{row.user ?? "Anonymous"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </Section>
  );
}

export function AnalyticsView() {
  const analytics = useApi<Analytics>("/api/admin/analytics");
  const data = analytics.data;

  return (
    <div>
      <PageHeader
        title="Analytics"
        description="What students ask, what the documents do not cover, and who can apply where."
        actions={
          <Button type="button" variant="outline" size="sm" onClick={analytics.reload} disabled={analytics.loading}>
            <RefreshCw aria-hidden="true" />
            Refresh
          </Button>
        }
      />

      {analytics.error ? (
        <ErrorState message={analytics.error} onRetry={analytics.reload} />
      ) : !data ? (
        <div className="space-y-6" aria-busy="true">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-64 w-full" />
          <LoadingRows rows={5} />
        </div>
      ) : (
        <div className="space-y-12">
          <Totals data={data} />

          <Section title="Questions per day" description="Last 14 days" data-tour="analytics-chart">
            <QuestionsChart data={data} />
          </Section>

          <div className="grid gap-10 xl:grid-cols-2">
            <Section title="Most asked" description="Answered questions, grouped when worded the same way" data-tour="analytics-top">
              <QuestionTable rows={data.top_questions} empty="No answered questions yet." />
            </Section>
            <Section
              title="Not answered"
              description="The documents did not cover these. Each one is a gap worth a notice."
              actions={
                <Button asChild size="sm" variant="ghost">
                  <Link href="/documents">
                    <FileStack aria-hidden="true" />
                    Add a document
                  </Link>
                </Button>
              }
              data-tour="analytics-unanswered"
            >
              <QuestionTable rows={data.unanswered_questions} empty="Every question so far was covered by the documents." />
            </Section>
          </div>

          <Section title="Eligibility across companies" description="From the current profiles of all registered students" data-tour="analytics-eligibility">
            <EligibilityTable data={data} />
          </Section>

          <div className="grid gap-10 xl:grid-cols-2">
            <Section title="Who answered" description="Which provider wrote each answer, and how long it took on average" data-tour="analytics-providers">
              {data.provider_usage.length ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Provider</TableHead>
                      <TableHead className="text-right">Answers</TableHead>
                      <TableHead className="text-right">Average time</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.provider_usage.map((row) => (
                      <TableRow key={row.provider}>
                        <TableCell>
                          <ProviderBadge provider={row.provider} />
                        </TableCell>
                        <TableCell className="text-right num">{row.count}</TableCell>
                        <TableCell className="text-right num">{seconds(row.avg_latency_ms)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <p className="py-6 text-sm text-muted-foreground">No answers yet.</p>
              )}
            </Section>
            <Section title="Blocked attempts" description="Messages the input guard stopped before anything was retrieved">
              {data.blocked_attempts.length ? (
                <ul className="divide-y">
                  {data.blocked_attempts.map((row) => (
                    <li key={`${row.at}-${row.question}`} className="py-3">
                      <p className="text-sm">{row.question}</p>
                      <p className="mt-1 flex flex-wrap gap-1.5">
                        {row.reasons.map((reason) => (
                          <ToneBadge key={reason} tone="error">
                            {reason}
                          </ToneBadge>
                        ))}
                        <span className="text-xs text-muted-foreground">{formatDateTime(row.at)}</span>
                      </p>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="py-6 text-sm text-muted-foreground">None so far.</p>
              )}
            </Section>
          </div>

          <ActivityLog />
        </div>
      )}
    </div>
  );
}
