/**
 * StripePaymentForm Types — FE-B13 (extended by FE-B14)
 *
 * Location: packages/ui/src/stripe-payment/types.ts
 *
 * FE-B13: Base locked interface (subscription mode).
 * FE-B14: Additive-only extension — two optional props for invoice context.
 *         StripePaymentForm.tsx itself is NOT modified.
 *
 * DOWNSTREAM CONTRACT: See design doc Section I.1.
 *   - No required props may be added.
 *   - No existing prop signatures may change.
 *   - FE-B13 subscription-mode usages remain completely unaffected.
 */

export type StripePaymentMode = "subscription" | "one-time";

export interface StripePaymentFormProps {
  // ─── FE-B13 LOCKED PROPS ─────────────────────────────────────────────────

  /** Stripe publishable key (from env). loadStripe() is memoized internally. */
  stripePublishableKey: string;
  /** Backend-provided client secret (SetupIntent or PaymentIntent client_secret) */
  clientSecret: string;
  /** Mode determines which Stripe flow is used */
  mode: StripePaymentMode;
  /** Amount in cents — required for 'one-time' mode; ignored for 'subscription' */
  paymentAmountCents?: number;
  /**
   * Submit button label.
   * Defaults: 'Set up payment' for subscription, 'Pay' for one-time.
   */
  submitLabel?: string;
  /** Called on successful Stripe payment confirmation */
  onSuccess: (result: StripePaymentResult) => void;
  /** Called on Stripe error (card declined, insufficient funds, etc.) */
  onError?: (error: StripePaymentError) => void;
  /** Loading state callback: true when Elements loading or submit in-flight */
  onLoadingChange?: (isLoading: boolean) => void;
  /** Externally disable the submit button */
  disabled?: boolean;
  testID?: string;

  // ─── FE-B14 ADDITIONS (optional — one-time mode invoice context only) ────
  // These props are ONLY relevant to public invoice payment pages.
  // Subscription-mode (FE-B13) usages that omit these props are unaffected.

  /**
   * Invoice signed token — used for constructing return_url on redirect flows.
   * Only relevant when mode='one-time'.
   */
  invoiceToken?: string;
  /**
   * Additional callback with actual amount paid — for invoice payment reconciliation.
   * When provided, fires alongside onSuccess with the confirmed PaymentIntent amount.
   * Subscription-mode usages that omit this prop behave identically to before.
   */
  onPaymentSuccess?: (
    result: StripePaymentResult & { actualAmountPaidCents: number },
  ) => void;
}

export interface StripePaymentResult {
  paymentMethodId?: string;
  paymentIntentId?: string;
}

export interface StripePaymentError {
  code: string;
  message: string;
  declineCode?: string;
}
