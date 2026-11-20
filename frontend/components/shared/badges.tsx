import { Cpu, FileSearch, Sparkles } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const PROVIDERS: Record<string, { label: string; icon: typeof Sparkles; hint: string }> = {
  gemini: { label: "Gemini", icon: Sparkles, hint: "Written by Gemini from the retrieved passages" },
  local: { label: "Local model", icon: Cpu, hint: "Written by the local Qwen model on this computer" },
  extractive: { label: "Extractive", icon: FileSearch, hint: "Sentences quoted from the passages; no model" },
  template: { label: "Template", icon: FileSearch, hint: "Written from a template because no model was available" },
  none: { label: "No model", icon: FileSearch, hint: "Answered by a guard; no model was called" },
};

export function ProviderBadge({ provider, className }: { provider: string; className?: string }) {
  const info = PROVIDERS[provider] ?? { label: provider, icon: Sparkles, hint: provider };
  const Icon = info.icon;
  return (
    <Badge variant="secondary" className={cn("gap-1 font-normal", className)} title={info.hint} data-tour="provider-badge">
      <Icon className="size-3" aria-hidden="true" />
      {info.label}
    </Badge>
  );
}

type Tone = "success" | "warning" | "error" | "neutral" | "info";

const TONES: Record<Tone, string> = {
  success: "bg-success-soft text-success",
  warning: "bg-warning-soft text-warning",
  error: "bg-error-soft text-error",
  neutral: "bg-secondary text-secondary-foreground",
  info: "bg-blue-soft text-cite",
};

/** A small coloured label. Always carries words, never colour alone. */
export function ToneBadge({ tone, children, className }: { tone: Tone; children: React.ReactNode; className?: string }) {
  return <span className={cn("inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-xs font-medium", TONES[tone], className)}>{children}</span>;
}

export function CategoryBadge({ category }: { category: string }) {
  const tone: Tone = category === "Dream" ? "info" : category === "Standard" ? "neutral" : "neutral";
  return <ToneBadge tone={tone}>{category}</ToneBadge>;
}
