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
