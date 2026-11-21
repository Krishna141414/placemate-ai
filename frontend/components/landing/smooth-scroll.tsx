"use client";

import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { ReactLenis, type LenisRef } from "lenis/react";
import { useEffect, useRef, type ReactNode } from "react";

import { useSpeed } from "@/lib/speed";

gsap.registerPlugin(ScrollTrigger);

/**
 * Lenis smooth scrolling for the landing page only, driven by GSAP's ticker so
 * ScrollTrigger and Lenis agree on every frame. Off when the user prefers
 * reduced motion.
 */
export function SmoothScroll({ children }: { children: ReactNode }) {
  const { reduced } = useSpeed();
  const lenisRef = useRef<LenisRef>(null);

  useEffect(() => {
    if (reduced) return;
    const lenis = lenisRef.current?.lenis;
    lenis?.on("scroll", ScrollTrigger.update);
    const update = (time: number) => lenisRef.current?.lenis?.raf(time * 1000);
    gsap.ticker.add(update);
    gsap.ticker.lagSmoothing(0);
    return () => {
      gsap.ticker.remove(update);
      lenis?.off("scroll", ScrollTrigger.update);
    };
  }, [reduced]);

  if (reduced) return <>{children}</>;
  return (
    <ReactLenis root options={{ autoRaf: false, lerp: 0.12, anchors: true }} ref={lenisRef}>
      {children}
    </ReactLenis>
  );
}
