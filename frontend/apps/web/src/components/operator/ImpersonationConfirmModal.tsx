"use client";

/**
 * ImpersonationConfirmModal — §16.7 always-preview-before-send confirm modal
 *
 * Location: apps/web/src/components/operator/ImpersonationConfirmModal.tsx
 *
 * C-B15 Part B: Domain-specific confirm modal (NOT MessagePreviewModal — that
 * is locked to comms previews). Built on the standard modal pattern (overlay
 * + panel + focus trap), consistent with C-B11's CloseCohortButton modal.
 *
 * On confirm → useImpersonationStart → setImpersonation → window.location.assign('/dashboard')
 * (deliberate full page reload — hard rule, design §G Q2/Q3).
 *
 * Error mapping per spec §5.9: 403/404/409 → specific messages, modal stays open.
 *
 * RULE 5: zero hex codes. RULE 15: WCAG 2.2 AA (focus trap, role=dialog, aria).
 */

import React, { useEffect, useRef, useState } from "react";
import {
  XMarkIcon,
  ExclamationTriangleIcon,
  ExclamationCircleIcon,
} from "@heroicons/react/24/outline";
import { isAxiosError, setImpersonation } from "@pilot/shared-api";
import { useImpersonationStart } from "@/features/operator/hooks/useImpersonationStart";
import { StatusPill } from "./StatusPill";
import type { components } from "@pilot/shared-types";

type OperatorTenantSummary = components["schemas"]["OperatorTenantSummary"];

interface ImpersonationConfirmModalProps {
  tenant: OperatorTenantSummary;
  onClose: () => void;
}

export function ImpersonationConfirmModal({
  tenant,
  onClose,
}: ImpersonationConfirmModalProps) {
  const startMutation = useImpersonationStart();
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const cancelButtonRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const previouslyFocused = useRef<HTMLElement | null>(null);

  // Focus trap: focus Cancel on open, trap Tab, return focus on close
  useEffect(() => {
    previouslyFocused.current = document.activeElement as HTMLElement;
    cancelButtonRef.current?.focus();

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
        return;
      }
      if (e.key === "Tab" && panelRef.current) {
        const focusable = panelRef.current.querySelectorAll<HTMLElement>(
          'button, [href], input, [tabindex]:not([tabindex="-1"])',
        );
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      previouslyFocused.current?.focus();
    };
  }, [onClose]);

  const handleConfirm = async () => {
    setErrorMessage(null);
    try {
      const result = await startMutation.mutateAsync({
        tenantId: tenant.tenant_id,
      });
      // Success — write session + full reload (hard rule)
      setImpersonation({
        tenantId: result.tenant_id,
        tenantName: result.tenant_name,
      });
      window.location.assign("/dashboard");
    } catch (error) {
      // Error mapping per spec §5.9
      if (isAxiosError(error)) {
        const status = error.response?.status;
        if (status === 403) {
          setErrorMessage("Your role does not permit impersonation.");
        } else if (status === 404) {
          setErrorMessage("This tenant no longer exists.");
        } else if (status === 409) {
          setErrorMessage(
            "This tenant is inactive and cannot be impersonated.",
          );
        } else {
          setErrorMessage("An unexpected error occurred. Please try again.");
        }
      } else {
        setErrorMessage("An unexpected error occurred. Please try again.");
      }
    }
  };

  const handleOverlayClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const isInFlight = startMutation.isPending;

  return (
    <div
      className="fixed inset-0 bg-neutral-900/50 z-50 flex items-start justify-center"
      onClick={handleOverlayClick}
      data-testid="impersonation-modal-overlay"
    >
      <div
        ref={panelRef}
        className="bg-white rounded-lg shadow-xl max-w-md w-full mx-auto mt-16 p-6"
        role="dialog"
        aria-modal="true"
        aria-labelledby="impersonation-modal-title"
        data-testid="impersonation-confirm-modal"
      >
        {/* Close button */}
        <button
          type="button"
          onClick={onClose}
          aria-label="Close dialog"
          className="absolute top-4 right-4 p-2.5 rounded-md hover:bg-neutral-100 focus-visible:ring-2 focus-visible:ring-brand-500"
        >
          <XMarkIcon className="w-5 h-5 text-neutral-500" aria-hidden="true" />
        </button>

        {/* Title */}
        <h2
          id="impersonation-modal-title"
          className="text-h2 font-semibold text-neutral-900"
        >
          View as a tenant
        </h2>

        {/* Lead sentence */}
        <p className="text-sm text-neutral-700 mt-2">
          You are about to view Pilot as{" "}
          <strong className="font-semibold text-neutral-900">
            {tenant.name}
          </strong>{" "}
          (owner).
        </p>

        {/* Warning sentence */}
        <p className="text-sm text-fault-600 font-medium mt-2 flex items-center gap-1.5">
          <ExclamationTriangleIcon className="w-4 h-4" aria-hidden="true" />
          All changes you make are real and audit-logged.
        </p>

        {/* Preview block */}
        <div className="bg-neutral-50 border border-neutral-200 rounded-md p-4 mt-4">
          <div className="flex justify-between gap-4 text-sm py-1">
            <span className="text-neutral-500">Tenant</span>
            <span className="text-neutral-900 font-medium">{tenant.name}</span>
          </div>
          <div className="flex justify-between gap-4 text-sm py-1">
            <span className="text-neutral-500">Tier</span>
            <span className="text-neutral-700">{tenant.tier_name ?? "—"}</span>
          </div>
          <div className="flex justify-between gap-4 text-sm py-1">
            <span className="text-neutral-500">Status</span>
            <StatusPill status={tenant.subscription_status} />
          </div>
          <div className="flex justify-between gap-4 text-sm py-1">
            <span className="text-neutral-500">Role</span>
            <span className="text-neutral-700">Owner (full access)</span>
          </div>
        </div>

        {/* Persistence note */}
        <p className="text-sm text-neutral-700 mt-3 flex items-center gap-1.5">
          <ExclamationCircleIcon
            className="w-4 h-4 text-alert-600"
            aria-hidden="true"
          />
          This session persists until you exit. Closing the tab also ends the
          session.
        </p>

        {/* Error message */}
        {errorMessage && (
          <p
            className="text-sm text-fault-600 mt-3"
            role="alert"
            data-testid="impersonation-modal-error"
          >
            {errorMessage}
          </p>
        )}

        {/* Action buttons */}
        <div className="flex justify-end gap-3 mt-6">
          <button
            ref={cancelButtonRef}
            type="button"
            onClick={onClose}
            className="border border-neutral-300 text-neutral-700 rounded-md px-4 py-2 text-sm font-medium hover:bg-neutral-50 focus-visible:ring-2 focus-visible:ring-brand-500"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={isInFlight}
            className="bg-brand-600 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-brand-700 focus-visible:ring-2 focus-visible:ring-brand-500 disabled:bg-neutral-300 disabled:cursor-not-allowed"
            data-testid="impersonation-confirm-button"
          >
            {isInFlight ? `View as ${tenant.name}…` : `View as ${tenant.name}`}
          </button>
        </div>
      </div>
    </div>
  );
}
