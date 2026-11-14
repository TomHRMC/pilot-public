/**
 * Plan page mode-aware subtitle integration test — SIGNUP-UI-FIX-1
 *
 * Location: apps/web/src/__tests__/batch_signup_ui_fix_1/plan_page_subtitle.integration.test.tsx
 *
 * Verifies the /signup/plan subtitle is mode-aware:
 *  - Charter mode (no trial tier) → "Join the Charter program..."
 *  - General Release mode (trial tier exists) → "Start with a 14-day free trial..."
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
  beforeEach,
} from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { WIZARD_TENANT_ID_KEY } from "@/features/signup/types";

// ── Hoisted navigation mock ─────────────────────────────────────────────────
const { replace, push } = vi.hoisted(() => ({
  replace: vi.fn(),
  push: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace, back: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

// Pages imported AFTER vi.mock so the mock applies.
import SignupPlanPage from "@/app/signup/plan/page";

// ── MSW server ──────────────────────────────────────────────────────────────
const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => {
  server.resetHandlers();
  replace.mockReset();
  push.mockReset();
});
afterAll(() => server.close());

// ── Helpers ─────────────────────────────────────────────────────────────────
const TENANT = "tenant-plan-subtitle-test-001";

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

// SIGNUP-UI-FIX-1: plan page now uses useAuth() — provide a not-authenticated context
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

// Tier fixtures
const CHARTER_ONLY_TIERS = {
  tiers: [
    {
      tier_id: "tier-charter-001",
      tier_name: "charter",
      display_label: "Charter",
      monthly_price_cents: 0,
      is_trial: false,
      trial_duration_days: null,
      max_users: 5,
      max_sms_segments_per_month: 100,
      display_order: 0,
      is_active: true,
    },
  ],
};

const TRIAL_TIERS = {
  tiers: [
    {
      tier_id: "tier-trial-001",
      tier_name: "trial",
      display_label: "Free Trial",
      monthly_price_cents: 0,
      is_trial: true,
      trial_duration_days: 14,
      max_users: 1,
      max_sms_segments_per_month: 50,
      display_order: 0,
      is_active: true,
    },
    {
      tier_id: "tier-starter-001",
      tier_name: "starter",
      display_label: "Starter",
      monthly_price_cents: 9900,
      is_trial: false,
      trial_duration_days: null,
      max_users: 5,
      max_sms_segments_per_month: 500,
      display_order: 1,
      is_active: true,
    },
  ],
};

// ── Tests ───────────────────────────────────────────────────────────────────

describe("SignupPlanPage mode-aware subtitle — SIGNUP-UI-FIX-1", () => {
  beforeEach(() => {
    sessionStorage.clear();
    sessionStorage.setItem(WIZARD_TENANT_ID_KEY, TENANT);
  });

  it("shows Charter text when no trial tier exists (Charter mode)", async () => {
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

    await waitFor(() => {
      expect(screen.getByText(/Join the Charter program/i)).toBeInTheDocument();
    });
  });

  it("shows trial text when a trial tier exists (General Release mode)", async () => {
    server.use(
      http.get(`/api/v1/signup/${TENANT}/state`, () =>
        HttpResponse.json({
          tenant_id: TENANT,
          signup_state: "step3_phone",
          collected_data: { business_size: "solo" },
        }),
      ),
      http.get("/api/v1/subscription-tiers", () =>
        HttpResponse.json(TRIAL_TIERS),
      ),
    );

    renderPlanPage();

    await waitFor(() => {
      expect(
        screen.getByText(/Start with a 14-day free trial/i),
      ).toBeInTheDocument();
    });
  });
});
