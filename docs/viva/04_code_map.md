# Code map for the viva: the 15 functions that matter most

If the mentor says "show me where X happens", it is almost always one of these. Paths are from the repository root. The longer, folder-by-folder map is `docs/CODE_MAP.md`.

## The 15

### 1. `run_pipeline`: `backend/app/rag/pipeline.py`
**What:** the whole question-answering pipeline, one stage at a time: input guard → hybrid retrieval → rerank → grounding check → generate → output guard. It is a generator: it `yield`s an event after each stage, so the same code drives the streaming UI, the JSON endpoint, the tests and the evaluation.
**In:** `question`, `mode` (`"final"` or `"baseline"` for the evaluation). **Out:** events `step`, `sources`, `delta`, `final` (the `final` event holds the full `AnswerResult`).
**Connects to:** `scan_user_input`, `retrieve`, `unknown_terms`, `router.generate`, `build_prompt`, `filter_output`. Called by `api/ask.py:ask` / `ask_stream` and `eval/run_eval.py`.

### 2. `retrieve`: `backend/app/rag/retriever.py`
**What:** finds the 5 best passages. Final mode: FAISS top 20 + BM25 top 20 → `rrf_fuse` → cross-encoder rerank → top 5. Baseline mode: FAISS only. Can filter by `company_id` and `doc_types` (the agent uses this).
**In:** query, mode, top_k, filters. **Out:** `RetrievalResult` with the scored chunks (every score kept: vector, BM25, RRF, rerank) and timings.
**Connects to:** `IndexStore.vector_search`, `IndexStore.bm25_search`, `rag/models.py:rerank_scores`.

### 3. `rrf_fuse`: `backend/app/rag/retriever.py`
**What:** Reciprocal Rank Fusion. For each passage, add 1 / (60 + its rank) from every list it appears in, then sort. Uses ranks, not scores, so BM25 scores and cosine scores (different scales) never need normalising.
**In:** lists of passage ids in rank order. **Out:** `(id, fused score)` sorted best first.

### 4. `IndexStore`: `backend/app/rag/index.py`
**What:** the search index. `build` loads every document (seed files + uploads), chunks them, embeds them, builds FAISS (`IndexFlatIP`, exact inner product) and BM25, and saves them to `backend/storage/index/`. `ensure` reuses the saved index when the corpus fingerprint is unchanged. `vector_search` and `bm25_search` do the two searches.
**Connects to:** `chunk_document`, `embed`, `set_index` / `get_index` (the live index, swapped atomically after an upload).

### 5. `chunk_document`: `backend/app/rag/chunker.py`
**What:** splits a document at its markdown headings, then packs paragraphs and list items into chunks of about 180 words with a 30-word overlap. Each chunk keeps its heading path; `index_text` (heading + text) is what gets embedded and searched.
**In:** a `SourceDoc`. **Out:** a list of `Chunk`.

### 6. `build_prompt` and `SYSTEM_PROMPT`: `backend/app/rag/prompts.py`
**What:** the six rules (sources only, cite every fact, say `NOT_IN_DOCUMENTS` if missing, brief, exact, never reveal) and the user message with numbered `<source>` blocks and the `<question>`. `_neutralise` swaps angle brackets so a document cannot break out of its tag. Full text in `03_models_prompts_choices.md`.

### 7. `generate`: `backend/app/llm/router.py`
**What:** tries the providers in order (Gemini → local → extractive, starting at `LLM_PROVIDER`). Skips one that is unavailable, raises, or fails the caller's `accept` check. Returns which provider answered and why the others were skipped.
**In:** `LLMRequest` (system, prompt, passages, max tokens), optional `accept` function. **Out:** `LLMResult(text, provider, model, fallbacks)`.

### 8. `scan_user_input`, `sanitize_document_text`, `filter_output`: `backend/app/security/injection.py`
**What:** the three injection defences.
- `scan_user_input`: normalise (Unicode, zero-width characters, "i g n o r e", leetspeak), then match six groups of patterns (instruction override, prompt extraction, role hijack, role spoofing, secret exfiltration, answer forcing). Used on questions **and** on retrieved passages.
- `sanitize_document_text`: removes instruction-like lines from a document at upload and indexing time.
- `filter_output`: canary leak → discard; strip images, HTML and links not in the sources; keep only valid citation numbers.

### 9. `redact_pii`: `backend/app/security/pii.py`
**What:** replaces emails, Indian phone numbers, address lines and LinkedIn/GitHub-style profile links with tokens such as `[PHONE REDACTED]`, and counts each kind. `scrub_for_log` is the lighter version used on log lines and stored questions.
**In:** text. **Out:** `RedactionResult(text, counts, total)`.

