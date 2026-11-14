/**
 * /trial-expired — Hard gate: trial expired paywall
 *
 * Location: apps/web/src/app/(authed)/trial-expired/page.tsx
 *
 * Design doc Decision 7: full-page hard gate; blocks all other routes.
 * The (authed) layout detects trial_expired=true and renders this page instead.
 * 402 global interceptor in providers.tsx also routes here.
 *
 * Token audit (Section H):
 *  - Headline: text-fault-700
 */

"use client";

import React, { useState } from "react";
import { TierPickerCard, StripePaymentForm } from "@pilot/ui";
import { apiClient } from "@pilot/shared-api";
import { useSubscriptionTiers } from "@/features/signup/hooks/useSubscriptionTiers";
import type { StripePaymentResult } from "@pilot/ui";

const STRIPE_PK =
  process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY ?? "pk_test_placeholder";
const TENANT_ID_PLACEHOLDER = ""; // In real use, from auth context

export default function TrialExpiredPage() {
  const [selectedTierId, setSelectedTierId] = useState<string | null>(null);
  const [clientSecret, setClientSecret] = useState<string | null>(null);
  const [paymentMethodId, setPaymentMethodId] = useState<string | null>(null);
  const [isConverting, setIsConverting] = useState(false);
  const [conversionError, setConversionError] = useState<string | null>(null);
  const [converted, setConverted] = useState(false);

  const { data: tiers, isLoading } = useSubscriptionTiers();

  const handleSelectTier = async (tierName: string) => {
    const tier = tiers?.find((t) => t.tier_name === tierName);
    if (!tier || tier.is_trial) return;

    setSelectedTierId(tier.tier_id);
    setPaymentMethodId(null);
    setConversionError(null);

    try {
      const res = await apiClient.post<{ client_secret: string }>(
        `/api/v1/signup/${TENANT_ID_PLACEHOLDER}/payment-intent`,
      );
      setClientSecret(res.data.client_secret);
    } catch {
      setConversionError("Couldn't load payment form. Please try again.");
    }
  };

  const handleStripeSuccess = (result: StripePaymentResult) => {
    setPaymentMethodId(result.paymentMethodId ?? null);
  };

  const handleConvert = async () => {
    if (!selectedTierId || !paymentMethodId) return;
    setIsConverting(true);
    setConversionError(null);
    try {
      await apiClient.post(
        `/api/v1/tenants/${TENANT_ID_PLACEHOLDER}/subscription/convert-from-trial`,
        {
          stripe_payment_method_id: paymentMethodId,
          selected_tier_id: selectedTierId,
        },
      );
      setConverted(true);
      // Reload to get fresh auth context
      window.location.replace("/dashboard");
    } catch {
      setConversionError("Couldn't process your upgrade. Please try again.");
      setIsConverting(false);
    }
  };

  const selectedTier = tiers?.find((t) => t.tier_id === selectedTierId);

  if (converted) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-neutral-50">
        <div className="text-center">
          <p className="text-base font-medium text-margin-600">
            ✓ Upgrade complete — loading your dashboard…
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      className="min-h-screen bg-neutral-50 flex flex-col items-center justify-start px-4 py-12"
      data-testid="trial-expired-page"
    >
      <div className="w-full max-w-2xl flex flex-col gap-8">
        {/* Header */}
        <div className="text-center flex flex-col gap-3">
          <div className="text-4xl" aria-hidden="true">
            ⏰
          </div>
          <h1
            className="text-2xl font-bold text-fault-700"
            data-testid="trial-expired-headline"
          >
            Your trial has ended
          </h1>
          <p className="text-sm text-neutral-600 max-w-md mx-auto">
            Pick a plan to keep using Pilot. Your data is preserved — pick up
            right where you left off.
          </p>
        </div>

        {/* Tier picker */}
        {isLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="animate-pulse rounded-xl border-2 border-neutral-200 bg-neutral-100 h-56"
              />
            ))}
          </div>
        ) : (
          <div
            role="radiogroup"
            aria-label="Select plan to upgrade"
            className="grid grid-cols-1 sm:grid-cols-3 gap-4"
          >
            {(tiers ?? [])
              .filter((t) => !t.is_trial)
              .sort((a, b) => a.display_order - b.display_order)
              .map((tier) => (
                <TierPickerCard
                  key={tier.tier_id}
                  tierName={tier.tier_name}
                  displayName={tier.display_label}
                  monthlyPriceCents={tier.monthly_price_cents}
                  features={[
                    { label: "Voice quoting", included: true },
                    { label: "Job management", included: true },
                    { label: "QuickBooks sync", included: true },
                    { label: `Up to ${tier.max_users} users`, included: true },
                  ]}
                  isFeatured={tier.tier_name === "starter"}
                  isSelected={selectedTierId === tier.tier_id}
                  onSelect={handleSelectTier}
                  testID={`expired-tier-card-${tier.tier_name}`}
                />
              ))}
          </div>
        )}

        {/* Inline Stripe form */}
        {selectedTier && clientSecret && (
          <div className="rounded-xl border border-neutral-200 bg-white p-5 flex flex-col gap-3">
            <h2 className="text-sm font-semibold text-neutral-900">
              Payment method
            </h2>
            <StripePaymentForm
              stripePublishableKey={STRIPE_PK}
              clientSecret={clientSecret}
              mode="subscription"
              submitLabel="Save payment method"
              onSuccess={handleStripeSuccess}
              onError={(err) => setConversionError(err.message)}
              testID="expired-stripe-form"
            />
          </div>
        )}

        {conversionError && (
          <p role="alert" className="text-fault-600 text-sm text-center">
            {conversionError}
          </p>
        )}

        {paymentMethodId && selectedTier && (
          <button
            type="button"
            onClick={handleConvert}
            disabled={isConverting}
            data-testid="trial-expired-upgrade-button"
            className={`
              w-full py-3 px-6 rounded-lg text-sm font-semibold transition-colors
              focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2
              ${
                isConverting
                  ? "opacity-40 cursor-not-allowed bg-brand-600 text-white"
                  : "bg-brand-600 hover:bg-brand-800 text-white"
              }
            `}
          >
            {isConverting
              ? "Processing…"
              : `Upgrade to ${selectedTier.display_label}`}
          </button>
        )}
      </div>
    </div>
  );
}
