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
const BULLET = /^\s*(?:[-*•]|\d{1,2}[.)])\s+/;

/** Models sometimes answer in light markdown; drop the emphasis markers so they never show as text. */
function plain(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/__(.+?)__/g, "$1")
    .replace(/^#{1,6}\s+/gm, "");
}

/** An answer's text with every [n] turned into a citation chip. Bulleted lines become a list. */
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
  const paragraphs = plain(text).split(/\n{2,}/);

  const inline = (line: string) =>
    line.split(CITE).map((part, i) => {
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
    });

  return (
    <div className="space-y-3 leading-relaxed">
      {paragraphs.map((paragraph, p) => {
        const lines = paragraph.split("\n").filter((line) => line.trim());
        if (lines.length > 0 && lines.every((line) => BULLET.test(line))) {
          return (
            <ul key={p} className="list-disc space-y-1.5 pl-5">
              {lines.map((line, l) => (
                <li key={l}>{inline(line.replace(BULLET, ""))}</li>
              ))}
            </ul>
          );
        }
        return (
          <p key={p} className="whitespace-pre-line">
            {inline(paragraph)}
          </p>
        );
      })}
    </div>
  );
}
