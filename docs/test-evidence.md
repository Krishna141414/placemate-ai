# Test evidence

What was run, how to run it again, and what it produced. Figures in the generated blocks are written by `eval/report.py` from `eval/results/tests.json` and the evaluation summaries; the raw outputs are in `docs/evidence/`.

## 1. Commands

All from the repository root in PowerShell, after `.\scripts\setup.ps1`.

| What | Command | Output |
|---|---|---|
| Backend tests + coverage | `.\scripts\test.ps1` | `docs/evidence/pytest-output.txt`, `pytest-junit.xml`, `coverage.json`, summary in `eval/results/tests.json` |
| Fast backend tests (skip the local LLM) | `.\scripts\test.ps1 -m "not slow"` | same |
| Evaluation, Gemini + offline | `.\scripts\eval.ps1` | `eval/results/<provider>/` (cases, summary, charts, run log) |
| Evaluation, offline only | `.\scripts\eval.ps1 -Providers extractive` | `eval/results/extractive/` |
| Rewrite the tables in the docs | `backend\.venv\Scripts\python.exe eval\report.py` | `docs/evaluation.md`, this file |
| Frontend smoke tests | `cd frontend; npx playwright test` | added in Phase 9 |

Tests never call the Gemini API: `backend/tests/conftest.py` sets `LLM_PROVIDER=extractive`, clears the key, and uses a throw-away database and index in a temporary folder. The one slow test loads the real cached `Qwen2.5-0.5B-Instruct` and generates on CPU.

## 2. Backend tests (pytest)

<!-- eval:tests:start -->
**369 passed, 0 failed, 0 skipped** in 248.1 s (run at 2026-11-19T16:21:33.724248+05:30). Line coverage of `backend/app`: **96.0%** (3203 of 3337 statements).

| Test file | Tests |
|---|---:|
| `test_admin.py` | 29 |
| `test_agent.py` | 32 |
| `test_applications.py` | 15 |
| `test_ask_api.py` | 15 |
| `test_auth.py` | 20 |
| `test_eligibility.py` | 35 |
| `test_injection.py` | 67 |
| `test_llm.py` | 24 |
| `test_pii.py` | 26 |
| `test_rag.py` | 57 |
| `test_resume.py` | 31 |
| `test_security_http.py` | 18 |
<!-- eval:tests:end -->

What the suites cover, mapped to the brief:

