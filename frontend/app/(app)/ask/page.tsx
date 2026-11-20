import type { Metadata } from "next";
import { Suspense } from "react";

import { LoadingRows } from "@/components/shared/page";
import { AskView } from "./ask-view";

export const metadata: Metadata = { title: "Ask PlaceMate" };

export default function AskPage() {
  return (
    <Suspense fallback={<LoadingRows rows={5} />}>
      <AskView />
    </Suspense>
  );
}
