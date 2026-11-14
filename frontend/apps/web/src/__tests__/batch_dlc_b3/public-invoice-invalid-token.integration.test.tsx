/**
 * DLC-B3 Integration Test — 10DLC Reviewer-Click Scenario
 *
 * This test encodes the exact Telnyx reviewer scenario that exposed a 500 in
 * the deployed environment: a fake token must render a graceful page, never a crash.
 *
 * Background (2026-07-25):
 *   - curl https://api.pilotfortrades.com/api/v1/public/invoices/A1b2C3 → 404
 *   - Browser showed 500 (SSR generateMetadata env-var mismatch + no 404 branch)
 *   - INV-ROUTE-FIX (Python) fixed the route collision → bad tokens now → 401
 *   - DLC-B3 (this batch) adds 404 branch + reconciles env-var name
 *
 * Three cases:
 *   1. Fake token (Telnyx sample link) → 401 → graceful invalid-link page
 *   2. Token resolves to 410 expired → graceful expired page
 *   3. Token resolves to 404 (pre-INV-ROUTE-FIX backend or edge CDN) → graceful
 *      invalid-link page (proves STEP 0 catch-all)
 */

import React from "react";
import { describe, it, expect, beforeAll, afterEach, afterAll } from "vitest";
import { render, screen } from "@testing-library/react";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";

import { PublicInvoicePage } from "../../features/public-invoice/PublicInvoicePage";

// ── MSW server ────────────────────────────────────────────────────────────────

const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("10DLC Reviewer-Click — Public Invoice Graceful Error States", () => {
  it("fake token 'A1b2C3' + 401 → graceful invoice-invalid-page (no crash, no 500)", async () => {
    // The exact token from the Telnyx 10DLC sample link.
    // After INV-ROUTE-FIX the backend returns 401 for an unparseable token.
    server.use(
      http.get("/api/v1/public/invoices/A1b2C3", () =>
        HttpResponse.json(
          {
            type: "https://errors.pilotfortrades.com/invalid-token",
            title: "Invalid or tampered token",
            status: 401,
          },
          { status: 401 },
        ),
      ),
    );

    render(<PublicInvoicePage token="A1b2C3" />);

    await screen.findByTestId("invoice-invalid-page");
    expect(screen.getByText("Invalid link")).toBeInTheDocument();
    expect(
      screen.getByText(/check the link in your email/i),
    ).toBeInTheDocument();
    // Confirm no unhandled error boundary triggered — the testid is present
    expect(screen.queryByTestId("public-invoice-page")).not.toBeInTheDocument();
  });

  it("expired token + 410 → graceful quote-expired-page (common real-world case)", async () => {
    server.use(
      http.get("/api/v1/public/invoices/expiredToken789", () =>
        HttpResponse.json(
          {
            detail: "Link has expired",
            tenant_name: "Apex Electrical LLC",
            tenant_phone: "555-000-1111",
            tenant_email: "billing@apexelectrical.example.com",
          },
          { status: 410 },
        ),
      ),
    );

    render(<PublicInvoicePage token="expiredToken789" />);

    await screen.findByTestId("quote-expired-page");
    expect(screen.getByTestId("expired-heading")).toBeInTheDocument();
    // Tenant contact info should be present since backend returned it
    expect(screen.getByTestId("tenant-contact-info")).toBeInTheDocument();
    expect(screen.queryByTestId("public-invoice-page")).not.toBeInTheDocument();
  });

  it("404 token → graceful invoice-invalid-page (STEP 0 — pre-INV-ROUTE-FIX catch-all)", async () => {
    // Pre-INV-ROUTE-FIX, the live backend returned 404 for this token.
    // Even after the fix, edge CDNs or proxy layers could still emit 404.
    // This branch must always render gracefully (same as 401).
    server.use(
      http.get("/api/v1/public/invoices/unknownToken000", () =>
        HttpResponse.json({ detail: "Not found" }, { status: 404 }),
      ),
    );

    render(<PublicInvoicePage token="unknownToken000" />);

    await screen.findByTestId("invoice-invalid-page");
    expect(screen.getByText("Invalid link")).toBeInTheDocument();
    expect(screen.queryByTestId("public-invoice-page")).not.toBeInTheDocument();
  });
});
