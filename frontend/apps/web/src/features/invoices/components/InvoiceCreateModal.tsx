/**
 * InvoiceCreateModal — modal to create a new invoice with proper form fields
 *
 * Location: apps/web/src/features/invoices/components/InvoiceCreateModal.tsx
 *
 * FE-B24: Replaces the zero-field stub in InvoicesPage.
 *
 * Form fields (all optional per InvoiceCreate schema):
 * - Job linkage dropdown (GET /api/v1/jobs/)
 * - Quote linkage dropdown (GET /api/v1/quotes/?status=accepted) — optional
 * - Due date: due_at (date input)
 * - Issue date: issued_at (date input, defaults to today)
 * - Customer notes: textarea
 * - Warning if neither job nor quote selected
 *
 * Submit: POST /api/v1/invoices/ with {quote_id?, job_id?, customer_notes?, due_at?, issued_at?}
 *
 * Pattern: inner <InvoiceCreateModalContent> mounts fresh on each open for clean state.
 */

"use client";

import { useEffect, useRef, useState } from "react";
import { useCreateInvoice } from "../hooks/useCreateInvoice";
import type { InvoiceResponse } from "../hooks/useInvoice";
import { useJobs } from "../../jobs/hooks/useJobs";
import { useQuotes } from "../../quotes/hooks/useQuotes";
import { LoadingState } from "@pilot/ui/states";

interface InvoiceCreateModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess?: (invoice: InvoiceResponse) => void;
  onTaxSetupRequired?: (detail: string) => void;
}

