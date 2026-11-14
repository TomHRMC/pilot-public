/**
 * MSW handlers — Invoice Detail, Create, Send, Record Payment, AR Aging — FE-B22
 *
 * Location: apps/web/src/mocks/handlers/invoiceDetailHandlers.ts
 *
 * Pre-work decisions:
 *  - payment_method table is empty; use sentinel UUID "00000000-0000-0000-0000-000000000001"
 *  - payment_status "succeeded" UUID: "fa70374c-513a-4cc3-baca-22a54a594a4d"
 *  - POST /api/v1/invoices/ returns 412 when tax not configured (simulated via query param in tests)
 *  - AR aging endpoint exists: GET /api/v1/reports/ar-aging
 *
 * Test resilience: fixture arrays are NEVER mutated. POST handlers return merged data.
 */

import { http, HttpResponse } from "msw";

// ── Fixtures ──────────────────────────────────────────────────────────────────

const MOCK_INVOICE_LINES = [
  {
    id: "il-00000001-0000-0000-0000-000000000001",
    invoice_id: "inv-00000001-0000-0000-0000-000000000001",
    source_type: "catalog_item",
    source_id: "ci-00000001-0000-0000-0000-000000000001",
    description: "200A Service Panel Upgrade",
    quantity: 1,
    unit_price_cents: 45000,
    subtotal_cents: 45000,
    tax_amount_cents: 3713,
    total_cents: 48713,
    sort_order: 0,
  },
  {
    id: "il-00000002-0000-0000-0000-000000000002",
    invoice_id: "inv-00000001-0000-0000-0000-000000000001",
    source_type: "catalog_item",
    source_id: "ci-00000002-0000-0000-0000-000000000002",
    description: "Wire, 12 AWG 100ft",
    quantity: 100,
    unit_price_cents: 85,
    subtotal_cents: 8500,
    tax_amount_cents: 701,
    total_cents: 9201,
    sort_order: 1,
  },
];

// ── List fixture for GET /api/v1/invoices/ ────────────────────────────────────
// SD-FE-1: status_code uses actual DB codes (issued, paid, void, writeoff — NOT "sent" or "overdue")
// FE-B24: added customer_name field (B18 adds this to InvoiceSummary response)
const MOCK_INVOICE_LIST = [
  {
    id: "inv-00000001-0000-0000-0000-000000000001",
    invoice_number: "INV-20260616-0001",
    customer_id: "c-00000001-0000-0000-0000-000000000001",
    customer_name: "Smith Electric LLC", // FE-B24
    site_id: "s-00000001-0000-0000-0000-000000000001",
    status_id: "st-issued-000-0000-0000-000000000001",
    status_code: "issued", // SD-FE-1: corrected from "sent" — "issued" is the DB code
    issued_at: "2026-06-16T00:00:00Z",
    due_at: "2026-05-01T00:00:00Z", // Past due — will show overdue badge
  },
  {
    id: "inv-00000002-0000-0000-0000-000000000002",
    invoice_number: "INV-20260610-0002",
    customer_id: "c-00000002-0000-0000-0000-000000000002",
    customer_name: "Johnson Electrical", // FE-B24
    site_id: "s-00000002-0000-0000-0000-000000000002",
    status_id: "st-paid-0000-0000-0000-000000000001",
    status_code: "paid",
    issued_at: "2026-06-10T00:00:00Z",
    due_at: "2026-06-24T00:00:00Z",
  },
  {
    id: "inv-00000003-0000-0000-0000-000000000003",
    invoice_number: "INV-20260601-0003",
    customer_id: "c-00000001-0000-0000-0000-000000000001",
    customer_name: "Smith Electric LLC", // FE-B24
    site_id: "s-00000001-0000-0000-0000-000000000001",
    status_id: "st-draft-000-0000-0000-000000000001",
    status_code: "draft",
    issued_at: null,
    due_at: null,
  },
];

