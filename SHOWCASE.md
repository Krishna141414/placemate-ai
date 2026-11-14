# SHOWCASE.md - PlaceMate UI, showcase and Guided Tour (follow exactly)

Industry-level product look. Must NOT look AI-generated or like a colorful demo. Think Linear / Vercel / Stripe dashboard quality.

## Visual identity
- **Palette (white + navy):** background `#FFFFFF` / subtle `#F8FAFC`, navy `#0B1F3A` (primary text, sidebar, hero), slate `#475569` (muted), primary accent `#1D4ED8` (buttons, links, active), soft accent `#DBEAFE` (highlights, selected rows), success `#15803D`, warning `#B45309`, error `#B91C1C`, borders `#E2E8F0`. Dark mode: navy `#0B1220` surfaces with the same accents.
- Typography: Inter (or Geist) with a clear scale; numbers tabular. 8px grid, generous whitespace, 12px radius, thin borders, soft shadows. Lucide icons. No neon, no rainbow gradients, no glassmorphism overload, no Aceternity.
- Run **Hallmark study** before designing and **Hallmark audit** after every page; fix what it flags.

## 1. Landing / Showcase page (`/`) - scroll storytelling (GSAP + ScrollTrigger + Lenis)
1. **Hero:** headline + subline (Humanizer copy), two CTAs ("Try the demo" -> login with demo account, "How it works" -> scroll). Product preview card that animates in (chat answer with citations typing).
2. **The problem:** 3 short stat/pain cards that reveal on scroll.
3. **Product walkthrough (pinned section):** as you scroll, a pinned device frame swaps through the 4 core features (Ask with citations -> Eligibility check -> Resume match -> Prep agent with approval), each with a short caption.
4. **How it works (animated pipeline):** scroll-driven diagram: Question -> Hybrid retrieval (BM25 + vectors) -> Rerank -> Grounded answer with citations; and a second track for the agent: Plan -> Tools -> Approval -> Saved plan. Lines draw themselves, nodes light up.
5. **Built responsibly:** security + evaluation highlights (injection blocked %, groundedness, tests passing) as count-up numbers from real results.
6. **Tech stack** row + footer (author Krishna, GitHub link).
- Respect `prefers-reduced-motion` (no scroll-jacking then).

## 2. App (after login) - sidebar navigation, separate pages (NOT one long scroll)
Each page has ready-made example inputs/buttons so every feature can be shown instantly.
1. **Dashboard** - welcome, eligibility summary, upcoming deadlines, recent questions, prep-plan progress.
2. **Ask PlaceMate** (AI Elements chat) - example question chips (policy, company process, unanswerable, prompt-injection attempt). Answer streams in with inline [1][2] citations -> source cards (document, snippet, score); a collapsible "How this was answered" panel shows the pipeline steps (retrieved -> reranked -> generated -> guard checks) and the provider badge.
3. **Eligibility** - pick a company (or "check all") with the demo profile -> animated pass/fail per criterion (CGPA, backlogs, branch, batch) with reasons.
4. **Resume Match** - paste/upload resume (demo resume button) + choose company -> match % ring, matched vs missing skills chips, PII redaction shown ("phone and email removed before AI").
5. **Prep Agent** - goal "Prepare me for <company>" -> agent timeline (plan steps light up), tool-call cards (AI Elements tool UI), state panel, error-recovery shown if a step fails, then an **approval dialog** (Approve / Reject) before saving the week-by-week plan.
6. **Applications** - tracker table (status, deadlines), add/update.
7. **Coordinator: Documents** (admin role) - upload docs (validation errors shown), re-index progress, document list.
8. **Coordinator: Analytics** - top questions, unanswered questions, eligibility stats, provider usage (charts).
9. **Evaluation** - real eval results: baseline vs final per metric (charts), test summary + coverage, link to docs.
10. **Security** - one card per measure with a "Try it" (injection blocked, unauthorised admin call -> 403, oversized upload rejected, rate limit -> 429, PII redaction preview).
- Friendly 404 / 403 / 429 / 500 pages in the same design. Toasts, skeleton loaders, empty states.
- Demo accounts: `student@placemate.demo / Student@123`, `coordinator@placemate.demo / Coord@123` (seeded), with "Use demo account" buttons on login.

## 3. Guided Tour (for presenting)
- **Default mode is MANUAL:** nothing moves until I press Next (or →); Auto mode is optional and Pause freezes immediately. No animation or tour starts on page load - only when I click "Start Tour". I explain everything myself in my video, so I must control the pace.
- The tour bar is fixed (bottom-centre), always on top; captions/tooltips/popups must NEVER cover the bar or the highlighted element. No hover popups on the speed buttons.
- No raw JSON/dicts anywhere on screen: answers as formatted text with citation chips, sources as cards, logs as tables; raw API output only in a collapsed, syntax-highlighted block.
- Floating bar: **Start Tour, ◀ Back, ⏸ Pause / ▶ Play, Next ▶, step "5 / 22", Mode Manual / Auto (default Manual), speed Slow / Medium / Fast (default Medium), Exit.**
- One tour script covers: landing sections -> login as student -> Ask (cited answer, unanswerable, injection blocked) -> Eligibility -> Resume Match (with PII redaction) -> Prep Agent (incl. a recovered step + approval) -> Applications -> switch to coordinator -> Documents upload -> Analytics -> Evaluation -> Security "Try it"s.
- Each step navigates, spotlights the element (dim the rest), shows a caption naming the requirement it proves (e.g. "Security: resume PII is redacted before the LLM"), and performs the action automatically. Space = pause/play, arrows = back/next. Tour state survives navigation.

## Motion & speed
- Motion: page transitions, list stagger, hover/press states, dialog/drawer animations. GSAP only on the landing page.
- Medium pace by default: ~1.5-2 s between pipeline/agent steps, ~0.6-0.8 s reveals, count-ups ~1.2-1.5 s, tour ~3-4 s per step (waits for AI responses). All timings in ONE config (`lib/speed.ts`), Slow / Medium / Fast toggle shared by tour and animations.

## Done means
Playwright screenshots (desktop + mobile) of landing + every app page, Hallmark audit + Vercel Web Design Guidelines audit fixed, full Guided Tour works (auto + pause + manual) with real responses, no console or server errors.
