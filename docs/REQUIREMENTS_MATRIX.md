# Requirements matrix

Every item in the official brief and in `CLAUDE.md`, where it is implemented, what proves it, and its status. Updated at the end of every phase.

Status values: `planned`, `in progress`, `done`. Last updated: Phase 2 (2026-11-14).

## A. Official brief

| # | Brief item | Implemented in | Proof | Status |
|---|---|---|---|---|
| A1 | Identify a meaningful problem | `docs/requirements.md` section 1 | Document | done |
| A2 | Prepare requirements | `docs/requirements.md` | Document | done |
| A3 | Prepare architecture | `docs/architecture.md`, `docs/architecture-diagram.*` | Document + diagram | done |
| A4 | Suitable AI components, not every technique | `docs/architecture.md` section 3 | Justification + "not used" table | done |
| A5 | RAG | `backend/app/rag/` | `tests/test_rag.py`, eval Hit@3 / MRR | planned |
| A6 | Tools | `backend/app/tools/` | `tests/test_eligibility.py`, `test_resume.py`, `test_applications.py` | planned |
| A7 | Agent | `backend/app/agent/` | `tests/test_agent.py`, eval agent task success | planned |
| A8 | Evaluation | `eval/` | `eval/results/`, `docs/evaluation.md` | planned |
| A9 | Testing | `backend/tests/`, `frontend/e2e/` | `docs/test-evidence.md` | planned |
| A10 | Security considerations | `backend/app/security/` | `SECURITY.md`, security tests | planned |
| A11 | Usable application interface | `frontend/` | `screenshots/`, Playwright smoke test | planned |
| A12 | Submit code | Repository | GitHub `main` | in progress |
| A13 | Submit README | `README.md` | Document | planned |
| A14 | Submit architecture | `docs/architecture.md` | Document | done |
| A15 | Submit test evidence | `docs/test-evidence.md` | Document | planned |
| A16 | Submit screenshots | `screenshots/` | Files | planned |
| A17 | Submit documentation | `docs/` | Files | in progress |

## B. Users and features

| # | Requirement | Implemented in | Proof | Status |
|---|---|---|---|---|
| B1 | Student asks placement questions | `app/api/ask.py`, `frontend/app/(app)/ask` | `tests/test_ask_api.py`, smoke test | planned |
| B2 | Student checks eligibility | `app/tools/eligibility.py`, eligibility page | `tests/test_eligibility.py` | planned |
| B3 | Student matches resume to a job | `app/tools/resume.py`, resume page | `tests/test_resume.py` | planned |
| B4 | Student gets a prep plan | `app/agent/`, prep page | `tests/test_agent.py` | planned |
| B5 | Student tracks applications | `app/tools/applications.py`, applications page | `tests/test_applications.py` | planned |
| B6 | Coordinator uploads / updates documents | `app/api/admin.py`, documents page | `tests/test_admin.py` | planned |
| B7 | Coordinator analytics: top questions, unanswered, eligibility stats | `app/services/analytics.py`, analytics page | `tests/test_admin.py` | planned |
| B8 | Coordinator views logs | `app/api/admin.py` (`/api/admin/logs`) | `tests/test_admin.py` | planned |

## C. AI components

| # | Requirement | Implemented in | Proof | Status |
|---|---|---|---|---|
| C1 | Hybrid retrieval: BM25 + vector with RRF | `app/rag/retriever.py` | `tests/test_rag.py`; eval baseline vs final | planned |
| C2 | Cross-encoder reranking | `app/rag/retriever.py` | `tests/test_rag.py` | planned |
| C3 | Grounded generation with numbered citations | `app/rag/pipeline.py`, `citations.py` | eval groundedness, citation accuracy | planned |
| C4 | Refuse when not in documents | `app/rag/pipeline.py` | `test_rag.py::refusal`, eval refusal accuracy | planned |
| C5 | `check_eligibility` (CGPA, backlogs, branch, batch) | `app/tools/eligibility.py` | `tests/test_eligibility.py` | planned |
| C6 | `match_resume` (skills + embedding similarity) | `app/tools/resume.py` | `tests/test_resume.py` | planned |
| C7 | `track_application` | `app/tools/applications.py` | `tests/test_applications.py` | planned |
| C8 | Agent: plan, eligibility, resume, retrieval, weekly plan | `app/agent/planner.py`, `executor.py`, `steps.py` | `test_agent.py::happy_path` | planned |
| C9 | Approval before saving | `app/agent/executor.py` | `test_agent.py::approval_required` | planned |
| C10 | Max steps, saved state | `app/agent/executor.py`, `AgentRun` model | `test_agent.py::max_steps`, `::state_saved` | planned |
| C11 | Error recovery: retry, fallback, skip | `app/agent/executor.py` | `test_agent.py::recovery_*` | planned |
| C12 | Why fine-tuning, image models, multi-agent are not used | `docs/architecture.md` section 3 | Document | done |

