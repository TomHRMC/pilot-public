/**
 * ConflictPreviewPane — Side panel shown before confirming a job move
 *
 * Location: apps/web/src/features/dispatch-board/components/ConflictPreviewPane.tsx
 *
 * Shows conflicts from check-conflicts endpoint before confirming a move.
 * Four-class severity visual treatment per §G.6.
 * No hard blocks in MVP — all are warn-only per §13.4.
 * "info" conflicts show no blocking affordance.
 *
 * Per batch-fe-b4-design.md §A.2.3 §G.6
 */

"use client";

import React from "react";
import { XMarkIcon } from "@heroicons/react/24/outline";
import type { CheckConflictsResponse } from "../types-stub";
import { ConflictItem } from "./ConflictItem";

interface ConflictPreviewPaneProps {
  /** Conflicts from check-conflicts endpoint */
  conflicts: CheckConflictsResponse | null;
  isLoading?: boolean;
  /** Called when dispatcher confirms the move despite conflicts */
  onProceed: () => void;
  /** Called when dispatcher cancels the move */
  onCancel: () => void;
  /** Whether a move mutation is currently in flight */
  isPending?: boolean;
}

/**
 * ConflictPreviewPane
 *
 * Right-side panel (not modal) so dispatcher can see both grid and conflicts.
 * Matches the "inline panel" pattern from profitability spec §7.
 */
export function ConflictPreviewPane({
  conflicts,
  isLoading,
  onProceed,
  onCancel,
  isPending = false,
}: ConflictPreviewPaneProps) {
  const hasConflicts = (conflicts?.conflicts.length ?? 0) > 0;
  const hasBlockingConflicts = conflicts?.has_blocking_conflicts ?? false;
  const warnConflicts =
    conflicts?.conflicts.filter((c) => c.conflict_class !== "info") ?? [];
  const infoConflicts =
    conflicts?.conflicts.filter((c) => c.conflict_class === "info") ?? [];

  return (
    <div
      className="w-80 flex-shrink-0 flex flex-col h-full border-l border-neutral-200 bg-white shadow-lg"
      role="region"
      aria-label="Conflict preview"
      aria-live="polite"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-200">
        <h2 className="text-h2 font-medium text-neutral-900">Conflict Check</h2>
        <button
          type="button"
          onClick={onCancel}
          className="text-neutral-400 hover:text-neutral-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 rounded-sm"
          aria-label="Close conflict preview"
        >
          <XMarkIcon className="w-4 h-4" aria-hidden="true" />
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="text-body text-neutral-400">
              Checking conflicts…
            </div>
          </div>
        ) : !hasConflicts ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <div className="w-8 h-8 rounded-full bg-margin-50 flex items-center justify-center mb-3">
              <svg
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="currentColor"
                className="text-margin-600"
                aria-hidden="true"
              >
                <path
                  fillRule="evenodd"
                  d="M13.485 3.515a.75.75 0 010 1.06l-7 7a.75.75 0 01-1.06 0l-3.5-3.5a.75.75 0 011.06-1.06L6 9.985l6.425-6.47a.75.75 0 011.06 0z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <p className="text-body font-medium text-neutral-900">
              No conflicts
            </p>
            <p className="text-caption text-neutral-400 mt-1">
              This move looks good — no scheduling issues detected.
            </p>
          </div>
        ) : (
          <>
            {/* Warning conflicts */}
            {warnConflicts.length > 0 && (
              <div
                role="list"
                aria-label="Scheduling conflicts"
                className="space-y-2"
              >
                {warnConflicts.map((conflict, i) => (
                  <ConflictItem
                    key={`${conflict.conflict_class}-${i}`}
                    conflict={conflict}
                  />
                ))}
              </div>
            )}

            {/* Info conflicts */}
            {infoConflicts.length > 0 && (
              <div
                role="list"
                aria-label="Scheduling notes"
                className="space-y-2"
              >
                {infoConflicts.map((conflict, i) => (
                  <ConflictItem key={`info-${i}`} conflict={conflict} />
                ))}
              </div>
            )}
          </>
        )}
      </div>

      {/* Footer actions */}
      <div className="px-4 py-3 border-t border-neutral-200 flex items-center justify-end gap-3">
        <button
          type="button"
          onClick={onCancel}
          disabled={isPending}
          className="px-4 py-2 rounded-md text-body font-medium text-neutral-600 bg-neutral-100 hover:bg-neutral-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-1 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Cancel
        </button>
        <button
          type="button"
          onClick={onProceed}
          disabled={isPending || hasBlockingConflicts}
          className={[
            "px-4 py-2 rounded-md text-body font-medium text-white",
            "focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-1 disabled:opacity-50 disabled:cursor-not-allowed",
            hasConflicts && warnConflicts.length > 0
              ? "bg-fault-600 hover:bg-fault-800 focus-visible:ring-fault-600"
              : "bg-brand-600 hover:bg-brand-800 focus-visible:ring-brand-600",
          ].join(" ")}
        >
          {isPending
            ? "Moving…"
            : hasConflicts && warnConflicts.length > 0
              ? "Move anyway (not recommended)"
              : "Confirm move"}
        </button>
      </div>
    </div>
  );
}
