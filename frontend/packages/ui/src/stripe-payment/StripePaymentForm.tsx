/**
 * StripePaymentForm — FE-B13 (RULE 1: single Stripe Elements boundary)
 *
 * Location: packages/ui/src/stripe-payment/StripePaymentForm.tsx
 *
 * CRITICAL ARCHITECTURE RULES:
 *  - This is the ONLY component that may import from @stripe/react-stripe-js
 *  - Owns the <Elements> provider internally — consumers NEVER wrap with <Elements>
 *  - Consumers pass stripePublishableKey; loadStripe() is memoized by Stripe.js SDK
 *  - Both 'subscription' and 'one-time' modes use PaymentElement
 *
 * LOCKED INTERFACE for FE-B14 (see packages/ui/src/stripe-payment/types.ts)
 *
 * FE-B13: subscription mode (wizard step 4 + trial conversion)
 * FE-B14: one-time mode (public invoice payment link) — additive extension only
 *
 * Token requirements (Section H):
 *  - Submit button: bg-brand-600 hover:bg-brand-800 text-white
 *  - Error text: text-fault-600 text-sm mt-1
 */

"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { loadStripe } from "@stripe/stripe-js";
import {
  Elements,
  PaymentElement,
  AddressElement,
  useStripe,
  useElements,
} from "@stripe/react-stripe-js";
import type {
  StripePaymentFormProps,
  StripePaymentResult,
  StripePaymentError,
} from "./types";

// ─── Inner form — rendered inside <Elements> context ─────────────────────────

interface StripePaymentFormInnerProps {
  mode: StripePaymentFormProps["mode"];
  paymentAmountCents?: number;
  submitLabel?: string;
  onSuccess: (result: StripePaymentResult) => void;
  onError?: (error: StripePaymentError) => void;
  onLoadingChange?: (isLoading: boolean) => void;
  disabled?: boolean;
  testID?: string;
}

function StripePaymentFormInner({
  mode,
  paymentAmountCents,
  submitLabel,
  onSuccess,
  onError,
  onLoadingChange,
  disabled = false,
  testID,
}: StripePaymentFormInnerProps) {
  const stripe = useStripe();
  const elements = useElements();
  const [inlineError, setInlineError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isReady, setIsReady] = useState(false);

  const resolvedSubmitLabel =
    submitLabel ?? (mode === "subscription" ? "Set up payment" : "Pay");

  useEffect(() => {
    onLoadingChange?.(!isReady || isSubmitting);
  }, [isReady, isSubmitting, onLoadingChange]);

  const handleSubmit = useCallback(
    async (e: React.FormEvent<HTMLFormElement>) => {
      e.preventDefault();
      if (!stripe || !elements || isSubmitting || disabled) return;

      setIsSubmitting(true);
      setInlineError(null);
      onLoadingChange?.(true);

      try {
        let result;
        if (mode === "subscription") {
          result = await stripe.confirmSetup({
            elements,
            confirmParams: {
              return_url: `${typeof window !== "undefined" ? window.location.origin : ""}/signup/ready`,
            },
            redirect: "if_required",
          });
        } else {
          result = await stripe.confirmPayment({
            elements,
            confirmParams: {
              return_url: `${typeof window !== "undefined" ? window.location.origin : ""}/payment/success`,
            },
            redirect: "if_required",
          });
        }

        if (result.error) {
          const stripeErr: StripePaymentError = {
            code: result.error.code ?? "stripe_error",
            message: result.error.message ?? "An error occurred.",
            declineCode: result.error.decline_code,
          };
          setInlineError(stripeErr.message);
          onError?.(stripeErr);
        } else {
          // Extract payment method or intent ID from confirmed result
          const paymentResult: StripePaymentResult = {};
          if ("setupIntent" in result && result.setupIntent) {
            const pmId = result.setupIntent.payment_method;
            if (typeof pmId === "string") {
              paymentResult.paymentMethodId = pmId;
            }
          }
          if ("paymentIntent" in result && result.paymentIntent) {
            paymentResult.paymentIntentId = result.paymentIntent.id;
          }
          onSuccess(paymentResult);
        }
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "An unexpected error occurred.";
        const stripeErr: StripePaymentError = {
          code: "unexpected_error",
          message,
        };
        setInlineError(message);
        onError?.(stripeErr);
      } finally {
        setIsSubmitting(false);
        onLoadingChange?.(false);
      }
    },
    [
      stripe,
      elements,
      isSubmitting,
      disabled,
      mode,
      onSuccess,
      onError,
      onLoadingChange,
    ],
  );

  const isButtonDisabled =
    !stripe || !elements || !isReady || isSubmitting || disabled;

  return (
    <form
      onSubmit={handleSubmit}
      data-testid={testID ?? "stripe-payment-form"}
      aria-label="Payment form"
    >
      {/* Payment method collection */}
      <div className="mb-4">
        <PaymentElement
          onReady={() => setIsReady(true)}
          options={{
            layout: "tabs",
          }}
        />
      </div>

      {/* Billing address */}
      <div className="mb-4">
        <AddressElement options={{ mode: "billing" }} />
      </div>

      {/* Amount display (one-time mode only) */}
      {mode === "one-time" && paymentAmountCents !== undefined && (
        <div className="mb-4 flex items-center justify-between rounded-lg bg-neutral-50 px-4 py-3">
          <span className="text-sm text-neutral-600">Amount due</span>
          <span className="text-base font-semibold text-neutral-900">
            {formatCentsForDisplay(paymentAmountCents)}
          </span>
        </div>
      )}

      {/* Inline error (fault-600 token — Section H) */}
      {inlineError && (
        <p
          role="alert"
          data-testid="stripe-inline-error"
          className="text-fault-600 text-sm mt-1 mb-3"
        >
          {inlineError}
        </p>
      )}

      {/* Submit button (brand tokens — Section H) */}
      <button
        type="submit"
        disabled={isButtonDisabled}
        data-testid="stripe-submit-button"
        className={`
          w-full py-3 px-6 rounded-lg text-sm font-semibold
          transition-colors focus:outline-none focus-visible:ring-2
          focus-visible:ring-brand-600 focus-visible:ring-offset-2
          ${
            isButtonDisabled
              ? "opacity-40 cursor-not-allowed bg-brand-600 text-white"
              : "bg-brand-600 hover:bg-brand-800 text-white"
          }
        `}
      >
        {isSubmitting ? (
          <span className="flex items-center justify-center gap-2">
            <svg
              className="animate-spin h-4 w-4 text-white"
              fill="none"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
            Processing…
          </span>
        ) : (
          resolvedSubmitLabel
        )}
      </button>
    </form>
  );
}

