"use client";

import { Check, EyeOff, FileUp, Loader2, Minus, ScanSearch, UserRound } from "lucide-react";
import { motion } from "motion/react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useRef, useState } from "react";
import { toast } from "sonner";

import { ToneBadge } from "@/components/shared/badges";
import { CompanySelect } from "@/components/shared/company-select";
import { CountUp } from "@/components/shared/count-up";
import { EmptyState, ErrorState, PageHeader, Panel, Reveal, Section } from "@/components/shared/page";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { api, errorMessage } from "@/lib/api";
import { useSpeed } from "@/lib/speed";
import type { ResumeMatch } from "@/lib/types";
import { cn } from "@/lib/utils";

const MAX_CHARS = 20000;

function MatchRing({ value }: { value: number }) {
  const { t, reduced } = useSpeed();
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const tone = value >= 75 ? "var(--success)" : value >= 50 ? "var(--blue)" : "var(--warning)";
  return (
    <div className="relative size-40 shrink-0" data-tour="match-ring">
      <svg viewBox="0 0 128 128" className="size-40 -rotate-90" aria-hidden="true">
        <circle cx="64" cy="64" r={radius} fill="none" stroke="var(--rule)" strokeWidth="10" />
        <motion.circle
          cx="64"
          cy="64"
          r={radius}
          fill="none"
          stroke={tone}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: reduced ? circumference * (1 - value / 100) : circumference }}
          animate={{ strokeDashoffset: circumference * (1 - value / 100) }}
          transition={{ duration: t.countUp / 1000, ease: [0.16, 1, 0.3, 1] }}
        />
      </svg>
      <div className="absolute inset-0 grid place-items-center text-center">
        <div>
          <CountUp value={value} suffix="%" startOnView={false} className="text-3xl font-semibold tracking-tight" />
          <p className="text-xs text-muted-foreground">match</p>
        </div>
      </div>
    </div>
  );
}

function SkillChips({ title, items, tone, icon }: { title: string; items: string[]; tone: "success" | "error" | "neutral"; icon: "check" | "minus" | "none" }) {
  if (!items.length) return null;
  return (
    <div>
      <p className="mb-2 text-sm font-medium">{title}</p>
      <ul className="flex flex-wrap gap-1.5">
        {items.map((skill) => (
          <li key={skill}>
            <ToneBadge tone={tone} className="px-2 py-1 text-sm font-normal">
              {icon === "check" && <Check className="size-3.5" aria-hidden="true" />}
              {icon === "minus" && <Minus className="size-3.5" aria-hidden="true" />}
              {skill}
            </ToneBadge>
          </li>
        ))}
      </ul>
    </div>
  );
}

function RedactionNotice({ result }: { result: ResumeMatch }) {
  const counts = result.redaction.counts;
  const parts = [
    counts.phone && `${counts.phone} phone number${counts.phone > 1 ? "s" : ""}`,
    counts.email && `${counts.email} email${counts.email > 1 ? "s" : ""}`,
    counts.address && `${counts.address} address${counts.address > 1 ? "es" : ""}`,
    counts.link && `${counts.link} profile link${counts.link > 1 ? "s" : ""}`,
  ].filter(Boolean) as string[];
  return (
    <Panel className="border-success/30 bg-success-soft/40" data-tour="pii-notice">
      <div className="flex items-start gap-3">
        <EyeOff className="mt-0.5 size-5 shrink-0 text-success" aria-hidden="true" />
        <div className="min-w-0 flex-1">
          <p className="font-medium">{parts.length ? `${parts.join(", ")} removed before any AI saw your resume` : "No contact details found to remove"}</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Matching used only the redacted text below. Contact details are never sent to a model and never written to a log.
          </p>
          <Collapsible className="mt-3">
            <CollapsibleTrigger asChild>
              <Button type="button" size="sm" variant="outline">
                Show what the model saw
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap rounded-lg border bg-background p-3 font-mono text-xs leading-relaxed">
                {result.redaction.preview}
              </pre>
            </CollapsibleContent>
          </Collapsible>
        </div>
      </div>
    </Panel>
  );
}

