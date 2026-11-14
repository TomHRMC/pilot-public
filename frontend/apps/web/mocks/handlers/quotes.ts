/**
 * MSW handlers for quote approval endpoints
 *
 * Location: apps/web/mocks/handlers/quotes.ts
 *
 * Mocks all 11 approval endpoints listed in batch-fe-b5-design.md §D.
 * Used by integration tests and development.
 */

import { http, HttpResponse } from "msw";
import type { PendingQuoteSummary } from "@/features/quote-approval/hooks/usePendingQuotes";
import type { QuoteDetail } from "@/features/quote-approval/hooks/useQuoteDetail";

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const PENDING_QUOTE_1: PendingQuoteSummary = {
  id: "quote-uuid-1",
  quote_number: "Q-2025-001",
  title: "200A Panel Upgrade",
  status_code: "pending_approval",
  customer_id: "cust-uuid-1",
  customer_name: "Johnson Electric",
  total_cents: 450000,
  subtotal_cents: 420000,
  tax_cents: 30000,
};

const PENDING_QUOTE_2: PendingQuoteSummary = {
  id: "quote-uuid-2",
  quote_number: "Q-2025-002",
  title: "Riverside Condos Rewire",
  status_code: "pending_approval",
  customer_id: "cust-uuid-2",
  customer_name: "Riverside Condos",
  total_cents: 1250000,
  subtotal_cents: 1160000,
  tax_cents: 90000,
};

const QUOTE_DETAIL_1: QuoteDetail = {
  id: "quote-uuid-1",
  quote_number: "Q-2025-001",
  status: "pending_approval",
  submitted_by_user_id: "tech-uuid-1",
  submitted_by_name: "Jake Torres",
  customer_id: "cust-uuid-1",
  customer_name: "Johnson Electric",
  site_id: "site-uuid-1",
  line_items: [
    {
      id: "line-uuid-1",
      description: "200A Panel Upgrade",
      customer_visible: true,
      unit_price_cents: 150000,
      quantity: 1,
      total_cents: 150000,
      line_type: "deliverable",
      qco_line_type_id: "qco-lt-deliverable-0000-0000-000000000001",
    },
    {
      id: "line-uuid-2",
      description: "Labor — 8hrs @ $125/hr",
      customer_visible: true,
      unit_price_cents: 12500,
      quantity: 8,
      total_cents: 100000,
      line_type: "component",
      qco_line_type_id: "qco-lt-component-0000-0000-000000000002",
    },
    {
      id: "line-uuid-3",
      description: "Permit fee",
      customer_visible: true,
      unit_price_cents: 20000,
      quantity: 1,
      total_cents: 20000,
      line_type: "component",
      qco_line_type_id: "qco-lt-component-0000-0000-000000000003",
    },
  ],
  subtotal_cents: 270000,
  tax_cents: 18000,
  total_cents: 288000,
  margin_percent: 42.5,
  submitted_at: new Date(Date.now() - 3 * 3600 * 1000).toISOString(),
  approved_at: null,
  rejected_at: null,
  quote_version_id: "qv-uuid-1",
  has_owner_edits: false,
  require_approval: true,
};

// ─── Handlers ─────────────────────────────────────────────────────────────────

export const quoteHandlers = [
  // GET /api/v1/quotes/pending-approval
  http.get("/api/v1/quotes/pending-approval", () => {
    return HttpResponse.json({
      items: [PENDING_QUOTE_1, PENDING_QUOTE_2],
      total: 2,
    });
  }),

  // GET /api/v1/quotes/:id/detail (aggregated endpoint — PRE-WS3-FIX-01)
  http.get("/api/v1/quotes/:id/detail", ({ params }) => {
    const id = params["id"] as string;
    if (id === "quote-uuid-1") {
      return HttpResponse.json(QUOTE_DETAIL_1);
    }
    return new HttpResponse(null, { status: 404 });
  }),

  // GET /api/v1/quotes/:id (legacy bare endpoint — kept for other consumers)
  http.get("/api/v1/quotes/:id", ({ params }) => {
    const id = params["id"] as string;
    if (id === "quote-uuid-1") {
      return HttpResponse.json(QUOTE_DETAIL_1);
    }
    return new HttpResponse(null, { status: 404 });
  }),

  // POST /api/v1/quotes/:id/approve
  http.post("/api/v1/quotes/:id/approve", () => {
    return HttpResponse.json({
      id: "quote-uuid-1",
      status: "approved",
      quote_version_id: "qv-uuid-1-approved",
      approved_at: new Date().toISOString(),
    });
  }),

  // POST /api/v1/quotes/:id/reject
  http.post("/api/v1/quotes/:id/reject", () => {
    return HttpResponse.json({
      id: "quote-uuid-1",
      status: "rejected",
      rejected_at: new Date().toISOString(),
    });
  }),

  // POST /api/v1/quotes/:id/kickback
  http.post("/api/v1/quotes/:id/kickback", () => {
    return HttpResponse.json({
      id: "quote-uuid-1",
      status: "draft",
      kicked_back_at: new Date().toISOString(),
    });
  }),

  // GET /api/v1/quotes/:id/pending-edits
  http.get("/api/v1/quotes/:id/pending-edits", () => {
    return HttpResponse.json([]);
  }),

  // POST /api/v1/quotes/:id/pending-edits
  http.post("/api/v1/quotes/:id/pending-edits", async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({
      id: "edit-uuid-1",
      quote_id: "quote-uuid-1",
      affected_line_item_id: body["affected_line_item_id"] ?? null,
      edit_type: body["edit_type"] ?? "field_edit",
      field_name: body["field_name"] ?? null,
      old_value: body["old_value"] ?? null,
      new_value: body["new_value"] ?? null,
      created_at: new Date().toISOString(),
    });
  }),

  // PATCH /api/v1/quotes/:id/pending-edits/:editId
  http.patch(
    "/api/v1/quotes/:id/pending-edits/:editId",
    async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      return HttpResponse.json({
        id: "edit-uuid-1",
        quote_id: "quote-uuid-1",
        affected_line_item_id: null,
        edit_type: "field_edit",
        field_name: body["field_name"] ?? null,
        old_value: body["old_value"] ?? null,
        new_value: body["new_value"] ?? null,
        created_at: new Date().toISOString(),
      });
    },
  ),

  // DELETE /api/v1/quotes/:id/pending-edits/:editId
  http.delete("/api/v1/quotes/:id/pending-edits/:editId", () => {
    return new HttpResponse(null, { status: 204 });
  }),

  // DELETE /api/v1/quotes/:id/pending-edits (cancel all)
  http.delete("/api/v1/quotes/:id/pending-edits", () => {
    return new HttpResponse(null, { status: 204 });
  }),

  // GET /api/v1/quotes/:id/comments
  http.get("/api/v1/quotes/:id/comments", () => {
    return HttpResponse.json([]);
  }),

  // GET /api/v1/quotes (tech list)
  http.get("/api/v1/quotes", () => {
    return HttpResponse.json([
      {
        id: "quote-uuid-1",
        quote_number: "Q-2025-001",
        status: "pending_approval",
        customer_name: "Johnson Electric",
        total_cents: 288000,
        submitted_at: new Date(Date.now() - 3 * 3600 * 1000).toISOString(),
        has_owner_edits: false,
        quote_version_id: "qv-uuid-1",
      },
    ]);
  }),
];
