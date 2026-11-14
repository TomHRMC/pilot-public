/**
 * QuoteAcceptedState — FE-B14
 *
 * Location: apps/web/src/features/public-quote/QuoteAcceptedState.tsx
 *
 * State-aware revisit: renders when quote.status === 'accepted'.
 * Shows acceptance confirmation + customer comment (if any).
 *
 * Token: bg-margin-50 / text-margin-700 for success state.
 * RULE 1: No useAuth().
 */

import React from "react";

interface QuoteAcceptedStateProps {
  acceptedAt?: string;
  customerComment: string | null;
}

export function QuoteAcceptedState({
  acceptedAt,
  customerComment,
}: QuoteAcceptedStateProps) {
  const formattedDate = acceptedAt
    ? new Intl.DateTimeFormat("en-US", {
        month: "long",
        day: "numeric",
        year: "numeric",
      }).format(new Date(acceptedAt))
    : null;

  return (
    <div
      className="rounded-xl bg-margin-50 border border-margin-200 p-6"
      data-testid="quote-accepted-state"
    >
      <div className="flex items-start gap-3">
        {/* Checkmark icon */}
        <div className="flex-shrink-0 h-8 w-8 rounded-full bg-margin-200 flex items-center justify-center">
          <svg
            className="h-5 w-5 text-margin-700"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2.5}
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M5 13l4 4L19 7"
            />
          </svg>
        </div>
        <div className="flex flex-col gap-1">
          <p className="text-base font-semibold text-margin-700">
            Quote accepted
          </p>
          {formattedDate && (
            <p className="text-sm text-margin-600" data-testid="accepted-date">
              Accepted on {formattedDate}
            </p>
          )}
          {customerComment && (
            <div className="mt-3" data-testid="accepted-comment">
              <p className="text-xs font-medium text-neutral-500 uppercase tracking-wide">
                Your note
              </p>
              <p className="mt-1 text-sm text-neutral-700 italic">
                &ldquo;{customerComment}&rdquo;
              </p>
            </div>
          )}
          <p className="mt-3 text-sm text-neutral-600">
            The contractor has been notified and will reach out to schedule the
            work.
          </p>
        </div>
      </div>
    </div>
  );
}
