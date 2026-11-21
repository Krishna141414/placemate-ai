# Decisions

Short record of each design choice and the reason. Newest phase at the bottom.

## Phase 0 - Preflight

| # | Decision | Reason |
|---|---|---|
| D-01 | Python 3.14 for the venv | It is the only Python installed and a CPU PyTorch wheel exists for it (`torch 2.15.0+cpu`, cp314). |
| D-02 | All runtime artefacts under `backend/storage/` | One ignored folder for the database, index, uploads and logs keeps `.gitignore` simple and avoids hiding source by accident. |
| D-03 | `.gitignore` has no broad `lib/`, `data/` or `build/` rules | Those common template lines would hide `frontend/lib` and `backend/data`. |
| D-04 | Plain `git` over HTTPS, no `gh` | `gh` is not installed and is not needed to push. |

## Phase 1 - Research and plan

| # | Decision | Reason |
|---|---|---|
| D-05 | The core feature is college-specific answers and rule-based eligibility | Research: existing career tools bundle resume, JD match and interview prep, but none knows a college's own rules. |
| D-06 | RAG is a fixed pipeline, not an agent | One search answers a placement question. An agent here would add latency and failure modes. |
| D-07 | Exactly one agent, for "Prepare me for <company>" | It is the only goal with dependent steps, possible failures and a write at the end. |
| D-08 | The planner is rule-based; the LLM writes plan text but does not pick tools | The step order is known. This keeps the agent testable and working even on the extractive fallback and with a 0.5B local model. |
| D-09 | Hand-written agent loop, no framework | About 150 lines. State, retries and the approval gate stay explicit and easy to explain in the video. |
| D-10 | One approval gate, before the only write | Research: gate writes, not reads; too many gates become a rubber stamp. |
| D-11 | An ineligible student gets reasons and alternatives, not a saveable plan | Saving an application the student cannot make would be misleading. |
| D-12 | Eligibility and tracking are pure functions over structured data | Numeric and set comparisons must be exact and auditable. |
| D-13 | Company criteria live in YAML front matter of each company markdown file | One file is both the RAG document and the tool's data source, so they cannot disagree. |
| D-14 | BM25 top 20 + FAISS top 20, RRF k = 60, rerank to top 5 | Standard starting values from current practice; RRF needs no score normalisation. The eval checks they beat the baseline. |
| D-15 | Refusal is decided by the reranker score before any model is called | Deterministic, cheap, and identical whichever provider answers. |
| D-16 | The pipeline and the agent executor are generators that yield stage events | One implementation serves streaming UI, JSON API, tests and eval. |
| D-17 | Groundedness is computed without an LLM judge | The eval must run offline and give the same number each time. A sentence counts as grounded when a cited chunk supports it by overlap and embedding similarity. |
| D-18 | JWT in an httpOnly, SameSite=Lax cookie; argon2id hashing | The token is unreadable from JavaScript; argon2id is the current recommended password hash. |
| D-19 | An Origin check on unsafe methods in addition to CORS | CORS does not stop a cross-site form post; with cookie auth this closes CSRF without a token scheme. |
| D-20 | In-memory sliding-window rate limiter, written in-house | One process, no Redis. Small enough to test fully, and avoids a dependency that may lag Python 3.14. |
| D-21 | The frontend calls the backend directly (CORS), not through a Next.js rewrite | "CORS restricted to the frontend origin" is then a real control, and SSE is not buffered by a proxy. |
| D-22 | SQLite + in-process FAISS | A college corpus is a few hundred chunks. No server to install, and the index rebuilds in seconds on upload. |
| D-23 | An `events` table for analytics and the audit log | One append-only table answers "top questions", "unanswered", "provider usage" and "who uploaded what". |
| D-24 | A `demo_fault` option on agent runs | The tour must show a recovered step on demand. It only makes one named step fail once; it grants nothing. |
| D-25 | Eval summary is written to `eval/results/` and copied to `frontend/public/` | The landing and Evaluation pages show real numbers even when the backend is not running, and never hard-coded ones. |
| D-26 | Architecture diagram uses the project palette, in the project file only | The Diagram Design skill's global style guide was left at its defaults; changing a global tool for one project is not this project's call. |
| D-27 | Last30days ran cookie-free and its first-run setup was not persisted | I did not read browser cookies or write to the user's global last30days config without being asked. Sources were Reddit, Hacker News, GitHub and web. |
| D-28 | Gemini model id is confirmed with a live call in Phase 4 | Docs show `gemini-2.x` is no longer current (GA: `gemini-3.6-flash`, `gemini-3.5-flash-lite`); the free-tier choice is verified rather than assumed. |

