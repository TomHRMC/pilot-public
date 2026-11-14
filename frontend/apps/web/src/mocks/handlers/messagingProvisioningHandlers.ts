/**
 * Messaging Provisioning MSW handlers — C-B9
 *
 * Location: apps/web/src/mocks/handlers/messagingProvisioningHandlers.ts
 *
 * Handlers for the 8 messaging provisioning endpoints + the C-B8 quote endpoint.
 * All endpoints are tenant-scoped under /api/v1/tenants/:tenantId/messaging/.
 *
 * RULE 13: registered in the barrel index.ts.
 */

import { http, HttpResponse } from "msw";

// ── Mock data ─────────────────────────────────────────────────────────────────

const MOCK_QUOTE = {
  entity_type: "standard",
  setup_total_millicents: 400000, // $4.00
  recurring_monthly_millicents: 30000, // $0.30
  setup_items: [
    {
      fee_code: "brand_registration",
      description: "Brand registration",
      amount_millicents: 400000, // $4.00
    },
    {
      fee_code: "campaign_registration",
      description: "Campaign registration",
      amount_millicents: 0,
    },
    {
      fee_code: "phone_number_assignment",
      description: "Phone number assignment",
      amount_millicents: 0,
    },
  ],
  recurring_items: [
    {
      fee_code: "phone_number",
      description: "Phone number",
      amount_millicents: 30000, // $0.30
    },
    {
      fee_code: "campaign_maintenance",
      description: "Campaign maintenance",
      amount_millicents: 0,
    },
  ],
};

const MOCK_VERTICALS = {
  verticals: [
    "ENERGY",
    "TECHNOLOGY",
    "FINANCE",
    "HEALTHCARE",
    "RETAIL",
    "CONSTRUCTION",
    "ELECTRICIAN",
    "CONTRACTOR",
    "REAL_ESTATE",
    "EDUCATION",
  ],
};

const MOCK_AVAILABLE_NUMBERS = {
  numbers: [
    {
      phone_number: "+13025551234",
      locality: "Wilmington",
      region: "DE",
      monthly_cost_millicents: 100000, // $1.00
    },
    {
      phone_number: "+13025555678",
      locality: "Dover",
      region: "DE",
      monthly_cost_millicents: 100000,
    },
    {
      phone_number: "+13025559012",
      locality: "Newark",
      region: "DE",
      monthly_cost_millicents: 100000,
    },
  ],
};

// Mutable state for the mock — simulates the provisioning lifecycle
let mockStatus: {
  registration_id: string;
  status: string;
  entity_type: string;
  telnyx_brand_id: string | null;
  telnyx_campaign_id: string | null;
  telnyx_phone_number: string | null;
  quoted_setup_cents: number | null;
  quoted_monthly_cents: number | null;
  otp_requested_at: string | null;
  failure_reason: string | null;
  updated_at: string | null;
} | null = null;

export const messagingProvisioningHandlers = [
  // POST /messaging/provision
  http.post("/api/v1/tenants/:tenantId/messaging/provision", async () => {
    mockStatus = {
      registration_id: "reg-mock-001",
      status: "quoting",
      entity_type: "standard",
      telnyx_brand_id: null,
      telnyx_campaign_id: null,
      telnyx_phone_number: null,
      quoted_setup_cents: 400000,
      quoted_monthly_cents: 30000,
      otp_requested_at: null,
      failure_reason: null,
      updated_at: new Date().toISOString(),
    };
    return HttpResponse.json({
      registration_id: mockStatus.registration_id,
      status: mockStatus.status,
      entity_type: mockStatus.entity_type,
      quote: MOCK_QUOTE,
    });
  }),

  // POST /messaging/checkout
  http.post("/api/v1/tenants/:tenantId/messaging/checkout", () => {
    if (mockStatus) {
      mockStatus.status = "awaiting_payment";
    }
    return HttpResponse.json({
      checkout_url: "https://checkout.stripe.com/c/cs_test_mock",
      checkout_session_id: "cs_test_mock",
    });
  }),

  // POST /messaging/otp
  http.post("/api/v1/tenants/:tenantId/messaging/otp", async () => {
    if (mockStatus) {
      mockStatus.status = "brand_verified";
    }
    return HttpResponse.json({ status: "brand_verified" });
  }),

  // GET /messaging/status
  http.get("/api/v1/tenants/:tenantId/messaging/status", () => {
    if (!mockStatus) {
      return HttpResponse.json(
        { detail: "No registration found" },
        { status: 404 },
      );
    }
    return HttpResponse.json(mockStatus);
  }),

  // POST /messaging/retry
  http.post("/api/v1/tenants/:tenantId/messaging/retry", () => {
    if (mockStatus) {
      mockStatus.status = "quoting";
    }
    return HttpResponse.json({
      status: "quoting",
      quote: MOCK_QUOTE,
    });
  }),

  // GET /messaging/verticals
  http.get("/api/v1/tenants/:tenantId/messaging/verticals", () =>
    HttpResponse.json(MOCK_VERTICALS),
  ),

  // GET /messaging/available-numbers
  http.get("/api/v1/tenants/:tenantId/messaging/available-numbers", () =>
    HttpResponse.json(MOCK_AVAILABLE_NUMBERS),
  ),

  // POST /messaging/assign-number
  http.post(
    "/api/v1/tenants/:tenantId/messaging/assign-number",
    async ({ request }: { request: Request }) => {
      const body = (await request.json()) as { phone_number: string };
      if (mockStatus) {
        mockStatus.status = "active";
        mockStatus.telnyx_phone_number = body.phone_number;
      }
      return HttpResponse.json({
        status: "active",
        telnyx_phone_number: body.phone_number,
      });
    },
  ),

  // GET /messaging/quote (C-B8, reused)
  http.get("/api/v1/tenants/:tenantId/messaging/quote", () =>
    HttpResponse.json(MOCK_QUOTE),
  ),
];

/** Reset mock state — used in test beforeEach */
export function resetMessagingMockState() {
  mockStatus = null;
}