## D. Data

| # | Requirement | Implemented in | Proof | Status |
|---|---|---|---|---|
| D1 | `placement_policy.md` | `backend/data/` | File | done |
| D2 | About 12 fictional company profiles + JDs | `backend/data/companies/` | Files | done |
| D3 | About 15 interview experiences | `backend/data/interviews/` | Files | done |
| D4 | About 6 prep guides | `backend/data/guides/` | Files | done |
| D5 | `students_seed.json`, demo resumes | `backend/data/` | Files | done |
| D6 | Fictional only, marked as sample data | `backend/data/README.md`, `README.md` | Document | planned |
| D7 | Upload `.md` / `.txt` / `.pdf` then re-index | `app/api/admin.py`, `app/rag/index.py` | `tests/test_admin.py` | planned |

## E. LLM providers

| # | Requirement | Implemented in | Proof | Status |
|---|---|---|---|---|
| E1 | Gemini via `google-genai`, key from `.env` | `app/llm/gemini.py` | `tests/test_llm.py` | planned |
| E2 | Local fallback (cached Qwen2.5-0.5B-Instruct) | `app/llm/local.py` | `tests/test_llm.py` | planned |
| E3 | Extractive fallback with citations | `app/llm/extractive.py` | `tests/test_llm.py` | planned |
| E4 | Automatic fallback; works with no key | `app/llm/router.py` | `test_llm.py::fallback_chain` | planned |
| E5 | Provider badge | `AnswerResult.provider`, Ask page | Screenshot | planned |
| E6 | MiniLM embeddings, ms-marco reranker, CPU torch only | `app/rag/models.py`, `requirements.txt` | Preflight in `PROGRESS.md` | planned |

## F. Stack and run

| # | Requirement | Implemented in | Proof | Status |
|---|---|---|---|---|
| F1 | FastAPI, SQLAlchemy + SQLite, Pydantic, FAISS, rank-bm25 | `backend/` | `requirements.txt` | planned |
| F2 | Structured JSON logging | `app/logging_conf.py` | `tests/test_logging.py` | planned |
| F3 | OpenAPI at `/docs` | `app/main.py` | Manual check in Phase 3 | planned |
| F4 | Next.js App Router, TypeScript, Tailwind, shadcn/ui | `frontend/` | Build | planned |
| F5 | AI Elements for chat, citations, reasoning, tool calls | `frontend/components/ai-elements/` | Ask and Prep pages | planned |
| F6 | Motion; GSAP + ScrollTrigger + Lenis on landing | `frontend/components/landing/` | Landing page | planned |
| F7 | One command to run both | `scripts/dev.ps1` | Fresh-clone check | planned |
| F8 | `.gitignore` covers venv, node_modules, .next, .env, DB, logs, indexes | `.gitignore` | Phase 0 | done |
| F9 | `screenshots/` kept with `.gitkeep` | `screenshots/.gitkeep` | Phase 0 | done |

## G. Security

| # | Requirement | Implemented in | Proof | Status |
|---|---|---|---|---|
| G1 | JWT in httpOnly cookie, student / coordinator roles | `app/security/auth.py` | `tests/test_auth.py` | planned |
| G2 | argon2 password hashing | `app/security/auth.py` | `tests/test_auth.py` | planned |
| G3 | Role check on every admin route | `app/api/admin.py` | `test_admin.py::all_admin_routes_forbidden` | planned |
| G4 | Input validation | `app/schemas.py` | `tests/test_ask_api.py`, `test_auth.py` | planned |
| G5 | Upload validation: type, size, sanitised filename | `app/security/uploads.py` | `tests/test_admin.py` | planned |
| G6 | Rate limiting | `app/security/rate_limit.py` | `tests/test_security_http.py` | planned |
| G7 | CORS restricted to the frontend origin | `app/main.py` | `tests/test_security_http.py` | planned |
| G8 | Security headers | `app/security/headers.py` | `tests/test_security_http.py` | planned |
| G9 | Injection guard on user input | `app/security/injection.py` | `tests/test_injection.py`, eval block rate | planned |
| G10 | Injection guard on retrieved / uploaded text | `app/security/injection.py` | `tests/test_injection.py` | planned |
| G11 | PII redaction before any LLM; never logged | `app/security/pii.py`, `logging_conf.py` | `tests/test_pii.py` | planned |
| G12 | Secrets only in `.env`; `.env.example` committed | `.env.example`, `app/config.py` | Phase 0 | done |
| G13 | No stack traces to users | `app/errors.py` | `tests/test_security_http.py` | planned |
| G14 | Dependency pinning | `requirements.txt`, `package-lock.json` | Files | planned |
| G15 | `SECURITY.md` with file locations | `SECURITY.md` | Document | planned |