## Phase 3 - Backend core

| # | Decision | Reason |
|---|---|---|
| D-29 | Middleware is plain ASGI, not `BaseHTTPMiddleware` | Streaming (SSE) responses pass through untouched, and the request-id context variable stays valid. |
| D-30 | Order: CORS, security headers, request context, origin check, rate limit, routes | Every response, including 403, 429 and 500, carries CORS and hardening headers and a request id. |
| D-31 | Unhandled exceptions are caught in the request-context middleware | The client gets a generic message and a request id; the traceback goes only to the log. |
| D-32 | The role is read from the database on every request, not from the token | A forged or stale role claim cannot grant access. |
| D-33 | Unknown email and wrong password give the same response and cost the same time | Prevents account enumeration. A dummy hash is verified when the email is unknown. |
| D-34 | Rate limiting keys on the socket address, not `X-Forwarded-For` | The header is client-controlled. Behind a trusted proxy this would need to change. |
| D-35 | A separate `probe` limit class (5/min) on `/api/meta/ping` | The Security page can show a real 429 without locking the demo account out of login. |
| D-36 | Only the demo student and coordinator have known passwords | The other seeded students exist for analytics and get random unusable passwords. |
| D-37 | Validation errors return field names and reasons, never the submitted value | Avoids reflecting user input (or a mistyped password) back in a response. |
| D-38 | One pinned `requirements.txt` from `pip freeze` | Reproducible installs with a single command. |

## Phase 4 - RAG

| # | Decision | Reason |
|---|---|---|
| D-39 | Gemini model `gemini-3.5-flash-lite` | Confirmed live with the available key: listed, stable, about 1 s for a short answer. Resolves D-28. |
| D-40 | Each chunk is indexed as "Title > Section path" + text, but source cards show only the text | "Minimum CGPA: 7.0" is useless without knowing which company it belongs to; the heading makes it findable without cluttering the card. |
| D-41 | Refusal threshold: cross-encoder logit 0.0 | On the sample corpus real questions score about 4 to 8 and off-topic ones about -8 to -11. 0.0 sits in the gap; the eval set checks it. |
| D-42 | Router rejects an answer with no valid citation and moves to the next provider | An uncited answer cannot be checked, so it is treated as a failed answer, not shown. |
| D-43 | The extractive fallback uses only passages within 3.0 logits of the best one, and keeps list items whole | Without this it quoted a neighbouring company's rules; with it, an answer stays inside the right document. |
| D-44 | Retrieved passages are scanned again by the injection guard before use | Defence in depth: a document that reached the index another way still cannot steer the model. |
| D-45 | A canary string in the system prompt; any answer containing it is discarded | Detects prompt leakage without relying on the model's cooperation. |
| D-46 | Links and HTML are stripped from answers unless the URL appears in a source | Blocks data exfiltration through rendered links or images. |
| D-47 | The local model gets only the top 3 passages, cut to 700 characters | A 0.5B model on CPU must answer in seconds; it is a fallback, not the main path. |
| D-48 | Questions stored in analytics events are scrubbed of emails and phone numbers | Coordinators see what is asked, not who can be contacted. |

## Phase 5 - Tools and agent

