import type { Metadata } from "next";

import { StatusView } from "@/components/shared/status-view";

export const metadata: Metadata = { title: "Slow down" };

export default function TooManyRequestsPage() {
  return (
    <StatusView
      code="429"
      title="Too many requests in a short time"
      message="PlaceMate limits how often each address can call it, to keep it fair and to stop password guessing. Wait a minute and try again."
      action={{ label: "Back to the app", href: "/dashboard" }}
    />
  );
}