| Area | Files | Examples of what is checked |
|---|---|---|
| Tools | `test_eligibility.py`, `test_resume.py`, `test_applications.py` | CGPA exactly at the cut-off passes and 0.01 below fails; float noise cannot flip a verdict; 0/1/2 backlog limits; case-insensitive branch; wrong batch; missing profile fields reported, not guessed; skill extraction without false positives (Java vs JavaScript, C vs C#, the ECE branch name); the published score formula; upsert without duplicates; another student's application is a 404 |
| API | `test_auth.py`, `test_security_http.py`, `test_ask_api.py` | login, logout, expired and forged tokens, role taken from the database not the token, 401 vs 403, validation errors that never echo input, 429 with `Retry-After`, CORS, origin check, error envelope, no stack trace on a crash, SSE event order |
| RAG | `test_rag.py`, `test_llm.py` | chunking keeps heading paths; RRF arithmetic; the policy, company and guide questions retrieve the right document; off-topic and unknown-company questions are refused without calling a model; fallback chain gemini, local, extractive with reasons; uncited, empty or markup-echoing answers rejected; invalid citations stripped; index rebuilt when deleted |
| Agent | `test_agent.py` | happy path stops at the gate with nothing saved; approve saves plan and application once; double approve is 409; reject saves nothing; someone else's run is 404; retry, fallback, skip and fail paths; the 8-call budget; an unexpected exception inside a step is contained |
| Security | `test_injection.py`, `test_pii.py`, `test_admin.py` | 23 attack strings blocked including spaced, zero-width, full-width and leetspeak forms; 27 normal questions not blocked; instruction lines removed from documents at ingest and from retrieved passages; emails, Indian phone formats, addresses and profile links redacted from resumes and logs; every admin route 401/403 for non-coordinators (read from the OpenAPI schema); uploads rejected by type, size, magic bytes, encoding and duplicate checksum; path traversal in filenames |

Coverage by module, lowest first:

<!-- eval:coverage:start -->
| Module (lowest coverage first) | Coverage |
|---|---:|
| `app/llm/gemini.py` | 85.4% |
| `app/db.py` | 86.2% |
| `app/config.py` | 86.6% |
| `app/api/agent.py` | 87.1% |
| `app/tools/catalog.py` | 90.6% |
| `app/agent/steps.py` | 90.8% |
| `app/rag/loader.py` | 90.8% |
| `app/rag/index.py` | 90.9% |
<!-- eval:coverage:end -->

## 3. Evaluation (RAG and agent)

Full method and discussion: [`docs/evaluation.md`](evaluation.md). Headline table for the Gemini run:

<!-- eval:gemini-metrics:start -->
| Metric | Baseline | Final | Better when |
|---|---:|---:|---|
| Hit@3 | 100.0% | 100.0% | higher |
| MRR | 0.980 | 1.000 | higher |
| Answer quality (correct facts) | 92.0% | 100.0% | higher |
| Groundedness | 100.0% | 98.3% | higher |
| Citation accuracy | 96.9% | 93.2% | higher |
| Refusal accuracy | 93.5% | 100.0% | higher |
| Hallucination rate on traps | 0.0% | 0.0% | lower |
| Injection block rate | 0.0% | 100.0% | higher |
| Unsafe outputs (attack succeeded) | 0 | 0 | lower |
| Ambiguous inputs handled | 100.0% | 100.0% | higher |
| Agent task success | 33.3% | 100.0% | higher |
| Latency p50 | 3.30 s | 5.39 s | lower |
| Latency p95 | 8.14 s | 10.61 s | lower |
| Answers by provider | gemini: 41 | gemini: 29, none: 12 | |
<!-- eval:gemini-metrics:end -->

Without any API key (extractive):

<!-- eval:extractive-metrics:start -->
| Metric | Baseline | Final | Better when |
|---|---:|---:|---|
| Hit@3 | 100.0% | 100.0% | higher |
| MRR | 0.980 | 1.000 | higher |
| Answer quality (correct facts) | 80.0% | 84.0% | higher |
| Groundedness | 98.1% | 97.8% | higher |
| Citation accuracy | 80.5% | 84.6% | higher |
| Refusal accuracy | 80.6% | 96.8% | higher |
| Hallucination rate on traps | 100.0% | 16.7% | lower |
| Injection block rate | 0.0% | 100.0% | higher |
| Unsafe outputs (attack succeeded) | 0 | 0 | lower |
| Ambiguous inputs handled | 100.0% | 100.0% | higher |
| Agent task success | 33.3% | 100.0% | higher |
| Latency p50 | 0.36 s | 0.26 s | lower |
| Latency p95 | 0.59 s | 1.49 s | lower |
| Answers by provider | extractive: 41 | extractive: 29, none: 12 | |
<!-- eval:extractive-metrics:end -->

## 4. Manual checks

Recorded in `PROGRESS.md` as each phase finished:

- Phase 3: server started with uvicorn; `/health`, `/docs`, login and the company list checked over HTTP.
- Phase 4: five questions through Gemini and the extractive provider (cited answer, multi-source answer, process question, out-of-scope refusal, injection block), then the same through the running server and its SSE stream.
- Phase 5: the prep agent streamed against the running server with Gemini and a demo fault (recovered retry), approved, and the tracker, analytics and logs checked.

## 5. Frontend and screenshots

Added in Phase 9: Playwright smoke tests of login, ask, eligibility and the prep agent with approval, and the list of screenshots in `screenshots/`.
