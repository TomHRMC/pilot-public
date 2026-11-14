/**
 * PublicInvoicePage — FE-B14
 *
 * Location: apps/web/src/features/public-invoice/PublicInvoicePage.tsx
 *
 * Client component orchestrating the public invoice page.
 *
 * RULE 1 — CRITICAL: NEVER calls useAuth(), RequireAuth, or RoleGate.
 * RULE 4: Signed URL is the ONLY authentication.
 * RULE 5: Tenant brand color applied as CSS custom property.
 * RULE 6: PaymentIntent created with ACTUAL chosen amount.
 */

"use client";

import React, { useCallback, useEffect, useState } from "react";
import { parseProblemBody } from "@pilot/shared-api";
import type { PublicInvoiceData } from "./types";
import { normalizeInvoiceData } from "./types";
import type { ExpiredLinkMeta } from "../public-quote/types";
import { TenantBrandedHeader } from "../public-quote/TenantBrandedHeader";
import { PoweredByPilotFooter } from "../public-quote/PoweredByPilotFooter";
import { QuoteLineItemsTable } from "../public-quote/QuoteLineItemsTable";
import { QuoteExpiredPage } from "../public-quote/QuoteExpiredPage";
import { InvoicePaidState } from "./InvoicePaidState";
import { InvoicePartialPaidState } from "./InvoicePartialPaidState";
import { InvoicePaymentModal } from "./InvoicePaymentModal";
import { ManualPaymentPanel } from "./ManualPaymentPanel";

function formatCents(cents: number, currency = "USD"): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
  }).format(cents / 100);
}

type PageState =
  | { phase: "loading" }
  | { phase: "error-expired"; meta?: ExpiredLinkMeta }
  | { phase: "error-invalid" }
  | { phase: "error-generic"; message: string }
  | { phase: "ready"; invoice: PublicInvoiceData };

interface PublicInvoicePageProps {
  token: string;
}

