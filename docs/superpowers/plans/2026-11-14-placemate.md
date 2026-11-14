# PlaceMate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build PlaceMate, a placement copilot that gives students cited answers, eligibility checks, resume matching and an approved prep plan, and gives coordinators document management and analytics.

**Architecture:** A FastAPI backend owns all logic: a fixed RAG pipeline (BM25 + FAISS, RRF, cross-encoder rerank, guarded generation), three deterministic tools, and one hand-written agent loop with persisted state and an approval gate. A Next.js frontend talks to it directly over JSON and SSE with an httpOnly session cookie. The RAG pipeline and the agent executor are both generators that yield stage events, so the same code serves the streaming UI, the JSON API, the tests and the evaluation.

**Tech Stack:** Python 3.14, FastAPI, SQLAlchemy 2 + SQLite, Pydantic 2, sentence-transformers, faiss-cpu, rank-bm25, google-genai, transformers (CPU torch), PyJWT, argon2-cffi, pytest. Next.js 16 (App Router), TypeScript, Tailwind 4, shadcn/ui, AI Elements, Motion, GSAP + ScrollTrigger, Lenis, Recharts, Playwright.

**Spec:** `CLAUDE.md`, `SHOWCASE.md`, `BUILD_PROMPT.md` (repo root). Research input: `docs/research.md`.

## Global Constraints

- CPU-only PyTorch from `https://download.pytorch.org/whl/cpu`. Never CUDA. Download no new LLM.
- Models: embeddings `sentence-transformers/all-MiniLM-L6-v2`, reranker `cross-encoder/ms-marco-MiniLM-L-6-v2`, local LLM `Qwen/Qwen2.5-0.5B-Instruct`, all from the Hugging Face cache.
- Provider order is always gemini -> local -> extractive. The app must work with no API key.
- All sample data is fictional: no real company names, no real people.
- Secrets only in `.env`. Resume PII is redacted before any LLM call and is never logged.
- Never invent a test or eval number. Every figure in docs and UI comes from a file produced by a real run.
- Palette, typography, tour behaviour and timings exactly as in `SHOWCASE.md`. No Aceternity. GSAP only on the landing page.
- All dependencies pinned to exact versions.
- Demo accounts: `student@placemate.demo / Student@123`, `coordinator@placemate.demo / Coord@123`.
- Runtime artefacts live in `backend/storage/` (ignored). Paths stay short.
- After each phase: run its checks, update `PROGRESS.md` and `docs/REQUIREMENTS_MATRIX.md`, commit, push to `main`.

## Review Focus

1. **Question is empty, whitespace or over 2,000 characters** -> 422 with a readable message, never a 500. (Task 4: `test_ask_rejects_empty_and_oversized`)
2. **Unknown company id** in eligibility, resume match or the agent -> 404 `company_not_found`; the agent run is not created. (Task 5: `test_unknown_company_is_404`)
3. **Student has no resume or an incomplete profile** -> the agent skips the optional resume step and says so; eligibility reports the missing field instead of guessing. (Task 5: `test_agent_skips_resume_when_missing`, `test_eligibility_incomplete_profile`)
4. **Every LLM provider fails or the index is missing at startup** -> the answer falls back to extractive with citations; a missing index is rebuilt, not a crash. (Task 4: `test_fallback_to_extractive`, `test_index_rebuilds_when_missing`)
5. **Approve twice, or approve another student's run** -> second approve is 409 and writes nothing; someone else's run is 404. (Task 5: `test_double_approve_conflict`, `test_cannot_approve_foreign_run`)

---

## File structure

