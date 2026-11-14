/**
 * C-B12 MSW Handlers — Charter Upgrade
 *
 * Location: apps/web/src/mocks/handlers/charterUpgradeHandlers.ts
 *
 * Mocks:
 *   - POST /api/v1/tenants/:tenantId/subscription/upgrade-from-charter
 *   - POST /api/v1/tenants/:tenantId/subscription/upgrade-from-charter/test
 *
 * Returns a successful UpgradeFromCharterResponse by default.
 * Supports error simulation via the `X-Mock-Error` request header:
 *   - "no-payment-method" → 400 (no payment method on file)
 *   - "not-charter" → 400 (not a Charter member)
 *   - "stripe-error" → 502 (payment provider error)
 */

import { http, HttpResponse, delay } from "msw";

const TENANTS_API = "/api/v1/tenants";

function buildSuccessResponse(billingInterval: string) {
  return {
    psp_subscription_id: "sub_test_mock",
    new_tier_name: "teams",
    billing_interval: billingInterval,
    charter_eligible_forfeited: true,
  };
}

export const charterUpgradeHandlers = [
  http.post(
    `${TENANTS_API}/:tenantId/subscription/upgrade-from-charter`,
    async ({ request }) => {
      const body = (await request.json()) as { billing_interval: string };
      const mockError = request.headers.get("X-Mock-Error");

      await delay(300);

      if (mockError === "no-payment-method") {
        return HttpResponse.json(
          {
            type: "https://errors.pilotfortrades.com/no-payment-method",
            title: "No payment method on file.",
            status: 400,
            detail: "No payment method on file. Add a card before upgrading.",
          },
          { status: 400 },
        );
      }

      if (mockError === "not-charter") {
        return HttpResponse.json(
          {
            type: "https://errors.pilotfortrades.com/not-charter",
            title: "Not a Charter member.",
            status: 400,
            detail:
              "This account is no longer eligible for the Charter upgrade.",
          },
          { status: 400 },
        );
      }

      if (mockError === "stripe-error") {
        return HttpResponse.json(
          {
            type: "https://errors.pilotfortrades.com/stripe-error",
            title: "Payment provider error.",
            status: 502,
            detail:
              "Upgrade failed due to a payment provider error. Please try again or contact support.",
          },
          { status: 502 },
        );
      }

      return HttpResponse.json(buildSuccessResponse(body.billing_interval));
    },
  ),

  http.post(
    `${TENANTS_API}/:tenantId/subscription/upgrade-from-charter/test`,
    async ({ request }) => {
      const body = (await request.json()) as { billing_interval: string };
      return HttpResponse.json({
        psp_subscription_id: "test_sub_mock_id",
        new_tier_name: "teams",
        billing_interval: body.billing_interval,
        charter_eligible_forfeited: true,
      });
    },
  ),
];