| # | Decision | Reason |
|---|---|---|
| D-49 | Eligibility compares CGPA at two decimals | A cut-off of 7.0 must not fail a 7.0 student because of float noise. |
| D-50 | Missing profile fields fail that criterion with "not set" | The tool never guesses a student's CGPA or batch. |
| D-51 | Resume skills come from a fixed vocabulary with aliases and implications | Predictable and explainable ("MySQL" implies "SQL"); every matched and missing skill can be shown. |
| D-52 | Match % = 60% skill coverage + 40% semantic similarity, formula shown in the UI | Skills are what companies list; similarity credits related experience the keyword list misses. The weights are a judgement call, so they are published rather than hidden. |
| D-53 | Semantic similarity is "best resume section per job-description section", averaged and rescaled from 0.15-0.60 | MiniLM truncates long input; section-level matching avoids that, and the observed cosine range on the sample data is mapped to 0-1. |
| D-54 | The agent's tool-call budget counts retries | A run with failing steps still stops; the limit is about cost, not about step names. |
| D-55 | Only process retrieval and the plan summary have fallbacks | Process retrieval falls back to the structured rounds; the summary falls back to a template. Eligibility has no honest substitute, so its failure stops the run. |
| D-56 | The plan's structure is rule-based; the model only writes the cited summary | The plan must be identical whichever provider is up, and a 0.5B local model cannot be trusted to produce a structured plan. |
| D-57 | Plan length follows the application deadline (2-4 weeks) | A plan that ends after the deadline is useless. |
| D-58 | Approving keeps an application the student already tracks | The agent must not overwrite a status like "online_test" with "planned". |
| D-59 | `demo_fault` can only target four named steps and fails each once | The tour can show recovery on demand; it cannot be used to break eligibility or loop. |
| D-60 | Uploads are checked by magic bytes as well as extension, and duplicates are refused by checksum | A renamed binary or the same notice uploaded twice should not reach the index. |
| D-61 | Stored upload names get a random prefix and live only in `storage/uploads/` | No overwrites, no path traversal; the original name is kept only in sanitised form. |
| D-62 | Eligibility statistics are computed from current profiles, not from check events | "How many students can apply to X" should not depend on who happened to click. |
| D-63 | Logs are returned as readable sentences, not raw payloads | SHOWCASE.md forbids raw JSON on screen. |

## Phase 6 - Tests and evaluation

| # | Decision | Reason |
|---|---|---|
| D-64 | Metrics are computed by code, with no LLM judge | Same answers always get the same scores, the eval runs offline, and no model grades itself. |
| D-65 | "Supported" = 60% content-word overlap or 0.72 embedding similarity with a sentence of the passage, heading included | Simple, explainable, and it accepts paraphrase without accepting unrelated text. Its limits are written down in `docs/evaluation.md`. |
| D-66 | Baseline agent = no retries, no fallbacks, every step required | Makes the value of the recovery design measurable rather than claimed. |
| D-67 | Two eval runs: Gemini (the configured provider) and extractive (no key) | The brief requires the app to work without a key; the offline run shows how well it does. |
| D-68 | Every figure in the docs is written by `eval/report.py` | "Real results only": numbers can only come from result files. |
| D-69 | First runs are archived, not overwritten | The fixes in section 7 of the evaluation are visible against the run that found them. |
| D-70 | Refuse questions that name something absent from every document | A student asking about a company that never visits must not get another company's cut-off. Acronyms that are initials of a corpus phrase are allowed so "DSA" still works. |
| D-71 | Model answers under 5 words or repeating prompt markup are rejected | A degenerate local-model answer is worse than an extractive one. |
| D-72 | Re-grade saved answers after a metric fix instead of calling Gemini again | Cheaper and keeps the answers fixed; `regrade.py` refuses to run if retrieval no longer matches the saved run. |
| D-73 | Chart colours: teal #0E8F86 (baseline) and brand blue #1D4ED8 (final) | Validated with the dataviz palette checker (lightness, chroma, colour-blind separation, contrast). Slate failed the chroma floor; orange is too close to the reserved warning colour. |

## Phase 7 - Frontend app

