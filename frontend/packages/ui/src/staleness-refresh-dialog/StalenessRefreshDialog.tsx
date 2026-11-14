/**
 * StalenessRefreshDialog — 409 Conflict Dialog
 *
 * Location: packages/ui/src/staleness-refresh-dialog/StalenessRefreshDialog.tsx
 * Exported from: packages/ui/src/index.ts
 *
 * Established in FE-B4. Consumed transparently via useStalenessRetry() —
 * downstream batches never render this directly.
 *
 * Visual spec (FE-B4 dispatch context — no DiffView yet):
 * ┌──────────────────────────────────────────────────────────┐
 * │  ⚠️  Schedule changed while you were working              │
 * │                                                           │
 * │  The job was moved since you loaded the board.            │
 * │  Current assignment:                                      │
 * │  • Tech: Mike Chen                                        │
 * │  • Time: Tue Jun 10, 9:00 AM – 11:00 AM                  │
 * │                                                           │
 * │  Would you like to retry your move with the latest info?  │
 * │                                                           │
 * │  [Cancel]                    [Retry with updated data]    │
 * └──────────────────────────────────────────────────────────┘
 *
 * Uses shadcn/ui Dialog. Traps focus per WAI-ARIA dialog pattern.
 */

"use client";

import React, { useEffect, useRef } from "react";
import type { StalenessRefreshDialogProps } from "./types";

/**
 * StalenessRefreshDialog
 *
 * Shown when a mutation receives a 409 Conflict (staleness check failure).
 * Focus is trapped inside the dialog per WAI-ARIA 1.2 dialog pattern.
 *
 * @example
 * // Rendered automatically by useStalenessRetry() via StalenessDialog component
 * <StalenessRefreshDialog
 *   isOpen={isStalenessDialogOpen}
 *   onRetry={handleRetry}
 *   onCancel={handleCancel}
 * >
 *   <p>Current slot: Mike Chen at 9:00 AM</p>
 * </StalenessRefreshDialog>
 */
export function StalenessRefreshDialog({
  isOpen,
  onRetry,
  onCancel,
  title = "This record was updated while you were working",
  children,
  isRetrying = false,
}: StalenessRefreshDialogProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const cancelButtonRef = useRef<HTMLButtonElement>(null);

  // Focus cancel button on open (safe default per WAI-ARIA)
  useEffect(() => {
    if (isOpen) {
      // Defer to next tick to allow DOM to render
      const timer = setTimeout(() => {
        cancelButtonRef.current?.focus();
      }, 0);
      return () => clearTimeout(timer);
    }
  }, [isOpen]);

  // Focus trap
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onCancel();
        return;
      }

      if (e.key !== "Tab") return;
      const dialog = dialogRef.current;
      if (!dialog) return;

      const focusable = Array.from(
        dialog.querySelectorAll<HTMLElement>(
          'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ),
      );

      if (focusable.length === 0) return;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onCancel]);

  if (!isOpen) return null;

  return (
    /* Backdrop */
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      aria-modal="true"
      role="dialog"
      aria-labelledby="staleness-dialog-title"
      aria-describedby="staleness-dialog-desc"
    >
      {/* Overlay */}
      <div
        className="absolute inset-0 bg-neutral-900/50"
        onClick={onCancel}
        aria-hidden="true"
      />

      {/* Dialog panel */}
      <div
        ref={dialogRef}
        className="relative z-10 w-full max-w-md rounded-lg bg-white shadow-lg p-6 mx-4"
      >
        {/* Header */}
        <div className="flex items-start gap-3 mb-4">
          {/* Warning icon using token color */}
          <span
            className="flex-shrink-0 text-alert-400 mt-0.5"
            aria-hidden="true"
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 20 20"
              fill="currentColor"
              aria-hidden="true"
            >
              <path
                fillRule="evenodd"
                d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z"
                clipRule="evenodd"
              />
            </svg>
          </span>
          <h2
            id="staleness-dialog-title"
            className="text-h2 font-medium text-neutral-900"
          >
            {title}
          </h2>
        </div>

        {/* Body */}
        <div id="staleness-dialog-desc" className="mb-6">
          {children ?? (
            <p className="text-body text-neutral-600">
              Someone else updated this record after you loaded the page. Would
              you like to retry your action using the latest data?
            </p>
          )}
        </div>

        {/* Action buttons */}
        <div className="flex items-center justify-end gap-3">
          <button
            ref={cancelButtonRef}
            type="button"
            onClick={onCancel}
            disabled={isRetrying}
            className="px-4 py-2 rounded-md text-body font-medium text-neutral-600 bg-neutral-100 hover:bg-neutral-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-1 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onRetry}
            disabled={isRetrying}
            className="px-4 py-2 rounded-md text-body font-medium text-white bg-brand-600 hover:bg-brand-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-1 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isRetrying ? "Retrying…" : "Retry with updated data"}
          </button>
        </div>
      </div>
    </div>
  );
}
