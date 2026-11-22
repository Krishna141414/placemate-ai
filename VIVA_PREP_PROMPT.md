# VIVA_PREP_PROMPT.md - Task 15 viva preparation (run inside the PlaceMate repo)

Context: My Task 15 is a live viva with a mentor about my Task 14 project (PlaceMate, this repo). Official brief: "Demonstrate independent understanding of AI, GenAI and completed project work. Explain the final project's requirements, architecture, data flow, model/LLM choices, prompts, retrieval/tool/agent workflow where applicable, evaluation and important code. Diagnose an issue and perform a small live modification requested by the mentor."

Read the whole codebase and docs first. Everything you write must match the REAL code (file paths, function names, numbers). Write simply - I must be able to explain it in my own words. Put everything in `docs/viva/`. Do NOT change application code on `main`.

## Step 1 - Readiness check
- A fresh-clone test was already done at the end of Task 14 (it passed), so don't repeat it. Just confirm demo logins, both servers start (`npm run dev:all`), and the Guided Tour works. Use `npm run reset-demo` for clean data. Note anything I must prepare on viva day in `docs/viva/00_viva_day_checklist.md` (what to open, `.env`, start commands, backup plan if the LLM/API fails).

## Step 2 - `docs/viva/01_walkthrough_script.md`
A 5-7 minute spoken script: problem -> users -> requirements -> architecture -> live demo order (which page, what to click, what to say) -> evaluation results -> security -> limitations -> future work.

## Step 3 - `docs/viva/02_architecture_and_data_flow.md`
Simple diagram + step-by-step data flow for each feature (Ask/RAG, Eligibility, Resume Match, Prep Agent with approval, Document upload/re-index, Login/auth): request -> which endpoint -> which functions in order (file:function) -> what's stored -> response.

## Step 4 - `docs/viva/03_models_prompts_choices.md`
Every model and why (LLM providers + fallback order, embedding model, reranker), key parameters and why (chunk size/overlap, top-k, thresholds, temperature, max tokens), every prompt in full with an explanation of each part, and "what I'd change with more resources".

## Step 5 - `docs/viva/04_code_map.md`
The ~15 most important functions/classes: file path, what it does in plain English, inputs/outputs, how it connects to others. Plus where to look for: config, logs, DB models, tests, eval.

## Step 6 - `docs/viva/05_questions_and_answers.md`
~60 likely viva questions with short, clear answers (2-4 lines each):
- PlaceMate-specific (~35): design decisions, RAG pipeline, hybrid search vs vector only, reranking, citations, refusal, tools vs LLM, agent loop, approval, error recovery, evaluation metrics and results, testing, security (injection, PII redaction, auth/roles, rate limiting), limitations, scaling.
- General AI/GenAI (~25), linked to my Tasks 1-14: overfitting vs underfitting, train/val/test, metrics (precision/recall/F1/ROC-AUC), feature engineering, CNN + transfer learning, tokens/context/temperature, zero/few-shot, structured output + validation, embeddings + vector DBs, chunking, RAG vs fine-tuning, hallucination, prompt injection, function calling, agents, evaluation of LLM apps.

## Step 7 - `docs/viva/06_diagnose_drills.md` + branch `viva-practice`
- Create a branch `viva-practice` (never touch `main`). Plant ~8 realistic bugs, ONE commit each, each tagged `drill-1` ... `drill-8`, e.g.: wrong env var name, broken import, off-by-one in chunking overlap, retrieval threshold too high (everything "not found"), eligibility comparison flipped (>= vs <), missing auth check on an admin route, prompt missing the citation instruction, frontend calling the wrong API path.
- In the doc, for each drill: the symptom I'd see (NOT the answer), then a hidden "Solution" section below with cause, how to find it (logs/tests/debugging steps), and the fix. Add a general debugging checklist (read the error, check logs, reproduce, run the test, check recent change, use the debugger/print, fix, re-test).

## Step 8 - `docs/viva/07_live_modification_drills.md`
~10 small changes a mentor might ask, each with: the request, which files to touch, step-by-step how to do it, how to test it, expected time. Examples: add a new eligibility criterion (e.g. minimum 10th/12th %), change chunk size and re-index, add a new field to the resume match output, add a new example question chip, change the refusal threshold, add a new tool to the agent, change the system prompt tone, add a new API endpoint, add a column to the applications table, change a UI label/colour/theme token.

## Step 9 - Finish
Commit `docs/viva/` to `main` and push; push the `viva-practice` branch too. Reply with a short summary of the files and how I should use them.
