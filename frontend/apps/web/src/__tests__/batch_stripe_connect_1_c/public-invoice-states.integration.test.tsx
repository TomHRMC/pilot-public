/**
 * Public Invoice Payment States — Integration Tests — STRIPE-CONNECT-1-C
 *
 * Location: apps/web/src/__tests__/batch_stripe_connect_1_c/public-invoice-states.integration.test.tsx
 *
 * Page renders (no 404) and, via server.use overrides on the invoice GET:
 *   - unpaid + enabled → Pay CTA visible, no panel
 *   - unpaid + disabled → ManualPaymentPanel visible (heading + both links), no Pay CTA, no Stripe caption
 *   - partial + disabled → partial state visible, no "Pay remaining" button, panel appended beneath
 *   - both contact fields null → fallback line rendered
 */

import React from "react";
import { describe, it, expect, beforeAll, afterEach, afterAll } from "vitest";
import { render, screen } from "@testing-library/react";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import "@testing-library/jest-dom";

import { PublicInvoicePage } from "../../features/public-invoice/PublicInvoicePage";

// ── Fixtures ──────────────────────────────────────────────────────────────────

const VALID_TOKEN = "validToken123";

const baseInvoice = {
  invoice_id: "inv-abc-001",
  tenant_name: "Apex Electrical LLC",
  customer_name: "John Smith",
  invoice_total_cents: 125000,
  currency: "USD",
  due_date: "2026-08-31",
  line_items: [
    {
      description: "Panel upgrade 200A",
      quantity: "1",
      unit_price_cents: 125000,
      total_cents: 125000,
    },
  ],
  branding: {
    logo_url: null,
    brand_color_hex: "#3B43D6",
  },
};

const unpaidEnabled = {
  ...baseInvoice,
  amount_paid_cents: 0,
  amount_due_cents: 125000,
  status: "unpaid",
  card_payments_enabled: true,
  payment_unavailable_reason: null,
  tenant_phone: "(804) 555-0142",
  tenant_email: "billing@example.com",
};

const unpaidDisabled = {
  ...unpaidEnabled,
  card_payments_enabled: false,
  payment_unavailable_reason: "not_connected",
};

const partialDisabled = {
  ...baseInvoice,
  amount_paid_cents: 50000,
  amount_due_cents: 75000,
  status: "partial",
  card_payments_enabled: false,
  payment_unavailable_reason: "charges_disabled",
  tenant_phone: "(804) 555-0142",
  tenant_email: "billing@example.com",
};

const unpaidDisabledBothNull = {
  ...unpaidDisabled,
  tenant_phone: null,
  tenant_email: null,
};

// ── MSW ──────────────────────────────────────────────────────────────────────

const server = setupServer();
beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Tests ────────────────────────────────────────────────────────────────────

describe("STRIPE-CONNECT-1-C — Public Invoice Payment States", () => {
  it("unpaid + enabled → Pay CTA visible, no manual panel", async () => {
    server.use(
      http.get(`/api/v1/public/invoices/${VALID_TOKEN}`, () =>
        HttpResponse.json(unpaidEnabled),
      ),
    );

    render(<PublicInvoicePage token={VALID_TOKEN} />);

    await screen.findByTestId("public-invoice-page");
    expect(screen.getByTestId("pay-invoice-button")).toBeInTheDocument();
    expect(
      screen.queryByTestId("manual-payment-panel"),
    ).not.toBeInTheDocument();
  });

  it("unpaid + disabled → ManualPaymentPanel visible (heading + both links), no Pay CTA, no Stripe caption", async () => {
    server.use(
      http.get(`/api/v1/public/invoices/${VALID_TOKEN}`, () =>
        HttpResponse.json(unpaidDisabled),
      ),
    );

    render(<PublicInvoicePage token={VALID_TOKEN} />);

    await screen.findByTestId("manual-payment-panel");
    expect(screen.getByText("How to pay this invoice")).toBeInTheDocument();
    expect(screen.getByTestId("manual-payment-phone-link")).toBeInTheDocument();
    expect(screen.getByTestId("manual-payment-email-link")).toBeInTheDocument();

    // No Pay CTA
    expect(screen.queryByTestId("pay-invoice-button")).not.toBeInTheDocument();

    // No Stripe caption
    expect(screen.queryByText(/powered by stripe/i)).not.toBeInTheDocument();
  });

  it("partial + disabled → partial state visible, no 'Pay remaining' button, panel appended beneath", async () => {
    server.use(
      http.get(`/api/v1/public/invoices/${VALID_TOKEN}`, () =>
        HttpResponse.json(partialDisabled),
      ),
    );

    render(<PublicInvoicePage token={VALID_TOKEN} />);

    // Partial state renders
    await screen.findByTestId("invoice-partial-paid-state");
    expect(screen.getByTestId("partial-progress-bar")).toBeInTheDocument();

    // "Pay remaining" CTA suppressed
    expect(
      screen.queryByTestId("pay-remaining-button"),
    ).not.toBeInTheDocument();

    // Manual panel appended beneath
    expect(screen.getByTestId("manual-payment-panel")).toBeInTheDocument();
    expect(screen.getByText("How to pay this invoice")).toBeInTheDocument();
  });

  it("both contact fields null → fallback line rendered, no contact links", async () => {
    server.use(
      http.get(`/api/v1/public/invoices/${VALID_TOKEN}`, () =>
        HttpResponse.json(unpaidDisabledBothNull),
      ),
    );

    render(<PublicInvoicePage token={VALID_TOKEN} />);

    await screen.findByTestId("manual-payment-panel");
    expect(
      screen.getByText(
        /Please reach out to Apex Electrical LLC to arrange payment/,
      ),
    ).toBeInTheDocument();
    expect(
      screen.queryByTestId("manual-payment-phone-link"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("manual-payment-email-link"),
    ).not.toBeInTheDocument();
  });
});
