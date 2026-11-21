"use client";

import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { ArrowRight, ExternalLink } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { CountUp } from "@/components/shared/count-up";
import { Button } from "@/components/ui/button";
import { REPO_URL, loadEvalSummary, type EvalSummary } from "@/lib/eval-summary";

import { HeroAnswer } from "./hero-answer";
import { SmoothScroll } from "./smooth-scroll";
import "./landing.css";

gsap.registerPlugin(ScrollTrigger, useGSAP);

const PROBLEMS = [
  {
    title: "Rules live in PDFs and notices",
    text: "The one-offer rule, the CGPA cut-off and the dress code sit in different files, so students ask the placement cell instead.",
  },
  {
    title: "Eligibility is checked by hand",
    text: "Before every drive someone compares CGPA, backlogs, branch and batch against the criteria, one student at a time.",
  },
  {
    title: "Preparation starts without a map",
    text: "Students hear about the rounds from seniors and guess what to practise for each company.",
  },
];

const WALKTHROUGH = [
  {
    title: "Ask, with sources",
    text: "Answers come from the placement documents, and each sentence cites its source. If the documents don't cover a question, PlaceMate says so.",
    image: "/product/ask.webp",
    height: 585,
    alt: "The Ask page with a cited answer about the one-offer policy and its source cards",
  },
  {
    title: "Eligibility, criterion by criterion",
    text: "CGPA, backlogs, branch and batch are checked by code against the company's rules, with the reason for every pass or fail.",
    image: "/product/eligibility.webp",
    height: 640,
    alt: "The Eligibility page showing a company check that fails on CGPA",
  },
  {
    title: "Resume against the job",
    text: "You get a match score and see which required skills you have and which you're missing. Phone, email and address are removed before any model sees the text.",
    image: "/product/resume.webp",
    height: 640,
    alt: "The Resume match page with a match ring, matched and missing skills",
  },
  {
    title: "A plan you approve",
    text: "The prep agent checks eligibility, matches your resume and reads the company's process, then waits for your yes before saving anything.",
    image: "/product/agent.webp",
    height: 640,
    alt: "The Prep agent page with tool steps and the approval card",
  },
];

const TRACKS = [
  {
    name: "Answering a question",
    nodes: [
      { title: "Question", text: "Checked for prompt injection first" },
      { title: "Hybrid retrieval", text: "BM25 and vector search, fused with RRF" },
      { title: "Rerank", text: "A cross-encoder keeps the best five passages" },
      { title: "Answer with citations", text: "Grounded in the passages, or a refusal" },
    ],
  },
  {
    name: "Preparing you for a company",
    nodes: [
      { title: "Plan", text: "Steps for the company you name" },
      { title: "Tools", text: "Eligibility, resume match, the company's process" },
      { title: "Your approval", text: "Nothing is saved until you say yes" },
      { title: "Saved plan", text: "Week-by-week plan and a tracked application" },
    ],
  },
];

const STACK = [
  { group: "Backend", items: "FastAPI, SQLAlchemy, SQLite, Pydantic" },
  { group: "Retrieval", items: "FAISS, rank-bm25, MiniLM embeddings, a cross-encoder reranker" },
  { group: "Models", items: "Gemini, a local Qwen 0.5B, an extractive fallback" },
  { group: "Frontend", items: "Next.js, Tailwind, shadcn/ui, AI Elements, Motion, GSAP, Lenis" },
];

const DESKTOP_MOTION = "(min-width: 1024px) and (prefers-reduced-motion: no-preference)";
const WIDE = "(min-width: 768px)";
const MOTION = "(prefers-reduced-motion: no-preference)";

