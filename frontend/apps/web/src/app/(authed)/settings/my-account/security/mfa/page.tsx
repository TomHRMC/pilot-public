/**
 * MFA Methods Page — MFA-WIRE-1 Part B (spec §2.1–2.9)
 * Route: /settings/my-account/security/mfa
 *
 * Embeds MFAEnrollmentWizard in voluntary mode (with close affordance).
 * Renders method cards from the new `methods[]` array with an optimistic
 * Remove flow. Constrained to `allowedPaths={["totp","sms"]}` (email is not
 * a pool factor — design §G-Q2).
 */
"use client";
import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { MFAEnrollmentWizard } from "@pilot/ui";
import type { MFAEnrollmentPath } from "@pilot/ui";
import { apiClient } from "@pilot/shared-api";
import { ErrorState } from "@pilot/ui/states";
import type { components } from "@pilot/shared-types";
import { MfaMethodCardList } from "../../../../../../features/account-settings/components/MfaMethodCardList";

type MfaStatusResponse = components["schemas"]["MfaStatusResponse"];

async function fetchMfaStatus(): Promise<MfaStatusResponse> {
  const res = await apiClient.get("/api/v1/users/me/mfa-status");
  return res.data as MfaStatusResponse;
}

// MFA-WIRE-1 (design §G-Q2): email is not a pool factor — only totp + sms.
const ALL_MFA_METHODS: MFAEnrollmentPath[] = ["totp", "sms"];

export default function MfaMethodsPage() {
  const [showEnrollWizard, setShowEnrollWizard] = useState(false);

  const {
    data: mfaStatus,
    isPending,
    isError,
    refetch,
  } = useQuery({
    queryKey: ["users", "me", "mfa-status"],
    queryFn: fetchMfaStatus,
    staleTime: 30_000,
  });

  const handleComplete = () => {
    setShowEnrollWizard(false);
    void refetch();
  };

  const enrolledCount = mfaStatus?.methods.length ?? 0;
  // Both methods enrolled → hide Add button (spec §2.6 — hidden, not disabled)
  const enrolledTypes = new Set(
    mfaStatus?.methods.map((m) => m.method_type) ?? [],
  );
  const allMethodsEnrolled = ALL_MFA_METHODS.every((m) => enrolledTypes.has(m));

  // Button label: "Add a method" when none enrolled, "Add another method" when 1+
  const addButtonLabel =
    enrolledCount === 0 ? "Add a method" : "Add another method";

  // ─── Loading state: 2-card skeleton (spec §2.8) ──────────────────────────
  if (isPending) {
    return (
      <div className="flex flex-col gap-6 max-w-2xl">
        <div>
          <h1 className="text-h2 font-semibold text-neutral-900">
            Two-factor authentication
          </h1>
          <p className="mt-1 text-sm text-neutral-500">
            Add an extra layer of security to your account.
          </p>
        </div>
        <div
          className="flex flex-col gap-3"
          data-testid="mfa-method-card-skeleton"
          aria-busy="true"
        >
          {[0, 1].map((i) => (
            <div
              key={i}
              className="rounded-lg border border-neutral-200 bg-white px-4 py-3 flex items-center gap-3"
            >
              <div className="w-10 h-10 rounded-full bg-neutral-100 animate-pulse motion-reduce:animate-none" />
              <div className="flex-1">
                <div className="h-4 w-32 rounded bg-neutral-100 animate-pulse motion-reduce:animate-none" />
                <div className="h-3 w-48 rounded bg-neutral-100 animate-pulse motion-reduce:animate-none mt-1" />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // ─── Error state (spec §2.9) ─────────────────────────────────────────────
  if (isError) {
    return (
      <div className="flex flex-col gap-6 max-w-2xl">
        <div>
          <h1 className="text-h2 font-semibold text-neutral-900">
            Two-factor authentication
          </h1>
          <p className="mt-1 text-sm text-neutral-500">
            Add an extra layer of security to your account.
          </p>
        </div>
        <ErrorState
          type="server"
          description="We couldn't load your MFA methods."
          onRetry={() => void refetch()}
          testID="mfa-status-error"
        />
      </div>
    );
  }

  // ─── Populated / empty state ─────────────────────────────────────────────
  // MfaMethodCardList always renders — it contains the tenant-policy banner
  // (which must show even when methods is empty), the error banner, the card
  // list, and the empty state. This ensures the policy banner is visible
  // regardless of enrollment state (spec §2.2).
  return (
    <div className="flex flex-col gap-6 max-w-2xl">
      <div>
        <h1 className="text-h2 font-semibold text-neutral-900">
          Two-factor authentication
        </h1>
        <p className="mt-1 text-sm text-neutral-500">
          Add an extra layer of security to your account.
        </p>
      </div>

      {mfaStatus && <MfaMethodCardList status={mfaStatus} />}

      {/* Add-method button — hidden (not disabled) when both enrolled (spec §2.6) */}
      {!showEnrollWizard && !allMethodsEnrolled && (
        <button
          type="button"
          onClick={() => setShowEnrollWizard(true)}
          className="self-start rounded-lg px-4 py-2.5 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 active:bg-brand-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 transition-colors duration-150 ease-in-out motion-reduce:transition-none"
          data-testid="add-mfa-method-btn"
        >
          {addButtonLabel}
        </button>
      )}

      {/* MFAEnrollmentWizard in voluntary mode (with close affordance) */}
      {showEnrollWizard && (
        <div
          className="rounded-xl border border-neutral-200 bg-white shadow-sm overflow-hidden"
          data-testid="mfa-wizard-container"
        >
          <MFAEnrollmentWizard
            onComplete={handleComplete}
            onCancel={() => setShowEnrollWizard(false)}
            enrolledMethods={
              (mfaStatus?.methods.map((m) => m.method_type) ??
                []) as MFAEnrollmentPath[]
            }
            allowedPaths={["totp", "sms"]}
            showRecoveryCodes={!mfaStatus || mfaStatus.methods.length === 0}
            forceFlow={false}
            testID="mfa-enrollment-wizard"
          />
        </div>
      )}
    </div>
  );
}
