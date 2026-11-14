# Requirements

## 1. Problem

At tier-2 and tier-3 engineering colleges, one small placement cell serves hundreds of final-year students. The same questions arrive every week: "Am I eligible for this company?", "What is the one-offer policy?", "What are the interview rounds?", "How do I prepare?". The answers already exist in policy documents, company notices and seniors' interview write-ups, but students cannot find them quickly, and the guidance they get is not personal to their CGPA, branch or resume.

The result is that coordinators spend their time repeating answers, and students prepare without knowing where they stand.

## 2. Solution in one paragraph

PlaceMate is a web application that answers placement questions from the college's own documents with citations, decides eligibility with the college's actual rules, compares a resume with a job description, and builds a week-by-week preparation plan that the student approves before it is saved. Coordinators upload documents and see what students are asking and where they struggle.

## 3. Users

| User | Goals |
|---|---|
| **Student** | Get a correct answer with its source; know eligibility for each company and why; see which skills a resume is missing for a role; get a preparation plan; track applications and deadlines |
| **Coordinator** | Keep documents current; see top questions, questions the system could not answer, eligibility statistics and provider usage; review activity logs |

## 4. Functional requirements

### Authentication and roles
- **FR-1** Users log in with email and password. Two roles exist: `student` and `coordinator`.
- **FR-2** Coordinator-only pages and API routes are refused for students (403) and anonymous users (401).
- **FR-3** Two demo accounts are seeded, with one-click "Use demo account" buttons on the login page.

### Ask PlaceMate (RAG)
- **FR-4** A student asks a question in natural language and receives an answer grounded in the indexed documents.
- **FR-5** Every factual statement carries a numbered citation; each citation opens a source card with the document, the retrieved snippet and its score.
- **FR-6** If the documents do not contain the answer, the system says so and does not guess.
- **FR-7** The answer streams in, and a panel shows how it was produced: guard check, retrieved, reranked, generated, and which provider answered.
- **FR-8** Conversations are saved and can be reopened.

### Eligibility
- **FR-9** A student checks eligibility for one company or for all companies.
- **FR-10** The result lists each criterion (CGPA, active backlogs, branch, batch) with pass or fail, the required value, the student's value and a reason.

### Resume match
- **FR-11** A student pastes or uploads a resume, picks a company, and receives a match percentage with matched and missing skills.
- **FR-12** Phone numbers, email addresses and postal addresses are removed before any model sees the resume, and the page shows what was removed.

### Prep agent
- **FR-13** Given "Prepare me for <company>", the agent plans its steps, checks eligibility, matches the resume, retrieves the company's process and interview experiences, and drafts a week-by-week plan.
- **FR-14** Each step, its tool call and its result are visible as they happen.
- **FR-15** If a step fails, the agent retries, falls back, or skips the step when it is optional, and shows which of these happened.
- **FR-16** Nothing is saved until the student approves. Approve saves the plan and adds the application to the tracker; Reject discards both.
- **FR-17** A run has a hard step limit, and its state is stored so it can be inspected later.

### Applications
- **FR-18** A student adds, updates and views applications with status and deadline.

### Coordinator
- **FR-19** A coordinator uploads `.md`, `.txt` or `.pdf` documents; invalid files are rejected with a clear reason.
- **FR-20** After an upload or delete, the index is rebuilt and the new content is searchable.
- **FR-21** An analytics page shows top questions, unanswered questions, eligibility statistics and provider usage.
- **FR-22** A log view shows recent activity as a table.

### Showcase
- **FR-23** A landing page explains the product with scroll-driven sections.
- **FR-24** A Guided Tour walks through every feature under presenter control (manual by default).
- **FR-25** An Evaluation page shows real baseline-versus-final results, and a Security page lets each protection be tried live.

## 5. Non-functional requirements

| ID | Requirement | Target |
|---|---|---|
| **NFR-1** Availability without a key | Works with no API key | Falls back gemini -> local -> extractive automatically |
| **NFR-2** Grounding | Answers come from documents | Measured groundedness and citation accuracy reported in `docs/evaluation.md` |
| **NFR-3** Safety | Prompt injection is blocked in user input and in document text | Measured block rate on the eval set |
| **NFR-4** Privacy | Resume PII never reaches an LLM or a log | Unit tests on the redactor and on log output |
| **NFR-5** Security | Hashed passwords, httpOnly session cookie, role checks, validation, upload checks, rate limiting, restricted CORS, security headers, no stack traces | Each item listed with its file in `SECURITY.md` and covered by a test |
| **NFR-6** Performance | Usable on a laptop CPU | Retrieval and rerank under about 1 s after warm-up; end-to-end latency reported per provider |
| **NFR-7** Reliability | Agent survives a failing tool | Recovery paths tested; max 8 steps |
| **NFR-8** Testability | Automated tests | pytest suite with coverage reported; Playwright smoke test |
| **NFR-9** Usability | Looks and behaves like a product | Responsive at desktop and mobile widths, keyboard accessible, `prefers-reduced-motion` respected |
| **NFR-10** Portability | Runs on Windows from a fresh clone | One setup script and one run script; verified by a fresh-clone check |
| **NFR-11** Reproducibility | Same result on another machine | All dependencies pinned |

## 6. Scope

In scope: everything in sections 4 and 5, with a fictional sample corpus (one policy, 12 companies, 15 interview experiences, 6 prep guides, demo students and resumes).

## 7. Out of scope

- **Fine-tuning.** The documents change every season; retrieval handles that, training would not.
- **Image or voice models.** The problem is text.
- **Multi-agent systems.** One goal with five steps does not need agents talking to each other.
- **Real company data and real student records.** All data is invented.
- **Applying to companies on the student's behalf**, sending email, or any action outside the app.
- **Multi-college tenancy, SSO, password reset by email.** A real deployment would need them; a demonstration does not.
- **Mock interviews.** Common in commercial tools, but a separate product.

## 8. Assumptions and constraints

- Runs locally on Windows with Python 3.14 and Node 24, CPU only.
- The local model is `Qwen2.5-0.5B-Instruct`. It is small, so answers from it are shorter and less fluent than Gemini's; the extractive fallback guarantees a cited answer even without it.
- SQLite and an in-process index are enough for one college's document set (hundreds of chunks, not millions).

## 9. Success criteria

1. A student can ask, check eligibility, match a resume and get an approved prep plan without reading any instructions.
2. The final pipeline beats the vector-only baseline on retrieval metrics on the same question set.
3. Out-of-scope questions are refused and injection attempts are blocked, with measured rates.
4. Every requirement here maps to code and to a test or eval case in `docs/REQUIREMENTS_MATRIX.md`.
