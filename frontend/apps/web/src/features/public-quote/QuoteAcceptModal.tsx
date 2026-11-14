/**
 * QuoteAcceptModal — FE-B14
 *
 * Location: apps/web/src/features/public-quote/QuoteAcceptModal.tsx
 *
 * Accept confirmation overlay with optional comment (max 2000 chars).
 * Comment is optional for accept (unlike payment variance where it's required).
 *
 * Token requirements:
 *  - Submit button: bg-brand-600 hover:bg-brand-800 text-white
 *  - Comment validation error: text-fault-600
 *
 * RULE 1: No useAuth() — unauthenticated.
 * RULE 7: Comment POST goes to /accept endpoint, NOT to comms threads.
 */

"use client";

import React, { useState } from "react";
import type { QuoteActionState } from "./types";

const MAX_COMMENT_CHARS = 2000;

interface QuoteAcceptModalProps {
  tenantName: string;
  onConfirm: (comment?: string) => Promise<void>;
  onCancel: () => void;
  actionState: QuoteActionState;
}

export function QuoteAcceptModal({
  tenantName,
  onConfirm,
  onCancel,
  actionState,
}: QuoteAcceptModalProps) {
  const [comment, setComment] = useState("");
  const isSubmitting = actionState.phase === "submitting";

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    void onConfirm(comment.trim() || undefined);
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
      data-testid="quote-accept-modal"
    >
      <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
        <h2 className="text-lg font-semibold text-neutral-900">
          Accept this quote?
        </h2>
        <p className="mt-1 text-sm text-neutral-600">
          You&apos;re accepting the quote from <strong>{tenantName}</strong>.
          They&apos;ll be notified and will reach out to schedule the work.
        </p>

        <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-3">
          {/* Optional comment textarea */}
          <div>
            <label
              htmlFor="accept-comment"
              className="block text-sm font-medium text-neutral-700"
            >
              Add a note{" "}
              <span className="font-normal text-neutral-400">(optional)</span>
            </label>
            <textarea
              id="accept-comment"
              data-testid="accept-comment-input"
              value={comment}
              onChange={(e) =>
                setComment(e.target.value.slice(0, MAX_COMMENT_CHARS))
              }
              rows={3}
              placeholder="Any questions or details for the contractor..."
              className="mt-1 w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm text-neutral-800 placeholder:text-neutral-400 focus:border-neutral-400 focus:outline-none focus:ring-1 focus:ring-neutral-400"
            />
            <p
              className="mt-1 text-right text-xs text-neutral-400"
              data-testid="accept-comment-counter"
            >
              {comment.length} / {MAX_COMMENT_CHARS}
            </p>
          </div>

          {/* Error state */}
          {actionState.phase === "error" && (
            <p className="text-sm text-fault-600" data-testid="accept-error">
              {actionState.message ?? "Something went wrong. Please try again."}
            </p>
          )}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onCancel}
              disabled={isSubmitting}
              className="flex-1 rounded-lg border border-neutral-300 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-brand-800 disabled:opacity-50"
              data-testid="accept-confirm-button"
            >
              {isSubmitting ? "Accepting…" : "Accept quote"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
