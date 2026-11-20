import type { Metadata } from "next";

import { StatusView } from "@/components/shared/status-view";

export const metadata: Metadata = { title: "Not allowed" };

export default function ForbiddenPage() {
  return (
    <StatusView
      code="403"
      title="You do not have access to this"
      message="This part of PlaceMate belongs to another role. Coordinator pages need a coordinator account."
      action={{ label: "Go back to the app", href: "/dashboard" }}
      secondary={{ label: "Log in as someone else", href: "/login" }}
    />
  );
}
