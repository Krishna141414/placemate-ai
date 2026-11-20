import type { Metadata } from "next";
import { Suspense } from "react";

import { LoadingRows } from "@/components/shared/page";
import { ResumeView } from "./resume-view";

export const metadata: Metadata = { title: "Resume match" };

export default function ResumePage() {
  return (
    <Suspense fallback={<LoadingRows rows={6} />}>
      <ResumeView />
    </Suspense>
  );
}
