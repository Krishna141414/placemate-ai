# Code map

A guide to the code for explaining it on video. Part 1 follows one request from the browser to the database. Part 2 goes folder by folder. Part 3 walks through each flow. Part 4 suggests an order for the recording.

File paths are from the repository root. Function names are given so you can jump to them with Ctrl+Click or a search.

---

## Part 1. How a request travels

Take "Ask a question" as the example, because it touches every layer.

```
Browser (Next.js page)
  frontend/app/(app)/ask/ask-view.tsx          ask() → streamSSE("/api/ask/stream", …)
  frontend/lib/api.ts                          fetch with credentials (the httpOnly cookie goes along)
        │  HTTPS JSON in, server-sent events out
        ▼
FastAPI edge  backend/app/main.py               create_app(): middleware + routers
  CORS (one allowed origin)
  SecurityHeadersMiddleware                     headers on every response
  RequestContextMiddleware                      request id, one JSON log line per request
  OriginCheckMiddleware                         refuses cross-site POST/PATCH/DELETE
  RateLimitMiddleware                           10 / 5 / 120 per minute
        ▼
Route  backend/app/api/ask.py                   ask_stream(body: AskRequest, user = Depends(get_current_user))
  Pydantic validates the body (backend/app/schemas.py)
  get_current_user reads the cookie, checks the JWT, loads the user (backend/app/security/auth.py)
        ▼
Service  backend/app/rag/pipeline.py            run_pipeline(question) yields steps as they finish
  input guard → hybrid retrieval → rerank → grounding check → generate → output guard
  retrieval:  backend/app/rag/retriever.py, index.py (FAISS + BM25), models.py (embedder, reranker)
  generation: backend/app/llm/router.py → gemini.py → local.py → extractive.py
        ▼
Database  backend/app/models.py, db.py          Conversation + Message rows; an Event row for analytics
        ▼
Back to the browser as events: step, sources, delta, final
  ask-view.tsx paces them with lib/speed.ts and renders AnswerText, PipelinePanel, SourceCards
```

The other features follow the same path with a different middle:

- **Eligibility and resume match:** `api/tools.py` → `tools/eligibility.py` or `tools/resume.py` (plain Python, no LLM for the decision).
- **Prep agent:** `api/agent.py` → `agent/executor.py`, which calls the tools and the RAG retriever step by step and saves its state to the `agent_runs` table after each one.
- **Coordinator pages:** `api/admin.py` → `services/analytics.py`, `rag/loader.py`, `rag/index.py`.

---

## Part 2. Folder by folder

### Root

| File | Job |
|---|---|
| `README.md` | What the project is, how to run it, results |
| `SECURITY.md` | Every protection with its file and test |
| `PROGRESS.md` | Phase-by-phase log of what was built and checked |
| `package.json` | Root shortcuts: `npm run setup`, `dev:all`, `reset-demo`, `test:backend`, `test:e2e`, `eval` |
| `.env.example` | Every setting, documented. Copy to `.env` |
| `scripts/` | `setup.ps1` (install), `dev.ps1` (run both servers), `reset-demo.ps1`, `test.ps1` (pytest + coverage evidence), `eval.ps1` (evaluation) |

### `backend/app/` (FastAPI)

**Entry and plumbing**

| File | Job | Main names |
|---|---|---|
| `main.py` | Builds the app: middleware order, routers, error handlers. On startup creates tables, seeds the demo data if empty, builds or loads the search index and warms the reranker | `create_app`, `lifespan` |
| `config.py` | All settings from `.env` and the environment, with defaults | `Settings`, `get_settings` |
| `db.py` | SQLite engine and sessions | `init_db`, `get_db` |
| `models.py` | Tables: users, student profiles, documents, conversations, messages, applications, prep plans, agent runs, events. `UTCDateTime` keeps timestamps in UTC | `User`, `Document`, `AgentRun`, `Event` |
| `schemas.py` | Every request and response shape. `StrictModel` rejects unknown fields | `AskRequest`, `AnswerOut`, `EligibilityOut` |
| `errors.py` | One error envelope; no stack traces to clients | `AppError`, `register_error_handlers` |
| `logging_conf.py` | JSON log lines with a request id; masks emails and phones | `JsonFormatter`, `PiiScrubFilter` |
| `seed.py` | Demo users, profiles, applications; `--reset` restores the clean state | `seed_demo_data`, `reset_demo_data` |

