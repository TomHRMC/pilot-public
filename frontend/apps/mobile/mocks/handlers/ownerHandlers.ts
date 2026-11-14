/**
 * ownerHandlers — MSW handlers for Owner tab sections (MOB-B5)
 *
 * Tier prices and user caps below are fixture values from an earlier pricing
 * draft. Canonical pricing: Starter $59 / Teams $179 monthly ($49 / $149 billed
 * annually), Charter $49, unlimited users.
 *
 * Location: apps/mobile/mocks/handlers/ownerHandlers.ts
 *
 * Fixtures:
 *   - GET /api/v1/quotes?status=pending_approval  → 2 pending quotes
 *   - GET /api/v1/integrations/quickbooks/status  → connected or disconnected (via ?scenario=)
 *   - GET /api/v1/invoices/                       → 3 invoices, 1 overdue
 *   - GET /api/v1/tenants/:tenantId/subscription  → TenantSubscriptionResponse fixture
 */

import { http, HttpResponse } from "msw";

const BASE = "*/api/v1";

const TODAY = new Date().toISOString().slice(0, 10);
const PAST_DATE = new Date(Date.now() - 10 * 86_400_000).toISOString(); // 10 days ago
const FUTURE_DATE = new Date(Date.now() + 20 * 86_400_000).toISOString(); // 20 days from now

// ─── Quotes fixtures ──────────────────────────────────────────────────────────

export const MOCK_PENDING_QUOTES = [
  {
    id: "quote-pending-001",
    tenant_id: "tenant-001",
    customer_id: "customer-001",
    customer_name: "Acme Electric",
    site_id: "site-001",
    status_id: "status-pending-approval",
    status_code: "pending_approval",
    subtotal_cents: 125000,
  },
  {
    id: "quote-pending-002",
    tenant_id: "tenant-001",
    customer_id: "customer-002",
    customer_name: "Jones Commercial",
    site_id: "site-002",
    status_id: "status-pending-approval",
    status_code: "pending_approval",
    subtotal_cents: 87500,
  },
];

// ─── QB status fixtures ───────────────────────────────────────────────────────

export const MOCK_QB_CONNECTED = {
  is_connected: true,
  realm_id: "1234567890123456",
  company_name: "Acme Electrical LLC",
  connected_at: "2026-05-01T12:00:00Z",
  expires_at: "2026-08-01T12:00:00Z",
  connection_status: "active",
};

export const MOCK_QB_DISCONNECTED = {
  is_connected: false,
  realm_id: null,
  company_name: null,
  connected_at: null,
  expires_at: null,
  connection_status: "not_configured",
};

// ─── Invoice fixtures ─────────────────────────────────────────────────────────

export const MOCK_INVOICES = {
  items: [
    {
      id: "invoice-001",
      invoice_number: "INV-0041",
      customer_id: "customer-001",
      site_id: "site-001",
      status_id: "status-sent",
      status_code: "sent",
      issued_at: new Date(Date.now() - 30 * 86_400_000).toISOString(),
      due_at: PAST_DATE, // overdue
      subtotal_cents: 150000,
      tax_cents: 12000,
      total_cents: 162000,
      balance_due_cents: 162000,
      currency: "USD",
      quote_id: null,
      job_id: "job-001",
      created_at: new Date(Date.now() - 31 * 86_400_000).toISOString(),
      updated_at: new Date(Date.now() - 30 * 86_400_000).toISOString(),
    },
    {
      id: "invoice-002",
      invoice_number: "INV-0042",
      customer_id: "customer-002",
      site_id: "site-002",
      status_id: "status-sent",
      status_code: "sent",
      issued_at: new Date(Date.now() - 5 * 86_400_000).toISOString(),
      due_at: FUTURE_DATE, // not overdue
      subtotal_cents: 87500,
      tax_cents: 7000,
      total_cents: 94500,
      balance_due_cents: 94500,
      currency: "USD",
      quote_id: null,
      job_id: "job-002",
      created_at: new Date(Date.now() - 6 * 86_400_000).toISOString(),
      updated_at: new Date(Date.now() - 5 * 86_400_000).toISOString(),
    },
    {
      id: "invoice-003",
      invoice_number: "INV-0043",
      customer_id: "customer-003",
      site_id: "site-003",
      status_id: "status-sent",
      status_code: "sent",
      issued_at: new Date(Date.now() - 2 * 86_400_000).toISOString(),
      due_at: FUTURE_DATE, // not overdue
      subtotal_cents: 45000,
      tax_cents: 3600,
      total_cents: 48600,
      balance_due_cents: 48600,
      currency: "USD",
      quote_id: "quote-001",
      job_id: null,
      created_at: new Date(Date.now() - 3 * 86_400_000).toISOString(),
      updated_at: new Date(Date.now() - 2 * 86_400_000).toISOString(),
    },
  ],
  total: 3,
  limit: 50,
  offset: 0,
};

