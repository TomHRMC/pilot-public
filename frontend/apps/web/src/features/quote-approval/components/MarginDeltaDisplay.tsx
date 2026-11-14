/**
 * MarginDeltaDisplay — shows current projected margin vs pre-edit margin
 *
 * Location: apps/web/src/features/quote-approval/components/MarginDeltaDisplay.tsx
 */

import React from "react";

interface MarginDeltaDisplayProps {
  /** May be null when cost data is missing from the API response */
  currentMarginPercent: number | null | undefined;
  preEditMarginPercent?: number | null;
  targetMarginPercent?: number;
  testID?: string;
}

export function MarginDeltaDisplay({
  currentMarginPercent,
  preEditMarginPercent,
  targetMarginPercent = 30,
  testID,
}: MarginDeltaDisplayProps) {
  // Guard: render placeholder when margin data is unavailable
  if (currentMarginPercent == null) {
    return (
      <div
        className="flex items-center gap-2"
        data-testid={testID ?? "margin-delta-display"}
        aria-label="Projected margin: unavailable"
      >
        <span className="text-caption text-neutral-400">Margin</span>
        <span className="text-body text-neutral-400">—</span>
      </div>
    );
  }

  const isBelowTarget = currentMarginPercent < targetMarginPercent;
  const hasChanged =
    preEditMarginPercent != null &&
    preEditMarginPercent !== currentMarginPercent;

  const marginColorClass = isBelowTarget ? "text-fault-600" : "text-margin-600";

  return (
    <div
      className="flex items-center gap-2"
      data-testid={testID ?? "margin-delta-display"}
      aria-label={`Projected margin: ${currentMarginPercent.toFixed(1)}%`}
    >
      <span className="text-caption text-neutral-400">Margin</span>

      {hasChanged && preEditMarginPercent != null && (
        <span
          className="text-caption text-neutral-400 line-through"
          aria-label={`Previous margin: ${preEditMarginPercent.toFixed(1)}%`}
        >
          {preEditMarginPercent.toFixed(1)}%
        </span>
      )}

      <span
        className={`text-body font-medium ${marginColorClass}`}
        aria-label={
          isBelowTarget ? "Below target margin" : "At or above target margin"
        }
      >
        {currentMarginPercent.toFixed(1)}%
      </span>

      {isBelowTarget && (
        <span className="text-caption text-fault-600" aria-label="Below target">
          (below {targetMarginPercent}% target)
        </span>
      )}
    </div>
  );
}