export function LandingPage() {
  const root = useRef<HTMLDivElement>(null);
  const [summary, setSummary] = useState<{ data: EvalSummary | null; error: boolean }>({ data: null, error: false });

  useEffect(() => {
    let alive = true;
    loadEvalSummary()
      .then((data) => alive && setSummary({ data, error: false }))
      .catch(() => alive && setSummary({ data: null, error: true }));
    return () => {
      alive = false;
    };
  }, []);

  useGSAP(
    () => {
      const mm = gsap.matchMedia();

      // Problem cards rise in as they reach the viewport.
      mm.add(MOTION, () => {
        gsap.from(".problem-card", {
          y: 24,
          opacity: 0,
          duration: 0.7,
          stagger: 0.12,
          ease: "power2.out",
          scrollTrigger: { trigger: ".problem-grid", start: "top 80%", once: true },
        });
      });

      // Walkthrough: pin the section and swap the four screens as you scroll.
      mm.add(DESKTOP_MOTION, () => {
        const section = root.current?.querySelector<HTMLElement>(".walk");
        if (!section) return;
        section.dataset.pinned = "true";
        const figures = gsap.utils.toArray<HTMLElement>(".walk-stack > figure");
        const captions = gsap.utils.toArray<HTMLElement>(".walk-cap");
        gsap.set(figures.slice(1), { autoAlpha: 0 });
        gsap.set(captions.slice(1), { opacity: 0.35 });
        const tl = gsap.timeline({
          scrollTrigger: {
            trigger: ".walk-pin",
            start: "top top",
            end: `+=${(figures.length - 1) * 70}%`,
            pin: true,
            scrub: 0.5,
          },
        });
        for (let i = 1; i < figures.length; i++) {
          tl.to(figures[i - 1], { autoAlpha: 0, duration: 0.4 }, i)
            .to(figures[i], { autoAlpha: 1, duration: 0.4 }, i)
            .to(captions[i - 1], { opacity: 0.35, duration: 0.4 }, i)
            .to(captions[i], { opacity: 1, duration: 0.4 }, i);
        }
        tl.to({}, { duration: 0.6 });
        return () => {
          delete section.dataset.pinned;
        };
      });

      // Pipeline: each track lights its nodes and draws its lines with the scroll.
      mm.add({ wide: WIDE, motion: MOTION }, (context) => {
        const { wide, motion } = context.conditions as { wide: boolean; motion: boolean };
        if (!motion) return;
        gsap.utils.toArray<HTMLElement>(".pipe-track").forEach((track) => {
          const tl = gsap.timeline({
            scrollTrigger: { trigger: track, start: "top 75%", end: "bottom 45%", scrub: 0.6 },
          });
          const nodes = track.querySelectorAll(".pipe-lit");
          const lines = track.querySelectorAll(".pipe-line > span");
          nodes.forEach((node, i) => {
            tl.from(node, { opacity: 0, duration: 0.5 });
            if (lines[i]) tl.from(lines[i], wide ? { scaleX: 0, duration: 0.7 } : { scaleY: 0, duration: 0.7 });
          });
        });
      });

      return () => mm.revert();
    },
    { scope: root },
  );

  const final = summary.data ? summary.data.runs[summary.data.primary]?.modes.final : null;
  const tests = summary.data?.tests ?? null;

  return (
    <SmoothScroll>
      <div ref={root} className="landing min-h-dvh bg-background text-foreground">
        <header className="mx-auto flex max-w-[var(--container)] items-center justify-between px-4 py-5 sm:px-6">
          <Link href="/" className="text-lg font-semibold tracking-tight">
            PlaceMate
          </Link>
          <nav aria-label="Landing" className="flex items-center gap-1 sm:gap-2">
            <a href="#how" className="hidden rounded-md px-3 py-2 text-sm text-muted-foreground hover:text-foreground sm:inline">
              How it works
            </a>
            <a href="#evidence" className="hidden rounded-md px-3 py-2 text-sm text-muted-foreground hover:text-foreground sm:inline">
              Results
            </a>
            <Button asChild size="sm">
              <Link href="/login">Try the demo</Link>
            </Button>
          </nav>
        </header>

        <main id="main">
          {/* 1. Hero */}
          <section className="mx-auto grid max-w-[var(--container)] items-center gap-12 px-4 pt-10 pb-20 sm:px-6 lg:grid-cols-[1fr_1.05fr] lg:pt-16 lg:pb-28" data-tour="landing-hero">
            <div>
              <h1 className="max-w-[14ch] text-4xl font-semibold tracking-tight text-balance sm:text-5xl lg:text-[3.5rem] lg:leading-[1.05]">
                Placement answers, with the source attached
              </h1>
              <p className="mt-5 max-w-[42ch] text-lg text-muted-foreground">
                Cited answers, eligibility checks and a prep plan you approve.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <Button asChild size="lg">
                  <Link href="/login">
                    Try the demo
                    <ArrowRight aria-hidden="true" />
                  </Link>
                </Button>
                <Button asChild size="lg" variant="outline">
                  <a href="#how">How it works</a>
                </Button>
              </div>
              <p className="mt-6 text-sm text-muted-foreground">Runs on sample data. Every company and student in it is fictional.</p>
            </div>
            <HeroAnswer />
          </section>

          {/* 2. The problem */}
          <section className="border-y bg-muted" aria-labelledby="problem-title" data-tour="landing-problem">
            <div className="mx-auto max-w-[var(--container)] px-4 py-20 sm:px-6">
              <h2 id="problem-title" className="max-w-[24ch] text-3xl font-semibold tracking-tight text-balance">
                The placement cell answers the same questions every week
              </h2>
              <div className="problem-grid mt-10 grid gap-4 md:grid-cols-3">
                {PROBLEMS.map((problem) => (
                  <article key={problem.title} className="problem-card rounded-xl border bg-card p-6">
                    <h3 className="font-semibold">{problem.title}</h3>
                    <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{problem.text}</p>
                  </article>
                ))}
              </div>
            </div>
          </section>

          {/* 3. Product walkthrough (pinned on large screens) */}
          <section className="walk" aria-labelledby="walk-title" data-tour="landing-walkthrough">
            <div className="walk-pin">
              <div className="mx-auto max-w-[var(--container)] px-4 py-20 sm:px-6 lg:flex lg:min-h-dvh lg:flex-col lg:justify-center lg:py-12">
                <h2 id="walk-title" className="text-3xl font-semibold tracking-tight">
                  Four things a student can do
                </h2>
                <div className="walk-grid mt-10">
                  <ol className="walk-caps">
                    {WALKTHROUGH.map((step, i) => (
                      <li key={step.title} className="walk-cap" data-tour={`landing-walk-${i + 1}`}>
                        <h3 className="font-semibold">{step.title}</h3>
                        <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{step.text}</p>
                      </li>
                    ))}
                  </ol>
                  <div className="walk-stack">
                    {WALKTHROUGH.map((step) => (
                      <figure key={step.title}>
                        <figcaption>
                          <h3 className="font-semibold">{step.title}</h3>
                          <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{step.text}</p>
                        </figcaption>
                        <div className="landing-frame">
                          <Image loading="eager" src={step.image} alt={step.alt} width={1008} height={step.height} sizes="(min-width: 1024px) 640px, 100vw" />
                        </div>
                      </figure>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* 4. How it works */}
          <section id="how" className="scroll-mt-6 border-t bg-muted" aria-labelledby="how-title" data-tour="landing-pipeline">
            <div className="mx-auto max-w-[var(--container)] px-4 py-20 sm:px-6">
              <h2 id="how-title" className="text-3xl font-semibold tracking-tight">
                What runs behind each answer and plan
              </h2>
              <div className="mt-10 space-y-12">
                {TRACKS.map((track) => (
                  <div key={track.name} className="pipe-track">
                    <h3 className="font-semibold">{track.name}</h3>
                    <ol className="pipe-row mt-4">
                      {track.nodes.map((node, i) => (
                        <li key={node.title} className="pipe-item">
                          <div className="pipe-node rounded-xl border bg-card p-4">
                            <span className="pipe-lit" aria-hidden="true" />
                            <p className="font-semibold">{node.title}</p>
                            <p className="mt-1 text-sm text-muted-foreground">{node.text}</p>
                          </div>
                          {i < track.nodes.length - 1 ? (
                            <div className="pipe-line" aria-hidden="true">
                              <span />
                            </div>
                          ) : null}
                        </li>
                      ))}
                    </ol>
                  </div>
                ))}
              </div>
            </div>
          </section>

          {/* 5. Built responsibly */}
          <section id="evidence" className="scroll-mt-6" aria-labelledby="evidence-title" data-tour="landing-evidence">
            <div className="mx-auto max-w-[var(--container)] px-4 py-20 sm:px-6">
              <h2 id="evidence-title" className="text-3xl font-semibold tracking-tight">
                What the tests show
              </h2>
              <p className="mt-3 max-w-[60ch] text-muted-foreground">
                These numbers come from the {final?.cases ?? 47}-case evaluation of the final pipeline and the backend test suite. The baseline comparison is on the Evaluation page.
              </p>
              {summary.error ? (
                <p className="mt-8 text-sm text-muted-foreground">The results file could not be loaded. They are in docs/evaluation.md in the repository.</p>
              ) : (
                <dl className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  <Stat label="Injection attempts blocked" value={final?.injection_block_rate} percent />
                  <Stat label="Answer sentences backed by a source" value={final?.groundedness} percent decimals={1} />
                  <Stat label="Correct refusals on questions the documents can't answer" value={final?.refusal_accuracy} percent />
                  <Stat label={tests ? `Backend tests passing, ${tests.coverage_pct ?? 0}% coverage` : "Backend tests passing"} value={tests?.passed} suffix={tests ? ` / ${tests.total}` : ""} />
                </dl>
              )}
              <div className="mt-8 flex flex-wrap gap-3">
                <Button asChild variant="outline">
                  <Link href="/login?next=/evaluation">See the full evaluation</Link>
                </Button>
                <Button asChild variant="ghost">
                  <a href={`${REPO_URL}/blob/main/docs/evaluation.md`} target="_blank" rel="noreferrer">
                    Read the method
                  </a>
                </Button>
              </div>
            </div>
          </section>

          {/* 6. Stack */}
          <section className="border-t" aria-labelledby="stack-title" data-tour="landing-stack">
            <div className="mx-auto max-w-[var(--container)] px-4 py-16 sm:px-6">
              <h2 id="stack-title" className="text-xl font-semibold tracking-tight">
                Built with
              </h2>
              <dl className="mt-6 grid gap-x-8 gap-y-4 sm:grid-cols-2">
                {STACK.map((row) => (
                  <div key={row.group} className="flex gap-4 border-b pb-4">
                    <dt className="w-24 shrink-0 text-sm font-medium">{row.group}</dt>
                    <dd className="text-sm text-muted-foreground">{row.items}</dd>
                  </div>
                ))}
              </dl>
            </div>
          </section>
        </main>

        <footer className="border-t">
          <div className="mx-auto flex max-w-[var(--container)] flex-col gap-3 px-4 py-8 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between sm:px-6">
            <p>Built by Krishna for the VoidMain internship final project.</p>
            <a href={REPO_URL} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 hover:text-foreground">
              Source on GitHub
              <ExternalLink className="size-3.5" aria-hidden="true" />
            </a>
          </div>
        </footer>
      </div>
    </SmoothScroll>
  );
}

function Stat({
  label,
  value,
  percent = false,
  decimals = 0,
  suffix = "",
}: {
  label: string;
  value: number | null | undefined;
  percent?: boolean;
  decimals?: number;
  suffix?: string;
}) {
  const shown = value == null ? null : percent ? value * 100 : value;
  return (
    <div className="flex flex-col rounded-xl border bg-card p-5">
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className="mt-auto pt-4 text-3xl font-semibold tracking-tight tabular-nums">
        {shown == null ? <span className="text-muted-foreground">-</span> : <CountUp value={shown} decimals={decimals} suffix={percent ? "%" : suffix} />}
      </dd>
    </div>
  );
}
