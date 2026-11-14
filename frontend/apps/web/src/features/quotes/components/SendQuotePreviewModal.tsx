/**
 * SendQuotePreviewModal — always-preview-before-send enforcement (mvp-arch §16.7)
 *
 * Location: apps/web/src/features/quotes/components/SendQuotePreviewModal.tsx
 *
 * This modal MUST render before any public link is generated and before any
 * communication is sent to the customer. There is no code path that bypasses it.
 *
 * The useGeneratePublicLink mutation is called ONLY from the "Confirm Send" button
 * handler — never pre-emptively.
 */

"use client";

import React from "react";

interface SendQuotePreviewModalProps {
  open: boolean;
  quoteId: string;
  customerEmail: string | null;
  customerName: string;
  onClose: () => void;
  onConfirm: () => void;
  isConfirming: boolean;
}

export function SendQuotePreviewModal({
  open,
  quoteId,
  customerEmail,
  customerName,
  onClose,
  onConfirm,
  isConfirming,
}: SendQuotePreviewModalProps) {
  if (!open) return null;

  const shortId = quoteId.slice(0, 8);

  return (
    // Backdrop
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/40"
      role="dialog"
      aria-modal="true"
      aria-labelledby="send-preview-title"
      onClick={(e) => {
        // Close on backdrop click
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4 p-6 space-y-5">
        {/* Header */}
        <div>
          <h2
            id="send-preview-title"
            className="text-lg font-semibold text-neutral-900"
          >
            Send Quote to Customer
          </h2>
          <p className="text-sm text-neutral-500 mt-1">
            Review the details before sending.
          </p>
        </div>

        {/* Preview details */}
        <div className="rounded-md border border-neutral-200 divide-y divide-neutral-100 text-sm">
          <div className="flex justify-between px-4 py-3">
            <span className="text-neutral-500 font-medium">Recipient</span>
            <span className="text-neutral-900">
              {customerName}
              {customerEmail ? (
                <span className="text-neutral-500 ml-1">({customerEmail})</span>
              ) : (
                <span className="text-neutral-400 ml-1 italic">
                  (no email on file)
                </span>
              )}
            </span>
          </div>
          <div className="flex justify-between px-4 py-3">
            <span className="text-neutral-500 font-medium">Channel</span>
            <span className="text-neutral-900">Email</span>
          </div>
          <div className="flex justify-between px-4 py-3">
            <span className="text-neutral-500 font-medium">Quote</span>
            <span className="text-neutral-900 font-mono text-xs">
              {shortId}…
            </span>
          </div>
          <div className="px-4 py-3">
            <span className="text-neutral-500 font-medium block mb-1">
              Action
            </span>
            <span className="text-neutral-700">
              A secure link to Quote{" "}
              <span className="font-mono text-xs">{shortId}…</span> will be
              sent. The customer can view and accept from the link.
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
