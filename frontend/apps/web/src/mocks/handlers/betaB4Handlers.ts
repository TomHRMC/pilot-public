/**
 * BETA-B4 MSW Handlers
 *
 * Location: apps/web/src/mocks/handlers/betaB4Handlers.ts
 *
 * Covers backend gaps for BETA-B4:
 *  - GET  /api/v1/settings/tenant/mfa-required (BETA-B4-BE-03)
 *  - PUT  /api/v1/settings/tenant/mfa-required (augments existing PUT)
 *  - GET  /api/v1/users (team user list)
 *  - POST /api/v1/users/:userId/role (role assignment)
 *  - GET  /api/v1/tenants/:tenantId/subscription
 *  - POST /api/v1/tenants/:tenantId/subscription/change-tier
 *  - GET  /api/v1/integrations/quickbooks/status
 *  - GET  /api/v1/integrations/quickbooks/connect
 *  - DELETE /api/v1/integrations/quickbooks/disconnect
 *  - GET  /api/v1/integrations/calendar/status
 *  - GET  /api/v1/integrations/sync-dashboard/
 *  - GET  /api/v1/tenants/:tenantId/phone-numbers/
 *  - GET  /api/v1/notifications/in-app/recent
 *  - POST /api/v1/notifications/in-app/mark-read
 */

import { http, HttpResponse } from "msw";

// Mutable state for simulating toggle changes
let tenantMfaRequired = false;
let gracePeriodStartsAt: string | null = null;
let qbConnected = true;

const TEAM_USERS = [
  {
    user_id: "user-001",
    email: "owner@example.com",
    first_name: "Tom",
    last_name: "Owner",
    display_color: "#4F86C6", // eslint-disable-line pilot/no-hardcoded-design-values
    role_code: "owner",
    role_name: "Owner",
    permissions: ["settings.manage", "billing.view"],
    joined_at: "2025-01-15T10:00:00Z",
    is_active: true,
  },
  {
    user_id: "user-002",
    email: "tech@example.com",
    first_name: "Mike",
    last_name: "Sparks",
    display_color: "#E8724A", // eslint-disable-line pilot/no-hardcoded-design-values
    role_code: "technician",
    role_name: "Field Technician",
    permissions: [
      "mfa.enroll_self",
      "account.session.view_own",
      "account.session.revoke_own",
      "help_chat.delete_own_history",
    ],
    joined_at: "2025-03-01T09:00:00Z",
    is_active: true,
  },
  {
    user_id: "user-003",
    email: "office@example.com",
    first_name: "Sarah",
    last_name: "Jones",
    display_color: "#52C077", // eslint-disable-line pilot/no-hardcoded-design-values
    role_code: "office_staff",
    role_name: "Office Staff",
    permissions: ["quotes.approve", "invoices.approve"],
    joined_at: "2025-04-10T14:00:00Z",
    is_active: true,
  },
];

// Export TEAM_USERS for use in other test files
export { TEAM_USERS };

const SUBSCRIPTION_FIXTURE = {
  current_tier: {
    tier_id: "tier-starter",
    tier_name: "starter",
    display_label: "Starter",
    monthly_price_cents: 5900,
    annual_price_cents: 58800,
    is_trial: true,
    trial_duration_days: 14,
    schedule_lanes: 5,
    display_order: 10,
    is_active: true,
    free_period_days: null,
    requires_payment_method: true,
    signup_cap: null,
    price_locked: false,
  },
  trial_ends_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
  stripe_customer_id: null,
  usage: {
    current_user_count: 3,
    current_sms_segments: 42,
  },
  tier_override: null,
  // PLP-FIX-5 (Issue 8): plan_summary — an "active" monthly example for tests
  plan_summary: {
    status_code: "active",
    status_name: "Active",
    is_billing_active: true,
    billing_interval: "monthly",
    renews_at: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
    free_period_ends_at: null,
  },
  charter_eligible: false,
  limits: {
    outbound_sms_segments: 100,
    schedule_lanes: 5,
    voice_ai_minutes: 90,
  },
};

const IN_APP_NOTIFICATIONS = [
  {
    notification_id: "notif-001",
    category: "job_status",
    title: "Job completed",
    body: "Technician Mike marked the job as complete.",
    is_read: false,
    created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    deep_link_href: "/jobs/job-1042",
  },
  {
    notification_id: "notif-002",
    category: "quote_approved",
    title: "Quote approved",
    body: "Customer approved the quote.",
    is_read: true,
    created_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    deep_link_href: "/quotes/quote-2024-0187",
  },
];

