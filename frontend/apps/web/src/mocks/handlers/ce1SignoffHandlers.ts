/**
 * MSW handlers — CE-1 Part C: Invoice Signoff + Resolve Variance
 *
 * Location: apps/web/src/mocks/handlers/ce1SignoffHandlers.ts
 *
 * Endpoints:
 *  - GET  /api/v1/invoices/:invoiceId/signoff → InvoiceSignoffDetailResponse
 *  - POST /api/v1/invoices/:paymentId/resolve-variance → extended PaymentResponse
 *
 * Test resilience: fixtures are NEVER mutated. Each handler returns fresh objects.
 */

import { http, HttpResponse } from "msw";

// ── Fixtures ──────────────────────────────────────────────────────────────────

const MOCK_SIGNOFF = {
  signoff_id: "so-00000001-0000-0000-0000-000000000001",
  invoice_id: "inv-00000001-0000-0000-0000-000000000001",
  signed_by_name: "John Smith",
  signed_at: "2026-08-12T14:30:00Z",
  client_capture_at: null,
  captured_by_user_id: "u-tech-001-0000-0000-0000-000000000001",
  signature_url: "https://mock-s3.example.com/signatures/test-sig.png",
};

const MOCK_SIGNOFF_WITH_OFFLINE = {
  ...MOCK_SIGNOFF,
  signoff_id: "so-00000002-0000-0000-0000-000000000002",
  client_capture_at: "2026-08-12T14:28:00Z",
};

// ── Handlers ──────────────────────────────────────────────────────────────────

export const ce1SignoffHandlers = [
  // GET /api/v1/invoices/:invoiceId/signoff
  http.get("/api/v1/invoices/:invoiceId/signoff", ({ params }) => {
    const { invoiceId } = params as { invoiceId: string };

    // Special invoice IDs for test scenarios
    if (invoiceId === "inv-signoff-null-0000-0000-0000-000000000001") {
      return HttpResponse.json({
        signoff: null,
        superseded_count: 0,
      });
    }

    if (invoiceId === "inv-signoff-offline-0000-0000-0000-000000000001") {
      return HttpResponse.json({
        signoff: MOCK_SIGNOFF_WITH_OFFLINE,
        superseded_count: 0,
      });
    }

    if (invoiceId === "inv-signoff-superseded-0000-0000-0000-000000000001") {
      return HttpResponse.json({
        signoff: MOCK_SIGNOFF,
        superseded_count: 2,
      });
    }

    if (invoiceId === "inv-signoff-error-0000-0000-0000-000000000001") {
      return HttpResponse.json(
        { detail: "Internal server error" },
        { status: 500 },
      );
    }

    // Default: populated signoff
    return HttpResponse.json({
      signoff: MOCK_SIGNOFF,
      superseded_count: 0,
    });
  }),

  // POST /api/v1/invoices/:paymentId/resolve-variance
  http.post(
    "/api/v1/invoices/:paymentId/resolve-variance",
    async ({ params, request }) => {
      const { paymentId } = params as { paymentId: string };
      const body = (await request.json()) as {
        resolution: string;
        note?: string;
      };

      // 409 — already resolved
      if (paymentId === "pay-already-resolved-0000-0000-000000000001") {
        return HttpResponse.json(
          {
            type: "https://errors.pilotfortrades.com/conflict",
            title: "Already resolved",
            status: 409,
            detail: "This overpayment was already resolved.",
          },
          { status: 409 },
        );
      }

      // 422 — no overpayment
      if (paymentId === "pay-no-variance-0000-0000-0000-000000000001") {
        return HttpResponse.json(
          {
            type: "https://errors.pilotfortrades.com/validation",
            title: "No overpayment",
            status: 422,
            detail: "No overpayment to resolve.",
          },
          { status: 422 },
        );
      }

      // 500 — server error
      if (paymentId === "pay-server-error-0000-0000-0000-000000000001") {
        return HttpResponse.json(
          { detail: "Internal server error" },
          { status: 500 },
        );
      }

      // Success — return extended PaymentResponse
      return HttpResponse.json({
        id: paymentId,
        invoice_id: "inv-00000001-0000-0000-0000-000000000001",
        tenant_id: "t-00000001-0000-0000-0000-000000000001",
        amount_cents: 60000,
        paid_via: "card",
        balance_due_cents: 0,
        amount_variance_cents: 1500,
        status_id: "fa70374c-513a-4cc3-baca-22a54a594a4d",
        paid_at: "2026-08-12T10:00:00Z",
        idempotency_key: null,
        created_at: "2026-08-12T10:00:00Z",
        variance_resolution: body.resolution,
        variance_resolution_note: body.note ?? null,
        variance_resolved_at: new Date().toISOString(),
        variance_resolved_by_user_id: "u-00000001-0000-0000-0000-000000000001",
      });
    },
  ),
];