```
backend/
  requirements.txt  requirements-dev.txt  pyproject.toml
  app/
    main.py            create_app(), lifespan (init DB, seed, load index)
    config.py          Settings, get_settings()
    db.py              engine, SessionLocal, Base, get_db()
    models.py          User, StudentProfile, Document, Conversation, Message,
                       Application, PrepPlan, AgentRun, Event
    schemas.py         all request/response models
    logging_conf.py    JSON formatter, request-id contextvar, PII-safe filter
    errors.py          AppError, register_error_handlers()
    seed.py            seed_demo_data(), reset_demo_data()
    security/
      auth.py          hash_password, verify_password, create_token, decode_token,
                       get_current_user, require_role
      rate_limit.py    RateLimiter, RateLimitMiddleware
      headers.py       SecurityHeadersMiddleware, OriginCheckMiddleware
      injection.py     scan_user_input, sanitize_document_text, filter_output
      pii.py           redact_pii
      uploads.py       validate_upload
    rag/
      loader.py        load_corpus(), parse_front_matter(), clean_text(), extract_pdf_text()
      chunker.py       chunk_document()
      models.py        get_embedder(), get_reranker() (lazy singletons)
      index.py         IndexStore (build, save, load, ensure)
      retriever.py     retrieve(), rrf_fuse()
      prompts.py       SYSTEM_PROMPT, build_prompt()
      citations.py     extract_citations(), validate_citations()
      pipeline.py      run_pipeline() generator, answer_question()
    llm/
      base.py          LLMResult, LLMProvider, ProviderError
      gemini.py  local.py  extractive.py
      router.py        generate()
    tools/
      catalog.py       Company, get_catalog()
      skills.py        SKILLS, extract_skills()
      eligibility.py   check_eligibility()
      resume.py        match_resume()
      applications.py  track_application()
    agent/
      state.py         AgentState, StepRecord, StepStatus
      planner.py       make_plan()
      steps.py         one function per step
      executor.py      run_agent() generator, approve_run(), reject_run()
      plan_builder.py  build_prep_plan()
    services/
      analytics.py     summary queries for the coordinator
      events.py        log_event()
    api/
      auth.py  ask.py  tools.py  agent.py  applications.py  admin.py  meta.py
  data/                sample corpus (Task 2)
  tests/               conftest.py + one file per area
eval/
  cases.json  run_eval.py  metrics.py  charts.py  results/
frontend/
  app/                 layout, landing, login, (app)/..., error pages
  components/          ui/ (shadcn), ai-elements/, shell/, landing/, tour/, shared/
  lib/                 api.ts, sse.ts, auth.tsx, speed.ts, tour-script.ts, types.ts
  proxy.ts  e2e/  playwright.config.ts
scripts/               dev.ps1, setup.ps1, test.ps1, eval.ps1, reset-demo.ps1
```

---

### Task 2: Sample data

**Files:** `backend/data/placement_policy.md`, `backend/data/companies/*.md` (12), `backend/data/interviews/*.md` (15), `backend/data/guides/*.md` (6), `backend/data/students_seed.json`, `backend/data/resumes/*.txt`, `backend/data/README.md`.

**Produces:** every company file starts with YAML front matter that the tools read:

```yaml
---
id: nimbusware            # slug, unique
name: Nimbusware Technologies
doc_type: company         # company | interview | guide | policy
role: Software Engineer Trainee
ctc_lpa: [6.5, 8.0]
min_cgpa: 7.0
max_active_backlogs: 0
allowed_branches: [CSE, IT, ECE]
batch: 2027
required_skills: [python, sql, data structures]
preferred_skills: [django, git]
rounds: [Online Assessment, Technical Interview, HR Interview]
apply_by: 2026-12-05
---
```

Interview and guide files carry `doc_type`, `title` and (for interviews) `company_id`.

- [ ] Write the policy, companies, interviews, guides, students and resumes. Indian campus context, invented names only. Resumes include a phone, an email and an address so redaction has something to remove.
- [ ] Spread criteria so the demo student is eligible for some companies and fails others on each of CGPA, backlogs, branch and batch.
- [ ] Include one document with an embedded instruction line for the injection tests, clearly marked as a test fixture.
- [ ] Commit and push.

### Task 3: Backend core

**Files:** `app/main.py`, `config.py`, `db.py`, `models.py`, `schemas.py`, `logging_conf.py`, `errors.py`, `seed.py`, `security/auth.py`, `security/rate_limit.py`, `security/headers.py`, `api/auth.py`, `api/meta.py`, `tests/conftest.py`, `tests/test_auth.py`, `tests/test_security_http.py`.

**Produces:**
- `get_settings() -> Settings` with fields matching `.env.example`.
- `get_db() -> Iterator[Session]`.
- `get_current_user(request, db) -> User`; `require_role(*roles) -> Depends`.
- Session cookie `pm_session`: JWT HS256, `httponly`, `samesite=lax`, `secure` from `COOKIE_SECURE`, claims `sub`, `role`, `exp`.
- Error envelope for every non-2xx: `{"error": {"code": str, "message": str, "request_id": str, "details"?: list}}`.
- Routes: `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`, `GET /health`, `GET /api/meta/companies`.
- `Event(type, user_id, payload_json, created_at)` and `log_event(db, type, user_id, **payload)` for analytics and the audit log.

- [ ] Tests first: login success sets the cookie; wrong password is 401 with the same message as unknown email; `/api/auth/me` without cookie is 401; student on a coordinator route is 403; 11th login attempt in a minute is 429 with `Retry-After`; responses carry `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Content-Security-Policy`; CORS allows only `FRONTEND_ORIGIN`; an unhandled exception returns the envelope with no traceback; unsafe methods with a foreign `Origin` are 403.
- [ ] Implement. Passwords use argon2id. Rate limiter is an in-memory sliding window keyed by client IP and route class (`auth` 10/min, `default` 60/min, both from settings).
- [ ] Run the server, open `/docs` and `/health`. Commit and push.

