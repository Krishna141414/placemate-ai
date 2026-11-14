# PROGRESS

Resume rule: read `CLAUDE.md` and this file, then continue `BUILD_PROMPT.md` from the first unfinished step.

## Status

| Phase | Name | Status |
|---|---|---|
| 0 | Preflight | done |
| 1 | Research & plan | next |
| 2 | Data | todo |
| 3 | Backend core | todo |
| 4 | RAG | todo |
| 5 | Tools & agent | todo |
| 6 | Tests & evaluation | todo |
| 7 | Frontend app | todo |
| 8 | Landing showcase + Guided Tour | todo |
| 9 | Verify | todo |
| 10 | Docs & finish | todo |

## Next step

Phase 1, step 1: Last30days research on AI career/placement copilots and RAG product UIs -> `docs/research.md`.

## Phase 0 - Preflight (done 2026-11-14)

### 0.1 Runtimes
- Python 3.14.0 is the only Python installed (`py -0` lists just 3.14). No 3.12 fallback available.
- CPU PyTorch wheel exists for it: `torch-2.15.0+cpu-cp314-cp314-win_amd64` from `https://download.pytorch.org/whl/cpu`. So the venv uses Python 3.14.
- Binary wheels also confirmed for cp314: `faiss-cpu 1.16.0`, `tokenizers 0.23.3`, `safetensors 0.8.0`, `bcrypt 5.0.0`, `argon2-cffi-bindings 26.2.0`, `pymupdf 2.1`.
- Node v24.11.1, npm 11.6.2, git 2.52.0.
- `gh` CLI is not installed. Not needed: plain `git push` over HTTPS reaches the repo.
- Remote `origin` = `https://github.com/Krishna141414/placemate-ai.git` (repo existed and was empty).

### 0.2 Toolkit available
- Plugins: Superpowers 7.0.2, Last30days 3.31.0, Diagram Design 2.6.142, Humanizer 3.1.0.
- MCP: Playwright (connected), Context7 (connected).
- Global skills: hallmark, gsap-core, gsap-timeline, gsap-scrolltrigger, gsap-react, gsap-performance, gsap-plugins, gsap-utils, gsap-frameworks, web-design-guidelines, humanizer, find-skills.
- shadcn MCP and AI Elements are per-project; set up inside `frontend/` in Phase 7.

### 0.3 Hugging Face cache (all present, nothing to download)
- `Qwen/Qwen2.5-0.5B-Instruct` (model.safetensors 942 MB)
- `sentence-transformers/all-MiniLM-L6-v2` (87 MB)
- `cross-encoder/ms-marco-MiniLM-L-6-v2` (87 MB)

### 0.4 Scaffold
- Folders: `backend/`, `frontend/`, `eval/`, `docs/`, `scripts/`, `screenshots/.gitkeep`.
- `.gitignore`, `.env.example`, `PROGRESS.md` created.

## Notes / decisions taken without asking
- `.gitignore` deliberately avoids broad patterns like `lib/`, `data/` or `build/` so `frontend/lib` and `backend/data` are never hidden.
- Runtime artefacts (SQLite DB, FAISS/BM25 index, uploads, logs) all live under `backend/storage/`, which is ignored as one folder.
