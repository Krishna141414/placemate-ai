"use client";

import { animate, useInView } from "motion/react";
import { useEffect, useRef } from "react";

import { useSpeed } from "@/lib/speed";

/** A number that counts up once it scrolls into view. Text content only changes; no layout shift. */
export function CountUp({
  value,
  decimals = 0,
  suffix = "",
  className,
  startOnView = true,
}: {
  value: number;
  decimals?: number;
  suffix?: string;
  className?: string;
  /** wait until the number scrolls into view (landing page); false starts on mount */
  startOnView?: boolean;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const seen = useInView(ref, { once: true, margin: "-40px" });
  const inView = startOnView ? seen : true;
  const { t } = useSpeed();

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    const render = (v: number) => {
      node.textContent = `${v.toFixed(decimals)}${suffix}`;
    };
    if (!inView || t.countUp === 0) {
      render(inView || t.countUp === 0 ? value : 0);
      return;
    }
    const controls = animate(0, value, { duration: t.countUp / 1000, ease: [0.16, 1, 0.3, 1], onUpdate: render });
    return () => controls.stop();
  }, [inView, value, decimals, suffix, t.countUp]);

  return (
    <span ref={ref} className={className} data-num>
      {`${value.toFixed(decimals)}${suffix}`}
    </span>
  );
}