### Task 4: RAG

**Files:** everything under `app/rag/`, `app/llm/`, `security/injection.py`, `api/ask.py`, `tests/test_rag.py`, `tests/test_llm.py`, `tests/test_injection.py`, `tests/test_ask_api.py`.

**Produces:**
- `Chunk(id, doc_id, title, doc_type, company_id, section, text)`.
- `IndexStore.ensure(db) -> IndexStore` (load from `storage/index/`, rebuild if missing or stale); `IndexStore.build(db)`.
- `retrieve(query, *, mode: Literal["baseline","final"], top_k=5, company_id=None, doc_types=None) -> RetrievalResult` with `candidates`, `results: list[ScoredChunk]`, `timings`. `baseline` = vector only, no rerank. `final` = BM25 top 20 + vector top 20, RRF k=60, cross-encoder rerank to `top_k`.
- `generate(system, prompt, *, sources, max_tokens) -> LLMResult(text, provider, model, fallbacks: list[str])`.
- `run_pipeline(question, *, mode, user_id) -> Iterator[PipelineEvent]` yielding `guard`, `retrieved`, `reranked`, `delta`, `final`. `answer_question(...) -> AnswerResult(answer, citations, sources, refused, blocked, provider, model, steps, latency_ms)`.
- `scan_user_input(text) -> GuardResult(blocked, reasons)`; `sanitize_document_text(text) -> (clean_text, removed_lines)`; `filter_output(text, n_sources) -> text`.
- Routes: `POST /api/ask` (JSON), `POST /api/ask/stream` (SSE), `GET /api/conversations`, `GET /api/conversations/{id}`.
- Refusal text is one constant, `REFUSAL_MESSAGE`, used by the pipeline, tests and eval.

- [ ] Tests first: chunker keeps heading context and respects size limits; a CGPA-policy question returns the policy document in the top 3; a company-round question returns that company's file first; an off-topic question is refused and makes no LLM call; an injection attempt is blocked before retrieval; an instruction line inside a document is removed at ingest; citations outside `1..n` are stripped; with gemini and local both failing the answer comes from extractive and still has citations; a missing index directory is rebuilt; Review Focus 1 and 4.
- [ ] Implement. Chunk by markdown heading, about 180 words with 30 overlap, heading path prefixed to the chunk text. Refusal when the top reranker score is below a threshold stored in settings and tuned on the eval set (baseline uses a cosine threshold).
- [ ] Manual check with 5 questions, recorded in `PROGRESS.md`. Commit and push.

### Task 5: Tools, agent, coordinator

**Files:** `app/tools/*`, `app/agent/*`, `security/pii.py`, `security/uploads.py`, `services/analytics.py`, `api/tools.py`, `api/agent.py`, `api/applications.py`, `api/admin.py`, tests `test_eligibility.py`, `test_resume.py`, `test_pii.py`, `test_applications.py`, `test_agent.py`, `test_admin.py`.

**Produces:**
- `check_eligibility(profile: StudentProfileData, company: Company) -> EligibilityResult(eligible, criteria: list[Criterion(name, passed, required, actual, reason)])` for `cgpa`, `backlogs`, `branch`, `batch`.
- `redact_pii(text) -> RedactionResult(text, counts: {"email": n, "phone": n, "address": n})`.
- `match_resume(resume_text, company) -> ResumeMatch(match_pct, skill_score, semantic_score, matched_required, missing_required, matched_preferred, missing_preferred, redaction)`. `match_pct = round(100 * (0.6 * skill_score + 0.4 * semantic_score))`, `skill_score = 0.75 * required_coverage + 0.25 * preferred_coverage`.
- `track_application(db, user_id, company_id, *, status=None, deadline=None, notes=None) -> Application` (upsert on user + company; statuses `planned, applied, online_test, interview, offer, rejected`).
- `run_agent(db, user, company_id, *, demo_fault: str | None = None) -> Iterator[AgentEvent]`; `approve_run(db, user, run_id)`, `reject_run(db, user, run_id)`.
- Agent steps: `check_eligibility` (required), `match_resume` (optional, skipped without a resume), `retrieve_process` (required, falls back to the company file itself), `retrieve_experiences` (optional), `build_plan` (required, falls back to a template plan when the LLM fails), then `awaiting_approval`. `MAX_STEPS = 8`, 2 retries per step. An ineligible student gets the failed criteria and up to 3 eligible alternatives; nothing is offered for saving.
- Routes: `POST /api/tools/eligibility`, `POST /api/tools/eligibility/all`, `POST /api/tools/resume-match`, `POST /api/agent/runs` (SSE or JSON), `GET /api/agent/runs/{id}`, `POST /api/agent/runs/{id}/approve|reject`, `GET|POST|PATCH /api/applications`, `GET /api/prep-plans`, `POST /api/admin/documents`, `GET /api/admin/documents`, `DELETE /api/admin/documents/{id}`, `POST /api/admin/reindex`, `GET /api/admin/analytics`, `GET /api/admin/logs`.
- Upload rules: `.md`, `.txt`, `.pdf` only; size <= `MAX_UPLOAD_MB`; PDF must start with `%PDF-`; text must decode as UTF-8; filename reduced to `[a-z0-9._-]`; text passes through `sanitize_document_text`.

