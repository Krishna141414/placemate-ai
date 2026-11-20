"use client";

import { GraduationCap, Loader2, UserCog } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, errorMessage } from "@/lib/api";
import { DEMO_ACCOUNTS, homeFor, useAuth } from "@/lib/auth";

function safeNext(next: string | null): string | null {
  // Only same-site paths: never redirect to another origin after login.
  if (!next || !next.startsWith("/") || next.startsWith("//")) return null;
  return next;
}

export function LoginForm() {
  const { login, user, loading } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const next = safeNext(params.get("next"));
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const emailRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!loading && user) router.replace(next ?? homeFor(user));
  }, [loading, user, next, router]);

  async function submit(address: string, secret: string, which: string) {
    setBusy(which);
    setError(null);
    try {
      const me = await login(address, secret);
      router.replace(next && !(me.role === "student" && next.startsWith("/documents")) ? next : homeFor(me));
    } catch (err) {
      setError(err instanceof ApiError && err.status === 429 ? `Too many attempts. Try again in ${err.retryAfter ?? 60} seconds.` : errorMessage(err));
      setBusy(null);
      emailRef.current?.focus();
    }
  }

  return (
    <div className="w-full max-w-sm">
      <Link href="/" className="text-sm font-semibold tracking-tight">
        PlaceMate
      </Link>
      <h1 className="mt-8 text-2xl font-semibold tracking-tight">Log in</h1>
      <p className="mt-1.5 text-muted-foreground">Use your college account, or one of the demo accounts.</p>

      <div className="mt-6 grid gap-2.5" data-tour="demo-buttons">
        <Button
          type="button"
          variant="outline"
          className="h-11 justify-start gap-3"
          disabled={busy !== null}
          onClick={() => submit(DEMO_ACCOUNTS.student.email, DEMO_ACCOUNTS.student.password, "student")}
          data-tour="demo-student"
        >
          {busy === "student" ? <Loader2 className="animate-spin" aria-hidden="true" /> : <GraduationCap aria-hidden="true" />}
          Use demo student
          <span className="ml-auto text-xs text-muted-foreground">Ananya, CSE</span>
        </Button>
        <Button
          type="button"
          variant="outline"
          className="h-11 justify-start gap-3"
          disabled={busy !== null}
          onClick={() => submit(DEMO_ACCOUNTS.coordinator.email, DEMO_ACCOUNTS.coordinator.password, "coordinator")}
          data-tour="demo-coordinator"
        >
          {busy === "coordinator" ? <Loader2 className="animate-spin" aria-hidden="true" /> : <UserCog aria-hidden="true" />}
          Use demo coordinator
          <span className="ml-auto text-xs text-muted-foreground">Placement cell</span>
        </Button>
      </div>

      <div className="my-6 flex items-center gap-3 text-xs text-muted-foreground">
        <span className="h-px flex-1 bg-border" />
        or with email
        <span className="h-px flex-1 bg-border" />
      </div>

      <form
        className="grid gap-4"
        onSubmit={(event) => {
          event.preventDefault();
          void submit(email, password, "form");
        }}
      >
        <div className="grid gap-1.5">
          <Label htmlFor="email">Email</Label>
          <Input
            ref={emailRef}
            id="email"
            name="email"
            type="email"
            autoComplete="username"
            inputMode="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="h-10"
          />
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="h-10"
          />
        </div>
        <p role="alert" aria-live="polite" className="min-h-5 text-sm text-error">
          {error}
        </p>
        <Button type="submit" className="h-10" disabled={busy !== null}>
          {busy === "form" && <Loader2 className="animate-spin" aria-hidden="true" />}
          Log in
        </Button>
      </form>

      <p className="mt-8 text-xs text-muted-foreground">
        Demo logins: {DEMO_ACCOUNTS.student.email} / {DEMO_ACCOUNTS.student.password}, {DEMO_ACCOUNTS.coordinator.email} / {DEMO_ACCOUNTS.coordinator.password}
      </p>
    </div>
  );
}
