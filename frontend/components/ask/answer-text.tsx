"use client";

import { Fragment } from "react";

import {
  InlineCitation,
  InlineCitationCard,
  InlineCitationCardBody,
  InlineCitationCardTrigger,
  InlineCitationQuote,
  InlineCitationSource,
} from "@/components/ai-elements/inline-citation";
import type { Source } from "@/lib/types";

const CITE = /(\[\d{1,3}\])/g;

/** An answer's text with every [n] turned into a citation chip. */
export function AnswerText({
  text,
  sources,
  activeSource,
  onCite,
}: {
  text: string;
  sources: Source[];
  activeSource?: number | null;
  onCite?: (n: number) => void;
}) {
  const byNumber = new Map(sources.map((source) => [source.n, source]));
  const paragraphs = text.split(/\n{2,}/);
  return (
    <div className="space-y-3 leading-relaxed">
      {paragraphs.map((paragraph, p) => (
        <p key={p} className="whitespace-pre-line">
          {paragraph.split(CITE).map((part, i) => {
            const match = /^\[(\d{1,3})\]$/.exec(part);
            if (!match) return <Fragment key={i}>{part}</Fragment>;
            const n = Number(match[1]);
            const source = byNumber.get(n);
            if (!source) return null;
            return (
              <InlineCitation key={i} className="inline">
                <InlineCitationCard>
                  <InlineCitationCardTrigger
                    sources={[]}
                    className="cite-chip ml-0 rounded-md border-0"
                    data-active={activeSource === n}
                    role="button"
                    tabIndex={0}
                    aria-label={`Source ${n}: ${source.title}`}
                    onClick={() => onCite?.(n)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        onCite?.(n);
                      }
                    }}
                  >
                    {n}
                  </InlineCitationCardTrigger>
                  <InlineCitationCardBody className="w-96 max-w-[90vw]">
                    <div className="space-y-2 p-4">
                      <InlineCitationSource title={source.title} description={source.section || undefined} />
                      <InlineCitationQuote className="not-italic">{source.snippet}</InlineCitationQuote>
                    </div>
                  </InlineCitationCardBody>
                </InlineCitationCard>
              </InlineCitation>
            );
          })}
        </p>
      ))}
    </div>
  );
}
