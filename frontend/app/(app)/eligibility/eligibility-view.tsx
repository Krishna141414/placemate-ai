"use client";

import { Check, ListChecks, X } from "lucide-react";
import { motion } from "motion/react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { CategoryBadge, ToneBadge } from "@/components/shared/badges";
import { CompanySelect } from "@/components/shared/company-select";
import { EmptyState, ErrorState, LoadingRows, PageHeader, Panel } from "@/components/shared/page";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api, errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useSpeed } from "@/lib/speed";
import type { Criterion, Eligibility, EligibilityAll } from "@/lib/types";
import { cn } from "@/lib/utils";

// Each example shows a different outcome for the demo student.
const EXAMPLES = [
  { id: "nimbusware", label: "Nimbusware", note: "eligible" },
  { id: "orbitpay", label: "OrbitPay", note: "fails CGPA" },
  { id: "lumengrid", label: "LumenGrid", note: "fails backlogs" },
  { id: "halcyon", label: "Halcyon", note: "fails branch" },
  { id: "zephyrnet", label: "ZephyrNet", note: "fails batch" },
];

function PassMark({ passed, label }: { passed: boolean; label: string }) {
  return passed ? (
    <span className="inline-flex items-center gap-1 text-success">
      <Check className="size-4" aria-hidden="true" />
      <span className="sr-only">{label} met</span>
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 text-error">
      <X className="size-4" aria-hidden="true" />
      <span className="sr-only">{label} not met</span>
    </span>
  );
}

function CriteriaList({ criteria }: { criteria: Criterion[] }) {
  const { t, reduced } = useSpeed();
  return (
    <ol className="divide-y" data-tour="eligibility-criteria">
      {criteria.map((criterion, index) => (
        <motion.li
          key={criterion.name}
          className="grid gap-x-6 gap-y-1 py-4 sm:grid-cols-[10rem_minmax(0,1fr)]"
          initial={reduced ? false : { opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: t.reveal / 1000, delay: (index * t.step) / 3000, ease: [0.16, 1, 0.3, 1] }}
        >
          <div className="flex items-center gap-2.5">
            <span
              className={cn(
                "grid size-6 place-items-center rounded-full",
                criterion.passed ? "bg-success-soft text-success" : "bg-error-soft text-error",
              )}
              aria-hidden="true"
            >
              {criterion.passed ? <Check className="size-3.5" /> : <X className="size-3.5" />}
            </span>
            <span className="font-medium">{criterion.label}</span>
          </div>
          <div className="min-w-0">
            <p className="text-sm">{criterion.reason}</p>
            <dl className="mt-1 flex flex-wrap gap-x-6 text-xs text-muted-foreground">
              <div className="flex gap-1">
                <dt>Required:</dt>
                <dd className="num">{criterion.required}</dd>
              </div>
              <div className="flex gap-1">
                <dt>Yours:</dt>
                <dd className="num">{criterion.actual}</dd>
              </div>
            </dl>
          </div>
        </motion.li>
      ))}
    </ol>
  );
}

function SingleResult({ result }: { result: Eligibility }) {
  return (
    <Panel className="p-0" data-tour="eligibility-result">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b px-5 py-4">
        <div className="min-w-0">
          <p className="text-lg font-semibold">{result.company_name}</p>
          <p className="text-sm text-muted-foreground">
            {result.role}, {result.ctc_label}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <CategoryBadge category={result.category} />
          {result.eligible ? (
            <ToneBadge tone="success" className="px-2 py-1 text-sm">
              <Check className="size-4" aria-hidden="true" />
              Eligible
            </ToneBadge>
          ) : (
            <ToneBadge tone="error" className="px-2 py-1 text-sm">
              <X className="size-4" aria-hidden="true" />
              Not eligible
            </ToneBadge>
          )}
        </div>
      </div>
      <div className="px-5">
        <CriteriaList criteria={result.criteria} />
      </div>
    </Panel>
  );
}