export function ResumeView() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const company = params.get("company") ?? undefined;
  const [text, setText] = useState("");
  const [save, setSave] = useState(false);
  const [busy, setBusy] = useState<"match" | "load" | "upload" | null>(null);
  const [result, setResult] = useState<ResumeMatch | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  async function loadSaved() {
    setBusy("load");
    try {
      const saved = await api<{ text: string; has_resume: boolean }>("/api/tools/resume");
      if (!saved.has_resume) toast.info("No resume saved in your profile yet. Paste one and turn on saving.");
      else setText(saved.text);
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  async function upload(file: File) {
    setBusy("upload");
    try {
      const form = new FormData();
      form.append("file", file);
      const extracted = await api<{ text: string; filename: string }>("/api/tools/resume-extract", { method: "POST", form });
      setText(extracted.text);
      toast.success(`Read ${extracted.filename}`);
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setBusy(null);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function match() {
    if (!company) {
      toast.error("Choose a company first.");
      return;
    }
    setBusy("match");
    setError(null);
    try {
      const data = await api<ResumeMatch>("/api/tools/resume-match", {
        method: "POST",
        body: { company_id: company, resume_text: text.trim() || null, save_to_profile: save && Boolean(text.trim()) },
      });
      setResult(data);
      if (save && text.trim()) toast.success("Resume saved to your profile.");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div>
      <PageHeader
        title="Resume match"
        description="See which of a company's required and preferred skills your resume shows, and how closely it reads like the job description."
      />

      <div className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
        <Section title="Your resume">
          <div className="mb-3 flex flex-wrap gap-2">
            <Button type="button" size="sm" variant="outline" onClick={() => void loadSaved()} disabled={busy !== null} data-tour="resume-demo">
              {busy === "load" ? <Loader2 className="animate-spin" aria-hidden="true" /> : <UserRound aria-hidden="true" />}
              Use my saved resume
            </Button>
            <Button type="button" size="sm" variant="outline" onClick={() => fileRef.current?.click()} disabled={busy !== null}>
              {busy === "upload" ? <Loader2 className="animate-spin" aria-hidden="true" /> : <FileUp aria-hidden="true" />}
              Upload .txt or .pdf
            </Button>
            <input
              ref={fileRef}
              type="file"
              accept=".txt,.md,.pdf,text/plain,application/pdf"
              className="sr-only"
              aria-label="Upload a resume file"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) void upload(file);
              }}
            />
          </div>
          <Label htmlFor="resume-text" className="sr-only">
            Resume text
          </Label>
          <Textarea
            id="resume-text"
            name="resume"
            value={text}
            onChange={(event) => setText(event.target.value.slice(0, MAX_CHARS))}
            placeholder="Paste your resume here. Leave it empty to use the one saved in your profile."
            className="max-h-[28rem] min-h-80 overflow-y-auto font-mono text-sm leading-relaxed"
            data-tour="resume-text"
          />
          <div className="mt-1 flex justify-between text-xs text-muted-foreground">
            <span>Phone numbers, emails and addresses are removed before matching.</span>
            <span className="num">
              {text.length.toLocaleString()}/{MAX_CHARS.toLocaleString()}
            </span>
          </div>

          <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center">
            <CompanySelect value={company} onChange={(id) => router.replace(`${pathname}?company=${id}`, { scroll: false })} data-tour="resume-company" />
            <Button type="button" onClick={() => void match()} disabled={busy !== null || !company} data-tour="resume-match-button">
              {busy === "match" ? <Loader2 className="animate-spin" aria-hidden="true" /> : <ScanSearch aria-hidden="true" />}
              Match resume
            </Button>
          </div>
          <div className="mt-4 flex items-center gap-2">
            <Switch id="save-resume" checked={save} onCheckedChange={setSave} disabled={!text.trim()} />
            <Label htmlFor="save-resume" className="text-sm font-normal">
              Save this text to my profile (the prep agent uses it)
            </Label>
          </div>
        </Section>

        <Section title="Result" aria-live="polite">
          {error ? (
            <ErrorState message={error} onRetry={() => void match()} />
          ) : busy === "match" ? (
            <Panel className="flex items-center gap-3 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" aria-hidden="true" />
              Removing contact details, finding skills and comparing with the job description…
            </Panel>
          ) : !result ? (
            <EmptyState title="No match yet" message="Load or paste a resume, choose a company and press Match resume." />
          ) : (
            <Reveal className="space-y-6" key={`${result.company_id}-${result.match_pct}`}>
              <Panel className="flex flex-col items-center gap-6 sm:flex-row" data-tour="match-result">
                <MatchRing value={result.match_pct} />
                <div className="min-w-0 flex-1 space-y-3">
                  <div>
                    <p className="text-lg font-semibold">{result.company_name}</p>
                    <p className="text-sm text-muted-foreground">{result.role}</p>
                  </div>
                  <dl className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <dt className="text-muted-foreground">Skill coverage</dt>
                      <dd className="font-medium num">{Math.round(result.skill_score * 100)}%</dd>
                    </div>
                    <div>
                      <dt className="text-muted-foreground">Similarity to the job</dt>
                      <dd className="font-medium num">{Math.round(result.semantic_score * 100)}%</dd>
                    </div>
                  </dl>
                  <Collapsible>
                    <CollapsibleTrigger className="text-sm text-link underline-offset-4 hover:underline">How is this calculated?</CollapsibleTrigger>
                    <CollapsibleContent>
                      <p className="mt-2 text-sm text-muted-foreground">{result.formula}</p>
                    </CollapsibleContent>
                  </Collapsible>
                </div>
              </Panel>

              <div className={cn("grid gap-5", "sm:grid-cols-2")} data-tour="skill-chips">
                <SkillChips title="Required skills you show" items={result.matched_required} tone="success" icon="check" />
                <SkillChips title="Required skills missing" items={result.missing_required} tone="error" icon="minus" />
                <SkillChips title="Preferred skills you show" items={result.matched_preferred} tone="success" icon="check" />
                <SkillChips title="Preferred skills missing" items={result.missing_preferred} tone="neutral" icon="minus" />
              </div>
              {result.extra_skills.length > 0 && (
                <p className="text-sm text-muted-foreground">Also on your resume: {result.extra_skills.join(", ")}.</p>
              )}

              <div>
                <p className="mb-2 text-sm font-medium">What to do next</p>
                <ul className="list-disc space-y-1 pl-5 text-sm">
                  {result.advice.map((tip) => (
                    <li key={tip}>{tip}</li>
                  ))}
                </ul>
              </div>

              <RedactionNotice result={result} />
            </Reveal>
          )}
        </Section>
      </div>
    </div>
  );
}
