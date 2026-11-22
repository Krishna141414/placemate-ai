# Likely viva questions, with short answers

Say the answers in your own words. Each one is 2 to 4 lines on purpose: start with the short answer, then give one detail or number, and stop. If the mentor wants more, they will ask.

Part A is about PlaceMate (35 questions). Part B is general AI / GenAI (25 questions); each one ends with where it shows up in PlaceMate. Where it says **Your example**, add one line from your own Tasks 1 to 13 so you can link back to work you did.

---

## Part A. PlaceMate

### Problem and design

**A1. What problem does PlaceMate solve?**
Students at tier-2/3 colleges ask the placement cell the same questions again and again, eligibility is checked by hand, and preparation depends on which seniors you know. PlaceMate gives cited answers from the college's own documents, exact eligibility checks, resume matching and an approved prep plan, plus analytics for the coordinator.

**A2. Who are the users, and what can each do?**
A student: ask, check eligibility, match resume, run the prep agent, track applications. A coordinator: upload documents, see analytics and the activity log. Roles are checked on every request; a student gets 403 on coordinator routes.

**A3. Why did you use RAG, tools and an agent, and not just one LLM?**
Each part matches a kind of work. Questions about documents → RAG, so answers are grounded and cited. Rules and numbers (eligibility, scores) → plain code, which can't hallucinate. One multi-step goal ("prepare me for X") → one agent. I did not use the agent for everything because most requests are one step, and an agent adds cost and failure points.

**A4. What did you choose *not* to use, and why?**
Fine-tuning: the documents change every season and retrieval handles that, so training would go stale. Image models: all inputs are text. Multi-agent: one agent with tools covers the only multi-step goal.

**A5. What is the most important design principle in the project?**
"Let the model write, let code decide the facts." The LLM only phrases answers from retrieved passages and writes the plan summary. Eligibility, scores, the plan structure, refusals and blocks are all decided by code.

### RAG pipeline

**A6. Walk me through what happens when a student asks a question.**
`run_pipeline`: input guard → hybrid retrieval (BM25 20 + vectors 20, RRF) → cross-encoder rerank to top 5 → grounding check (refuse if the best score < 0 or an unknown name) → LLM with the system prompt and numbered sources → output guard (canary, citations, links). Each step streams to the UI.

**A7. Why hybrid search instead of only vector search?**
Vectors are good at meaning ("leave after placement" ≈ "one-offer policy") but blur exact tokens like company names, "PPO", "C++" or "7.5". BM25 matches those exactly. Combining them gets both. In the evaluation the reranked hybrid moved MRR from 0.98 to 1.00.

**A8. What is Reciprocal Rank Fusion, and why use it?**
Each passage gets Σ 1/(60 + rank) over the lists it appears in (`rrf_fuse`). It uses ranks, not raw scores, so I don't have to normalise BM25 scores and cosine scores, which are on different scales, or tune weights. k = 60 is the standard value.

**A9. What does the reranker do that the embeddings don't?**
The embedding model encodes the question and a passage separately and compares vectors (a bi-encoder). The cross-encoder reads both together, so it sees exact interactions ("Nimbusware" + "CGPA") and scores relevance better. It's slower, so it only reorders the 20 fused candidates.

**A10. How do you chunk documents, and why that size?**
Split at markdown headings first, then pack into about 180 words with a 30-word overlap, keeping the heading path in each chunk (`chunk_document`). 180 words holds one rule with context; the overlap keeps a sentence whole across a boundary; the heading tells you whose rule it is.

**A11. How do citations work, and how do you know they're real?**
Passages are numbered in the prompt, and rule 2 says to cite every fact as [n]. `filter_output` then keeps only numbers 1 to 5 and the router rejects an answer with no valid citation. The evaluation also checks citation accuracy: whether the cited passage actually supports its sentence (93.2% final).

