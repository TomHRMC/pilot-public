/**
 * RejectCommentModal — modal for reject action
 *
 * Location: apps/web/src/features/quote-approval/components/RejectCommentModal.tsx
 *
 * Overall reason textarea (required).
 * Calls POST /api/v1/quotes/{id}/reject
 */

"use client";

import React, { useEffect, useRef, useState } from "react";
import { useQuoteReject } from "../hooks/useQuoteApprove";

interface RejectCommentModalProps {
  quoteId: string;
  onClose: () => void;
}

export function RejectCommentModal({
  quoteId,
  onClose,
}: RejectCommentModalProps) {
  const [reason, setReason] = useState("");
  const reject = useQuoteReject(quoteId);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!reason.trim()) return;
    await reject.mutateAsync({ reason: reason.trim() });
    onClose();
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="reject-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center"
    >
      <div
        className="absolute inset-0 bg-neutral-900 opacity-40"
        onClick={onClose}
        aria-hidden="true"
      />

      <div className="relative bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
        <div className="p-6">
          <h2
            id="reject-modal-title"
            className="text-h2 font-medium text-neutral-900 mb-1"
          >
            Reject Quote
          </h2>
          <p className="text-body text-neutral-600 mb-4">
            This action is final. The quote will be marked as rejected and the
            technician will be notified.
          </p>

          <form onSubmit={(e) => void handleSubmit(e)}>
            <div className="mb-4">
              <label
                htmlFor="reject-reason"
                className="block text-body font-medium text-neutral-900 mb-1"
              >
                Reason for rejection <span className="text-fault-600">*</span>
              </label>
              <textarea
                id="reject-reason"
                ref={textareaRef}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                rows={4}
                placeholder="Explain why this quote is being rejected."
                className="w-full border border-neutral-200 rounded-md px-3 py-2 text-body text-neutral-900 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-brand-600 resize-none"
                required
                aria-required="true"
              />
            </div>

            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={onClose}
                disabled={reject.isPending}
                className="px-4 py-2 text-body font-medium text-neutral-800 border border-neutral-200 rounded-md hover:bg-neutral-100 disabled:opacity-50 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!reason.trim() || reject.isPending}
                className="px-4 py-2 text-body font-medium text-white bg-fault-600 hover:bg-fault-800 rounded-md disabled:opacity-50 transition-colors"
                aria-label="Confirm quote rejection"
                data-testid="reject-submit-btn"
              >
                {reject.isPending ? "Rejecting…" : "Reject Quote"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
