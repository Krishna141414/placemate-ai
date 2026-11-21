// The guided tour, one step per screen moment. Each step names the requirement
// it demonstrates (SHOWCASE.md section 3). Targets are `data-tour` values on the
// pages; actions run only when moving forward, never on Back.

import { TOUR_LIMITS } from "@/lib/speed";

export type TourAuth = "visitor" | "student" | "coordinator";

export interface TourTarget {
  /** a `data-tour` value */
  target: string;
  /** use the last match (newest answer turn) instead of the first */
  last?: boolean;
}

export type TourAction =
  /** click an element once it is enabled; optionally wait for a new item to finish */
  | ({
      do: "click";
      until?: {
        target: string;
        status?: string;
        timeout: number;
        newItem?: boolean;
      };
    } & TourTarget)
  /** wait for an element (optionally with data-status, or a filled text field) */
  | ({
      do: "wait";
      timeout: number;
      status?: string;
      filled?: boolean;
    } & TourTarget)
  /** move the spotlight to another element */
  | ({ do: "spot" } & TourTarget)
  /** hold for a number of pipeline steps (lib/speed.ts `step`) so the audience can read */
  | { do: "hold"; steps: number }
  /** fire a window event a page listens for */
  | { do: "event"; name: string; holdSteps?: number }
  /** delete an earlier demo upload with this file name, so the upload can be shown again */
  | { do: "remove-upload"; filename: string }
  /** wait until the app has navigated to a path */
  | { do: "path"; path: string; timeout: number };

export interface TourStep {
  id: string;
  /** where the step happens; query parameters in it must match too */
  route: string;
  /** the URL must have no other query parameters (stops a stale ?next= on /login) */
  exactQuery?: boolean;
  /** who must be logged in; "visitor" logs out first */
  auth?: TourAuth;
  /** what the spotlight lands on when the step opens */
  spot?: TourTarget;
  title: string;
  caption: string;
  /** the requirement this step proves */
  requirement: string;
  actions?: TourAction[];
}

