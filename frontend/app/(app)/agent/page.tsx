import type { Metadata } from "next";
import { Suspense } from "react";

import { LoadingRows } from "@/components/shared/page";
import { AgentView } from "./agent-view";

export const metadata: Metadata = { title: "Prep agent" };

export default function AgentPage() {
  return (
    <Suspense fallback={<LoadingRows rows={6} />}>
      <AgentView />
    </Suspense>
  );
}