// ─── Outer wrapper — owns the Elements provider ───────────────────────────────

/**
 * StripePaymentForm
 *
 * RULE 1 enforcement: this component is the SINGLE Stripe Elements boundary.
 * No other component in the codebase may import from @stripe/react-stripe-js.
 *
 * @example Subscription mode (wizard step 4)
 * <StripePaymentForm
 *   stripePublishableKey={process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY!}
 *   clientSecret={paymentIntentClientSecret}
 *   mode="subscription"
 *   onSuccess={(result) => handlePaymentSuccess(result)}
 *   onError={(err) => console.error(err)}
 * />
 *
 * @example One-time mode (FE-B14 invoice payment)
 * <StripePaymentForm
 *   stripePublishableKey={process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY!}
 *   clientSecret={invoicePaymentIntentClientSecret}
 *   mode="one-time"
 *   paymentAmountCents={14900}
 *   submitLabel="Pay $149"
 *   onSuccess={(result) => handleInvoicePaid(result)}
 * />
 */
export function StripePaymentForm({
  stripePublishableKey,
  clientSecret,
  mode,
  paymentAmountCents,
  submitLabel,
  onSuccess,
  onError,
  onLoadingChange,
  disabled,
  testID,
}: StripePaymentFormProps) {
  // loadStripe is memoized by the Stripe.js SDK — passing the same key returns
  // the same Promise. This is safe to call on each render.
  const stripePromise = useMemo(
    () => loadStripe(stripePublishableKey),
    [stripePublishableKey],
  );

  const elementsOptions = useMemo(
    () => ({
      clientSecret,
      appearance: {
        theme: "stripe" as const,
        variables: {
          // Map Stripe's CSS variables to our brand tokens at runtime
          colorPrimary: "var(--color-brand-600)",
          colorDanger: "var(--color-fault-600)",
          borderRadius: "0.5rem",
          fontFamily: "var(--font-sans, system-ui, sans-serif)",
        },
      },
    }),
    [clientSecret],
  );

  return (
    <Elements stripe={stripePromise} options={elementsOptions}>
      <StripePaymentFormInner
        mode={mode}
        paymentAmountCents={paymentAmountCents}
        submitLabel={submitLabel}
        onSuccess={onSuccess}
        onError={onError}
        onLoadingChange={onLoadingChange}
        disabled={disabled}
        testID={testID}
      />
    </Elements>
  );
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatCentsForDisplay(cents: number): string {
  const dollars = Math.floor(cents / 100);
  const remaining = cents % 100;
  if (remaining === 0) return `$${dollars}`;
  return `$${dollars}.${String(remaining).padStart(2, "0")}`;
}
