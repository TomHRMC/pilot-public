/**
 * Catalog MSW Handlers — FE-B20
 *
 * Location: apps/web/src/mocks/handlers/catalogHandlers.ts
 *
 * Covers:
 *   GET/POST   /api/v1/catalog/pricebook
 *   GET/PATCH  /api/v1/catalog/pricebook/:itemId
 *   POST       /api/v1/catalog/pricebook/:itemId/price
 *   GET        /api/v1/catalog/supplier-items
 *   GET/POST   /api/v1/settings/markups
 *   GET/POST   /api/v1/settings         (labor rates)
 *   GET        /api/v1/job-expense-categories
 *
 * Rule 15: module-level fixtures are never mutated by handlers.
 * POST handlers return new objects with generated IDs without modifying shared arrays.
 */

import { http, HttpResponse } from "msw";

// ---------------------------------------------------------------------------
// Fixtures — NEVER mutate these at module level
// ---------------------------------------------------------------------------

const PRICEBOOK_ITEMS = [
  {
    id: "pb-item-1",
    tenant_id: "tenant-test-1",
    sku: "SW-200A",
    name: "200A Service Panel",
    description: "200-amp main service panel with breakers",
    uom_id: null,
    taxability_code: "taxable",
    is_active: true,
    created_at: "2026-06-01T00:00:00Z",
    updated_at: "2026-06-01T00:00:00Z",
    created_by: null,
    updated_by: null,
    current_price: {
      id: 1,
      default_unit_price_cents: 45000,
      valid_period_lower: "2026-06-01T00:00:00Z",
      valid_period_upper: null,
      recorded_at: "2026-06-01T00:00:00Z",
    },
  },
  {
    id: "pb-item-2",
    tenant_id: "tenant-test-1",
    sku: "WIRE-12AWG",
    name: "Wire 12 AWG (ft)",
    description: "12-gauge copper wire per foot",
    uom_id: null,
    taxability_code: "taxable",
    is_active: true,
    created_at: "2026-06-01T00:00:00Z",
    updated_at: "2026-06-01T00:00:00Z",
    created_by: null,
    updated_by: null,
    current_price: {
      id: 2,
      default_unit_price_cents: 85,
      valid_period_lower: "2026-06-01T00:00:00Z",
      valid_period_upper: null,
      recorded_at: "2026-06-01T00:00:00Z",
    },
  },
  {
    id: "pb-item-3",
    tenant_id: "tenant-test-1",
    sku: "LABOR-M",
    name: "Master Electrician Labor",
    description: "Hourly rate for master electrician",
    uom_id: null,
    taxability_code: "exempt",
    is_active: true,
    created_at: "2026-06-01T00:00:00Z",
    updated_at: "2026-06-01T00:00:00Z",
    created_by: null,
    updated_by: null,
    current_price: {
      id: 3,
      default_unit_price_cents: 12000,
      valid_period_lower: "2026-06-01T00:00:00Z",
      valid_period_upper: null,
      recorded_at: "2026-06-01T00:00:00Z",
    },
  },
];

const MARKUPS = {
  items: [
    {
      id: 1,
      tenant_id: "tenant-test-1",
      job_expense_category_code: "materials",
      markup_pct: 20,
      markup_amt_cents: null,
      valid_period_lower: "2026-06-01T00:00:00Z",
      valid_period_upper: null,
      recorded_at: "2026-06-01T00:00:00Z",
      created_by: null,
    },
    {
      id: 2,
      tenant_id: "tenant-test-1",
      job_expense_category_code: "equipment",
      markup_pct: 15,
      markup_amt_cents: null,
      valid_period_lower: "2026-06-01T00:00:00Z",
      valid_period_upper: null,
      recorded_at: "2026-06-01T00:00:00Z",
      created_by: null,
    },
    {
      id: 3,
      tenant_id: "tenant-test-1",
      job_expense_category_code: "permits",
      markup_pct: 0,
      markup_amt_cents: null,
      valid_period_lower: "2026-06-01T00:00:00Z",
      valid_period_upper: null,
      recorded_at: "2026-06-01T00:00:00Z",
      created_by: null,
    },
  ],
  total: 3,
};

