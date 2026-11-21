import type { Metadata } from "next";

import { LandingPage } from "@/components/landing/landing-page";

export const metadata: Metadata = {
  title: { absolute: "PlaceMate - placement answers with the source attached" },
};

export default function Home() {
  return <LandingPage />;
}
