/**
 * Billing Upgrade — Integration Tests (C-B12 Part B)
 *
 * Location: apps/web/src/__tests__/batch_c_b12/billing-upgrade.integration.test.tsx
 *
 * Platform: Web (Vitest + @testing-library/react + MSW)
 *
 * Tests:
 * 1. Charter member sees "Upgrade to Teams" button on billing page
 * 2. Non-Charter member does NOT see "Upgrade to Teams" button
 * 3. Clicking "Upgrade to Teams" opens the forfeiture modal
 * 4. Clicking "I understand — upgrade to Teams" fires POST /upgrade-from-charter
 * 5. After successful upgrade, modal closes + success notification dispatched
 * 6. Stale "Pro"/"Growth" tier picker is NOT present
 */

import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterEach,
  afterAll,
} from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import "@testing-library/jest-dom";

import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue, PilotRole } from "@pilot/ui/auth";
import { BillingSettingsPage } from "../../features/settings/components/BillingSettingsPage";
import { charterUpgradeHandlers } from "../../mocks/handlers/charterUpgradeHandlers";

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

// Mock notification queue — the provider does not render to DOM without the
// NotificationPortal, so we spy on addNotification instead.
const addNotificationSpy = vi.fn();
vi.mock("@pilot/ui/notification-banner", () => ({
  useNotificationQueue: () => ({
    addNotification: addNotificationSpy,
    notifications: [],
    dismissNotification: vi.fn(),
    dismissAll: vi.fn(),
  }),
  NotificationBanner: ({ notification }: { notification: { title: string } }) =>
    React.createElement("div", null, notification.title),
}));

// ── Fixtures ──────────────────────────────────────────────────────────────────

const CHARTER_SUBSCRIPTION = {
  current_tier: {
    tier_id: "tier-charter-001",
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
  stripe_customer_id: "cus_test_123",
  usage: {
    current_user_count: 2,
    current_sms_segments: 10,
  },
  tier_override: null,
  // PLP-FIX-5 (Issue 8): new payload sections
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

const TEAMS_SUBSCRIPTION = {
  current_tier: {
    tier_id: "tier-teams-001",
    tier_name: "teams",
    display_label: "Teams",
    monthly_price_cents: 17900,
    annual_price_cents: 178800,
    is_trial: false,
    trial_duration_days: null,
    schedule_lanes: 20,
    display_order: 3,
    is_active: true,
    free_period_days: null,
    requires_payment_method: true,
    signup_cap: null,
    price_locked: false,
  },
  trial_ends_at: null,
  stripe_customer_id: "cus_test_456",
  usage: {
    current_user_count: 5,
    current_sms_segments: 100,
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
    outbound_sms_segments: 500,
    schedule_lanes: 20,
    voice_ai_minutes: 300,
  },
};

// ── MSW ──────────────────────────────────────────────────────────────────────

const server = setupServer(
  http.get("/api/v1/tenants/:tenantId/subscription", () => {
    return HttpResponse.json(CHARTER_SUBSCRIPTION);
  }),
  ...charterUpgradeHandlers,
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => {
  server.resetHandlers();
  addNotificationSpy.mockClear();
});
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

function renderPage(role: PilotRole = "owner") {
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

// ── Integration Tests ─────────────────────────────────────────────────────────

describe("C-B12 — Billing Upgrade Integration", () => {
  it("1. Charter member sees 'Upgrade to Teams' button on billing page", async () => {
    renderPage("owner");
    await waitFor(() => {
      expect(screen.getByText("Charter")).toBeInTheDocument();
    });
    expect(
      screen.getByRole("button", { name: /Upgrade to Teams/i }),
    ).toBeInTheDocument();
  });

  it("2. Non-Charter member does NOT see 'Upgrade to Teams' button", async () => {
    server.use(
      http.get("/api/v1/tenants/:tenantId/subscription", () => {
        return HttpResponse.json(TEAMS_SUBSCRIPTION);
      }),
    );
    renderPage("owner");
    await waitFor(() => {
      expect(screen.getByText("Teams")).toBeInTheDocument();
    });
    expect(
      screen.queryByRole("button", { name: /Upgrade to Teams/i }),
    ).not.toBeInTheDocument();
  });

  it("3. clicking 'Upgrade to Teams' opens the forfeiture modal", async () => {
    renderPage("owner");
    await waitFor(() => {
      expect(screen.getByText("Charter")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: /Upgrade to Teams/i }));
    expect(screen.getByText(/lose your Charter rate/i)).toBeInTheDocument();
  });

  it("4. clicking 'I understand — upgrade to Teams' fires POST /upgrade-from-charter", async () => {
    const postSpy = vi.fn();
    server.use(
      http.post(
        "/api/v1/tenants/:tenantId/subscription/upgrade-from-charter",
        async ({ request }) => {
          const body = (await request.json()) as { billing_interval: string };
          postSpy(body.billing_interval);
          return HttpResponse.json({
            psp_subscription_id: "sub_test_mock",
            new_tier_name: "teams",
            billing_interval: body.billing_interval,
            charter_eligible_forfeited: true,
          });
        },
      ),
    );

    renderPage("owner");
    await waitFor(() => {
      expect(screen.getByText("Charter")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Upgrade to Teams/i }));
    fireEvent.click(screen.getByText("I understand — upgrade to Teams"));

    await waitFor(() => {
      expect(postSpy).toHaveBeenCalledWith("monthly");
    });
  });

  it("5. after successful upgrade, modal closes + success notification dispatched", async () => {
    renderPage("owner");
    await waitFor(() => {
      expect(screen.getByText("Charter")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Upgrade to Teams/i }));
    fireEvent.click(screen.getByText("I understand — upgrade to Teams"));

    // Success notification should be dispatched via addNotification
    await waitFor(() => {
      expect(addNotificationSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          severity: "success",
          title: expect.stringContaining("Teams plan"),
        }),
      );
    });

    // Modal should close (header text gone)
    await waitFor(() => {
      expect(
        screen.queryByText(/lose your Charter rate/i),
      ).not.toBeInTheDocument();
    });
  });

  it("6. stale 'Pro'/'Growth' tier picker is NOT present", async () => {
    renderPage("owner");
    await waitFor(() => {
      expect(screen.getByText("Charter")).toBeInTheDocument();
    });
    expect(screen.queryByText("Pro")).not.toBeInTheDocument();
    expect(screen.queryByText("Growth")).not.toBeInTheDocument();
    expect(screen.queryByText("Upgrade Your Plan")).not.toBeInTheDocument();
  });

  it("7. Charter member sees locked rate display", async () => {
    renderPage("owner");
    await waitFor(() => {
      expect(screen.getByText(/locked/i)).toBeInTheDocument();
    });
  });

  it("8. error state — no payment method shows error in modal", async () => {
    server.use(
      http.post(
        "/api/v1/tenants/:tenantId/subscription/upgrade-from-charter",
        () => {
          return HttpResponse.json(
            {
              type: "https://errors.pilotfortrades.com/no-payment-method",
              title: "No payment method on file.",
              status: 400,
              detail: "No payment method on file. Add a card before upgrading.",
            },
            { status: 400 },
          );
        },
      ),
    );

    renderPage("owner");
    await waitFor(() => {
      expect(screen.getByText("Charter")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Upgrade to Teams/i }));
    fireEvent.click(screen.getByText("I understand — upgrade to Teams"));

    await waitFor(() => {
      expect(
        screen.getByText(/No payment method on file/i),
      ).toBeInTheDocument();
    });

    // Modal stays open on error
    expect(screen.getByText(/lose your Charter rate/i)).toBeInTheDocument();
  });
});
