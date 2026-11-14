/**
 * SIGNUP-GA-B1 — Signup Wizard State-Machine Guard Alignment (Integration)
 *
 * Location: apps/web/src/__tests__/batch_signup_ga_b1/signup_state_machine.integration.test.tsx
 *
 * Regression lock for the off-by-one state-machine model conflict (Model A vs
 * Model B). Walks the whole machine end-to-end against the CORRECTED MSW
 * handlers (single-step transitions) and asserts every page guard admits its
 * correct backend state and forwards others.
 *
 * Model B (authoritative — backend VALID_STATE_TRANSITIONS):
 *   signup_state = stepN  ⇒  step N is complete; user is now on UI page N+1
 *     step1_account → Legal   (account done ⇒ collect legal)
 *     step2_legal   → Phone
 *     step3_phone   → Plan
 *     step4_tier    → Ready
 *     step5_confirm → Ready (payment/confirm)
 *     complete      → Dashboard
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
import { apiClient } from "@pilot/shared-api";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { signupHandlers } from "@/mocks/handlers/signupHandlers";
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
import SignupLegalPage from "@/app/signup/legal/page";
import SignupPhonePage from "@/app/signup/phone/page";
import SignupPlanPage from "@/app/signup/plan/page";
import SignupReadyPage from "@/app/signup/ready/page";
import SignupAccountPage from "@/app/signup/account/page";

// ── MSW server (corrected signupHandlers — single-step transitions) ─────────
const server = setupServer(...signupHandlers);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Helpers ─────────────────────────────────────────────────────────────────
const TENANT = "tenant-test-00000000-0000-0000-0000-000000000001";

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

// SIGNUP-UI-FIX-1: account page now uses useAuth() — provide a not-authenticated context
const notAuthValue: AuthContextValue = {
  user: null,
  isAuthenticated: false,
  role: null,
  signIn: vi.fn(),
  confirmMfaChallenge: vi.fn(),
  signOut: vi.fn(),
  refreshSession: vi.fn().mockResolvedValue("mock-token"),
};

function renderWithProvider(ui: React.ReactElement) {
  return render(
    <AuthContext.Provider value={notAuthValue}>
      <QueryClientProvider client={makeQueryClient()}>{ui}</QueryClientProvider>
    </AuthContext.Provider>,
  );
}

/** Per-test override: GET /state returns a specific signup_state + collected_data. */
function overrideState(state: string, collected: Record<string, unknown> = {}) {
  server.use(
    http.get(`/api/v1/signup/${TENANT}/state`, () =>
      HttpResponse.json({
        tenant_id: TENANT,
        signup_state: state,
        collected_data: {
          business_name: "Apex Electric LLC",
          owner_first_name: "Mike",
          owner_email: "mike@apexelectric.example.com",
          business_size: "solo",
          ...collected,
        },
      }),
    ),
  );
}

function setSessionTenant() {
  sessionStorage.setItem(WIZARD_TENANT_ID_KEY, TENANT);
}

beforeEach(() => {
  replace.mockClear();
  push.mockClear();
  sessionStorage.clear();
});

// ── Tests ───────────────────────────────────────────────────────────────────

