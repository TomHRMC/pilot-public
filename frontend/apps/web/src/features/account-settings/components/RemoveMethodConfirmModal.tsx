/**
 * RemoveMethodConfirmModal — MFA-WIRE-1 Part B (spec §2.5, §10.4)
 *
 * Location: apps/web/src/features/account-settings/components/RemoveMethodConfirmModal.tsx
 *
 * Surface-scoped destructive confirm modal per design-system §7 pattern.
 *
 * Accessibility (spec §10.4 — WCAG 2.2 AA):
 *   - Focus moves to "Keep method" (safe default) on open
 *   - Tab/Shift+Tab cycle within the modal (lightweight focus trap —
 *     `react-focus-lock` is NOT a dependency, so a useEffect Tab handler
 *     is used per spec §10.4 allowance)
 *   - Escape = cancel (Keep method)
 *   - Focus returns to the Remove button that opened the modal on close
 *   - role="dialog" + aria-modal="true" + aria-labelledby
 *
 * NOT exported from packages/ui — surface-scoped by design (§I).
 */
"use client";

import React, { useEffect, useRef, useCallback } from "react";
import {
  ExclamationTriangleIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";

export interface RemoveMethodConfirmModalProps {
  open: boolean;
  methodLabel: string;
  /** ID of the Remove button that opened the modal — focus returns here on close. */
  triggerButtonId: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export function RemoveMethodConfirmModal({
  open,
  methodLabel,
  triggerButtonId,
  onConfirm,
  onCancel,
}: RemoveMethodConfirmModalProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const cancelBtnRef = useRef<HTMLButtonElement>(null);

  // On open: move focus to the "Keep method" (cancel) button — safe default.
  // On close: return focus to the Remove button that opened the modal.
  useEffect(() => {
    if (open) {
      // Move focus into the modal on the next tick (after render)
      const timer = setTimeout(() => {
        cancelBtnRef.current?.focus();
      }, 0);
      return () => clearTimeout(timer);
    }
    // When closing (open flips to false), return focus to the trigger
    if (!open) {
      const trigger = document.getElementById(triggerButtonId);
      trigger?.focus();
    }
  }, [open, triggerButtonId]);

  // Lightweight focus trap: Tab/Shift+Tab cycles within the modal.
  // Queries all focusable elements inside the panel and wraps focus.
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!open) return;
      if (e.key === "Escape") {
        e.preventDefault();
        onCancel();
        return;
      }
      if (e.key !== "Tab") return;

      const panel = panelRef.current;
      if (!panel) return;

      const focusable = panel.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
      );
      if (focusable.length === 0) return;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault();
          last.focus();
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    },
    [open, onCancel],
  );

  // Attach/detach the keydown listener on the document while open.
  useEffect(() => {
    if (!open) return;
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, handleKeyDown]);

  if (!open) return null;

  const titleId = "mfa-remove-modal-title";

  return (
    <div
      className="fixed inset-0 bg-neutral-900/50 z-50 flex items-start justify-center transition-opacity duration-150 ease-in-out motion-reduce:transition-none"
      data-testid="mfa-remove-modal-overlay"
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        data-testid="mfa-remove-modal"
        className="bg-white rounded-lg shadow-xl max-w-md w-full mx-auto mt-16 p-6 transition-transform duration-150 ease-out motion-reduce:transition-none"
      >
        {/* Close button — top-right, 44×44px hit area */}
        <div className="flex justify-end -mr-2 -mt-2">
          <button
            type="button"
            onClick={onCancel}
            aria-label="Close"
            className="p-2 rounded-md text-neutral-400 hover:text-neutral-600 active:text-neutral-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
          >
            <XMarkIcon className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>

        {/* Icon + title + body */}
        <div className="flex items-start gap-3">
          <ExclamationTriangleIcon
            className="w-6 h-6 flex-shrink-0 text-fault-600"
            aria-hidden="true"
          />
          <div className="flex flex-col gap-2">
            <h2 id={titleId} className="text-h3 font-semibold text-neutral-900">
              Remove {methodLabel}?
            </h2>
            <p className="text-sm text-neutral-600">
              You{"'"}ll no longer be able to sign in with {methodLabel}. If
              this is your only method, you may be locked out of your account.
            </p>
          </div>
        </div>

        {/* Button row */}
        <div className="mt-6 flex items-center justify-end gap-3">
          <button
            ref={cancelBtnRef}
            type="button"
            onClick={onCancel}
            data-testid="mfa-remove-modal-cancel"
            className="border border-neutral-300 text-neutral-700 bg-white rounded-md px-4 py-2 text-sm font-medium hover:bg-neutral-50 active:bg-neutral-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 transition-colors duration-150 ease-in-out motion-reduce:transition-none"
          >
            Keep method
          </button>
          <button
            type="button"
            onClick={onConfirm}
            data-testid="mfa-remove-modal-confirm"
            className="bg-fault-600 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-fault-700 active:bg-fault-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-fault-500 focus-visible:ring-offset-2 transition-colors duration-150 ease-in-out motion-reduce:transition-none"
          >
            Remove method
          </button>
        </div>
      </div>
    </div>
  );
}
