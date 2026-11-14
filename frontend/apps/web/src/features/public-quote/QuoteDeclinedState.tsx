/**
 * QuoteDeclinedState — FE-B14
 *
 * Location: apps/web/src/features/public-quote/QuoteDeclinedState.tsx
 *
 * State-aware revisit: renders when quote.status === 'declined'.
 * Token: neutral-50 background.
 * RULE 1: No useAuth().
 */

import React from "react";
import { DECLINE_REASON_LABELS } from "./types";
import type { DeclineReason } from "./types";

interface QuoteDeclinedStateProps {
  declinedAt?: string;
  customerComment: string | null;
  declineReason?: DeclineReason;
}

export function QuoteDeclinedState({
  declinedAt,
  customerComment,
  declineReason,
}: QuoteDeclinedStateProps) {
  const formattedDate = declinedAt
    ? new Intl.DateTimeFormat("en-US", {
        month: "long",
        day: "numeric",
        year: "numeric",
      }).format(new Date(declinedAt))
    : null;

  return (
    <div
      className="rounded-xl bg-neutral-50 border border-neutral-200 p-6"
      data-testid="quote-declined-state"
    >
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 h-8 w-8 rounded-full bg-neutral-200 flex items-center justify-center">
          <svg
            className="h-5 w-5 text-neutral-600"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2.5}
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </div>
        <div className="flex flex-col gap-1">
          <p className="text-base font-semibold text-neutral-800">
            Quote declined
          </p>
          {formattedDate && (
            <p className="text-sm text-neutral-500" data-testid="declined-date">
              Declined on {formattedDate}
            </p>
          )}
          {declineReason && (
            <p
              className="text-sm text-neutral-600"
              data-testid="declined-reason"
            >
              Reason: {DECLINE_REASON_LABELS[declineReason]}
            </p>
          )}
          {customerComment && (
            <div className="mt-3" data-testid="declined-comment">
              <p className="text-xs font-medium text-neutral-500 uppercase tracking-wide">
                Your note
              </p>
              <p className="mt-1 text-sm text-neutral-700 italic">
                &ldquo;{customerComment}&rdquo;
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
