/**
 * SendInvoicePreviewModal — always-preview-before-send enforcement (mvp-arch §16.7)
 *
 * Location: apps/web/src/features/invoices/components/SendInvoicePreviewModal.tsx
 *
 * This modal MUST render before the invoice send API is called. There is no
 * code path that bypasses it.
 *
 * useSendInvoice is called ONLY from the "Confirm Send" button handler (onConfirm).
 * Never pre-emptively.
 *
 * Pattern mirrors SendQuotePreviewModal (FE-B19).
 */

"use client";

interface SendInvoicePreviewModalProps {
  open: boolean;
  invoiceId: string;
  invoiceNumber: string;
  customerEmail: string | null;
  onClose: () => void;
  onConfirm: () => void;
  isConfirming: boolean;
}

export function SendInvoicePreviewModal({
  open,
  invoiceId,
  invoiceNumber,
  customerEmail,
  onClose,
  onConfirm,
  isConfirming,
}: SendInvoicePreviewModalProps) {
  if (!open) return null;

  const shortId = invoiceId.slice(0, 8);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40"
      role="dialog"
      aria-modal="true"
      aria-labelledby="send-invoice-preview-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4 p-6 space-y-5">
        {/* Header */}
        <div>
          <h2
            id="send-invoice-preview-title"
            className="text-lg font-semibold text-neutral-900"
          >
            Send Invoice to Customer
          </h2>
          <p className="text-sm text-neutral-500 mt-1">
            Review the details before sending.
          </p>
        </div>

        {/* Preview details */}
        <div className="rounded-md border border-neutral-200 divide-y divide-neutral-100 text-sm">
          <div className="flex justify-between px-4 py-3">
            <span className="text-neutral-500 font-medium">Invoice</span>
            <span className="text-neutral-900 font-mono">{invoiceNumber}</span>
          </div>
          <div className="flex justify-between px-4 py-3">
            <span className="text-neutral-500 font-medium">Invoice ID</span>
            <span className="text-neutral-900 font-mono text-xs">
              {shortId}…
            </span>
          </div>
          <div className="flex justify-between px-4 py-3">
            <span className="text-neutral-500 font-medium">Recipient</span>
            <span className="text-neutral-900">
              {customerEmail ? (
                customerEmail
              ) : (
                <span className="text-neutral-400 italic">
                  (no email on file)
                </span>
              )}
            </span>
          </div>
          <div className="flex justify-between px-4 py-3">
            <span className="text-neutral-500 font-medium">Channel</span>
            <span className="text-neutral-900">Email</span>
          </div>
          <div className="px-4 py-3">
            <span className="text-neutral-500 font-medium block mb-1">
              Action
            </span>
            <span className="text-neutral-700">
              A secure payment link for Invoice{" "}
              <span className="font-mono text-xs">{invoiceNumber}</span> will be
              generated and sent to the customer.
            </span>
          </div>
        </div>

        {!customerEmail && (
          <p className="text-xs text-alert-600 bg-alert-50 border border-alert-200 rounded px-3 py-2">
            ⚠ This customer has no email address on file. Add one in the
            customer profile before sending.
          </p>
        )}

        {/* Actions */}
        <div className="flex gap-3 justify-end pt-1">
          <button
            type="button"
            onClick={onClose}
            disabled={isConfirming}
            className="px-4 py-2 text-sm font-medium text-neutral-700 border border-neutral-200 rounded-md hover:bg-neutral-50 transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isConfirming || !customerEmail}
            className="px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded-md hover:bg-brand-700 transition-colors disabled:opacity-50"
          >
            {isConfirming ? "Sending…" : "Confirm Send"}
          </button>
        </div>
      </div>
    </div>
  );
}
