"use client";

/**
 * CloseCohortButton — cohort close action with confirmation modal
 *
 * Location: apps/web/src/components/operator/cohort/CloseCohortButton.tsx
 *
 * C-B11 Part B: Destructive confirm pattern (§7 of design-system-reference).
 * Button in the header area (only visible when cohort_is_active === true).
 * Click opens a confirmation modal. Cancel is the default safe action.
 *
 * RULE 5: zero hex codes. RULE 11: no hand-memo.
 * RULE 15: WCAG 2.2 AA — focus trap, target size ≥24px, Escape to close.
 */

import React, { useEffect, useRef, useState } from "react";
import {
  LockClosedIcon,
  XMarkIcon,
  ExclamationTriangleIcon,
} from "@heroicons/react/24/outline";
import { useCloseCohort } from "@/features/operator/hooks/useCloseCohort";
import { useNotificationQueue } from "@pilot/ui/notification-banner";
import { isAxiosError } from "@pilot/shared-api";

interface CloseCohortButtonProps {
  cohortIsActive: boolean;
  memberCount: number;
}

export function CloseCohortButton({
  cohortIsActive,
  memberCount,
}: CloseCohortButtonProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const closeMutation = useCloseCohort();
  const { addNotification } = useNotificationQueue();
  const modalRef = useRef<HTMLDivElement>(null);
  const cancelButtonRef = useRef<HTMLButtonElement>(null);

  // Focus management: focus the Cancel button on open
  useEffect(() => {
    if (isModalOpen) {
      cancelButtonRef.current?.focus();
    }
  }, [isModalOpen]);

  // Escape to close + focus trap
  useEffect(() => {
    if (!isModalOpen) return;
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setIsModalOpen(false);
      }
      if (e.key === "Tab" && modalRef.current) {
        const focusable = modalRef.current.querySelectorAll(
          'button, [href], input, [tabindex]:not([tabindex="-1"])',
        );
        if (focusable.length === 0) return;
        const first = focusable[0] as HTMLElement;
        const last = focusable[focusable.length - 1] as HTMLElement;
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isModalOpen]);

  function openModal() {
    setIsModalOpen(true);
  }

  function closeModal() {
    setIsModalOpen(false);
  }

  function handleConfirm() {
    closeMutation.mutate(undefined, {
      onSuccess: () => {
        addNotification({
          id: `cohort-closed-${Date.now()}`,
          severity: "success",
          title: `Charter cohort closed. ${memberCount} members retain their locked rate.`,
          dismissAfterMs: 6000,
        });
        closeModal();
      },
      onError: (err) => {
        const isAlreadyClosed =
          isAxiosError(err) && err.response?.status === 409;
        if (isAlreadyClosed) {
          addNotification({
            id: `cohort-already-closed-${Date.now()}`,
            severity: "warning",
            title: "The cohort was already closed.",
            dismissAfterMs: 6000,
          });
        } else {
          addNotification({
            id: `cohort-close-failed-${Date.now()}`,
            severity: "error",
            title: "Failed to close cohort. Please try again.",
            dismissAfterMs: 12000,
          });
        }
        closeModal();
      },
    });
  }

  // If cohort is already closed, show static badge
  if (!cohortIsActive) {
    return (
      <span className="inline-flex items-center gap-1.5 bg-neutral-100 text-neutral-500 rounded-md px-3 py-2 text-sm font-medium">
        <LockClosedIcon className="w-4 h-4" />
        Cohort closed
      </span>
    );
  }

  return (
    <>
      <button
        type="button"
        onClick={openModal}
        disabled={closeMutation.isPending}
        className="inline-flex items-center gap-2 bg-fault-600 text-white rounded-md px-4 py-2.5 text-sm font-medium hover:bg-fault-700 focus-visible:ring-2 focus-visible:ring-fault-500 disabled:bg-neutral-300 disabled:cursor-not-allowed"
        aria-label="Close Charter cohort"
      >
        <LockClosedIcon className="w-4 h-4" />
        Close Cohort
      </button>

      {isModalOpen && (
        <div
          className="fixed inset-0 bg-neutral-900/50 z-50 flex items-start justify-center"
          onClick={closeModal}
          role="dialog"
          aria-modal="true"
          aria-label="Close Charter cohort confirmation"
        >
          <div
            ref={modalRef}
            className="bg-white rounded-lg shadow-xl max-w-md w-full mx-auto mt-16 p-6"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-h2 font-semibold text-neutral-900">
                Close Charter cohort?
              </h2>
              <button
                type="button"
                onClick={closeModal}
                className="text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 rounded-md p-2.5 focus-visible:ring-2 focus-visible:ring-brand-500"
                aria-label="Close modal"
              >
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>

            {/* Body */}
            <p className="text-sm text-neutral-700 mt-2">
              This will archive the Charter price and close the cohort to new
              signups. Existing members keep their locked rate.
            </p>

            {/* Warning */}
            <p className="text-sm text-fault-600 font-medium mt-2 flex items-center gap-1.5">
              <ExclamationTriangleIcon className="w-4 h-4" />
              This cannot be undone.
            </p>

            {/* Action buttons */}
            <div className="flex justify-end gap-3 mt-6">
              <button
                type="button"
                ref={cancelButtonRef}
                onClick={closeModal}
                className="border border-neutral-300 text-neutral-700 rounded-md px-4 py-2 text-sm font-medium hover:bg-neutral-50 focus-visible:ring-2 focus-visible:ring-brand-500"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirm}
                disabled={closeMutation.isPending}
                className="bg-fault-600 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-fault-700 focus-visible:ring-2 focus-visible:ring-fault-500 disabled:bg-neutral-300 disabled:cursor-not-allowed"
              >
                {closeMutation.isPending ? "Closing…" : "Close Cohort"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
