/**
 * QuoteReviewModeBar — top review-mode affordance bar
 *
 * Location: apps/web/src/features/quote-approval/components/QuoteReviewModeBar.tsx
 *
 * Shown when quote.status === 'pending_approval' AND user has owner role.
 * Shows pending edit count, margin delta, and Cancel-edits button.
 */

"use client";

import React, { useState } from "react";

interface QuoteReviewModeBarProps {
  pendingEditCount: number;
  onCancelAllEdits: () => Promise<void>;
  /** May be null when cost data is missing from the API response */
  currentMarginPercent: number | null | undefined;
  preEditMarginPercent?: number | null;
  testID?: string;
}

export function QuoteReviewModeBar({
  pendingEditCount,
  onCancelAllEdits,
  currentMarginPercent,
  preEditMarginPercent,
  testID,
}: QuoteReviewModeBarProps) {
  const [isCanceling, setIsCanceling] = useState(false);

  async function handleCancel() {
    if (pendingEditCount === 0) return;
    const confirmed = window.confirm(
      `Cancel all ${pendingEditCount} pending edit${pendingEditCount !== 1 ? "s" : ""}? This cannot be undone.`,
    );
    if (!confirmed) return;
    setIsCanceling(true);
    try {
      await onCancelAllEdits();
    } finally {
      setIsCanceling(false);
    }
  }

  const hasChanged =
    preEditMarginPercent != null &&
    currentMarginPercent != null &&
    preEditMarginPercent !== currentMarginPercent;

  return (
    <div
      data-testid={testID ?? "quote-review-mode-bar"}
      className="bg-alert-50 border-b border-alert-400 px-6 py-3 flex items-center justify-between"
      role="status"
      aria-label="Quote review mode"
    >
      <div className="flex items-center gap-4">
        <span className="text-body font-medium text-alert-800">
          Review Mode
        </span>
        <span className="text-body text-alert-800" aria-live="polite">
          {pendingEditCount > 0
            ? `${pendingEditCount} pending edit${pendingEditCount !== 1 ? "s" : ""}`
            : "No pending edits"}
        </span>

        {currentMarginPercent != null && (
          <div className="flex items-center gap-2 text-caption text-neutral-600">
            <span>Margin:</span>
            {hasChanged && preEditMarginPercent != null && (
              <span className="line-through text-neutral-400">
                {preEditMarginPercent.toFixed(1)}%
              </span>
            )}
            <span className="text-neutral-900 font-medium">
              {currentMarginPercent.toFixed(1)}%
            </span>
          </div>
        )}
      </div>

      {pendingEditCount > 0 && (
        <button
          type="button"
          onClick={() => void handleCancel()}
          disabled={isCanceling}
          className="text-body text-fault-600 hover:text-fault-800 underline disabled:opacity-50"
          aria-label={`Cancel all ${pendingEditCount} pending edits`}
        >
          {isCanceling ? "Canceling..." : "Cancel all edits"}
        </button>
      )}
    </div>
  );
}
