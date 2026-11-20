"use client";

// Placeholder for the guided tour (built in Phase 8). It exists now so the
// provider tree is stable and pages can already mark tour targets.

import type { ReactNode } from "react";

export function TourProvider({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
