import type { Metadata } from "next";
import { Suspense } from "react";

import { LoadingRows } from "@/components/shared/page";
import { EligibilityView } from "./eligibility-view";

export const metadata: Metadata = { title: "Eligibility" };

export default function EligibilityPage() {
  return (
    <Suspense fallback={<LoadingRows rows={6} />}>
      <EligibilityView />
    </Suspense>
  );
}
