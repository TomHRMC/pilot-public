/**
 * CreateCustomerModal — modal to create a new customer
 *
 * Location: apps/web/src/features/customers/components/CreateCustomerModal.tsx
 *
 * Follows the modal pattern established in KickbackCommentModal:
 * fixed backdrop + role="dialog" + Escape key closes.
 */

"use client";

import { useEffect, useRef, useState } from "react";
import { getApiProblem } from "@pilot/shared-api";
import { useCreateCustomer } from "../hooks/useCreateCustomer";
import { CustomerForm } from "./CustomerForm";
import type { CustomerFormValues } from "./CustomerForm";

interface CreateCustomerModalProps {
  open: boolean;
  onClose: () => void;
}

export function CreateCustomerModal({
  open,
  onClose,
}: CreateCustomerModalProps) {
  const { mutate, isPending, reset } = useCreateCustomer();
  const firstFocusRef = useRef<HTMLDivElement>(null);
  const [apiError, setApiError] = useState<string | null>(null);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  // Focus trap on open
  useEffect(() => {
    if (open) {
      setTimeout(() => firstFocusRef.current?.focus(), 50);
    } else {
      reset();
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setApiError(null);
    }
  }, [open, reset]);

  if (!open) return null;

  function handleSubmit(values: CustomerFormValues) {
    setApiError(null);
    mutate(values, {
      onSuccess: () => {
        onClose();
      },
      onError: (err) => {
        const problem = getApiProblem(err);
        setApiError(
          problem.detail ?? "Failed to create customer. Please try again.",
        );
      },
    });
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="create-customer-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-neutral-900 opacity-40"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal panel */}
      <div
        ref={firstFocusRef}
        tabIndex={-1}
        className="relative bg-white rounded-lg shadow-xl w-full max-w-lg mx-4 max-h-screen overflow-y-auto focus:outline-none"
      >
        <div className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2
              id="create-customer-modal-title"
              className="text-lg font-semibold text-neutral-900"
            >
              Add Customer
            </h2>
            <button
              type="button"
              onClick={onClose}
              className="text-neutral-400 hover:text-neutral-600 transition-colors"
              aria-label="Close modal"
            >
              <svg
                className="w-5 h-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>

          {apiError && (
            <div
              role="alert"
              data-testid="create-customer-api-error"
              className="mb-4 rounded-md border border-fault-200 bg-fault-50 px-4 py-3 text-sm text-fault-700"
            >
              {apiError}
            </div>
          )}

          <CustomerForm
            onSubmit={handleSubmit}
            onCancel={onClose}
            isSubmitting={isPending}
            submitLabel="Add Customer"
          />
        </div>
      </div>
    </div>
  );
}
