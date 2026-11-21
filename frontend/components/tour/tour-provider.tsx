"use client";

// Runs the guided tour: for each step it makes sure the right user is logged in,
// navigates, spotlights the target and, when moving forward, performs the
// step's actions. Manual by default; nothing starts until "Start tour".

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, type ReactNode } from "react";

import { api } from "@/lib/api";
import { DEMO_ACCOUNTS, useAuth } from "@/lib/auth";
import { TOUR_LIMITS, useSpeed } from "@/lib/speed";
import { TOUR_STEPS, type TourAction, type TourAuth, type TourStep } from "@/lib/tour-script";

import { TourBar } from "./tour-bar";
import { click, count, find, gate, hold, isTypingTarget, reveal, TourCancelled, TourTimeout, until, type RunContext } from "./tour-dom";
import { TourSpotlight } from "./tour-spotlight";
import { exitTour, goTo, tourStore, useTourState } from "./tour-store";

function routeMatches(route: string, exact: boolean): boolean {
  const want = new URL(route, window.location.origin);
  if (window.location.pathname !== want.pathname) return false;
  const have = new URLSearchParams(window.location.search);
  if (exact && have.toString() !== want.searchParams.toString()) return false;
  for (const [key, value] of want.searchParams) if (have.get(key) !== value) return false;
  return true;
}