function AllResults({ data, onPick }: { data: EligibilityAll; onPick: (id: string) => void }) {
  const short: Record<string, string> = { cgpa: "CGPA", backlogs: "Backlogs", branch: "Branch", batch: "Batch" };
  return (
    <div data-tour="eligibility-all">
      <p className="mb-3 text-sm text-muted-foreground">
        Eligible for <span className="font-medium text-foreground num">{data.eligible_count}</span> of{" "}
        <span className="num">{data.total}</span> companies. Select a row for the reasons.
      </p>
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Company</TableHead>
              <TableHead className="hidden sm:table-cell">Category</TableHead>
              {Object.values(short).map((label) => (
                <TableHead key={label} className="text-center">
                  {label}
                </TableHead>
              ))}
              <TableHead className="text-right">Result</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.results.map((row) => (
              <TableRow
                key={row.company_id}
                className="cursor-pointer active:bg-secondary"
                onClick={() => onPick(row.company_id)}
                onKeyDown={(event) => event.key === "Enter" && onPick(row.company_id)}
                tabIndex={0}
                aria-label={`${row.company_name}: ${row.eligible ? "eligible" : "not eligible"}`}
              >
                <TableCell className="font-medium">{row.company_name}</TableCell>
                <TableCell className="hidden sm:table-cell">
                  <CategoryBadge category={row.category} />
                </TableCell>
                {row.criteria.map((criterion) => (
                  <TableCell key={criterion.name} className="text-center">
                    <span className="inline-flex justify-center">
                      <PassMark passed={criterion.passed} label={criterion.label} />
                    </span>
                  </TableCell>
                ))}
                <TableCell className="text-right">
                  {row.eligible ? <ToneBadge tone="success">Eligible</ToneBadge> : <ToneBadge tone="error">Not eligible</ToneBadge>}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

export function EligibilityView() {
  const { user } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const company = params.get("company") ?? undefined;
  const showAll = params.get("view") === "all";

  const key = showAll ? "all" : company ?? null;
  const [single, setSingle] = useState<Eligibility | null>(null);
  const [all, setAll] = useState<EligibilityAll | null>(null);
  const [result, setResult] = useState<{ key: string; error: string | null } | null>(null);
  const [attempt, setAttempt] = useState(0);
  // Loading is derived: a key is selected and its result has not arrived yet.
  const loading = key !== null && result?.key !== key;
  const error = result?.key === key ? result.error : null;

  const go = (query: Record<string, string>) => router.replace(`${pathname}?${new URLSearchParams(query).toString()}`, { scroll: false });

  useEffect(() => {
    if (key === null) return;
    let alive = true;
    const request =
      key === "all"
        ? api<EligibilityAll>("/api/tools/eligibility/all", { method: "POST" }).then((data) => alive && setAll(data))
        : api<Eligibility>("/api/eligibility", { method: "POST", body: { company_id: key } }).then((data) => alive && setSingle(data));
    request
      .then(() => alive && setResult({ key, error: null }))
      .catch((err) => alive && setResult({ key, error: errorMessage(err) }));
    return () => {
      alive = false;
    };
  }, [key, attempt]);

  const retry = () => {
    setResult(null);
    setAttempt((n) => n + 1);
  };

  const profile = user?.profile;

  return (
    <div>
      <PageHeader
        title="Eligibility"
        description="Your profile is checked against each company's criteria by fixed rules: CGPA, active backlogs, branch and batch. No AI guesses here."
      />

      <div className="mb-6 flex flex-col gap-4 rounded-xl border bg-muted/40 p-4 lg:flex-row lg:items-center lg:justify-between">
        <dl className="flex flex-wrap gap-x-8 gap-y-2 text-sm" aria-label="Your profile">
          {[
            ["Branch", profile?.branch],
            ["CGPA", profile?.cgpa?.toFixed(1)],
            ["Active backlogs", profile?.active_backlogs],
            ["Batch", profile?.batch],
          ].map(([label, value]) => (
            <div key={label as string}>
              <dt className="text-muted-foreground">{label}</dt>
              <dd className="font-medium num">{value ?? "Not set"}</dd>
            </div>
          ))}
        </dl>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <CompanySelect value={company} onChange={(id) => go({ company: id })} data-tour="eligibility-select" />
          <Button type="button" variant="outline" onClick={() => go({ view: "all" })} data-tour="eligibility-all-button">
            <ListChecks aria-hidden="true" />
            Check all companies
          </Button>
        </div>
      </div>

      <div className="mb-6 flex flex-wrap items-center gap-2 text-sm" data-tour="eligibility-examples">
        <span className="text-muted-foreground">Examples:</span>
        {EXAMPLES.map((example) => (
          <Button key={example.id} type="button" size="sm" variant="secondary" onClick={() => go({ company: example.id })}>
            {example.label}
            <span className="text-muted-foreground">{example.note}</span>
          </Button>
        ))}
      </div>

      {loading ? (
        <LoadingRows rows={5} />
      ) : error ? (
        <ErrorState message={error} onRetry={retry} />
      ) : showAll && all ? (
        <AllResults data={all} onPick={(id) => go({ company: id })} />
      ) : !showAll && single && single.company_id === company ? (
        <div className="space-y-4">
          <SingleResult result={single} />
          {single.eligible ? (
            <p className="text-sm text-muted-foreground">
              Next: <Link className="text-link underline-offset-4 hover:underline" href={`/agent?company=${single.company_id}`}>build a prep plan for {single.company_name}</Link> or{" "}
              <Link className="text-link underline-offset-4 hover:underline" href={`/resume?company=${single.company_id}`}>match your resume</Link>.
            </p>
          ) : null}
        </div>
      ) : (
        <EmptyState
          title="Pick a company to check"
          message="Choose one from the list, try an example above, or check all twelve at once."
          action={
            <Button type="button" size="sm" onClick={() => go({ view: "all" })}>
              Check all companies
            </Button>
          }
        />
      )}
    </div>
  );
}
