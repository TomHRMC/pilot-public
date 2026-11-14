/**
 * MSW handler for quotes list — BETA-B3 / UI-FIX-1C
 *
 * Location: apps/web/src/mocks/handlers/quotesListHandlers.ts
 *
 * UI-FIX-1C: Updated to return PaginatedResult shape.
 * Added support for: offset, limit, customer_search, title_search params.
 * Mock fixtures updated with title field.
 */

import { http, HttpResponse } from "msw";

const MOCK_QUOTES = [
  {
    id: "q-00000001-0000-0000-0000-000000000001",
    tenant_id: "t-00000001-0000-0000-0000-000000000001",
    customer_id: "c-00000001-0000-0000-0000-000000000001",
    customer_name: "Smith Electrical",
    site_id: "s-00000001-0000-0000-0000-000000000001",
    status_id: "st-00000001-0000-0000-0000-000000000001",
    status_code: "draft",
    title: "Panel Upgrade Q1",
    subtotal_cents: 185000,
    tax_cents: 14800,
    total_cents: 199800,
  },
  {
    id: "q-00000002-0000-0000-0000-000000000002",
    tenant_id: "t-00000001-0000-0000-0000-000000000001",
    customer_id: "c-00000002-0000-0000-0000-000000000002",
    customer_name: "Johnson Home Services",
    site_id: "s-00000002-0000-0000-0000-000000000002",
    status_id: "st-00000002-0000-0000-0000-000000000002",
    status_code: "sent",
    title: "Rewire Master Bedroom",
    subtotal_cents: 320000,
    tax_cents: 25600,
    total_cents: 345600,
  },
  {
    id: "q-00000003-0000-0000-0000-000000000003",
    tenant_id: "t-00000001-0000-0000-0000-000000000001",
    customer_id: "c-00000003-0000-0000-0000-000000000003",
    customer_name: "Martinez Properties LLC",
    site_id: "s-00000003-0000-0000-0000-000000000003",
    status_id: "st-00000003-0000-0000-0000-000000000003",
    status_code: "pending_approval",
    title: "Commercial Lighting Install",
    subtotal_cents: 750000,
    tax_cents: 60000,
    total_cents: 810000,
  },
  {
    id: "q-00000004-0000-0000-0000-000000000004",
    tenant_id: "t-00000001-0000-0000-0000-000000000001",
    customer_id: "c-00000004-0000-0000-0000-000000000004",
    customer_name: "Park Avenue Condos",
    site_id: "s-00000004-0000-0000-0000-000000000004",
    status_id: "st-00000004-0000-0000-0000-000000000004",
    status_code: "expired",
    title: "EV Charger Installation",
    subtotal_cents: 95000,
    tax_cents: 7600,
    total_cents: 102600,
  },
];

export const quotesListHandlers = [
  // GET /api/v1/quotes — paginated list with optional filters (UI-FIX-1C)
  // UI-FIX-2D: added ?customer_id= exact UUID filter
  http.get("/api/v1/quotes", ({ request }) => {
    const url = new URL(request.url);
    const status = url.searchParams.get("status");
    const customerId = url.searchParams.get("customer_id") ?? "";
    const customerSearch =
      url.searchParams.get("customer_search")?.toLowerCase() ?? "";
    const titleSearch =
      url.searchParams.get("title_search")?.toLowerCase() ?? "";
    // Support both offset (canonical) and skip (deprecated alias)
    const offset = parseInt(
      url.searchParams.get("offset") ?? url.searchParams.get("skip") ?? "0",
      10,
    );
    const limit = parseInt(url.searchParams.get("limit") ?? "25", 10);

    let filtered = MOCK_QUOTES;
    if (customerId)
      filtered = filtered.filter((q) => q.customer_id === customerId);
    if (status) filtered = filtered.filter((q) => q.status_code === status);
    if (customerSearch)
      filtered = filtered.filter((q) =>
        (q.customer_name ?? "").toLowerCase().includes(customerSearch),
      );
    if (titleSearch)
      filtered = filtered.filter((q) =>
        (q.title ?? "").toLowerCase().includes(titleSearch),
      );
    // date_from / date_to not applied in mock (no created_at on fixtures)

    const total = filtered.length;
    const items = filtered.slice(offset, offset + limit);

    return HttpResponse.json({ items, total, limit, offset });
  }),
];
