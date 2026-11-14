/**
 * C-B5 Plan page — Charter tier renders CharterTierCard integration test
 *
 * Location: apps/web/src/__tests__/batch_c_b5/plan_page_charter.integration.test.tsx
 *
 * Verifies:
 *  - Charter tier renders CharterTierCard instead of TierPickerCard
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
import type { AuthContextValue } from "@pilot/ui/auth";
import { WIZARD_TENANT_ID_KEY } from "@/features/signup/types";

const { replace, push } = vi.hoisted(() => ({
  replace: vi.fn(),
  push: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace, back: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

import SignupPlanPage from "@/app/signup/plan/page";

const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => {
  server.resetHandlers();
  replace.mockReset();
  push.mockReset();
  sessionStorage.clear();
});
afterAll(() => server.close());

const TENANT = "tenant-cb5-plan-test-001";

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

const notAuthValue: AuthContextValue = {
  user: null,
  isAuthenticated: false,
  role: null,
  signIn: vi.fn(),
  confirmMfaChallenge: vi.fn(),
  signOut: vi.fn(),
  refreshSession: vi.fn().mockResolvedValue("mock-token"),
};

function renderPlanPage() {
  return render(
    <AuthContext.Provider value={notAuthValue}>
      <QueryClientProvider client={makeQueryClient()}>
        <SignupPlanPage />
      </QueryClientProvider>
    </AuthContext.Provider>,
  );
}

const CHARTER_ONLY_TIERS = {
  tiers: [
    {
      tier_id: "tier-charter-001",
      tier_name: "charter",
      display_label: "Charter",
      monthly_price_cents: 4900,
      is_trial: false,
      trial_duration_days: null,
      max_users: 12,
      max_sms_segments_per_month: 2000,
      display_order: 0,
      is_active: true,
      free_period_days: 90,
      requires_payment_method: false,
      signup_cap: 12,
    },
  ],
};

describe("C-B5 — Plan page Charter tier", () => {
  it("Charter tier renders CharterTierCard instead of TierPickerCard", async () => {
    sessionStorage.setItem(WIZARD_TENANT_ID_KEY, TENANT);

    server.use(
      http.get(`/api/v1/signup/${TENANT}/state`, () =>
        HttpResponse.json({
          tenant_id: TENANT,
          signup_state: "step3_phone",
          collected_data: { business_size: "solo" },
        }),
      ),
      http.get("/api/v1/subscription-tiers", () =>
        HttpResponse.json(CHARTER_ONLY_TIERS),
      ),
    );

    renderPlanPage();

    // Wait for the CharterTierCard to render
    await waitFor(() => {
      expect(screen.getByTestId("charter-tier-card")).toBeInTheDocument();
    });

    // The free-period callout should be visible
    expect(screen.getByTestId("charter-free-period-callout")).toHaveTextContent(
      "Free for 90 days. No card needed.",
    );
  });
});
