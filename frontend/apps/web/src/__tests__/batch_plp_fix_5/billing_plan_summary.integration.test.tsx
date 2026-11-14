/**
 * PLP-FIX-5 Part B — Billing Settings Plan-Summary Integration
 *
 * Location: apps/web/src/__tests__/batch_plp_fix_5/billing_plan_summary.integration.test.tsx
 *
 * Tests:
 * 1. Status badge renders the fixture's status label ("Active")
 * 2. Monthly price line renders "$59/mo"
 * 3. Annual price line renders "$588/yr ($49/mo)"
 * 4. Date line renders "Renews …" when renews_at is set
 * 5. Breadcrumb renders with Settings link
 * 6. SMS usage bar receives the real max; members row has no bar
 * 7. Charter fixture: "Free period ends …" + locked rate
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
import { render, screen, waitFor } from "@testing-library/react";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue, PilotRole } from "@pilot/ui/auth";
import { BillingSettingsPage } from "../../features/settings/components/BillingSettingsPage";

// ── Mocks ────────────────────────────────────────────────────────────────────

vi.mock("next/navigation", () => ({
  usePathname: () => "/settings/billing",
  useSearchParams: () => new URLSearchParams(""),
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
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

// Mock notification queue
vi.mock("@pilot/ui/notification-banner", () => ({
  useNotificationQueue: () => ({
    addNotification: vi.fn(),
    notifications: [],
    dismissNotification: vi.fn(),
    dismissAll: vi.fn(),
  }),
  NotificationBanner: () => null,
  NotificationQueueProvider: ({ children }: { children: React.ReactNode }) =>
    React.createElement(React.Fragment, null, children),
}));

// ── Fixtures ──────────────────────────────────────────────────────────────────

const ACTIVE_MONTHLY_SUBSCRIPTION = {
  current_tier: {
    tier_id: "tier-starter",
    tier_name: "starter",
    display_label: "Starter",
    monthly_price_cents: 5900,
    annual_price_cents: 58800,
    is_trial: false,
    trial_duration_days: null,
    schedule_lanes: 5,
    display_order: 10,
    is_active: true,
    free_period_days: null,
    requires_payment_method: true,
    signup_cap: null,
    price_locked: false,
  },
  trial_ends_at: null,
  stripe_customer_id: "cus_test_001",
  usage: {
    current_user_count: 3,
    current_sms_segments: 42,
  },
  tier_override: null,
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

const ANNUAL_SUBSCRIPTION = {
  ...ACTIVE_MONTHLY_SUBSCRIPTION,
  plan_summary: {
    ...ACTIVE_MONTHLY_SUBSCRIPTION.plan_summary,
    billing_interval: "annual",
  },
};

const CHARTER_SUBSCRIPTION = {
  current_tier: {
    tier_id: "tier-charter",
    tier_name: "charter",
    display_label: "Charter",
    monthly_price_cents: 4900,
    annual_price_cents: 0,
    is_trial: false,
    trial_duration_days: null,
    schedule_lanes: 5,
    display_order: 1,
    is_active: true,
    free_period_days: 90,
    requires_payment_method: false,
    signup_cap: 12,
    price_locked: true,
  },
  trial_ends_at: null,
  stripe_customer_id: "cus_charter",
  usage: {
    current_user_count: 2,
    current_sms_segments: 10,
  },
  tier_override: null,
  plan_summary: {
    status_code: "active",
    status_name: "Active",
    is_billing_active: true,
    billing_interval: "monthly",
    renews_at: null,
    free_period_ends_at: new Date(
      Date.now() + 60 * 24 * 60 * 60 * 1000,
    ).toISOString(),
  },
  charter_eligible: true,
  limits: {
    outbound_sms_segments: 100,
    schedule_lanes: 5,
    voice_ai_minutes: 90,
  },
};

// ── MSW ──────────────────────────────────────────────────────────────────────

const server = setupServer(
  http.get("/api/v1/tenants/:tenantId/subscription", () =>
    HttpResponse.json(ACTIVE_MONTHLY_SUBSCRIPTION),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Helpers ──────────────────────────────────────────────────────────────────

function makeAuthValue(role: PilotRole = "owner"): AuthContextValue {
  return {
    user: {
      id: "u1",
      email: "test@example.com",
      role,
      tenantId: "t1",
      displayName: "Test User",
      accessToken: "tok",
    },
    isAuthenticated: true,
    role,
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("tok"),
  };
}

function renderPage(
  role: PilotRole = "owner",
  subscription: Record<string, unknown> = ACTIVE_MONTHLY_SUBSCRIPTION,
) {
  server.use(
    http.get("/api/v1/tenants/:tenantId/subscription", () =>
      HttpResponse.json(subscription),
    ),
  );
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    React.createElement(
      AuthContext.Provider,
      { value: makeAuthValue(role) },
      React.createElement(
        QueryClientProvider,
        { client: queryClient },
        React.createElement(BillingSettingsPage),
      ),
    ),
  );
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("PLP-FIX-5 — Billing Plan-Summary", () => {
  it("1. status badge renders the fixture's 'Active' label", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Starter")).toBeInTheDocument();
    });
    expect(screen.getByTestId("plan-status-badge")).toHaveTextContent("Active");
  });

  it("2. monthly price line renders '$59/mo'", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Starter")).toBeInTheDocument();
    });
    expect(screen.getByText("$59/mo")).toBeInTheDocument();
  });

  it("3. annual price line renders '$588/yr ($49/mo)'", async () => {
    renderPage("owner", ANNUAL_SUBSCRIPTION);
    await waitFor(() => {
      expect(screen.getByText("Starter")).toBeInTheDocument();
    });
    expect(screen.getByText("$588/yr ($49/mo)")).toBeInTheDocument();
  });

  it("4. date line renders 'Renews …' when renews_at is set", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Starter")).toBeInTheDocument();
    });
    expect(screen.getByText(/^Renews /)).toBeInTheDocument();
  });

  it("5. breadcrumb renders with Settings link", async () => {
    renderPage();
    const settingsLink = await screen.findByRole("link", { name: "Settings" });
    expect(settingsLink).toBeInTheDocument();
    expect(settingsLink.getAttribute("href")).toBe("/settings");
  });

  it("6. SMS usage bar shows real max; members row shows count only (no bar)", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Starter")).toBeInTheDocument();
    });
    // SMS segments: current / max
    expect(screen.getByText(/42 \/ 100/)).toBeInTheDocument();
    // Team members: count only, no "/ max" suffix
    expect(screen.getByText(/3$/)).toBeInTheDocument();
  });

  it("7. Charter fixture: 'Free period ends …' + locked rate", async () => {
    renderPage("owner", CHARTER_SUBSCRIPTION);
    await waitFor(() => {
      expect(screen.getByText("Charter")).toBeInTheDocument();
    });
    expect(screen.getByText(/locked/i)).toBeInTheDocument();
    expect(screen.getByText(/^Free period ends /)).toBeInTheDocument();
  });
});
