# Research notes

What current AI career tools and RAG products look like, and what that means for PlaceMate.

- **Run on:** 2026-11-14, with the Last30days skill (window 2026-10-15 to 2026-11-14) plus web search.
- **Coverage:** Reddit (17 threads), Hacker News (13 stories), GitHub (4 items), and 15 web pages. X, YouTube and TikTok were not configured on this machine, and the Polymarket lane timed out, so none of those are represented.
- **Honest caveat:** recent community discussion of *campus placement* copilots specifically was thin. Most career-tool material came from vendor pages, so those claims are treated as descriptions of what exists, not as proof that it works. The RAG and agent-UX findings rest on firmer ground.

## Takeaways

### 1. Career tools are converging on one bundle, and none of them know a college's own rules

The current products all ship the same three features: resume analysis, job-description matching and interview prep. Examples are [Career Copilot for Indian freshers](https://topai.tools/t/career-copilot), the all-in-one tools described in a [University of Calgary career-services write-up](https://ucalgary.ca/news/job-search-theres-ai), and [Jobscan's match rate](https://www.jobscan.co/blog/best-ai-resume-builders/). They are general-purpose. None answers "am I eligible for this company under my college's policy?" because that needs the placement cell's own documents.

**For PlaceMate:** the gap worth filling is the college-specific layer: cited answers from the placement policy and company documents, and eligibility decided by the college's actual rules. Resume match and prep are table stakes, so they are included but are not the headline.

### 2. A match score nobody can explain is not trusted

One guide on resume checkers says outright that a perfect score can just mean the tool over-weights keyword overlap, and that the better checkers [explain why a score changed](https://www.atsresumeai.com/blog/ai-resume-checker). Jobscan's pattern of a score plus specific missing skills is the established baseline.

**For PlaceMate:** the resume match shows the percentage together with the matched skills, the missing skills and how the score was computed. The eligibility check lists every criterion with its own pass or fail and the reason, never a bare verdict.

### 3. Hybrid retrieval with reranking is the default, but it has to be measured

Practitioner guides agree that adding BM25 to a vector-only setup is the [highest-impact retrieval upgrade](https://denser.ai/blog/hybrid-search-for-rag/), that [RRF with k=60](https://www.callmissed.com/blog/rag-best-practices-2026) is the usual fusion starting point, and that the standard shape is [hybrid for recall, cross-encoder for precision](https://dataaspirant.com/blog/hybrid-search/). BM25 matters most for exact tokens such as names and codes ([Indexical](https://indexical.dev/knowledge/what_are_the_best_hybrid_search_reranking_strategies_for_production_rag_systems_in_2026.php)), which in our data means company names, CGPA cut-offs and round names. One guide also warns that a [badly tuned hybrid can lose to dense-only](https://aiworkflowlab.dev/article/how-to-build-hybrid-search-rag-bm25-rrf-fusion-cross-encoder-reranking).

**For PlaceMate:** BM25 + vectors fused with RRF, then a cross-encoder rerank. The evaluation runs the vector-only baseline against the final pipeline on the same labelled questions (Hit@3, MRR), so the improvement is a measured number and not an assumption.

### 4. Citations have to show the retrieved text, not just a file name

The most common UI pattern is numbered inline markers that link to source cards with title and excerpt ([AI SDK Patterns](https://ai-sdk-patterns.vercel.app/patterns/chat-with-citations)). A compliance-oriented guide makes the sharper point that printing only a source name is cosmetic: the reader must be able to see [the exact text that was retrieved](https://theneuralbase.com/conversational-ai/learn/intermediate/citation-and-source-display/). A recent [RAG take-home spec on GitHub](https://github.com/dragomir-parvanov/epam-preescreen-task-rag/issues/1) treats "a chat UI that shows the document citations behind each answer" as a baseline requirement.

**For PlaceMate:** inline `[1][2]` chips open source cards showing the document, the snippet that was actually retrieved, and its score. A citation that points at a chunk the model was never given is counted as an error in the evaluation (citation accuracy).

### 5. Keep retrieval a fixed step; use an agent only where one search is not enough

The author of the RAG_Techniques repo summarised his rule on r/Rag: ["keep retrieval a fixed step until one search stops being enough"](https://www.reddit.com/r/Rag/comments/1xfzz0v/im_the_author_of_the_rag_techniques_and_genai/). A separate r/Rag thread asks whether [anyone is getting real value or just stuck in POCs](https://www.reddit.com/r/Rag/comments/1x8a9hi/is_gen_ai_actually_generating_real_value_or_is/), which is the cost of forcing agents everywhere.

**For PlaceMate:** ordinary questions go through a fixed RAG pipeline. The agent exists only for "Prepare me for <company>", which really does need several steps (eligibility, resume match, two retrievals, a plan). This matches the brief's instruction not to force every technique.

### 6. Deterministic work belongs in code, not in the model's context

On r/AI_Agents, the top reply to someone asking an LLM to categorise 2,000 transactions was: ["don't feed 2000 rows into a single chat window, context decay is why it hallucinates at the bottom."](https://www.reddit.com/r/AI_Agents/comments/1xjq94a/which_ai_would_you_recommend_for_categorising/) In the r/Rag thread on an open-sourced platform, a commenter advised keeping LLM-written hints ["separate from the original chunk"](https://www.reddit.com/r/Rag/comments/1xijlbb/i_opensourced_my_rag_platform_chatviaai/) and labelled as derived text.

**For PlaceMate:** eligibility (CGPA, backlogs, branch, batch) and application tracking are plain functions over structured data. The LLM never decides whether a student is eligible; it only words the explanation. Index chunks stay as the original document text.

### 7. Approval must come before the side effect, and show exactly what will be saved

Human-in-the-loop write-ups ([Cloudflare Agents docs](https://developers.cloudflare.com/agents/concepts/agentic-patterns/human-in-the-loop/), [tool approval patterns](https://www.kunalganglani.com/blog/tool-approval-patterns-ai-agents), [StackAI](https://www.stackai.com/insights/human-in-the-loop-ai-agents-how-to-design-approval-workflows-for-safe-and-scalable-automation)) repeat the same points: let reads run freely and gate writes; pause, persist the run state, then resume on approve or reject; show the reviewer the real payload; and do not gate so many steps that approval becomes a rubber stamp. The mood on Hacker News this month backs the caution: [United Airlines banning AI agents from booking on travellers' behalf](https://www.cbsnews.com/news/united-airlines-bans-ai-agents-booking-flights/) drew a large thread.

**For PlaceMate:** the prep agent's read steps run without interruption. There is exactly one gate, before the only write (saving the plan and the application). The dialog shows the full week-by-week plan and the application record that will be created. The run is stored as `awaiting_approval` and nothing is written until the student approves.

### 8. Quiet data sharing destroys trust, so the privacy step is shown on screen

The highest-scoring privacy story in the window was Postman [auto-installing AI plugins and sharing request data](https://github.com/postmanlabs/postman-app-support/issues/14370). One Hacker News commenter [pointed out](https://news.ycombinator.com/item?id=50358055) that the tool "logs detailed information on every single API request you make", secrets included.

**For PlaceMate:** phone numbers, emails and addresses are stripped from resume text before it reaches any LLM and are never written to logs. The Resume Match page shows what was removed, and the provider badge shows which model (or the offline extractive fallback) produced each answer.

## What this changed in the plan

| Finding | Design decision |
|---|---|
| Generic tools lack college rules | College documents and policy-driven eligibility are the core feature |
| Unexplained scores are distrusted | Every score and verdict comes with its reasons |
| Hybrid + rerank is standard but must be measured | Baseline vs final evaluation on the same question set |
| Citations must show retrieved text | Source cards with the real snippet and score; citation accuracy metric |
| Agents only where needed | One agent, one goal; everything else is fixed pipelines and tools |
| Gate writes, not reads | A single approval gate before the save |
| Hidden data flows lose users | PII redaction and provider badge are visible in the UI |

## A note for the student audience

A comment on r/developersIndia, replying to a developer worried about AI skills, put the learning curve plainly: ["The AI skills you mentioned barely takes a day to understand. Python fundamentals and fast api, a week Max if you're completely new to backend."](https://reddit.com/r/developersIndia/comments/1xcwjqd/35_yoe_frontend_developer_recently_laid_off_and/19rice9669ezo/) The prep guides in the sample data are written in that spirit: concrete and time-boxed.

## Current docs checked (Context7, 2026-11-14)

| Library | What was confirmed |
|---|---|
| FastAPI | `lifespan` context manager for startup resources; `@app.exception_handler` for `RequestValidationError` and HTTP errors |
| Next.js 16 | `proxy.ts` replaces `middleware.ts` for optimistic cookie checks; it must not be the only line of defence |
| shadcn/ui | `npx shadcn@latest init`; MCP via `npx shadcn@latest mcp init --client claude` (writes `.mcp.json`) |
| AI Elements | `npx ai-elements@latest add <component>` (conversation, message, sources, inline-citation, reasoning, tool) |
| google-genai | `genai.Client(api_key=..., http_options=types.HttpOptions(timeout=...))`, `client.models.generate_content(..., config=types.GenerateContentConfig(system_instruction=..., temperature=..., max_output_tokens=...))`, errors in `google.genai.errors` |
| Gemini models | `gemini-2.x` is no longer current. GA Flash models are `gemini-3.6-flash` and `gemini-3.5-flash-lite`; the exact free-tier model is confirmed with a live call in Phase 4 |
| Lenis + GSAP | `lenis.on('scroll', ScrollTrigger.update)`, drive `lenis.raf` from `gsap.ticker`, `gsap.ticker.lagSmoothing(0)`; `ReactLenis` with `autoRaf: false` |
