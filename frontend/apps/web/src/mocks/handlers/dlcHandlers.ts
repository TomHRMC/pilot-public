/**
 * DLC MSW handlers — DLC-1
 *
 * Location: apps/web/src/mocks/handlers/dlcHandlers.ts
 *
 * Handlers for the 10DLC profile endpoints:
 *   GET  /api/v1/settings/10dlc-profile
 *   PUT  /api/v1/settings/10dlc-profile
 */

import { http, HttpResponse } from "msw";

const MOCK_DLC_PROFILE = {
  tenant_id: "t-test-001",
  legal_business_name: "Smith Electrical LLC",
  dba_name: null,
  ein_masked: "**-***1234",
  hq_address_line1: "123 Main Street",
  hq_address_line2: null,
  hq_city: "Denver",
  hq_state: "CO",
  hq_postal_code: "80202",
  hq_country: "US",
  support_email: "support@smithelectrical.example.com",
  support_phone: "+13035550000",
  updated_at: "2026-07-05T18:00:00Z",
};

export const dlcHandlers = [
  http.get("/api/v1/settings/10dlc-profile", () =>
    HttpResponse.json(MOCK_DLC_PROFILE),
  ),

  http.put(
    "/api/v1/settings/10dlc-profile",
    async ({ request }: { request: Request }) => {
      const body = (await request.json()) as typeof MOCK_DLC_PROFILE & {
        ein?: string;
      };
      return HttpResponse.json({
        ...MOCK_DLC_PROFILE,
        ...body,
        ein_masked: body.ein
          ? "**-***" + body.ein.slice(-4)
          : MOCK_DLC_PROFILE.ein_masked,
      });
    },
  ),
];
