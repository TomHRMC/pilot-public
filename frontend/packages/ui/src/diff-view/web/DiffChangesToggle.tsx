/**
 * DiffChangesToggle — "Show / Hide changes" toggle (web)
 *
 * Location: packages/ui/src/diff-view/web/DiffChangesToggle.tsx
 * Internal component — not exported from barrel.
 */

import React from "react";

interface DiffChangesToggleProps {
  showChanges: boolean;
  onToggle: () => void;
  changesCount: number;
}

export function DiffChangesToggle({
  showChanges,
  onToggle,
  changesCount,
}: DiffChangesToggleProps) {
  return (
    <button
      type="button"
      className="flex items-center gap-1.5 text-body text-brand-600 hover:text-brand-800 font-medium mb-3"
      onClick={onToggle}
      aria-expanded={showChanges}
      aria-controls="diff-view-content"
    >
      <span aria-hidden="true">{showChanges ? "▾" : "▸"}</span>
      {showChanges ? "Hide changes" : `Show changes (${changesCount})`}
    </button>
  );
}
