# Architecture and data flow

All paths are from the repository root. `file:function` means "the function `function` in that file".

## The picture

```
 Browser (Next.js 16, React)                           frontend/
   pages in frontend/app/(app)/*/…-view.tsx
   frontend/lib/api.ts  → fetch(…, credentials: "include")   (cookie goes along)
        │   JSON requests,  answers stream back as server-sent events (SSE)
        ▼
 ┌──────────────────────── FastAPI backend  (backend/app/main.py:create_app) ────────────────────────┐
 │ Edge middleware, every request:                                                                     │
 │   CORS (only http://localhost:3000) → security headers → request id + JSON log line                 │
 │   → origin check (no cross-site POST/PATCH/DELETE) → rate limit (login 10, demo probe 5, API 120/min)│
 │                                                                                                     │
 │ Routes (backend/app/api/*.py): validate body (Pydantic), load user from cookie, check role          │
 │      │                    │                         │                          │                   │
 │      ▼                    ▼                         ▼                          ▼                   │
 │  RAG pipeline         Tools (plain Python)      Prep agent                 Coordinator             │
 │  rag/pipeline.py      tools/eligibility.py      agent/executor.py          api/admin.py            │
 │  rag/retriever.py     tools/resume.py           agent/steps.py             services/analytics.py   │
 │  llm/router.py        tools/applications.py     (calls tools + retriever)  rag/index.py (rebuild)  │
 │      │                                                                                              │
 │      ├─ Search index: FAISS (vectors) + BM25 (keywords)   backend/storage/index/                    │
 │      └─ LLM: Gemini → local Qwen 0.5B → extractive        backend/app/llm/                          │
 │                                                                                                     │
 │ Database: SQLite  backend/storage/placemate.db  (users, profiles, documents, conversations,         │
 │           messages, applications, prep_plans, agent_runs, events)                                   │
 └─────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

Start-up (`backend/app/main.py:lifespan`): create tables → seed demo users if the DB is empty (`app/seed.py:seed_demo_data`) → load the saved search index, or build it if the documents changed (`app/rag/index.py:IndexStore.ensure`) → warm the reranker with one dummy call, so the first real question is not slow.

The same edge applies to every flow below, so it is not repeated.

---

## 1. Ask a question (RAG)

**Request:** the Ask page (`frontend/app/(app)/ask/ask-view.tsx:ask`) calls `streamSSE("/api/ask/stream", {question, conversation_id?})` from `frontend/lib/api.ts`.

**Endpoint:** `POST /api/ask/stream` → `backend/app/api/ask.py:ask_stream` (any logged-in user, via `get_current_user`). The body is `AskRequest` (question 1 to 2000 characters).

**Functions, in order** (all in `backend/app/rag/pipeline.py:run_pipeline` unless noted):

1. **Input guard** `security/injection.py:scan_user_input`. Normalises the text (Unicode, zero-width characters, spaced letters, leetspeak) and matches the injection patterns. If blocked: answer = a fixed message, stop. No retrieval, no model.
2. **Hybrid retrieval** `rag/retriever.py:retrieve(mode="final")`:
   - `IndexStore.vector_search` (FAISS, MiniLM embeddings) → top 20
   - `IndexStore.bm25_search` (rank-bm25 over tokenised text) → top 20
   - `rrf_fuse` merges the two ranked lists: score = Σ 1 / (60 + rank)
3. **Rerank** `rag/models.py:rerank_scores` (cross-encoder) scores all fused candidates against the question; keep the top 5. Each kept passage is scanned again with `scan_user_input`; one with instructions inside is dropped.
4. **Grounding check:**
   - `unknown_terms`: a capitalised name or acronym in the question that appears in no document (for example "Google") → refuse.
   - best rerank score < `rerank_refusal_threshold` (0.0) → refuse.
   - A refusal costs no model call.
5. **Generate** `llm/router.py:generate` with `SYSTEM_PROMPT` and `rag/prompts.py:build_prompt(question, passages)`. Tries Gemini → local → extractive. Each answer must pass `accept` (no canary, at least 5 words, no prompt markup, at least one valid citation) or the router moves to the next provider.
6. **Output guard** `security/injection.py:filter_output`: discard if the canary leaked; strip images, HTML, links not in the sources; keep only citation numbers 1 to 5.
7. Events are yielded after each step: `step`, `sources`, `delta` (answer text), `final`.

**Stored** (`api/ask.py:_persist`): a `Conversation` (title = first 80 characters of the question), two `Message` rows (user question; assistant answer with sources, steps, provider and latency in `meta`), and one `Event` (`ask`, `ask_refused` or `ask_blocked`, with the question scrubbed of emails and phones by `security/pii.py:scrub_for_log`).

**Response:** SSE events. The page shows the steps one by one ("How this was answered"), the answer with citation chips (`components/ask/answer-text.tsx`), source cards and the provider badge.

---

## 2. Eligibility check (tool)

**Request:** `eligibility-view.tsx` reads `?company=orbitpay` from the URL and posts `{company_id}`.

**Endpoint:** `POST /api/tools/eligibility` → `backend/app/api/tools.py:eligibility` (students only, `require_student`). "Check all" uses `POST /api/tools/eligibility/all` → `eligibility_all`.

**Functions:**
1. `tools/catalog.py:get_catalog().get(company_id)` loads the company's criteria from the YAML front matter of `backend/data/companies/<id>.md` (`min_cgpa`, `max_active_backlogs`, `allowed_branches`, `batch`).
2. `tools/eligibility.py:StudentProfileData.from_model(user.profile)` takes branch, CGPA, active backlogs and batch from the database.
3. `tools/eligibility.py:check_eligibility` runs `_check_cgpa` (CGPA ≥ minimum, compared at 2 decimals), `_check_backlogs` (count ≤ limit), `_check_branch` (branch in the allowed list), `_check_batch` (batch equals the drive's batch). Eligible = all four pass. A missing profile field fails that criterion with a clear message instead of a guess.

**Stored:** one `Event` (`eligibility_check`) for analytics. Nothing else.

**Response:** `EligibilityOut`: eligible, and for each criterion: passed, required, actual, reason. The page animates the four rows.

---

## 3. Resume match (tool)

**Request:** `resume-view.tsx`: **Use my saved resume** (`GET /api/tools/resume`), upload (`POST /api/tools/resume-extract`, text only, nothing stored) or paste; then **Match** posts `{company_id, resume_text?, save_to_profile?}`.

**Endpoint:** `POST /api/tools/resume-match` → `backend/app/api/tools.py:resume_match` (students). With no `resume_text`, the saved profile resume is used.

**Functions** (`backend/app/tools/resume.py:match_resume`):
1. `security/pii.py:redact_pii` removes emails, Indian phone numbers, address lines and profile links. **Everything after this line uses only the redacted text.**
2. `tools/skills.py:extract_skills` finds known skills (with aliases).
3. Skill score = 75% × (required skills found / required) + 25% × (preferred found / preferred).
4. `semantic_similarity`: embeds resume chunks and job-description chunks with MiniLM; for each JD chunk takes its best resume chunk; averages; maps the range 0.15 to 0.60 onto 0 to 1.
5. Match % = 60% × skill score + 40% × semantic score, rounded.
6. `_advice` writes tips (missing required skill → the prep guide to read).

**Stored:** one `Event` (`resume_match`); the resume text itself is saved to the profile only if `save_to_profile` is true and text was pasted.

**Response:** `ResumeMatchOut`: match %, both scores, matched / missing / extra skills, the redaction counts and a redacted preview ("what the model saw"), the formula, advice.

---

## 4. Prep agent with approval

**Request:** `agent-view.tsx` posts `{company_id, demo_fault?}` to `POST /api/agent/runs/stream`.

**Endpoint:** `backend/app/api/agent.py:create_run_stream` (students).

**Functions:**
1. `agent/executor.py:start_run` creates an `AgentRun` row (status `running`) with a state from `agent/planner.py:make_plan`: six steps, fixed by rules (not chosen by a model):

   | # | Step | Kind | Required | On failure |
   |---|---|---|---|---|
   | 1 | `check_eligibility` | tool | yes | (not eligible → run ends, alternatives shown) |
   | 2 | `match_resume` | tool | no | skipped |
   | 3 | `retrieve_process` | retrieval | yes | fallback: rounds from the company profile |
   | 4 | `retrieve_experiences` | retrieval | no | skipped |
   | 5 | `build_plan` | llm | yes | fallback: template summary |
   | 6 | `approval` | gate | yes | waits for the student |

2. `agent/executor.py:execute_run` loops over the steps. For each: check the budget (8 tool calls, retries included) → `tool_calls += 1` → call `agent/steps.py:STEP_FUNCTIONS[name]` → on `StepError` retry (up to 2 retries) → then fallback (`FALLBACKS`), skip (optional step) or fail the run (required, no fallback). **The state is saved to `agent_runs.state` after every step** (`_save`).
   - `step_retrieve_process` calls `retrieve(..., company_id=…, doc_types=["company"], top_k=3)`.
   - `step_build_plan` builds the weeks with `agent/plan_builder.py:build_prep_plan` (rules: skill gaps first, one topic per round, mock interviews last, 2 to 4 weeks from the deadline), then asks the LLM router for a short cited summary using the same `SYSTEM_PROMPT`.
3. At the gate: `run.status = "awaiting_approval"`, the plan and the application are kept in `state.pending`, event `approval_required`. **Nothing is written to the plans or applications tables yet.**
4. The student clicks **Approve** → `POST /api/agent/runs/{id}/approve` → `executor.py:approve_run`: checks the run is the student's own and awaiting approval, then adds a `PrepPlan` and creates or updates the `Application` (`tools/applications.py:track_application`), and commits **both in one transaction**. A second approve gets 409. **Reject** → `reject_run`: nothing saved.

**Stored:** `agent_runs` (state after each step), and on approve `prep_plans` + `applications`; events `agent_approved` / `agent_rejected`.

**Response:** SSE events `run`, `plan`, `step` (many), `approval_required`, `final`. The page shows the timeline, the run-state panel (tool calls used, recoveries) and the approval dialog.

---

## 5. Document upload and re-index (coordinator)

**Request:** `documents-view.tsx` sends multipart `file` to `POST /api/admin/documents`.

**Endpoint:** `backend/app/api/admin.py:upload_document`. The whole `/api/admin` router has `dependencies=[Depends(require_coordinator)]`.

**Functions:**
1. `security/uploads.py:read_limited` reads in 64 KB pieces and stops past 5 MB → 413.
2. `security/uploads.py:validate_bytes`: extension `.md` / `.txt` / `.pdf` (415), real content (a `.pdf` must start with `%PDF-`; a text file must not look like a binary), at least 40 characters of text; `sanitize_filename`; a random prefix for the stored name.
3. SHA-256 checksum: the same file again → 409 duplicate.
4. The file is written to `backend/storage/uploads/`.
5. `rag/loader.py:build_source_doc` reads the front matter, cleans the text and runs `security/injection.py:sanitize_document_text`, which **removes instruction-like lines** and returns them.
6. A `Document` row is saved, then `_reindex` → `rag/index.py:IndexStore.build`: load all documents, `rag/chunker.py:chunk_document` (about 180 words, 30-word overlap, heading kept), embed with MiniLM, build FAISS + BM25, save to `backend/storage/index/`, swap the live index (`set_index`). If re-indexing fails, the upload is rolled back.

**Stored:** the file, a `documents` row (with `removed_lines`), the new index, a `document_upload` event (or `document_upload_rejected`).

**Response:** `UploadOut`: the document, the re-index stats (documents, chunks, time) and the removed lines, which the page shows struck through.

---

## 6. Login and auth

**Request:** `frontend/app/login/login-form.tsx:submit` → `useAuth().login` (`frontend/lib/auth.tsx`) → `POST /api/auth/login` with `{email, password}`.

**Endpoint:** `backend/app/api/auth.py:login`.

**Functions:**
1. `security/auth.py:authenticate`: find the user by email (case-insensitive) and `verify_password` with argon2id. For an unknown email it still verifies against a dummy hash, so the response time does not reveal which emails exist.
2. `create_token`: a JWT (HS256) with `sub` = user id, `role`, `iat`, `exp` (8 hours).
3. `set_session_cookie`: cookie `pm_session`, `HttpOnly`, `SameSite=Lax`.
4. `events.log_event(LOGIN)`; a failed login logs `login_failed` and returns 401 with the same message for both cases.

**On every later request:** `security/auth.py:get_current_user` reads the cookie → `decode_token` (bad signature or expired → 401) → loads the user from the DB, so the **role comes from the database, not the token**. `require_student` / `require_coordinator` (`require_role`) return 403 for the wrong role.

**Frontend side:** on page load `AuthProvider` calls `GET /api/auth/session` (always 200, `user: null` for visitors). `frontend/components/shell/app-shell.tsx` redirects visitors to `/login?next=…` and shows a 403 view for the wrong role. `frontend/proxy.ts` does a quick cookie-present check before rendering. The real check is always the backend.

**Stored:** nothing except the `login` / `login_failed` event. Sessions are stateless (no session table).

**Response:** the user (`UserOut`) plus the `Set-Cookie` header. `homeFor` sends a student to `/dashboard` and a coordinator to `/analytics`.
