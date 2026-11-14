/**
 * MfaMethodCardList — MFA-WIRE-1 Part B (spec §2.2–2.5, §5.2, §8 row 3)
 *
 * Location: apps/web/src/features/account-settings/components/MfaMethodCardList.tsx
 *
 * Surface-scoped list component that:
 *   - Renders the tenant-policy/grace banner (spec §2.2) above the card list
 *   - Maps `methods[]` → <MfaMethodCard>
 *   - Manages the Remove confirm modal open state
 *   - Drives the Remove mutation through `useRemoveMfaMethod` with optimistic UI
 *     (dim + <PendingBadge> per spec §2.4; rollback on error)
 *   - Renders inline error banners for 409 last_method_required (warning),
 *     502 cognito_unavailable (error), 401 mfa_access_token_invalid (error)
 *     per spec §5.2
 *
 * NOT exported from packages/ui — surface-scoped by design (§I).
 */
"use client";

import React, { useState, useCallback } from "react";
import { ShieldExclamationIcon } from "@heroicons/react/24/outline";
import { isAxiosError } from "@pilot/shared-api";
import type { components } from "@pilot/shared-types";
import { MfaMethodCard } from "./MfaMethodCard";
import { RemoveMethodConfirmModal } from "./RemoveMethodConfirmModal";
import { useRemoveMfaMethod } from "../hooks/useRemoveMfaMethod";

type MfaStatusResponse = components["schemas"]["MfaStatusResponse"];
type MfaMethodInfo = components["schemas"]["MfaMethodInfo"];

export interface MfaMethodCardListProps {
  status: MfaStatusResponse;
}

/** Inline banner severity → token classes (spec §3, §5.2). */
const BANNER_CLASSES = {
  warning: "bg-alert-50 border-alert-200 text-alert-700",
  error: "bg-fault-50 border-fault-200 text-fault-700",
} as const;

/** Error-code → banner copy (spec §5.2). */
function resolveBannerCopy(
  code: string | null,
  detail: string | null,
): { severity: "warning" | "error"; copy: string } | null {
  switch (code) {
    case "last_method_required":
      return {
        severity: "warning",
        copy: "Your organization requires MFA. Add another method before removing this one.",
      };
    case "cognito_unavailable":
      return {
        severity: "error",
        copy: "We couldn't reach the authentication service — your method was NOT removed. Try again.",
      };
    case "mfa_access_token_invalid":
      return {
        severity: "error",
        copy: "Your session has expired. Please sign in again to manage MFA.",
      };
    case "mfa_access_token_required":
      // Client bug in prod — surface generic 502 copy (spec §5.2)
      return {
        severity: "error",
        copy: "We couldn't reach the authentication service — your method was NOT removed. Try again.",
      };
    default:
      // Unknown error — use the detail if available, else generic
      return {
        severity: "error",
        copy: detail ?? "Something went wrong. Please try again.",
      };
  }
}

/** Compute tenant-policy banner copy + severity (spec §2.2, §5.3). */
function resolvePolicyBanner(
  status: MfaStatusResponse,
): { isZeroDay: boolean; copy: string } | null {
  if (!status.tenant_policy_required) return null;

  if (status.grace_period_active && status.grace_ends_at) {
    const endsAt = new Date(status.grace_ends_at);
    const now = new Date();
    const daysRemaining = Math.ceil(
      (endsAt.getTime() - now.getTime()) / (1000 * 60 * 60 * 24),
    );
    if (daysRemaining <= 0) {
      return {
        isZeroDay: true,
        copy: "MFA enrollment is required today to continue using Pilot.",
      };
    }
    if (daysRemaining <= 3) {
      return {
        isZeroDay: false,
        copy: `Your organization requires MFA. ${daysRemaining} day${daysRemaining === 1 ? "" : "s"} left to enroll — add a method now.`,
      };
    }
    return {
      isZeroDay: false,
      copy: `Your organization requires MFA. You have ${daysRemaining} days left to enroll before access is restricted.`,
    };
  }

  // Policy required, no grace
  return {
    isZeroDay: false,
    copy: "Your organization requires multi-factor authentication. Add at least one method to keep your account secure.",
  };
}

