"use client";

import { ChevronLeft, ChevronRight, Loader2, Pause, Play, X } from "lucide-react";
import { useEffect, useRef } from "react";

import { Button } from "@/components/ui/button";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { useSpeed, type Speed } from "@/lib/speed";
import { TOUR_STEPS } from "@/lib/tour-script";

import { exitTour, startTour, tourStore, useTourState, type TourMode } from "./tour-store";

const SPEED_LABELS: { value: Speed; label: string }[] = [
  { value: "slow", label: "Slow" },
  { value: "medium", label: "Medium" },
  { value: "fast", label: "Fast" },
];

/**
 * The presenter's controls, fixed at the bottom centre above everything else.
 * The caption is part of the bar, so it can never cover the bar or the
 * highlighted element (the page keeps clear of the bar's height).
 */
export function TourBar({ onNext, onBack }: { onNext: () => void; onBack: () => void }) {
  const state = useTourState();
  const { speed, setSpeed } = useSpeed();
  const dock = useRef<HTMLElement>(null);

  // Publish the bar's height so pages and the spotlight keep clear of it.
  useEffect(() => {
    const root = document.documentElement;
    const node = dock.current;
    if (!state.active || !node) {
      root.style.removeProperty("--tour-inset");
      delete root.dataset.tourActive;
      return;
    }
    root.dataset.tourActive = "true";
    const observer = new ResizeObserver(() => root.style.setProperty("--tour-inset", `${node.offsetHeight + 24}px`));
    observer.observe(node);
    return () => {
      observer.disconnect();
      root.style.removeProperty("--tour-inset");
      delete root.dataset.tourActive;
    };
  }, [state.active]);

  if (!state.active) {
    return (
      <div className="tour-ui tour-idle fixed right-4 bottom-4 z-[70]" data-tour-ui>
        <Button type="button" size="sm" variant="outline" className="shadow-[var(--shadow-soft)]" onClick={startTour}>
          <Play aria-hidden="true" />
          Start tour
        </Button>
      </div>
    );
  }

  const index = Math.min(state.index, TOUR_STEPS.length - 1);
  const step = TOUR_STEPS[index];
  const last = index === TOUR_STEPS.length - 1;

  return (
    <div className="tour-ui pointer-events-none fixed inset-x-0 bottom-3 z-[70] flex justify-center px-3" data-tour-ui>
      <section
        ref={dock}
        aria-label="Guided tour"
        data-phase={state.phase}
        className="pointer-events-auto w-full max-w-[46rem] rounded-xl border bg-card text-card-foreground shadow-lg"
      >
        <div className="relative px-4 pt-3 pb-2.5 pr-12">
          <Button type="button" size="icon-sm" variant="ghost" aria-label="Exit tour" onClick={exitTour} className="absolute top-2 right-2">
            <X aria-hidden="true" />
          </Button>
          <div aria-live="polite">
            <p className="font-semibold">{step.title}</p>
            <p className="mt-0.5 text-sm text-muted-foreground">{step.caption}</p>
            <p className="mt-2 flex flex-wrap items-center gap-2 text-xs">
              <span className="rounded-md bg-accent px-2 py-0.5 text-accent-foreground">Proves: {step.requirement}</span>
              {state.note ? (
                <span className={state.phase === "stuck" ? "text-warning" : "flex items-center gap-1.5 text-muted-foreground"}>
                  {state.phase === "running" ? <Loader2 className="size-3 animate-spin motion-reduce:animate-none" aria-hidden="true" /> : null}
                  {state.note}
                </span>
              ) : null}
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-x-2 gap-y-2 border-t px-3 py-2">
          <Button type="button" size="sm" variant="ghost" onClick={onBack} disabled={index === 0} className="disabled:opacity-40">
            <ChevronLeft aria-hidden="true" />
            Back
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => tourStore.set({ paused: !state.paused })}
            aria-pressed={state.paused}
            className="min-w-[5.5rem]"
          >
            {state.paused ? <Play aria-hidden="true" /> : <Pause aria-hidden="true" />}
            {state.paused ? "Play" : "Pause"}
          </Button>
          <Button type="button" size="sm" onClick={onNext}>
            {last ? "Finish" : "Next"}
            <ChevronRight aria-hidden="true" />
          </Button>
          <span className="px-1 text-sm tabular-nums text-muted-foreground" aria-label={`Step ${index + 1} of ${TOUR_STEPS.length}`}>
            {index + 1} / {TOUR_STEPS.length}
          </span>

          <div className="ml-auto flex flex-wrap items-center gap-2">
            <ToggleGroup
              type="single"
              size="sm"
              variant="outline"
              value={state.mode}
              onValueChange={(value) => value && tourStore.set({ mode: value as TourMode })}
              aria-label="Tour mode"
            >
              <ToggleGroupItem value="manual">Manual</ToggleGroupItem>
              <ToggleGroupItem value="auto">Auto</ToggleGroupItem>
            </ToggleGroup>
            <ToggleGroup
              type="single"
              size="sm"
              variant="outline"
              value={speed}
              onValueChange={(value) => value && setSpeed(value as Speed)}
              aria-label="Speed"
            >
              {SPEED_LABELS.map((option) => (
                <ToggleGroupItem key={option.value} value={option.value}>
                  {option.label}
                </ToggleGroupItem>
              ))}
            </ToggleGroup>
          </div>
        </div>
      </section>
    </div>
  );
}