- [ ] Tests first: eligibility boundary cases (CGPA exactly at the cut-off passes, one backlog over fails, branch case-insensitive, wrong batch, missing profile field); resume match finds known skills and reports missing ones; the text given to the embedder contains no email, phone or address; agent happy path ends `awaiting_approval` and has written no Application or PrepPlan; approve writes both; reject writes neither; a step that fails once is retried and marked recovered; an optional step that keeps failing is skipped; a required step falls back; max steps is enforced; every admin route is 403 for a student and 401 anonymous; bad uploads are rejected with a specific code; Review Focus 2, 3 and 5.
- [ ] Implement. Commit and push.

### Task 6: Tests and evaluation

**Files:** `eval/cases.json`, `eval/run_eval.py`, `eval/metrics.py`, `eval/charts.py`, `scripts/test.ps1`, `scripts/eval.ps1`, `docs/evaluation.md`, `docs/test-evidence.md`.

**Produces:** `eval/results/summary.json` (also copied to `frontend/public/eval-summary.json`) with `{generated_at, provider_counts, baseline: {...}, final: {...}, per_category, tests: {passed, failed, coverage_pct}}`; `eval/results/cases_baseline.json`, `cases_final.json`; charts `retrieval.png`, `safety.png`, `latency.png`.

- [ ] About 40 cases across: answerable (policy, company, guide), hallucination traps (not in documents), ambiguous, injection, agent success, agent tool failure. Each case names the expected source document where one exists.
- [ ] Metrics: Hit@3, MRR, groundedness (share of answer sentences supported by a cited chunk), citation accuracy, refusal accuracy, injection block rate, agent task success, latency p50/p95, provider counts.
- [ ] Run `pytest --cov=app`, then the eval in `baseline` and `final` modes. Write both docs from the output files only. Commit and push.

### Task 7: Frontend app

**Files:** `frontend/` scaffold, `app/(app)/*` pages in `SHOWCASE.md` order, `components/shell/*`, `lib/api.ts`, `lib/sse.ts`, `lib/auth.tsx`, `lib/speed.ts`, `proxy.ts`, error pages.

**Produces:** `api<T>(path, init) -> Promise<T>` that throws `ApiError(status, code, message)` and routes 401/403/429 to their pages; `streamSSE(path, body, onEvent)`; `useAuth()`; `SPEED` config with `slow | medium | fast` and the timings from `SHOWCASE.md`; `data-tour="..."` attributes on every element the tour targets.

- [ ] Hallmark study. `create-next-app`, `shadcn init`, shadcn MCP, AI Elements components, theme tokens.
- [ ] Shell, login with demo buttons, role-protected routes.
- [ ] Pages: Dashboard, Ask, Eligibility, Resume Match, Prep Agent, Applications, Documents, Analytics, Evaluation, Security. Each with example inputs, skeletons, empty and error states, toasts.
- [ ] Hallmark audit after each page. `npm run build` and `tsc` clean. Commit and push every 2-3 pages.

### Task 8: Landing and Guided Tour

**Files:** `app/page.tsx`, `components/landing/*`, `components/tour/*`, `lib/tour-script.ts`.

- [ ] Six landing sections with GSAP + ScrollTrigger + Lenis; reduced motion disables pinning and smooth scroll. Copy through Humanizer.
- [ ] Tour: manual by default, fixed bottom-centre bar, spotlight, captions that never cover the bar or the target, keyboard control, state kept across navigation, one script covering every step listed in `SHOWCASE.md`. Commit and push.

### Task 9: Verify

- [ ] Playwright smoke tests (login, ask, eligibility, prep agent with approval) and screenshots of every page at desktop and mobile width into `screenshots/`.
- [ ] Hallmark and Web Design Guidelines audits; fix findings.
- [ ] Full tour in manual, auto and paused modes with no console or server errors.
- [ ] verification-before-completion against every `CLAUDE.md` requirement. Commit and push.

### Task 10: Docs and finish

- [ ] `README.md`, `SECURITY.md`, `docs/api.md`, `docs/CODE_MAP.md`, final `docs/REQUIREMENTS_MATRIX.md`.
- [ ] Fresh-clone check in a temp folder following the README; confirm no needed file is ignored; reset demo data.
- [ ] Final commit and push; summary.
