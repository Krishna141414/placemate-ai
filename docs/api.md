# API

The backend is FastAPI. With it running, the interactive reference is at **http://127.0.0.1:8000/docs** (Swagger UI) and the schema at `/openapi.json`. This page is the short version: every endpoint, who may call it, and the conventions that apply to all of them.

## Conventions

- **Base URL:** `http://127.0.0.1:8000` (the frontend uses `http://localhost:8000`; set `NEXT_PUBLIC_API_URL` to change it).
- **Authentication:** `POST /api/auth/login` sets the `pm_session` cookie (httpOnly JWT). Send it with every request (`credentials: "include"` in the browser). There are no API keys or bearer tokens.
- **Roles:** *student* or *coordinator*, read from the database on every request. "Login" below means either role.
- **Cross-site requests:** state-changing requests (POST, PATCH, DELETE) must come from the frontend origin, or carry no `Origin` header at all (curl, tests).
- **Errors** always have one shape:

  ```json
  { "error": { "code": "not_authenticated", "message": "Please log in to continue.", "request_id": "ed72301460704d7e" } }
  ```

  Validation errors (422) add `details: [{ "field", "message" }]`. A 429 adds a `Retry-After` header. The `request_id` matches the server log line.
- **Rate limits per address per minute:** login 10, `/api/meta/ping` 5, everything else 120. `/health` and the docs are not limited.
- **Timestamps** are ISO 8601 in UTC with an offset (`2026-11-21T15:04:00+00:00`). Dates (deadlines) are `YYYY-MM-DD`.

## Endpoints

### Auth

| Method | Path | Who | What |
|---|---|---|---|
| POST | `/api/auth/login` | anyone | Log in with `{email, password}`; sets the session cookie, returns the user |
| POST | `/api/auth/logout` | anyone | Clears the cookie (204) |
| GET | `/api/auth/session` | anyone | `{user}` for a logged-in user, `{user: null}` for a visitor (always 200) |
| GET | `/api/auth/me` | login | The logged-in user and, for students, their profile (401 for a visitor) |
| PATCH | `/api/auth/profile` | student | Update own branch, CGPA, backlogs, batch or resume text |

### Ask (RAG)

| Method | Path | Who | What |
|---|---|---|---|
| POST | `/api/ask` | login | `{question, conversation_id?}` → cited answer: `answer`, `sources[]`, `refused`, `blocked`, `provider`, `steps[]`, `latency_ms` |
| POST | `/api/ask/stream` | login | Same, as server-sent events (below) |
| GET | `/api/conversations` | login | Own saved conversations |
| GET | `/api/conversations/{id}` | login | One own conversation with its messages (404 if it is not yours) |
| DELETE | `/api/conversations/{id}` | login | Delete one own conversation |

Server-sent events from `/api/ask/stream`, in order:

| Event | Data |
|---|---|
| `step` | One pipeline step as it finishes: input guard, hybrid retrieval, rerank, grounding check, generate, output guard (name, status, detail, ms) |
| `sources` | The numbered passages given to the model |
| `delta` | A piece of the answer text |
| `final` | The full result plus `conversation_id` and `message_id` |
| `error` | `{code, message}` if something failed after the stream started |

A refused or blocked question is a normal 200 with `refused` or `blocked` set, not an error.

### Tools (student)

| Method | Path | What |
|---|---|---|
| POST | `/api/tools/eligibility` | `{company_id}` → eligible or not, with each criterion (CGPA, backlogs, branch, batch), the required and actual values, and a reason |
| POST | `/api/tools/eligibility/all` | The same for every company |
| POST | `/api/tools/resume-match` | `{company_id, resume_text?, save_to_profile?}` → match %, skill coverage, similarity, matched / missing / extra skills, advice, and what PII was redacted. Without `resume_text` the saved resume is used |
| GET | `/api/tools/resume` | Own saved resume text |
| POST | `/api/tools/resume-extract` | Multipart `.txt`, `.md` or `.pdf` → its text (nothing stored) |

### Prep agent (student)

| Method | Path | What |
|---|---|---|
| POST | `/api/agent/runs` | `{company_id, demo_fault?}` → runs to the approval step and returns the run |
| POST | `/api/agent/runs/stream` | Same, as server-sent events: `run` (created), `step` (each tool step with status, attempts, output), `plan` (the drafted plan), `approval_required`, `final` (the saved run), or `error` |
| GET | `/api/agent/runs` | Own recent runs |
| GET | `/api/agent/runs/{id}` | One own run with its full saved state |
| POST | `/api/agent/runs/{id}/approve` | Saves the plan and adds or updates the application, in one transaction. 409 if already decided |
| POST | `/api/agent/runs/{id}/reject` | Discards the plan; nothing is saved |

`demo_fault` makes one step fail once so the recovery can be shown: `retrieve_process`, `match_resume`, `retrieve_experiences` or `build_plan`.

### Applications and plans (student)

| Method | Path | What |
|---|---|---|
| GET | `/api/applications` | Own applications, soonest deadline first |
| POST | `/api/applications` | `{company_id, status?, deadline?, notes?}`; creates, or updates the existing one for that company |
| PATCH | `/api/applications/{id}` | Change status, deadline or notes |
| DELETE | `/api/applications/{id}` | Remove from the tracker |
| GET | `/api/prep-plans` | Own approved plans |
| GET | `/api/prep-plans/{id}` | One plan |
| PATCH | `/api/prep-plans/{id}` | Mark tasks done |

Statuses: `planned`, `applied`, `online_test`, `interview`, `offer`, `rejected`.

### Coordinator

| Method | Path | What |
|---|---|---|
| GET | `/api/admin/documents` | Every indexed document with type, chunk count and removed lines |
| POST | `/api/admin/documents` | Multipart upload (`.md`, `.txt`, `.pdf`, up to 5 MB). Validated, sanitised, indexed. 413, 415, 409 or 422 with a reason when refused |
| DELETE | `/api/admin/documents/{id}` | Delete an uploaded document and re-index (seed documents cannot be deleted) |
| POST | `/api/admin/reindex` | Rebuild the search index |
| GET | `/api/admin/analytics` | Totals, questions per day, most asked, not answered, eligibility per company, provider usage, blocked attempts |
| GET | `/api/admin/logs?type=&limit=` | Recent activity as readable rows |

### Meta

| Method | Path | Who | What |
|---|---|---|---|
| GET | `/health` | anyone | Liveness and index status |
| GET | `/api/meta/companies` | login | Companies visiting campus (id, name, role, category, CTC) |
| GET | `/api/meta/providers` | login | The configured LLM provider and fallback order |
| GET | `/api/meta/ping` | login | Limited to 5 a minute so the Security page can show a 429 |
| POST | `/api/meta/redact-preview` | login | `{text}` → the text with PII redacted and counts. Nothing is stored or logged |

## Try it with curl

```bash
# log in (stores the cookie in a file)
curl -c jar.txt -H "Content-Type: application/json" \
  -d '{"email":"student@placemate.demo","password":"Student@123"}' \
  http://127.0.0.1:8000/api/auth/login

# ask a question
curl -b jar.txt -H "Content-Type: application/json" \
  -d '{"question":"Can I sit for another company after I get an offer?"}' \
  http://127.0.0.1:8000/api/ask

# check eligibility
curl -b jar.txt -H "Content-Type: application/json" \
  -d '{"company_id":"orbitpay"}' http://127.0.0.1:8000/api/tools/eligibility
```
