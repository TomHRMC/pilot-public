/**
 * customersHandlers — MSW handlers for customers + sites endpoints (MOB-B3)
 *
 * Location: apps/mobile/mocks/handlers/customersHandlers.ts
 *
 * Covers:
 *   GET /api/v1/customers/         — list with optional ?search= param
 *   GET /api/v1/customers/:id      — single customer detail
 *   GET /api/v1/sites/             — with ?customer_id= filter
 *
 * Fixtures:
 *   - 2 residential customers (customer-001, customer-002)
 *   - 1 commercial customer (customer-003)
 *   - 2 sites for customer-001
 */

import { http, HttpResponse } from "msw";

const BASE = "*/api/v1";

// ── Customer fixtures ─────────────────────────────────────────────────────────

export const MOCK_CUSTOMER_ID = "customer-001";

export const CUSTOMER_JOHN_SMITH = {
  id: "customer-001",
  tenant_id: "tenant-001",
  type: "residential",
  display_name: "John Smith",
  first_name: "John",
  last_name: "Smith",
  company_name: null,
  email: "john.smith@example.com",
};

export const CUSTOMER_JANE_DOE = {
  id: "customer-002",
  tenant_id: "tenant-001",
  type: "residential",
  display_name: "Jane Doe",
  first_name: "Jane",
  last_name: "Doe",
  company_name: null,
  email: null,
};

export const CUSTOMER_ACME_CORP = {
  id: "customer-003",
  tenant_id: "tenant-001",
  type: "commercial",
  display_name: "Acme Corp",
  first_name: null,
  last_name: null,
  company_name: "Acme Corp",
  email: "billing@acme.example.com",
};

export const ALL_CUSTOMER_FIXTURES = [
  CUSTOMER_JOHN_SMITH,
  CUSTOMER_JANE_DOE,
  CUSTOMER_ACME_CORP,
];

// ── Site fixtures for customer-001 ────────────────────────────────────────────

export const SITE_MAIN_HOME = {
  id: "site-001",
  tenant_id: "tenant-001",
  customer_id: "customer-001",
  name: "Main Home",
  notes: null,
  jurisdiction_code: "IL",
  is_active: true,
  address: {
    id: "address-001",
    line1: "123 Main St",
    line2: null,
    line3: null,
    city: "Springfield",
    state: "IL",
    postal_code: "62701",
    country: "US",
    latitude: 39.7817,
    longitude: -89.6501,
    is_active: true,
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
  },
};

export const SITE_RENTAL_PROPERTY = {
  id: "site-002",
  tenant_id: "tenant-001",
  customer_id: "customer-001",
  name: "Rental Property",
  notes: "Gate code: 1234",
  jurisdiction_code: "IL",
  is_active: true,
  address: {
    id: "address-002",
    line1: "456 Oak Ave",
    line2: null,
    line3: null,
    city: "Springfield",
    state: "IL",
    postal_code: "62702",
    country: "US",
    latitude: 39.79,
    longitude: -89.645,
    is_active: true,
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
  },
};

// ── Handlers ──────────────────────────────────────────────────────────────────

/** GET /api/v1/customers/ — list with optional ?search= filter
 * Backend returns PaginatedCustomerResponse { items, total, limit, offset }
 */
export const getCustomersList = http.get(
  `${BASE}/customers/`,
  ({ request }) => {
    const url = new URL(request.url);
    const search = url.searchParams.get("search")?.toLowerCase() ?? "";

    const results = search
      ? ALL_CUSTOMER_FIXTURES.filter(
          (c) =>
            c.display_name.toLowerCase().includes(search) ||
            (c.email ?? "").toLowerCase().includes(search) ||
            (c.company_name ?? "").toLowerCase().includes(search),
        )
      : ALL_CUSTOMER_FIXTURES;

    return HttpResponse.json({
      items: results,
      total: results.length,
      limit: 50,
      offset: 0,
    });
  },
);

export const getCustomersListEmpty = http.get(`${BASE}/customers/`, () => {
  return HttpResponse.json({ items: [], total: 0, limit: 50, offset: 0 });
});

export const getCustomersListError = http.get(`${BASE}/customers/`, () => {
  return HttpResponse.json(
    { detail: "Internal server error" },
    { status: 500 },
  );
});

/** GET /api/v1/customers/:customerId — single customer detail */
export const getCustomerDetail = http.get(
  `${BASE}/customers/:customerId`,
  ({ params }) => {
    const { customerId } = params as { customerId: string };
    const customer = ALL_CUSTOMER_FIXTURES.find((c) => c.id === customerId);
    if (!customer) {
      return HttpResponse.json({ detail: "Not found" }, { status: 404 });
    }
    return HttpResponse.json(customer);
  },
);

export const getCustomerDetailError = http.get(
  `${BASE}/customers/:customerId`,
  () => {
    return HttpResponse.json(
      { detail: "Internal server error" },
      { status: 500 },
    );
  },
);

/** GET /api/v1/sites/ — filtered by ?customer_id= */
export const getSitesByCustomer = http.get(`${BASE}/sites/`, ({ request }) => {
  const url = new URL(request.url);
  const customerId = url.searchParams.get("customer_id");

  if (customerId === "customer-001") {
    return HttpResponse.json([SITE_MAIN_HOME, SITE_RENTAL_PROPERTY]);
  }

  return HttpResponse.json([]);
});

export const getSitesByCustomerError = http.get(`${BASE}/sites/`, () => {
  return HttpResponse.json(
    { detail: "Internal server error" },
    { status: 500 },
  );
});

// ── MOB-B3: Customers list + detail + sites ───────────────────────────────────
export const customersHandlers = [
  getCustomersList,
  getCustomerDetail,
  getSitesByCustomer,
];
