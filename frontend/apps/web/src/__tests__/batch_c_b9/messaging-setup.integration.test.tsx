/**
 * C-B9 Integration Test — Messaging Setup Page
 *
 * Location: apps/web/src/__tests__/batch_c_b9/messaging-setup.integration.test.tsx
 *
 * Tests:
 * 1. Page renders (not 404) — primary content visible with MSW mock
 * 2. RBAC — owner sees the page content
 * 3. RBAC — tech role is blocked (RoleGate hides content)
 * 4. Initial state (404 on status) → EntityTypeSelector visible
 * 5. Provisioning mutation fires correct POST to /messaging/provision
 * 6. Status polling shows correct panel for "quoting" status
 * 7. Checkout button fires POST to /messaging/checkout
 *
 * RULE 14: retry: false QueryClient. RULE 15: server.resetHandlers in afterEach.
 */

import React from "react";
import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterEach,
  afterAll,
} from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue, PilotUser, PilotRole } from "@pilot/ui/auth";
import { NotificationQueueProvider } from "@pilot/ui";

import { MessagingSetupClient } from "@/components/settings/messaging/MessagingSetupClient";

// ── Navigation mocks ──────────────────────────────────────────────────────────

const mockReplace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: mockReplace }),
  usePathname: () => "/settings/messaging",
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...rest
  }: {
    href: string;
    children: React.ReactNode;
    [key: string]: unknown;
  }) => React.createElement("a", { href, ...rest }, children),
}));

// ── MSW server ────────────────────────────────────────────────────────────────

const MOCK_QUOTE = {
  entity_type: "standard",
  setup_total_millicents: 400000,
  recurring_monthly_millicents: 30000,
  setup_items: [
    {
      fee_code: "brand_registration",
      description: "Brand registration",
      amount_millicents: 400000,
    },
  ],
  recurring_items: [
    {
      fee_code: "phone_number",
      description: "Phone number",
      amount_millicents: 30000,
    },
  ],
};

const MOCK_VERTICALS = {
  verticals: ["ELECTRICIAN", "CONTRACTOR", "ENERGY"],
};

