/**
 * MSW handlers — Customer + Site CRUD (FE-B18)
 *
 * Location: apps/web/src/mocks/handlers/customerHandlers.ts
 *
 * Fixtures use consistent IDs so GET-after-create logic works across handlers.
 * Customer IDs match the seed data referenced in quotesListHandlers.ts.
 *
 * IMPORTANT: Never mutate the module-level fixture arrays.
 * POST/PATCH handlers return merged objects — they do not modify shared state.
 */

import { http, HttpResponse } from "msw";

// ── Fixtures ──────────────────────────────────────────────────────────────────

export const MOCK_CUSTOMERS = [
  {
    id: "c-00000001-0000-0000-0000-000000000001",
    tenant_id: "t-00000001-0000-0000-0000-000000000001",
    type: "company",
    display_name: "Smith Electrical",
    first_name: null,
    last_name: null,
    company_name: "Smith Electrical LLC",
    email: "smith@example.com",
    mobile_phone: "5551234567",
    is_active: true,
    taxability_code: null,
    sms_opted_out: false,
    sms_opt_out_at: null,
    sms_opt_in_consent: true,
    sms_opt_in_at: "2024-01-15T10:00:00Z",
    sms_opt_in_source: "manual",
  },
  {
    id: "c-00000002-0000-0000-0000-000000000002",
    tenant_id: "t-00000001-0000-0000-0000-000000000001",
    type: "company",
    display_name: "Johnson Home Services",
    first_name: null,
    last_name: null,
    company_name: "Johnson Home Services Inc",
    email: "johnson@example.com",
    mobile_phone: null,
    is_active: true,
    taxability_code: null,
    sms_opted_out: false,
    sms_opt_out_at: null,
    sms_opt_in_consent: true,
    sms_opt_in_at: "2024-02-01T09:00:00Z",
    sms_opt_in_source: "web",
  },
  {
    id: "c-00000003-0000-0000-0000-000000000003",
    tenant_id: "t-00000001-0000-0000-0000-000000000001",
    type: "company",
    display_name: "Martinez Properties LLC",
    first_name: null,
    last_name: null,
    company_name: "Martinez Properties LLC",
    email: "martinez@example.com",
    mobile_phone: "5559876543",
    is_active: true,
    taxability_code: null,
    sms_opted_out: true,
    sms_opt_out_at: "2024-03-10T14:30:00Z",
    sms_opt_in_consent: false,
    sms_opt_in_at: null,
    sms_opt_in_source: null,
  },
  // CUST-UI-B1: person customer for site_type default testing
  {
    id: "c-00000004-0000-0000-0000-000000000004",
    tenant_id: "t-00000001-0000-0000-0000-000000000001",
    type: "person",
    display_name: "John Homeowner",
    first_name: "John",
    last_name: "Homeowner",
    company_name: null,
    email: "john.homeowner@example.com",
    mobile_phone: null,
    is_active: true,
    taxability_code: null,
    sms_opted_out: false,
    sms_opt_out_at: null,
    sms_opt_in_consent: false,
    sms_opt_in_at: null,
    sms_opt_in_source: null,
  },
];

