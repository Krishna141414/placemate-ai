import Link from "next/link";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type Action = { label: string; href?: string; onClick?: () => void };

/** A friendly full-page (or embedded) status: 404, 403, 429, 500, offline. */
export function StatusView({
  code,
  title,
  message,
  action,
  secondary,
  embedded = false,
}: {
  code: string;
  title: string;
  message: string;
  action?: Action;
  secondary?: Action;
  embedded?: boolean;
}) {
  const button = (a: Action, variant: "default" | "outline") =>
    a.href ? (
      <Button asChild variant={variant}>
        <Link href={a.href}>{a.label}</Link>
      </Button>
    ) : (
      <Button type="button" variant={variant} onClick={a.onClick}>
        {a.label}
      </Button>
    );

  return (
    <div className={cn("grid place-items-center px-6", embedded ? "py-20" : "min-h-dvh py-16")}>
      <div className="max-w-md text-center">
        <p className="text-sm font-medium text-muted-foreground num">{code}</p>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight">{title}</h1>
        <p className="mt-3 text-muted-foreground">{message}</p>
        {(action || secondary) && (
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            {action && button(action, "default")}
            {secondary && button(secondary, "outline")}
          </div>
        )}
      </div>
    </div>
  );
}