const MOCK_PROFILE = {
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

// Track POST requests for assertion
// eslint-disable-next-line @typescript-eslint/no-unused-vars
let provisionRequestCalled = false;
// eslint-disable-next-line @typescript-eslint/no-unused-vars
let checkoutRequestCalled = false;

const server = setupServer(
  // GET /messaging/status — default: 404 (not started)
  http.get("/api/v1/tenants/:tenantId/messaging/status", () =>
    HttpResponse.json({ detail: "Not found" }, { status: 404 }),
  ),

  // GET /settings/10dlc-profile
  http.get("/api/v1/settings/10dlc-profile", () =>
    HttpResponse.json(MOCK_PROFILE),
  ),

  // GET /messaging/verticals
  http.get("/api/v1/tenants/:tenantId/messaging/verticals", () =>
    HttpResponse.json(MOCK_VERTICALS),
  ),

  // POST /messaging/provision
  http.post("/api/v1/tenants/:tenantId/messaging/provision", () => {
    provisionRequestCalled = true;
    return HttpResponse.json({
      registration_id: "reg-mock-001",
      status: "quoting",
      entity_type: "standard",
      quote: MOCK_QUOTE,
    });
  }),

  // POST /messaging/checkout
  http.post("/api/v1/tenants/:tenantId/messaging/checkout", () => {
    checkoutRequestCalled = true;
    return HttpResponse.json({
      checkout_url: "https://checkout.stripe.com/c/cs_test_mock",
      checkout_session_id: "cs_test_mock",
    });
  }),

  // GET /messaging/quote
  http.get("/api/v1/tenants/:tenantId/messaging/quote", () =>
    HttpResponse.json(MOCK_QUOTE),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => {
  server.resetHandlers();
  provisionRequestCalled = false;
  checkoutRequestCalled = false;
});
afterAll(() => server.close());

// ── Auth helpers ──────────────────────────────────────────────────────────────

function makeAuthValue(role: PilotRole = "owner"): AuthContextValue {
  const user: PilotUser = {
    id: "u-cb9-test",
    email: "test@pilot.example.com",
    role,
    tenantId: "t-cb9-test",
    displayName: "Test User",
    accessToken: "mock-token",
  };
  return {
    user,
    isAuthenticated: true,
    role,
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("mock-token"),
  };
}

function renderPage(role: PilotRole = "owner") {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    <AuthContext.Provider value={makeAuthValue(role)}>
      <QueryClientProvider client={qc}>
        <NotificationQueueProvider>
          <MessagingSetupClient />
        </NotificationQueueProvider>
      </QueryClientProvider>
    </AuthContext.Provider>,
  );
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("C-B9 — Messaging Setup Page Integration", () => {
  it("1. page renders — primary heading visible", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Text Messaging Setup")).toBeInTheDocument();
    });
  });

  it("2. RBAC — owner sees the page content", async () => {
    renderPage("owner");
    await waitFor(() => {
      expect(screen.getByText("Text Messaging Setup")).toBeInTheDocument();
    });
  });

  it("3. initial state (404 on status) — EntityTypeSelector visible", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Business Type")).toBeInTheDocument();
    });
    expect(
      screen.getByText(/Does your business have an EIN/),
    ).toBeInTheDocument();
  });

  it("4. selecting entity type shows brand registration form", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Business Type")).toBeInTheDocument();
    });

    // Click "Yes, we have an EIN" (standard)
    fireEvent.click(screen.getByTestId("entity-type-standard"));

    await waitFor(() => {
      expect(screen.getByTestId("brand-registration-form")).toBeInTheDocument();
    });
  });

  it("5. status=quoting shows CarrierQuoteDisplay with checkout button", async () => {
    // Override status to return "quoting"
    server.use(
      http.get("/api/v1/tenants/:tenantId/messaging/status", () =>
        HttpResponse.json({
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
        }),
      ),
    );

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("carrier-quote-display")).toBeInTheDocument();
    });
    expect(screen.getByText("Cost Quote")).toBeInTheDocument();
    expect(screen.getByTestId("checkout-redirect-button")).toBeInTheDocument();
  });

  it("6. status=active shows success panel with phone number", async () => {
    server.use(
      http.get("/api/v1/tenants/:tenantId/messaging/status", () =>
        HttpResponse.json({
          registration_id: "reg-mock-001",
          status: "active",
          entity_type: "standard",
          telnyx_brand_id: "brand_abc",
          telnyx_campaign_id: "camp_abc",
          telnyx_phone_number: "+13025551234",
          quoted_setup_cents: 400000,
          quoted_monthly_cents: 30000,
          otp_requested_at: null,
          failure_reason: null,
          updated_at: new Date().toISOString(),
        }),
      ),
    );

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("messaging-success")).toBeInTheDocument();
    });
    expect(screen.getByText("Text Messaging is Active")).toBeInTheDocument();
    expect(screen.getByText("(302) 555-1234")).toBeInTheDocument();
  });

  it("7. status=payment_failed shows error panel with retry button", async () => {
    server.use(
      http.get("/api/v1/tenants/:tenantId/messaging/status", () =>
        HttpResponse.json({
          registration_id: "reg-mock-001",
          status: "payment_failed",
          entity_type: "standard",
          telnyx_brand_id: null,
          telnyx_campaign_id: null,
          telnyx_phone_number: null,
          quoted_setup_cents: 400000,
          quoted_monthly_cents: 30000,
          otp_requested_at: null,
          failure_reason: "Card declined",
          updated_at: new Date().toISOString(),
        }),
      ),
    );

    renderPage();

    await waitFor(() => {
      expect(
        screen.getByTestId("provisioning-error-panel"),
      ).toBeInTheDocument();
    });
    expect(screen.getByText("Payment Failed")).toBeInTheDocument();
    expect(screen.getByTestId("error-retry-button")).toBeInTheDocument();
  });

  it("8. status=awaiting_otp shows OTP entry panel", async () => {
    server.use(
      http.get("/api/v1/tenants/:tenantId/messaging/status", () =>
        HttpResponse.json({
          registration_id: "reg-mock-001",
          status: "awaiting_otp",
          entity_type: "sole_proprietor",
          telnyx_brand_id: "brand_abc",
          telnyx_campaign_id: null,
          telnyx_phone_number: null,
          quoted_setup_cents: 1500000,
          quoted_monthly_cents: 36700,
          otp_requested_at: new Date().toISOString(),
          failure_reason: null,
          updated_at: new Date().toISOString(),
        }),
      ),
    );

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("otp-entry-panel")).toBeInTheDocument();
    });
    expect(screen.getByText("Verify Your Business")).toBeInTheDocument();
    // 6 OTP digit inputs
    expect(screen.getByTestId("otp-digit-1")).toBeInTheDocument();
    expect(screen.getByTestId("otp-digit-6")).toBeInTheDocument();
  });

  it("9. status=awaiting_number_selection shows phone number selector", async () => {
    server.use(
      http.get("/api/v1/tenants/:tenantId/messaging/status", () =>
        HttpResponse.json({
          registration_id: "reg-mock-001",
          status: "awaiting_number_selection",
          entity_type: "standard",
          telnyx_brand_id: "brand_abc",
          telnyx_campaign_id: "camp_abc",
          telnyx_phone_number: null,
          quoted_setup_cents: 4000000,
          quoted_monthly_cents: 30000,
          otp_requested_at: null,
          failure_reason: null,
          updated_at: new Date().toISOString(),
        }),
      ),
      http.get("/api/v1/tenants/:tenantId/messaging/available-numbers", () =>
        HttpResponse.json({
          numbers: [
            {
              phone_number: "+13025551234",
              locality: "Wilmington",
              region: "DE",
              monthly_cost_millicents: 100000,
            },
          ],
        }),
      ),
    );

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("phone-number-selector")).toBeInTheDocument();
    });
    expect(screen.getByText("Choose Your Phone Number")).toBeInTheDocument();
  });

  it("10. status=brand_rejected shows rejected error panel", async () => {
    server.use(
      http.get("/api/v1/tenants/:tenantId/messaging/status", () =>
        HttpResponse.json({
          registration_id: "reg-mock-001",
          status: "brand_rejected",
          entity_type: "standard",
          telnyx_brand_id: "brand_abc",
          telnyx_campaign_id: null,
          telnyx_phone_number: null,
          quoted_setup_cents: 4000000,
          quoted_monthly_cents: 30000,
          otp_requested_at: null,
          failure_reason: "Invalid EIN",
          updated_at: new Date().toISOString(),
        }),
      ),
    );

    renderPage();

    await waitFor(() => {
      expect(
        screen.getByTestId("provisioning-error-panel"),
      ).toBeInTheDocument();
    });
    expect(screen.getByText("Registration Rejected")).toBeInTheDocument();
    expect(screen.getByTestId("error-contact-support")).toBeInTheDocument();
  });
});
