/**
 * MFA Force-Flow Enrollment Page — MFA-WIRE-1 Part B (spec §2.10)
 * Route: /settings/my-account/security/mfa/enroll
 *
 * Reads ?mfa_required=1&grace_days=N from FE-B2's auth interceptor redirect.
 * Renders MFAEnrollmentWizard in force-flow mode (no cancel, full-page).
 *
 * MFA-WIRE-1: adds `allowedPaths={["totp","sms"]}` (email is not a pool
 * factor — design §G-Q2) and a force-flow context banner above the wizard.
 */
"use client";
import React from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { MFAEnrollmentWizard } from "@pilot/ui";
import { ShieldExclamationIcon } from "@heroicons/react/24/outline";

export default function MfaEnrollPage() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const graceDays = searchParams.get("grace_days");
  const gracePeriodDaysRemaining =
    graceDays != null ? parseInt(graceDays, 10) : undefined;

  const handleComplete = () => {
    // Redirect to the originally intended destination or dashboard
    const returnTo = searchParams.get("return_to") ?? "/";
    router.replace(returnTo);
  };

  return (
    <div className="min-h-screen bg-neutral-50 flex items-start justify-center">
      <div className="w-full max-w-lg">
        {/* Force-flow context banner (spec §2.10) */}
        <div
          role="alert"
          data-testid="mfa-force-flow-context-banner"
          className="rounded-md bg-alert-50 border border-alert-200 px-4 py-3 flex items-start gap-3 mb-4"
        >
          <ShieldExclamationIcon
            className="w-5 h-5 flex-shrink-0 text-alert-600"
            aria-hidden="true"
          />
          <span className="text-sm text-alert-700">
            Your organization requires multi-factor authentication. Enrollment
            is not optional — set up a method to continue.
          </span>
        </div>

        <MFAEnrollmentWizard
          onComplete={handleComplete}
          onCancel={() => {}} // No-op in force-flow
          allowedPaths={["totp", "sms"]}
          gracePeriodDaysRemaining={gracePeriodDaysRemaining}
          forceFlow={true}
          testID="mfa-force-flow-wizard"
        />
      </div>
    </div>
  );
}
