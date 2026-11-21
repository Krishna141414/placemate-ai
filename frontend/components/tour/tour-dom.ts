"use client";

// Small DOM helpers for the guided tour: find targets, wait for them, click
// them and scroll them into the part of the screen the tour bar leaves free.

import { sleep } from "@/lib/speed";
import type { TourTarget } from "@/lib/tour-script";

import { tourStore } from "./tour-store";

export interface RunContext {
  cancelled: boolean;
}

/** Thrown (and caught by the runner) when the presenter moves on mid-step. */
export class TourCancelled extends Error {}

/** Thrown when something the step waits for never shows up. */
export class TourTimeout extends Error {}

export function selector(target: string, status?: string): string {
  return `[data-tour="${target}"]${status ? `[data-status="${status}"]` : ""}`;
}

export function find(spot: TourTarget, status?: string): HTMLElement | null {
  const all = document.querySelectorAll<HTMLElement>(selector(spot.target, status));
  if (!all.length) return null;
  return spot.last ? all[all.length - 1] : all[0];
}

export function count(target: string): number {
  return document.querySelectorAll(selector(target)).length;
}

/** Waits while the tour is paused; throws if the step was abandoned. */
export async function gate(ctx: RunContext) {
  while (tourStore.get().paused && !ctx.cancelled) await sleep(100);
  if (ctx.cancelled) throw new TourCancelled();
}

/** Hold for `ms` of unpaused time. */
export async function hold(ms: number, ctx: RunContext) {
  let left = ms;
  while (left > 0) {
    await gate(ctx);
    const slice = Math.min(100, left);
    await sleep(slice);
    left -= slice;
  }
  await gate(ctx);
}

/** Poll until `check` passes. Paused time does not count against the timeout. */
export async function until<T>(check: () => T | null | false | undefined, timeout: number, ctx: RunContext): Promise<T> {
  let waited = 0;
  for (;;) {
    if (ctx.cancelled) throw new TourCancelled();
    const value = check();
    if (value) return value;
    if (waited >= timeout) throw new TourTimeout();
    await sleep(100);
    if (!tourStore.get().paused) waited += 100;
  }
}

function enabled(el: HTMLElement): boolean {
  return !(el as HTMLButtonElement).disabled && el.getAttribute("aria-disabled") !== "true";
}

export async function click(spot: TourTarget, timeout: number, ctx: RunContext) {
  const el = await until(
    () => {
      const found = find(spot);
      return found && enabled(found) ? found : null;
    },
    timeout,
    ctx,
  );
  el.click();
}

/** The lowest y the tour may use: above the tour bar and above sticky page bars. */
export function visibleBottom(forElement?: Element | null): number {
  const inset = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--tour-inset")) || 0;
  let bottom = window.innerHeight - inset;
  document.querySelectorAll<HTMLElement>("[data-tour-obstacle]").forEach((obstacle) => {
    if (forElement && obstacle.contains(forElement)) return;
    const top = obstacle.getBoundingClientRect().top;
    if (top > 0 && top < bottom) bottom = top;
  });
  return bottom;
}

async function settle(el: HTMLElement, limit: number) {
  let last = el.getBoundingClientRect().top;
  let still = 0;
  const start = performance.now();
  while (still < 4 && performance.now() - start < limit) {
    await new Promise((resolve) => requestAnimationFrame(resolve));
    const now = el.getBoundingClientRect().top;
    still = Math.abs(now - last) < 0.5 ? still + 1 : 0;
    last = now;
  }
}

/** Scroll so the element sits in the free area; tall elements start at its top. */
export async function reveal(el: HTMLElement, smooth: boolean, settleLimit: number) {
  const behavior: ScrollBehavior = smooth ? "smooth" : "auto";
  el.scrollIntoView({ block: "nearest", inline: "nearest", behavior });
  await settle(el, settleLimit);
  const rect = el.getBoundingClientRect();
  const free = visibleBottom(el);
  const top = 16;
  let delta = 0;
  if (rect.height > free - top * 2) delta = rect.top - top;
  else if (rect.top < top || rect.bottom > free - top) delta = rect.top + rect.height / 2 - free / 2;
  if (Math.abs(delta) > 2) {
    window.scrollBy({ top: delta, behavior });
    await settle(el, settleLimit);
  }
}

export function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName);
}