// ─── Subscription fixture ─────────────────────────────────────────────────────

export const MOCK_SUBSCRIPTION = {
  current_tier: {
    tier_id: "tier-starter-001",
    tier_name: "Starter",
    display_label: "Starter Plan",
    monthly_price_cents: 14900,
    is_trial: false,
    trial_duration_days: null,
    max_users: 5,
    max_sms_segments_per_month: 500,
    display_order: 1,
    is_active: true,
  },
  trial_ends_at: null,
  stripe_customer_id: "cus_mock_001",
  usage: {
    period_start: `${TODAY}T00:00:00Z`,
    period_end: new Date(Date.now() + 30 * 86_400_000).toISOString(),
    current_user_count: 3,
    current_sms_segment_count: 42,
  },
  tier_override: null,
};

// ─── Handlers ─────────────────────────────────────────────────────────────────

/** GET /api/v1/quotes — returns PaginatedQuoteListResponse { items, total, limit, offset }
 * Backend changed from plain array to paginated response.
 */
export const getOwnerPendingQuotes = http.get(
  `${BASE}/quotes`,
  ({ request }) => {
    const url = new URL(request.url);
    const status = url.searchParams.get("status");
    if (status === "pending_approval") {
      return HttpResponse.json({
        items: MOCK_PENDING_QUOTES,
        total: MOCK_PENDING_QUOTES.length,
        limit: 100,
        offset: 0,
      });
    }
    // Let other quote handlers take over for non-pending_approval requests
    return HttpResponse.json({ items: [], total: 0, limit: 100, offset: 0 });
  },
);

/**
 * GET /api/v1/integrations/quickbooks/status
 * Use ?scenario=connected or ?scenario=disconnected (default: connected)
 */
export const getQbStatus = http.get(
  `${BASE}/integrations/quickbooks/status`,
  ({ request }) => {
    const url = new URL(request.url);
    const scenario = url.searchParams.get("scenario");
    if (scenario === "disconnected") {
      return HttpResponse.json(MOCK_QB_DISCONNECTED);
    }
    return HttpResponse.json(MOCK_QB_CONNECTED);
  },
);

/** GET /api/v1/invoices/ — returns 3 invoices, 1 overdue */
export const getOwnerInvoices = http.get(`${BASE}/invoices/`, () => {
  return HttpResponse.json(MOCK_INVOICES);
});

/** GET /api/v1/tenants/:tenantId/subscription */
export const getOwnerSubscription = http.get(
  `${BASE}/tenants/:tenantId/subscription`,
  () => {
    return HttpResponse.json(MOCK_SUBSCRIPTION);
  },
);

// ─── Handler array ────────────────────────────────────────────────────────────

// MOB-B5: Owner dashboard sections
export const ownerHandlers = [
  getOwnerPendingQuotes,
  getQbStatus,
  getOwnerInvoices,
  getOwnerSubscription,
];
