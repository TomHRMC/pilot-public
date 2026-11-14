/**
 * MSW handlers for Quote Builder — FE-B19
 *
 * Location: apps/web/src/mocks/handlers/quoteBuilderHandlers.ts
 *
 * Covers:
 *  - POST /api/v1/quotes/               → create new quote
 *  - GET  /api/v1/quotes/:quoteId/lines → list lines (also from detail)
 *  - POST /api/v1/quotes/:quoteId/lines → add line
 *  - POST /api/v1/quotes/:quoteId/submit-for-approval
 *  - POST /api/v1/quotes/:quoteId/versions/:versionId/public-link
 *  - POST /api/v1/quotes/:quoteId/convert (returns 201)
 *
 * Fixture IDs match quotesListHandlers.ts so list and detail work together.
 * NOTE: Fixture arrays are READ-ONLY. POST handlers merge input with new IDs
 *       and never mutate shared arrays.
 */

import { http, HttpResponse } from "msw";

// ---------------------------------------------------------------------------
// QCO line type IDs from DB (seed data)
// ---------------------------------------------------------------------------
export const QCO_LINE_TYPE_IDS = {
  labor: "65a92851-3635-4d42-a99c-c40f1ab2e52e",
  material: "bb1588c7-e91f-4db8-8497-5d81679bc084",
  misc: "c067e242-84dc-4d73-bdce-84aec6d0bd3a",
  discount: "78d28734-eb44-4a16-9d52-1dfd6a34e061",
  note: "1dd2f395-e703-4247-a57d-08e90e1ffd90",
} as const;

// ---------------------------------------------------------------------------
// Shared fixture quote (draft) used across tests
// ---------------------------------------------------------------------------
const DRAFT_QUOTE_ID = "q-00000001-0000-0000-0000-000000000001";
const DRAFT_VERSION_ID = "qv-00000001-0000-0000-0000-000000000001";

export const MOCK_QUOTE_RESPONSE = {
  id: DRAFT_QUOTE_ID,
  tenant_id: "t-00000001-0000-0000-0000-000000000001",
  customer_id: "c-00000001-0000-0000-0000-000000000001",
  site_id: "s-00000001-0000-0000-0000-000000000001",
  status_id: "st-00000001-0000-0000-0000-000000000001",
  status_code: "draft",
  subtotal_cents: 0,
  tax_cents: 0,
  total_cents: 0,
  currency: "USD",
  is_active: true,
  discount_pct: null,
  discount_amount_cents: null,
  discount_expires_at: null,
  discount_applied_by_user_id: null,
  customer_accepted_at: null,
  customer_acceptance_comment: null,
  customer_declined_at: null,
  customer_decline_comment: null,
  customer_decline_reason: null,
  customer_email_at_action: null,
  expires_at: null,
};

export const MOCK_QUOTE_LINE = {
  id: "ql-00000001-0000-0000-0000-000000000001",
  quote_id: DRAFT_QUOTE_ID,
  version_id: DRAFT_VERSION_ID,
  position: 1,
  qco_line_type_id: QCO_LINE_TYPE_IDS.misc,
  pricebook_item_id: null,
  supplier_id: null,
  supplier_item_id: null,
  taxability_code: null,
  description: "Panel upgrade",
  quantity: 1,
  unit: null,
  unit_price_cents: 120000,
  customer_visible: true,
  parent_line_id: null,
  display_order: 1,
  is_section_header: false,
};

export const MOCK_CONVERT_RESPONSE = {
  job_id: "job-00000001-0000-0000-0000-000000000001",
  quote_id: DRAFT_QUOTE_ID,
  quote_status: "converted",
  job_status_id: "js-00000001-0000-0000-0000-000000000001",
  quote_version_id: DRAFT_VERSION_ID,
};

export const MOCK_PUBLIC_LINK_RESPONSE = {
  id: "pl-00000001-0000-0000-0000-000000000001",
  quote_id: DRAFT_QUOTE_ID,
  contact_id: null,
  url: "https://app.pilotfortrades.com/q/public/test-signed-token-abc123",
  expires_at: null,
  signed_token: "test-signed-token-abc123",
};

