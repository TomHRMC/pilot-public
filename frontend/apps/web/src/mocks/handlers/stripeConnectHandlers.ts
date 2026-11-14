/**
 * MSW handlers — Stripe Connect endpoints
 *
 * Location: apps/web/src/mocks/handlers/stripeConnectHandlers.ts
 *
 * Registered in: mocks/handlers/index.ts
 * Endpoints covered:
 *   GET  /api/v1/settings/billing/stripe-connect/status
 *   POST /api/v1/settings/billing/stripe-connect/onboard
 *   DELETE /api/v1/settings/billing/stripe-connect
 */

import { http, HttpResponse } from "msw";

export const stripeConnectHandlers = [
  // Default: not connected
  http.get("/api/v1/settings/billing/stripe-connect/status", () =>
    HttpResponse.json({
      connected: false,
      account_id: null,
      account_name: null,
      charges_enabled: false,
      payouts_enabled: false,
    }),
  ),

  // Onboard: returns a mock Stripe Account Link URL
  http.post("/api/v1/settings/billing/stripe-connect/onboard", () =>
    HttpResponse.json({
      account_link_url: "https://connect.stripe.com/setup/s/mock_test_link",
      expires_at: Math.floor(Date.now() / 1000) + 600, // 10 min from now
    }),
  ),

  // Disconnect: returns success
  http.delete("/api/v1/settings/billing/stripe-connect", () =>
    HttpResponse.json({
      disconnected: true,
      message:
        "Stripe account disconnected. Customers will see manual payment instructions.",
    }),
  ),
];
