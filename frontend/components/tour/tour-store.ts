"use client";

// Tour state lives outside React so it survives page navigation, and the
// persistent part is kept in sessionStorage so a reload resumes the same step.

import { useSyncExternalStore } from "react";

import type { TourTarget } from "@/lib/tour-script";

export type TourMode = "manual" | "auto";
export type TourPhase = "running" | "ready" | "stuck";

export interface TourState {
  active: boolean;
  index: number;
  mode: TourMode;
  paused: boolean;
  phase: TourPhase;
  /** forward runs the step's actions; back and restore only show it */
  direction: "forward" | "back" | "restore";
  /** bumps on every step start, so the runner re-runs even on the same index */
  run: number;
  spot: TourTarget | null;
  /** a short status line under the caption ("Waiting for the answer") */
  note: string | null;
}

const KEY = "pm-tour";

const INITIAL: TourState = {
  active: false,
  index: 0,
  mode: "manual",
  paused: false,
  phase: "ready",
  direction: "forward",
  run: 0,
  spot: null,
  note: null,
};

let state: TourState = INITIAL;
let hydrated = false;
const listeners = new Set<() => void>();

function hydrate() {
  if (hydrated || typeof window === "undefined") return;
  hydrated = true;
  try {
    const saved = JSON.parse(window.sessionStorage.getItem(KEY) ?? "null") as Partial<TourState> | null;
    if (saved?.active) {
      state = {
        ...INITIAL,
        active: true,
        index: Number(saved.index) || 0,
        mode: saved.mode === "auto" ? "auto" : "manual",
        paused: Boolean(saved.paused),
        direction: "restore",
        run: 1,
      };
    }
  } catch {
    // storage blocked or corrupt: start fresh
  }
}

function persist() {
  try {
    const { active, index, mode, paused } = state;
    window.sessionStorage.setItem(KEY, JSON.stringify({ active, index, mode, paused }));
  } catch {
    // the tour still works for this page view
  }
}

export const tourStore = {
  get(): TourState {
    hydrate();
    return state;
  },
  set(patch: Partial<TourState>) {
    hydrate();
    state = { ...state, ...patch };
    persist();
    listeners.forEach((listener) => listener());
  },
  subscribe(listener: () => void) {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },
};

const serverState = () => INITIAL;

export function useTourState(): TourState {
  return useSyncExternalStore(tourStore.subscribe, tourStore.get, serverState);
}

/** Open a step. Forward runs its actions; back only shows it again. */
export function goTo(index: number, direction: "forward" | "back") {
  const { run } = tourStore.get();
  tourStore.set({
    index,
    direction,
    run: run + 1,
    phase: "running",
    spot: null,
    note: null,
  });
}

export function startTour() {
  tourStore.set({ active: true, paused: false });
  goTo(0, "forward");
}

export function exitTour() {
  tourStore.set({
    active: false,
    spot: null,
    note: null,
    paused: false,
    phase: "ready",
  });
}