| # | Decision | Reason |
|---|---|---|
| D-74 | Next.js App Router with every data page as a client component behind a server wrapper for metadata | All data comes from FastAPI with the user's cookie; the wrapper still gives each page its own title. |
| D-75 | `proxy.ts` only checks that a session cookie exists; the shell checks the role; the API enforces both | Next.js docs: proxy is an optimistic check and must not be the only line of defence. |
| D-76 | Dark mode via `data-theme` on `<html>` rather than a `.dark` class | Hallmark's linter recognises `:root[data-theme="dark"]` as a theme block; shadcn's `dark:` variant was pointed at the same attribute. |
| D-77 | AI Elements components are edited where they did not fit: Tool header accepts a badge and icon, InlineCitation accepts a label, Sources is typed as a Collapsible, status icons use theme tokens | They are copied into the project to be owned; document sources have no URL, and agent statuses are not AI SDK tool states. |
| D-78 | Streams are consumed through a queue and revealed at the pace in `lib/speed.ts` | SHOWCASE.md asks for about 1.5-2 s between steps at medium speed; the backend answers faster than a viewer can follow. |
| D-79 | The approval is a dialog that shows the exact plan and application record, plus an inline Confirmation card that stays on the page | SHOWCASE.md asks for an approval dialog; the card keeps the decision visible afterwards. |
| D-80 | Every data region has loading, empty, error and full states, via one `useApi` hook | Hallmark app-screen rule, and a consistent way to show backend failures. |
| D-81 | Selections live in the URL (`?company=`, `?run=`, `?c=`, `?status=`, `?view=all`) | A refresh or the guided tour can reopen the same state. |
| D-82 | The Security page runs real requests and shows the real status codes | "Try it" must prove the control, not describe it. |
| D-83 | `POST /api/meta/redact-preview` exists for any logged-in user and logs nothing | The coordinator cannot call resume matching, but the PII demo should work for both roles. |
| D-84 | Security headers are listed in CORS `expose_headers` | Otherwise the browser hides them from page code and the Security page could not show them. |
| D-85 | Evaluation page reads the published `eval-summary.json` and phrases its comparisons from the data | Numbers and the direction of each difference can never drift from the saved run. |
| D-86 | Analytics chart uses status colours (warning, error) for "not in the documents" and "blocked", always labelled | Those series are states, which is what the status palette is for (dataviz rule); answered uses the categorical blue. |
| D-87 | The landing hero card renders finished and types out only on Replay (or when the tour asks) | SHOWCASE.md wants the typing card, and also says no animation starts on page load. Replay satisfies both, and the presenter controls when it plays. |
| D-88 | The hero card shows a real Gemini answer from the running app, quoted verbatim (first three sentences) | No invented output on the landing page; the card says it is a real answer from the sample documents. |
| D-89 | The walkthrough pins only on screens 1024px and wider with motion allowed; otherwise it is a plain list of captioned screenshots | Pinning on phones is scroll-jacking, and SHOWCASE.md forbids it under reduced motion. The list reads fine with no JS. |
| D-90 | Landing animations use `gsap.from` over a fully drawn default state | Content and the pipeline diagram stay visible if JS fails or motion is reduced. |
| D-91 | Walkthrough images are real app screenshots (WebP, 1008px wide) | A hand-drawn browser mock would be an illustration; these show the actual product. |
| D-92 | `GET /api/auth/session` returns 200 with `user: null` for visitors; the auth provider uses it instead of `/me` | Public pages (landing, login) checked `/me` and logged a 401 in the console on every visit; "no console errors" is part of Done. `/me` still returns 401 for API clients. |
| D-93 | The tour caption is part of the bottom bar, and the page reserves the bar's height (`--tour-inset`) | SHOWCASE.md says captions must never cover the bar or the highlighted element. A caption docked in the bar can't, and the spotlight is clipped to the area above it. |
| D-94 | The idle "Start tour" button sits bottom-right; the active bar is bottom-centre | A centred pill on every page would sit over the Ask input and page footers when nobody is presenting. |
| D-95 | Pause freezes everything, in both modes; Mode decides only whether steps advance on their own | Gives Play/Pause and Manual/Auto separate jobs. Pause also stops a running action (typing, a wait) mid-way. |
| D-96 | Actions run only when moving forward; Back and a reload show the step without repeating it | Going back must not ask the model again, start a second agent run or upload twice. |
| D-97 | Tour state is a small external store mirrored to sessionStorage | It survives client navigation (the provider sits in the root layout) and a reload, with no hydration mismatch. |
| D-98 | The tour logs in or out with the demo accounts when a step needs a role | A presenter can start, go back or jump in mid-way and every step still opens as the right user. |
| D-99 | The tour removes its own earlier demo upload (by file name) before uploading again | The backend rejects duplicates by checksum, which would stop a second run of the tour at the upload step. |
| D-100 | Spotlight follows its element every frame by transform, with no transform transition | Answers stream and pages reflow; a transition would lag behind the element during scrolling. |
| D-101 | Space is captured while the tour is active, unless the focus is in a text field | Stops Space from pressing a focused button (such as Approve) while the presenter means to pause. |
| D-102 | Intentional 4xx responses (Security "Try it"s, the invalid upload) still show as "Failed to load resource" in the browser console | Chrome logs every 4xx fetch; these requests exist to show the rejection. No other console errors remain. |
| D-103 | Playwright tests run against the real backend and model, logged in once per role | Smoke tests should prove the flows a reviewer will click, not mocks. One login per role keeps the suite under the 10-a-minute login limit. |
| D-104 | Playwright uses its own Chromium when installed, otherwise Edge on Windows | The pinned runner wanted a newer Chromium build than the one on the machine and the download stalled; Edge ships with Windows. |
| D-105 | General API rate limit raised from 60 to 120 a minute (login 10 and the demo probe 5 unchanged) | A single-page app makes 2 to 4 calls per screen; the smoke run and a fast tour hit 60. Abuse protection stays on the expensive and sensitive routes. |
| D-106 | A 429 on the session check shows a 429 page and keeps the user logged in | Being rate limited says nothing about the session; redirecting to login was wrong. |
| D-107 | Timestamps use a `UTCDateTime` column type | SQLite drops timezones, so responses had no offset and browsers showed times 5.5 hours off. |
| D-108 | Registry code (`components/ui`, `components/ai-elements`) keeps its upstream patterns; three React Compiler advisories are off for those folders only | Easier to update from the registries; our own code keeps the full rule set and passes it. |
| D-109 | Headings and buttons use sentence case, not Title Case | The Web Interface Guidelines suggest Title Case, but the design brief (Hallmark, Humanizer) uses sentence case throughout; one style is applied everywhere. |
| D-110 | The idle "Start tour" button hides while a dialog is open, and the Ask input leaves room for it on phones | On a phone it covered the send button and could cover dialog buttons. |
| D-111 | `npm run setup` / `dev:all` / `reset-demo` at the repository root wrap the PowerShell scripts with `-ExecutionPolicy Bypass` | Windows blocks unsigned scripts by default; one familiar command avoids that first-run failure. |
| D-112 | `dev.ps1` runs the backend in its own window and the frontend in the current one | Two readable logs without adding a process manager dependency. |
| D-113 | Retrieval models go offline only when both are already cached | The default `hf_offline=True` stopped a fresh machine from downloading them, so the backend could not start. Cached machines still never touch the network. |
| D-114 | The answer renderer turns "- " lines into a list and drops `**` markers | Models sometimes reply in light markdown; raw markers must never show (SHOWCASE.md: no raw output on screen). |
| D-115 | The approval dialog focuses itself on open, not its first focusable element | The first focusable element is a citation chip, and focusing it popped a preview over the plan. |
| D-116 | Evaluation run logs are committed (un-ignored from `*.log`) | They are part of the evidence the docs point to and contain no secrets or personal data. |