export const MOCK_SITES = [
  {
    id: "site-00000001-0000-0000-0000-000000000001",
    tenant_id: "t-00000001-0000-0000-0000-000000000001",
    customer_id: "c-00000001-0000-0000-0000-000000000001",
    name: "Main Office",
    notes: "Primary commercial location",
    jurisdiction_code: "TX-AUSTIN",
    is_active: true,
    site_type: "commercial",
    address: {
      id: "addr-00000001-0000-0000-0000-000000000001",
      line1: "123 Main St",
      line2: null,
      line3: null,
      city: "Austin",
      state: "TX",
      postal_code: "78701",
      country: "US",
      latitude: 30.2672,
      longitude: -97.7431,
      is_active: true,
      created_at: "2024-01-15T10:00:00Z",
      updated_at: "2024-01-15T10:00:00Z",
    },
  },
  {
    id: "site-00000002-0000-0000-0000-000000000002",
    tenant_id: "t-00000001-0000-0000-0000-000000000001",
    customer_id: "c-00000001-0000-0000-0000-000000000001",
    name: "Warehouse",
    notes: "Storage and staging area",
    jurisdiction_code: null,
    is_active: true,
    site_type: "industrial",
    address: {
      id: "addr-00000002-0000-0000-0000-000000000002",
      line1: "456 Industrial Dr",
      line2: null,
      line3: null,
      city: "Austin",
      state: "TX",
      postal_code: "78741",
      country: "US",
      latitude: null,
      longitude: null,
      is_active: true,
      created_at: "2024-01-20T10:00:00Z",
      updated_at: "2024-01-20T10:00:00Z",
    },
  },
  {
    id: "site-00000003-0000-0000-0000-000000000003",
    tenant_id: "t-00000001-0000-0000-0000-000000000001",
    customer_id: "c-00000002-0000-0000-0000-000000000002",
    name: "Johnson HQ",
    notes: null,
    jurisdiction_code: null,
    is_active: true,
    site_type: "commercial",
    address: null,
  },
  // CUST-UI-B1: residential site for person customer
  {
    id: "site-00000004-0000-0000-0000-000000000004",
    tenant_id: "t-00000001-0000-0000-0000-000000000001",
    customer_id: "c-00000004-0000-0000-0000-000000000004",
    name: "Home",
    notes: null,
    jurisdiction_code: null,
    is_active: true,
    site_type: "residential",
    address: null,
  },
  // CUST-UI-B1: site without site_type (null) for omit-chip test
  {
    id: "site-00000005-0000-0000-0000-000000000005",
    tenant_id: "t-00000001-0000-0000-0000-000000000001",
    customer_id: "c-00000001-0000-0000-0000-000000000001",
    name: "Temporary Site",
    notes: null,
    jurisdiction_code: null,
    is_active: true,
    site_type: null,
    address: null,
  },
];

// ── Handlers ──────────────────────────────────────────────────────────────────