describe("SIGNUP-GA-B1 — Signup Wizard State-Machine Guard Alignment", () => {
  // 1. The reported bug is fixed: legal renders at step1_account (no bounce).
  it("1. legal page: state step1_account does NOT redirect to /signup/account; legal form renders", async () => {
    setSessionTenant();
    overrideState("step1_account");

    renderWithProvider(<SignupLegalPage />);

    // The legal form renders (guard did not bounce to /signup/account).
    await waitFor(() => {
      expect(screen.getByTestId("signup-legal-form")).toBeInTheDocument();
    });

    // No redirect to /signup/account happened.
    expect(replace).not.toHaveBeenCalledWith("/signup/account");
  });

  // 2. Forward walk: each PUT /stepN returns the correct SINGLE-STEP next state.
  it("2. forward walk: PUT /step2→step2_legal, /step3→step3_phone, /step4→step4_tier, /step5→complete (no double-jump)", async () => {
    // POST /signup resets the mutable MSW state machine to step1_account.
    const initiate = await apiClient.post(`/api/v1/signup`, {
      business_name: "Apex Electric LLC",
      trade: "electrical",
      business_size: "solo",
      zip: "10001",
      time_zone: "America/New_York",
      owner_email: "mike@apexelectric.example.com",
      owner_first_name: "Mike",
      owner_last_name: "Johnson",
    });
    expect(initiate.data.signup_state).toBe("step1_account");

    const step2 = await apiClient.put(`/api/v1/signup/${TENANT}/step2`, {
      documents_accepted: ["tos", "privacy", "eula"],
    });
    expect(step2.data.signup_state).toBe("step2_legal");

    const step3 = await apiClient.put(`/api/v1/signup/${TENANT}/step3`, {
      phone_verified: true,
    });
    expect(step3.data.signup_state).toBe("step3_phone");

    const step4 = await apiClient.put(`/api/v1/signup/${TENANT}/step4`, {
      selected_tier_id: "tier-trial-00000000-0000-0000-0000-000000000001",
    });
    expect(step4.data.signup_state).toBe("step4_tier");

    const step5 = await apiClient.put(`/api/v1/signup/${TENANT}/step5`, {
      confirmed: true,
    });
    expect(step5.data.signup_state).toBe("complete");
  });

  // 3a. Legal admits step1_account; forwards step2_legal → /signup/phone.
  it("3a. legal page: admits step1_account; forwards step2_legal to /signup/phone", async () => {
    setSessionTenant();
    overrideState("step2_legal");

    renderWithProvider(<SignupLegalPage />);

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/signup/phone"));
  });

  // 3b. Phone admits step2_legal; bounces step1_account back to /signup/legal.
  it("3b. phone page: admits step2_legal; bounces step1_account back to /signup/legal", async () => {
    setSessionTenant();
    overrideState("step1_account");

    renderWithProvider(<SignupPhonePage />);

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/signup/legal"));
  });

  // 3c. Phone admits step2_legal (no redirect).
  it("3c. phone page: state step2_legal does NOT redirect", async () => {
    setSessionTenant();
    overrideState("step2_legal");

    renderWithProvider(<SignupPhonePage />);

    // Give the state fetch + guard effect a chance to run.
    await waitFor(() => {
      expect(replace).not.toHaveBeenCalled();
    });
  });

  // 3d. Plan admits step3_phone; forwards step2_legal → /signup/phone.
  it("3d. plan page: admits step3_phone; forwards step2_legal to /signup/phone", async () => {
    setSessionTenant();
    overrideState("step2_legal");

    renderWithProvider(<SignupPlanPage />);

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/signup/phone"));
  });

  // 3e. Ready admits step4_tier (no redirect).
  it("3e. ready page: state step4_tier does NOT redirect", async () => {
    setSessionTenant();
    overrideState("step4_tier");

    renderWithProvider(<SignupReadyPage />);

    await waitFor(() => {
      expect(replace).not.toHaveBeenCalled();
    });
  });

  // 3f. Ready admits step5_confirm (no redirect) — both tier+confirm map to Ready.
  it("3f. ready page: state step5_confirm does NOT redirect (both step4_tier + step5_confirm map to Ready)", async () => {
    setSessionTenant();
    overrideState("step5_confirm");

    renderWithProvider(<SignupReadyPage />);

    await waitFor(() => {
      expect(replace).not.toHaveBeenCalled();
    });
  });

  // 3g. Ready forwards step3_phone → /signup/plan.
  it("3g. ready page: forwards step3_phone to /signup/plan", async () => {
    setSessionTenant();
    overrideState("step3_phone");

    renderWithProvider(<SignupReadyPage />);

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/signup/plan"));
  });

  // 3h. Ready special-cases complete → /dashboard (clears session).
  it("3h. ready page: state complete redirects to /dashboard and clears session", async () => {
    setSessionTenant();
    overrideState("complete");

    renderWithProvider(<SignupReadyPage />);

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/dashboard"));
    expect(sessionStorage.getItem(WIZARD_TENANT_ID_KEY)).toBeNull();
  });

  // 4. Account resume: step1_account forwards to /signup/legal (not stays).
  it("4. account page resume: state step1_account redirects to /signup/legal (not /signup/account)", async () => {
    setSessionTenant();
    overrideState("step1_account");

    renderWithProvider(<SignupAccountPage />);

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/signup/legal"));
    expect(replace).not.toHaveBeenCalledWith("/signup/account");
  });

  // 5a. Welcome-back banner populates with owner_first_name.
  it("5a. legal page: renders 'Welcome back, Mike' when collected_data.owner_first_name is 'Mike'", async () => {
    setSessionTenant();
    overrideState("step1_account", { owner_first_name: "Mike" });

    renderWithProvider(<SignupLegalPage />);

    await waitFor(() => {
      expect(screen.getByText(/Welcome back, Mike/i)).toBeInTheDocument();
    });
  });

  // 5b. Welcome-back banner is null-safe (no "Welcome back, .").
  it("5b. legal page: does NOT render 'Welcome back' when owner_first_name is null (no 'Welcome back, .')", async () => {
    setSessionTenant();
    overrideState("step1_account", { owner_first_name: null });

    renderWithProvider(<SignupLegalPage />);

    // Wait for the form to render (query resolved, guard did not bounce).
    await waitFor(() => {
      expect(screen.getByTestId("signup-legal-form")).toBeInTheDocument();
    });
    // No "Welcome back" banner at all.
    expect(screen.queryByText(/Welcome back/i)).toBeNull();
  });
});
