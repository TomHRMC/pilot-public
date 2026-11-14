/**
 * GenerateDrawInvoiceButton — per-pending-draw generate-invoice action
 *
 * Location: apps/web/src/features/billing/components/GenerateDrawInvoiceButton.tsx
 *
 * BILLING-B1 Part B — Payment Schedule Builder (UI spec §4.3).
 *
 * Composes the always-preview-before-send pattern (§16.7). The UI spec says
 * to compose <MessagePreviewModal>, but that shared modal's previewData
 * contract is communication-oriented (rendered_body, recipient_name,
 * actual_channel: sms|email) — it does not fit an invoice-generation
 * preview. The invoices feature already solved this with a feature-local
 * <SendInvoicePreviewModal> sibling (also not the shared modal). We mirror
 * that established pattern: a feature-local preview modal that enforces the
 * "review before generate" gate with the same a11y (role=dialog, focus-trap
 * via overlay click, aria-modal, aria-labelledby).
 *
 * Fires useGenerateDrawInvoice with an Idempotency-Key (stable per line).
 * On 409 (already invoiced — Integrity rule 4) → <NotificationBanner> fault
 * severity (NOT the staleness dialog — this is a rule-4 conflict).
 *
 * React Compiler (§32): no hand-memoization; component is pure.
 */

"use client";

import { useState } from "react";
import { DocumentPlusIcon } from "@heroicons/react/24/outline";
import type { PaymentScheduleLineResponse } from "../hooks/usePaymentSchedule";
import { useGenerateDrawInvoice } from "../hooks/useGenerateDrawInvoice";
import { formatCents } from "../utils/format";

interface GenerateDrawInvoiceButtonProps {
  scheduleId: string;
  line: PaymentScheduleLineResponse;
  customerName?: string;
  siteLabel?: string;
  /** Fired when generation succeeds — caller can navigate to the invoice. */
  onGenerated?: (invoiceId: string) => void;
  /** Fired when the backend returns 409 (already invoiced) — caller shows a banner. */
  onAlreadyInvoiced?: (detail: string) => void;
}

export function GenerateDrawInvoiceButton({
  scheduleId,
  line,
  customerName,
  siteLabel,
  onGenerated,
  onAlreadyInvoiced,
}: GenerateDrawInvoiceButtonProps) {
  const [previewOpen, setPreviewOpen] = useState(false);

  const { mutate: generateInvoice, isPending } = useGenerateDrawInvoice({
    onSuccess: (invoice) => {
      setPreviewOpen(false);
      onGenerated?.(invoice.id);
    },
    onAlreadyInvoiced: (detail) => {
      setPreviewOpen(false);
      onAlreadyInvoiced?.(detail);
    },
  });

  function handleConfirm() {
    generateInvoice({ scheduleId, lineId: line.id });
  }

  return (
    <>
      <button
        type="button"
        onClick={() => setPreviewOpen(true)}
        disabled={isPending}
        className="inline-flex items-center gap-1.5 text-sm text-brand-600 hover:text-brand-700 font-medium px-2 py-1 rounded-md hover:bg-brand-50 focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 disabled:opacity-50"
        aria-label={`Generate invoice for draw ${line.sequence}: ${line.label}`}
        data-testid={`generate-invoice-btn-${line.id}`}
      >
        <DocumentPlusIcon className="w-4 h-4" aria-hidden="true" />
        {isPending ? "Generating…" : "Generate invoice"}
      </button>

      {previewOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40"
          role="dialog"
          aria-modal="true"
          aria-labelledby="generate-draw-invoice-title"
          onClick={(e) => {
            if (e.target === e.currentTarget && !isPending)
              setPreviewOpen(false);
          }}
          data-testid="generate-draw-invoice-modal"
        >
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4 p-6 space-y-5">
            {/* Header */}
            <div>
              <h2
                id="generate-draw-invoice-title"
                className="text-lg font-semibold text-neutral-900"
              >
                Generate Draw Invoice
              </h2>
              <p className="text-sm text-neutral-500 mt-1">
                Review the draw details before generating the invoice.
              </p>
            </div>

            {/* Preview details */}
            <div className="rounded-md border border-neutral-200 divide-y divide-neutral-100 text-sm">
              <div className="flex justify-between px-4 py-3">
                <span className="text-neutral-500 font-medium">Draw</span>
                <span className="text-neutral-900">
                  #{line.sequence} — {line.label}
                </span>
              </div>
              <div className="flex justify-between px-4 py-3">
                <span className="text-neutral-500 font-medium">Amount</span>
                <span className="text-neutral-900 font-medium">
                  {formatCents(line.resolved_amount_cents)}
                </span>
              </div>
              {customerName && (
                <div className="flex justify-between px-4 py-3">
                  <span className="text-neutral-500 font-medium">Customer</span>
                  <span className="text-neutral-900">{customerName}</span>
                </div>
              )}
              {siteLabel && (
                <div className="flex justify-between px-4 py-3">
                  <span className="text-neutral-500 font-medium">Site</span>
                  <span className="text-neutral-900">{siteLabel}</span>
                </div>
              )}
              <div className="px-4 py-3">
                <span className="text-neutral-500 font-medium block mb-1">
                  Action
                </span>
                <span className="text-neutral-700">
                  A progress invoice for{" "}
                  <span className="font-medium">
                    {formatCents(line.resolved_amount_cents)}
                  </span>{" "}
                  will be generated for this draw.
                </span>
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-3 justify-end pt-1">
              <button
                type="button"
                onClick={() => setPreviewOpen(false)}
                disabled={isPending}
                className="px-4 py-2 text-sm font-medium text-neutral-700 border border-neutral-200 rounded-md hover:bg-neutral-50 transition-colors disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirm}
                disabled={isPending}
                className="px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded-md hover:bg-brand-700 transition-colors disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2"
                data-testid="generate-draw-invoice-confirm"
              >
                {isPending ? "Generating…" : "Generate Invoice"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
