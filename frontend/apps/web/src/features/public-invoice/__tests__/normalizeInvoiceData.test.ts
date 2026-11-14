/**
 * normalizeInvoiceData tests — STRIPE-CONNECT-1-C
 *
 * Location: apps/web/src/features/public-invoice/__tests__/normalizeInvoiceData.test.ts
 *
 * Verifies the 4 new fields map correctly (snake_case → camelCase, null-safe),
 * and that absent card_payments_enabled defaults to false (fail-closed).
 */

import { describe, it, expect } from "vitest";
import { normalizeInvoiceData } from "../types";

const baseRaw = {
  invoice_id: "inv-001",
  tenant_name: "Acme Electric",
  customer_name: "John Smith",
  invoice_total_cents: 125000,
  amount_paid_cents: 0,
  amount_due_cents: 125000,
  currency: "USD",
  status: "unpaid",
  due_date: "2026-09-01",
  line_items: [
    {
      description: "Panel upgrade",
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

describe("normalizeInvoiceData — STRIPE-CONNECT-1-C fields", () => {
  it("maps all 4 new fields when present", () => {
    const raw = {
      ...baseRaw,
      card_payments_enabled: true,
      payment_unavailable_reason: null,
      tenant_phone: "(804) 555-0142",
      tenant_email: "billing@example.com",
    };

    const invoice = normalizeInvoiceData(raw);

    expect(invoice.cardPaymentsEnabled).toBe(true);
    expect(invoice.paymentUnavailableReason).toBeNull();
    expect(invoice.tenantPhone).toBe("(804) 555-0142");
    expect(invoice.tenantEmail).toBe("billing@example.com");
  });

  it("maps payment_unavailable_reason when set", () => {
    const raw = {
      ...baseRaw,
      card_payments_enabled: false,
      payment_unavailable_reason: "not_connected",
      tenant_phone: null,
      tenant_email: null,
    };

    const invoice = normalizeInvoiceData(raw);

    expect(invoice.cardPaymentsEnabled).toBe(false);
    expect(invoice.paymentUnavailableReason).toBe("not_connected");
    expect(invoice.tenantPhone).toBeNull();
    expect(invoice.tenantEmail).toBeNull();
  });

  it("maps charges_disabled reason", () => {
    const raw = {
      ...baseRaw,
      card_payments_enabled: false,
      payment_unavailable_reason: "charges_disabled",
      tenant_phone: "(555) 123-4567",
      tenant_email: null,
    };

    const invoice = normalizeInvoiceData(raw);

    expect(invoice.cardPaymentsEnabled).toBe(false);
    expect(invoice.paymentUnavailableReason).toBe("charges_disabled");
    expect(invoice.tenantPhone).toBe("(555) 123-4567");
    expect(invoice.tenantEmail).toBeNull();
  });

  it("absent card_payments_enabled defaults to false (fail-closed)", () => {
    // Simulate a stale backend that hasn't shipped the new fields
    const invoice = normalizeInvoiceData(baseRaw);

    expect(invoice.cardPaymentsEnabled).toBe(false);
    expect(invoice.paymentUnavailableReason).toBeNull();
    expect(invoice.tenantPhone).toBeNull();
    expect(invoice.tenantEmail).toBeNull();
  });
});
