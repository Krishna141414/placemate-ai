"use client";

import { BookOpen, ChevronDown } from "lucide-react";

import { Sources, SourcesContent, SourcesTrigger } from "@/components/ai-elements/sources";
import { ToneBadge } from "@/components/shared/badges";
import type { Source } from "@/lib/types";
import { cn } from "@/lib/utils";

const TYPE_LABELS: Record<string, string> = {
  policy: "Policy",
  company: "Company profile",
  interview: "Interview experience",
  guide: "Prep guide",
  upload: "Uploaded",
};

export function SourceCards({
  sources,
  cited,
  activeSource,
  defaultOpen = true,
  idPrefix = "",
}: {
  sources: Source[];
  cited: number[];
  activeSource?: number | null;
  defaultOpen?: boolean;
  idPrefix?: string;
}) {
  if (!sources.length) return null;
  const used = new Set(cited);
  return (
    <Sources defaultOpen={defaultOpen} className="mb-0 mt-4 text-foreground" data-tour="source-cards">
      <SourcesTrigger count={sources.length} className="text-sm text-muted-foreground hover:text-foreground">
        <BookOpen className="size-4" aria-hidden="true" />
        <span className="font-medium">
          {sources.length} sources retrieved, {used.size} cited
        </span>
        <ChevronDown className="size-4" aria-hidden="true" />
      </SourcesTrigger>
      <SourcesContent className="w-full">
        <ol className="grid w-full gap-2 sm:grid-cols-2">
          {sources.map((source) => (
            <li
              key={source.n}
              id={`${idPrefix}source-${source.n}`}
              className={cn(
                "min-w-0 rounded-lg border bg-card p-3 transition-colors duration-200",
                activeSource === source.n && "border-primary bg-accent",
                !used.has(source.n) && "opacity-75",
              )}
            >
              <div className="flex items-start gap-2">
                <span className="cite-chip mt-0.5 shrink-0 cursor-default" aria-hidden="true">
                  {source.n}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium" title={source.title}>
                    {source.title}
                  </p>
                  {source.section && <p className="truncate text-xs text-muted-foreground">{source.section}</p>}
                </div>
              </div>
              <p className="mt-2 line-clamp-3 text-sm text-muted-foreground">{source.snippet}</p>
              <div className="mt-2 flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
                <ToneBadge tone="neutral">{TYPE_LABELS[source.doc_type] ?? source.doc_type}</ToneBadge>
                {used.has(source.n) ? <ToneBadge tone="info">Cited</ToneBadge> : <ToneBadge tone="neutral">Not cited</ToneBadge>}
                <span className="ml-auto num" title="Relevance score from retrieval">
                  score {source.score.toFixed(2)}
                </span>
              </div>
            </li>
          ))}
        </ol>
      </SourcesContent>
    </Sources>
  );
}
