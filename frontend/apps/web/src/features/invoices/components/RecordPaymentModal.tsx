/**
 * RecordPaymentModal — record a manual payment against an invoice
 *
 * Location: apps/web/src/features/invoices/components/RecordPaymentModal.tsx
 *
 * Pre-work decisions:
 *  - payment_method table is empty; no lookup endpoint exists
 *  - Uses paid_via dropdown ("check", "cash", "bank_transfer", "credit_card", "other")
 *  - payment_method_id: MANUAL_PAYMENT_METHOD_ID sentinel
 *  - payment_status_id: PAYMENT_STATUS_SUCCEEDED_ID (succeeded)
 *  - Amount pre-filled with balance_due_cents (allow partial)
 *  - Date defaults to today
 */

"use client";

import { useState } from "react";
import { useNotificationQueue } from "@pilot/ui/notification-banner";
import {
  useRecordPayment,
  MANUAL_PAYMENT_METHOD_ID,
  PAYMENT_STATUS_SUCCEEDED_ID,
} from "../hooks/useRecordPayment";

interface RecordPaymentModalProps {
  open: boolean;
  invoiceId: string;
  balanceDueCents: number;
  onClose: () => void;
}

const PAID_VIA_OPTIONS = [
  { label: "Check", value: "check" },
  { label: "Cash", value: "cash" },
  { label: "Bank Transfer (ACH)", value: "bank_transfer" },
  { label: "Credit Card", value: "credit_card" },
  { label: "Other", value: "other" },
];

function centsToDecimal(cents: number): string {
  return (cents / 100).toFixed(2);
}

function decimalToCents(value: string): number {
  const num = parseFloat(value);
  return isNaN(num) ? 0 : Math.round(num * 100);
}

export function RecordPaymentModal({
  open,
  invoiceId,
  balanceDueCents,
  onClose,
}: RecordPaymentModalProps) {
  const { addNotification } = useNotificationQueue();

  const [amountStr, setAmountStr] = useState(centsToDecimal(balanceDueCents));
  const [paidVia, setPaidVia] = useState("check");
  const [paidAt, setPaidAt] = useState(
    () => new Date().toISOString().split("T")[0],
  );
  const [reference, setReference] = useState("");

  const { mutate: recordPayment, isPending } = useRecordPayment({
    invoiceId,
    onSuccess: () => {
      addNotification({
        id: `payment-recorded-${invoiceId}`,
        severity: "success",
        title: "Payment recorded successfully.",
      });
      onClose();
    },
    onError: (problem) => {
      addNotification({
        id: `payment-error-${invoiceId}-${Date.now()}`,
        severity: "error",
        title: problem.title ?? "Payment failed",
        detail: problem.detail ?? "Could not record payment. Please try again.",
      });
    },
  });

  if (!open) return null;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const amountCents = decimalToCents(amountStr);
    if (amountCents <= 0) return;

    recordPayment({
      amount_cents: amountCents,
      paid_via: paidVia,
      payment_method_id: MANUAL_PAYMENT_METHOD_ID,
      payment_status_id: PAYMENT_STATUS_SUCCEEDED_ID,
      paid_at: new Date(paidAt).toISOString(),
      reference: reference || null,
      idempotency_key: `pay-${invoiceId}-${Date.now()}`,
    });
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40"
      role="dialog"
      aria-modal="true"
      aria-labelledby="record-payment-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4 p-6 space-y-5">
        <div>
          <h2
            id="record-payment-title"
            className="text-lg font-semibold text-neutral-900"
          >
            Record Payment
          </h2>
          <p className="text-sm text-neutral-500 mt-1">
            Log a payment received against this invoice.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Amount */}
          <div>
            <label
              htmlFor="payment-amount"
              className="block text-sm font-medium text-neutral-700 mb-1"
            >
              Amount ($)
            </label>
            <input
              id="payment-amount"
              type="number"
              step="0.01"
              min="0.01"
              value={amountStr}
              onChange={(e) => setAmountStr(e.target.value)}
              required
              className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-brand-400"
            />
          </div>

          {/* Payment Method */}
          <div>
            <label
              htmlFor="payment-method"
              className="block text-sm font-medium text-neutral-700 mb-1"
            >
              Payment Method
            </label>
            <select
              id="payment-method"
              value={paidVia}
              onChange={(e) => setPaidVia(e.target.value)}
              className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-brand-400"
            >
              {PAID_VIA_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Payment Date */}
          <div>
            <label
              htmlFor="payment-date"
              className="block text-sm font-medium text-neutral-700 mb-1"
            >
              Date
            </label>
            <input
              id="payment-date"
              type="date"
              value={paidAt}
              onChange={(e) => setPaidAt(e.target.value)}
              required
              className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-brand-400"
            />
          </div>

          {/* Reference (optional) */}
          <div>
            <label
              htmlFor="payment-reference"
              className="block text-sm font-medium text-neutral-700 mb-1"
            >
              Reference <span className="text-neutral-400">(optional)</span>
            </label>
            <input
              id="payment-reference"
              type="text"
              value={reference}
              onChange={(e) => setReference(e.target.value)}
              placeholder="Check #, transaction ID, etc."
              className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-brand-400"
            />
          </div>

          {/* Actions */}
          <div className="flex gap-3 justify-end pt-1">
            <button
              type="button"
              onClick={onClose}
              disabled={isPending}
              className="px-4 py-2 text-sm font-medium text-neutral-700 border border-neutral-200 rounded-md hover:bg-neutral-50 transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isPending || decimalToCents(amountStr) <= 0}
              className="px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded-md hover:bg-brand-700 transition-colors disabled:opacity-50"
            >
              {isPending ? "Recording…" : "Record Payment"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
