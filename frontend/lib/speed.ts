"use client";

// All UI timings live here, so the guided tour and the in-app animations share
// one pace. Medium is the default, per SHOWCASE.md.

import { createContext, createElement, useCallback, useContext, useMemo, useSyncExternalStore, type ReactNode } from "react";

export type Speed = "slow" | "medium" | "fast";

export interface Timings {
  /** gap between revealing pipeline or agent steps */
  step: number;
  /** a reveal (fade / slide) */
  reveal: number;
  /** a number counting up */
  countUp: number;
  /** stagger between list items */
  stagger: number;
  /** how long the tour waits on a step in auto mode (after any action finished) */
  tourStep: number;
  /** delay between typed characters when the tour fills an input */
  typing: number;
}

export const SPEEDS: Record<Speed, Timings> = {
  slow: { step: 2400, reveal: 900, countUp: 1800, stagger: 110, tourStep: 5200, typing: 38 },
  medium: { step: 1700, reveal: 700, countUp: 1350, stagger: 70, tourStep: 3600, typing: 22 },
  fast: { step: 800, reveal: 400, countUp: 800, stagger: 40, tourStep: 2000, typing: 10 },
};

const STORAGE_KEY = "pm-speed";

interface SpeedContextValue {
  speed: Speed;
  setSpeed: (speed: Speed) => void;
  t: Timings;
  /** true when the user prefers reduced motion: animations collapse to instant */
  reduced: boolean;
}

const SpeedContext = createContext<SpeedContextValue | null>(null);

const SPEED_EVENT = "pm-speed-change";

function readStored(): Speed {
  try {
    const value = window.localStorage.getItem(STORAGE_KEY);
    if (value === "slow" || value === "medium" || value === "fast") return value;
  } catch {
    // storage unavailable: fall back to the default
  }
  return "medium";
}

function subscribeSpeed(callback: () => void) {
  window.addEventListener(SPEED_EVENT, callback);
  window.addEventListener("storage", callback);
  return () => {
    window.removeEventListener(SPEED_EVENT, callback);
    window.removeEventListener("storage", callback);
  };
}

const REDUCED_QUERY = "(prefers-reduced-motion: reduce)";

function subscribeReduced(callback: () => void) {
  const query = window.matchMedia(REDUCED_QUERY);
  query.addEventListener("change", callback);
  return () => query.removeEventListener("change", callback);
}

export function SpeedProvider({ children }: { children: ReactNode }) {
  // External stores: the server renders the defaults, the browser reads the real values.
  const speed = useSyncExternalStore<Speed>(subscribeSpeed, readStored, () => "medium");
  const reduced = useSyncExternalStore(subscribeReduced, () => window.matchMedia(REDUCED_QUERY).matches, () => false);

  const setSpeed = useCallback((value: Speed) => {
    try {
      window.localStorage.setItem(STORAGE_KEY, value);
    } catch {
      // ignore: the change still applies for this page
    }
    window.dispatchEvent(new Event(SPEED_EVENT));
  }, []);

  const value = useMemo<SpeedContextValue>(() => {
    const base = SPEEDS[speed];
    const t = reduced ? { ...base, reveal: 0, countUp: 0, stagger: 0, step: Math.min(base.step, 300) } : base;
    return { speed, setSpeed, t, reduced };
  }, [speed, setSpeed, reduced]);

  return createElement(SpeedContext.Provider, { value }, children);
}

export function useSpeed(): SpeedContextValue {
  const context = useContext(SpeedContext);
  if (!context) return { speed: "medium", setSpeed: () => {}, t: SPEEDS.medium, reduced: false };
  return context;
}

export const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

/**
 * Guided-tour limits. These are ceilings, not pacing: the tour moves on as soon
 * as the thing it waits for appears. Pacing comes from `Timings` above.
 */
export const TOUR_LIMITS = {
  /** waiting for a page's element to render after navigation */
  target: 12_000,
  /** waiting for a cited answer from the model */
  answer: 90_000,
  /** waiting for the prep agent to reach the approval step */
  agent: 180_000,
  /** waiting for an upload, a match or a live security check */
  action: 30_000,
  /** how long the scroll may take to settle before the spotlight is placed */
  settle: 1_200,
} as const;
