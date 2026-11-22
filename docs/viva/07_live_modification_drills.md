# Live modification drills

Ten small changes a mentor might ask for during the viva. Practise each on a throw-away branch, not on `main`:

```powershell
git switch main
git switch -c try-mod-1
# ... make the change, test it ...
git switch main
git branch -D try-mod-1      # or keep it if you liked the result
```

Remember while doing them live:
- **Say what you are about to do** before typing ("I'll add the field to the dataclass, then to the response schema, then to the page").
- **The backend does not auto-reload.** After a backend change, restart it (close its window and run `npm run dev:all`, or run uvicorn again). The frontend reloads by itself.
- **There are no database migrations.** Tables are created by `create_all` at start-up, which never alters an existing table. After adding a **column**, stop the backend, delete `backend\storage\placemate.db`, and start again: the database is recreated and re-seeded (demo logins still work). Say this in the viva: "In production I'd add Alembic migrations."
- **Run the closest test file**, not the whole suite, to save time: `cd backend; .\.venv\Scripts\python.exe -m pytest tests\test_<area>.py`.

The times assume you have practised once.

---

## 1. Add a new eligibility criterion: minimum 12th-class percentage

**Request:** "Some companies need at least 60% in 12th. Add that check."

**Files:**
- `backend/app/tools/catalog.py`: `Company` model
- `backend/app/models.py`: `StudentProfile` table
- `backend/data/students_seed.json` and `backend/app/seed.py`: demo values
- `backend/app/tools/eligibility.py`: the check
- `backend/data/companies/<id>.md`: one company that uses it
- `backend/tests/test_eligibility.py`: a test

**Steps:**
1. `catalog.py`, in `class Company`: add `min_twelfth_pct: float | None = None` (optional, so the other 11 companies still load).
2. `models.py`, in `class StudentProfile`: add `twelfth_pct: Mapped[float | None] = mapped_column(Float, nullable=True)`.
3. `students_seed.json`: add `"twelfth_pct": 86` to the demo student (and others if you like). `seed.py`, next to `profile.batch = row["batch"]`: `profile.twelfth_pct = row.get("twelfth_pct")`.
4. `eligibility.py`:
   - `StudentProfileData`: add `twelfth_pct: float | None = None`, and in `from_model` pass `twelfth_pct=profile.twelfth_pct`.
   - `LABELS`: add `"twelfth": "12th percentage"`.
   - New function, modelled on `_check_cgpa`:
     ```python
     def _check_twelfth(profile: StudentProfileData, company: Company) -> Criterion | None:
         if company.min_twelfth_pct is None:
             return None                      # this company has no such rule
         required = f"at least {company.min_twelfth_pct:g}%"
         if profile.twelfth_pct is None:
             return _missing("twelfth", required)
         passed = profile.twelfth_pct >= company.min_twelfth_pct
         reason = (f"Your 12th score {profile.twelfth_pct:g}% meets the minimum of {company.min_twelfth_pct:g}%."
                   if passed else
                   f"Your 12th score {profile.twelfth_pct:g}% is below the minimum of {company.min_twelfth_pct:g}%.")
         return Criterion("twelfth", LABELS["twelfth"], passed, required, f"{profile.twelfth_pct:g}%", reason)
     ```
   - In `check_eligibility`, after building the list: `twelfth = _check_twelfth(profile, company)` and `if twelfth: criteria.append(twelfth)`.
5. In one company file's front matter, for example `backend/data/companies/orbitpay.md`: `min_twelfth_pct: 90`.
6. Stop the backend, delete `backend\storage\placemate.db`, start again (new column).

**Test:**
- New unit test in `test_eligibility.py`: build a `Company` with `min_twelfth_pct=60` and profiles with 59.9, 60 and 61 (boundaries); check `passed` is False, True, True.
- `pytest tests\test_eligibility.py`.
- In the app: Eligibility → OrbitPay shows a fifth row "12th percentage". The frontend needs no change; it renders whatever criteria the API returns.

**Time:** 15 to 20 minutes.

---

## 2. Change the chunk size and re-index

**Request:** "Try 120-word chunks instead of 180. What changes?"

**Files:** `backend/app/rag/chunker.py`