const MOCK_INVOICES: Record<string, object> = {
  "inv-00000001-0000-0000-0000-000000000001": {
    id: "inv-00000001-0000-0000-0000-000000000001",
    tenant_id: "t-00000001-0000-0000-0000-000000000001",
    invoice_number: "INV-20260616-0001",
    customer_id: "c-00000001-0000-0000-0000-000000000001",
    site_id: "s-00000001-0000-0000-0000-000000000001",
    status_id: "st-issued-000-0000-0000-000000000001",
    status_code: "issued", // SD-FE-1: corrected from "sent" — "issued" is the DB code
    quote_id: "q-00000001-0000-0000-0000-000000000001",
    job_id: null,
    idempotency_key: "idem-0001",
    issued_at: "2026-06-16T00:00:00Z",
    due_at: "2026-06-30T00:00:00Z",
    subtotal_cents: 53500,
    tax_cents: 4414,
    total_cents: 57914,
    balance_due_cents: 57914,
    currency: "USD",
    customer_notes: "Thank you for your business.",
    terms_and_conditions: null,
    pdf_object_key: null,
    is_active: true,
    created_at: "2026-06-16T10:00:00Z",
    updated_at: "2026-06-16T10:00:00Z",
    created_by: null,
    updated_by: null,
    lines: MOCK_INVOICE_LINES,
    // UI-FIX-1B: FIX-013-FE — payments field added to invoice detail mock
    payments: [
      {
        id: "pay-mock-001",
        amount_cents: 80000,
        paid_at: "2026-07-01T00:00:00Z",
        paid_via: "check",
        psp_provider: null,
        customer_payment_comment: "July partial payment",
        status_id: "ps-mock-001",
      },
    ],
  },
  "inv-00000002-0000-0000-0000-000000000002": {
    id: "inv-00000002-0000-0000-0000-000000000002",
    tenant_id: "t-00000001-0000-0000-0000-000000000001",
    invoice_number: "INV-20260610-0002",
    customer_id: "c-00000002-0000-0000-0000-000000000002",
    site_id: "s-00000002-0000-0000-0000-000000000002",
    status_id: "st-paid-0000-0000-0000-000000000001",
    status_code: "paid",
    quote_id: null,
    job_id: "j-00000001-0000-0000-0000-000000000001",
    idempotency_key: "idem-0002",
    issued_at: "2026-06-10T00:00:00Z",
    due_at: "2026-06-24T00:00:00Z",
    subtotal_cents: 32000,
    tax_cents: 2640,
    total_cents: 34640,
    balance_due_cents: 0,
    currency: "USD",
    customer_notes: null,
    terms_and_conditions: null,
    pdf_object_key: null,
    is_active: true,
    created_at: "2026-06-10T09:00:00Z",
    updated_at: "2026-06-10T09:00:00Z",
    created_by: null,
    updated_by: null,
    lines: [],
    payments: [],
  },
};

// ── Handlers ──────────────────────────────────────────────────────────────────

