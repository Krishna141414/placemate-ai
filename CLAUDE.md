# Task 14: PlaceMate - AI Placement Copilot (VoidMain Internship - Final Industry-Style Project)

## Brief (official)
"Build an advanced end-to-end AI/GenAI solution for a realistic problem. Identify a meaningful problem and prepare requirements and architecture. Implement suitable AI/GenAI components such as RAG, tools or agents based on the problem rather than forcing every technique. Include evaluation, testing, security considerations and a usable application interface. Submit code, README, architecture, test evidence, screenshots and documentation." (160 pts)

**This is a major project: industry-level quality, NOT a vibe-coded demo.** Follow BUILD_PROMPT.md phase by phase. UI/showcase rules are in SHOWCASE.md.

## Problem
Students at tier-2/3 engineering colleges get little personalised placement guidance; the placement cell answers the same questions again and again (eligibility, policies, company process, preparation). PlaceMate gives students instant, cited answers and personalised preparation, and gives coordinators a dashboard of what students struggle with.

## Users
- **Student:** asks placement questions, checks eligibility, matches resume to a job, gets a prep plan, tracks applications.
- **Coordinator (admin):** uploads/updates documents, sees analytics (top questions, unanswered questions, eligibility stats), views logs.

## AI components (only what the problem needs - justify each in docs/architecture.md)
1. **RAG (core):** Q&A over placement documents with citations. Hybrid retrieval (BM25 + vector, Reciprocal Rank Fusion) -> cross-encoder reranking -> grounded generation with numbered citations -> refuse when not in documents.
2. **Tools (deterministic logic the LLM must not guess):**
   - `check_eligibility(student_profile, company_id)` - CGPA, backlogs, branch, batch rules from company criteria.
   - `match_resume(resume_text, company_id)` - skill extraction + embedding similarity vs the job description -> match %, matched skills, missing skills.
   - `track_application(...)` - create/update applications and deadlines (DB).
3. **Agent (only for the multi-step goal "Prepare me for <company>"):** plan -> eligibility -> resume match -> retrieve that company's process + interview experiences -> week-by-week prep plan -> **ask the student to approve before saving** the plan + application to their tracker. Max steps, state saved, error recovery (retry / fallback / skip optional step).
- Not used (and say why in docs): fine-tuning, image models, multi-agent systems - not needed for this problem.

## Data (sample, clearly marked as sample data in README)
Create realistic but **fictional** data in `backend/data/` - never real company names or real people:
- `placement_policy.md` (eligibility rules, one-offer policy, attendance, documents, dress code, process stages)
- ~12 fictional company profiles + job descriptions (role, CTC range, criteria, rounds, skills) as markdown
- ~15 interview-experience write-ups (fictional), ~6 prep guides (DSA, aptitude, HR, resume, SQL, system design basics)
- `students_seed.json` (demo student profiles), demo resumes as text
- Coordinators can upload new `.md`/`.txt`/`.pdf` documents -> re-index.

## LLM providers (config switch + automatic fallback)
`LLM_PROVIDER=gemini` (Gemini API via `google-genai`, key `GEMINI_API_KEY` from `.env`; look up the current free-tier fast model via Context7/docs) -> fallback `local` (small instruct model already in `%USERPROFILE%\.cache\huggingface\hub`, e.g. Qwen2.5-0.5B-Instruct - download no new LLM) -> fallback `extractive` (best sentences from sources with citations). App must work with no key. Show which provider answered (small badge). Embeddings `sentence-transformers/all-MiniLM-L6-v2`, reranker `cross-encoder/ms-marco-MiniLM-L-6-v2` (both likely cached). CPU-only PyTorch (`--index-url https://download.pytorch.org/whl/cpu`), never CUDA.

