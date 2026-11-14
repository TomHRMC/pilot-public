"use client";

/**
 * CarrierQuoteDisplay — C-B9
 *
 * Location: apps/web/src/components/settings/messaging/CarrierQuoteDisplay.tsx
 *
 * Itemized cost quote display. Implements the always-preview-before-send
 * pattern (§16.7) — the tenant sees each cost line before paying.
 *
 * Amounts arrive as millicents (1 millicent = $0.00001).
 *
 * UI spec §4.4. RULE 5: zero hex codes. RULE 11: no hand-memo.
 */

import React from "react";
import { InformationCircleIcon } from "@heroicons/react/24/outline";
import { ErrorState, EmptyState } from "@pilot/ui";
import type { components } from "@pilot/shared-types";
import {
  formatMillicentsAsUSD,
  formatMillicentsPerSegment,
} from "@/features/messaging/types";

type CarrierQuoteResponse = components["schemas"]["CarrierQuoteResponse"];

export interface CarrierQuoteDisplayProps {
  quote: CarrierQuoteResponse | null;
  isLoading?: boolean;
  isError?: boolean;
  onRetry?: () => void;
  readOnly?: boolean;
}

export function CarrierQuoteDisplay({
  quote,
  isLoading = false,
  isError = false,
  onRetry,
  readOnly = false,
}: CarrierQuoteDisplayProps) {
  if (isLoading) {
    return (
      <div
        className="bg-white rounded-lg border border-neutral-200 shadow-sm p-6 space-y-4"
        data-testid="carrier-quote-loading"
      >
        <div className="h-6 w-40 bg-neutral-100 rounded animate-pulse" />
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="flex justify-between h-4 bg-neutral-100 rounded animate-pulse"
            >
              <div className="w-48 bg-neutral-100" />
              <div className="w-16 bg-neutral-100" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <ErrorState
        type="server"
        title="Could not load quote"
        description="Check your connection and try again."
        onRetry={onRetry}
      />
    );
  }

  if (
    !quote ||
    ((!quote.setup_items?.length || !quote.setup_items) &&
      (!quote.recurring_items?.length || !quote.recurring_items) &&
      !quote.setup_total_millicents &&
      !quote.recurring_monthly_millicents)
  ) {
    return (
      <EmptyState
        type="no-data"
        title="No quote available"
        description="Complete your brand registration to get a quote."
      />
    );
  }

  return (
    <div
      className="bg-white rounded-lg border border-neutral-200 shadow-sm p-6 space-y-4"
      data-testid="carrier-quote-display"
    >
      <div>
        <h2 className="text-h2 font-semibold text-neutral-900">Cost Quote</h2>
        <p className="text-sm text-neutral-500 mt-1">
          Carrier registration fees — passed through at cost. Pilot adds no
          markup.
        </p>
      </div>

      {readOnly && (
        <div className="rounded-md p-3 text-sm bg-neutral-50 border border-neutral-200 text-neutral-600">
          Quote is locked — payment is being processed.
        </div>
      )}

      {/* One-Time Setup Costs */}
      <div className="space-y-2">
        <p className="text-sm font-medium text-neutral-700">
          One-Time Setup Costs
        </p>
        <div className="space-y-0.5">
          {quote.setup_items?.map((item) => (
            <div
              key={item.fee_code}
              className="flex justify-between py-1.5 text-sm text-neutral-900"
            >
              <span className="text-neutral-700">{item.description}</span>
              <span className="font-mono">
                {formatMillicentsAsUSD(item.amount_millicents)}
              </span>
            </div>
          ))}
          <div className="border-t border-neutral-200 my-2" />
          <div className="flex justify-between py-1.5 text-sm font-medium text-neutral-900">
            <span>Setup total</span>
            <span className="font-mono">
              {formatMillicentsAsUSD(quote.setup_total_millicents)}
            </span>
          </div>
        </div>
      </div>

      {/* Recurring Monthly Costs */}
      <div className="space-y-2">
        <p className="text-sm font-medium text-neutral-700">
          Recurring Monthly Costs
        </p>
        <div className="space-y-0.5">
          {quote.recurring_items?.map((item) => (
            <div
              key={item.fee_code}
              className="flex justify-between py-1.5 text-sm text-neutral-900"
            >
              <span className="text-neutral-700">{item.description}</span>
              <span className="font-mono">
                {formatMillicentsAsUSD(item.amount_millicents)}
              </span>
            </div>
          ))}
          <div className="border-t border-neutral-200 my-2" />
          <div className="flex justify-between py-1.5 text-sm font-medium text-neutral-900">
            <span>Monthly total</span>
            <span className="font-mono">
              {formatMillicentsAsUSD(quote.recurring_monthly_millicents)}/mo
            </span>
          </div>
        </div>
      </div>

      {/* Surcharge info callout */}
      <div className="bg-neutral-50 border border-neutral-200 rounded-md p-3 text-xs text-neutral-600 flex items-start gap-2">
        <InformationCircleIcon className="w-4 h-4 shrink-0 mt-0.5" />
        <p>
          Per-message surcharges apply at carrier rates (~
          {formatMillicentsPerSegment(300)}). Billed monthly.
        </p>
      </div>

      <p className="text-xs text-neutral-500 italic mt-2">
        Passed through at cost — Pilot adds no markup.
      </p>
    </div>
  );
}