// ---------------------------------------------------------------------------
// Handlers
// ---------------------------------------------------------------------------
export const quoteBuilderHandlers = [
  // PLP-FIX-2: GET /api/v1/qco-line-types — line-type lookup consumed by useQcoLineTypes
  http.get("/api/v1/qco-line-types", () =>
    HttpResponse.json([
      {
        id: QCO_LINE_TYPE_IDS.discount,
        code: "discount",
        name: "Discount",
        is_default: false,
        is_active: true,
        is_tenant_override: false,
      },
      {
        id: QCO_LINE_TYPE_IDS.labor,
        code: "labor",
        name: "Labor",
        is_default: true,
        is_active: true,
        is_tenant_override: false,
      },
      {
        id: QCO_LINE_TYPE_IDS.material,
        code: "material",
        name: "Material",
        is_default: false,
        is_active: true,
        is_tenant_override: false,
      },
      {
        id: QCO_LINE_TYPE_IDS.misc,
        code: "misc",
        name: "Misc",
        is_default: false,
        is_active: true,
        is_tenant_override: false,
      },
      {
        id: QCO_LINE_TYPE_IDS.note,
        code: "note",
        name: "Note",
        is_default: false,
        is_active: true,
        is_tenant_override: false,
      },
    ]),
  ),

  // POST /api/v1/quotes/ — create new quote
  http.post("/api/v1/quotes/", async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json(
      {
        ...MOCK_QUOTE_RESPONSE,
        customer_id:
          (body.customer_id as string) ?? MOCK_QUOTE_RESPONSE.customer_id,
        site_id: (body.site_id as string) ?? MOCK_QUOTE_RESPONSE.site_id,
        expires_at: (body.expires_at as string | null) ?? null,
        currency: (body.currency as string) ?? "USD",
      },
      { status: 201 },
    );
  }),

  // GET /api/v1/quotes/:quoteId/lines — list lines for a quote
  http.get("/api/v1/quotes/:quoteId/lines", ({ params }) => {
    const { quoteId } = params as { quoteId: string };
    if (quoteId === DRAFT_QUOTE_ID) {
      return HttpResponse.json([MOCK_QUOTE_LINE]);
    }
    return HttpResponse.json([]);
  }),

  // POST /api/v1/quotes/:quoteId/lines — add line to quote
  // NOTE: No DELETE/PATCH endpoints exist for lines — add-only for persisted quotes
  http.post("/api/v1/quotes/:quoteId/lines", async ({ params, request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    const { quoteId } = params as { quoteId: string };
    return HttpResponse.json(
      {
        ...MOCK_QUOTE_LINE,
        id: `ql-new-${Date.now()}`,
        quote_id: quoteId,
        description: (body.description as string) ?? "",
        quantity: (body.quantity as number) ?? 1,
        unit_price_cents: (body.unit_price_cents as number) ?? 0,
        qco_line_type_id:
          (body.qco_line_type_id as string) ?? QCO_LINE_TYPE_IDS.misc,
        position: (body.position as number) ?? 1,
        customer_visible: (body.customer_visible as boolean) ?? true,
      },
      { status: 201 },
    );
  }),

  // POST /api/v1/quotes/:quoteId/submit-for-approval
  http.post("/api/v1/quotes/:quoteId/submit-for-approval", ({ params }) => {
    const { quoteId } = params as { quoteId: string };
    return HttpResponse.json({
      id: quoteId,
      status_code: "pending_approval",
    });
  }),

  // POST /api/v1/quotes/:quoteId/versions/:versionId/public-link
  http.post(
    "/api/v1/quotes/:quoteId/versions/:versionId/public-link",
    ({ params }) => {
      const { quoteId } = params as { quoteId: string; versionId: string };
      return HttpResponse.json(
        {
          ...MOCK_PUBLIC_LINK_RESPONSE,
          quote_id: quoteId,
        },
        { status: 201 },
      );
    },
  ),

  // POST /api/v1/quotes/:quoteId/convert — returns 201
  http.post("/api/v1/quotes/:quoteId/convert", ({ params }) => {
    const { quoteId } = params as { quoteId: string };
    return HttpResponse.json(
      {
        ...MOCK_CONVERT_RESPONSE,
        quote_id: quoteId,
      },
      { status: 201 },
    );
  }),

  // FE-B24: PATCH /api/v1/quotes/:quoteId — update expires_at, currency
  http.patch("/api/v1/quotes/:quoteId", async ({ params, request }) => {
    const { quoteId } = params as { quoteId: string };
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({
      id: quoteId,
      expires_at: body.expires_at ?? null,
      currency: body.currency ?? "USD",
    });
  }),
];