## Stack (my standard for major projects)
- **Backend:** Python FastAPI (`backend/`), SQLite via SQLAlchemy, Pydantic schemas, FAISS + rank-bm25, structured JSON logging. OpenAPI docs at `/docs`.
- **Frontend:** Next.js (App Router) + TypeScript + Tailwind + shadcn/ui (`frontend/`), Vercel AI Elements for the chat/citations/reasoning/tool-call UI, Motion for micro-interactions, GSAP + ScrollTrigger + Lenis for the landing/showcase scroll storytelling.
- One command to run both locally (`scripts/dev.ps1` + `npm run dev:all` or similar) and clear separate steps in README.
- Windows + PowerShell, Python 3.14 (if CPU PyTorch has no wheel for the installed Python, use `py -3.12` for the venv if installed, otherwise stop and tell me), Node.js LTS (v24 installed). Project in `D:\Internship Projects\placemate-ai` (NOT OneDrive; keep paths short because of Windows' 260-character limit). Gitignore `.venv`, `node_modules`, `.next`, `.env`, DB files, logs, indexes, model cache. Keep `screenshots/` with `.gitkeep`.

## Toolkit to use (installed globally - use them, don't skip)
- **Research/plan:** Last30days (what top AI placement/career tools and RAG apps look like now), Context7 (current docs for FastAPI, Next.js, shadcn, AI Elements, google-genai, GSAP), Superpowers (installed: brainstorming, writing-plans, executing-plans, verification-before-completion skills; check exact names in the `/` picker).
- **Design:** Hallmark (study first, audit after every big UI change and after pasting any component), shadcn MCP, 21st.dev / React Bits components (hero, text, backgrounds - always hallmark-audited), Motion, GSAP (official GSAP skills installed: gsap-core, gsap-timeline, gsap-scrolltrigger, gsap-react, gsap-performance - use them). **No Aceternity** (looks AI-generated).
- **Verify:** Playwright MCP screenshots (desktop + mobile) of every page; if the Playwright MCP won't connect, take the screenshots with the project's own Playwright instead. Vercel Web Design Guidelines audit, Hallmark audit.
- shadcn MCP and AI Elements are per-project: set them up inside `frontend/` (`npx shadcn@latest ...`, `npx ai-elements@latest ...`), checking current commands with Context7.
- **Docs:** Diagram Design for the architecture diagram, Humanizer for README/landing copy (no AI-sounding text).

## Security (must be real and listed in SECURITY.md with file locations)
Auth (JWT in httpOnly cookie or session) with student/coordinator roles; bcrypt/argon2 password hashing; role checks on every admin route; input validation (Pydantic); upload validation (type, size, sanitised filename); rate limiting; CORS restricted to the frontend origin; security headers; prompt-injection guard on user input AND on retrieved/uploaded document text; **PII redaction** (phone, email, address) before resume text is sent to any LLM and never logged; secrets only in `.env` (`.env.example` committed); no stack traces to users; dependency pinning.

## Evaluation & testing (test evidence is required)
- **pytest** (`backend/tests/`): tools (eligibility edge cases, resume match), API (auth, roles, validation, rate limit, errors), RAG pipeline (retrieval returns correct source, refusal when not in docs), agent (happy path, tool failure recovery, approval required), security (injection blocked, PII redacted). Aim for meaningful coverage; report coverage %.
- **RAG/agent evaluation** (`eval/`): ~40-case eval set (answer quality, grounding/citations, hallucination traps, ambiguous inputs, injection, tool failures). Metrics: Hit@3, MRR, groundedness, citation accuracy, refusal accuracy, injection block rate, agent task success, latency, provider used. Run with baseline (vector only, no rerank) vs final (hybrid + rerank + guards) to show the improvement. Save `eval/results/` + charts.
- Frontend: Playwright smoke test of main flows (login, ask, eligibility, prep agent with approval).
- `docs/test-evidence.md`: commands, pytest output summary, coverage, eval tables, screenshot list.

## Documentation (required deliverables)
- `README.md` (Humanizer-polished): problem, solution, Preview (images from `screenshots/`), features, architecture diagram, tech stack, AI components + why, how to run (step by step, Windows), demo logins, eval results table, test evidence link, security summary, limitations, future work.
- `docs/requirements.md` (problem, users, functional + non-functional requirements, scope, out of scope).
- `docs/architecture.md` (Diagram Design diagram + Mermaid fallback, components, data flow for RAG / tools / agent, why each AI component was chosen and what was NOT used).
- `docs/evaluation.md`, `docs/test-evidence.md`, `SECURITY.md`, `docs/api.md` (or link to `/docs`).
- `docs/REQUIREMENTS_MATRIX.md`: every brief item and CLAUDE.md requirement -> where it is implemented -> which test/eval proves it -> status. Keep it updated every phase.
- `docs/DECISIONS.md`: short decision + reason for every design/architecture choice.
- `docs/CODE_MAP.md` (for my explanation video): Part 1 how a request travels (frontend -> API -> service -> RAG/tools/agent -> DB), Part 2 folder by folder (each file's job + main functions/classes, no line-by-line), Part 3 each flow step by step (ask, eligibility, resume match, prep agent with approval, upload + re-index, auth, eval run), Part 4 a suggested order for a video walkthrough.

## Rules
- Follow BUILD_PROMPT.md phases in order; commit + push after each phase; keep `PROGRESS.md` updated (done / next) so work can resume after a usage-limit stop.
- Do everything without asking me unless something truly blocks you. Pick the safer option and note it in PROGRESS.md.
- If the usage limit is close, finish the current small step, commit, update PROGRESS.md with the exact next step, and stop cleanly.
- Before finishing: a fresh-clone check (clone into a temp folder, follow the README from zero) and make sure no source file is hidden by `.gitignore`.
- Real results only - never invent eval numbers or test results.
- Finish: everything pushed to `main`, short summary (eval table, test summary, how to run, demo logins).
