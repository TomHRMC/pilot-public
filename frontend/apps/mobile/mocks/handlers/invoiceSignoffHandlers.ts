/**
 * invoiceSignoffHandlers — MSW handlers for CE-1 Part B invoice sign-off endpoints
 *
 * Location: apps/mobile/mocks/handlers/invoiceSignoffHandlers.ts
 *
 * Covers:
 *   GET  /api/v1/jobs/:jobId/signoff-context  (D.1)
 *   POST /api/v1/invoices/:invoiceId/signoff   (D.2)
 *
 * Fixtures carry varied states per seed-awareness note (inclusions §18):
 *   (a) single invoice, active_signoff: null
 *   (b) invoice with active_signoff populated
 *   (c) multi-invoice context (2+ invoices)
 *
 * Per batch-ce-1-react-native-engr-prompt.md Step 7.
 * Rule 18: all handlers use the wildcard prefix (mobile apiClient.baseURL is absolute).
 */

import { http, HttpResponse } from "msw";

const BASE = "*/api/v1";

// ── Fixture IDs ───────────────────────────────────────────────────────────────

export const SIGNOFF_JOB_ID = "job-today-001";
export const SIGNOFF_INVOICE_ID = "invoice-signoff-001";
export const SIGNOFF_INVOICE_ID_2 = "invoice-signoff-002";
export const SIGNOFF_SIGNED_INVOICE_ID = "invoice-signoff-signed-001";

// ── Default fixture: single invoice, no signoff (ready-to-capture) ────────────

export const getSignoffContextDefault = http.get(
  `${BASE}/jobs/:jobId/signoff-context`,
  () => {
    return HttpResponse.json({
      job_id: SIGNOFF_JOB_ID,
      customer_display_name: "John Smith",
      invoices: [
        {
          invoice_id: SIGNOFF_INVOICE_ID,
          invoice_number: "INV-0042",
          status: "issued",
          total_cents: 125000,
          balance_due_cents: 125000,
          currency: "USD",
          terms_text:
            "By signing, the customer acknowledges the work described has been completed satisfactorily and agrees to the payment terms outlined above.",
          active_signoff: null,
        },
      ],
    });
  },
);

// ── Fixture: multi-invoice context (2+ invoices) ──────────────────────────────

export const getSignoffContextMulti = http.get(
  `${BASE}/jobs/:jobId/signoff-context`,
  () => {
    return HttpResponse.json({
      job_id: SIGNOFF_JOB_ID,
      customer_display_name: "Apex Commercial LLC",
      invoices: [
        {
          invoice_id: SIGNOFF_INVOICE_ID,
          invoice_number: "INV-0042",
          status: "issued",
          total_cents: 125000,
          balance_due_cents: 125000,
          currency: "USD",
          terms_text: "Standard terms apply.",
          active_signoff: null,
        },
        {
          invoice_id: SIGNOFF_INVOICE_ID_2,
          invoice_number: "INV-0043",
          status: "partial",
          total_cents: 85000,
          balance_due_cents: 42500,
          currency: "USD",
          terms_text: "Partial payment received. Remaining balance due.",
          active_signoff: null,
        },
      ],
    });
  },
);

// ── Fixture: invoice with active_signoff populated (already-signed) ───────────

export const getSignoffContextSigned = http.get(
  `${BASE}/jobs/:jobId/signoff-context`,
  () => {
    return HttpResponse.json({
      job_id: SIGNOFF_JOB_ID,
      customer_display_name: "Mary Johnson",
      invoices: [
        {
          invoice_id: SIGNOFF_SIGNED_INVOICE_ID,
          invoice_number: "INV-0050",
          status: "issued",
          total_cents: 95000,
          balance_due_cents: 95000,
          currency: "USD",
          terms_text: "Standard terms apply.",
          active_signoff: {
            signoff_id: "signoff-001",
            signed_by_name: "Mary Johnson",
            signed_at: "2026-08-12T14:30:00Z",
          },
        },
      ],
    });
  },
);

// ── Fixture: empty invoices (hidden state) ────────────────────────────────────

export const getSignoffContextEmpty = http.get(
  `${BASE}/jobs/:jobId/signoff-context`,
  () => {
    return HttpResponse.json({
      job_id: SIGNOFF_JOB_ID,
      customer_display_name: "Bob Davis",
      invoices: [],
    });
  },
);

// ── Fixture: error state ──────────────────────────────────────────────────────

export const getSignoffContextError = http.get(
  `${BASE}/jobs/:jobId/signoff-context`,
  () => {
    return HttpResponse.json(
      { detail: "Internal server error" },
      { status: 500 },
    );
  },
);

// ── POST signoff handler ──────────────────────────────────────────────────────

export const postInvoiceSignoff = http.post(
  `${BASE}/invoices/:invoiceId/signoff`,
  () => {
    return HttpResponse.json({
      signoff_id: "signoff-new-001",
      invoice_id: SIGNOFF_INVOICE_ID,
      signed_by_name: "John Smith",
      signed_at: new Date().toISOString(),
      client_capture_at: new Date().toISOString(),
      captured_by_user_id: "tech-user-001",
      signature_url:
        "https://s3.amazonaws.com/pilot-signatures/test/signature.png",
    });
  },
);

// ── Handler array ─────────────────────────────────────────────────────────────

export const invoiceSignoffHandlers = [
  getSignoffContextDefault,
  postInvoiceSignoff,
];