**A12. When does PlaceMate refuse, and why refuse before calling the model?**
When the best rerank score is below 0.0, when the question names something in no document (`unknown_terms`, e.g. "Google"), or when the model replies `NOT_IN_DOCUMENTS`. Refusing early is cheaper and faster, and the model can't hallucinate if it isn't asked.

**A13. How did you pick the refusal threshold?**
The cross-encoder outputs a logit; above 0 roughly means "relevant". I checked it on the evaluation set: with the unknown-name check, the final run refused all 6 traps and answered all 25 answerable questions. It is a setting (`RERANK_REFUSAL_THRESHOLD`), so it can be tuned.

**A14. What happens if Gemini is down?**
`router.generate` falls back to the local Qwen 0.5B model, then to the extractive answerer, which picks source sentences and can't hallucinate. The badge shows which answered. The app works with no key at all.

**A15. Why temperature 0.1?**
The answers are factual; I want the same answer to the same question, not creative wording. Low temperature makes the output nearly deterministic. The local model uses greedy decoding for the same reason.

### Tools and the agent

**A16. Why is eligibility a tool and not an LLM answer?**
It is `>=`, `<=` and "is in the list". Code is always right about that, explains each criterion, and can be unit-tested (35 tests in `backend/tests/test_eligibility.py`, edge cases such as exactly-equal CGPA and missing profile fields). An LLM can misread 7.8 vs 8.0 or invent an exception.

**A17. How is the resume match score calculated?**
Match % = 60% skill score + 40% semantic score. Skill score = 75% of required skills found + 25% of preferred. Semantic = MiniLM similarity between resume chunks and job-description chunks, rescaled from 0.15–0.60 to 0–1. The formula is shown in the UI.

**A18. Describe the agent loop.**
`make_plan` gives six fixed steps. `execute_run` runs each: check the 8-call budget, call the step, retry up to 2 times on failure, then use a fallback (required step), skip (optional step) or stop the run. State is saved after every step. It stops at the approval gate.

**A19. Why is the agent's plan made by rules and not by the LLM?**
The goal always has the same shape, so rules make it predictable, testable and identical across providers, even offline. The LLM only writes the short cited summary at the top; if that fails, a template is used.

**A20. How does the approval step work?**
At the gate the plan and the application are kept in `state.pending`; nothing is in the plans or applications tables. Approve → `approve_run` writes both in one transaction. Reject writes nothing. A second approve gets 409. This is human-in-the-loop for anything that changes the student's data.

**A21. How does the agent recover from errors? Show me.**
On the Prep agent page choose "Process search fails once": step 3 fails, is retried and shows "Recovered after retry". If it failed every time, the fallback reads the rounds from the company profile. An optional step that keeps failing is skipped and the plan still comes out. In the evaluation this took agent task success from 33% to 100%.

**A22. What stops the agent looping forever?**
The budget: `AGENT_MAX_STEPS` = 8 tool calls including retries. When it's reached, the run stops with "the run reached its limit" and nothing is saved.

### Evaluation and testing

**A23. How did you evaluate the system?**
47 hand-written cases (25 answerable, 6 traps, 6 injections, 4 ambiguous, 6 agent tasks), run in a baseline mode (vector only, no guards, naive agent) and the final mode. All metrics are computed by code in `eval/metrics.py`: no LLM judge, so results are repeatable.

**A24. What are Hit@3 and MRR?**
Hit@3: is a correct source document in the top 3 passages? MRR: 1 / rank of the first correct one, averaged (rank 1 → 1.0, rank 2 → 0.5). Both were high in both modes (Hit@3 100%) because the corpus is small; MRR rose from 0.98 to 1.00.

**A25. How do you measure groundedness without an LLM judge?**
A sentence counts as supported if at least 60% of its content words appear in a retrieved passage, or its embedding is at least 0.72 cosine-similar to a passage sentence. Groundedness = supported sentences / all sentences (98.3% final).

