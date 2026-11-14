/**
 * MfaEnrollmentRequiredGate — web
 *
 * Location: apps/web/src/features/login/components/MfaEnrollmentRequiredGate.tsx
 *
 * Shown when login succeeds but tenant-required MFA policy is active and
 * the user has no enrolled methods (and grace period has expired).
 *
 * FE-B2 minimal implementation:
 * - Grace period: shows persistent warning banner; allows app access
 * - Post-grace: blocking screen — cannot access app until MFA enrolled
 *
 * Full MFA enrollment wizard lives in FE-B12.
 */

"use client";

import React from "react";
import Link from "next/link";

interface MfaEnrollmentRequiredGateProps {
  gracePeriodEndsAt?: string; // ISO date string — if present, still in grace period
  onBeginEnrollment: () => void;
  onSignOut: () => void;
}

function getDaysRemaining(endsAt: string): number {
  const end = new Date(endsAt);
  const now = new Date();
  const diffMs = end.getTime() - now.getTime();
  return Math.max(0, Math.ceil(diffMs / (1000 * 60 * 60 * 24)));
}

export function MfaEnrollmentRequiredGate({
  gracePeriodEndsAt,
  onBeginEnrollment,
  onSignOut,
}: MfaEnrollmentRequiredGateProps) {
  const isInGracePeriod = Boolean(gracePeriodEndsAt);
  const daysRemaining = gracePeriodEndsAt
    ? getDaysRemaining(gracePeriodEndsAt)
    : 0;

  if (isInGracePeriod) {
    // Non-blocking: shows warning banner but user can proceed
    return (
      <div
        role="alert"
        className="rounded-md bg-alert-50 border border-alert-200 px-4 py-3 flex items-start gap-3"
      >
        <div className="flex-1">
          <p className="text-body text-alert-600">
            MFA enrollment required within{" "}
            <strong>
              {daysRemaining} day{daysRemaining !== 1 ? "s" : ""}
            </strong>
            .
          </p>
        </div>
        <button
          type="button"
          onClick={onBeginEnrollment}
          className="text-body text-brand-600 hover:underline focus:outline-none whitespace-nowrap"
        >
          Set up now →
        </button>
      </div>
    );
  }

  // Blocking: grace period expired
  return (
    <div
      role="main"
      aria-label="MFA enrollment required"
      className="flex min-h-screen flex-col items-center justify-center p-6 bg-neutral-50"
    >
      <div className="w-full max-w-md rounded-lg bg-white p-8 shadow-sm border border-neutral-200 flex flex-col gap-6 text-center">
        <div className="flex flex-col gap-2">
          <h1 className="text-h1 text-neutral-900">
            Multi-factor authentication required
          </h1>
          <p className="text-body text-neutral-600">
            Multi-factor authentication is required by your organization. Set it
            up to continue.
          </p>
        </div>

        <button
          type="button"
          onClick={onBeginEnrollment}
          className="w-full rounded-md bg-brand-600 px-4 py-2 text-body-lg text-white hover:bg-brand-800 focus:outline-none focus:ring-2 focus:ring-brand-600 focus:ring-offset-2"
        >
          Set up MFA
        </button>

        <Link
          href="/settings/my-account"
          className="text-body text-brand-600 hover:underline focus:outline-none"
        >
          Go to account settings
        </Link>

        <button
          type="button"
          onClick={onSignOut}
          className="text-caption text-neutral-400 hover:text-neutral-600 hover:underline focus:outline-none"
        >
          Sign out
        </button>
      </div>
    </div>
  );
}
