import { StatusView } from "@/components/shared/status-view";

export default function NotFound() {
  return (
    <StatusView
      code="404"
      title="This page does not exist"
      message="The link may be old, or the address has a typo."
      action={{ label: "Go to PlaceMate", href: "/" }}
      secondary={{ label: "Log in", href: "/login" }}
    />
  );
}
