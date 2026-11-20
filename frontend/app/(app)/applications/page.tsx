import type { Metadata } from "next";
import { Suspense } from "react";

import { LoadingRows } from "@/components/shared/page";
import { ApplicationsView } from "./applications-view";

export const metadata: Metadata = { title: "Applications" };

export default function ApplicationsPage() {
  return (
    <Suspense fallback={<LoadingRows rows={6} />}>
      <ApplicationsView />
    </Suspense>
  );
}