const LABOR_RATES = [
  {
    id: 1,
    skill_level_code: "master",
    hourly_rate_cents: 12000,
    burden_pct: "0.15",
    burdened_rate_cents: 13800,
    valid_period_lower: "2026-06-01T00:00:00Z",
    valid_period_upper: null,
    created_at: "2026-06-01T00:00:00Z",
    created_by: null,
  },
  {
    id: 2,
    skill_level_code: "journeyman",
    hourly_rate_cents: 8500,
    burden_pct: "0.15",
    burdened_rate_cents: 9775,
    valid_period_lower: "2026-06-01T00:00:00Z",
    valid_period_upper: null,
    created_at: "2026-06-01T00:00:00Z",
    created_by: null,
  },
  {
    id: 3,
    skill_level_code: "apprentice",
    hourly_rate_cents: 5500,
    burden_pct: "0.15",
    burdened_rate_cents: 6325,
    valid_period_lower: "2026-06-01T00:00:00Z",
    valid_period_upper: null,
    created_at: "2026-06-01T00:00:00Z",
    created_by: null,
  },
];

const SUPPLIER_ITEMS = [
  {
    id: "sup-item-1",
    tenant_id: "tenant-test-1",
    supplier_id: "sup-1",
    sku: "HD-SW200A",
    name: "200A Square D Service Panel",
    description: "Home Depot SKU: 200A service panel",
    uom_id: "uom-ea",
    is_active: true,
  },
  {
    id: "sup-item-2",
    tenant_id: "tenant-test-1",
    supplier_id: "sup-1",
    sku: "HD-WIRE12",
    name: "12 AWG Copper Wire",
    description: "Home Depot SKU: 12 gauge copper wire per spool",
    uom_id: "uom-ft",
    is_active: true,
  },
];

const JOB_EXPENSE_CATEGORIES = {
  categories: [
    { code: "materials", label: "Materials" },
    { code: "equipment", label: "Equipment" },
    { code: "permits", label: "Permits" },
  ],
};

let nextPricebookId = 100;
let nextMarkupId = 100;
let nextLaborRateId = 100;

// ---------------------------------------------------------------------------
// Handlers
// ---------------------------------------------------------------------------

