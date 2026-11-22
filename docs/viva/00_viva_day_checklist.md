# Viva day checklist

Checked on 2026-11-22: `npm run reset-demo` worked, `npm run dev:all` started both servers in about 22 seconds, both demo logins returned 200, and the full Guided Tour test (`npm run test:tour`, 30 steps in Auto mode with a pause) passed in 2.4 minutes.

## The night before

- [ ] Laptop charged, charger packed. Windows updates done (an update restart during the viva is the worst case).
- [ ] `git pull` on `main` so the code matches GitHub.
- [ ] Run the app once end to end (below). If anything fails, you have time to fix it.
- [ ] Read `01_walkthrough_script.md` out loud once with a timer (aim for 6 minutes).

## Configuration (`.env`)

- This machine has **no `.env` file** in the repo. The Gemini key comes from the Windows environment variable `GEMINI_API_KEY`, which `backend/app/config.py` reads (it also accepts `GOOGLE_API_KEY`).
- Everything else uses the defaults in `backend/app/config.py`, which match `.env.example`.
- If you ever need to change a setting, create `.env` in the repo root (copy `.env.example`) and restart the backend. The backend reads settings once at start-up.

Check the key is visible before the viva:

```powershell
$env:GEMINI_API_KEY.Length    # should print a number, not 0 or nothing
```

## 30 minutes before

```powershell
cd "D:\Internship Projects\placemate-ai"
npm run reset-demo      # clean data: no old questions, runs or uploads
npm run dev:all         # backend opens in its own window; frontend runs here
```

Wait for `Backend ready` and then Next.js `Ready`. Then check:

- http://127.0.0.1:8000/health shows `"ready": true, "documents": 34, "chunks": 227`
- http://localhost:3000 shows the landing page
- Log in with the **Use demo student** button. Ask the policy example once, so the models are warm and you see the **Gemini** badge.
- Then run `npm run reset-demo` again so the demo starts clean (it restarts the backend window for you), or just leave that one question in place.

## What to have open

Browser tabs:
1. http://localhost:3000 (landing page)
2. http://localhost:3000/login
3. http://127.0.0.1:8000/docs (API reference, in case the mentor asks about endpoints)
4. GitHub repo page (README with the results table)

VS Code, files open in tabs (in walkthrough order):
1. `backend/app/rag/pipeline.py` (`run_pipeline`)
2. `backend/app/rag/retriever.py` (`retrieve`, `rrf_fuse`)
3. `backend/app/rag/prompts.py` (`SYSTEM_PROMPT`, `build_prompt`)
4. `backend/app/llm/router.py` (`generate`)
5. `backend/app/tools/eligibility.py` (`check_eligibility`)
6. `backend/app/tools/resume.py` (`match_resume`)
7. `backend/app/agent/executor.py` (`execute_run`, `approve_run`)
8. `backend/app/security/injection.py` and `pii.py`
9. `backend/app/config.py`
10. `docs/evaluation.md`

Two terminals: one running `npm run dev:all`, one free for commands (tests, git, curl).

## Demo logins

| Role | Email | Password |
|---|---|---|
| Student (Ananya, CSE, CGPA 7.8, 1 backlog, batch 2027) | `student@placemate.demo` | `Student@123` |
| Coordinator | `coordinator@placemate.demo` | `Coord@123` |

## Commands you may need during the viva

| Need | Command (repo root unless noted) |
|---|---|
| Start everything | `npm run dev:all` |
| Clean demo data | `npm run reset-demo` |
| All backend tests | `npm run test:backend` (about 1 to 3 minutes) |
| One test file | `cd backend; .\.venv\Scripts\python.exe -m pytest tests\test_eligibility.py` |
| One test by name | `... -m pytest tests\test_rag.py -k refus` |
| Frontend smoke tests | `npm run test:e2e` (servers must be up, about 1 minute) |
| Restart only the backend | close its window, then `cd backend; .\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000` |
| See the backend log | the backend window, or `backend\storage\logs\` |

## Backup plans

**Gemini fails (no internet, quota, slow API).** The app does not break: the router falls back to the local Qwen model, then to the extractive answerer, and the badge shows which one answered. But each question would first wait for Gemini's 30-second timeout. To avoid that wait, switch the default provider before you start:

```powershell
# repo root
"LLM_PROVIDER=extractive" | Out-File -Encoding utf8 .env
# then restart the backend (close its window, run npm run dev:all again)
```

`extractive` answers in about a second with real citations (every word comes from a source). `local` (Qwen 0.5B on CPU) also works offline but takes tens of seconds per answer. Delete `.env` afterwards to go back to Gemini. Say it plainly in the viva: "The internet is down, so I switched to the extractive provider. This is the fallback I designed for exactly this."

**Port already in use.** `dev.ps1` tells you. Close the old backend window, or find the process: `Get-NetTCPConnection -LocalPort 8000 | Select OwningProcess`, then `Stop-Process -Id <id>`.

**Backend window closed by mistake.** Run `npm run dev:all` again; it reuses the running frontend if port 3000 is still up.

**Something looks wrong in the data** (old questions, a duplicate upload). `npm run reset-demo`.

**The live demo fails completely.** Use the screenshots in `screenshots/desktop/` (26 views, numbered in demo order) and the README. Keep the folder open in Explorer as a last resort.

**The Guided Tour gets stuck on a step.** The bar says "This step did not finish in time". Press Next (or →); it carries on. You can also Exit and click through by hand.

## Practice material on the `viva-practice` branch

- The bug drills in `06_diagnose_drills.md` live on the `viva-practice` branch, one commit per bug, tagged `drill-1` to `drill-8`. To practise one bug alone: `git switch -c practice-3 main` then `git cherry-pick drill-3` (the doc explains). `git switch viva-practice` gives all eight at once.
- Always come back with `git switch main` before the viva. **Never present from the practice branch**, it has planted bugs.
