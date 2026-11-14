/**
 * InvoicePaidState — FE-B14
 *
 * Location: apps/web/src/features/public-invoice/InvoicePaidState.tsx
 *
 * State-aware revisit: renders when invoice.status === 'paid'.
 * Token: bg-margin-50 / text-margin-700 for success state.
 * RULE 1: No useAuth().
 */

import React from "react";

function formatCents(cents: number, currency = "USD"): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
  }).format(cents / 100);
}

interface InvoicePaidStateProps {
  amountPaidCents: number;
  currency?: string;
  tenantName: string;
}

export function InvoicePaidState({
  amountPaidCents,
  currency = "USD",
  tenantName,
}: InvoicePaidStateProps) {
  return (
    <div
      className="rounded-xl bg-margin-50 border border-margin-200 p-6"
      data-testid="invoice-paid-state"
    >
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 h-9 w-9 rounded-full bg-margin-200 flex items-center justify-center">
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
        <div>
          <p
            className="text-base font-semibold text-margin-700"
            data-testid="paid-badge"
          >
            Paid in full
          </p>
          <p className="text-sm text-margin-600 mt-0.5">
            {formatCents(amountPaidCents, currency)} received by {tenantName}
          </p>
          <p className="text-sm text-neutral-500 mt-2">
            Thank you — this invoice has been paid in full.
          </p>
        </div>
      </div>
    </div>
  );
}
