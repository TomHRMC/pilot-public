/**
 * InvoiceAmountSelector — FE-B14
 *
 * Location: apps/web/src/features/public-invoice/InvoiceAmountSelector.tsx
 *
 * Amount selection UI per design doc Decision 3:
 *  - Default: full amount_due_cents pre-filled, "Adjust amount" checkbox unchecked
 *  - Adjusted: amount input editable, comment textarea required, variance row shown
 *
 * RULE 6: PaymentIntent is created with ACTUAL chosen amount, not full invoice amount.
 * Validation blocks submission before any network call.
 *
 * RULE 1: No useAuth().
 */

"use client";

import React from "react";
import type { AmountSelectorState } from "./types";
import { derivePaymentVariance } from "./types";

function formatCents(cents: number, currency = "USD"): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
  }).format(cents / 100);
}

const MAX_COMMENT_CHARS = 2000;

interface InvoiceAmountSelectorProps {
  invoiceAmountDueCents: number;
  invoiceTotalCents: number;
  tenantName: string;
  currency?: string;
  state: AmountSelectorState;
  onStateChange: (update: Partial<AmountSelectorState>) => void;
  onContinue: (amountCents: number, comment?: string) => void;
  isLoading?: boolean;
}

export function InvoiceAmountSelector({
  invoiceAmountDueCents,
  invoiceTotalCents,
  tenantName,
  currency = "USD",
  state,
  onStateChange,
  onContinue,
  isLoading = false,
}: InvoiceAmountSelectorProps) {
  const selectedAmount = state.adjusting
    ? state.customAmountCents
    : invoiceAmountDueCents;

  const { varianceCents, remainingCents, isOverpayment } = state.adjusting
    ? derivePaymentVariance(selectedAmount, invoiceTotalCents)
    : { varianceCents: 0, remainingCents: 0, isOverpayment: false };

  const showVariance =
    state.adjusting && selectedAmount !== invoiceAmountDueCents;

  function handleContinue(e: React.FormEvent) {
    e.preventDefault();

    let hasError = false;

    // Validate amount > 0
    if (selectedAmount <= 0) {
      onStateChange({ amountError: "Amount must be greater than $0." });
      hasError = true;
    } else {
      onStateChange({ amountError: null });
    }

    // Validate comment required when adjusting
    if (state.adjusting && !state.comment.trim()) {
      onStateChange({
        commentError: "Please explain why you're paying a different amount.",
      });
      hasError = true;
    } else {
      onStateChange({ commentError: null });
    }

    if (hasError) return;

    // RULE 6: Pass ACTUAL selected amount, not full invoice amount
    onContinue(
      selectedAmount,
      state.adjusting ? state.comment.trim() : undefined,
    );
  }

  function handleAmountInput(raw: string) {
    // Convert dollar input to cents
    const dollars = parseFloat(raw.replace(/[^0-9.]/g, ""));
    const cents = isNaN(dollars) ? 0 : Math.round(dollars * 100);
    onStateChange({ customAmountCents: cents, amountError: null });
  }

  return (
    <form
      onSubmit={handleContinue}
      className="flex flex-col gap-5"
      data-testid="invoice-amount-selector"
    >
      {/* Amount display */}
      <div>
        <label className="block text-sm font-medium text-neutral-700 mb-1">
          Payment amount
        </label>

        {!state.adjusting ? (
          <div
            className="rounded-lg border border-neutral-200 bg-neutral-50 px-4 py-3 text-lg font-semibold text-neutral-900"
            data-testid="full-amount-display"
          >
            {formatCents(invoiceAmountDueCents, currency)}
          </div>
        ) : (
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-500 text-sm">
              $
            </span>
            <input
              type="number"
              step="0.01"
              min="0.01"
              data-testid="custom-amount-input"
              defaultValue={(state.customAmountCents / 100).toFixed(2)}
              onChange={(e) => handleAmountInput(e.target.value)}
              className="w-full rounded-lg border border-neutral-300 pl-7 pr-4 py-3 text-lg font-semibold text-neutral-900 focus:border-neutral-400 focus:outline-none focus:ring-1 focus:ring-neutral-400"
            />
          </div>
        )}

        {state.amountError && (
          <p className="mt-1 text-sm text-fault-600" data-testid="amount-error">
            {state.amountError}
          </p>
        )}
      </div>

      {/* "Adjust amount" checkbox */}
      <label className="flex items-center gap-2.5 cursor-pointer select-none">
        <input
          type="checkbox"
          data-testid="adjust-amount-checkbox"
          checked={state.adjusting}
          onChange={(e) => {
            onStateChange({
              adjusting: e.target.checked,
              customAmountCents: invoiceAmountDueCents,
              comment: "",
              commentError: null,
              amountError: null,
            });
          }}
          className="h-4 w-4 rounded border-neutral-300 accent-brand-600"
        />
        <span className="text-sm text-neutral-700">
          Adjust amount (pay more or less)
        </span>
      </label>

      {/* Variance display */}
      {showVariance && (
        <div
          className="rounded-lg border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm flex flex-col gap-1"
          data-testid="variance-display"
        >
          <div className="flex justify-between text-neutral-700">
            <span>Variance</span>
            <span
              className={
                isOverpayment
                  ? "text-margin-700 font-medium"
                  : "text-neutral-700"
              }
            >
              {varianceCents > 0 ? "+" : ""}
              {formatCents(varianceCents, currency)} (
              {isOverpayment
                ? "overpayment"
                : `${Math.round(Math.abs(varianceCents / invoiceTotalCents) * 100)}% less`}
              )
            </span>
          </div>
          {!isOverpayment && remainingCents > 0 && (
            <div className="flex justify-between text-neutral-500">
              <span>Remaining balance after this payment</span>
              <span>{formatCents(remainingCents, currency)}</span>
            </div>
          )}
          {!isOverpayment && remainingCents > 0 && (
            <p className="text-xs text-neutral-400 mt-1">
              The remaining balance of {formatCents(remainingCents, currency)}{" "}
              will stay on your invoice. {tenantName} can collect the remainder
              later.
            </p>
          )}
        </div>
      )}

      {/* Comment textarea — only visible when adjusting */}
      {state.adjusting && (
        <div data-testid="variance-comment-field">
          <label
            htmlFor="variance-comment"
            className="block text-sm font-medium text-neutral-700"
          >
            Reason for different amount{" "}
            <span className="text-fault-600">*</span>
          </label>
          <textarea
            id="variance-comment"
            data-testid="variance-comment-input"
            value={state.comment}
            onChange={(e) =>
              onStateChange({
                comment: e.target.value.slice(0, MAX_COMMENT_CHARS),
                commentError: null,
              })
            }
            rows={3}
            placeholder="e.g. Paying deposit now, will pay remainder on completion..."
            className="mt-1 w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm text-neutral-800 placeholder:text-neutral-400 focus:border-neutral-400 focus:outline-none focus:ring-1 focus:ring-neutral-400"
          />
          <div className="flex items-start justify-between mt-1">
            {state.commentError && (
              <p className="text-xs text-fault-600" data-testid="comment-error">
                {state.commentError}
              </p>
            )}
            <p
              className="ml-auto text-xs text-neutral-400"
              data-testid="variance-comment-counter"
            >
              {state.comment.length} / {MAX_COMMENT_CHARS}
            </p>
          </div>
        </div>
      )}

      <button
        type="submit"
        disabled={isLoading}
        className="w-full rounded-lg bg-brand-600 py-3 px-6 text-sm font-semibold text-white hover:bg-brand-800 disabled:opacity-50"
        data-testid="continue-to-payment-button"
      >
        {isLoading
          ? "Creating payment…"
          : `Continue to payment — ${formatCents(selectedAmount, currency)}`}
      </button>
    </form>
  );
}
