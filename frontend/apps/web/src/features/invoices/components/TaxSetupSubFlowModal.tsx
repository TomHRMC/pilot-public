/**
 * TaxSetupSubFlowModal — intercepts 412 Precondition Required from useCreateInvoice
 *
 * Location: apps/web/src/features/invoices/components/TaxSetupSubFlowModal.tsx
 *
 * Pre-work finding: No tax jurisdiction endpoint exists (no POST /api/v1/settings/tax-jurisdiction).
 * Tax paths in OpenAPI: /api/v1/reports/tax-liability (report only, not configuration).
 *
 * Decision (design doc §G): Show user-friendly error with link to Settings → Tax.
 * DO NOT silently ignore the 412.
 *
 * Opens when useCreateInvoice receives HTTP 412.
 */

"use client";

interface TaxSetupSubFlowModalProps {
  open: boolean;
  detail?: string;
  onClose: () => void;
}

export function TaxSetupSubFlowModal({
  open,
  detail,
  onClose,
}: TaxSetupSubFlowModalProps) {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40"
      role="dialog"
      aria-modal="true"
      aria-labelledby="tax-setup-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4 p-6 space-y-5">
        {/* Icon + Header */}
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 w-10 h-10 rounded-full bg-alert-100 flex items-center justify-center">
            <span className="text-alert-600 text-lg" aria-hidden="true">
              ⚠
            </span>
          </div>
          <div>
            <h2
              id="tax-setup-title"
              className="text-lg font-semibold text-neutral-900"
            >
              Tax Configuration Required
            </h2>
            <p className="text-sm text-neutral-500 mt-1">
              Invoice creation requires tax rates to be configured first.
            </p>
          </div>
        </div>

        {/* Detail message from 412 response */}
        <div className="rounded-md border border-alert-200 bg-alert-50 px-4 py-3 text-sm text-alert-700">
          {detail ?? "Tax rates must be configured before creating invoices."}
        </div>

        {/* Instructions */}
        <div className="text-sm text-neutral-700 space-y-2">
          <p>To configure tax rates:</p>
          <ol className="list-decimal list-inside space-y-1 text-neutral-600">
            <li>
              Go to{" "}
              <a
                href="/settings/tax"
                className="text-brand-600 hover:underline font-medium"
                data-testid="tax-settings-link"
              >
                Settings → Tax
              </a>
            </li>
            <li>Add your jurisdiction and default tax rate</li>
            <li>Return here and create the invoice again</li>
          </ol>
        </div>

        {/* Actions */}
        <div className="flex gap-3 justify-end pt-1">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-neutral-700 border border-neutral-200 rounded-md hover:bg-neutral-50 transition-colors"
          >
            Close
          </button>
          <a
            href="/settings/tax"
            className="px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded-md hover:bg-brand-700 transition-colors"
          >
            Configure Tax
          </a>
        </div>
      </div>
    </div>
  );
}