### 10. `check_eligibility`: `backend/app/tools/eligibility.py`
**What:** four deterministic checks: CGPA ≥ minimum (compared at 2 decimals), active backlogs ≤ limit, branch in the allowed list, batch equals the drive's batch. Each returns passed, required, actual and a reason. `check_all` runs it for every company.
**In:** `StudentProfileData`, `Company`. **Out:** `EligibilityResult`.

### 11. `match_resume`: `backend/app/tools/resume.py`
**What:** `redact_pii` first, then `extract_skills`, skill score (75% required + 25% preferred), `semantic_similarity` (MiniLM, rescaled), match % = 60% skill + 40% semantic, plus advice.
**In:** resume text, `Company`. **Out:** `ResumeMatch` (match %, matched / missing / extra skills, redaction summary, formula, advice).

### 12. `make_plan`: `backend/app/agent/planner.py`
**What:** the agent's fixed step list for "Prepare me for X": check eligibility, match resume (optional), retrieve selection process, retrieve interview experiences (optional), draft plan, approval gate. Built by rules, not by a model, so it is predictable and testable. If there is no resume, step 2 is planned as skipped.

### 13. `execute_run`: `backend/app/agent/executor.py`
**What:** the agent loop. For each step: check the 8-call budget, call the step function, retry on `StepError` (up to 2 times), then use the fallback, skip if optional, or fail the run. Saves the state after every step. Stops early if the student is not eligible (with alternatives). Ends at the approval gate with the plan in `state.pending`, nothing saved.
**In:** DB session, `AgentRun`, optional `faults` (demo failures). **Out:** events `run`, `plan`, `step`, `approval_required`, `final`.
**Connects to:** `agent/steps.py:STEP_FUNCTIONS` and `FALLBACKS`.

### 14. `approve_run`: `backend/app/agent/executor.py`
**What:** the only place the agent's plan is written. Checks the run belongs to the student and is awaiting approval (else 404 or 409), adds a `PrepPlan`, creates or updates the `Application` via `track_application`, and commits both in **one transaction**. `reject_run` saves nothing.

### 15. `get_current_user` and `require_role`: `backend/app/security/auth.py`
**What:** authentication on every protected route. Reads the `pm_session` cookie, verifies the JWT (`decode_token`), loads the user from the database (so the role comes from the DB, not the token). `require_role("coordinator")` wraps it and returns 403 for the wrong role; `require_student` and `require_coordinator` are the two instances.

### Bonus: `create_app` and `lifespan`: `backend/app/main.py`
Middleware order, routers and error handlers; at start-up: create tables, seed, load or build the index, warm the reranker.

## Where to look for…

| Thing | Where |
|---|---|
| **Config** (every setting and its default) | `backend/app/config.py` (`Settings`); documented in `.env.example`; override in `.env` at the repo root |
| **Logs** | `backend/storage/logs/app.log` (JSON lines, one per request, with `request_id`; emails and phones masked by `PiiScrubFilter` in `backend/app/logging_conf.py`); also the backend's console window |
| **Errors to the user** | `backend/app/errors.py` (one envelope: code, message, request_id) |
| **Database models** | `backend/app/models.py` (User, StudentProfile, Document, Conversation, Message, Application, PrepPlan, AgentRun, Event); the file is `backend/storage/placemate.db` |
| **Request / response shapes** | `backend/app/schemas.py` |
| **Routes** | `backend/app/api/` (`auth`, `ask`, `tools`, `agent`, `applications`, `admin`, `meta`); live list at http://127.0.0.1:8000/docs |
| **Sample data** | `backend/data/` (policy, 12 companies with criteria in front matter, 15 interview write-ups, 6 guides, `students_seed.json`, 3 resumes) |
| **Demo data reset** | `backend/app/seed.py` (`reset_demo_data`), run with `npm run reset-demo` |
| **Backend tests** | `backend/tests/` (one file per area; `conftest.py` forces the extractive provider, so tests never call Gemini) |
| **Frontend tests** | `frontend/e2e/` (`smoke.spec.ts`, `tour.spec.ts`, `screenshots.spec.ts`) |
| **Evaluation** | `eval/cases.json` (47 cases), `eval/run_eval.py`, `eval/metrics.py`, results in `eval/results/`, write-up in `docs/evaluation.md` |
| **Frontend API client** | `frontend/lib/api.ts` (`api`, `streamSSE`) |
| **Frontend pages** | `frontend/app/(app)/<page>/<page>-view.tsx` |
| **UI timings, tour** | `frontend/lib/speed.ts`, `frontend/lib/tour-script.ts` |
| **Theme colours** | `frontend/app/globals.css` (`:root` tokens, dark mode under `[data-theme="dark"]`) |