export const customerHandlers = [
  // GET /api/v1/customers/ — paginated list with optional search + status filter (UI-FIX-1C)
  http.get("/api/v1/customers/", ({ request }) => {
    const url = new URL(request.url);
    const search = url.searchParams.get("search")?.toLowerCase() ?? "";
    const status = url.searchParams.get("status") ?? "";
    // Support both offset (canonical) and skip (deprecated alias)
    const offset = parseInt(
      url.searchParams.get("offset") ?? url.searchParams.get("skip") ?? "0",
      10,
    );
    const limit = parseInt(url.searchParams.get("limit") ?? "25", 10);

    let filtered = search
      ? MOCK_CUSTOMERS.filter(
          (c) =>
            c.display_name.toLowerCase().includes(search) ||
            c.email?.toLowerCase().includes(search) ||
            c.company_name?.toLowerCase().includes(search),
        )
      : MOCK_CUSTOMERS;

    if (status === "active") {
      filtered = filtered.filter((c) => c.is_active);
    } else if (status === "inactive") {
      filtered = filtered.filter((c) => !c.is_active);
    }

    const total = filtered.length;
    const items = filtered.slice(offset, offset + limit);

    return HttpResponse.json({ items, total, limit, offset });
  }),

  // GET /api/v1/customers/:customerId — single customer
  http.get("/api/v1/customers/:customerId", ({ params }) => {
    const { customerId } = params as { customerId: string };
    const customer = MOCK_CUSTOMERS.find((c) => c.id === customerId);
    if (!customer) {
      return HttpResponse.json(
        { detail: "Customer not found" },
        { status: 404 },
      );
    }
    return HttpResponse.json(customer);
  }),

  // POST /api/v1/customers/ — create customer
  http.post("/api/v1/customers/", async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    const newCustomer = {
      id: `c-new-${Date.now()}-0000-0000-0000-000000000000`,
      tenant_id: "t-00000001-0000-0000-0000-000000000001",
      type: (body.type as string) ?? "person",
      display_name: (body.display_name as string) ?? "",
      first_name: (body.first_name as string | null) ?? null,
      last_name: (body.last_name as string | null) ?? null,
      company_name: (body.company_name as string | null) ?? null,
      email: (body.email as string | null) ?? null,
      mobile_phone: (body.mobile_phone as string | null) ?? null,
      is_active: true,
      taxability_code: null,
      sms_opted_out: false,
      sms_opt_out_at: null,
      sms_opt_in_consent: false,
      sms_opt_in_at: null,
      sms_opt_in_source: null,
    };
    return HttpResponse.json(newCustomer, { status: 201 });
  }),

  // PATCH /api/v1/customers/:customerId — update customer
  http.patch("/api/v1/customers/:customerId", async ({ params, request }) => {
    const { customerId } = params as { customerId: string };
    const body = (await request.json()) as Record<string, unknown>;
    const existing = MOCK_CUSTOMERS.find((c) => c.id === customerId);
    if (!existing) {
      return HttpResponse.json(
        { detail: "Customer not found" },
        { status: 404 },
      );
    }
    // Return merged — never mutate existing fixture
    return HttpResponse.json({ ...existing, ...body });
  }),

  // DELETE /api/v1/customers/:customerId
  http.delete("/api/v1/customers/:customerId", ({ params }) => {
    const { customerId } = params as { customerId: string };
    const exists = MOCK_CUSTOMERS.some((c) => c.id === customerId);
    if (!exists) {
      return HttpResponse.json(
        { detail: "Customer not found" },
        { status: 404 },
      );
    }
    return new HttpResponse(null, { status: 204 });
  }),

  // GET /api/v1/sites/ — list sites (optional customer_id filter)
  http.get("/api/v1/sites/", ({ request }) => {
    const url = new URL(request.url);
    const customerId = url.searchParams.get("customer_id");

    const filtered = customerId
      ? MOCK_SITES.filter((s) => s.customer_id === customerId)
      : MOCK_SITES;

    return HttpResponse.json(filtered);
  }),

  // GET /api/v1/sites/:siteId — single site
  http.get("/api/v1/sites/:siteId", ({ params }) => {
    const { siteId } = params as { siteId: string };
    const site = MOCK_SITES.find((s) => s.id === siteId);
    if (!site) {
      return HttpResponse.json({ detail: "Site not found" }, { status: 404 });
    }
    return HttpResponse.json(site);
  }),

  // POST /api/v1/sites/ — create site
  http.post("/api/v1/sites/", async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    const newSite = {
      id: `site-new-${Date.now()}-0000-0000-0000-000000000000`,
      tenant_id: "t-00000001-0000-0000-0000-000000000001",
      customer_id: (body.customer_id as string) ?? "",
      name: (body.name as string | null) ?? null,
      notes: (body.notes as string | null) ?? null,
      jurisdiction_code: (body.jurisdiction_code as string | null) ?? null,
      is_active: true,
      site_type: (body.site_type as string | null) ?? null,
      address: (body.address as Record<string, unknown> | null) ?? null,
    };
    return HttpResponse.json(newSite, { status: 201 });
  }),

  // PATCH /api/v1/sites/:siteId — update site
  http.patch("/api/v1/sites/:siteId", async ({ params, request }) => {
    const { siteId } = params as { siteId: string };
    const body = (await request.json()) as Record<string, unknown>;
    const existing = MOCK_SITES.find((s) => s.id === siteId);
    if (!existing) {
      return HttpResponse.json({ detail: "Site not found" }, { status: 404 });
    }
    // Return merged — never mutate existing fixture
    return HttpResponse.json({ ...existing, ...body });
  }),
];
