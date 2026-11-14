/**
 * Cohort Dashboard MSW handlers — C-B11 Part B
 *
 * Location: apps/web/src/mocks/handlers/cohortDashboardHandlers.ts
 *
 * Handlers for the 4 operator cohort endpoints:
 *   GET  /api/v1/operator/cohort
 *   POST /api/v1/operator/cohort/{tenant_id}/extend
 *   POST /api/v1/operator/cohort/close
 *   GET  /api/v1/operator/auth/me
 *
 * RULE 13: registered in the barrel index.ts.
 */

import { http, HttpResponse } from "msw";

// ── Mock data (fictional businesses; no real Charter members existed) ────────

const MOCK_COHORT_OVERVIEW = {
  cohort_tier_name: "Charter",
  cohort_is_active: true,
  signup_cap: 12,
  members: [
    {
      tenant_id: "tenant-001",
      business_name: "Acme Electric",
      charter_member_number: 1,
      free_period_ends_at: "2026-11-04T00:00:00Z",
      days_remaining: 90,
      stripe_status: "trialing",
      has_payment_method: false,
      messaging_status: "not_started",
      customer_count: 3,
      invoice_count: 2,
      days_since_last_job: 5,
      last_contact: null,
      alert_level: "none",
    },
    {
      tenant_id: "tenant-002",
      business_name: "Volts & Co",
      charter_member_number: 2,
      free_period_ends_at: "2026-08-14T00:00:00Z",
      days_remaining: 7,
      stripe_status: "trialing",
      has_payment_method: false,
      messaging_status: "active",
      customer_count: 1,
      invoice_count: 0,
      days_since_last_job: 3,
      last_contact: null,
      alert_level: "amber",
    },
    {
      tenant_id: "tenant-003",
      business_name: "Sparky Services",
      charter_member_number: 3,
      free_period_ends_at: "2026-12-01T00:00:00Z",
      days_remaining: 120,
      stripe_status: "trialing",
      has_payment_method: false,
      messaging_status: "not_started",
      customer_count: 0,
      invoice_count: 0,
      days_since_last_job: null,
      last_contact: null,
      alert_level: "red",
    },
  ],
};

const MOCK_AUTH_ME_PLATFORM = {
  user_type: "platform",
  user_id: "uuid-platform",
  email: "tom@pilotfortrades.com",
  first_name: "Tom",
  last_name: "Owner",
  platform_role_code: "owner",
  redirect_to: "/operator/cohort",
};

// Mutable state for cohort close simulation
let cohortClosed = false;

export const cohortDashboardHandlers = [
  // GET /api/v1/operator/cohort
  http.get("/api/v1/operator/cohort", () => {
    return HttpResponse.json({
      ...MOCK_COHORT_OVERVIEW,
      cohort_is_active: !cohortClosed,
    });
  }),

  // POST /api/v1/operator/cohort/:tenantId/extend
  http.post(
    "/api/v1/operator/cohort/:tenantId/extend",
    async ({ request, params }) => {
      const body = (await request.json()) as {
        new_free_period_ends_at: string;
        override_reason: string;
      };

      const tenantId = params.tenantId as string;

      // Simulate 409 if the member is not trialing (tenant-003 is "red" but still trialing)
      // For test edge cases, check a special tenant id
      if (tenantId === "tenant-not-trialing") {
        return HttpResponse.json(
          {
            type: "https://errors.pilotfortrades.com/cohort-not-trialing",
            title: "Subscription is not trialing",
            status: 409,
            detail:
              "This member's subscription is no longer trialing and cannot be extended.",
          },
          { status: 409 },
        );
      }

      // Simulate 422 if the new date is before the current
      if (body.new_free_period_ends_at < "2026-01-01T00:00:00Z") {
        return HttpResponse.json(
          {
            type: "https://errors.pilotfortrades.com/invalid-date",
            title: "Invalid date",
            status: 422,
            detail: "New date must be after the current end date.",
          },
          { status: 422 },
        );
      }

      return HttpResponse.json({
        tenant_id: tenantId,
        previous_free_period_ends_at: "2026-11-04T00:00:00Z",
        new_free_period_ends_at: body.new_free_period_ends_at,
        stripe_subscription_id: "sub_mock_001",
        stripe_trial_end_updated: true,
      });
    },
  ),

  // POST /api/v1/operator/cohort/close
  http.post("/api/v1/operator/cohort/close", () => {
    if (cohortClosed) {
      return HttpResponse.json(
        {
          type: "https://errors.pilotfortrades.com/cohort-already-closed",
          title: "Cohort already closed",
          status: 409,
          detail: "The Charter cohort is already closed.",
        },
        { status: 409 },
      );
    }
    cohortClosed = true;
    return HttpResponse.json({
      charter_price_archived: true,
      charter_tier_deactivated: true,
      activated_tiers: ["trial", "starter", "teams"],
    });
  }),

  // GET /api/v1/operator/auth/me
  http.get("/api/v1/operator/auth/me", () => {
    return HttpResponse.json(MOCK_AUTH_ME_PLATFORM);
  }),
];
