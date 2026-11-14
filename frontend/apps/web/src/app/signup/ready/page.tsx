/**
 * /signup/ready — Step 5: Trial confirmation + "Get started →"
 *
 * Location: apps/web/src/app/signup/ready/page.tsx
 *
 * RULE 4: On mount, verifies backend state = step5_confirm or complete.
 * "Get started →" calls PUT step5 then redirects to /dashboard.
 * sessionStorage tenant_id cleared on completion.
 */

"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiClient, getApiProblem } from "@pilot/shared-api";
import { useAuth } from "@pilot/ui/auth";
import { WizardProgressBar } from "@/features/signup/components/WizardProgressBar";
import { Step5Confirmation } from "@/features/signup/components/Step5Confirmation";
import {
  WIZARD_TENANT_ID_KEY,
  signupStateToStep,
  stepToUrl,
  OnboardingStep,
  type WizardSignupState,
} from "@/features/signup/types";

interface SignupSummaryItem {
  label: string;
  value: string;
  complete: boolean;
}

export default function SignupReadyPage() {
  const router = useRouter();
  const { user } = useAuth();
  // SIGNUP-UI-FIX-1: fall back to user.tenantId when sessionStorage is cleared
  const [tenantId] = useState<string | null>(() =>
    typeof window !== "undefined"
      ? (sessionStorage.getItem(WIZARD_TENANT_ID_KEY) ?? user?.tenantId ?? null)
      : null,
  );
  const [ownerName, setOwnerName] = useState("there");
  const [businessName, setBusinessName] = useState("");
  const planLabel = "Free Trial";
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  // C-B5: Charter branch state
  const [requiresPaymentMethod, setRequiresPaymentMethod] = useState(true);
  const [freePeriodEndsAt, setFreePeriodEndsAt] = useState<string | null>(null);

  const summaryItems: SignupSummaryItem[] = [
    { label: "Account", value: businessName || "Created", complete: true },
    { label: "Legal agreements", value: "Accepted", complete: true },
    { label: "Phone", value: "Verified", complete: true },
    { label: "Plan", value: planLabel, complete: true },
  ];

  useEffect(() => {
    const stored = tenantId;
    if (!stored) {
      router.replace("/signup/account");
      return;
    }

    // SIGNUP-UI-FIX-1: persist tenantId to sessionStorage for subsequent steps
    if (!sessionStorage.getItem(WIZARD_TENANT_ID_KEY) && stored) {
      sessionStorage.setItem(WIZARD_TENANT_ID_KEY, stored);
    }

    apiClient
      .get(`/api/v1/signup/${stored}/state`)
      .then((res) => {
        // SIGNUP-GA-B1: Model B — Ready is the page for both `step4_tier`
        // (plan done ⇒ confirm) and `step5_confirm` (payment/confirm).
        // `signupStateToStep` maps both to Ready, so the single-rule check
        // admits them. `complete` is special-cased to /dashboard.
        const current = res.data.signup_state as WizardSignupState;
        if (current === "complete") {
          // Already completed — clear session and go to dashboard
          sessionStorage.removeItem(WIZARD_TENANT_ID_KEY);
          router.replace("/dashboard");
          return;
        }
        setOwnerName(res.data.collected_data?.owner_first_name ?? "there");
        setBusinessName(res.data.collected_data?.business_name ?? "");
        // C-B5: Extract Charter branch fields from collected_data
        setRequiresPaymentMethod(
          res.data.collected_data?.requires_payment_method ?? true,
        );
        setFreePeriodEndsAt(
          res.data.collected_data?.free_period_ends_at ?? null,
        );
        // Plan label from selected_tier_id — approximate from trial assumption here
        // (exact label comes from tier list, but trial is the default path)
        const belongsOn = signupStateToStep[current];
        if (belongsOn !== OnboardingStep.Ready) {
          router.replace(stepToUrl[belongsOn] ?? "/signup/account");
        }
      })
      .catch(() => {
        sessionStorage.removeItem(WIZARD_TENANT_ID_KEY);
        router.replace("/signup/account");
      });
  }, [router, tenantId]);

  const handleGetStarted = async () => {
    if (!tenantId) return;
    setIsSubmitting(true);
    setSubmitError(null);

    try {
      await apiClient.put(`/api/v1/signup/${tenantId}/step5`, {
        confirmed: true,
      });
      // Clear session on successful completion
      sessionStorage.removeItem(WIZARD_TENANT_ID_KEY);
      router.replace("/dashboard");
    } catch (err: unknown) {
      const problem = getApiProblem(err);
      setSubmitError(
        problem.detail ?? "Couldn't complete setup. Please try again.",
      );
      setIsSubmitting(false);
    }
  };

  // C-B5: Charter branch (requires_payment_method=false) renders Step5Confirmation.
  // Non-Charter branch (requires_payment_method=true) renders the existing trial flow.
  if (!requiresPaymentMethod && freePeriodEndsAt) {
    return (
      <div className="flex flex-col gap-8">
        <WizardProgressBar currentStep="ready" />
        <Step5Confirmation
          freePeriodEndsAt={freePeriodEndsAt}
          ownerName={ownerName}
          onConfirm={handleGetStarted}
          isSubmitting={isSubmitting}
          submitError={submitError}
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-8">
      <WizardProgressBar currentStep="ready" />

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
        {summaryItems.map((item) => (
          <li key={item.label} className="flex items-center gap-3">
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
              {item.label}
            </span>
            <span className="text-sm font-medium text-neutral-900">
              {item.value}
            </span>
          </li>
        ))}
      </ul>

      {/* Trial details callout */}
      <div
        className="rounded-lg bg-brand-50 border border-brand-100 px-4 py-3 text-sm text-brand-700"
        data-testid="trial-callout"
      >
        Your free 14-day trial starts today. No credit card required. Upgrade
        anytime from your account settings.
      </div>

      {submitError && (
        <p role="alert" className="text-fault-600 text-sm text-center">
          {submitError}
        </p>
      )}

      <button
        type="button"
        onClick={handleGetStarted}
        disabled={isSubmitting}
        data-testid="signup-ready-get-started"
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
        {isSubmitting ? "Setting up…" : "Get started →"}
      </button>
    </div>
  );
}
