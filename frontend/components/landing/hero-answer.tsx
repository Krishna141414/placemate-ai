"use client";

import { FileText, RotateCcw } from "lucide-react";
import { Fragment, useCallback, useEffect, useRef, useState } from "react";

import { ProviderBadge } from "@/components/shared/badges";
import { Button } from "@/components/ui/button";
import { useSpeed } from "@/lib/speed";

// A real answer from the running app (student account, Gemini, 2026-11-21) to
// "Can I sit for another company after I get an offer?", first three sentences.
const QUESTION = "Can I sit for another company after I get an offer?";
const ANSWER =
  "A student who receives an offer through campus placements is considered placed and generally cannot sit for further companies [1]. " +
  "Under the dream exception, a placed student may appear for at most one more company, provided that company is in a higher category than the offer already held [1]. " +
  "A student with a Regular offer may attempt one Standard or one Dream company [1].";

const TOKENS = ANSWER.split(" ");
const CITE = /^\[(\d)\]([.,]?)$/;

/** Event the guided tour sends to replay the typing on the landing page. */
export const HERO_REPLAY_EVENT = "pm:hero-replay";

/**
 * The hero's product card. It renders finished, so nothing moves on load
 * (SHOWCASE.md: no animation starts on page load); Replay types the answer out.
 */
export function HeroAnswer() {
  const { t, reduced } = useSpeed();
  const [shown, setShown] = useState(TOKENS.length);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  const replay = useCallback(() => {
    if (timer.current) clearInterval(timer.current);
    if (reduced) {
      setShown(TOKENS.length);
      return;
    }
    setShown(0);
    timer.current = setInterval(() => {
      setShown((n) => {
        if (n + 1 >= TOKENS.length && timer.current) clearInterval(timer.current);
        return Math.min(n + 1, TOKENS.length);
      });
    }, t.typing * 3);
  }, [reduced, t.typing]);

  useEffect(() => {
    window.addEventListener(HERO_REPLAY_EVENT, replay);
    return () => {
      window.removeEventListener(HERO_REPLAY_EVENT, replay);
      if (timer.current) clearInterval(timer.current);
    };
  }, [replay]);

  const done = shown >= TOKENS.length;

  return (
    <figure className="landing-frame m-0 p-5 sm:p-6" data-tour="landing-answer">
      <div className="flex justify-end">
        <p className="max-w-[85%] rounded-xl bg-secondary px-3.5 py-2 text-sm text-foreground">{QUESTION}</p>
      </div>

      <div className="mt-5 text-[0.95rem] leading-relaxed text-foreground">
        <p className="sr-only">{ANSWER.replaceAll("[1]", "(source 1)")}</p>
        <p aria-hidden="true">
          {TOKENS.map((token, i) => {
            const cite = CITE.exec(token);
            const hidden = i >= shown;
            return (
              <Fragment key={i}>
                <span className={hidden ? "opacity-0" : undefined}>
                  {cite ? (
                    <>
                      <span className="cite-chip">{cite[1]}</span>
                      {cite[2]}
                    </>
                  ) : (
                    token
                  )}
                </span>{" "}
              </Fragment>
            );
          })}
        </p>
      </div>

      <div className={done ? "mt-5 flex items-start gap-3 rounded-xl border bg-muted p-3 transition-opacity duration-300" : "mt-5 flex items-start gap-3 rounded-xl border bg-muted p-3 opacity-0"}>
        <span className="cite-chip mt-0.5">1</span>
        <div className="min-w-0 text-sm">
          <p className="flex items-center gap-1.5 font-medium text-foreground">
            <FileText className="size-3.5 text-muted-foreground" aria-hidden="true" />
            Placement Policy 2026-27
          </p>
          <p className="mt-0.5 text-muted-foreground">Section 5, One-offer policy</p>
        </div>
      </div>

      <figcaption className="mt-4 flex items-center justify-between gap-3 text-xs text-muted-foreground">
        <span className="flex items-center gap-2">
          <ProviderBadge provider="gemini" />
          A real answer from the sample documents
        </span>
        <Button type="button" variant="ghost" size="sm" onClick={replay} aria-label="Replay the answer">
          <RotateCcw aria-hidden="true" />
          Replay
        </Button>
      </figcaption>
    </figure>
  );
}