export function TourProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const auth = useAuth();
  const { t, reduced } = useSpeed();
  const state = useTourState();

  // The runner reads these through refs so a login mid-step doesn't restart it.
  const routerRef = useRef(router);
  const authRef = useRef(auth);
  const speedRef = useRef({ t, reduced });
  useEffect(() => {
    routerRef.current = router;
    authRef.current = auth;
    speedRef.current = { t, reduced };
  });

  const ensureAuth = useCallback(async (want: TourAuth | undefined, ctx: RunContext) => {
    if (!want) return;
    await until(() => !authRef.current.loading, TOUR_LIMITS.target, ctx);
    const user = authRef.current.user;
    if (want === "visitor") {
      if (user) await authRef.current.logout();
      await until(() => authRef.current.user === null, TOUR_LIMITS.target, ctx);
      return;
    }
    if (user?.role === want) return;
    if (user) await authRef.current.logout();
    const account = DEMO_ACCOUNTS[want];
    await authRef.current.login(account.email, account.password);
    await until(() => authRef.current.user?.role === want, TOUR_LIMITS.target, ctx);
  }, []);

  const navigate = useCallback(async (step: TourStep, ctx: RunContext) => {
    const exact = Boolean(step.exactQuery);
    // Wait out any redirect already in flight (a logout sends app pages to /login).
    await new Promise((resolve) => setTimeout(resolve, 50));
    for (let attempt = 0; attempt < 3 && !routeMatches(step.route, exact); attempt++) {
      routerRef.current.push(step.route);
      try {
        await until(() => routeMatches(step.route, exact), TOUR_LIMITS.target / 3, ctx);
      } catch (error) {
        if (!(error instanceof TourTimeout)) throw error;
      }
    }
    if (!routeMatches(step.route, exact)) throw new TourTimeout();
  }, []);

  const spot = useCallback(async (target: TourStep["spot"], ctx: RunContext, wait = TOUR_LIMITS.target) => {
    if (!target) return;
    const el = await until(() => find(target), wait, ctx);
    tourStore.set({ spot: target });
    await reveal(el, !speedRef.current.reduced, TOUR_LIMITS.settle);
  }, []);

  const perform = useCallback(
    async (action: TourAction, ctx: RunContext) => {
      const { t: pace } = speedRef.current;
      await gate(ctx);
      switch (action.do) {
        case "hold":
          await hold(pace.step * action.steps, ctx);
          return;
        case "event":
          window.dispatchEvent(new Event(action.name));
          if (action.holdSteps) await hold(pace.step * action.holdSteps, ctx);
          return;
        case "spot":
          await spot(action, ctx);
          return;
        case "remove-upload": {
          // Housekeeping so the tour can be run more than once: the backend
          // rejects a second copy of the same file as a duplicate. Stored
          // names carry a unique prefix, so match on the end of the name.
          const documents = await api<{ id: number; filename: string; source: string }[]>("/api/admin/documents");
          for (const doc of documents.filter((d) => d.source === "upload" && d.filename.endsWith(`-${action.filename}`))) {
            await api(`/api/admin/documents/${doc.id}`, { method: "DELETE" });
          }
          return;
        }
        case "path":
          await until(() => window.location.pathname === action.path, action.timeout, ctx);
          return;
        case "wait":
          tourStore.set({ note: "Waiting for the result" });
          await until(
            () => {
              const el = find(action, action.status);
              if (!el) return null;
              if (action.filled) return (el as HTMLTextAreaElement).value?.trim() ? el : null;
              return el;
            },
            action.timeout,
            ctx,
          );
          tourStore.set({ note: null });
          return;
        case "click": {
          const wait = action.until;
          const before = wait ? count(wait.target) : 0;
          await click(action, TOUR_LIMITS.target, ctx);
          if (!wait) return;
          tourStore.set({
            note: wait.timeout >= TOUR_LIMITS.answer ? "Waiting for the answer" : "Waiting for the result",
          });
          await until(
            () => {
              if (wait.newItem && count(wait.target) <= before) return null;
              return find({ target: wait.target, last: wait.newItem }, wait.status);
            },
            wait.timeout,
            ctx,
          );
          tourStore.set({ note: null });
          return;
        }
      }
    },
    [spot],
  );

  const runStep = useCallback(
    async (step: TourStep, forward: boolean, ctx: RunContext) => {
      try {
        await ensureAuth(step.auth, ctx);
        await navigate(step, ctx);
        try {
          await spot(step.spot, ctx);
        } catch (error) {
          // A target that only exists after the step's action (or after a run
          // Back skips) is not an error: show the caption without a spotlight.
          if (!(error instanceof TourTimeout)) throw error;
        }
        if (forward) for (const action of step.actions ?? []) await perform(action, ctx);
        if (!ctx.cancelled) tourStore.set({ phase: "ready", note: null });
      } catch (error) {
        if (error instanceof TourCancelled || ctx.cancelled) return;
        tourStore.set({
          phase: "stuck",
          note: "This step did not finish in time. Press Next to go on.",
        });
      }
    },
    [ensureAuth, navigate, spot, perform],
  );

  // Run the current step whenever a new run starts (Start, Next, Back, reload).
  useEffect(() => {
    if (!state.active) return;
    const ctx: RunContext = { cancelled: false };
    const step = TOUR_STEPS[Math.min(state.index, TOUR_STEPS.length - 1)];
    void runStep(step, state.direction === "forward", ctx);
    return () => {
      ctx.cancelled = true;
    };
  }, [state.active, state.run, state.index, state.direction, runStep]);

  const next = useCallback(() => {
    const { index } = tourStore.get();
    if (index >= TOUR_STEPS.length - 1) exitTour();
    else goTo(index + 1, "forward");
  }, []);

  const back = useCallback(() => {
    const { index } = tourStore.get();
    if (index > 0) goTo(index - 1, "back");
  }, []);

  // Auto mode: move on after the step's action finished and the pause has passed.
  useEffect(() => {
    if (!state.active || state.mode !== "auto" || state.paused || state.phase === "running") return;
    const timer = setTimeout(next, t.tourStep);
    return () => clearTimeout(timer);
  }, [state.active, state.mode, state.paused, state.phase, state.run, t.tourStep, next]);

  // Space pauses or plays, arrows move. Keys typed into a field are left alone.
  useEffect(() => {
    if (!state.active) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.altKey || event.ctrlKey || event.metaKey || isTypingTarget(event.target)) return;
      if (event.key === " ") {
        // Also stops a focused button from being pressed by the same key.
        event.preventDefault();
        event.stopPropagation();
        if (event.type === "keydown" && !event.repeat) tourStore.set({ paused: !tourStore.get().paused });
        return;
      }
      if (event.type !== "keydown") return;
      if (event.key === "ArrowRight") {
        event.preventDefault();
        next();
      } else if (event.key === "ArrowLeft") {
        event.preventDefault();
        back();
      }
    };
    window.addEventListener("keydown", onKey, true);
    window.addEventListener("keyup", onKey, true);
    return () => {
      window.removeEventListener("keydown", onKey, true);
      window.removeEventListener("keyup", onKey, true);
    };
  }, [state.active, next, back]);

  return (
    <>
      {children}
      <TourSpotlight />
      <TourBar onNext={next} onBack={back} />
    </>
  );
}
