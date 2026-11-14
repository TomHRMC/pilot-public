/**
 * TrialConversionModal — Soft-gate upgrade modal
 *
 * Location: apps/web/src/features/onboarding/components/TrialConversionModal.tsx
 *
 * Design doc Decision 7: modal overlay with TierPickerCard grid + StripePaymentForm.
 * Reuses TierPickerCard (isCurrentTier on trial card).
 * On successful conversion: modal dismisses; parent should invalidate auth context.
 */

"use client";

import React, { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { TierPickerCard, StripePaymentForm } from "@pilot/ui";
import { apiClient } from "@pilot/shared-api";
import {
  useSubscriptionTiers,
  getRecommendedTierName,
} from "@/features/signup/hooks/useSubscriptionTiers";
import type { StripePaymentResult } from "@pilot/ui";

const STRIPE_PK =
  process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY ?? "pk_test_placeholder";

interface TrialConversionModalProps {
  tenantId: string;
  isOpen: boolean;
  onClose: () => void;
  onConverted: () => void;
  /** Tenant's current trial tier ID (to mark isCurrentTier) */
  currentTierName?: string;
}

export function TrialConversionModal({
  tenantId,
  isOpen,
  onClose,
  onConverted,
  currentTierName = "trial",
}: TrialConversionModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [selectedTierId, setSelectedTierId] = useState<string | null>(null);
  const [paymentMethodId, setPaymentMethodId] = useState<string | null>(null);
  const [isConverting, setIsConverting] = useState(false);
  const [conversionError, setConversionError] = useState<string | null>(null);

  const { data: tiers, isLoading } = useSubscriptionTiers();

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (isOpen && !dialog.open) {
      dialog.showModal();
    } else if (!isOpen && dialog.open) {
      dialog.close();
    }
  }, [isOpen]);

  // useQuery fetches payment intent — no setState in effect
  const { data: paymentIntentData } = useQuery({
    queryKey: ["conversion-payment-intent", tenantId, selectedTierId],
    queryFn: async () => {
      const res = await apiClient.post<{ client_secret: string }>(
        `/api/v1/signup/${tenantId}/payment-intent`,
      );
      return res.data;
    },
    enabled: !!tenantId && !!selectedTierId,
    staleTime: 10 * 60 * 1000,
  });

  const clientSecret = paymentIntentData?.client_secret ?? null;

  const handleSelectTier = (tierName: string) => {
    const tier = tiers?.find((t) => t.tier_name === tierName);
    if (tier && !tier.is_trial) {
      setSelectedTierId(tier.tier_id);
      setPaymentMethodId(null);
      setConversionError(null);
    }
  };

  const handleStripeSuccess = (result: StripePaymentResult) => {
    setPaymentMethodId(result.paymentMethodId ?? null);
  };

  const handleConvert = async () => {
    if (!selectedTierId || !paymentMethodId || !tenantId) return;
    setIsConverting(true);
    setConversionError(null);
    try {
      await apiClient.post(
        `/api/v1/tenants/${tenantId}/subscription/convert-from-trial`,
        {
          stripe_payment_method_id: paymentMethodId,
          selected_tier_id: selectedTierId,
        },
      );
      onConverted();
    } catch {
      setConversionError("Couldn't process your upgrade. Please try again.");
    } finally {
      setIsConverting(false);
    }
  };

  const selectedTier = tiers?.find((t) => t.tier_id === selectedTierId);
  const recommendedTierName = getRecommendedTierName("small");

  return (
    <dialog
      ref={dialogRef}
      data-testid="trial-conversion-modal"
      className="backdrop:bg-black/50 rounded-2xl shadow-2xl p-0 w-full max-w-2xl max-h-[90vh] overflow-y-auto"
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-100 sticky top-0 bg-white z-10">
        <h2 className="text-lg font-semibold text-neutral-900">
          Choose your plan
        </h2>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close upgrade modal"
          data-testid="trial-modal-close"
          className="text-neutral-400 hover:text-neutral-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 rounded"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            viewBox="0 0 20 20"
            aria-hidden="true"
          >
            <path
              d="M4 4l12 12M16 4L4 16"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
            />
          </svg>
        </button>
      </div>

      <div className="px-6 py-6 flex flex-col gap-6">
        {isLoading ? (
          <div className="grid grid-cols-2 gap-4">
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
            aria-label="Upgrade plan selection"
            className="grid grid-cols-1 sm:grid-cols-3 gap-4"
          >
            {(tiers ?? [])
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
                    {
                      label: "QuickBooks sync",
                      included: tier.tier_name !== "trial",
                    },
                    { label: `Up to ${tier.max_users} users`, included: true },
                  ]}
                  isFeatured={tier.tier_name === recommendedTierName}
                  isTrialTier={tier.is_trial}
                  trialDurationDays={tier.trial_duration_days ?? undefined}
                  isCurrentTier={tier.tier_name === currentTierName}
                  isSelected={selectedTierId === tier.tier_id}
                  onSelect={handleSelectTier}
                  testID={`modal-tier-card-${tier.tier_name}`}
                />
              ))}
          </div>
        )}

        {/* Stripe form when paid tier selected */}
        {selectedTier && clientSecret && (
          <div className="rounded-xl border border-neutral-200 bg-white p-5 flex flex-col gap-3">
            <h3 className="text-sm font-semibold text-neutral-900">
              Payment method
            </h3>
            <StripePaymentForm
              stripePublishableKey={STRIPE_PK}
              clientSecret={clientSecret}
              mode="subscription"
              submitLabel="Save payment method"
              onSuccess={handleStripeSuccess}
              onError={(err) => setConversionError(err.message)}
              testID="conversion-stripe-form"
            />
          </div>
        )}

        {conversionError && (
          <p role="alert" className="text-fault-600 text-sm">
            {conversionError}
          </p>
        )}

        {/* Confirm upgrade button */}
        {paymentMethodId && selectedTier && (
          <button
            type="button"
            onClick={handleConvert}
            disabled={isConverting}
            data-testid="trial-modal-confirm-button"
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
    </dialog>
  );
}