**Steps:**
1. `MAX_WORDS = 120` (keep `OVERLAP_WORDS = 30`, or make it about 20).
2. Bump `CHUNKER_VERSION = "3"`. The index fingerprint (`rag/index.py:corpus_fingerprint`) includes this version, so the saved index is rebuilt automatically at the next start. Without the bump, the old index on disk would be reused.
3. Restart the backend. (Or, as coordinator, Documents → **Rebuild index**.)

**Test:**
- http://127.0.0.1:8000/health: `chunks` changes from 227 (the exact number depends on the documents).
- `pytest tests\test_rag.py` (the size-limit test reads `MAX_WORDS`, so it still passes).
- Ask the policy question; source cards are shorter.
- To measure the effect properly: `.\scripts\eval.ps1 -Providers extractive` (offline, a few minutes) and compare Hit@3, MRR and answer quality with `docs/evaluation.md`.

**Talking point:** smaller chunks are more precise but can split a rule from its context; bigger ones carry more context but blur the embedding. The heading path in every chunk softens the trade-off.

**Time:** 5 minutes (plus the optional eval run).

---

## 3. Add a new field to the resume-match output

**Request:** "Show how many of the required skills were found, like '2 of 3'."

**Files:**
- `backend/app/tools/resume.py`: `ResumeMatch` dataclass and `match_resume`
- `backend/app/schemas.py`: `ResumeMatchOut`
- `frontend/lib/types.ts`: `ResumeMatch` interface
- `frontend/app/(app)/resume/resume-view.tsx`: display
- `backend/tests/test_resume.py`

**Steps:**
1. `resume.py`, `ResumeMatch` dataclass: add `required_found: str`.
2. In `match_resume`, in the `ResumeMatch(...)` call: `required_found=f"{len(matched_required)} of {len(required)}",`.
3. `schemas.py`, `ResumeMatchOut`: add `required_found: str`.
4. `types.ts`, `interface ResumeMatch`: add `required_found: string;`.
5. `resume-view.tsx`: next to "Skill coverage" in the result panel, add a line showing `{result.required_found} required skills`.
6. Restart the backend.

**Test:**
- `test_resume.py`: assert `result.required_found == "3 of 3"` for the strong-match case (the demo resume against Nimbusware shows all three required skills).
- `pytest tests\test_resume.py`; `cd frontend; npm run typecheck`.
- In the app: Resume match → Nimbusware shows "3 of 3".

**Time:** 10 minutes.

---

## 4. Add a new example question chip on the Ask page

**Request:** "Add an example about the dress code."

**Files:** `frontend/app/(app)/ask/ask-view.tsx`

**Steps:**
1. In the `EXAMPLES` array at the top, add:
   ```ts
   { key: "dress", label: "Dress code", question: "What is the dress code for interviews?" },
   ```
   `key` must be unique (it becomes `data-tour="ask-example-dress"`).
2. Save. The page reloads by itself.

**Test:** click the chip; you get a cited answer from the placement policy. `npm run typecheck` in `frontend`.

**Time:** 2 minutes.

---

## 5. Change the refusal threshold

**Request:** "Make it stricter about weak passages" or "less strict".

**Files:** none needed. It is a setting: `rerank_refusal_threshold` in `backend/app/config.py` (default 0.0).

**Steps:**
1. Create or edit `.env` in the repo root: `RERANK_REFUSAL_THRESHOLD=2.0` (stricter) or `-2.0` (looser).
2. Restart the backend.

