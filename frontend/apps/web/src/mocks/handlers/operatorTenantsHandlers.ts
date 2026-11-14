/**
 * Operator Tenants MSW handlers — C-B15 Part B
 *
 * Location: apps/web/src/mocks/handlers/operatorTenantsHandlers.ts
 *
 * Handlers for the 3 operator tenant/impersonation endpoints:
 *   GET  /api/v1/operator/tenants
 *   POST /api/v1/operator/impersonation/start
 *   POST /api/v1/operator/impersonation/end
 *
 * RULE 13: registered in the barrel index.ts.
 */

import { http, HttpResponse } from "msw";

// ── Mock data — 10 fictional fixture tenants with varied tiers and statuses ──

const MOCK_TENANTS = [
  {
    tenant_id: "tenant-001",
    name: "Acme Electric",
    is_active: true,
    tier_name: "Charter",
    subscription_status: "trialing",
    created_at: "2026-08-01T00:00:00Z",
  },
  {
    tenant_id: "tenant-002",
    name: "Bright Spark LLC",
    is_active: true,
    tier_name: "Charter",
    subscription_status: "active",
    created_at: "2026-07-15T00:00:00Z",
  },
  {
    tenant_id: "tenant-003",
    name: "Delta Wiring",
    is_active: true,
    tier_name: "Pro",
    subscription_status: "past_due",
    created_at: "2026-06-20T00:00:00Z",
  },
  {
    tenant_id: "tenant-004",
    name: "Elite Electrical Services",
    is_active: true,
    tier_name: "Charter",
    subscription_status: "active",
    created_at: "2026-07-01T00:00:00Z",
  },
  {
    tenant_id: "tenant-005",
    name: "Frontier Power Solutions",
    is_active: true,
    tier_name: "Pro",
    subscription_status: "canceled",
    created_at: "2026-05-10T00:00:00Z",
  },
  {
    tenant_id: "tenant-006",
    name: "Greenfield Electric Co",
    is_active: true,
    tier_name: "Charter",
    subscription_status: "trialing",
    created_at: "2026-08-05T00:00:00Z",
  },
  {
    tenant_id: "tenant-007",
    name: "Highland Wiring Inc",
    is_active: true,
    tier_name: "Starter",
    subscription_status: null,
    created_at: "2026-08-07T00:00:00Z",
  },
  {
    tenant_id: "tenant-008",
    name: "Ironclad Electrical",
    is_active: true,
    tier_name: "Pro",
    subscription_status: "active",
    created_at: "2026-04-12T00:00:00Z",
  },
  {
    tenant_id: "tenant-009",
    name: "Junction City Electric",
    is_active: true,
    tier_name: "Charter",
    subscription_status: "paused",
    created_at: "2026-03-18T00:00:00Z",
  },
  {
    tenant_id: "tenant-010",
    name: "Keystone Power Systems",
    is_active: false,
    tier_name: "Pro",
    subscription_status: "canceled",
    created_at: "2026-01-22T00:00:00Z",
  },
];

export const operatorTenantsHandlers = [
  // GET /api/v1/operator/tenants
  http.get("/api/v1/operator/tenants", () => {
    return HttpResponse.json({ tenants: MOCK_TENANTS });
  }),

  // POST /api/v1/operator/impersonation/start
  http.post("/api/v1/operator/impersonation/start", async ({ request }) => {
    const body = (await request.json()) as { tenant_id: string };

    // 404 — tenant not found
    if (body.tenant_id === "tenant-not-found") {
      return HttpResponse.json(
        {
          type: "https://errors.pilotfortrades.com/tenant-not-found",
          title: "Tenant not found",
          status: 404,
          detail: "This tenant no longer exists.",
        },
        { status: 404 },
      );
    }

    // 409 — tenant inactive
    if (body.tenant_id === "tenant-010") {
      return HttpResponse.json(
        {
          type: "https://errors.pilotfortrades.com/tenant-inactive",
          title: "Tenant is inactive",
          status: 409,
          detail: "This tenant is inactive and cannot be impersonated.",
        },
        { status: 409 },
      );
    }

    // 403 — role lacks impersonate_tenant (simulated for accountant test)
    if (body.tenant_id === "tenant-forbidden") {
      return HttpResponse.json(
        {
          type: "https://errors.pilotfortrades.com/impersonation-forbidden",
          title: "Impersonation not permitted",
          status: 403,
          detail: "Your role does not permit impersonation.",
        },
        { status: 403 },
      );
    }

    // Find the tenant for the success response
    const tenant = MOCK_TENANTS.find((t) => t.tenant_id === body.tenant_id);
    const tenantName = tenant?.name ?? "Unknown Tenant";

    return HttpResponse.json({
      tenant_id: body.tenant_id,
      tenant_name: tenantName,
      impersonator_user_id: "uuid-platform-operator",
      role_code: "owner",
      started_at: new Date().toISOString(),
    });
  }),

  // POST /api/v1/operator/impersonation/end
  http.post("/api/v1/operator/impersonation/end", async () => {
    // Always 200 — defensive (client state may have been cleared)
    return HttpResponse.json({ ended: true });
  }),
];
