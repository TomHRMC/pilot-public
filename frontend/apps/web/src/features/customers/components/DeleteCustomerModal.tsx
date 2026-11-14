/**
 * DeleteCustomerModal — confirm-as-turn pattern for customer deletion
 *
 * Location: apps/web/src/features/customers/components/DeleteCustomerModal.tsx
 *
 * FE-B24: Opened from CustomerOverviewTab with RoleGate permission="customers.delete".
 *
 * Confirm-as-turn: shows confirmation text before DELETE fires.
 * - Cancel button: closes modal
 * - Delete button: calls DELETE /api/v1/customers/{customerId} via useDeleteCustomer
 * - On success: calls onSuccess() (caller navigates to /customers)
 *
 * Pattern: direct render (no inner remount needed — form is just 2 buttons).
 */

"use client";

import { useEffect } from "react";
import { useDeleteCustomer } from "../hooks/useDeleteCustomer";
import { RoleGate } from "@pilot/ui/role-gate";

interface DeleteCustomerModalProps {
  customerId: string;
  customerName: string;
  open: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export function DeleteCustomerModal({
  customerId,
  customerName,
  open,
  onClose,
  onSuccess,
}: DeleteCustomerModalProps) {
  const { mutate: deleteCustomer, isPending, reset } = useDeleteCustomer();

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  // Reset mutation state on close
  useEffect(() => {
    if (!open) {
      reset();
    }
  }, [open, reset]);

  if (!open) return null;

  function handleDelete() {
    deleteCustomer(customerId, {
      onSuccess: () => {
        onSuccess?.();
        onClose();
      },
    });
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-customer-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-neutral-900 opacity-40"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal panel */}
      <div className="relative bg-white rounded-lg shadow-xl w-full max-w-md mx-4 p-6">
        <h2
          id="delete-customer-modal-title"
          className="text-lg font-semibold text-neutral-900 mb-2"
        >
          Delete Customer
        </h2>

        <p className="text-sm text-neutral-600 mb-6">
          Delete <strong>{customerName}</strong>? This action cannot be undone.
        </p>

        <div className="flex gap-3 justify-end">
          <button
            type="button"
            onClick={onClose}
            disabled={isPending}
            className="px-4 py-2 text-sm font-medium text-neutral-700 border border-neutral-200 rounded-md hover:bg-neutral-50 disabled:opacity-50"
          >
            Cancel
          </button>

          <RoleGate permission="customers.delete">
            <button
              type="button"
              onClick={handleDelete}
              disabled={isPending}
              className="px-4 py-2 text-sm font-medium text-white bg-fault-600 rounded-md hover:bg-fault-700 disabled:opacity-50"
              data-testid="confirm-delete-customer-btn"
            >
              {isPending ? "Deleting…" : "Delete Customer"}
            </button>
          </RoleGate>
        </div>
      </div>
    </div>
  );
}