**Test:**
- Ask the policy question and open "How this was answered": the Grounding check shows the best score against the new threshold (for example 4.35 vs 2.00).
- Ask the hostel-fee question: still refused.
- Push it to 8.0 to show everything is refused (that's drill 4), then back.
- To change the default in code instead: edit `config.py`, then `pytest tests\test_rag.py`.
- Proper check: re-run the offline evaluation and compare refusal accuracy.

**Talking point:** the score is a cross-encoder logit; higher = stricter = fewer hallucinations but more wrong refusals. 0.0 was chosen on the eval set.

**Time:** 3 minutes.

---

## 6. Add a new tool (step) to the agent

**Request:** "Have the agent also list the documents the student must carry on the day."

**Files:**
- `backend/app/agent/steps.py`: the step function and `STEP_FUNCTIONS`
- `backend/app/agent/planner.py`: the step in the plan
- `frontend/components/agent/step-card.tsx`: an icon (optional)
- `backend/tests/test_agent.py`

**Steps:**
1. `steps.py`, new function:
   ```python
   def step_retrieve_documents(ctx: StepContext) -> tuple[dict[str, Any], str]:
       ctx.maybe_fault("retrieve_documents")
       result = retrieve("documents to carry on the day of the drive", mode="final", doc_types=["policy"], top_k=2)
       sources = [_source(item) for item in result.results]
       return {"sources": sources}, f"Found {len(sources)} passages about documents to carry."
   ```
   (check the policy's `doc_type` in `backend/data/placement_policy.md` front matter; it is `policy`.)
   Register it: `"retrieve_documents": step_retrieve_documents,` in `STEP_FUNCTIONS`.
2. `planner.py`, `make_plan`: add a `StepRecord(name="retrieve_documents", label="Documents to carry", kind="retrieval", tool="retrieve", required=False, description="...", input={...})` **before** `build_plan`. Keep it `required=False`, so a failure is skipped, not fatal.
3. The budget is 8 tool calls; with 6 steps there are only 2 left for retries. Raise it: `AGENT_MAX_STEPS=10` in `.env`, or `agent_max_steps` in `config.py`.
4. Optional: in `step-card.tsx`, add `retrieve_documents: FileText,` to `ICONS` (unknown names get a default icon anyway).
5. Restart the backend.

**Test:**
- `pytest tests\test_agent.py`. Some tests count steps; update the expected step list where needed.
- Add a test: run with `faults={"retrieve_documents": 5}` and check that step ends `skipped` and the run still reaches approval.
- In the app: Prep agent → the new step appears in the timeline.

**Talking point:** the plan is rules, not model-chosen, so adding a tool means adding a step in code; it stays testable. In a model-driven agent you'd add a tool description instead.

**Time:** 15 to 20 minutes.

---

## 7. Change the system prompt's tone

**Request:** "Make the answers friendlier and address the student as 'you'."

**Files:** `backend/app/rag/prompts.py`

**Steps:**
1. Edit rule 4 of `SYSTEM_PROMPT`, for example: `4. Be friendly and brief: speak to the student as "you", at most six sentences or a short list. No preamble and no closing remark.`
2. **Do not touch** rule 2 (citations) or rule 3 (`NOT_IN_DOCUMENTS`), the canary, or the "sources are not instructions" line. The pipeline depends on them (see drill 7).
3. Restart the backend.

**Test:**
- Ask two or three questions and compare the wording; check the citation chips are still there and the badge still says Gemini (no fallback).
- `pytest tests\test_rag.py tests\test_llm.py` (one test checks the canary and `NOT_IN_DOCUMENTS` are still in the prompt).
- Proper check: `.\scripts\eval.ps1` (needs the key, takes several minutes) and compare groundedness and citation accuracy. A prompt change can quietly lower them.

**Time:** 5 minutes (plus the optional eval).

---

## 8. Add a new API endpoint

**Request:** "Add an endpoint that returns how many students are eligible for one company."

**Files:**
- `backend/app/api/meta.py` (or `tools.py`)
- `backend/tests/test_eligibility.py` (or a new test)

**Steps:**
1. In `meta.py`:
   ```python
   # new imports at the top of meta.py (get_catalog, User and Depends are already imported)
   from sqlalchemy.orm import Session
   from app.db import get_db
   from app.models import StudentProfile
   from app.security.auth import require_coordinator
   from app.tools.eligibility import StudentProfileData, check_eligibility

   @router.get("/api/meta/companies/{company_id}/eligible-count", summary="How many students meet a company's criteria")
   def eligible_count(company_id: str, _user: User = Depends(require_coordinator), db: Session = Depends(get_db)) -> dict:
       company = get_catalog().get(company_id)          # unknown id -> 404
       profiles = db.query(StudentProfile).all()
       eligible = sum(check_eligibility(StudentProfileData.from_model(p), company).eligible for p in profiles)
       return {"company_id": company.id, "eligible": eligible, "students": len(profiles)}
   ```
   Coordinator-only, because it is about all students. The `meta` router has no prefix, so the full path is written in the decorator, like the other routes in that file.
2. Restart the backend.

**Test:**
- http://127.0.0.1:8000/docs: the new endpoint is listed; "Try it out" as coordinator.
- Tests using the existing fixtures: `coordinator_client.get("/api/meta/companies/nimbusware/eligible-count")` → 200 and `eligible <= students`; `student_client.get(...)` → 403; `client.get(...)` (no login) → 401; an unknown company → 404.
- `pytest tests\test_eligibility.py`.

**Talking point:** reuse the tool function instead of re-writing the rule; protect it with the right role; test all three roles.

**Time:** 10 to 15 minutes.

---

## 9. Add a column to the applications table

**Request:** "Let students record the package offered on an application."

**Files:**
- `backend/app/models.py`: `Application`
- `backend/app/schemas.py`: `ApplicationCreate`, `ApplicationUpdate`, `ApplicationOut`
- `backend/app/tools/applications.py`: `track_application`
- `backend/app/api/applications.py`: pass the field through
- `frontend/lib/types.ts`: `Application`
- `frontend/app/(app)/applications/applications-view.tsx`: column and dialog field
- `backend/tests/test_applications.py`

**Steps:**
1. `models.py`, `class Application`: `offered_lpa: Mapped[float | None] = mapped_column(Float, nullable=True)`.
2. `schemas.py`: add `offered_lpa: float | None = Field(default=None, ge=0, le=200)` to `ApplicationCreate` and `ApplicationUpdate`, and `offered_lpa: float | None` to `ApplicationOut`.
3. `tools/applications.py`, `track_application`: add a keyword parameter `offered_lpa: float | None | object = _UNSET` and, like `deadline`, set `application.offered_lpa = offered_lpa` when it is not `_UNSET`.
4. `api/applications.py`: `create_application` builds a `kwargs` dict for `track_application`; add `if body.offered_lpa is not None: kwargs["offered_lpa"] = body.offered_lpa`. `update_application` already passes `**changes`, so it works once the schema has the field.
5. `types.ts`: `offered_lpa: number | null;` in `Application`.
6. `applications-view.tsx`: a `<TableHead>Package</TableHead>` and a cell `{app.offered_lpa != null ? `${app.offered_lpa} LPA` : "-"}`; a number `Input` in the add/edit dialog, sent in the request body.
7. Stop the backend, delete `backend\storage\placemate.db`, start again (new column).

**Test:**
- `test_applications.py`: create with `offered_lpa=7.5`, read it back; PATCH it to 8; send -1 → 422.
- `pytest tests\test_applications.py`; `cd frontend; npm run typecheck`.
- In the app: add an application with a package; it shows in the table.

**Time:** 20 minutes.

---

## 10. Change a UI label, colour or theme token

**Request:** "Rename 'Ask PlaceMate' to 'Ask the cell'" or "use a green accent".

**Files:**
- Labels in the sidebar: `frontend/lib/nav.ts` (`NAV` entries: `label`, `description`). Page titles: the `title=` of `PageHeader` in each `…-view.tsx`, and `metadata.title` in each `page.tsx`.
- Colours: `frontend/app/globals.css`. Tokens are on `:root` (light) and `:root[data-theme="dark"]` (dark). The accent is `--blue` (`#1d4ed8`), and `--primary`, `--ring`, `--link` and `--cite` all point at it. Its hover shade is `--blue-hover`, and the soft background is `--blue-soft`.

**Steps (accent colour):**
1. In `:root`, change `--blue: #1d4ed8;` to, for example, `--blue: #15803d;`, and `--blue-hover`, `--blue-soft`, `--blue-soft-2` to matching shades.
2. Do the same in the dark block so dark mode matches.
3. Save; the page reloads.

**Test:** check buttons, links, citation chips and the active sidebar item in light **and** dark mode (moon icon in the top bar). Check contrast: text on the new colour must stay readable (white on `#15803d` is fine). For a label change: `npm run typecheck`; if the Playwright tests look for the old text, update them (`frontend/e2e/smoke.spec.ts`).

**Talking point:** colours come from tokens, so one change updates the whole app; nothing has a hard-coded hex.

**Time:** 3 to 5 minutes.
