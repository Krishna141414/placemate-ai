# Walkthrough script (5 to 7 minutes)

Read it aloud a few times, then speak from the headings. The words in quotes are a suggestion, not something to memorise. Times are a guide; the live demo is the part to keep, the rest can shrink.

Before you start: `npm run reset-demo`, `npm run dev:all`, browser on http://localhost:3000, VS Code open on `backend/app/rag/pipeline.py`.

---

## 1. Problem (30 seconds)

"At tier-2 and tier-3 engineering colleges, placement information is spread across PDFs, notices and WhatsApp forwards. Students keep asking the placement cell the same questions: can I sit for another company after an offer, am I eligible with one backlog, what are the rounds at this company. Eligibility is checked by hand before every drive, and preparation depends on which seniors you know."

## 2. Users (20 seconds)

"There are two users. A **student** asks questions, checks eligibility, compares their resume with a job, gets a prep plan and tracks applications. A **coordinator** in the placement cell uploads documents and sees analytics: what students ask, what the documents don't answer, and who is eligible where."

## 3. Requirements (30 seconds)

"The main functional requirements were: answers must come only from the college's documents, with citations, and refuse when the documents don't say. Eligibility must be exact, so it's code, not a model. Resume contact details must never reach a model. The prep plan must not be saved without the student's approval.

The non-functional ones: it must work with no API key, it must be secure (roles, injection, PII, rate limits), and it must be measured, with an evaluation and tests. All of that is in `docs/requirements.md`, and `docs/REQUIREMENTS_MATRIX.md` maps each requirement to the code and the test that proves it."

## 4. Architecture (45 seconds)

Show `docs/architecture-diagram.png` (or the README).

"The frontend is Next.js. It talks to one FastAPI backend, with the session in an httpOnly cookie. Every request passes the edge first: CORS, security headers, an origin check and rate limits.

Behind the routes there are three AI parts, and each one is there for a reason:
- **RAG** for questions: BM25 plus vector search, fused with Reciprocal Rank Fusion, then a cross-encoder reranks to the best five passages, and the model answers with numbered citations.
- **Tools** for anything that is a rule or a number: eligibility, resume match, the application tracker. Plain Python, so they can't hallucinate.
- **One agent**, only for 'Prepare me for a company', because that goal needs several steps in order, and it has to ask before saving.

For the model I use Gemini Flash-Lite, with a fallback to a small local model, Qwen 0.5B, and then to an extractive answerer, so the app always answers, even offline. Data is in SQLite, and the search index is FAISS plus BM25."

## 5. Live demo (3 minutes)

| # | Page | Click | Say |
|---|---|---|---|
| 1 | `/` landing | Scroll once through the hero and "How it works" | "This is the landing page. The answer card here is a real answer from the app." |
| 2 | `/login` | **Use demo student** | "Seeded demo accounts. Login sets an httpOnly JWT cookie." |
| 3 | Ask | Chip **Policy: Can I sit for another company after I get placed?** | "Every sentence has a citation. Hover the number to see the passage." Open **How this was answered**: "Input guard, hybrid retrieval, rerank, grounding check, generate, output guard. The badge shows Gemini answered." |
| 4 | Ask | Chip **Not in the documents: hostel fee** | "Not in the documents, so it refuses. No guessing." |
| 5 | Ask | Chip **Injection attempt** | "Blocked by the input guard before retrieval, and no model is called." |
| 6 | Eligibility | Example **OrbitPay fails CGPA** | "Checked by code, criterion by criterion, with the reason. 7.8 is below OrbitPay's minimum." |
| 7 | Resume match | **Use my saved resume**, company Nimbusware, **Match** | "Skills plus embedding similarity. And here: the phone, email and address were removed before any model saw the resume." |
| 8 | Prep agent | Nimbusware, Recovery demo **Process search fails once**, **Start** | "The agent runs five steps. Step 3 failed once and was retried: Recovered after retry. The budget shows tool calls used." When the dialog opens: "It shows exactly what will be saved, and nothing is saved until I approve." Click **Approve**. |
| 9 | Applications | (sidebar) | "The approved plan added the application here." |
| 10 | Log out, **Use demo coordinator**, Documents | **Upload a notice with planted instructions** | "This notice hides instructions for the model. They are stripped before indexing; here are the two removed lines." |
| 11 | Analytics | scroll | "Most asked, not answered, eligibility per company." |

If time is short, do 3, 5, 6, 8 and 10. Option: press **Start tour** and use Next instead of clicking by hand; the tour does the same flow and names the requirement at each step.

## 6. Evaluation (45 seconds)

Open the **Evaluation** page (or `docs/evaluation.md`).

"I built a 47-case evaluation: 25 answerable questions, 6 hallucination traps, 6 injection attempts, 4 ambiguous ones and 6 agent tasks. Every metric is computed by code, no LLM judge. I compared a **baseline**, vector search only with no guards, against the **final** system.

With Gemini: answer quality went from 92 to 100%, refusal accuracy from 93.5 to 100%, injection blocking from 0 to 100%, and agent task success from 33 to 100% because of the retries and fallbacks. The cost: median latency went from 3.3 to 5.4 seconds, and citation accuracy dropped a little, from 96.9 to 93.2%, because the final system cites more passages per sentence and some only partly support it. That's the next thing I'd fix.

There are 380 backend tests with 96% coverage, and 18 Playwright tests of the main flows."

## 7. Security (30 seconds)

Open the **Security** page and press one or two **Try it** buttons.

"Argon2 password hashes, a JWT in an httpOnly cookie, the role checked from the database on every request, ownership checks so students only see their own data. Injection guards on user input and on document text, a canary in the system prompt, an output filter. PII redaction before any model. Upload validation, rate limits, CORS for one origin, security headers, and no stack traces to users. Each one is in `SECURITY.md` with its file and test."

## 8. Limitations (20 seconds)

"The evaluation set is small and I wrote it myself, so the numbers are optimistic; there's no held-out set. Thirty-four documents make retrieval easy. Injection detection is pattern-based, so a new phrasing can get past the input guard, which is why there are other layers. The rate limiter is in memory, so it's for one server process."

## 9. Future work (20 seconds)

"College single sign-on instead of seeded accounts. Make each sentence cite only the passage that states the fact, to bring citation accuracy back up. A held-out evaluation set written by someone else, and an LLM judge as a second opinion. Deadline notifications. And Postgres with a shared rate-limit store, to run more than one server."

---

**Closing line:** "So the core idea is: let the model write, but let code decide the facts, and measure everything. I'm happy to go into any part of the code."