**A26. What were the main results?**
With Gemini, baseline → final: answer quality 92 → 100%, refusal accuracy 93.5 → 100%, injection blocking 0 → 100%, agent success 33 → 100%. The costs: median latency 3.3 → 5.4 s, citation accuracy 96.9 → 93.2%.

**A27. Why did citation accuracy go down?**
The final system answers more questions with longer answers that cite several passages per sentence ("[1][2][4]"), and some extra citations point at related passages that only partly support the sentence. Fix: cite only the passage that states each fact, and drop citations the support check rejects.

**A28. What did the evaluation find that you then fixed?**
Three things. "Minimum CGPA for Google?" got another company's rule → added `unknown_terms`. When Gemini timed out, an unusable local answer was shown → added the answer quality gate (`answer_problem`). An extractive list intro rendered badly → fixed. Each fix got its own unit test outside the eval set.

**A29. How is the code tested?**
380 pytest tests at 96% line coverage (tools, API, auth, roles, validation, rate limits, RAG, refusal, agent paths, injection, PII), and 18 Playwright end-to-end tests of the main flows. Tests force the extractive provider, so they never call Gemini and always give the same result.

### Security

**A30. How do you defend against prompt injection?**
In layers: an input guard (normalise, then patterns) blocks before retrieval; uploaded documents have instruction-like lines removed; retrieved passages are scanned again; the prompt marks sources as data inside tags with angle brackets neutralised; a canary detects prompt leaks; the output filter strips links and fake citations. It blocked 6/6 injection attempts in the evaluation.

**A31. How is PII handled?**
`redact_pii` removes emails, phone numbers, address lines and profile links from a resume **first**, so the skill extractor, the embeddings and any LLM only see redacted text. Logs pass through a scrub filter, and stored questions are scrubbed too. The UI shows the student what was removed.