export function MfaMethodCardList({ status }: MfaMethodCardListProps) {
  const [pendingMethodId, setPendingMethodId] = useState<string | null>(null);
  const [modalMethod, setModalMethod] = useState<MfaMethodInfo | null>(null);
  const [banner, setBanner] = useState<{
    severity: "warning" | "error";
    copy: string;
  } | null>(null);

  const removeMutation = useRemoveMfaMethod();

  const handleRemoveClick = useCallback((method: MfaMethodInfo) => {
    setModalMethod(method);
    setBanner(null);
  }, []);

  const handleCancelModal = useCallback(() => {
    setModalMethod(null);
  }, []);

  const handleConfirmRemove = useCallback(() => {
    if (!modalMethod) return;
    const methodId = modalMethod.method_id;
    setModalMethod(null);
    // Enter optimistic pending state (dim + badge per spec §2.4)
    setPendingMethodId(methodId);
    setBanner(null);

    // Single mutateAsync call. On 204 → hook invalidates the query →
    // methods[] refetches → card disappears. On error → rollback + banner.
    // The error code is extracted from the actual error object (not the
    // stale closure's removeMutation.errorCode) so it's always current.
    removeMutation.mutateAsync(methodId).then(
      () => {
        // Success — clear pending (the invalidation refetches the list)
        setPendingMethodId(null);
      },
      (err: unknown) => {
        // Error path — rollback pending + show banner (spec §5.2)
        setPendingMethodId(null);
        let code: string | null = null;
        let detail: string | null = null;
        if (isAxiosError(err)) {
          const data = err.response?.data as
            | { code?: string; detail?: string }
            | undefined;
          code = data?.code ?? null;
          detail = data?.detail ?? null;
        }
        const resolved = resolveBannerCopy(code, detail);
        if (resolved) setBanner(resolved);
      },
    );
  }, [modalMethod, removeMutation]);

  // Simpler: use mutate (fire-and-forget) + watch mutation state via effect.
  // Refactored below to avoid double-call.

  const policyBanner = resolvePolicyBanner(status);

  return (
    <div className="flex flex-col gap-4">
      {/* Tenant-policy / grace banner (spec §2.2) */}
      {policyBanner && (
        <div
          role="alert"
          data-testid="mfa-tenant-policy-banner"
          className={`rounded-md border px-4 py-3 flex items-start gap-3 ${
            policyBanner.isZeroDay
              ? "bg-fault-50 border-fault-200 text-fault-700"
              : "bg-alert-50 border-alert-200 text-alert-700"
          }`}
        >
          <ShieldExclamationIcon
            className={`w-5 h-5 flex-shrink-0 ${
              policyBanner.isZeroDay ? "text-fault-600" : "text-alert-600"
            }`}
            aria-hidden="true"
          />
          <span className="text-sm">{policyBanner.copy}</span>
        </div>
      )}

      {/* Inline error/warning banner (spec §5.2) */}
      {banner && (
        <div
          role="alert"
          data-testid="mfa-remove-error-banner"
          className={`rounded-md border px-4 py-3 flex items-start gap-3 ${BANNER_CLASSES[banner.severity]}`}
        >
          <ShieldExclamationIcon
            className="w-5 h-5 flex-shrink-0"
            aria-hidden="true"
          />
          <span className="text-sm">{banner.copy}</span>
        </div>
      )}

      {/* Method card list (spec §2.3) OR empty state (spec §2.7) */}
      {status.methods.length > 0 ? (
        <div className="flex flex-col gap-3" data-testid="mfa-method-card-list">
          {status.methods.map((method) => (
            <MfaMethodCard
              key={method.method_id}
              method={method}
              isPending={pendingMethodId === method.method_id}
              onRemove={() => handleRemoveClick(method)}
            />
          ))}
        </div>
      ) : (
        <div
          className="rounded-lg border border-neutral-200 bg-white p-6 flex flex-col items-center gap-3 text-center"
          data-testid="mfa-empty-state"
        >
          <ShieldExclamationIcon
            className="w-8 h-8 text-neutral-400"
            aria-hidden="true"
          />
          <p className="text-sm font-medium text-neutral-900">
            No authentication methods enrolled
          </p>
          <p className="text-sm text-neutral-500">
            Add an authenticator app or text-message verification to protect
            your account.
          </p>
        </div>
      )}

      {/* Remove confirm modal (spec §2.5) */}
      {modalMethod && (
        <RemoveMethodConfirmModal
          open={true}
          methodLabel={
            modalMethod.method_type === "totp"
              ? "Authenticator app"
              : "Text message"
          }
          triggerButtonId={`mfa-method-remove-${modalMethod.method_type}`}
          onConfirm={handleConfirmRemove}
          onCancel={handleCancelModal}
        />
      )}
    </div>
  );
}
