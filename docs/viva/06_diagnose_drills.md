# Diagnose drills

Eight realistic bugs are planted on the branch **`viva-practice`**, one commit each, tagged `drill-1` to `drill-8`. The commit messages sound harmless on purpose, as real ones do. **`main` is never touched.**

For each drill, read only the **Symptom**, then find and fix the bug yourself. The solution is folded away below it; open it only after you have tried (aim for 10 minutes each).

## How to practise one drill on its own

The commits on `viva-practice` build on each other, so the branch tip has all eight bugs at once (that's the "hard mode"). To get **only one** bug, put it on a copy of `main`:

```powershell
cd "D:\Internship Projects\placemate-ai"
git switch main
git switch -c practice-3        # any name
git cherry-pick drill-3         # now only bug 3 is in the code
# restart the backend (close its window, run npm run dev:all) - it does not reload code by itself
# ... find it, fix it, run the tests ...
git switch main
git branch -D practice-3        # throw the practice copy away
```

Before the viva: `git switch main` and check `git status` is clean. **Never demo from a practice branch.**

## General debugging checklist

Use the same order every time, and say the steps out loud in the viva; mentors like to hear a method.

1. **Read the error message fully.** The last line of a Python traceback says *what*; the lines above say *where* (file and line). In the browser, read the message on screen and the browser's Network tab (status code and response).
2. **Check the logs.** Backend: its console window, or `backend/storage/logs/app.log` (JSON lines; find the `request_id` shown in the error envelope). Each request logs method, path, status and duration.
3. **Reproduce it on purpose,** with the smallest input: one question, one curl call, one test. If you can't reproduce it, you can't confirm the fix.
4. **Run the tests for that area.** `cd backend; .\.venv\Scripts\python.exe -m pytest tests\test_<area>.py` (`-k name` for one test, `-x` to stop at the first failure). A failing test usually points straight at the function.
5. **Check what changed recently.** `git log --oneline -5`, `git diff main` (on a practice branch), `git show <commit>`. Most bugs come from the last change.
6. **Look inside.** Add a `print()` or a `logger.info(...)`, use the VS Code debugger with a breakpoint, or call the function directly in a Python shell (`cd backend; .\.venv\Scripts\python.exe`). Check the values you *think* you have.
7. **Fix the cause, not the symptom.** For example, don't lower a test's expectation to make it pass.
8. **Re-test:** the failing test, then the whole area, then the feature in the app. Then commit with a clear message.

Useful one-liners:

```powershell
# Is the backend up? Which documents and chunks?
curl.exe http://127.0.0.1:8000/health
# Which LLM providers are available? (needs a login cookie; easier: the Ask page's "How this was answered")
# Does an endpoint exist? Status code only:
curl.exe -s -o NUL -w "%{http_code}" -X POST http://127.0.0.1:8000/api/tools/eligibility
# Search the code
git grep -n "rerank_refusal_threshold"
```

---

## Drill 1

**Symptom.** Every answer still appears, but slowly (20 to 60 seconds), and the badge under "How this was answered" says **Local model** (sometimes **Extractive**) instead of Gemini. The Generate step's detail mentions a fallback. `$env:GEMINI_API_KEY` is set and the key works. All backend tests pass.

<details>
<summary>Solution</summary>

**Cause.** `backend/app/config.py` reads the key with `validation_alias=AliasChoices("GEMINI_KEY", "GOOGLE_GEMINI_KEY")`. The environment variable is `GEMINI_API_KEY`, so the setting stays empty, `GeminiProvider.available()` returns "no API key", and the router falls back to the local model.

**How to find it.** Open "How this was answered": the Generate step says *Fell back after: gemini: no API key*. So the app does not see the key. Search where the key is read: `git grep -n "gemini_api_key" backend/app` → `config.py`. Check what the app actually loads:
```powershell
cd backend; .\.venv\Scripts\python.exe -c "from app.config import Settings; print(len(Settings().gemini_api_key))"   # prints 0
```
`git log -p -1 -- backend/app/config.py` shows the alias change. Tests pass because `conftest.py` blanks the key on purpose and the Gemini tests set the attribute directly.

**Fix.** `AliasChoices("GEMINI_API_KEY", "GOOGLE_API_KEY")`, the names in `.env.example`. Restart the backend; the badge says Gemini again.

**Lesson.** Configuration names must match across `.env.example`, the code and the docs. A test that loads settings from a fake environment would catch this.
</details>

## Drill 2

**Symptom.** `npm run dev:all` prints *"The backend did not answer within 4 minutes"*. The backend window shows a red traceback and closes or sits at a prompt. Running the tests fails before any test runs.

<details>
<summary>Solution</summary>

**Cause.** `backend/app/api/tools.py` imports `check_eligibilty` (missing "i"), which does not exist in `app/tools/eligibility.py`, and calls it under that name.

**How to find it.** The last line of the traceback: `ImportError: cannot import name 'check_eligibilty' from 'app.tools.eligibility'`. The line above shows the file: `app/api/tools.py`. pytest says the same: *ImportError while loading conftest*. Quick check without starting the server: `cd backend; .\.venv\Scripts\python.exe -c "import app.main"`.

**Fix.** Import and call `check_eligibility`. Restart.

**Lesson.** Read the *last* line of the traceback first. An import error stops the whole app, because `main.py` imports every router at start-up.
</details>

## Drill 3

**Symptom.** The seeded documents look fine. But when the coordinator uploads a long notice (a section well over 180 words), its source cards on the Ask page are very long and repeat the same sentences. One RAG test fails.

<details>
<summary>Solution</summary>

**Cause.** In `backend/app/rag/chunker.py:_pack`, the overlap carried into the next chunk is `split()[OVERLAP_WORDS:]` (everything *except* the first 30 words) instead of `split()[-OVERLAP_WORDS:]` (the *last* 30 words). The next chunk starts with almost the whole previous chunk, but `count` is still set to 30, so chunks grow past the 180-word limit and repeat text.

**How to find it.** `pytest tests\test_rag.py` → `test_long_sections_are_split_within_the_size_limit` fails. That points at chunking. Read `_pack` and look at the overlap line; `git diff main -- backend/app/rag/chunker.py` shows a one-character change (the missing minus). Check by hand:
```python
from app.rag.chunker import _pack
blocks = [" ".join(f"w{i}" for i in range(100)) for _ in range(3)]   # three 100-word paragraphs
[len(c.split()) for c in _pack(blocks)]   # correct: [100, 131, 131]   with the bug: [100, 171, 242]
```
Why the seed documents look fine: their sections are short (the longest chunk is 129 words), so the overlap code rarely runs. Also, the saved index is only rebuilt when the documents or `CHUNKER_VERSION` change, so a chunker change does not show until a re-index.

**Fix.** `split()[-OVERLAP_WORDS:]`. Then bump `CHUNKER_VERSION` (or press **Rebuild index** on the Documents page) so the index is rebuilt with the fixed chunker.

**Lesson.** Slicing with and without a minus sign is a classic off-by-one-style bug. Size limits need a test with long input, which is why that test exists.
</details>

## Drill 4

**Symptom.** Every question, even "Can I sit for another company after I get placed?", gets *"I could not find this in the placement documents, so I will not guess."* The answer comes back instantly. Several RAG tests fail.

<details>
<summary>Solution</summary>

**Cause.** `backend/app/config.py`: `rerank_refusal_threshold = 8.0`. The cross-encoder's best scores are around 2 to 6 for good passages, so nothing passes and everything is refused before the model is called.

**How to find it.** Open "How this was answered": the Grounding check says *Best passage score 4.35 is below the threshold 8.00. No model was called.* So retrieval worked; the threshold is wrong. `git grep -n "rerank_refusal_threshold"` → `config.py`. Tests: `pytest tests\test_rag.py` (8 failures).

**Fix.** Back to `0.0` (the value chosen on the evaluation set). It can also be set without code: `RERANK_REFUSAL_THRESHOLD=0.0` in `.env`.

**Lesson.** The UI's step details are a debugging tool: "instant answer + refusal" means the model was never called, so look before generation.
</details>

## Drill 5

**Symptom.** The demo student (CGPA 7.8, **1 active backlog**) is suddenly *Not eligible* for Nimbusware, which allows one backlog. The dashboard lists fewer companies, and the prep agent for Nimbusware stops at step 1. Many eligibility and agent tests fail.

<details>
<summary>Solution</summary>

**Cause.** `backend/app/tools/eligibility.py:_check_backlogs` uses `count < limit`. It must be `count <= limit`: "at most 1" means 1 is allowed.

**How to find it.** The eligibility page shows the reason: the backlogs row fails with 1 against a limit of 1. Open `_check_backlogs`. `pytest tests\test_eligibility.py` → `test_backlog_boundaries[1-1-True]` (and the 0-0 and 2-2 cases) fail: exactly the boundary values. The agent tests fail only because their student is now ineligible.

**Fix.** `passed = count <= limit`.

**Lesson.** Boundary values (exactly equal) are where comparison bugs hide; that is why the test checks `limit - 1`, `limit` and `limit + 1`. One wrong operator can break many tests downstream; fix the first, deepest one.
</details>

## Drill 6

**Symptom.** The app looks normal. But the **Security** page's "Role checks on every admin route" **Try it** reports *Not protected*, and `curl.exe http://127.0.0.1:8000/api/admin/analytics` with **no login at all** returns 200 and the analytics data. One admin test fails.

<details>
<summary>Solution</summary>

**Cause.** `backend/app/api/admin.py`: the router lost `dependencies=[Depends(require_coordinator)]`. Upload, delete and reindex still check the role on the route itself, but `GET /documents`, `GET /analytics` and `GET /logs` now have no check: anyone, even a visitor, can read them.

**How to find it.** `pytest tests\test_admin.py` → `test_every_admin_route_requires_the_coordinator` fails and names the paths that returned 200. Open `admin.py`; compare the routes that still have `Depends(require_coordinator)` with those that don't. `git log -p -1 -- backend/app/api/admin.py`.

**Fix.** Put `dependencies=[Depends(require_coordinator)]` back on the `APIRouter(...)`, so *every* route in the file is protected by default.

**Lesson.** The frontend hiding a page is not security; only the backend check counts. Protecting the whole router, plus a test that walks every admin path in the OpenAPI schema, means a new route can't be forgotten.
</details>

## Drill 7

**Symptom.** Answers still appear and look right, with citation chips, but they are slow (several seconds to over a minute) and the badge says **Extractive** instead of Gemini. Gemini is reachable and the key is fine. All backend tests pass.

<details>
<summary>Solution</summary>

**Cause.** In `backend/app/rag/prompts.py` the citation rule ("Put the source number in square brackets after every sentence…") was removed from `SYSTEM_PROMPT`, and "with a citation after each fact" from the end of `build_prompt`. Gemini now answers without `[n]` citations. The pipeline's `accept` check rejects any answer with no valid citation, so the router moves on: Gemini rejected, local model rejected, extractive (which always cites) answers.

**How to find it.** "How this was answered" → Generate: *Fell back after: gemini: answer had no valid citation; local: answer had no valid citation.* So the models answered, but their answers failed a check. Find the message: `git grep -n "answer had no valid citation"` → `rag/pipeline.py` (`accept`). Why would there be no citation? Look at the prompt that asks for them: `git log -p -- backend/app/rag/prompts.py`. Tests pass because they use the extractive provider, which never reads the prompt.

**Fix.** Restore rule 2 (and renumber), and the "with a citation after each fact" line.

**Lesson.** A prompt is code: changes to it need a review and an evaluation run (`scripts\eval.ps1`), because unit tests with a fake model don't notice. The fallback chain hid the problem from users (they still got cited answers) but showed it in the step details.
</details>

## Drill 8

**Symptom.** On the **Eligibility** page, picking any company (or an example chip) shows an error box saying **"Not Found"** with a Retry button. **Check all companies** still works. The backend window shows `POST /api/eligibility … 404`.

<details>
<summary>Solution</summary>

**Cause.** `frontend/app/(app)/eligibility/eligibility-view.tsx` calls `api("/api/eligibility", …)`. The real endpoint is `/api/tools/eligibility` (`backend/app/api/tools.py`, router prefix `/api/tools`). "Check all" uses `/api/tools/eligibility/all`, which is still right.

**How to find it.** Browser DevTools → Network: the request is `POST http://localhost:8000/api/eligibility` → 404, response `{"error":{"code":"not_found","message":"Not Found",…}}`. Compare with http://127.0.0.1:8000/docs, which lists `POST /api/tools/eligibility`. Search the frontend: `git grep -n "/api/eligibility" frontend`.

**Fix.** Back to `/api/tools/eligibility`. Next.js reloads the page by itself; no restart needed.

**Lesson.** A 404 from your own backend means the path is wrong, not the data. Check the Network tab, then `/docs`. The Playwright smoke test (`npm run test:e2e`, the eligibility test) would also catch this.
</details>

---

## Quick reference: all eight at once (hard mode)

`git switch viva-practice` puts all eight bugs in the code together. Start the app and work through the symptoms in order: drill 2 stops the backend from starting at all, so it comes first. Then:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -x     # stop at the first failure, fix, run again
```

`git diff main --stat` lists every file that differs, if you get stuck.