function InvoiceCreateModalContent({
  onClose,
  onSuccess,
  onTaxSetupRequired,
}: {
  onClose: () => void;
  onSuccess?: (invoice: InvoiceResponse) => void;
  onTaxSetupRequired?: (detail: string) => void;
}) {
  const firstFocusRef = useRef<HTMLDivElement>(null);

  const [jobId, setJobId] = useState("");
  const [quoteId, setQuoteId] = useState("");
  const [dueAt, setDueAt] = useState("");
  const [issuedAt, setIssuedAt] = useState(
    new Date().toISOString().split("T")[0],
  );
  const [customerNotes, setCustomerNotes] = useState("");
  const [apiError, setApiError] = useState<string | null>(null);

  const { data: jobsData, isLoading: jobsLoading } = useJobs();
  const jobs = jobsData?.items ?? [];
  const { data: quotesData, isLoading: quotesLoading } = useQuotes({
    status: "accepted",
  });

  const { mutate: createInvoice, isPending } = useCreateInvoice({
    onTaxSetupRequired: (detail) => {
      onTaxSetupRequired?.(detail);
    },
    onSuccess: (invoice) => {
      onSuccess?.(invoice);
      onClose();
    },
  });

  // Focus trap on mount
  useEffect(() => {
    const timer = setTimeout(() => firstFocusRef.current?.focus(), 50);
    return () => clearTimeout(timer);
  }, []);

  const isStandalone = !jobId && !quoteId;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setApiError(null);

    createInvoice(
      {
        job_id: jobId || null,
        quote_id: quoteId || null,
        due_at: dueAt || null,
        issued_at: issuedAt || null,
        customer_notes: customerNotes || null,
      },
      {
        onError: (err) => {
          const status = (err as { response?: { status?: number } })?.response
            ?.status;
          if (status === 412) {
            // Handled by useCreateInvoice — onTaxSetupRequired fires
            return;
          }
          const message =
            (err as { response?: { data?: { detail?: string } } })?.response
              ?.data?.detail ?? "Failed to create invoice. Please try again.";
          setApiError(message);
        },
      },
    );
  }

  const isLoading = jobsLoading || quotesLoading;

  return (
    <div
      ref={firstFocusRef}
      tabIndex={-1}
      className="relative bg-white rounded-lg shadow-xl w-full max-w-lg mx-4 max-h-screen overflow-y-auto focus:outline-none"
    >
      <div className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h2
            id="create-invoice-modal-title"
            className="text-lg font-semibold text-neutral-900"
          >
            Create Invoice
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-neutral-400 hover:text-neutral-600 transition-colors"
            aria-label="Close modal"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {isLoading ? (
          <LoadingState type="inline" label="Loading options..." />
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Standalone warning */}
            {isStandalone && (
              <div
                role="note"
                className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-md px-3 py-2"
                data-testid="standalone-invoice-warning"
              >
                Creating a standalone invoice. Consider linking to a job or
                quote.
              </div>
            )}

            {/* Job linkage */}
            <div>
              <label
                htmlFor="invoice-job"
                className="block text-sm font-medium text-neutral-700 mb-1"
              >
                Link to Job{" "}
                <span className="text-neutral-400 font-normal">(optional)</span>
              </label>
              <select
                id="invoice-job"
                value={jobId}
                onChange={(e) => {
                  setJobId(e.target.value);
                  if (e.target.value) setQuoteId(""); // clear quote when job selected
                }}
                className="w-full px-3 py-2 border border-neutral-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white"
                data-testid="invoice-job-select"
              >
                <option value="">— No job —</option>
                {(jobs ?? []).map((j) => (
                  <option key={j.id} value={j.id}>
                    {j.customer_name} ({j.status_code})
                  </option>
                ))}
              </select>
            </div>

            {/* Quote linkage */}
            <div>
              <label
                htmlFor="invoice-quote"
                className="block text-sm font-medium text-neutral-700 mb-1"
              >
                Link to Quote{" "}
                <span className="text-neutral-400 font-normal">(optional)</span>
              </label>
              <select
                id="invoice-quote"
                value={quoteId}
                onChange={(e) => {
                  setQuoteId(e.target.value);
                  if (e.target.value) setJobId(""); // clear job when quote selected
                }}
                className="w-full px-3 py-2 border border-neutral-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white"
                data-testid="invoice-quote-select"
              >
                <option value="">— No quote —</option>
                {(quotesData?.items ?? []).map((q) => (
                  <option key={q.id} value={q.id}>
                    Quote #{q.id.slice(0, 8)}
                    {q.customer_name ? ` — ${q.customer_name}` : ""}
                  </option>
                ))}
              </select>
            </div>

            {/* Issue Date */}
            <div>
              <label
                htmlFor="invoice-issued-at"
                className="block text-sm font-medium text-neutral-700 mb-1"
              >
                Issue Date
              </label>
              <input
                id="invoice-issued-at"
                type="date"
                value={issuedAt}
                onChange={(e) => setIssuedAt(e.target.value)}
                className="w-full px-3 py-2 border border-neutral-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                data-testid="invoice-issued-at-input"
              />
            </div>

            {/* Due Date */}
            <div>
              <label
                htmlFor="invoice-due-at"
                className="block text-sm font-medium text-neutral-700 mb-1"
              >
                Due Date{" "}
                <span className="text-neutral-400 font-normal">(optional)</span>
              </label>
              <input
                id="invoice-due-at"
                type="date"
                value={dueAt}
                onChange={(e) => setDueAt(e.target.value)}
                className="w-full px-3 py-2 border border-neutral-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                data-testid="invoice-due-at-input"
              />
            </div>

            {/* Customer Notes */}
            <div>
              <label
                htmlFor="invoice-customer-notes"
                className="block text-sm font-medium text-neutral-700 mb-1"
              >
                Customer Notes{" "}
                <span className="text-neutral-400 font-normal">(optional)</span>
              </label>
              <textarea
                id="invoice-customer-notes"
                value={customerNotes}
                onChange={(e) => setCustomerNotes(e.target.value)}
                rows={3}
                placeholder="Thank you for your business."
                className="w-full px-3 py-2 border border-neutral-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 resize-none"
                data-testid="invoice-customer-notes-textarea"
              />
            </div>

            {/* API error */}
            {apiError && (
              <p
                role="alert"
                className="text-sm text-fault-700 bg-fault-50 border border-fault-200 rounded-md px-3 py-2"
              >
                {apiError}
              </p>
            )}

            {/* Actions */}
            <div className="flex gap-3 justify-end pt-2">
              <button
                type="button"
                onClick={onClose}
                disabled={isPending}
                className="px-4 py-2 text-sm font-medium text-neutral-700 border border-neutral-200 rounded-md hover:bg-neutral-50 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isPending}
                className="px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded-md hover:bg-brand-700 disabled:opacity-50"
                data-testid="invoice-create-submit-btn"
              >
                {isPending ? "Creating…" : "Create Invoice"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

export function InvoiceCreateModal({
  open,
  onClose,
  onSuccess,
  onTaxSetupRequired,
}: InvoiceCreateModalProps) {
  useEffect(() => {
    if (!open) return;
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="create-invoice-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-neutral-900 opacity-40"
        onClick={onClose}
        aria-hidden="true"
      />
      {/* Inner content — remounts fresh on each open */}
      <InvoiceCreateModalContent
        onClose={onClose}
        onSuccess={onSuccess}
        onTaxSetupRequired={onTaxSetupRequired}
      />
    </div>
  );
}