**`api/`: the HTTP routes.** Each file is thin: validate, check the user, call a service, shape the response.

| File | Routes |
|---|---|
| `auth.py` | login, logout, session, me, profile |
| `ask.py` | ask, ask/stream (SSE), conversations |
| `tools.py` | eligibility (one / all), resume-match, own resume, resume-extract |
| `agent.py` | start a run (JSON or SSE), list, get, approve, reject |
| `applications.py` | tracker CRUD, prep plans, plan progress |
| `admin.py` | documents (list, upload, delete), reindex, analytics, logs. The router itself requires the coordinator |
| `meta.py` | health, companies, providers, ping (rate-limit demo), redact-preview |

**`rag/`: retrieval-augmented generation**

| File | Job | Main names |
|---|---|---|
| `loader.py` | Reads Markdown / text / PDF, YAML front matter, cleans text, and runs the document injection guard on every file | `load_seed_documents`, `build_source_doc` |
| `chunker.py` | Splits by headings into chunks of about 180 words, keeping the heading with the text | `chunk_document` |
| `models.py` | Loads `all-MiniLM-L6-v2` and the `ms-marco` cross-encoder once | `embed`, `rerank_scores` |
| `index.py` | FAISS inner-product index plus BM25, saved to `backend/storage/index/` with a fingerprint of the corpus | `IndexStore.build`, `get_index` |
| `retriever.py` | 20 from BM25 + 20 from vectors, fused with Reciprocal Rank Fusion (k=60), then reranked to the top 5 | `retrieve`, `rrf_fuse` |
| `prompts.py` | The system prompt (with a canary) and numbered passages inside delimiters | `build_prompt` |
| `pipeline.py` | The whole answer: guard, retrieve, rerank, refuse if the best score is below 0 or the question names something the documents never mention, generate, filter. Also the "baseline" mode used by the evaluation | `run_pipeline`, `answer_question`, `unknown_terms` |

**`llm/`: model providers**

| File | Job |
|---|---|
| `base.py` | Shared types: `LLMRequest`, `LLMResult`, `ProviderError` |
| `gemini.py` | Gemini through `google-genai` (`gemini-3.5-flash-lite` by default) |
| `local.py` | Qwen2.5-0.5B-Instruct from the Hugging Face cache, on CPU |
| `extractive.py` | No model: picks the source sentences that best answer the question, with citations |
| `router.py` | Tries the configured provider, then the next, and records which one answered and why it fell back | 

**`tools/`: deterministic tools the LLM must not guess**

| File | Job | Main names |
|---|---|---|
| `catalog.py` | The 12 fictional companies from `backend/data/companies/*.md` front matter | `get_catalog` |
| `eligibility.py` | CGPA, active backlogs, branch and batch against a company's criteria, with a reason per criterion | `check_eligibility`, `check_all` |
| `skills.py` | Skill vocabulary with aliases; careful matching (for example "communication" inside "Electronics and Communication" is not a skill) | `extract_skills` |
| `resume.py` | Redacts PII first, then skill score (75% required skills found + 25% preferred) and semantic score (MiniLM similarity between resume sections and the job description, mapped from 0.15 to 0.60 onto 0 to 1) → match % = 60% skill + 40% semantic, plus advice | `match_resume` |
| `applications.py` | Create or update one application per company | `track_application` |

**`agent/`: the prep agent (only for "Prepare me for &lt;company&gt;")**

