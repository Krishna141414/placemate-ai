# BUILD_PROMPT.md - PlaceMate step-by-step build (follow every step, skip nothing)

> **For Krishna (how to start):** put CLAUDE.md, SHOWCASE.md, BUILD_PROMPT.md in `D:\Internship Projects\placemate-ai`, create an empty public GitHub repo `placemate-ai`, open the folder in VS Code, Claude Code on **High**, and paste:
> `Read CLAUDE.md, SHOWCASE.md and BUILD_PROMPT.md fully, then start BUILD_PROMPT.md from Phase 0 and keep going phase by phase. Follow every step; skip nothing. Update PROGRESS.md after every step.`
> New session after a limit: `Read CLAUDE.md and PROGRESS.md, then continue BUILD_PROMPT.md from the first unfinished step.`

Read CLAUDE.md and SHOWCASE.md fully first. Work phase by phase. After EACH phase: run what it says to run, fix errors, update `PROGRESS.md` (done / next / notes), `git commit` with a clear message and `git push` to `main`. If you stop (usage limit), resume from `PROGRESS.md`. Never invent results.

## Phase 0 - Preflight
1. Check: `python --version`, `py -0` (installed Pythons), `node --version`, `git remote -v` (add `origin` = github.com/Krishna141414/placemate-ai if missing). Check that a CPU PyTorch wheel exists for the chosen Python before creating the venv.
2. Check the toolkit: `claude plugin list` (Superpowers, Last30days, Diagram Design, Humanizer), `claude mcp list` (Playwright, Context7), `npx skills ls -g` (Hallmark, gsap-*, web-design-guidelines). Note in PROGRESS.md what's available; use everything that is.
3. Check the Hugging Face cache for Qwen2.5-0.5B-Instruct, all-MiniLM-L6-v2, ms-marco-MiniLM-L-6-v2. Download nothing big without need (never a new LLM; never CUDA torch).
4. Create the folder structure (`backend/`, `frontend/`, `eval/`, `docs/`, `scripts/`, `screenshots/.gitkeep`), `.gitignore`, `.env.example`, `PROGRESS.md`. Commit + push.

## Phase 1 - Research & plan
1. Last30days: research current AI career/placement copilots and well-designed RAG product UIs; write 5-8 takeaways in `docs/research.md`.
2. Context7: pull current docs for FastAPI, Next.js App Router, shadcn/ui, AI Elements, google-genai, GSAP ScrollTrigger, Lenis.
3. Superpowers brainstorm + write-plan (if installed); otherwise write the plan yourself.
4. Write `docs/requirements.md`, `docs/architecture.md` (Diagram Design diagram + Mermaid), `docs/REQUIREMENTS_MATRIX.md` and start `docs/DECISIONS.md`. Commit + push.

## Phase 2 - Data
1. Create the fictional sample data from CLAUDE.md (policy, ~12 companies + JDs, ~15 interview experiences, ~6 prep guides, demo students + resumes). Realistic Indian campus context, fictional names only.
2. Commit + push.

## Phase 3 - Backend core
1. FastAPI app factory, config (`.env`), SQLAlchemy models (User, Document, Conversation, Application, PrepPlan, AgentRun), Pydantic schemas, structured JSON logging with request id, global error handlers, seed script with demo accounts.
2. Auth (student / coordinator roles), password hashing, rate limiting, CORS, security headers.
3. Run the server, hit `/docs` and `/health`. Commit + push.

## Phase 4 - RAG
1. Ingestion + cleaning + chunking, embeddings, FAISS + BM25, RRF hybrid retrieval, cross-encoder rerank, prompt with numbered context, citations, refusal below threshold.
2. LLM providers: gemini -> local -> extractive with automatic fallback + provider badge info in responses.
3. Prompt-injection guard (user input + retrieved text), output filter.
4. `/api/ask` endpoint + saved conversations. Quick manual check with 5 questions. Commit + push.

## Phase 5 - Tools & agent
1. `check_eligibility`, `match_resume` (with PII redaction first), `track_application`, with Pydantic args.
2. Prep agent: planner -> executor loop with state, max steps, retry/fallback recovery, approval gate (pending -> approve/reject endpoints), saved runs.
3. Coordinator: document upload (validated) + re-index, analytics endpoints. Commit + push.

## Phase 6 - Tests & evaluation
1. pytest suites from CLAUDE.md; run them; get coverage (`pytest --cov`). Fix failures.
2. Eval set (~40 cases) + runner: baseline vs final. Save results + charts in `eval/results/`.
3. Write `docs/evaluation.md` and `docs/test-evidence.md` from the REAL outputs. Commit + push.

## Phase 7 - Frontend app
1. Hallmark study. Next.js + TypeScript + Tailwind + shadcn init (+ shadcn MCP). Theme tokens from SHOWCASE.md (white + navy).
2. Layout: sidebar, top bar, auth pages with demo buttons, protected routes by role.
3. Pages in SHOWCASE.md order (Dashboard, Ask with AI Elements, Eligibility, Resume Match, Prep Agent with approval dialog, Applications, Documents, Analytics, Evaluation, Security) with ready-made examples, toasts, skeletons, empty/error states, Motion transitions.
4. Hallmark audit after each page; fix. Commit + push after every 2-3 pages.

## Phase 8 - Landing showcase + Guided Tour
1. Landing page with GSAP + ScrollTrigger + Lenis sections from SHOWCASE.md (use 21st.dev / React Bits only where they fit, hallmark-audited). Copy via Humanizer.
2. Guided Tour (tour script, spotlight, captions, Play/Pause/Next/Back, speed toggle, keyboard, survives navigation) + `lib/speed.ts`.
3. Commit + push.

## Phase 9 - Verify
1. Start backend + frontend. Playwright: smoke tests of main flows + screenshots of landing and every page at desktop and mobile width (save to `screenshots/`).
2. Hallmark audit + Vercel Web Design Guidelines audit; fix issues.
3. Run the full Guided Tour (auto, pause, manual). Fix console/server errors.
4. Superpowers verification-before-completion (if installed): check every CLAUDE.md requirement and every brief item (problem, requirements, architecture, AI components, evaluation, testing, security, interface, code, README, architecture, test evidence, screenshots, documentation). Commit + push.

## Phase 10 - Docs & finish
1. README (Humanizer-polished) with Preview images from `screenshots/`, step-by-step Windows run guide (`scripts/dev.ps1`), demo logins, eval + test tables, links to all docs. `SECURITY.md`, `docs/api.md`, `docs/CODE_MAP.md` (checked against the real code), final `docs/REQUIREMENTS_MATRIX.md`.
2. Fresh-clone check from the README in a temp folder; confirm nothing needed is git-ignored. Reset demo data so it's clean for recording.
3. Final commit + push. Reply with a short summary: eval table (baseline vs final), test results + coverage, how to run, demo logins.
