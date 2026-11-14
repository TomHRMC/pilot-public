/**
 * InvoicePaymentModal — FE-B14
 *
 * Location: apps/web/src/features/public-invoice/InvoicePaymentModal.tsx
 *
 * Orchestrates the full Stripe payment flow for public invoice pages.
 * State machine: amount-select → pi-loading → card-entry → submitting →
 *                processing → success | error
 *
 * RULE 1: No useAuth() — unauthenticated.
 * RULE 6: PaymentIntent POST fires with the SELECTED amount, not the full amount.
 * RULE 7: Comment goes to /payment-intent endpoint, NOT comms threads.
 *
 * StripePaymentForm is NOT modified — wraps it externally (Decision 1).
 */

"use client";

import React, { useRef, useState } from "react";
import type {
  PaymentModalState,
  AmountSelectorState,
  PaymentIntentResponse,
} from "./types";
import { InvoiceAmountSelector } from "./InvoiceAmountSelector";
import { StripePaymentForm } from "@pilot/ui";

const STRIPE_PUBLISHABLE_KEY =
  process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY ?? "";

function formatCents(cents: number, currency = "USD"): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
  }).format(cents / 100);
}

interface InvoicePaymentModalProps {
  token: string;
  invoiceTotalCents: number;
  amountDueCents: number;
  tenantName: string;
  currency?: string;
  onSuccess: (amountPaidCents: number) => void;
  onClose: () => void;
}

