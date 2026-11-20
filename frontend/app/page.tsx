import Link from "next/link";

import { Button } from "@/components/ui/button";

// Temporary entry page. The scroll-story landing page replaces it in Phase 8.
export default function Home() {
  return (
    <main className="grid min-h-dvh place-items-center px-6">
      <div className="max-w-xl text-center">
        <h1 className="text-3xl font-semibold tracking-tight">PlaceMate</h1>
        <p className="mt-3 text-muted-foreground">Placement answers with sources, eligibility checks and a prep plan you approve.</p>
        <Button asChild className="mt-8">
          <Link href="/login">Try the demo</Link>
        </Button>
      </div>
    </main>
  );
}