**A32. How do authentication and roles work?**
argon2id password hashes; login returns a JWT in an httpOnly cookie (JavaScript can't read it); every request decodes it and loads the user from the DB, so the role comes from the DB, not the token. `require_role` gives 403 for the wrong role, and queries always filter by the user's id.

**A33. What other protections are there?**
Rate limits (login 10/min, API 120/min), CORS for one origin, an origin check on state-changing requests, security headers, Pydantic validation with unknown fields rejected, upload checks (size, type, real content, filename, duplicates), one error format with no stack traces, secrets only in `.env`.

### Limits and scaling

**A34. What are the limitations?**
The eval set is small, self-written and used during development (optimistic numbers, no held-out set). 34 documents make retrieval easy. Pattern-based injection detection can miss new phrasings. The local model is slow on CPU. The rate limiter is in memory.

**A35. How would you scale this to many colleges?**
Postgres instead of SQLite, a managed vector store (pgvector or Qdrant) with one collection per college, a shared rate-limit store (Redis), several backend processes behind a load balancer, a response cache for repeated questions, SSO login, and background jobs for re-indexing large uploads.

---

## Part B. General AI and GenAI

**B1. Overfitting vs underfitting?**
Overfitting: the model learns the training data, noise included, so training accuracy is high and validation accuracy is low. Underfitting: too simple to learn the pattern, so both are low. Fixes: more data, regularisation, dropout or early stopping for overfitting; a bigger model or better features for underfitting.
*In PlaceMate:* my refusal threshold and fixes were tuned on the same eval set, a kind of overfitting to it; that's why I say a held-out set is needed. **Your example:** ___

**B2. Why split data into train, validation and test?**
Train fits the model; validation chooses hyperparameters and when to stop; test is touched once at the end to estimate real performance. Using the test set for decisions leaks it and makes the score optimistic.
*In PlaceMate:* my 47 cases acted as validation, not a true test set. **Your example:** ___

**B3. Precision, recall, F1?**
Precision: of what I flagged, how much was right (TP / (TP+FP)). Recall: of what was really there, how much I found (TP / (TP+FN)). F1: their harmonic mean, useful when classes are imbalanced.
*In PlaceMate:* the injection guard needs high recall (catch attacks) without hurting precision (no false blocks on normal questions; there were 0 false refusals). **Your example:** ___

**B4. ROC-AUC?**
The ROC curve plots true-positive rate against false-positive rate as the decision threshold moves; AUC is the area under it, 0.5 = random, 1.0 = perfect. It measures ranking quality independent of one threshold.
*In PlaceMate:* the refusal threshold on the rerank score is exactly such a threshold choice. **Your example:** ___

**B5. What is feature engineering?**
Turning raw data into inputs a model can use: scaling, encoding categories, combining columns, extracting signals. Good features often matter more than the model choice.
*In PlaceMate:* skill extraction from resume text, and the heading path added to each chunk, are hand-made features. **Your example:** ___

**B6. How does a CNN work, and what is transfer learning?**
Convolution filters slide over an image to detect local patterns (edges, then shapes), with pooling to reduce size; later layers combine them. Transfer learning reuses a model pretrained on a big dataset (e.g. ImageNet) and retrains only the last layers on your small dataset.
*In PlaceMate:* the same idea, for text: I use pretrained MiniLM and a pretrained cross-encoder instead of training my own. **Your example:** ___

**B7. What are tokens and the context window?**
Models read tokens (word pieces, roughly ¾ of a word in English). The context window is the maximum tokens of input + output per call. Longer prompts cost more and are slower, and models attend less well to the middle of long contexts.
*In PlaceMate:* I send only the top 5 passages of about 180 words, and the local model only 3 passages cut to 700 characters.

**B8. What does temperature do?**
It scales the randomness of sampling the next token: near 0 = almost always the most likely token (consistent, factual), higher = more varied and creative.
*In PlaceMate:* 0.1 for Gemini, greedy decoding for the local model, because answers must be factual and repeatable.

**B9. Zero-shot vs few-shot prompting?**
Zero-shot: just instructions. Few-shot: instructions plus a few worked examples in the prompt, which helps with format and edge cases at the cost of more tokens.
*In PlaceMate:* zero-shot with very explicit rules; the citation format "[1] or [1][3]" is shown inline. **Your example:** ___

**B10. How do you get structured output from an LLM reliably?**
Ask for a fixed format (JSON or a schema), use the provider's JSON/schema mode if it has one, then **validate** with code (e.g. Pydantic) and retry or fall back if it fails. Never trust it unchecked.
*In PlaceMate:* answers are checked by code (citations parsed and bounded, `NOT_IN_DOCUMENTS` token, quality gate) and rejected answers fall through to the next provider. **Your example:** ___

**B11. What are embeddings?**
Vectors that represent meaning: texts with similar meaning are close together (high cosine similarity). They come from a model trained so that related pairs end up near each other.
*In PlaceMate:* MiniLM, 384 dimensions, normalised, for retrieval and resume similarity.

**B12. What is a vector database, and do you need one?**
A store that finds the nearest vectors quickly (often with approximate indexes such as HNSW or IVF) and adds filtering, persistence and scaling. For small data an in-memory exact index is enough.
*In PlaceMate:* FAISS `IndexFlatIP` (exact search) over 227 chunks, saved to disk. With thousands of documents I'd move to pgvector or Qdrant.

**B13. Why does chunking matter?**
Too big: the passage mixes topics, the embedding gets vague and wastes context. Too small: a rule loses its context. Overlap prevents cutting a fact in half; keeping headings keeps meaning.
*In PlaceMate:* 180 words, 30-word overlap, heading-aware.

**B14. RAG vs fine-tuning: when to use each?**
RAG gives the model facts at question time: good for changing knowledge, citations and access control. Fine-tuning changes the model's behaviour or style using examples: good for format or a specialised task, bad for facts that change.
*In PlaceMate:* RAG, because placement rules change every season and every answer needs a source.

**B15. What is hallucination, and how do you reduce it?**
The model states something fluent but false or unsupported. Reduce it with grounding (RAG), explicit "say you don't know" instructions, refusing when retrieval is weak, low temperature, citation checks, and measuring it.
*In PlaceMate:* hallucination rate on traps was 0% with Gemini; with the extractive fallback it dropped from 100% (baseline) to 16.7%.

**B16. What is prompt injection, and what are the direct and indirect kinds?**
Text that tries to override the system's instructions. Direct: the user types it ("ignore previous instructions"). Indirect: it hides in data the model reads (a document, a web page, an email).
*In PlaceMate:* both are handled, the input guard for direct and document sanitising + passage scanning for indirect (the "planted instructions" notice demo).

**B17. What is function calling (tool use)?**
The model is given tool descriptions; instead of text it returns "call tool X with arguments Y"; your code runs the tool and gives the result back. It lets a model use exact computation and live data.
*In PlaceMate:* tools exist, but the agent's steps are chosen by rules, not by the model, for predictability. The same tools could be exposed as function calls to a model-driven agent. **Your example:** ___

**B18. What is an agent, and what makes one safe?**
An LLM-based loop that plans, calls tools, looks at results and continues until the goal is done. Safety: limited tools, a step budget, retries with limits, saved state, validation of tool inputs and outputs, and human approval before irreversible actions.
*In PlaceMate:* all of those: 8-call budget, 2 retries, fallbacks, state saved per step, approval before saving.

**B19. How do you evaluate an LLM application?**
Separate retrieval (Hit@k, MRR), answer quality (correct facts, groundedness, citation accuracy), safety (refusal, hallucination, injection), task success for agents, and latency and cost. Use a fixed test set, compare to a baseline, and prefer deterministic metrics or a judge checked against human labels.
*In PlaceMate:* exactly this, in `eval/`, baseline vs final.

**B20. What is the difference between a bi-encoder and a cross-encoder?**
A bi-encoder embeds each text separately (fast, vectors can be precomputed, used for search). A cross-encoder reads the pair together and outputs one relevance score (more accurate, but must run per pair, so it is used to rerank a short list).
*In PlaceMate:* MiniLM bi-encoder to search, ms-marco cross-encoder to rerank 20.

**B21. What is BM25?**
A keyword ranking function: a term counts more if it is rare across documents (IDF) and frequent in this document, with diminishing returns (k1) and a length normalisation (b).
*In PlaceMate:* `rank_bm25.BM25Okapi` with a custom tokenizer that keeps "c++" and "7.5" and folds simple plurals.

**B22. Why validate LLM and user input with schemas?**
Inputs from users and outputs from models are untrusted. A schema rejects wrong types, missing fields and oversized values early, with a clear error, instead of failing deep inside the code.
*In PlaceMate:* Pydantic models in `schemas.py` (`StrictModel` forbids unknown fields; question ≤ 2000 characters).

**B23. What are the main costs and latency drivers of an LLM app?**
Tokens in and out (price and time), the number of calls per request, model size, and network. Reduce with shorter prompts, smaller models where good enough, caching, streaming (feels faster), and skipping the model when code can answer.
*In PlaceMate:* refusals and blocks cost no model call and return in milliseconds; answers stream.

**B24. What is model drift, and how would you monitor it here?**
Quality changes over time because the data, the users' questions or the provider's model change. Monitor by logging, re-running the eval set regularly and tracking metrics.
*In PlaceMate:* the analytics "not answered" list shows new gaps, and `scripts\eval.ps1` can be re-run after any model or document change.

**B25. What is the difference between AI, ML, deep learning and GenAI?**
AI is the broad goal of machines doing intelligent tasks. ML learns patterns from data instead of hand-written rules. Deep learning is ML with multi-layer neural networks. GenAI is deep learning that generates new content (text, images), usually with large pretrained models.
*In PlaceMate:* GenAI writes answers; classic deterministic code makes the decisions. **Your example:** ___
