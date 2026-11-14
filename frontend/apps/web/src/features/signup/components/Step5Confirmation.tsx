/**
 * Step5Confirmation — Step 5 Charter confirmation branch (no-card path)
 *
 * Location: apps/web/src/features/signup/components/Step5Confirmation.tsx
 *
 * C-B5: Renders the Charter (no-card) branch of step 5. Replaces the trial
 * callout with a Charter-specific confirmation message: "You are set. No charge
 * until {free_period_ends_at}." with a "Complete Signup" button.
 *
 * The existing StripePaymentForm is retained and made conditional in
 * ready/page.tsx — flipping requires_payment_method to true re-enables it.
 */

"use client";

import React from "react";
import { CheckBadgeIcon } from "@heroicons/react/24/outline";

interface Step5ConfirmationProps {
  freePeriodEndsAt: string;
  ownerName: string;
  onConfirm: () => void;
  isSubmitting: boolean;
  submitError: string | null;
}

export function Step5Confirmation({
  freePeriodEndsAt,
  ownerName,
  onConfirm,
  isSubmitting,
  submitError,
}: Step5ConfirmationProps): React.ReactElement {
  const formattedDate = new Date(freePeriodEndsAt).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  return (
    <div className="flex flex-col gap-6">
      {/* Celebration header */}
      <div className="flex flex-col items-center gap-3 text-center">
        <div
          className="w-16 h-16 rounded-full bg-margin-50 border-2 border-margin-200 flex items-center justify-center text-3xl"
          aria-hidden="true"
        >
          🎉
        </div>
        <h1 className="text-2xl font-bold text-neutral-900">
          You&apos;re all set, {ownerName}!
        </h1>
        <p className="text-sm text-neutral-600">
          Your Pilot account is ready. Here&apos;s a summary of what you
          completed:
        </p>
      </div>

      {/* Summary checklist */}
      <ul
        className="flex flex-col gap-3 rounded-xl border border-neutral-200 bg-white p-6"
        aria-label="Setup summary"
        data-testid="signup-summary"
      >
        <li className="flex items-center gap-3">
          <div className="w-5 h-5 rounded-full bg-margin-600 flex items-center justify-center flex-shrink-0">
            <svg
              className="w-3 h-3 text-white"
              fill="none"
              viewBox="0 0 12 12"
              aria-hidden="true"
            >
              <path
                d="M2 6l3 3 5-5"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <span className="text-sm text-neutral-700 flex-1">Account</span>
          <span className="text-sm font-medium text-neutral-900">Created</span>
        </li>
        <li className="flex items-center gap-3">
          <div className="w-5 h-5 rounded-full bg-margin-600 flex items-center justify-center flex-shrink-0">
            <svg
              className="w-3 h-3 text-white"
              fill="none"
              viewBox="0 0 12 12"
              aria-hidden="true"
            >
              <path
                d="M2 6l3 3 5-5"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <span className="text-sm text-neutral-700 flex-1">
            Legal agreements
          </span>
          <span className="text-sm font-medium text-neutral-900">Accepted</span>
        </li>
        <li className="flex items-center gap-3">
          <div className="w-5 h-5 rounded-full bg-margin-600 flex items-center justify-center flex-shrink-0">
            <svg
              className="w-3 h-3 text-white"
              fill="none"
              viewBox="0 0 12 12"
              aria-hidden="true"
            >
              <path
                d="M2 6l3 3 5-5"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <span className="text-sm text-neutral-700 flex-1">Phone</span>
          <span className="text-sm font-medium text-neutral-900">Verified</span>
        </li>
        <li className="flex items-center gap-3">
          <div className="w-5 h-5 rounded-full bg-margin-600 flex items-center justify-center flex-shrink-0">
            <svg
              className="w-3 h-3 text-white"
              fill="none"
              viewBox="0 0 12 12"
              aria-hidden="true"
            >
              <path
                d="M2 6l3 3 5-5"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <span className="text-sm text-neutral-700 flex-1">Plan</span>
          <span className="text-sm font-medium text-neutral-900">Charter</span>
        </li>
      </ul>

      {/* Charter confirmation callout */}
      <div
        className="rounded-lg bg-brand-50 border border-brand-100 px-4 py-3 flex items-start gap-3"
        data-testid="charter-confirmation-callout"
      >
        <CheckBadgeIcon className="w-5 h-5 text-brand-600 flex-shrink-0" />
        <p className="text-sm text-brand-700">
          You&apos;re set. No charge until {formattedDate}.
        </p>
      </div>

      {submitError && (
        <p
          role="alert"
          className="text-fault-600 text-sm text-center"
          data-testid="step5-confirmation-error"
        >
          {submitError}
        </p>
      )}

      <button
        type="button"
        onClick={onConfirm}
        disabled={isSubmitting}
        aria-disabled={isSubmitting}
        data-testid="step5-confirmation-complete"
        className={`
          w-full py-3 px-6 rounded-lg text-sm font-semibold transition-colors
          focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2
          ${
            isSubmitting
              ? "opacity-40 cursor-not-allowed bg-brand-600 text-white"
              : "bg-brand-600 hover:bg-brand-800 text-white"
          }
        `}
      >
        {isSubmitting ? "Setting up…" : "Complete Signup"}
      </button>
    </div>
  );
}