export const invoiceDetailHandlers = [
  // GET /api/v1/invoices/ — paginated invoice list with optional ?status=, ?overdue=true, ?customer_id= filters
  // SD-FE-1: Added ?overdue=true support. status_code uses actual DB codes (issued, paid, void, writeoff).
  // UI-FIX-2D: added ?customer_id= exact UUID filter
  http.get("/api/v1/invoices/", ({ request }) => {
    const url = new URL(request.url);
    const statusFilter = url.searchParams.get("status");
    const overdueFilter = url.searchParams.get("overdue") === "true";
    const customerId = url.searchParams.get("customer_id") ?? "";

    let filtered = MOCK_INVOICE_LIST;

    if (customerId)
      filtered = filtered.filter((inv) => inv.customer_id === customerId);

    if (overdueFilter) {
      // SD-06B: server-side overdue filter: due_at < NOW AND status NOT IN (paid, void, writeoff)
      const now = new Date();
      filtered = filtered.filter(
        (inv) =>
          inv.due_at !== null &&
          new Date(inv.due_at) < now &&
          !["paid", "void", "writeoff"].includes(inv.status_code),
      );
    } else if (statusFilter) {
      filtered = filtered.filter((inv) => inv.status_code === statusFilter);
    }

    return HttpResponse.json({
      items: filtered,
      total: filtered.length,
      limit: 50,
      offset: 0,
    });
  }),

  // GET /api/v1/invoices/:invoiceId — invoice detail with lines
  http.get("/api/v1/invoices/:invoiceId", ({ params }) => {
    const { invoiceId } = params as { invoiceId: string };
    const invoice = MOCK_INVOICES[invoiceId];
    if (!invoice) {
      return HttpResponse.json(
        { detail: "Invoice not found" },
        { status: 404 },
      );
    }
    return HttpResponse.json(invoice);
  }),

  // POST /api/v1/invoices/ — create invoice
  // Returns 412 when ?simulate_tax_missing=1 (test hook)
  http.post("/api/v1/invoices/", async ({ request }) => {
    const url = new URL(request.url);
    if (url.searchParams.get("simulate_tax_missing") === "1") {
      return HttpResponse.json(
        {
          detail:
            "Tax jurisdiction not configured. Please configure tax settings before creating invoices.",
        },
        { status: 412 },
      );
    }
    const body = (await request.json()) as Record<string, unknown>;
    const newInvoice = {
      id: "inv-new-0000-0000-0000-000000000099",
      tenant_id: "t-00000001-0000-0000-0000-000000000001",
      invoice_number: "INV-20260616-0099",
      customer_id: "c-00000001-0000-0000-0000-000000000001",
      site_id: null,
      status_id: "st-draft-0000-0000-0000-000000000001",
      status_code: "draft",
      quote_id: body.quote_id ?? null,
      job_id: body.job_id ?? null,
      idempotency_key: body.idempotency_key ?? null,
      issued_at: body.issued_at ?? new Date().toISOString(),
      due_at: body.due_at ?? null,
      subtotal_cents: 0,
      tax_cents: 0,
      total_cents: 0,
      balance_due_cents: 0,
      currency: "USD",
      customer_notes: body.customer_notes ?? null,
      terms_and_conditions: null,
      pdf_object_key: null,
      is_active: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      created_by: null,
      updated_by: null,
      lines: [],
    };
    return HttpResponse.json(newInvoice, { status: 201 });
  }),

  // POST /api/v1/invoices/:invoiceId/send — generate public link
  http.post("/api/v1/invoices/:invoiceId/send", ({ params }) => {
    const { invoiceId } = params as { invoiceId: string };
    const publicLink = {
      id: "pl-00000001-0000-0000-0000-000000000001",
      tenant_id: "t-00000001-0000-0000-0000-000000000001",
      invoice_id: invoiceId,
      contact_id: "c-00000001-0000-0000-0000-000000000001",
      signed_token: "mock-signed-token-abc123",
      expires_at: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
      max_uses: 10,
      used_count: 0,
      status: "active",
      last_used_at: null,
      created_at: new Date().toISOString(),
    };
    return HttpResponse.json(publicLink, { status: 201 });
  }),

  // POST /api/v1/invoices/:invoiceId/record-payment — record payment
  http.post(
    "/api/v1/invoices/:invoiceId/record-payment",
    async ({ params, request }) => {
      const { invoiceId } = params as { invoiceId: string };
      const body = (await request.json()) as Record<string, unknown>;
      const amountCents = Number(body.amount_cents ?? 0);
      const paymentResponse = {
        id: "pay-00000001-0000-0000-0000-000000000001",
        invoice_id: invoiceId,
        tenant_id: "t-00000001-0000-0000-0000-000000000001",
        amount_cents: amountCents,
        paid_via: body.paid_via ?? "other",
        balance_due_cents: 0,
        amount_variance_cents: 0,
        status_id: "fa70374c-513a-4cc3-baca-22a54a594a4d",
        paid_at: body.paid_at ?? new Date().toISOString(),
        idempotency_key: body.idempotency_key ?? null,
        created_at: new Date().toISOString(),
      };
      return HttpResponse.json(paymentResponse, { status: 201 });
    },
  ),

  // GET /api/v1/jobs/:job_id/billable-items — B20 endpoint (FE-B29)
  http.get("/api/v1/jobs/:job_id/billable-items", ({ params }) => {
    const { job_id } = params as { job_id: string };
    return HttpResponse.json({
      job_id,
      job_number: "JOB-000001",
      customer_name: "Acme Electric",
      time_entries: [
        {
          id: "te-00000001-0000-0000-0000-000000000001",
          user_id: "u-00000001-0000-0000-0000-000000000001",
          tech_name: "Jake Rodriguez",
          started_at: "2026-07-01T08:00:00Z",
          ended_at: "2026-07-01T12:00:00Z",
          hours: "4.00",
          hourly_rate_cents: 8500,
          total_cost_cents: 34000,
          notes: "Panel upgrade labor",
          is_already_invoiced: false,
        },
      ],
      expenses: [
        {
          id: "exp-00000001-0000-0000-0000-000000000001",
          description: "Wire 12AWG 50ft",
          cost_cents: 4800,
          billable_cents: 5280,
          is_billable: true,
          is_already_invoiced: false,
          incurred_at: "2026-07-01T09:30:00Z",
        },
      ],
    });
  }),

  // GET /api/v1/reports/ar-aging — AR aging report
  http.get("/api/v1/reports/ar-aging", () => {
    return HttpResponse.json({
      report_type: "ar_aging",
      as_of_date: new Date().toISOString().split("T")[0],
      display_mode: "summary",
      row_count: 9,
      report_chart_threshold: 10,
      summary: {
        current_cents: 245000,
        bucket_31_60_cents: 120000,
        bucket_61_90_cents: 80000,
        bucket_91_plus_cents: 35000,
        total_outstanding_cents: 480000,
      },
      data: [],
    });
  }),
];
