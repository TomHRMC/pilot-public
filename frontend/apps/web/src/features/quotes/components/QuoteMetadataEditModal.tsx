/**
 * QuoteMetadataEditModal — edit expires_at and currency on draft quotes
 *
 * Location: apps/web/src/features/quotes/components/QuoteMetadataEditModal.tsx
 *
 * FE-B24: Opened from QuoteDetailPage when quote.status === "draft".
 * Only renders for draft quotes — the caller controls the open prop.
 *
 * Fields:
 * - expires_at: date picker (pre-populated from currentExpiresAt)
 * - currency: select (USD, CAD — only USD for MVP; keep dropdown, default USD)
 *
 * Submit: PATCH /api/v1/quotes/{quoteId} via useUpdateQuote.
 *
 * Pattern: inner content mounts fresh on each open.
 */

"use client";

import { useEffect, useRef, useState } from "react";
import { useUpdateQuote } from "../hooks/useUpdateQuote";

interface QuoteMetadataEditModalProps {
  quoteId: string;
  currentExpiresAt: string | null;
  currentCurrency: string;
  open: boolean;
  onClose: () => void;
}

function QuoteMetadataEditContent({
  quoteId,
  currentExpiresAt,
  currentCurrency,
  onClose,
}: {
  quoteId: string;
  currentExpiresAt: string | null;
  currentCurrency: string;
  onClose: () => void;
}) {
  const firstFocusRef = useRef<HTMLDivElement>(null);

  // Pre-populate from current values — convert ISO to date string for input
  const initialExpiresAt = currentExpiresAt
    ? currentExpiresAt.split("T")[0]
    : "";
  const [expiresAt, setExpiresAt] = useState(initialExpiresAt);
  const [currency, setCurrency] = useState(currentCurrency ?? "USD");
  const [apiError, setApiError] = useState<string | null>(null);

  const { mutate: updateQuote, isPending } = useUpdateQuote(quoteId);

  // Focus trap on mount
  useEffect(() => {
    const timer = setTimeout(() => firstFocusRef.current?.focus(), 50);
    return () => clearTimeout(timer);
  }, []);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setApiError(null);

    updateQuote(
      {
        expires_at: expiresAt ? `${expiresAt}T23:59:59Z` : null,
        currency,
      },
      {
        onSuccess: () => {
          onClose();
        },
        onError: (err) => {
          const message =
            (err as { response?: { data?: { detail?: string } } })?.response
              ?.data?.detail ?? "Failed to update quote. Please try again.";
          setApiError(message);
        },
      },
    );
  }

  return (
    <div
      ref={firstFocusRef}
      tabIndex={-1}
      className="relative bg-white rounded-lg shadow-xl w-full max-w-md mx-4 focus:outline-none"
    >
      <div className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h2
            id="quote-metadata-edit-title"
            className="text-lg font-semibold text-neutral-900"
          >
            Edit Quote
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

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Expiry date */}
          <div>
            <label
              htmlFor="quote-expires-at"
              className="block text-sm font-medium text-neutral-700 mb-1"
            >
              Expiry Date{" "}
              <span className="text-neutral-400 font-normal">(optional)</span>
            </label>
            <input
              id="quote-expires-at"
              type="date"
              value={expiresAt}
              onChange={(e) => setExpiresAt(e.target.value)}
              className="w-full px-3 py-2 border border-neutral-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              data-testid="quote-expires-at-input"
            />
          </div>

          {/* Currency */}
          <div>
            <label
              htmlFor="quote-currency"
              className="block text-sm font-medium text-neutral-700 mb-1"
            >
              Currency
            </label>
            <select
              id="quote-currency"
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              className="w-full px-3 py-2 border border-neutral-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white"
              data-testid="quote-currency-select"
            >
              <option value="USD">USD — US Dollar</option>
              <option value="CAD">CAD — Canadian Dollar</option>
            </select>
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
              data-testid="quote-metadata-save-btn"
            >
              {isPending ? "Saving…" : "Save Changes"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export function QuoteMetadataEditModal({
  quoteId,
  currentExpiresAt,
  currentCurrency,
  open,
  onClose,
}: QuoteMetadataEditModalProps) {
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
      aria-labelledby="quote-metadata-edit-title"
      className="fixed inset-0 z-50 flex items-center justify-center"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-neutral-900 opacity-40"
        onClick={onClose}
        aria-hidden="true"
      />
      {/* Inner content — remounts fresh on each open */}
      <QuoteMetadataEditContent
        quoteId={quoteId}
        currentExpiresAt={currentExpiresAt}
        currentCurrency={currentCurrency}
        onClose={onClose}
      />
    </div>
  );
}