| File | Job | Main names |
|---|---|---|
| `planner.py` | The fixed plan: eligibility → resume match → selection process → interview experiences → draft plan → approval | `make_plan` |
| `steps.py` | One function per step and fallbacks for required steps (process falls back to the company's listed rounds; the plan summary falls back to a template) | `step_*`, `fallback_*` |
| `state.py` | What is saved after each step: steps, attempts, tool calls used, recoveries | `AgentState`, `StepRecord` |
| `plan_builder.py` | Turns missing skills, rounds and weeks left into a week-by-week plan | `build_prep_plan` |
| `executor.py` | Runs the steps with a budget of 8 tool calls and 2 retries per step, skips optional steps that fail, stops for approval, and saves plan + application in one transaction on approve | `execute_run`, `approve_run`, `reject_run` |

**`security/`**: `auth.py` (argon2id, JWT cookie, role checks), `headers.py` (headers, request id, origin check), `rate_limit.py`, `injection.py` (input guard, document guard, output filter), `pii.py`, `uploads.py`. See `SECURITY.md`.

**`services/`**: `events.py` writes the append-only event log; `analytics.py` turns it into the coordinator's numbers and readable log rows.

### `backend/data/` (sample data, all fictional)

`placement_policy.md`, `companies/` (12 profiles with criteria in front matter), `interviews/` (15 write-ups), `guides/` (6 prep guides), `students_seed.json`, `resumes/` (3 demo resumes), `fixtures/injected_notice.md` (a notice with planted instructions for the injection tests).

### `backend/tests/`

One file per area: `test_auth`, `test_security_http`, `test_injection`, `test_pii`, `test_rag`, `test_llm`, `test_eligibility`, `test_resume`, `test_applications`, `test_agent`, `test_admin`, `test_ask_api`, `test_timestamps`. `conftest.py` forces the extractive provider and uses a temporary database and index, so tests never call Gemini.

### `eval/`

| File | Job |
|---|---|
| `cases.json` | 47 cases: answerable, hallucination traps, injection, ambiguous, agent tasks |
| `run_eval.py` | Runs every case in baseline mode (vector only, no guards) and final mode, saving answers and timings |
| `metrics.py` | Hit@3, MRR, answer quality, groundedness, citation accuracy, refusal accuracy, injection block rate, agent task success, latency |
| `charts.py` | PNG charts per provider |
| `publish.py` | Merges runs and test results into `eval/results/summary.json` and `frontend/public/eval-summary.json` |
| `report.py` | Writes the tables in `docs/evaluation.md` and `docs/test-evidence.md` from those files |
| `collect_tests.py`, `regrade.py` | Test summary for the docs; re-grading saved answers when a metric changes |

### `frontend/` (Next.js App Router)

**Pages** (`app/`): each route has a small `page.tsx` (title) and a `*-view.tsx` (the client component).

| Route | View | Shows |
|---|---|---|
| `/` | `components/landing/landing-page.tsx` | Scroll story: hero, problem, pinned walkthrough, pipeline, results, stack |
| `/login` | `app/login/login-form.tsx` | Email login and the two demo buttons |
| `/dashboard` | `dashboard-view.tsx` | Eligible companies, deadlines, recent questions, plan progress |
| `/ask` | `ask-view.tsx` | Chat with example chips, citations, sources, "How this was answered" |
| `/eligibility` | `eligibility-view.tsx` | One company (criteria with reasons) or all companies |
| `/resume` | `resume-view.tsx` | Resume input, match ring, skills, PII notice |
| `/agent` | `agent-view.tsx` | Agent timeline, run state, approval dialog |
| `/applications` | `applications-view.tsx` | Tracker table with inline status change |
| `/documents` | `documents-view.tsx` | Coordinator uploads with demo files, document table |
| `/analytics` | `analytics-view.tsx` | Charts and tables from `/api/admin/analytics` |
| `/evaluation` | `evaluation-view.tsx` | Baseline vs final from `/eval-summary.json`, tests and coverage |
| `/security` | `security-view.tsx` | One card per protection with a live "Try it" |
| errors | `not-found.tsx`, `forbidden/`, `too-many-requests/`, `error.tsx` | Friendly status pages |

`app/(app)/layout.tsx` wraps the signed-in pages in `components/shell/app-shell.tsx` (sidebar by role, top bar, login redirect, 403 / 429 / offline states). `proxy.ts` sends visitors without a cookie to `/login` before rendering.

**Components**

| Folder | Job |
|---|---|
| `components/ask/` | `answer-text.tsx` (citation chips, lists), `source-cards.tsx`, `pipeline-panel.tsx` |
| `components/agent/` | `step-card.tsx` (one tool step, raw output collapsed), `plan-preview.tsx` |
| `components/shared/` | `page.tsx` (headers, sections, empty / error / loading states), `badges.tsx`, `count-up.tsx`, `company-select.tsx`, `status-view.tsx` |
| `components/landing/` | Landing page, hero answer card, Lenis smooth scroll, `landing.css` |
| `components/tour/` | Guided tour: `tour-store.ts` (state in sessionStorage), `tour-provider.tsx` (runs steps), `tour-bar.tsx`, `tour-spotlight.tsx`, `tour-dom.ts` |
| `components/ai-elements/` | Vercel AI Elements (conversation, message, prompt input, sources, inline citation, chain of thought, tool, confirmation, code block) |
| `components/ui/` | shadcn/ui primitives |

**Library** (`lib/`): `api.ts` (fetch + SSE client, `ApiError`), `auth.tsx` (session state, demo accounts), `speed.ts` (every timing, Slow / Medium / Fast), `tour-script.ts` (the 30 tour steps), `types.ts` (mirrors the backend schemas), `use-api.ts`, `format.ts`, `nav.ts`, `companies.ts`, `eval-summary.ts`.

**Tests** (`e2e/`): `smoke.spec.ts` (18 flows), `tour.spec.ts` (whole tour in Auto mode), `screenshots.spec.ts`, `auth.setup.ts`.

---

## Part 3. Each flow, step by step

### Ask a question

1. `ask-view.tsx` `ask()` adds a "streaming" turn and calls `streamSSE("/api/ask/stream")`.
2. Edge middleware runs (Part 1); `ask_stream` validates `AskRequest` and loads the user.
3. `run_pipeline`:
   1. **Input guard** `scan_user_input`: a blocked question stops here with a reason.
   2. **Hybrid retrieval** `retrieve`: BM25 and FAISS each return 20; RRF fuses them.
   3. Retrieved passages that contain instructions are dropped.
   4. **Rerank**: the cross-encoder scores the candidates; the top 5 are kept.
   5. **Grounding check**: refuse if the best score is below 0, or if the question names a company or term that appears nowhere in the documents (`unknown_terms`).
   6. **Generate**: `llm/router.generate` tries Gemini, then the local model, then extractive. Answers that are too short or echo the prompt count as failures and fall through.
   7. **Output guard** `filter_output`: canary check, citation numbers checked against the passages, unknown links removed.
4. Each step is sent as an SSE `step` event; then `sources`, the text, and `final`.
5. The conversation, message and an `ask` / `ask_refused` / `ask_blocked` event are saved.
6. The page reveals steps at the pace in `lib/speed.ts`, renders `[n]` as citation chips and shows the provider badge.

### Eligibility check

1. `eligibility-view.tsx` reads `?company=` from the URL and posts `{company_id}`.
2. `api/tools.py` `eligibility` loads the student's profile and the company from `tools/catalog.py`.
3. `check_eligibility` compares CGPA, active backlogs, branch and batch; each criterion gets pass/fail, required and actual values, and a sentence.
4. The page animates the criteria in. "Check all" calls `/eligibility/all` (`check_all`).

### Resume match

1. `resume-view.tsx`: the student loads the saved resume, uploads a file (`/resume-extract`) or pastes text, picks a company and presses Match.
2. `match_resume` runs `redact_pii` first; everything after sees only the redacted text.
3. `extract_skills` finds skills; coverage of required and preferred skills is computed.
4. `semantic_similarity` embeds the redacted resume and the job description.
5. Match % = 60% skill score (75% required + 25% preferred) + 40% semantic score; missing skills come with advice pointing to a prep guide.
6. The page shows the ring, chips, formula and "what the model saw" (counts of removed details).

### Prep agent with approval

1. `agent-view.tsx` posts `{company_id, demo_fault?}` to `/api/agent/runs/stream`.
2. `start_run` creates the `AgentRun` row; `make_plan` gives the step list.
3. `execute_run` runs each step from `agent/steps.py`, counting tool calls against the budget of 8:
   - check eligibility (required; if not eligible, the run ends with alternatives),
   - match resume (optional: skipped on failure),
   - retrieve the selection process (required: retried, then falls back to the company's listed rounds),
   - retrieve interview experiences (optional),
   - draft the plan (required: Gemini summary with citations, falling back to a template).
4. After every step the state is saved, and a `step` event goes to the page.
5. The run stops with `approval_required`; the page opens the dialog showing exactly what will be saved.
6. Approve → `approve_run` writes the `PrepPlan` and the `Application` in one transaction. Reject → nothing is written. A second decision returns 409.

### Upload and re-index (coordinator)

1. `documents-view.tsx` sends the file (or a demo file) as multipart to `POST /api/admin/documents`.
2. `read_limited` stops reading past 5 MB (413); `validate_bytes` checks the extension, content signature and text (415 / 422); `sanitize_filename` cleans the name.
3. A SHA-256 duplicate is refused (409).
4. The file is stored under `backend/storage/uploads/` with a random prefix; `build_source_doc` extracts text and runs `sanitize_document_text`, which strips instruction-like lines.
5. A `Document` row is added and `IndexStore.build` rebuilds the index; the new document is searchable straight away.
6. The page shows the stages, the removed lines struck through, and the updated table.

### Authentication

1. `login-form.tsx` → `useAuth().login` → `POST /api/auth/login`.
2. `authenticate` verifies the argon2id hash (or a dummy hash for unknown emails, so timing does not leak which emails exist).
3. `create_token` signs a JWT; `set_session_cookie` sets it httpOnly.
4. `AuthProvider` stores the user; `homeFor` sends students to `/dashboard` and coordinators to `/analytics`.
5. On later requests `get_current_user` decodes the cookie and loads the user and role from the database. `require_student` / `require_coordinator` guard the routes.
6. On page load, `AuthProvider` calls `/api/auth/session` (200 with `user: null` for visitors). `AppShell` redirects visitors to `/login?next=…` and shows 403 for the wrong role.

### Evaluation run

1. `scripts/eval.ps1` runs `eval/run_eval.py --provider gemini` and `--provider extractive`.
2. Each of the 47 cases runs in **baseline** (vector-only retrieval, no guards, no refusal, naive agent) and **final** mode, using a separate database and index in `eval/.work/`.
3. `metrics.py` grades retrieval (Hit@3, MRR), answers (key facts, groundedness against the passages, citation accuracy), refusals, injection blocks, the agent tasks and latency.
4. `charts.py` draws the PNGs; `publish.py` writes `summary.json` and `frontend/public/eval-summary.json`.
5. `report.py` writes the tables into `docs/evaluation.md` and `docs/test-evidence.md`. The Evaluation page and the landing page read the same JSON, so no number is typed by hand.

### Guided tour

1. "Start tour" calls `startTour()` in `tour-store.ts`; the state goes to sessionStorage.
2. `TourProvider` runs the current step from `lib/tour-script.ts`: log in as the right demo user if needed, navigate, spotlight the `data-tour` target, then (moving forward only) perform the actions: click an example, wait for the answer, run the agent, approve.
3. Manual mode waits for Next or →; Auto waits `tourStep` from `lib/speed.ts`. Space pauses everything, including a running action.

---

## Part 4. Suggested order for the video

1. **The problem and the demo (3 min).** Landing page, then log in as the student. Ask the policy question, then the hostel-fee question (refused) and the injection (blocked).
2. **Architecture (2 min).** `docs/architecture-diagram.png`, then Part 1 of this file: browser → edge → route → service → database.
3. **RAG (4 min).** `rag/pipeline.py` `run_pipeline` top to bottom, opening `retriever.py` (RRF) and `llm/router.py` (fallback) on the way. Show "How this was answered" in the app next to the code.
4. **Tools (3 min).** `tools/eligibility.py` (why the LLM must not decide eligibility), then `tools/resume.py` with `security/pii.py`. Show the redaction notice in the app.
5. **Agent (4 min).** `agent/planner.py`, `steps.py`, `executor.py`: budget, retries, fallbacks, state saved per step, approval. Run it with "Process search fails once" and approve.
6. **Coordinator side (2 min).** Upload the notice with planted instructions; open `security/injection.py` `sanitize_document_text`. Then analytics.
7. **Security (2 min).** `SECURITY.md` table, then the Security page "Try it" buttons.
8. **Evaluation and tests (3 min).** `eval/cases.json`, `metrics.py`, the Evaluation page (baseline vs final), `scripts/test.ps1` output and coverage, the Playwright smoke run.
9. **Frontend and tour (1 min).** `lib/tour-script.ts`, `lib/speed.ts`; start the tour.
10. **Close (1 min).** Limits and future work from the README.
