/**
 * MSW handlers — Billing Payment Contact (STRIPE-CONNECT-1-C B5)
 *
 * Location: apps/web/src/mocks/handlers/billingPaymentContactHandlers.ts
 *
 * Registered in: mocks/handlers/index.ts
 * Endpoints covered:
 *   GET   /api/v1/settings/billing/payment-contact
 *   PATCH /api/v1/settings/billing/payment-contact
 *
 * Authed surface — relative paths are correct for the web app (apiClient.baseURL
 * points to localhost:8000, same origin).
 */

import { http, HttpResponse } from "msw";

export const billingPaymentContactHandlers = [
  // GET — default fixture has both contact fields present
  http.get("/api/v1/settings/billing/payment-contact", () =>
    HttpResponse.json({
      billing_contact_phone: "(804) 555-0142",
      billing_contact_email: "billing@example.com",
    }),
  ),

  // PATCH — echoes back the submitted values (null when empty = cleared)
  http.patch(
    "/api/v1/settings/billing/payment-contact",
    async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      return HttpResponse.json({
        billing_contact_phone: body.billing_contact_phone ?? null,
        billing_contact_email: body.billing_contact_email ?? null,
      });
    },
  ),
];
