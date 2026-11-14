/**
 * /signup/plan — Step 4: Tier Selection + Inline Stripe Payment
 *
 * Location: apps/web/src/app/signup/plan/page.tsx
 *
 * RULE 4: Navigation driven by backend state.
 * Design doc Decision 3: Inline Stripe form below tier cards (no separate sub-step).
 * Trial selected (default) → Continue calls PUT step4 → navigates to /signup/ready
 * Paid tier selected → StripePaymentForm appears inline → Continue after payment
 */

"use client";

import React, { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiClient, getApiProblem } from "@pilot/shared-api";
import { useAuth } from "@pilot/ui/auth";
import { TierPickerCard, StripePaymentForm } from "@pilot/ui";
import { WizardProgressBar } from "@/features/signup/components/WizardProgressBar";
import { CharterTierCard } from "@/features/signup/components/CharterTierCard";
import {
  useSubscriptionTiers,
  getRecommendedTierName,
} from "@/features/signup/hooks/useSubscriptionTiers";
import {
  WIZARD_TENANT_ID_KEY,
  signupStateToStep,
  stepToUrl,
  OnboardingStep,
  type WizardSignupState,
  type SubscriptionTierAPI,
} from "@/features/signup/types";
import type { StripePaymentResult } from "@pilot/ui";

const STRIPE_PK =
  process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY ?? "pk_test_placeholder";

function tierToCardProps(tier: SubscriptionTierAPI, recommendedName: string) {
  return {
    tierName: tier.tier_name as string,
    displayName: tier.display_label,
    monthlyPriceCents: tier.monthly_price_cents,
    features: [
      { label: "Voice quoting", included: true },
      { label: "Job management", included: true },
      { label: "QuickBooks sync", included: tier.tier_name !== "trial" },
      {
        label: "SMS notifications",
        included: !!tier.max_sms_segments_per_month,
      },
      {
        label: "Team members",
        included: true,
        callout: `Up to ${tier.max_users}`,
      },
    ],
    isFeatured: tier.tier_name === recommendedName,
    isTrialTier: tier.is_trial,
    trialDurationDays: tier.trial_duration_days ?? undefined,
    maxUsers: tier.max_users,
  };
}

