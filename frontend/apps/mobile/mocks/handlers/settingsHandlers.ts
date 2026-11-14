/**
 * settingsHandlers — MSW handlers for settings endpoints (MOB-B7)
 *
 * Location: apps/mobile/mocks/handlers/settingsHandlers.ts
 *
 * Covers:
 *   GET /api/v1/settings/loto-policy — LOTO confirmation required setting
 */

import { http, HttpResponse } from "msw";

const BASE = "*/api/v1";

/** GET /api/v1/settings/loto-policy — returns false by default (optional mode) */
export const getLotoPolicy = http.get(`${BASE}/settings/loto-policy`, () => {
  return HttpResponse.json({ loto_confirmation_required: false });
});

/** POST /api/v1/customers/ — create a new customer */
export const postCreateCustomer = http.post(
  `${BASE}/customers/`,
  async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json(
      {
        id: "mob-b7-new-customer",
        tenant_id: "tenant-001",
        is_active: true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        ...body,
      },
      { status: 201 },
    );
  },
);

// MOB-B7: LOTO policy + customer create
export const settingsHandlers = [getLotoPolicy, postCreateCustomer];
