import type { Metadata } from "next";
import { Suspense } from "react";

import { LoginForm } from "./login-form";

export const metadata: Metadata = { title: "Log in" };

export default function LoginPage() {
  return (
    <main id="main" className="grid min-h-dvh lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
      <div className="flex items-center justify-center px-6 py-16">
        <Suspense>
          <LoginForm />
        </Suspense>
      </div>
      <aside className="hidden flex-col justify-between bg-navy p-12 text-on-navy-2 lg:flex" aria-label="About PlaceMate">
        <p className="text-sm font-medium text-on-navy-accent">Kaveri Ridge Institute of Technology, placement cell</p>
        <div className="max-w-md">
          <p className="text-2xl font-semibold leading-snug tracking-tight text-on-navy">
            Ask anything about placements. Every answer shows the document it came from.
          </p>
          <p className="mt-4 text-on-navy-2">
            Eligibility is checked against the college&apos;s actual rules, and your prep plan is saved only after you approve it.
          </p>
        </div>
        <p className="text-sm text-on-navy-3">All data in this demo is fictional.</p>
      </aside>
    </main>
  );
}
