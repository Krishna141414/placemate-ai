"use client";

import { useEffect } from "react";

import { StatusView } from "@/components/shared/status-view";

export default function ErrorPage({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);
  return (
    <StatusView
      code="500"
      title="Something broke on this page"
      message="It is not something you did. Try again, and if it keeps happening, reload the page."
      action={{ label: "Try again", onClick: reset }}
      secondary={{ label: "Go to PlaceMate", href: "/" }}
    />
  );
}