const SETTINGS_API = "/api/v1/settings";
const USERS_API = "/api/v1/users";
const TENANTS_API = "/api/v1/tenants";
const INTEGRATIONS_API = "/api/v1/integrations";
const NOTIFICATIONS_API = "/api/v1/notifications";

export const betaB4Handlers = [
  // ─── Tenant MFA Policy (BETA-B4-BE-03) ────────────────────────────────────
  http.get(`${SETTINGS_API}/tenant/mfa-required`, () => {
    return HttpResponse.json({
      tenant_mfa_required: tenantMfaRequired,
      grace_period_starts_at: gracePeriodStartsAt,
    });
  }),

  http.put(`${SETTINGS_API}/tenant/mfa-required`, async ({ request }) => {
    const body = (await request.json()) as { tenant_mfa_required: boolean };
    tenantMfaRequired = body.tenant_mfa_required;
    gracePeriodStartsAt = tenantMfaRequired ? new Date().toISOString() : null;
    return HttpResponse.json({
      tenant_mfa_required: tenantMfaRequired,
      grace_period_starts_at: gracePeriodStartsAt,
    });
  }),

  // ─── Team Users ────────────────────────────────────────────────────────────
  http.get(USERS_API, () => {
    return HttpResponse.json(TEAM_USERS);
  }),

  http.post(`${USERS_API}/:userId/role`, async ({ params, request }) => {
    const { userId } = params as { userId: string };
    const body = (await request.json()) as { role_code: string };
    const user = TEAM_USERS.find((u) => u.user_id === userId);
    if (!user) {
      return HttpResponse.json({ detail: "User not found" }, { status: 404 });
    }
    user.role_code = body.role_code;
    return HttpResponse.json({ user_id: userId, role_code: body.role_code });
  }),

  // ─── Subscription ──────────────────────────────────────────────────────────
  http.get(`${TENANTS_API}/:tenantId/subscription`, () => {
    return HttpResponse.json(SUBSCRIPTION_FIXTURE);
  }),

  http.post(
    `${TENANTS_API}/:tenantId/subscription/change-tier`,
    async ({ request }) => {
      const body = (await request.json()) as { target_tier_id: string };
      return HttpResponse.json({
        ...SUBSCRIPTION_FIXTURE,
        current_tier: {
          ...SUBSCRIPTION_FIXTURE.current_tier,
          tier_id: body.target_tier_id,
          is_trial: false,
        },
        trial_ends_at: null,
      });
    },
  ),

  // ─── QuickBooks ────────────────────────────────────────────────────────────
  http.get(`${INTEGRATIONS_API}/quickbooks/status`, () => {
    return HttpResponse.json({
      connected: qbConnected,
      company_name: qbConnected ? "Acme Electric LLC" : null,
      last_sync_at: qbConnected
        ? new Date(Date.now() - 30 * 60 * 1000).toISOString()
        : null,
      expires_at: qbConnected
        ? new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString()
        : null,
    });
  }),

  http.get(`${INTEGRATIONS_API}/quickbooks/connect`, () => {
    // OAuth redirect — in test, return a mock auth URL
    return HttpResponse.json({
      auth_url: "https://appcenter.intuit.com/connect/oauth2?mock=true",
    });
  }),

  http.delete(`${INTEGRATIONS_API}/quickbooks/disconnect`, () => {
    qbConnected = false;
    return new HttpResponse(null, { status: 204 });
  }),

  // ─── Calendar ─────────────────────────────────────────────────────────────
  http.get(`${INTEGRATIONS_API}/calendar/status`, () => {
    return HttpResponse.json({
      connected: false,
      last_sync_at: null,
    });
  }),

  // ─── Sync Dashboard ───────────────────────────────────────────────────────
  http.get(`${INTEGRATIONS_API}/sync-dashboard/`, () => {
    return HttpResponse.json({
      pending_count: 2,
      error_count: 0,
    });
  }),

  // ─── Phone Numbers (SMS provisioning) ─────────────────────────────────────
  http.get(`${TENANTS_API}/:tenantId/phone-numbers/`, () => {
    return HttpResponse.json([]);
  }),

  // ─── In-App Notifications ─────────────────────────────────────────────────
  http.get(`${NOTIFICATIONS_API}/in-app/recent`, () => {
    return HttpResponse.json(IN_APP_NOTIFICATIONS);
  }),

  http.post(`${NOTIFICATIONS_API}/in-app/mark-read`, () => {
    IN_APP_NOTIFICATIONS.forEach((n) => {
      n.is_read = true;
    });
    return HttpResponse.json({ marked_count: IN_APP_NOTIFICATIONS.length });
  }),
];
