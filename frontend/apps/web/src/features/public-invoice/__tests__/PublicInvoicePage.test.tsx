/**
 * PublicInvoicePage unit tests — DLC-B3
 *
 * Covers all error + ready states for the public invoice page.
 * Uses MSW (msw/node) to intercept the `fetch()` call at HTTP level.
 *
 * NOTE: PublicInvoicePage intentionally uses `fetch()` not `apiClient` —
 * unauthenticated surface; do NOT refactor those calls (see RULE 1 in source).
 */

import React from "react";
import { describe, it, expect, beforeAll, afterEach, afterAll } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";

import { PublicInvoicePage } from "../PublicInvoicePage";

// ── Fixtures ─────────────────────────────────────────────────────────────────

const VALID_TOKEN = "validToken123";

const mockInvoiceResponse = {
  invoice_id: "inv-abc-001",
  tenant_name: "Apex Electrical LLC",
  customer_name: "John Smith",
  invoice_total_cents: 125000,
  amount_paid_cents: 0,
  amount_due_cents: 125000,
  currency: "USD",
  status: "unpaid",
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
  // STRIPE-CONNECT-1-C: card payments enabled so the Pay CTA renders
  card_payments_enabled: true,
  payment_unavailable_reason: null,
  tenant_phone: "(804) 555-0142",
  tenant_email: "billing@example.com",
};

// ── MSW server ────────────────────────────────────────────────────────────────

const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Helpers ───────────────────────────────────────────────────────────────────

function renderPage(token = VALID_TOKEN) {
  return render(<PublicInvoicePage token={token} />);
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("PublicInvoicePage", () => {
  it("case 1 — 410 without tenant meta → expired page, no tenant-contact-info", async () => {
    server.use(
      http.get(`/api/v1/public/invoices/${VALID_TOKEN}`, () =>
        HttpResponse.json({ detail: "Link has expired" }, { status: 410 }),
      ),
    );

    renderPage();

    await screen.findByTestId("quote-expired-page");
    expect(screen.getByTestId("expired-heading")).toBeInTheDocument();
    expect(screen.queryByTestId("tenant-contact-info")).not.toBeInTheDocument();
  });

  it("case 2 — 410 WITH tenant metadata → expired page + tenant-contact-info visible", async () => {
    server.use(
      http.get(`/api/v1/public/invoices/${VALID_TOKEN}`, () =>
        HttpResponse.json(
          {
            detail: "Link has expired",
            tenant_name: "Apex Electrical LLC",
            tenant_phone: "555-123-4567",
            tenant_email: "info@apexelectrical.example.com",
          },
          { status: 410 },
        ),
      ),
    );

    renderPage();

    await screen.findByTestId("quote-expired-page");
    expect(screen.getByTestId("tenant-contact-info")).toBeInTheDocument();
    expect(screen.getByTestId("tenant-phone")).toBeInTheDocument();
    expect(screen.getByTestId("tenant-email")).toBeInTheDocument();
  });

  it("case 3 — 401 → invoice-invalid-page with 'Invalid link' heading", async () => {
    server.use(
      http.get(`/api/v1/public/invoices/${VALID_TOKEN}`, () =>
        HttpResponse.json({ detail: "Invalid token" }, { status: 401 }),
      ),
    );

    renderPage();

    await screen.findByTestId("invoice-invalid-page");
    expect(screen.getByText("Invalid link")).toBeInTheDocument();
    expect(
      screen.getByText(/check the link in your email/i),
    ).toBeInTheDocument();
  });

  it("case 4 — 404 → renders same invoice-invalid-page as 401 (STEP 0 fix)", async () => {
    server.use(
      http.get(`/api/v1/public/invoices/${VALID_TOKEN}`, () =>
        HttpResponse.json({ detail: "Not found" }, { status: 404 }),
      ),
    );

    renderPage();

    await screen.findByTestId("invoice-invalid-page");
    expect(screen.getByText("Invalid link")).toBeInTheDocument();
  });

  it("case 5 — 500 → generic error with 'Try again' button; retry succeeds", async () => {
    server.use(
      http.get(`/api/v1/public/invoices/${VALID_TOKEN}`, () =>
        HttpResponse.json({ detail: "Internal server error" }, { status: 500 }),
      ),
    );

    renderPage();

    // Wait for the generic error state
    const retryButton = await screen.findByRole("button", {
      name: /try again/i,
    });
    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();

    // Override to 200 then click retry
    server.use(
      http.get(`/api/v1/public/invoices/${VALID_TOKEN}`, () =>
        HttpResponse.json(mockInvoiceResponse),
      ),
    );

    fireEvent.click(retryButton);

    await screen.findByTestId("public-invoice-page");
    expect(screen.getByText("Invoice for John Smith")).toBeInTheDocument();
  });

  it("case 6 — network error → generic connection error message", async () => {
    server.use(
      http.get(`/api/v1/public/invoices/${VALID_TOKEN}`, () =>
        HttpResponse.error(),
      ),
    );

    renderPage();

    await screen.findByText(/could not load invoice/i);
    expect(
      screen.getByRole("button", { name: /try again/i }),
    ).toBeInTheDocument();
  });

  it("case 7 — 200 → ready invoice with customer name and pay button", async () => {
    server.use(
      http.get(`/api/v1/public/invoices/${VALID_TOKEN}`, () =>
        HttpResponse.json(mockInvoiceResponse),
      ),
    );

    renderPage();

    await screen.findByTestId("public-invoice-page");
    expect(screen.getByText("Invoice for John Smith")).toBeInTheDocument();
    expect(screen.getByTestId("pay-invoice-button")).toBeInTheDocument();
  });
});
