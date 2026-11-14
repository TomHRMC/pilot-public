/**
 * PendingQuoteCard — single row card in the pending quotes inbox
 *
 * Location: apps/web/src/features/quote-approval/components/PendingQuoteCard.tsx
 */

"use client";

import React from "react";
import Link from "next/link";
import type { PendingQuoteSummary } from "../hooks/usePendingQuotes";

interface PendingQuoteCardProps {
  quote: PendingQuoteSummary;
}

/** Formats cents to dollar string */
function formatCents(cents: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(cents / 100);
}

export function PendingQuoteCard({ quote }: PendingQuoteCardProps) {
  const displayName = quote.quote_number
    ? `#${quote.quote_number}`
    : `Quote ${quote.id.slice(0, 8)}`;

  return (
    <article
      className="bg-white border border-neutral-200 rounded-lg p-4 flex items-center gap-4 hover:border-brand-400 transition-colors"
      aria-label={`${displayName} from ${quote.customer_name ?? "Unknown customer"}`}
    >
      {/* Quote info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-body font-medium text-neutral-900">
            {displayName}
          </span>
          {quote.title && (
            <>
              <span className="text-caption text-neutral-400">·</span>
              <span className="text-caption text-neutral-500 truncate">
                {quote.title}
              </span>
            </>
          )}
        </div>
        <p className="text-body text-neutral-600 truncate">
          {quote.customer_name ?? "Unknown customer"}
        </p>
      </div>

      {/* Total */}
      <div className="text-right shrink-0">
        <p className="text-body font-medium text-neutral-900">
          {formatCents(quote.total_cents)}
        </p>
      </div>

      {/* Action */}
      <Link
        href={`/quotes/${quote.id}`}
        className="shrink-0 bg-brand-600 hover:bg-brand-800 text-white text-body font-medium px-4 py-2 rounded-md transition-colors"
        aria-label={`Review ${displayName}`}
      >
        Review
      </Link>
    </article>
  );
}
