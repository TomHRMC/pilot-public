/**
 * SIGNUP-UI-FIX-2 Task 1 — Charter plan page blocker regression test
 *
 * Location: apps/web/src/__tests__/batch_signup_ui_fix_2/plan_page_charter_detection.test.tsx
 *
 * Verifies the Charter detection fix: when the tiers payload omits
 * `requires_payment_method` (the field is optional in SubscriptionTierAPI),
 * selecting the Charter tier must NOT render the "Loading payment form…"
 * placeholder and Continue must enable with the "Join Charter →" label.
 *
 * Root cause (2026-08-10): `selectedTier?.requires_payment_method === false`
 * evaluated to `false` when the field was `undefined`, stranding the user on
 * the paid path waiting for a clientSecret that never resolved. The fix
 * falls back to `tier_name === "charter"`.
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
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
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

const TENANT = "tenant-charter-detection-test-001";

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

// Charter tier WITHOUT requires_payment_method — simulates a payload
// where the optional field is absent (the root-cause scenario).
const CHARTER_TIER_NO_RPM = {
  tier_id: "tier-charter-no-rpm-001",
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
  // requires_payment_method intentionally OMITTED
  signup_cap: 12,
};

describe("SIGNUP-UI-FIX-2 Task 1 — Charter detection without requires_payment_method", () => {
  it("selecting Charter (no requires_payment_method) shows no payment placeholder and enables Continue with 'Join Charter →'", async () => {
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
        HttpResponse.json({ tiers: [CHARTER_TIER_NO_RPM] }),
      ),
    );

    renderPlanPage();

    // Wait for the CharterTierCard to render
    await waitFor(() => {
      expect(screen.getByTestId("charter-tier-card")).toBeInTheDocument();
    });

    // Select the Charter tier
    const selectButton = screen.getByTestId("charter-tier-select-button");
    fireEvent.click(selectButton);

    // The "Loading payment form…" placeholder must NOT appear
    expect(screen.queryByText(/Loading payment form/i)).not.toBeInTheDocument();

    // The inline Stripe form must NOT appear
    expect(screen.queryByTestId("inline-stripe-form")).not.toBeInTheDocument();

    // Continue button must be enabled (not disabled)
    const continueButton = screen.getByTestId("signup-plan-continue");
    expect(continueButton).not.toBeDisabled();

    // Button label must be "Join Charter →"
    expect(continueButton).toHaveTextContent("Join Charter →");
  });
});
