# PROGRESS

Resume rule: read `CLAUDE.md` and this file, then continue `BUILD_PROMPT.md` from the first unfinished step.

## Status

| Phase | Name | Status |
|---|---|---|
| 0 | Preflight | done |
| 1 | Research & plan | done |
| 2 | Data | done |
| 3 | Backend core | done |
| 4 | RAG | next |
| 5 | Tools & agent | todo |
| 6 | Tests & evaluation | todo |
| 7 | Frontend app | todo |
| 8 | Landing showcase + Guided Tour | todo |
| 9 | Verify | todo |
| 10 | Docs & finish | todo |

## Next step

Phase 4, step 1: RAG ingestion. Extend `backend/app/rag/loader.py` (load corpus, clean, PDF text), then `chunker.py`, `models.py` (embedder + reranker singletons), `index.py` (FAISS + BM25, save/load/ensure), `retriever.py` (baseline vs final), then LLM providers, injection guard, pipeline and `/api/ask`. Register the index build as a startup hook in `app/main.py` (`app.state.startup_hooks`). Confirm the Gemini model id with a live call if a key is available (D-28).

## Phase 3 - Backend core (done 2026-11-14)

- venv on Python 3.14; `backend/requirements.txt` is a full `pip freeze` (95 pins) with the PyTorch CPU index. `torch 2.15.0+cpu`, `torch.cuda.is_available()` is False.
- 3.1 `app/main.py` (factory + lifespan), `config.py`, `db.py`, `models.py` (User, StudentProfile, Document, Conversation, Message, Application, PrepPlan, AgentRun, Event), `schemas.py`, `logging_conf.py` (JSON lines, request id, PII scrub filter), `errors.py` (one error envelope), `seed.py` (`python -m app.seed [--reset]`).
- 3.2 `security/auth.py` (argon2id, JWT in httpOnly SameSite=Lax cookie, role dependencies), `security/rate_limit.py` (sliding window: auth 10/min, probe 5/min, default 60/min), `security/headers.py` (request context, security headers, origin check), CORS limited to `FRONTEND_ORIGIN`. `security/pii.py` written early because the log filter uses it.
- 3.3 Server started with uvicorn: `/health` ok, `/docs` serves Swagger UI, login as the demo student works, `/api/meta/companies` returns 12.
- Tests: `tests/test_auth.py` + `tests/test_security_http.py`, 38 passed.

Notes:
- One requirements file instead of the planned runtime/dev split: one command to set up, and the test tools are needed for the required test evidence anyway.
- In development an unset `SECRET_KEY` generates a random key once into `backend/storage/dev_secret.key` (ignored). In production the app refuses to start without a real key.
- `GOOGLE_API_KEY` is accepted as an alias for `GEMINI_API_KEY`.

## Phase 2 - Data (done 2026-11-14)

- `backend/data/placement_policy.md` (15 sections: eligibility, backlogs, company categories, one-offer policy with the dream exception, PPO, attendance 75 percent, process stages, debarment, offer acceptance in 3 working days, documents, dress code).
- 12 companies in `backend/data/companies/` with YAML front matter (criteria, skills, rounds, deadline) and a prose body.
- 15 interview experiences in `backend/data/interviews/`, 6 guides in `backend/data/guides/`.
- `students_seed.json` (10 students + coordinator), 3 demo resumes with fake contact details for the PII redactor.
- `backend/data/fixtures/injected_notice.md`: planted-instruction document for injection tests; not indexed by default.
- About 12,000 words in total. All fictional; the college is "Kaveri Ridge Institute of Technology (KRIT)".

Demo student design (Ananya Rao: CSE, CGPA 7.8, 1 active backlog, batch 2027):
- Eligible: nimbusware, quantaleaf, kairoscloud, brightpath, tessera.
- Fails CGPA only: orbitpay (8.0), mosaicai (8.0). Fails CGPA and backlogs: veltrix (8.5, 0 backlogs).
- Fails backlogs only: lumengrid (0 allowed). Fails branch: ferrowind, halcyon. Fails batch: zephyrnet (2026 only).

