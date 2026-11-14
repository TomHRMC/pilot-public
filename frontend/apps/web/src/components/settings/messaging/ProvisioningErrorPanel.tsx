"use client";

/**
 * ProvisioningErrorPanel — C-B9
 *
 * Location: apps/web/src/components/settings/messaging/ProvisioningErrorPanel.tsx
 *
 * Error/retry panel for failed states. Three variants:
 * - payment_failed (retryable)
 * - rejected (terminal — contact support)
 * - suspended (terminal — contact support)
 *
 * UI spec §4.8. No refund text — Telnyx does not refund Pilot.
 * RULE 5: zero hex codes. RULE 11: no hand-memo.
 */

import React from "react";
import { ExclamationTriangleIcon } from "@heroicons/react/24/outline";
import { useRetryProvisioning } from "@/features/messaging/hooks/useRetryProvisioning";
import { useNotificationQueue } from "@pilot/ui";
import type { ErrorPanelVariant } from "@/features/messaging/types";

export interface ProvisioningErrorPanelProps {
  variant: ErrorPanelVariant;
  failureReason: string | null;
  onRetry?: () => void;
}

const TITLES: Record<ErrorPanelVariant, string> = {
  payment_failed: "Payment Failed",
  rejected: "Registration Rejected",
  suspended: "Messaging Suspended",
};

export function ProvisioningErrorPanel({
  variant,
  failureReason,
  onRetry,
}: ProvisioningErrorPanelProps) {
  const retryProvisioning = useRetryProvisioning();
  const { addNotification } = useNotificationQueue();

  async function handleRetry() {
    try {
      await retryProvisioning.mutateAsync();
      onRetry?.();
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response
        ?.status;
      if (status === 409) {
        addNotification({
          id: `retry-409-${Date.now()}`,
          severity: "error",
          title: "Cannot retry from current state. Refresh the page.",
        });
      } else {
        addNotification({
          id: `retry-err-${Date.now()}`,
          severity: "error",
          title: "Could not retry. Please try again.",
        });
      }
    }
  }

  const isPending = retryProvisioning.isPending;

  return (
    <div
      className="bg-white rounded-lg border border-fault-200 p-6 space-y-4"
      role="alert"
      data-testid="provisioning-error-panel"
    >
      <div className="flex items-center gap-2">
        <ExclamationTriangleIcon className="w-6 h-6 text-fault-600" />
        <h2 className="text-h2 font-semibold text-fault-600">
          {TITLES[variant]}
        </h2>
      </div>

      {variant === "payment_failed" && (
        <>
          <p className="text-sm text-neutral-900">
            Your payment could not be processed.
            {failureReason && ` ${failureReason}`}
          </p>
          <p className="text-sm text-neutral-500">
            No charge was made. You can retry with a different payment method.
          </p>
          <button
            type="button"
            onClick={() => void handleRetry()}
            disabled={isPending}
            className="bg-brand-600 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-brand-700 focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:outline-none active:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed"
            data-testid="error-retry-button"
          >
            {isPending ? "Retrying..." : "Try Again"}
          </button>
        </>
      )}

      {(variant === "rejected" || variant === "suspended") && (
        <>
          <p className="text-sm text-neutral-900">
            {variant === "rejected"
              ? "The carrier rejected your registration."
              : "Text messaging has been suspended."}
            {failureReason && ` ${failureReason}`}
          </p>
          {failureReason && (
            <p className="text-sm text-neutral-700 font-mono bg-neutral-50 rounded p-2">
              {failureReason}
            </p>
          )}
          <p className="text-sm text-neutral-500">
            Please contact support to resolve this:
          </p>
          <a
            href="mailto:support@pilotfortrades.com?subject=10DLC Registration Issue"
            className="inline-block border border-brand-600 text-brand-700 rounded-md px-4 py-2 text-sm font-medium hover:bg-brand-50 focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:outline-none"
            data-testid="error-contact-support"
          >
            Contact Support
          </a>
        </>
      )}
    </div>
  );
}
