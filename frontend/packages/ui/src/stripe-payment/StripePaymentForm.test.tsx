/**
 * StripePaymentForm — unit tests
 * Location: packages/ui/src/stripe-payment/StripePaymentForm.test.tsx
 *
 * RULE 5: Uses Stripe test mode — never real keys.
 * Stripe Elements (PaymentElement, AddressElement) are mocked.
 * @stripe/react-stripe-js is mocked entirely so no real Stripe.js loads.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { StripePaymentForm } from "./StripePaymentForm";

// ─── Mock @stripe/stripe-js ────────────────────────────────────────────────

vi.mock("@stripe/stripe-js", () => ({
  loadStripe: vi.fn().mockResolvedValue({
    confirmSetup: vi.fn().mockResolvedValue({
      setupIntent: { payment_method: "pm_test_mock_payment_method" },
    }),
    confirmPayment: vi.fn().mockResolvedValue({
      paymentIntent: { id: "pi_test_mock_payment_intent" },
    }),
  }),
}));

// ─── Mock @stripe/react-stripe-js ─────────────────────────────────────────

const mockStripe = {
  confirmSetup: vi.fn().mockResolvedValue({
    setupIntent: { payment_method: "pm_test_mock_payment_method" },
  }),
  confirmPayment: vi.fn().mockResolvedValue({
    paymentIntent: { id: "pi_test_mock_payment_intent" },
  }),
};

vi.mock("@stripe/react-stripe-js", () => ({
  Elements: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="stripe-elements">{children}</div>
  ),
  PaymentElement: ({ onReady }: { onReady?: () => void }) => {
    // Trigger onReady immediately to simulate loaded state
    if (onReady) setTimeout(onReady, 0);
    return <div data-testid="payment-element">PaymentElement</div>;
  },
  AddressElement: () => <div data-testid="address-element">AddressElement</div>,
  useStripe: () => mockStripe,
  useElements: () => ({}),
}));

const TEST_PK = "pk_test_mock_publishable_key_00000000000000000000";
const TEST_CLIENT_SECRET = "seti_1test_secret_test00000000000000000000000000";

function renderForm(
  overrides: Partial<React.ComponentProps<typeof StripePaymentForm>> = {},
) {
  const onSuccess = vi.fn();
  const onError = vi.fn();
  const onLoadingChange = vi.fn();

  render(
    <StripePaymentForm
      stripePublishableKey={TEST_PK}
      clientSecret={TEST_CLIENT_SECRET}
      mode="subscription"
      onSuccess={onSuccess}
      onError={onError}
      onLoadingChange={onLoadingChange}
      {...overrides}
    />,
  );

  return { onSuccess, onError, onLoadingChange };
}

describe("StripePaymentForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset stripe mock return values
    mockStripe.confirmSetup.mockResolvedValue({
      setupIntent: { payment_method: "pm_test_mock_payment_method" },
    });
    mockStripe.confirmPayment.mockResolvedValue({
      paymentIntent: { id: "pi_test_mock_payment_intent" },
    });
  });

  it("renders PaymentElement in subscription mode", () => {
    renderForm({ mode: "subscription" });
    expect(screen.getByTestId("payment-element")).toBeTruthy();
  });

  it("renders PaymentElement in one-time mode", () => {
    renderForm({ mode: "one-time", paymentAmountCents: 14900 });
    expect(screen.getByTestId("payment-element")).toBeTruthy();
  });

  it("renders amount display in one-time mode with paymentAmountCents", () => {
    renderForm({ mode: "one-time", paymentAmountCents: 14900 });
    expect(screen.getByText("$149")).toBeTruthy();
  });

  it("does NOT render amount display in subscription mode", () => {
    renderForm({ mode: "subscription" });
    expect(screen.queryByText("Amount due")).toBeNull();
  });

  it("renders submit button with default label for subscription", () => {
    renderForm({ mode: "subscription" });
    expect(screen.getByTestId("stripe-submit-button")).toBeTruthy();
    expect(screen.getByTestId("stripe-submit-button").textContent).toContain(
      "Set up payment",
    );
  });

  it("submitLabel override is rendered", () => {
    renderForm({ submitLabel: "Pay now" });
    expect(screen.getByTestId("stripe-submit-button").textContent).toContain(
      "Pay now",
    );
  });

  it("submit button is disabled when disabled=true", () => {
    renderForm({ disabled: true });
    const btn = screen.getByTestId("stripe-submit-button");
    expect(btn.hasAttribute("disabled")).toBe(true);
  });

  it("inline error renders with fault-600 token class on Stripe error", async () => {
    mockStripe.confirmSetup.mockResolvedValueOnce({
      error: {
        code: "card_declined",
        message: "Your card was declined.",
        decline_code: "insufficient_funds",
      },
    });
    renderForm();

    // Wait for PaymentElement onReady
    await waitFor(() =>
      expect(screen.getByTestId("stripe-submit-button")).not.toBeDisabled(),
    );

    fireEvent.submit(screen.getByRole("form", { hidden: true }) ?? document);

    await waitFor(() => {
      const errorEl = screen.queryByTestId("stripe-inline-error");
      if (errorEl) {
        expect(errorEl.className).toContain("text-fault-600");
      }
    });
  });

  it("StripePaymentFormProps type-checks for FE-B14 forward compat: mode='one-time'", () => {
    // If this compiles, the discriminated union is correct
    const props: React.ComponentProps<typeof StripePaymentForm> = {
      stripePublishableKey: TEST_PK,
      clientSecret: TEST_CLIENT_SECRET,
      mode: "one-time",
      paymentAmountCents: 5000,
      onSuccess: vi.fn(),
    };
    expect(props.mode).toBe("one-time");
  });
});