export function PublicInvoicePage({ token }: PublicInvoicePageProps) {
  const [pageState, setPageState] = useState<PageState>({ phase: "loading" });
  const [showPaymentModal, setShowPaymentModal] = useState(false);

  const fetchInvoice = useCallback(async () => {
    try {
      const res = await fetch(`/api/v1/public/invoices/${token}`);

      if (res.status === 410) {
        const data = (await res.json()) as {
          tenant_name?: string;
          tenant_phone?: string;
          tenant_email?: string;
        };
        setPageState({
          phase: "error-expired",
          meta: {
            tenantName: data.tenant_name,
            tenantPhone: data.tenant_phone,
            tenantEmail: data.tenant_email,
          },
        });
        return;
      }

      if (res.status === 401 || res.status === 404) {
        setPageState({ phase: "error-invalid" });
        return;
      }

      if (!res.ok) {
        const errorData = (await res.json().catch(() => null)) as unknown;
        const problem = parseProblemBody(res.status, errorData);
        setPageState({
          phase: "error-generic",
          message: problem.detail ?? `Error ${res.status}`,
        });
        return;
      }

      const data = (await res.json()) as Record<string, unknown>;
      const invoice = normalizeInvoiceData(data);
      setPageState({ phase: "ready", invoice });
    } catch {
      setPageState({
        phase: "error-generic",
        message: "Could not load invoice. Check your connection and try again.",
      });
    }
  }, [token]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void fetchInvoice();
  }, [fetchInvoice]);

  function handlePaymentSuccess() {
    setShowPaymentModal(false);
    void fetchInvoice(); // Re-fetch to show updated status
  }

  // ─── Loading ──────────────────────────────────────────────────────────────
  if (pageState.phase === "loading") {
    return (
      <div
        className="min-h-screen bg-neutral-50 flex items-center justify-center"
        data-testid="invoice-loading"
      >
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 rounded-full border-2 border-neutral-300 border-t-neutral-700 animate-spin" />
          <p className="text-sm text-neutral-500">Loading invoice…</p>
        </div>
      </div>
    );
  }

  // ─── Error states ─────────────────────────────────────────────────────────
  if (pageState.phase === "error-expired") {
    return <QuoteExpiredPage meta={pageState.meta} />;
  }

  if (pageState.phase === "error-invalid") {
    return (
      <div
        className="min-h-screen bg-fault-50 flex flex-col"
        data-testid="invoice-invalid-page"
      >
        <main className="flex-1 flex items-center justify-center px-4 py-16">
          <div className="w-full max-w-md rounded-xl border border-fault-200 bg-white p-8 text-center shadow-sm">
            <h1 className="text-xl font-semibold text-fault-600">
              Invalid link
            </h1>
            <p className="mt-2 text-sm text-neutral-600">
              This invoice link is invalid. Please check the link in your email.
            </p>
          </div>
        </main>
        <PoweredByPilotFooter />
      </div>
    );
  }

  if (pageState.phase === "error-generic") {
    return (
      <div className="min-h-screen bg-neutral-50 flex flex-col">
        <main className="flex-1 flex items-center justify-center px-4 py-16">
          <div className="w-full max-w-md rounded-xl border border-neutral-200 bg-white p-8 text-center shadow-sm">
            <h1 className="text-xl font-semibold text-neutral-800">
              Something went wrong
            </h1>
            <p className="mt-2 text-sm text-neutral-500">{pageState.message}</p>
            <button
              onClick={() => {
                setPageState({ phase: "loading" });
                void fetchInvoice();
              }}
              className="mt-4 rounded-lg border border-neutral-300 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
            >
              Try again
            </button>
          </div>
        </main>
        <PoweredByPilotFooter />
      </div>
    );
  }

  const { invoice } = pageState;

  // RULE 5: Tenant brand color as CSS custom property, not Tailwind class
  const tenantBrandStyle = {
    "--tenant-brand": invoice.branding.brandColorHex,
  } as React.CSSProperties;

  return (
    <div
      className="min-h-screen bg-neutral-50 flex flex-col"
      style={tenantBrandStyle}
      data-testid="public-invoice-page"
    >
      {/* Payment modal */}
      {showPaymentModal && (
        <InvoicePaymentModal
          token={token}
          invoiceTotalCents={invoice.invoiceTotalCents}
          amountDueCents={invoice.amountDueCents}
          tenantName={invoice.tenantName}
          currency={invoice.currency}
          onSuccess={handlePaymentSuccess}
          onClose={() => setShowPaymentModal(false)}
        />
      )}

      <TenantBrandedHeader
        tenantName={invoice.tenantName}
        branding={invoice.branding}
      />

      <main className="flex-1 mx-auto w-full max-w-2xl px-4 py-8 flex flex-col gap-6">
        {/* Invoice header */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-neutral-900">
              Invoice for {invoice.customerName}
            </h1>
            {invoice.dueDate && (
              <p className="mt-1 text-sm text-neutral-500">
                Due{" "}
                {new Intl.DateTimeFormat("en-US", {
                  month: "long",
                  day: "numeric",
                  year: "numeric",
                }).format(new Date(invoice.dueDate))}
              </p>
            )}
          </div>
          {/* Status badge */}
          <span
            className={[
              "inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold",
              invoice.status === "paid"
                ? "bg-margin-50 text-margin-700"
                : invoice.status === "partial"
                  ? "bg-neutral-100 text-neutral-700"
                  : "bg-fault-50 text-fault-700",
            ].join(" ")}
          >
            {invoice.status === "paid"
              ? "PAID"
              : invoice.status === "partial"
                ? "PARTIAL"
                : "UNPAID"}
          </span>
        </div>

        {/* State-aware: fully paid */}
        {invoice.status === "paid" && (
          <InvoicePaidState
            amountPaidCents={invoice.amountPaidCents}
            currency={invoice.currency}
            tenantName={invoice.tenantName}
          />
        )}

        {/* State-aware: partially paid */}
        {invoice.status === "partial" && (
          <>
            <InvoicePartialPaidState
              amountPaidCents={invoice.amountPaidCents}
              amountDueCents={invoice.amountDueCents}
              invoiceTotalCents={invoice.invoiceTotalCents}
              currency={invoice.currency}
              onPayRemaining={() => setShowPaymentModal(true)}
              cardPaymentsEnabled={invoice.cardPaymentsEnabled}
            />
            {/* STRIPE-CONNECT-1-C: partial × disabled — append manual panel beneath the partial state */}
            {!invoice.cardPaymentsEnabled && (
              <ManualPaymentPanel
                tenantName={invoice.tenantName}
                tenantPhone={invoice.tenantPhone}
                tenantEmail={invoice.tenantEmail}
              />
            )}
          </>
        )}

        {/* Line items */}
        <div className="rounded-xl border border-neutral-200 bg-white p-6 shadow-sm">
          <QuoteLineItemsTable
            lineItems={invoice.lineItems}
            currency={invoice.currency}
            quoteTotalCents={invoice.invoiceTotalCents}
          />
        </div>

        {/* Pay CTA — only for unpaid invoices with card payments enabled */}
        {invoice.status === "unpaid" && invoice.cardPaymentsEnabled && (
          <div className="flex flex-col gap-2">
            <button
              onClick={() => setShowPaymentModal(true)}
              className="w-full rounded-lg py-3.5 px-6 text-sm font-semibold text-white"
              style={{ backgroundColor: "var(--tenant-brand)" }}
              data-testid="pay-invoice-button"
            >
              Pay {formatCents(invoice.amountDueCents, invoice.currency)}
            </button>
            <p className="text-center text-xs text-neutral-400">
              Secure payment powered by Stripe
            </p>
          </div>
        )}

        {/* STRIPE-CONNECT-1-C: manual-payment panel for unpaid invoices when card payments are off */}
        {invoice.status === "unpaid" && !invoice.cardPaymentsEnabled && (
          <ManualPaymentPanel
            tenantName={invoice.tenantName}
            tenantPhone={invoice.tenantPhone}
            tenantEmail={invoice.tenantEmail}
          />
        )}
      </main>

      <PoweredByPilotFooter />
    </div>
  );
}