## H. Evaluation and testing

| # | Requirement | Implemented in | Proof | Status |
|---|---|---|---|---|
| H1 | pytest: tools, API, RAG, agent, security | `backend/tests/` | `docs/test-evidence.md` | planned |
| H2 | Coverage reported | `scripts/test.ps1` | `docs/test-evidence.md` | planned |
| H3 | About 40 eval cases across six categories | `eval/cases.json` | File | planned |
| H4 | Metrics: Hit@3, MRR, groundedness, citation accuracy, refusal accuracy, injection block rate, agent success, latency, provider | `eval/metrics.py` | `eval/results/summary.json` | planned |
| H5 | Baseline vs final | `eval/run_eval.py` | `docs/evaluation.md` | planned |
| H6 | Results and charts saved | `eval/results/` | Files | planned |
| H7 | Playwright smoke test of main flows | `frontend/e2e/smoke.spec.ts` | `docs/test-evidence.md` | planned |
| H8 | Real results only | All docs generated from result files | Review in Phase 9 | planned |

## I. Showcase (`SHOWCASE.md`)

| # | Requirement | Implemented in | Proof | Status |
|---|---|---|---|---|
| I1 | White + navy identity, typography, spacing | `frontend/app/globals.css` | Hallmark audit, screenshots | planned |
| I2 | Landing: six scroll sections | `frontend/components/landing/` | Screenshots | planned |
| I3 | Ten app pages with ready examples | `frontend/app/(app)/` | Screenshots | planned |
| I4 | Error pages 404 / 403 / 429 / 500, toasts, skeletons, empty states | `frontend/app/` | Screenshots | planned |
| I5 | Demo accounts with "Use demo account" buttons | `app/seed.py`, login page | Smoke test | planned |
| I6 | Guided Tour: manual default, bar, spotlight, keyboard, survives navigation | `frontend/components/tour/` | Phase 9 tour run | planned |
| I7 | One speed config shared by tour and animations | `frontend/lib/speed.ts` | Code | planned |
| I8 | `prefers-reduced-motion` respected | Landing + Motion config | Phase 9 check | planned |
| I9 | No raw JSON on screen | All pages | Phase 9 review | planned |
| I10 | Desktop + mobile screenshots of every page | `screenshots/` | Files | planned |
| I11 | Hallmark + Web Design Guidelines audits fixed | Phase 9 | `PROGRESS.md` notes | planned |

## J. Documentation

| # | Requirement | Implemented in | Status |
|---|---|---|---|
| J1 | `README.md` | Root | planned |
| J2 | `docs/requirements.md` | Done in Phase 1 | done |
| J3 | `docs/architecture.md` with diagram + Mermaid | Done in Phase 1 | done |
| J4 | `docs/evaluation.md` | Phase 6 | planned |
| J5 | `docs/test-evidence.md` | Phase 6, updated Phase 9 | planned |
| J6 | `SECURITY.md` | Phase 10 | planned |
| J7 | `docs/api.md` | Phase 10 | planned |
| J8 | `docs/REQUIREMENTS_MATRIX.md` | This file | in progress |
| J9 | `docs/DECISIONS.md` | Started Phase 1 | in progress |
| J10 | `docs/CODE_MAP.md` | Phase 10 | planned |
| J11 | `docs/research.md` | Done in Phase 1 | done |
| J12 | `PROGRESS.md` kept current | Root | in progress |

## K. Process rules

| # | Rule | Proof | Status |
|---|---|---|---|
| K1 | Phases in order; commit + push after each | Git history | in progress |
| K2 | Fresh-clone check | Phase 10 notes in `PROGRESS.md` | planned |
| K3 | No source file hidden by `.gitignore` | `git status --ignored` review in Phase 10 | planned |
| K4 | Everything on `main` | GitHub | in progress |