export const TOUR_STEPS: TourStep[] = [
  {
    id: "landing-hero",
    route: "/",
    spot: { target: "landing-hero" },
    title: "PlaceMate",
    caption: "A placement copilot for engineering students, with a dashboard for the placement cell.",
    requirement: "Brief: a usable application for a real problem",
  },
  {
    id: "landing-answer",
    route: "/",
    spot: { target: "landing-answer" },
    title: "A cited answer",
    caption: "A real answer from the sample documents. Each sentence points to the passage it came from.",
    requirement: "RAG: answers carry numbered citations",
    actions: [{ do: "event", name: "pm:hero-replay", holdSteps: 2 }],
  },
  {
    id: "landing-problem",
    route: "/",
    spot: { target: "landing-problem" },
    title: "The problem",
    caption: "Rules are spread across files, eligibility is checked by hand, and preparation is guesswork.",
    requirement: "Requirements: the problem and its users",
  },
  {
    id: "landing-walkthrough",
    route: "/",
    spot: { target: "landing-walkthrough" },
    title: "Four student features",
    caption: "Ask with sources, eligibility, resume match and a prep plan the student approves.",
    requirement: "Interface: the core student flows",
  },
  {
    id: "landing-pipeline",
    route: "/",
    spot: { target: "landing-pipeline" },
    title: "How it works",
    caption: "Hybrid retrieval and a reranker behind every answer; tools and an approval step behind every plan.",
    requirement: "Architecture: RAG, tools and one agent",
  },
  {
    id: "landing-evidence",
    route: "/",
    spot: { target: "landing-evidence" },
    title: "Measured, not claimed",
    caption: "These numbers are read from the saved evaluation run and the latest test run.",
    requirement: "Evaluation: real results",
  },
  {
    id: "login-student",
    route: "/login",
    exactQuery: true,
    auth: "visitor",
    spot: { target: "demo-student" },
    title: "Log in as a student",
    caption: "Demo accounts are seeded. The session is a JWT in an httpOnly cookie.",
    requirement: "Security: authentication with roles",
    actions: [
      { do: "hold", steps: 1 },
      { do: "click", target: "demo-student" },
      { do: "path", path: "/dashboard", timeout: TOUR_LIMITS.target },
    ],
  },
  {
    id: "dashboard",
    route: "/dashboard",
    auth: "student",
    spot: { target: "dashboard-eligibility" },
    title: "Student dashboard",
    caption: "Which companies the student is eligible for, upcoming deadlines and plan progress.",
    requirement: "Interface: personalised overview",
  },
  {
    id: "ask-policy",
    route: "/ask",
    auth: "student",
    spot: { target: "ask-examples" },
    title: "Ask a policy question",
    caption: "Hybrid retrieval, reranking, then a grounded answer with citations and source cards.",
    requirement: "RAG: cited answer from the documents",
    actions: [
      {
        do: "click",
        target: "ask-example-policy",
        until: {
          target: "answer-turn",
          status: "done",
          timeout: TOUR_LIMITS.answer,
          newItem: true,
        },
      },
      { do: "spot", target: "answer-turn", last: true },
    ],
  },
  {
    id: "ask-pipeline",
    route: "/ask",
    auth: "student",
    spot: { target: "pipeline-panel", last: true },
    title: "How this was answered",
    caption: "Retrieved, reranked, generated and checked, with the provider that wrote the answer.",
    requirement: "Transparency: pipeline steps and provider badge",
  },
  {
    id: "ask-unanswerable",
    route: "/ask",
    auth: "student",
    spot: { target: "ask-examples" },
    title: "A question the documents don't answer",
    caption: "When the documents are silent, PlaceMate says so instead of guessing.",
    requirement: "RAG: refusal when the answer is not in the documents",
    actions: [
      {
        do: "click",
        target: "ask-example-unanswerable",
        until: {
          target: "answer-turn",
          status: "done",
          timeout: TOUR_LIMITS.answer,
          newItem: true,
        },
      },
      { do: "spot", target: "answer-turn", last: true },
    ],
  },
  {
    id: "ask-injection",
    route: "/ask",
    auth: "student",
    spot: { target: "ask-examples" },
    title: "A prompt-injection attempt",
    caption: "The input guard blocks it before retrieval or any model call.",
    requirement: "Security: prompt-injection guard on user input",
    actions: [
      {
        do: "click",
        target: "ask-example-injection",
        until: {
          target: "answer-turn",
          status: "done",
          timeout: TOUR_LIMITS.answer,
          newItem: true,
        },
      },
      { do: "spot", target: "answer-turn", last: true },
    ],
  },
  {
    id: "eligibility-one",
    route: "/eligibility?company=orbitpay",
    auth: "student",
    spot: { target: "eligibility-result" },
    title: "Eligibility, checked by code",
    caption: "CGPA, backlogs, branch and batch against the company's rules. This one fails on CGPA.",
    requirement: "Tool: check_eligibility (deterministic)",
  },
  {
    id: "eligibility-all",
    route: "/eligibility?view=all",
    auth: "student",
    spot: { target: "eligibility-all" },
    title: "Every company at once",
    caption: "The same rules run for all twelve companies, with the reason for each fail.",
    requirement: "Tool: check_eligibility across companies",
  },
  {
    id: "resume-match",
    route: "/resume?company=nimbusware",
    auth: "student",
    spot: { target: "resume-text" },
    title: "Resume match",
    caption: "Skills from the resume against the job, plus embedding similarity to the description.",
    requirement: "Tool: match_resume",
    actions: [
      { do: "click", target: "resume-demo" },
      {
        do: "wait",
        target: "resume-text",
        filled: true,
        timeout: TOUR_LIMITS.action,
      },
      { do: "hold", steps: 1 },
      {
        do: "click",
        target: "resume-match-button",
        until: { target: "match-result", timeout: TOUR_LIMITS.action },
      },
      { do: "spot", target: "match-result" },
    ],
  },
  {
    id: "resume-pii",
    route: "/resume?company=nimbusware",
    auth: "student",
    spot: { target: "pii-notice" },
    title: "Contact details removed",
    caption: "Phone, email and address are redacted before the text reaches any model, and never logged.",
    requirement: "Security: resume PII is redacted before the LLM",
  },
  {
    id: "agent-run",
    route: "/agent?company=nimbusware&fault=retrieve_process",
    auth: "student",
    spot: { target: "agent-start" },
    title: "Prepare me for Nimbusware",
    caption: "The agent plans, checks eligibility, matches the resume and reads the process. One search is set to fail once.",
    requirement: "Agent: multi-step plan with error recovery",
    actions: [
      { do: "hold", steps: 1 },
      { do: "click", target: "agent-start" },
      { do: "spot", target: "agent-timeline" },
      { do: "wait", target: "approval-dialog", timeout: TOUR_LIMITS.agent },
      { do: "spot", target: "approval-dialog" },
    ],
  },
  {
    id: "agent-approve",
    route: "/agent",
    auth: "student",
    spot: { target: "approval-dialog" },
    title: "Nothing is saved without approval",
    caption: "The dialog shows exactly what will be saved. Approving writes the plan and the application together.",
    requirement: "Agent: human approval before saving",
    actions: [
      { do: "hold", steps: 2 },
      {
        do: "click",
        target: "approval-approve",
        until: { target: "agent-confirmation", timeout: TOUR_LIMITS.action },
      },
      { do: "spot", target: "agent-confirmation" },
    ],
  },
  {
    id: "applications",
    route: "/applications",
    auth: "student",
    spot: { target: "applications-table" },
    title: "Application tracker",
    caption: "The approved plan added an application here. Stages and deadlines can be changed inline.",
    requirement: "Tool: track_application",
  },
  {
    id: "login-coordinator",
    route: "/login",
    exactQuery: true,
    auth: "visitor",
    spot: { target: "demo-coordinator" },
    title: "Switch to the placement cell",
    caption: "The coordinator role sees documents and analytics. Students get a 403 on those routes.",
    requirement: "Security: role checks on admin routes",
    actions: [
      { do: "hold", steps: 1 },
      { do: "click", target: "demo-coordinator" },
      { do: "path", path: "/analytics", timeout: TOUR_LIMITS.target },
    ],
  },
  {
    id: "documents-injected",
    route: "/documents",
    auth: "coordinator",
    spot: { target: "upload-demos" },
    title: "Upload a document",
    caption: "This notice hides instructions aimed at the model. They are stripped before indexing.",
    requirement: "Security: injection guard on uploaded documents",
    actions: [
      { do: "remove-upload", filename: "shuttle-timings.md" },
      { do: "hold", steps: 1 },
      {
        do: "click",
        target: "upload-demo-injected",
        until: { target: "upload-result", timeout: TOUR_LIMITS.action },
      },
      { do: "spot", target: "upload-result" },
    ],
  },
  {
    id: "documents-invalid",
    route: "/documents",
    auth: "coordinator",
    spot: { target: "upload-demos" },
    title: "A file that isn't a document",
    caption: "Type, size and file name are validated before anything is stored.",
    requirement: "Security: upload validation",
    actions: [
      {
        do: "click",
        target: "upload-demo-invalid",
        until: { target: "upload-error", timeout: TOUR_LIMITS.action },
      },
      { do: "spot", target: "upload-error" },
    ],
  },
  {
    id: "analytics-top",
    route: "/analytics",
    auth: "coordinator",
    spot: { target: "analytics-top" },
    title: "What students ask",
    caption: "The most asked questions, from the questions the demo users have asked so far.",
    requirement: "Coordinator analytics: top questions",
  },
  {
    id: "analytics-unanswered",
    route: "/analytics",
    auth: "coordinator",
    spot: { target: "analytics-unanswered" },
    title: "What the documents don't cover",
    caption: "Refused questions show the cell which documents to write next.",
    requirement: "Coordinator analytics: unanswered questions",
  },
  {
    id: "evaluation-chart",
    route: "/evaluation",
    auth: "coordinator",
    spot: { target: "eval-chart" },
    title: "Baseline against final",
    caption: "Vector-only retrieval with no guards, against the full pipeline, on the same 47 cases.",
    requirement: "Evaluation: baseline vs final",
  },
  {
    id: "evaluation-tests",
    route: "/evaluation",
    auth: "coordinator",
    spot: { target: "eval-tests" },
    title: "Tests and coverage",
    caption: "The latest pytest run, read from the saved results.",
    requirement: "Testing: test evidence and coverage",
  },
  {
    id: "security-injection",
    route: "/security",
    auth: "coordinator",
    spot: { target: "security-injection" },
    title: "Security, checked live",
    caption: "Each card sends a real request to the backend and shows what came back.",
    requirement: "Security: injection blocked (live)",
    actions: [
      {
        do: "click",
        target: "security-injection-try",
        until: {
          target: "security-injection-result",
          timeout: TOUR_LIMITS.action,
        },
      },
      { do: "spot", target: "security-injection" },
    ],
  },
  {
    id: "security-upload",
    route: "/security",
    auth: "coordinator",
    spot: { target: "security-upload" },
    title: "Oversized and wrong-type uploads",
    caption: "The backend answers 413 and 415.",
    requirement: "Security: upload limits (live)",
    actions: [
      {
        do: "click",
        target: "security-upload-try",
        until: {
          target: "security-upload-result",
          timeout: TOUR_LIMITS.action,
        },
      },
      { do: "spot", target: "security-upload" },
    ],
  },
  {
    id: "security-ratelimit",
    route: "/security",
    auth: "coordinator",
    spot: { target: "security-ratelimit" },
    title: "Rate limiting",
    caption: "Six quick requests to a limited endpoint; the sixth gets a 429.",
    requirement: "Security: rate limit (live)",
    actions: [
      {
        do: "click",
        target: "security-ratelimit-try",
        until: {
          target: "security-ratelimit-result",
          timeout: TOUR_LIMITS.action,
        },
      },
      { do: "spot", target: "security-ratelimit" },
    ],
  },
  {
    id: "security-pii",
    route: "/security",
    auth: "coordinator",
    spot: { target: "security-pii" },
    title: "PII redaction preview",
    caption: "The same redaction that runs before resume text reaches a model.",
    requirement: "Security: PII redaction (live)",
    actions: [
      {
        do: "click",
        target: "security-pii-try",
        until: { target: "security-pii-result", timeout: TOUR_LIMITS.action },
      },
      { do: "spot", target: "security-pii" },
    ],
  },
];
