/**
 * ManualPaymentPanel — STRIPE-CONNECT-1-C
 *
 * Location: apps/web/src/features/public-invoice/ManualPaymentPanel.tsx
 *
 * Pure presentational panel shown on the public invoice page when the tenant
 * cannot accept card payments (cardPaymentsEnabled === false). Renders the
 * contractor's billing-contact phone/email so the customer can arrange payment
 * by check, card, or Zelle.
 *
 * Calm money-page mandate (spec §2.1): neutral tokens only, no fault color,
 * no alarm language, no "Powered by Stripe" caption. The contractor's business
 * must not look broken to their customer.
 *
 * Spec authority: mkt-stripe-connect-1-design-spec.md §6 (anatomy), §7 (copy),
 * §13 (accessibility). Implement token-for-token.
 *
 * RULE 1: No useAuth() — unauthenticated public surface.
 * No hooks, no fetch, no "use client" — renders identically at SSR and after hydration.
 */

import React from "react";
import { WalletIcon } from "@heroicons/react/24/outline";

interface ManualPaymentPanelProps {
  tenantName: string;
  tenantPhone: string | null;
  tenantEmail: string | null;
}

export function ManualPaymentPanel({
  tenantName,
  tenantPhone,
  tenantEmail,
}: ManualPaymentPanelProps) {
  const hasPhone = tenantPhone != null && tenantPhone !== "";
  const hasEmail = tenantEmail != null && tenantEmail !== "";
  const hasAnyContact = hasPhone || hasEmail;

  return (
    <section
      aria-label="Payment instructions"
      className="rounded-xl border border-neutral-200 bg-white p-6 shadow-sm"
      data-testid="manual-payment-panel"
    >
      <h3 className="text-h3 font-medium text-neutral-800 flex items-center gap-2">
        <WalletIcon
          className="h-4 w-4 text-neutral-400 mr-2 shrink-0"
          aria-hidden="true"
        />
        How to pay this invoice
      </h3>

      <p className="text-body text-neutral-600 mt-2">
        Contact {tenantName} to arrange payment by check, card, or Zelle.
      </p>

      {hasAnyContact ? (
        <>
          <hr className="border-neutral-200 my-4" />

          <div className="flex flex-col gap-3 sm:grid sm:grid-cols-2 sm:gap-6">
            {hasPhone && (
              <div className="space-y-1">
                <p className="text-caption text-neutral-600">Phone</p>
                <a
                  href={`tel:${tenantPhone}`}
                  className="inline-block py-1 text-body text-neutral-700 hover:text-neutral-900 underline focus-visible:outline-2 focus-visible:outline-brand-400 focus-visible:outline-offset-2 focus-visible:rounded-sm"
                  data-testid="manual-payment-phone-link"
                >
                  {tenantPhone}
                </a>
              </div>
            )}

            {hasEmail && (
              <div className="space-y-1">
                <p className="text-caption text-neutral-600">Email</p>
                <a
                  href={`mailto:${tenantEmail}`}
                  className="inline-block py-1 text-body text-neutral-700 hover:text-neutral-900 underline focus-visible:outline-2 focus-visible:outline-brand-400 focus-visible:outline-offset-2 focus-visible:rounded-sm"
                  data-testid="manual-payment-email-link"
                >
                  {tenantEmail}
                </a>
              </div>
            )}
          </div>
        </>
      ) : (
        <p className="text-body text-neutral-600 mt-4">
          Please reach out to {tenantName} to arrange payment.
        </p>
      )}
    </section>
  );
}
