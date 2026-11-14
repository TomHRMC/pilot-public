/**
 * InvoicePartialPaidState — FE-B14
 *
 * Location: apps/web/src/features/public-invoice/InvoicePartialPaidState.tsx
 *
 * State-aware revisit: renders when invoice.status === 'partial'.
 * Shows payment history + "Pay remaining $X" CTA.
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

interface InvoicePartialPaidStateProps {
  amountPaidCents: number;
  amountDueCents: number;
  invoiceTotalCents: number;
  currency?: string;
  onPayRemaining: () => void;
  /**
   * STRIPE-CONNECT-1-C: when false, the "Pay remaining" CTA is suppressed so the
   * customer never sees a button that opens a modal which will 402. Defaults true
   * for backward compatibility (existing callers/tests unaffected).
   */
  cardPaymentsEnabled?: boolean;
}

export function InvoicePartialPaidState({
  amountPaidCents,
  amountDueCents,
  invoiceTotalCents,
  currency = "USD",
  onPayRemaining,
  cardPaymentsEnabled = true,
}: InvoicePartialPaidStateProps) {
  return (
    <div
      className="rounded-xl border border-neutral-200 bg-white p-6 flex flex-col gap-4"
      data-testid="invoice-partial-paid-state"
    >
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-neutral-700">
          Payment status
        </h3>
        <span className="inline-flex items-center rounded-full bg-neutral-100 px-2.5 py-0.5 text-xs font-medium text-neutral-700">
          Partial
        </span>
      </div>

      {/* Progress bar */}
      <div>
        <div className="flex justify-between text-xs text-neutral-500 mb-1">
          <span>Paid</span>
          <span>
            {formatCents(amountPaidCents, currency)} of{" "}
            {formatCents(invoiceTotalCents, currency)}
          </span>
        </div>
        <div className="h-2 w-full rounded-full bg-neutral-200">
          <div
            className="h-2 rounded-full bg-margin-400"
            style={{
              width: `${Math.min(100, (amountPaidCents / invoiceTotalCents) * 100)}%`,
            }}
            data-testid="partial-progress-bar"
          />
        </div>
      </div>

      {/* Summary rows */}
      <div className="flex flex-col gap-1.5 text-sm">
        <div className="flex justify-between text-neutral-600">
          <span>Paid so far</span>
          <span className="font-medium text-margin-700">
            {formatCents(amountPaidCents, currency)}
          </span>
        </div>
        <div className="flex justify-between text-neutral-600">
          <span>Remaining balance</span>
          <span
            className="font-semibold text-neutral-900"
            data-testid="remaining-balance"
          >
            {formatCents(amountDueCents, currency)}
          </span>
        </div>
      </div>

      {/* Pay remaining CTA — suppressed when card payments are disabled (STRIPE-CONNECT-1-C) */}
      {cardPaymentsEnabled && (
        <button
          onClick={onPayRemaining}
          className="w-full rounded-lg bg-brand-600 py-3 px-6 text-sm font-semibold text-white hover:bg-brand-800"
          data-testid="pay-remaining-button"
        >
          Pay remaining {formatCents(amountDueCents, currency)}
        </button>
      )}
    </div>
  );
}
