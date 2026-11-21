"use client";

import { useEffect, useRef } from "react";

import { find, visibleBottom } from "./tour-dom";
import { tourStore, useTourState } from "./tour-store";

const PAD = 8;
const EDGE = 8;

/**
 * Dims the page except the current target. The hole follows the element every
 * frame (scrolling, streaming text, layout changes) and is clipped to the area
 * above the tour bar, so the bar never sits on top of the highlighted part.
 */
export function TourSpotlight() {
  const { active, spot } = useTourState();
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const node = ref.current;
    if (!active || !spot || !node) return;
    let frame = 0;
    const place = () => {
      const current = tourStore.get().spot;
      const el = current ? find(current) : null;
      if (!el) {
        node.style.opacity = "0";
      } else {
        const rect = el.getBoundingClientRect();
        const top = Math.max(rect.top - PAD, EDGE);
        const bottom = Math.min(rect.bottom + PAD, visibleBottom(el) - EDGE);
        const left = Math.max(rect.left - PAD, EDGE);
        const right = Math.min(rect.right + PAD, window.innerWidth - EDGE);
        if (bottom - top < 12 || right - left < 12) {
          node.style.opacity = "0";
        } else {
          node.style.opacity = "1";
          node.style.transform = `translate(${left}px, ${top}px)`;
          node.style.width = `${right - left}px`;
          node.style.height = `${bottom - top}px`;
        }
      }
      frame = requestAnimationFrame(place);
    };
    frame = requestAnimationFrame(place);
    return () => cancelAnimationFrame(frame);
  }, [active, spot]);

  if (!active || !spot) return null;
  return <div ref={ref} className="tour-spotlight" style={{ opacity: 0 }} aria-hidden="true" />;
}
