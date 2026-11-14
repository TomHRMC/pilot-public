/**
 * KickbackCommentModal — modal for kickback action
 *
 * Location: apps/web/src/features/quote-approval/components/KickbackCommentModal.tsx
 *
 * Contains overall comment textarea (required if no line comments) +
 * per-line-item comment thread (optional).
 * Calls POST /api/v1/quotes/{id}/kickback
 * All comments are tech-visible (no audience selector per §G.6).
 */

"use client";

import React, { useEffect, useRef, useState } from "react";
import { useQuoteKickback } from "../hooks/useQuoteApprove";
import type { QuoteLineItem } from "../hooks/useQuoteDetail";

interface KickbackCommentModalProps {
  quoteId: string;
  lineItems: QuoteLineItem[];
  onClose: () => void;
}

export function KickbackCommentModal({
  quoteId,
  lineItems,
  onClose,
}: KickbackCommentModalProps) {
  const [overallComment, setOverallComment] = useState("");
  const [lineComments, setLineComments] = useState<Record<string, string>>({});
  const kickback = useQuoteKickback(quoteId);
  const firstInputRef = useRef<HTMLTextAreaElement>(null);

  // Trap focus on mount
  useEffect(() => {
    firstInputRef.current?.focus();
  }, []);

  // Close on Escape
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  const hasAtLeastOneComment =
    overallComment.trim().length > 0 ||
    Object.values(lineComments).some((c) => c.trim().length > 0);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!hasAtLeastOneComment) return;

    const lineCommentsArray = Object.entries(lineComments)
      .filter(([, comment]) => comment.trim().length > 0)
      .map(([line_item_id, comment]) => ({ line_item_id, comment }));

    await kickback.mutateAsync({
      overall_comment: overallComment.trim() || undefined,
      line_comments:
        lineCommentsArray.length > 0 ? lineCommentsArray : undefined,
    });
    onClose();
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="kickback-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-neutral-900 opacity-40"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal */}
      <div className="relative bg-white rounded-lg shadow-xl w-full max-w-lg mx-4 max-h-screen overflow-y-auto">
        <div className="p-6">
          <h2
            id="kickback-modal-title"
            className="text-h2 font-medium text-neutral-900 mb-1"
          >
            Kick Back to Tech
          </h2>
          <p className="text-body text-neutral-600 mb-4">
            Add a comment explaining what needs to change. The technician will
            see your feedback.
          </p>

          <form onSubmit={(e) => void handleSubmit(e)}>
            {/* Overall comment */}
            <div className="mb-4">
              <label
                htmlFor="overall-comment"
                className="block text-body font-medium text-neutral-900 mb-1"
              >
                Overall comment
              </label>
              <textarea
                id="overall-comment"
                ref={firstInputRef}
                value={overallComment}
                onChange={(e) => setOverallComment(e.target.value)}
                rows={4}
                placeholder="What needs to change? Be specific so the tech can address it quickly."
                className="w-full border border-neutral-200 rounded-md px-3 py-2 text-body text-neutral-900 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-brand-600 resize-none"
                aria-required="false"
                aria-describedby="kickback-comment-hint"
              />
              <p
                id="kickback-comment-hint"
                className="text-caption text-neutral-400 mt-1"
              >
                Required if no line-item comments are provided.
              </p>
            </div>

            {/* Per-line comments (optional) */}
            {lineItems.filter((li) => li.customer_visible).length > 0 && (
              <details className="mb-4">
                <summary className="text-body font-medium text-neutral-900 cursor-pointer hover:text-brand-600">
                  Add line-item comments (optional)
                </summary>
                <div className="mt-3 space-y-3">
                  {lineItems
                    .filter((li) => li.customer_visible)
                    .map((li) => (
                      <div key={li.id}>
                        <label
                          htmlFor={`line-comment-${li.id}`}
                          className="block text-body text-neutral-600 mb-1 truncate"
                        >
                          {li.description}
                        </label>
                        <input
                          id={`line-comment-${li.id}`}
                          type="text"
                          value={lineComments[li.id] ?? ""}
                          onChange={(e) =>
                            setLineComments((prev) => ({
                              ...prev,
                              [li.id]: e.target.value,
                            }))
                          }
                          placeholder="Comment on this line item..."
                          className="w-full border border-neutral-200 rounded-md px-3 py-1.5 text-body text-neutral-900 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-brand-600"
                        />
                      </div>
                    ))}
                </div>
              </details>
            )}

            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={onClose}
                disabled={kickback.isPending}
                className="px-4 py-2 text-body font-medium text-neutral-800 border border-neutral-200 rounded-md hover:bg-neutral-100 disabled:opacity-50 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!hasAtLeastOneComment || kickback.isPending}
                className="px-4 py-2 text-body font-medium text-white bg-alert-600 hover:bg-alert-800 rounded-md disabled:opacity-50 transition-colors"
                aria-label="Submit kickback with comment"
                data-testid="kickback-submit-btn"
              >
                {kickback.isPending ? "Sending…" : "Kick Back"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