export default function SignupPlanPage() {
  const router = useRouter();
  const { user } = useAuth();

  // Lazy init: reads sessionStorage synchronously, falls back to user.tenantId
  // (SIGNUP-UI-FIX-1: sessionStorage is cleared when the browser tab closes,
  // but an authenticated user returning to the wizard should still resume).
  const [tenantId] = useState<string | null>(() =>
    typeof window !== "undefined"
      ? (sessionStorage.getItem(WIZARD_TENANT_ID_KEY) ?? user?.tenantId ?? null)
      : null,
  );

  // businessSize from backend: use ref so we can update it in effect without re-render issues
  const businessSizeRef = useRef<string>("solo");
  const [businessSize, setBusinessSize] = useState<string>("solo");

  // selectedTierId — null means "auto" → resolved to trial tier via derivation
  const [selectedTierId, setSelectedTierId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [paymentMethodId, setPaymentMethodId] = useState<string | null>(null);

  const {
    data: tiers,
    isError: tiersError,
    refetch: refetchTiers,
    isLoading: tiersLoading,
  } = useSubscriptionTiers();

  // Redirect to correct step if state doesn't match.
  // SIGNUP-GA-B1: Model B — Plan is the page for `step3_phone`
  // (phone done ⇒ select plan). Redirect only when the user belongs on a
  // different page. business_size is still read for tier recommendation.
  useEffect(() => {
    const stored = tenantId;
    if (!stored) {
      router.replace("/signup/account");
      return;
    }

    // SIGNUP-UI-FIX-1: persist tenantId to sessionStorage so subsequent
    // wizard steps + the Continue button have it available.
    if (!sessionStorage.getItem(WIZARD_TENANT_ID_KEY) && stored) {
      sessionStorage.setItem(WIZARD_TENANT_ID_KEY, stored);
    }

    apiClient
      .get(`/api/v1/signup/${stored}/state`)
      .then((res) => {
        const current = res.data.signup_state as WizardSignupState;
        const size = res.data.collected_data?.business_size ?? "solo";
        businessSizeRef.current = size;
        setBusinessSize(size);
        if (current === "complete") {
          router.replace("/dashboard");
          return;
        }
        const belongsOn = signupStateToStep[current];
        if (belongsOn !== OnboardingStep.Plan) {
          router.replace(stepToUrl[belongsOn] ?? "/signup/account");
        }
      })
      .catch(() => {
        sessionStorage.removeItem(WIZARD_TENANT_ID_KEY);
        router.replace("/signup/account");
      });
  }, [router, tenantId]);

  // Derive trial tier from loaded tiers
  const trialTier = tiers?.find((t) => t.is_trial);
  // Mode-aware subtitle (STEP 4 — SIGNUP-UI-FIX-1):
  // If no trial tier exists, the app is in Charter mode.
  const hasTrialTier = !!trialTier;
  const subtitleText = hasTrialTier
    ? "Start with a 14-day free trial — no credit card required."
    : "Join the Charter program — 90 days free, no credit card required.";
  // Effective selected tier: use explicit selection or default to trial
  const effectiveSelectedTierId = selectedTierId ?? trialTier?.tier_id ?? null;
  const selectedTier = tiers?.find(
    (t) => t.tier_id === effectiveSelectedTierId,
  );
  const selectedTierIsTrial = selectedTier?.is_trial ?? true;
  const recommendedTierName = getRecommendedTierName(businessSize);

  // Fetch Stripe payment intent when paid tier selected — useQuery handles async cleanly
  const { data: paymentIntentData } = useQuery({
    queryKey: ["payment-intent", tenantId, effectiveSelectedTierId],
    queryFn: async () => {
      const res = await apiClient.post<{ client_secret: string }>(
        `/api/v1/signup/${tenantId}/payment-intent`,
      );
      return res.data;
    },
    enabled: !!tenantId && !!effectiveSelectedTierId && !selectedTierIsTrial,
    staleTime: 10 * 60 * 1000, // 10 min — payment intents are stable
  });

  const clientSecret = selectedTierIsTrial
    ? null
    : (paymentIntentData?.client_secret ?? null);

  const handleSelectTier = (tierName: string) => {
    const tier = tiers?.find((t) => t.tier_name === tierName);
    if (tier) {
      setSelectedTierId(tier.tier_id);
      setPaymentMethodId(null);
      setSubmitError(null);
    }
  };

  const handleStripeSuccess = (result: StripePaymentResult) => {
    setPaymentMethodId(result.paymentMethodId ?? null);
  };

  const handleContinue = async () => {
    if (!tenantId || !effectiveSelectedTierId || !selectedTier) return;
    setIsSubmitting(true);
    setSubmitError(null);

    try {
      await apiClient.put(`/api/v1/signup/${tenantId}/step4`, {
        selected_tier_id: effectiveSelectedTierId,
      });

      // C-B5: Charter tier (requires_payment_method=false) skips step5 PUT —
      // the backend handles Charter confirmation in step4. Non-trial paid
      // tiers still require the step5 PUT with the Stripe payment method.
      // SIGNUP-UI-FIX-2: fall back to tier_name === "charter" when
      // requires_payment_method is absent/undefined (the field is optional
      // in SubscriptionTierAPI — a payload omitting it must not strand the
      // user on the paid path waiting for a clientSecret that never resolves).
      const isCharterTier =
        selectedTier.requires_payment_method === false ||
        selectedTier.tier_name === "charter";
      if (!selectedTierIsTrial && !isCharterTier) {
        await apiClient.put(`/api/v1/signup/${tenantId}/step5`, {
          confirmed: true,
          stripe_payment_method_id: paymentMethodId,
        });
      }

      router.push("/signup/ready");
    } catch (err: unknown) {
      // C-B5: 409 = tier-closed (cohort cap reached)
      const problem = getApiProblem(err);
      if (problem.status === 409) {
        setSubmitError(
          "This tier has reached its signup cap and is no longer accepting new members.",
        );
      } else {
        setSubmitError(
          problem.detail ??
            "Failed to save your plan selection. Please try again.",
        );
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  // C-B5: Charter tier (requires_payment_method=false) needs no payment method.
  // SIGNUP-UI-FIX-2: fall back to tier_name === "charter" when
  // requires_payment_method is absent/undefined so the payment-form
  // placeholder never renders for a Charter selection.
  const selectedTierIsCharter =
    selectedTier?.requires_payment_method === false ||
    selectedTier?.tier_name === "charter";
  const canContinue =
    !!effectiveSelectedTierId &&
    (selectedTierIsTrial || selectedTierIsCharter || !!paymentMethodId) &&
    !isSubmitting;

  return (
    <div className="flex flex-col gap-8">
      <WizardProgressBar currentStep="plan" />

      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-bold text-neutral-900">
          Choose your plan
        </h1>
        <p className="text-sm text-neutral-600">{subtitleText}</p>
      </div>

      {tiersError ? (
        <div
          className="rounded-lg border border-fault-200 bg-fault-50 px-4 py-3 text-sm text-fault-700 flex items-center justify-between"
          data-testid="tier-error"
        >
          <span>Couldn&apos;t load plans.</span>
          <button
            type="button"
            onClick={() => refetchTiers()}
            className="text-fault-700 underline hover:text-fault-900 focus:outline-none"
          >
            Retry
          </button>
        </div>
      ) : tiersLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="animate-pulse rounded-xl border-2 border-neutral-200 bg-neutral-100 h-64"
            />
          ))}
        </div>
      ) : (
        <div
          role="radiogroup"
          aria-label="Subscription plan selection"
          className="grid grid-cols-1 sm:grid-cols-2 gap-4"
          data-testid="tier-picker-grid"
        >
          {(tiers ?? [])
            .sort((a, b) => a.display_order - b.display_order)
            .map((tier) =>
              tier.tier_name === "charter" ? (
                <CharterTierCard
                  key={tier.tier_id}
                  tier={tier}
                  isSelected={effectiveSelectedTierId === tier.tier_id}
                  onSelect={() => handleSelectTier(tier.tier_name)}
                />
              ) : (
                <TierPickerCard
                  key={tier.tier_id}
                  {...tierToCardProps(tier, recommendedTierName)}
                  isSelected={effectiveSelectedTierId === tier.tier_id}
                  onSelect={handleSelectTier}
                  testID={`tier-card-${tier.tier_name}`}
                />
              ),
            )}
        </div>
      )}

      {/* Inline Stripe form for paid tier selection (excludes Charter — no card needed) */}
      {!selectedTierIsTrial && !selectedTierIsCharter && clientSecret && (
        <div
          className="rounded-xl border border-neutral-200 bg-white p-6 flex flex-col gap-4"
          data-testid="inline-stripe-form"
        >
          <h2 className="text-base font-semibold text-neutral-900">
            Payment method
          </h2>
          <p className="text-xs text-neutral-500">
            You won&apos;t be charged until your plan is confirmed.
          </p>
          <StripePaymentForm
            stripePublishableKey={STRIPE_PK}
            clientSecret={clientSecret}
            mode="subscription"
            submitLabel="Save payment method"
            onSuccess={handleStripeSuccess}
            onError={(err) => setSubmitError(err.message)}
            testID="signup-stripe-form"
          />
        </div>
      )}

      {!selectedTierIsTrial &&
        !selectedTierIsCharter &&
        !clientSecret &&
        !tiersLoading &&
        selectedTier && (
          <div className="rounded-lg bg-neutral-50 border border-neutral-200 px-4 py-3 text-sm text-neutral-600 animate-pulse">
            Loading payment form…
          </div>
        )}

      {submitError && (
        <p role="alert" className="text-fault-600 text-sm">
          {submitError}
        </p>
      )}

      <button
        type="button"
        onClick={handleContinue}
        disabled={!canContinue}
        aria-disabled={!canContinue}
        data-testid="signup-plan-continue"
        className={`
          w-full py-3 px-6 rounded-lg text-sm font-semibold transition-colors
          focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2
          ${
            !canContinue
              ? "opacity-40 cursor-not-allowed bg-brand-600 text-white"
              : "bg-brand-600 hover:bg-brand-800 text-white"
          }
        `}
      >
        {isSubmitting
          ? "Saving…"
          : selectedTierIsTrial
            ? "Start free trial →"
            : selectedTierIsCharter
              ? "Join Charter →"
              : "Continue →"}
      </button>
    </div>
  );
}
