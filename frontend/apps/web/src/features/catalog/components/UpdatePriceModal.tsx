/**
 * UpdatePriceModal — modal for adding a new price version to a pricebook item
 *
 * Location: apps/web/src/features/catalog/components/UpdatePriceModal.tsx
 *
 * Uses temporal versioning: POSTs a new price version via useAddPricebookItemPrice.
 * Current price is shown as reference only.
 */

"use client";

import { useEffect, useRef, useState } from "react";
import { useAddPricebookItemPrice } from "../hooks/useAddPricebookItemPrice";

interface UpdatePriceModalProps {
  open: boolean;
  itemId: string;
  itemName: string;
  currentPriceCents: number;
  onClose: () => void;
}

export function UpdatePriceModal({
  open,
  itemId,
  itemName,
  currentPriceCents,
  onClose,
}: UpdatePriceModalProps) {
  const { mutate, isPending, reset } = useAddPricebookItemPrice();
  const firstFocusRef = useRef<HTMLDivElement>(null);
  const [priceDollars, setPriceDollars] = useState("");
  const [effectiveFrom, setEffectiveFrom] = useState(
    new Date().toISOString().slice(0, 10),
  );

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  // Focus trap on open
  useEffect(() => {
    if (open) {
      setTimeout(() => firstFocusRef.current?.focus(), 50);
    } else {
      reset();
    }
  }, [open, reset]);

  if (!open) return null;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const priceCents = Math.round(parseFloat(priceDollars) * 100);
    const effectiveFromISO = new Date(
      effectiveFrom + "T00:00:00Z",
    ).toISOString();
    mutate(
      {
        itemId,
        payload: {
          unit_price_cents: priceCents,
          effective_from: effectiveFromISO,
        },
      },
      { onSuccess: () => onClose() },
    );
  }

  const inputClass =
    "w-full rounded-md border border-neutral-300 px-3 py-2 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-brand-600";

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="update-price-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center"
    >
      <div
        className="absolute inset-0 bg-neutral-900 opacity-40"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        ref={firstFocusRef}
        tabIndex={-1}
        className="relative bg-white rounded-lg shadow-xl w-full max-w-md mx-4 focus:outline-none"
      >
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2
              id="update-price-modal-title"
              className="text-lg font-semibold text-neutral-900"
            >
              Update Price
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

          <p className="text-sm text-neutral-600 mb-4">
            <span className="font-medium">{itemName}</span>
            <br />
            Current price:{" "}
            <span className="font-medium">
              ${(currentPriceCents / 100).toFixed(2)}
            </span>
          </p>

          <form onSubmit={handleSubmit} noValidate>
            <div className="space-y-4">
              <div>
                <label
                  htmlFor="new-price"
                  className="block text-sm font-medium text-neutral-700 mb-1"
                >
                  New Unit Price ($) <span className="text-error-600">*</span>
                </label>
                <input
                  id="new-price"
                  type="number"
                  min="0"
                  step="0.01"
                  required
                  value={priceDollars}
                  onChange={(e) => setPriceDollars(e.target.value)}
                  className={inputClass}
                  placeholder="0.00"
                />
              </div>
              <div>
                <label
                  htmlFor="effective-from"
                  className="block text-sm font-medium text-neutral-700 mb-1"
                >
                  Effective From <span className="text-error-600">*</span>
                </label>
                <input
                  id="effective-from"
                  type="date"
                  required
                  value={effectiveFrom}
                  onChange={(e) => setEffectiveFrom(e.target.value)}
                  className={inputClass}
                />
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-3">
              <button
                type="button"
                onClick={onClose}
                disabled={isPending}
                className="px-4 py-2 rounded-md border border-neutral-300 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isPending || !priceDollars}
                className="px-4 py-2 rounded-md bg-brand-600 text-white text-sm font-medium hover:bg-brand-700 transition-colors disabled:opacity-50"
              >
                {isPending ? "Saving…" : "Update Price"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
