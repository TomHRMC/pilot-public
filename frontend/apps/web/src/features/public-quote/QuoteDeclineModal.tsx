/**
 * QuoteDeclineModal — FE-B14
 *
 * Location: apps/web/src/features/public-quote/QuoteDeclineModal.tsx
 *
 * Decline overlay with required reason radio + optional comment (max 2000 chars).
 *
 * RULE 1: No useAuth() — unauthenticated.
 * RULE 7: Comment goes to /decline endpoint, NOT comms threads.
 */

"use client";

import React, { useState } from "react";
import type { DeclineReason, QuoteActionState } from "./types";
import { DECLINE_REASON_LABELS } from "./types";

const MAX_COMMENT_CHARS = 2000;
const DECLINE_REASONS = Object.keys(DECLINE_REASON_LABELS) as DeclineReason[];

interface QuoteDeclineModalProps {
  tenantName: string;
  onConfirm: (reason: DeclineReason, comment?: string) => Promise<void>;
  onCancel: () => void;
  actionState: QuoteActionState;
}

export function QuoteDeclineModal({
  tenantName,
  onConfirm,
  onCancel,
  actionState,
}: QuoteDeclineModalProps) {
  const [reason, setReason] = useState<DeclineReason | "">("");
  const [comment, setComment] = useState("");
  const [reasonError, setReasonError] = useState(false);
  const isSubmitting = actionState.phase === "submitting";

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!reason) {
      setReasonError(true);
      return;
    }
    setReasonError(false);
    void onConfirm(reason, comment.trim() || undefined);
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4"
      data-testid="quote-decline-modal"
    >
      <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
        <h2 className="text-lg font-semibold text-neutral-900">
          Decline this quote?
        </h2>
        <p className="mt-1 text-sm text-neutral-600">
          Let <strong>{tenantName}</strong> know why you&apos;re declining.
        </p>

        <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-4">
          {/* Reason radio group */}
          <fieldset>
            <legend className="text-sm font-medium text-neutral-700">
              Reason <span className="text-fault-600">*</span>
            </legend>
            <div
              className="mt-2 flex flex-col gap-2"
              role="radiogroup"
              aria-label="Decline reason"
            >
              {DECLINE_REASONS.map((r) => (
                <label
                  key={r}
                  className="flex items-center gap-2.5 cursor-pointer"
                >
                  <input
                    type="radio"
                    name="decline-reason"
                    value={r}
                    checked={reason === r}
                    onChange={() => {
                      setReason(r);
                      setReasonError(false);
                    }}
                    className="h-4 w-4 accent-brand-600"
                    data-testid={`decline-reason-${r}`}
                  />
                  <span className="text-sm text-neutral-700">
                    {DECLINE_REASON_LABELS[r]}
                  </span>
                </label>
              ))}
            </div>
            {reasonError && (
              <p
                className="mt-1 text-xs text-fault-600"
                data-testid="decline-reason-error"
              >
                Please select a reason.
              </p>
            )}
          </fieldset>

          {/* Optional comment */}
          <div>
            <label
              htmlFor="decline-comment"
              className="block text-sm font-medium text-neutral-700"
            >
              Additional comments{" "}
              <span className="font-normal text-neutral-400">(optional)</span>
            </label>
            <textarea
              id="decline-comment"
              data-testid="decline-comment-input"
              value={comment}
              onChange={(e) =>
                setComment(e.target.value.slice(0, MAX_COMMENT_CHARS))
              }
              rows={3}
              placeholder="Any feedback for the contractor..."
              className="mt-1 w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm text-neutral-800 placeholder:text-neutral-400 focus:border-neutral-400 focus:outline-none focus:ring-1 focus:ring-neutral-400"
            />
            <p
              className="mt-1 text-right text-xs text-neutral-400"
              data-testid="decline-comment-counter"
            >
              {comment.length} / {MAX_COMMENT_CHARS}
            </p>
          </div>

          {/* Error state */}
          {actionState.phase === "error" && (
            <p className="text-sm text-fault-600" data-testid="decline-error">
              {actionState.message ?? "Something went wrong. Please try again."}
            </p>
          )}

          <div className="flex gap-3 pt-1">
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
              data-testid="decline-confirm-button"
            >
              {isSubmitting ? "Declining…" : "Decline quote"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
