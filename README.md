# PlaceMate

An AI placement copilot for engineering students, and a dashboard for the placement cell that answers their questions.

Students ask about placement rules and companies and get answers with the source attached, check their eligibility for each company, compare their resume with a job description, and get a week-by-week prep plan that is saved only after they approve it. Coordinators upload documents and see what students ask, what the documents don't answer, and who is eligible for what.

> **Sample data.** Every company, student, resume and interview write-up in this repository is fictional, written for this project. No real company or person is described.

![Landing page](screenshots/desktop/01-landing-hero.png)

## Contents

- [The problem](#the-problem)
- [What PlaceMate does](#what-placemate-does)
- [Preview](#preview)
- [Architecture](#architecture)
- [AI components, and why each one is there](#ai-components-and-why-each-one-is-there)
- [Tech stack](#tech-stack)
- [Run it on Windows](#run-it-on-windows)
- [Demo logins](#demo-logins)
- [Results](#results)
- [Tests](#tests)
- [Security](#security)
- [Limitations](#limitations)
- [Future work](#future-work)
- [Documentation](#documentation)

## The problem

At many tier-2 and tier-3 engineering colleges, placement information lives in PDFs, notices and WhatsApp forwards. Students ask the placement cell the same questions every week: can I sit for another company after an offer, am I eligible with one backlog, what are the rounds at this company, how should I prepare. Eligibility is checked by hand before every drive. Preparation depends on which seniors a student happens to know.

## What PlaceMate does

**For students**

- **Ask, with sources.** Questions are answered from the college's placement documents only. Every sentence carries a numbered citation, the source passages are shown as cards, and a panel shows how the answer was produced. If the documents don't cover a question, PlaceMate says so instead of guessing.
- **Eligibility.** CGPA, active backlogs, branch and batch are checked by code against each company's criteria, with a reason for every pass or fail. One company or all twelve at once.
- **Resume match.** A match score against a job description, the required and preferred skills found and missing, and what to do about the gaps. Phone numbers, emails, addresses and profile links are removed before any model sees the resume, and the page shows what was removed.
- **Prep agent.** "Prepare me for Nimbusware": the agent checks eligibility, matches the resume, reads the company's selection process and seniors' interview write-ups, and drafts a week-by-week plan. It asks for approval before saving the plan and adding the application to the tracker. Failed steps are retried or replaced with a fallback, and the page shows how.
- **Application tracker** with stages and deadlines.

**For the placement cell**

- **Documents.** Upload `.md`, `.txt` or `.pdf` notices; they are validated, cleaned of hidden instructions aimed at the model, and searchable straight away.
- **Analytics.** Most asked questions, questions the documents could not answer, eligibility per company with the most common blocker, which model answered, blocked attempts, and an activity log.

**For a reviewer**

- **Evaluation** and **Security** pages inside the app: baseline vs final results from the saved evaluation run, test results and coverage, and one "Try it" button per security measure that sends a real request and shows the response.
- **Guided tour**: 30 steps from the landing page through both roles, each naming the requirement it demonstrates. Manual by default; nothing moves until you press Next.

## Preview

| | |
|---|---|
| ![Cited answer](screenshots/desktop/08-ask-cited-answer.png) Cited answer with the pipeline steps | ![Injection blocked](screenshots/desktop/09-ask-injection-blocked.png) Prompt injection blocked before retrieval |
| ![Eligibility](screenshots/desktop/10-eligibility.png) Eligibility, criterion by criterion | ![Resume match](screenshots/desktop/12-resume-match.png) Resume match |
| ![Agent approval](screenshots/desktop/14-agent-approval.png) The agent asks before saving | ![Agent recovered](screenshots/desktop/15-agent-recovered-and-saved.png) A failed step recovered, then saved |
| ![Analytics](screenshots/desktop/18-analytics.png) Coordinator analytics | ![Evaluation](screenshots/desktop/21-evaluation-chart.png) Baseline vs final |
| ![Security](screenshots/desktop/22-security.png) Live security checks | ![Guided tour](screenshots/desktop/23-guided-tour.png) Guided tour |

All 26 views at desktop and phone width are in [`screenshots/desktop`](screenshots/desktop) and [`screenshots/mobile`](screenshots/mobile).

## Architecture

![Architecture diagram](docs/architecture-diagram.png)

```mermaid
flowchart LR
  FE[Next.js app<br/>student + coordinator pages] -->|JSON + SSE, httpOnly cookie| API[FastAPI edge<br/>auth, roles, rate limit,<br/>CORS, headers, validation]
  API --> RAG[RAG pipeline<br/>guard, BM25 + FAISS, RRF,<br/>cross-encoder, citations]
  API --> TOOLS[Tools<br/>eligibility, resume match,<br/>application tracker]
  API --> AGENT[Prep agent<br/>plan, tools, retries,<br/>approval]
  AGENT --> TOOLS
  AGENT --> RAG
  RAG --> LLM[LLM router<br/>Gemini, local Qwen,<br/>extractive]
  RAG --> IDX[(Search index)]
  API --> DB[(SQLite)]
```

The frontend talks to the backend directly (CORS limited to the frontend's origin, session in an httpOnly cookie). The backend is one FastAPI app: routes stay thin and call the RAG pipeline, the tools or the agent. Every answer, tool call and agent step is logged as an event, and the coordinator's analytics are built from those events.

Full detail, with data flows for each feature, is in [`docs/architecture.md`](docs/architecture.md). A guided walk through the code is in [`docs/CODE_MAP.md`](docs/CODE_MAP.md).

## AI components, and why each one is there

| Component | Used for | Why |
|---|---|---|
| **RAG** with hybrid retrieval | Every question | Answers must come from this college's documents and be checkable. BM25 catches exact terms (company names, "CGPA", "PPO"); vectors catch paraphrases. Reciprocal Rank Fusion merges both, and a cross-encoder reranks the candidates to the best five. Low rerank scores, or a company name that appears in no document, lead to a refusal. |
| **Tools** (plain Python) | Eligibility, resume match, application tracking | These are rules and arithmetic. An LLM could get a CGPA comparison wrong; a function cannot. The model never decides who is eligible. |
| **One agent** | Only "Prepare me for &lt;company&gt;" | It is the one goal that needs several steps in order, with decisions between them (stop if not eligible, skip a failed optional step). It has a fixed set of tools, a budget of 8 tool calls, retries and fallbacks, saves its state after every step, and must get the student's approval before writing anything. |
| **LLM with fallback** | Writing the answer and the plan summary | Gemini (`gemini-3.5-flash-lite`) when a key is set; otherwise a small local model (Qwen2.5-0.5B-Instruct, CPU) if it is in the Hugging Face cache; otherwise an extractive answer built from the source sentences. The app works with no key and no download. A badge shows which one answered. |

**Not used, on purpose:** fine-tuning (the documents change every season; retrieval handles that, training would not), image models (all inputs are text), and multi-agent systems (one agent with tools covers the only multi-step goal; more agents would add cost and failure points without a task that needs them).

## Tech stack

| Layer | Choice |
|---|---|
| Backend | Python 3.14, FastAPI, SQLAlchemy 2 + SQLite, Pydantic 2, structured JSON logging |
| Retrieval | FAISS, rank-bm25, `sentence-transformers/all-MiniLM-L6-v2`, `cross-encoder/ms-marco-MiniLM-L-6-v2`, CPU-only PyTorch |
| Models | Gemini via `google-genai`; Qwen2.5-0.5B-Instruct via `transformers`; extractive fallback |
| Security | argon2id, JWT in an httpOnly cookie, rate limiting, prompt-injection guards, PII redaction |
| Frontend | Next.js 16 (App Router), TypeScript, Tailwind CSS 4, shadcn/ui, Vercel AI Elements, Motion, Recharts |
| Landing page | GSAP + ScrollTrigger, Lenis |
| Testing | pytest + coverage, Playwright |

## Run it on Windows

### What you need

- Windows 10 or 11 with PowerShell
- [Python](https://www.python.org/downloads/) 3.14 with the `py` launcher (the version this was built and tested on; `npm run setup` falls back to 3.12 if 3.14 is missing)
- [Node.js](https://nodejs.org/) 24 LTS
- Git
- About 3 GB of disk for Python packages (CPU-only PyTorch) and the two small retrieval models
- Optional: a Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey). Without one, answers come from the local model or the extractive fallback.

### Quick start

```powershell
git clone https://github.com/Krishna141414/placemate-ai.git
cd placemate-ai

# 1. Install everything (virtual environment, packages, .env)
npm run setup

# 2. Optional: put your key in .env
#    GEMINI_API_KEY=your-key

# 3. Start the backend and the frontend
npm run dev:all
```

Open **http://localhost:3000**. The first start downloads the two retrieval models (about 180 MB) if they are not already cached, builds the search index and seeds the demo data, which takes a minute or two. The backend runs in its own window; the API reference is at http://127.0.0.1:8000/docs.

`npm run setup` and `npm run dev:all` run `scripts\setup.ps1` and `scripts\dev.ps1`. If you call the scripts directly and PowerShell refuses to run them, use `powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1`.

### Step by step, without the scripts

```powershell
# Backend
cd backend
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt   # uses the CPU-only PyTorch index
copy ..\.env.example ..\.env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Frontend, in a second terminal
cd frontend
npm ci
npm run dev
```

### Other commands

| Command (from the repository root) | What it does |
|---|---|
| `npm run reset-demo` | Removes everything added during demos (questions, agent runs, uploads, plans) and restores the seeded state |
| `npm run test:backend` | pytest with coverage; writes `docs/evidence/` |
| `npm run test:e2e` | Playwright smoke tests (needs the servers, which it starts if they are not running) |
| `npm run eval` | The evaluation, baseline vs final, Gemini and offline (`scripts\eval.ps1 -Providers extractive` for offline only) |

## Demo logins

| Role | Email | Password |
|---|---|---|
| Student (Ananya, CSE, CGPA 7.8, 1 backlog) | `student@placemate.demo` | `Student@123` |
| Coordinator (placement cell) | `coordinator@placemate.demo` | `Coord@123` |

The login page has a button for each.

## Results

A 47-case evaluation set (25 answerable questions, 6 hallucination traps, 6 injection attempts, 4 ambiguous questions, 6 agent tasks) was run in two modes. **Baseline** is vector-only retrieval with no reranker, no guards and no refusal, and an agent with no retries or fallbacks. **Final** is the system as shipped. Run with Gemini on 2026-11-19:

| Metric | Baseline | Final |
|---|---:|---:|
| Hit@3 | 100.0% | 100.0% |
| MRR | 0.980 | 1.000 |
| Answer quality (correct facts) | 92.0% | 100.0% |
| Groundedness | 100.0% | 98.3% |
| Citation accuracy | 96.9% | 93.2% |
| Refusal accuracy | 93.5% | 100.0% |
| Hallucination rate on traps | 0.0% | 0.0% |
| Injection block rate | 0.0% | 100.0% |
| Agent task success | 33.3% | 100.0% |
| Latency p50 / p95 | 3.30 s / 8.14 s | 5.39 s / 10.61 s |

What it shows: the guards block every injection attempt before any model is called, so safety no longer depends on the model behaving; refusals are right in both directions (no answerable question refused, every trap refused); and the agent's retries and fallbacks take task success from 2 of 6 to 6 of 6. The costs are about 2 s more median latency, and slightly lower citation accuracy, because the final system cites several passages per sentence and some of them only partly support it.

Without any API key (extractive fallback), the final pipeline brings the hallucination rate on traps from 100% to 16.7% and refusal accuracy from 80.6% to 96.8%.

The method, both full tables, the bugs the evaluation found and how they were fixed, and the limits of a small hand-written set are in [`docs/evaluation.md`](docs/evaluation.md).

## Tests

| Suite | Result |
|---|---|
| Backend (pytest) | **379 passed**, 0 failed, **96.0% line coverage** |
| Frontend smoke tests (Playwright) | **18 passed**: login, ask (cited, refused, blocked), eligibility, resume match, agent with recovery and approval, tracker, roles, coordinator pages, tour controls |
| Guided tour, all 30 steps in Auto mode with a pause | **passed** |
| `tsc`, ESLint, `next build` | clean |

Commands, outputs and what each test covers are in [`docs/test-evidence.md`](docs/test-evidence.md); raw outputs are in [`docs/evidence/`](docs/evidence).

## Security

- Login with student and coordinator roles; argon2id password hashes; the session is a JWT in an httpOnly cookie; the role is read from the database on every request.
- Role checks on every coordinator route, and ownership checks so students see only their own data.
- Pydantic validation on every request; uploads checked for size, type, real content and file name.
- Rate limits (login 10 a minute, API 120), CORS limited to the frontend, an origin check on state-changing requests, security headers on every response.
- Prompt-injection guards on user input **and** on document text (at upload and again at retrieval), a canary in the system prompt, and an output filter.
- Phone, email, address and profile links removed from resumes before any model sees them, and masked in logs.
- One error format with a request id and no stack traces; secrets only in `.env`; pinned dependencies.

Each measure, its file and the test that proves it: [`SECURITY.md`](SECURITY.md).

## Limitations

- The evaluation set is small and was written by the same person who wrote the documents, and it was used during development. There is no separate held-out set, so the final numbers are optimistic.
- 34 documents make retrieval easy; at a real college's scale the retrieval numbers would need re-measuring.
- Injection detection is pattern-based. A new phrasing can get past the input guard; the other layers are there for that case.
- The local model is slow on CPU (tens of seconds per answer). It is a fallback, not a primary option.
- Rate limiting is in memory, for a single backend process.
- Accounts are seeded; there is no sign-up or password reset.

## Future work

- Sign-up through the college's single sign-on, and profile data from the college's records instead of a seed file.
- Cite only the passage that states each fact, to bring citation accuracy back up.
- A held-out evaluation set written by someone else, and an LLM judge as a second opinion on groundedness.
- Notifications for deadlines and new notices.
- Postgres and a shared rate-limit store for running more than one backend process.

## Documentation

| Document | Contents |
|---|---|
| [`docs/requirements.md`](docs/requirements.md) | Problem, users, functional and non-functional requirements, scope |
| [`docs/architecture.md`](docs/architecture.md) | Components, data flows, why each AI component was chosen and what was not used |
| [`docs/evaluation.md`](docs/evaluation.md) | Evaluation method, results, findings, limits |
| [`docs/test-evidence.md`](docs/test-evidence.md) | Test commands, outputs, coverage, screenshots list |
| [`SECURITY.md`](SECURITY.md) | Security measures with files and tests |
| [`docs/api.md`](docs/api.md) | Every endpoint, roles, streaming events |
| [`docs/CODE_MAP.md`](docs/CODE_MAP.md) | How a request travels, folder by folder, every flow step by step |
| [`docs/REQUIREMENTS_MATRIX.md`](docs/REQUIREMENTS_MATRIX.md) | Every requirement → where it is implemented → how it is proved |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | Each design decision and the reason for it |
| [`backend/data/README.md`](backend/data/README.md) | The sample data |

---

Built by Krishna for the VoidMain internship final project.
