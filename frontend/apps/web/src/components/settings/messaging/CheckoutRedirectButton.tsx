"use client";

/**
 * CheckoutRedirectButton — C-B9
 *
 * Location: apps/web/src/components/settings/messaging/CheckoutRedirectButton.tsx
 *
 * "Continue to payment" button → calls useCreateCheckout mutation →
 * redirects to Stripe Checkout URL.
 *
 * UI spec §4.5. WCAG 2.2 AA: ≥44px target, aria-label, aria-busy.
 * RULE 5: zero hex codes. RULE 11: no hand-memo.
 */

import React from "react";
import { ArrowRightIcon } from "@heroicons/react/24/outline";
import { useCreateCheckout } from "@/features/messaging/hooks/useCreateCheckout";
import { useNotificationQueue } from "@pilot/ui";

export function CheckoutRedirectButton() {
  const createCheckout = useCreateCheckout();
  const { addNotification } = useNotificationQueue();

  async function handleClick() {
    try {
      const result = await createCheckout.mutateAsync();
      // Full page redirect to Stripe Checkout
      window.location.href = result.checkout_url;
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response
        ?.status;
      if (status === 409) {
        addNotification({
          id: `checkout-409-${Date.now()}`,
          severity: "error",
          title:
            "Quote expired or setup already in progress. Refresh the page.",
        });
      } else {
        addNotification({
          id: `checkout-err-${Date.now()}`,
          severity: "error",
          title: "Payment system unavailable. Please try again in a moment.",
        });
      }
    }
  }

  const isPending = createCheckout.isPending;

  return (
    <div className="mt-4" data-testid="checkout-redirect">
      <button
        type="button"
        onClick={() => void handleClick()}
        disabled={isPending}
        aria-label="Continue to Stripe payment"
        aria-busy={isPending}
        className="w-full bg-brand-600 text-white rounded-md px-4 py-3 text-sm font-medium hover:bg-brand-700 transition-colors focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:outline-none active:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        data-testid="checkout-redirect-button"
      >
        {isPending ? "Redirecting to Stripe..." : "Continue to Payment"}
        {!isPending && <ArrowRightIcon className="w-5 h-5" />}
      </button>
      <p className="text-xs text-neutral-500 mt-2 text-center">
        You will be redirected to Stripe to complete payment securely. Your card
        is charged upon submission — this is how the carrier bills us.
      </p>
    </div>
  );
}