## Phase 1 - Research & plan (done 2026-11-14)

- 1.1 Last30days ran (Reddit 17 threads, HN 13 stories, GitHub 4 items + 15 web pages). X / YouTube / TikTok not configured; Polymarket timed out. Eight takeaways in `docs/research.md`. Community evidence on campus-placement tools was thin and is flagged as such in the doc.
- 1.2 Context7 docs pulled for FastAPI, Next.js 16 (`proxy.ts` replaces `middleware.ts`), shadcn (`init`, `mcp init --client claude`), AI Elements (`npx ai-elements@latest add <name>`), google-genai, Lenis + GSAP. Summary table at the end of `docs/research.md`.
- 1.3 Superpowers brainstorming + writing-plans used. Plan: `docs/superpowers/plans/2026-11-14-placemate.md`. Executing inline.
- 1.4 Written: `docs/requirements.md`, `docs/architecture.md` (Diagram Design figure as HTML + SVG + PNG, plus Mermaid), `docs/REQUIREMENTS_MATRIX.md`, `docs/DECISIONS.md` (D-01 to D-28).

Notes:
- The Diagram Design PNG helper needs Python Playwright, which is not installed. The PNG was rendered with the Playwright MCP instead; the SVG came from the skill's own exporter and the file passes its `self_check.py`.
- `.env.example` still names `gemini-2.5-flash`; docs show that family is no longer current. To fix in Phase 4 after a live call confirms the free-tier model (D-28).
- A Gemini/Google key appears to exist in the machine's process environment (seen as "present" by a tool diagnostic, value never read). Phase 4 checks whether the app can use it.

## Phase 0 - Preflight (done 2026-11-14)

### 0.1 Runtimes
- Python 3.14.0 is the only Python installed (`py -0` lists just 3.14). No 3.12 fallback available.
- CPU PyTorch wheel exists for it: `torch-2.15.0+cpu-cp314-cp314-win_amd64` from `https://download.pytorch.org/whl/cpu`. So the venv uses Python 3.14.
- Binary wheels also confirmed for cp314: `faiss-cpu 1.16.0`, `tokenizers 0.23.3`, `safetensors 0.8.0`, `bcrypt 5.0.0`, `argon2-cffi-bindings 26.2.0`, `pymupdf 2.1`.
- Node v24.11.1, npm 11.6.2, git 2.52.0.
- `gh` CLI is not installed. Not needed: plain `git push` over HTTPS reaches the repo.
- Remote `origin` = `https://github.com/Krishna141414/placemate-ai.git` (repo existed and was empty).

### 0.2 Toolkit available
- Plugins: Superpowers 7.0.2, Last30days 3.31.0, Diagram Design 2.6.142, Humanizer 3.1.0.
- MCP: Playwright (connected), Context7 (connected).
- Global skills: hallmark, gsap-core, gsap-timeline, gsap-scrolltrigger, gsap-react, gsap-performance, gsap-plugins, gsap-utils, gsap-frameworks, web-design-guidelines, humanizer, find-skills.
- shadcn MCP and AI Elements are per-project; set up inside `frontend/` in Phase 7.

### 0.3 Hugging Face cache (all present, nothing to download)
- `Qwen/Qwen2.5-0.5B-Instruct` (model.safetensors 942 MB)
- `sentence-transformers/all-MiniLM-L6-v2` (87 MB)
- `cross-encoder/ms-marco-MiniLM-L-6-v2` (87 MB)

### 0.4 Scaffold
- Folders: `backend/`, `frontend/`, `eval/`, `docs/`, `scripts/`, `screenshots/.gitkeep`.
- `.gitignore`, `.env.example`, `PROGRESS.md` created.

## Notes / decisions taken without asking
- `.gitignore` deliberately avoids broad patterns like `lib/`, `data/` or `build/` so `frontend/lib` and `backend/data` are never hidden.
- Runtime artefacts (SQLite DB, FAISS/BM25 index, uploads, logs) all live under `backend/storage/`, which is ignored as one folder.
