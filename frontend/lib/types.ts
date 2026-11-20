// Types mirroring the FastAPI schemas (backend/app/schemas.py).

export type Role = "student" | "coordinator";

export interface Profile {
  branch: string | null;
  cgpa: number | null;
  active_backlogs: number | null;
  batch: number | null;
  has_resume: boolean;
}

export interface User {
  id: number;
  email: string;
  name: string;
  role: Role;
  profile: Profile | null;
}

export interface Company {
  id: string;
  name: string;
  role: string;
  ctc_label: string;
  category: "Regular" | "Standard" | "Dream";
  min_cgpa: number;
  max_active_backlogs: number;
  allowed_branches: string[];
  batch: number;
  required_skills: string[];
  preferred_skills: string[];
  rounds: string[];
  apply_by: string | null;
}

export interface Source {
  n: number;
  doc_key: string;
  title: string;
  doc_type: string;
  section: string;
  snippet: string;
  text?: string;
  score: number;
}

export type StepStatus = "done" | "skipped" | "blocked" | "refused" | "fallback" | "running" | "pending";

export interface PipelineStep {
  name: string;
  label: string;
  status: StepStatus;
  detail: string;
  duration_ms: number;
}

export interface Answer {
  conversation_id: number | null;
  message_id: number | null;
  question: string;
  answer: string;
  citations: number[];
  sources: Source[];
  refused: boolean;
  blocked: boolean;
  block_reasons: string[];
  provider: string;
  model: string;
  fallbacks: string[];
  steps: PipelineStep[];
  latency_ms: number;
  mode: string;
}

export interface ConversationSummary {
  id: number;
  title: string;
  updated_at: string;
  message_count: number;
}

export interface ConversationMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  meta: Partial<Answer>;
  created_at: string;
}

export interface Conversation {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
  messages: ConversationMessage[];
}

export interface Criterion {
  name: "cgpa" | "backlogs" | "branch" | "batch";
  label: string;
  passed: boolean;
  required: string;
  actual: string;
  reason: string;
}

export interface Eligibility {
  company_id: string;
  company_name: string;
  role: string;
  ctc_label: string;
  category: string;
  eligible: boolean;
  criteria: Criterion[];
  summary: string;
}

export interface EligibilityAll {
  eligible_count: number;
  total: number;
  results: Eligibility[];
}

export interface Redaction {
  counts: { email: number; phone: number; address: number; link: number };
  total: number;
  preview: string;
}

export interface ResumeMatch {
  company_id: string;
  company_name: string;
  role: string;
  match_pct: number;
  skill_score: number;
  semantic_score: number;
  matched_required: string[];
  missing_required: string[];
  matched_preferred: string[];
  missing_preferred: string[];
  extra_skills: string[];
  redaction: Redaction;
  formula: string;
  advice: string[];
}

export type ApplicationStatus = "planned" | "applied" | "online_test" | "interview" | "offer" | "rejected";

export interface Application {
  id: number;
  company_id: string;
  company_name: string;
  role_title: string;
  status: ApplicationStatus;
  deadline: string | null;
  notes: string;
  created_at: string;
  updated_at: string;
}

export type AgentStepStatus =
  | "pending"
  | "running"
  | "done"
  | "recovered"
  | "fallback"
  | "skipped"
  | "failed"
  | "waiting"
  | "approved"
  | "rejected";

export interface AgentStep {
  name: string;
  label: string;
  kind: "tool" | "retrieval" | "llm" | "gate";
  tool: string;
  required: boolean;
  description: string;
  status: AgentStepStatus;
  attempts: number;
  detail: string;
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  errors: string[];
  recovery: "retry" | "fallback" | "skip" | null;
  duration_ms: number;
}

export interface PlanWeek {
  week: number;
  focus: string;
  tasks: string[];
  guides: string[];
}

export interface PrepPlanBody {
  title: string;
  company_id: string;
  company_name: string;
  role: string;
  category: string;
  apply_by: string | null;
  weeks_count: number;
  rounds: string[];
  focus_skills: string[];
  weeks: PlanWeek[];
  tips: { text: string; source: string }[];
  summary: string;
  summary_citations: number[];
  summary_sources: { doc_key: string; title: string; section: string; snippet: string }[];
  summary_provider: string;
  done?: string[];
}

export interface AgentState {
  goal: string;
  company_id: string;
  company_name: string;
  max_steps: number;
  retries: number;
  steps: AgentStep[];
  tool_calls: number;
  outcome: string;
  message: string;
  pending: { plan: PrepPlanBody; application: Record<string, string | null> } | null;
  alternatives: { company_id: string; company_name: string; role: string; ctc_label: string; category: string }[];
  saved: { prep_plan_id: number; application_id: number; application_created: boolean } | null;
}

export interface AgentRun {
  id: number;
  company_id: string;
  goal: string;
  status: "running" | "awaiting_approval" | "approved" | "rejected" | "completed" | "failed";
  outcome: string;
  state: AgentState;
  created_at: string;
  updated_at: string;
}

export interface PrepPlan {
  id: number;
  company_id: string;
  title: string;
  plan: PrepPlanBody;
  agent_run_id: number | null;
  created_at: string;
}

export interface DocumentRow {
  id: number;
  doc_key: string;
  title: string;
  doc_type: string;
  company_id: string | null;
  source: "seed" | "upload";
  filename: string;
  size_bytes: number;
  chunk_count: number;
  removed_lines: number;
  created_at: string;
}

export interface UploadResult {
  document: DocumentRow;
  reindex: { documents: number; chunks: number; duration_ms: number };
  removed_lines: string[];
}

export interface EventRow {
  id: number;
  type: string;
  user: string | null;
  summary: string;
  created_at: string;
}

export interface Analytics {
  totals: {
    questions: number;
    answered: number;
    unanswered: number;
    blocked: number;
    answer_rate: number | null;
    active_students: number;
    eligibility_checks: number;
    resume_matches: number;
    agent_runs: number;
    plans_approved: number;
    documents_uploaded: number;
  };
  top_questions: { question: string; count: number; last_asked: string }[];
  unanswered_questions: { question: string; count: number; last_asked: string }[];
  blocked_attempts: { question: string; reasons: string[]; at: string }[];
  top_documents: { title: string; count: number }[];
  provider_usage: { provider: string; count: number; avg_latency_ms: number | null }[];
  questions_per_day: { date: string; answered: number; refused: number; blocked: number }[];
  eligibility: {
    company_id: string;
    company_name: string;
    category: string;
    eligible: number;
    total: number;
    top_blocker: string | null;
    top_blocker_count: number;
  }[];
}

export interface ProviderStatus {
  name: "gemini" | "local" | "extractive";
  model: string;
  available: boolean;
  reason: string;
  configured: boolean;
}