export const catalogHandlers = [
  // GET /api/v1/catalog/pricebook — UI-FIX-1C: returns paginated shape; supports offset, limit, search, is_active
  http.get("*/api/v1/catalog/pricebook", ({ request }) => {
    const url = new URL(request.url);
    const search = url.searchParams.get("search")?.toLowerCase() ?? "";
    const isActiveParam = url.searchParams.get("is_active");
    const offset = parseInt(
      url.searchParams.get("offset") ?? url.searchParams.get("skip") ?? "0",
      10,
    );
    const limit = parseInt(url.searchParams.get("limit") ?? "25", 10);

    let filtered = PRICEBOOK_ITEMS;
    if (search)
      filtered = filtered.filter(
        (i) =>
          i.name.toLowerCase().includes(search) ||
          i.sku.toLowerCase().includes(search) ||
          (i.description ?? "").toLowerCase().includes(search),
      );
    if (isActiveParam === "true")
      filtered = filtered.filter((i) => i.is_active);
    else if (isActiveParam === "false")
      filtered = filtered.filter((i) => !i.is_active);

    const total = filtered.length;
    const items = filtered.slice(offset, offset + limit);
    return HttpResponse.json({ items, total, limit, offset });
  }),

  // POST /api/v1/catalog/pricebook
  http.post("*/api/v1/catalog/pricebook", async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    const newItem = {
      id: `pb-item-${++nextPricebookId}`,
      tenant_id: "tenant-test-1",
      sku: body.sku as string,
      name: body.name as string,
      description: (body.description as string) ?? null,
      uom_id: (body.uom_id as string) ?? null,
      taxability_code: (body.taxability_code as string) ?? null,
      is_active: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      created_by: null,
      updated_by: null,
      current_price: {
        id: nextPricebookId * 10,
        default_unit_price_cents: body.initial_price_cents as number,
        valid_period_lower: new Date().toISOString(),
        valid_period_upper: null,
        recorded_at: new Date().toISOString(),
      },
    };
    return HttpResponse.json(newItem, { status: 201 });
  }),

  // GET /api/v1/catalog/pricebook/:itemId
  http.get("*/api/v1/catalog/pricebook/:itemId", ({ params }) => {
    const item = PRICEBOOK_ITEMS.find((i) => i.id === params.itemId);
    if (!item)
      return HttpResponse.json({ detail: "Not found" }, { status: 404 });
    return HttpResponse.json(item);
  }),

  // PATCH /api/v1/catalog/pricebook/:itemId
  http.patch(
    "*/api/v1/catalog/pricebook/:itemId",
    async ({ params, request }) => {
      const item = PRICEBOOK_ITEMS.find((i) => i.id === params.itemId);
      if (!item)
        return HttpResponse.json({ detail: "Not found" }, { status: 404 });
      const body = (await request.json()) as Record<string, unknown>;
      // Return merged item — do not mutate PRICEBOOK_ITEMS
      return HttpResponse.json({
        ...item,
        ...body,
        updated_at: new Date().toISOString(),
      });
    },
  ),

  // POST /api/v1/catalog/pricebook/:itemId/price
  http.post(
    "*/api/v1/catalog/pricebook/:itemId/price",
    async ({ params, request }) => {
      const item = PRICEBOOK_ITEMS.find((i) => i.id === params.itemId);
      if (!item)
        return HttpResponse.json({ detail: "Not found" }, { status: 404 });
      const body = (await request.json()) as Record<string, unknown>;
      const newPrice = {
        id: nextPricebookId * 100,
        default_unit_price_cents: body.unit_price_cents as number,
        valid_period_lower: body.effective_from as string,
        valid_period_upper: null,
        recorded_at: new Date().toISOString(),
      };
      return HttpResponse.json(newPrice, { status: 201 });
    },
  ),

  // GET /api/v1/catalog/supplier-items
  http.get("*/api/v1/catalog/supplier-items", () => {
    return HttpResponse.json(SUPPLIER_ITEMS);
  }),

  // GET /api/v1/settings/markups
  http.get("*/api/v1/settings/markups", () => {
    return HttpResponse.json(MARKUPS);
  }),

  // POST /api/v1/settings/markups
  http.post("*/api/v1/settings/markups", async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    const newMarkup = {
      id: ++nextMarkupId,
      tenant_id: "tenant-test-1",
      job_expense_category_code: body.job_expense_category_code as string,
      markup_pct: body.markup_pct as number,
      markup_amt_cents: null,
      valid_period_lower:
        (body.effective_from as string) ?? new Date().toISOString(),
      valid_period_upper: null,
      recorded_at: new Date().toISOString(),
      created_by: null,
    };
    return HttpResponse.json(newMarkup, { status: 201 });
  }),

  // GET /api/v1/settings (labor rates — mounted at /api/v1/settings prefix)
  // NOTE: labor_rates router mounts at /api/v1/settings (not /settings/labor-rates)
  // We need a more specific pattern to avoid colliding with other /settings handlers
  http.get("*/api/v1/settings", ({ request }) => {
    const url = new URL(request.url);
    const skillLevelCode = url.searchParams.get("skill_level_code");
    const rates = skillLevelCode
      ? LABOR_RATES.filter((r) => r.skill_level_code === skillLevelCode)
      : LABOR_RATES;
    return HttpResponse.json(rates);
  }),

  // POST /api/v1/settings (labor rates — temporal supersession)
  http.post("*/api/v1/settings", async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    const burdenPct = body.burden_pct as number;
    const hourlyRate = body.hourly_rate_cents as number;
    const newRate = {
      id: ++nextLaborRateId,
      skill_level_code: body.skill_level_code as string,
      hourly_rate_cents: hourlyRate,
      burden_pct: String(burdenPct),
      burdened_rate_cents: Math.round(hourlyRate * (1 + burdenPct)),
      valid_period_lower:
        (body.effective_from as string) ?? new Date().toISOString(),
      valid_period_upper: null,
      created_at: new Date().toISOString(),
      created_by: null,
    };
    return HttpResponse.json(newRate, { status: 201 });
  }),

  // GET /api/v1/job-expense-categories
  http.get("*/api/v1/job-expense-categories", () => {
    return HttpResponse.json(JOB_EXPENSE_CATEGORIES);
  }),
];