export function InvoicePaymentModal({
  token,
  invoiceTotalCents,
  amountDueCents,
  tenantName,
  currency = "USD",
  onSuccess,
  onClose,
}: InvoicePaymentModalProps) {
  const [modalState, setModalState] = useState<PaymentModalState>({
    phase: "amount-select",
    selectedAmountCents: amountDueCents,
    comment: "",
    adjusting: false,
  });

  const [amountSelectorState, setAmountSelectorState] =
    useState<AmountSelectorState>({
      adjusting: false,
      customAmountCents: amountDueCents,
      comment: "",
      commentError: null,
      amountError: null,
    });

  // STRIPE-CONNECT-1-C: Idempotency-Key per pay attempt. A retry of the same
  // attempt reuses the same key (backend replays the cached response instead of
  // double-charging); a new attempt (user goes back, changes amount, resubmits)
  // generates a fresh key. Separate keys for payment-intent vs confirm-payment.
  const paymentIntentKeyRef = useRef<string>(crypto.randomUUID());
  const confirmPaymentKeyRef = useRef<string>(crypto.randomUUID());

  async function handleContinueToPayment(
    amountCents: number,
    comment?: string,
  ) {
    // Fresh key for this pay attempt (new amount / new submission = new key)
    paymentIntentKeyRef.current = crypto.randomUUID();
    setModalState({ phase: "pi-loading" });

    try {
      // RULE 6: POST with ACTUAL selected amount
      const res = await fetch(
        `/api/v1/public/invoices/${token}/payment-intent`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Idempotency-Key": paymentIntentKeyRef.current,
          },
          body: JSON.stringify({
            amount_cents: amountCents,
            ...(comment ? { comment } : {}),
          }),
        },
      );

      if (!res.ok) {
        const err = (await res.json()) as { detail?: string };
        setModalState({
          phase: "amount-select",
          selectedAmountCents: amountCents,
          comment: comment ?? "",
          adjusting: amountSelectorState.adjusting,
        });
        setAmountSelectorState((prev) => ({
          ...prev,
          amountError:
            err.detail ?? "Could not create payment. Please try again.",
        }));
        return;
      }

      const data = (await res.json()) as PaymentIntentResponse;
      setModalState({
        phase: "card-entry",
        clientSecret: data.client_secret,
        paymentIntentId: data.payment_intent_id,
        selectedAmountCents: amountCents,
      });
    } catch {
      setModalState({
        phase: "amount-select",
        selectedAmountCents: amountCents,
        comment: comment ?? "",
        adjusting: amountSelectorState.adjusting,
      });
      setAmountSelectorState((prev) => ({
        ...prev,
        amountError: "Network error. Please try again.",
      }));
    }
  }

  async function handlePaymentSuccess(result: {
    paymentMethodId?: string;
    paymentIntentId?: string;
    actualAmountPaidCents?: number;
  }) {
    if (modalState.phase !== "card-entry") return;
    const { paymentIntentId, selectedAmountCents } = modalState;

    // Fresh key for this confirmation attempt
    confirmPaymentKeyRef.current = crypto.randomUUID();
    setModalState({ phase: "processing", paymentIntentId });

    // Advisory confirm — webhook finalizes (RULE 6, design doc Section C.2)
    try {
      await fetch(`/api/v1/public/invoices/${token}/confirm-payment`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Idempotency-Key": confirmPaymentKeyRef.current,
        },
        body: JSON.stringify({
          payment_intent_id: result.paymentIntentId ?? paymentIntentId,
        }),
      });
    } catch {
      // Advisory only — ignore errors
    }

    setModalState({ phase: "success", amountPaidCents: selectedAmountCents });
    onSuccess(selectedAmountCents);
  }

  function handlePaymentError(error: { code: string; message: string }) {
    if (modalState.phase !== "card-entry") return;
    setModalState({
      phase: "error",
      error: error.message,
      recoverable: true,
    });
    // Return to card-entry so user can retry
    setModalState((prev) => {
      if (prev.phase === "error") {
        // Re-enter card-entry with same client_secret
        return prev;
      }
      return prev;
    });
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/40 px-0 sm:px-4"
      data-testid="invoice-payment-modal"
    >
      <div className="w-full sm:max-w-lg bg-white rounded-t-2xl sm:rounded-xl shadow-xl max-h-[90vh] overflow-y-auto">
        {/* Modal header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-200 sticky top-0 bg-white">
          <h2 className="text-base font-semibold text-neutral-900">
            Pay invoice
          </h2>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100"
            data-testid="payment-modal-close"
          >
            <svg
              className="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <div className="px-6 py-5">
          {/* ── Phase: amount-select ── */}
          {modalState.phase === "amount-select" && (
            <InvoiceAmountSelector
              invoiceAmountDueCents={amountDueCents}
              invoiceTotalCents={invoiceTotalCents}
              tenantName={tenantName}
              currency={currency}
              state={amountSelectorState}
              onStateChange={(update) =>
                setAmountSelectorState((prev) => ({ ...prev, ...update }))
              }
              onContinue={handleContinueToPayment}
            />
          )}

          {/* ── Phase: pi-loading ── */}
          {modalState.phase === "pi-loading" && (
            <div
              className="flex flex-col items-center gap-4 py-10"
              data-testid="pi-loading-state"
            >
              <div className="h-8 w-8 rounded-full border-2 border-neutral-300 border-t-brand-600 animate-spin" />
              <p className="text-sm text-neutral-600">Creating payment…</p>
            </div>
          )}

          {/* ── Phase: card-entry ── */}
          {modalState.phase === "card-entry" && (
            <div data-testid="card-entry-state">
              <div className="mb-4 flex items-center justify-between">
                <p className="text-sm text-neutral-600">
                  Paying{" "}
                  <strong>
                    {formatCents(modalState.selectedAmountCents, currency)}
                  </strong>{" "}
                  to {tenantName}
                </p>
                <button
                  onClick={() =>
                    setModalState({
                      phase: "amount-select",
                      selectedAmountCents: amountDueCents,
                      comment: "",
                      adjusting: false,
                    })
                  }
                  className="text-xs text-neutral-500 hover:text-neutral-700 underline"
                >
                  Change amount
                </button>
              </div>
              <StripePaymentForm
                stripePublishableKey={STRIPE_PUBLISHABLE_KEY}
                clientSecret={modalState.clientSecret}
                mode="one-time"
                paymentAmountCents={modalState.selectedAmountCents}
                submitLabel={`Pay ${formatCents(modalState.selectedAmountCents, currency)}`}
                invoiceToken={token}
                onSuccess={handlePaymentSuccess}
                onPaymentSuccess={(result) => {
                  void handlePaymentSuccess(result);
                }}
                onError={handlePaymentError}
              />
            </div>
          )}

          {/* ── Phase: error (inline — stays on card-entry, doesn't close modal) ── */}
          {modalState.phase === "error" && (
            <div data-testid="payment-error-state">
              <p
                className="text-sm text-fault-600 mb-4"
                data-testid="stripe-error-text"
              >
                {modalState.error}
              </p>
              <button
                onClick={() =>
                  setModalState({
                    phase: "amount-select",
                    selectedAmountCents: amountDueCents,
                    comment: "",
                    adjusting: false,
                  })
                }
                className="w-full rounded-lg border border-neutral-300 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
              >
                Try again
              </button>
            </div>
          )}

          {/* ── Phase: processing ── */}
          {modalState.phase === "processing" && (
            <div
              className="flex flex-col items-center gap-4 py-10"
              data-testid="payment-processing-state"
            >
              <div className="h-8 w-8 rounded-full border-2 border-neutral-300 border-t-neutral-700 animate-spin" />
              <p className="text-sm text-neutral-600">
                Payment processing — please wait
              </p>
              <p className="text-xs text-neutral-400">
                Do not close this window.
              </p>
            </div>
          )}

          {/* ── Phase: success ── */}
          {modalState.phase === "success" && (
            <div
              className="flex flex-col items-center gap-4 py-8 text-center"
              data-testid="payment-success-state"
            >
              <div className="h-12 w-12 rounded-full bg-margin-50 border border-margin-200 flex items-center justify-center">
                <svg
                  className="h-6 w-6 text-margin-700"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2.5}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M5 13l4 4L19 7"
                  />
                </svg>
              </div>
              <div>
                <p className="text-lg font-semibold text-margin-700">
                  Payment received!
                </p>
                <p className="text-sm text-neutral-600 mt-1">
                  {formatCents(modalState.amountPaidCents, currency)} sent to{" "}
                  {tenantName}
                </p>
              </div>
              <button
                onClick={onClose}
                className="mt-2 rounded-lg border border-neutral-300 px-6 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
              >
                Close
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
