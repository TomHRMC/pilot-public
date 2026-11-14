/**
 * PublicQuotePage unit tests — DLC-B3
 *
 * Covers all error + ready states for the public quote page.
 * Uses MSW (msw/node) to intercept the `fetch()` call at HTTP level.
 *
 * NOTE: PublicQuotePage intentionally uses `fetch()` not `apiClient` —
 * unauthenticated surface; do NOT refactor those calls (see RULE 1 in source).
 */

import React from "react";
import { describe, it, expect, beforeAll, afterEach, afterAll } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";

import { PublicQuotePage } from "../PublicQuotePage";

// ── Fixtures ─────────────────────────────────────────────────────────────────

const VALID_TOKEN = "quoteToken456";

const mockQuoteResponse = {
  quote_id: "quote-xyz-001",
  tenant_name: "Apex Electrical LLC",
  customer_name: "Mary Johnson",
  quote_total_cents: 98000,
  currency: "USD",
  status: "sent",
  expires_at: "2026-12-31T00:00:00Z",
  line_items: [
    {
      description: "Recessed lighting installation (10 fixtures)",
      quantity: "10",
      unit_price_cents: 9800,
      total_cents: 98000,
    },
  ],
  branding: {
    logo_url: null,
    brand_color_hex: "#3B43D6",
  },
  customer_acceptance_comment: null,
  customer_decline_comment: null,
};

// ── MSW server ────────────────────────────────────────────────────────────────

const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Helpers ───────────────────────────────────────────────────────────────────

function renderPage(token = VALID_TOKEN) {
  return render(<PublicQuotePage token={token} />);
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("PublicQuotePage", () => {
  it("case 1 — 410 without tenant meta → quote-expired-page, no tenant-contact-info", async () => {
    server.use(
      http.get(`/api/v1/public/quotes/${VALID_TOKEN}`, () =>
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
      http.get(`/api/v1/public/quotes/${VALID_TOKEN}`, () =>
        HttpResponse.json(
          {
            detail: "Link has expired",
            tenant_name: "Apex Electrical LLC",
            tenant_phone: "555-987-6543",
            tenant_email: "quotes@apexelectrical.example.com",
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

  it("case 3 — 401 → quote-invalid-page with 'Invalid link' heading", async () => {
    server.use(
      http.get(`/api/v1/public/quotes/${VALID_TOKEN}`, () =>
        HttpResponse.json({ detail: "Invalid token" }, { status: 401 }),
      ),
    );

    renderPage();

    await screen.findByTestId("quote-invalid-page");
    expect(screen.getByText("Invalid link")).toBeInTheDocument();
    expect(
      screen.getByText(/check the link in your email/i),
    ).toBeInTheDocument();
  });

  it("case 4 — 404 → renders same quote-invalid-page as 401 (STEP 0 fix)", async () => {
    server.use(
      http.get(`/api/v1/public/quotes/${VALID_TOKEN}`, () =>
        HttpResponse.json({ detail: "Not found" }, { status: 404 }),
      ),
    );

    renderPage();

    await screen.findByTestId("quote-invalid-page");
    expect(screen.getByText("Invalid link")).toBeInTheDocument();
  });

  it("case 5 — 500 → generic error with 'Try again' button; retry succeeds", async () => {
    server.use(
      http.get(`/api/v1/public/quotes/${VALID_TOKEN}`, () =>
        HttpResponse.json({ detail: "Internal server error" }, { status: 500 }),
      ),
    );

    renderPage();

    const retryButton = await screen.findByRole("button", {
      name: /try again/i,
    });
    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();

    // Override to 200 then click retry
    server.use(
      http.get(`/api/v1/public/quotes/${VALID_TOKEN}`, () =>
        HttpResponse.json(mockQuoteResponse),
      ),
    );

    fireEvent.click(retryButton);

    await screen.findByTestId("public-quote-page");
    expect(screen.getByText("Quote for Mary Johnson")).toBeInTheDocument();
  });

  it("case 6 — network error → generic connection error message", async () => {
    server.use(
      http.get(`/api/v1/public/quotes/${VALID_TOKEN}`, () =>
        HttpResponse.error(),
      ),
    );

    renderPage();

    await screen.findByText(/could not load quote/i);
    expect(
      screen.getByRole("button", { name: /try again/i }),
    ).toBeInTheDocument();
  });

  it("case 7 — 200 → ready quote with customer name and accept/decline buttons", async () => {
    server.use(
      http.get(`/api/v1/public/quotes/${VALID_TOKEN}`, () =>
        HttpResponse.json(mockQuoteResponse),
      ),
    );

    renderPage();

    await screen.findByTestId("public-quote-page");
    expect(screen.getByText("Quote for Mary Johnson")).toBeInTheDocument();
    expect(screen.getByTestId("accept-quote-button")).toBeInTheDocument();
    expect(screen.getByTestId("decline-quote-button")).toBeInTheDocument();
  });
});
