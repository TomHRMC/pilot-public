/**
 * SignupCompletionGuard integration tests — SIGNUP-UI-FIX-1
 *
 * Location: apps/web/src/__tests__/batch_signup_ui_fix_1/signup_completion_guard.integration.test.tsx
 *
 * Integration-level tests using the real signupHandlers MSW fixtures.
 * Verifies the guard redirects partially-onboarded users and lets
 * fully-onboarded users through.
 */

import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterEach,
  afterAll,
} from "vitest";
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { SignupCompletionGuard } from "@/components/SignupCompletionGuard";

// ── Hoisted navigation mock ─────────────────────────────────────────────────
const { replace } = vi.hoisted(() => ({ replace: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn(), back: vi.fn() }),
}));

// ── MSW server ──────────────────────────────────────────────────────────────
const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => {
  server.resetHandlers();
  replace.mockReset();
});
afterAll(() => server.close());

// ── Helpers ─────────────────────────────────────────────────────────────────
const TENANT_ID = "tenant-integration-test-001";

function makeAuthValue(): AuthContextValue {
  return {
    user: {
      id: "u1",
      email: "test@example.com",
      role: "owner",
      tenantId: TENANT_ID,
      displayName: "Test",
      accessToken: "tok",
    },
    isAuthenticated: true,
    role: "owner",
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn().mockResolvedValue(undefined),
    refreshSession: vi.fn().mockResolvedValue("tok"),
  };
}

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

function renderGuardWithContent() {
  return render(
    <QueryClientProvider client={makeQueryClient()}>
      <AuthContext.Provider value={makeAuthValue()}>
        <SignupCompletionGuard>
          <div data-testid="dashboard-content" role="main">
            Dashboard
          </div>
        </SignupCompletionGuard>
      </AuthContext.Provider>
    </QueryClientProvider>,
  );
}

// ── Tests ───────────────────────────────────────────────────────────────────

describe("SignupCompletionGuard integration — SIGNUP-UI-FIX-1", () => {
  it("authenticated user with signup_state 'step3_phone' is redirected to /signup/plan", async () => {
    server.use(
      http.get(`/api/v1/signup/${TENANT_ID}/state`, () =>
        HttpResponse.json({
          tenant_id: TENANT_ID,
          signup_state: "step3_phone",
          collected_data: {},
        }),
      ),
    );

    renderGuardWithContent();

    await waitFor(() => {
      expect(replace).toHaveBeenCalledWith("/signup/plan");
    });
  });

  it("authenticated user with signup_state 'complete' sees dashboard content (no redirect)", async () => {
    server.use(
      http.get(`/api/v1/signup/${TENANT_ID}/state`, () =>
        HttpResponse.json({
          tenant_id: TENANT_ID,
          signup_state: "complete",
          collected_data: {},
        }),
      ),
    );

    renderGuardWithContent();

    await waitFor(() => {
      expect(screen.getByTestId("dashboard-content")).toBeInTheDocument();
    });
    expect(replace).not.toHaveBeenCalled();
  });

  it("authenticated user with API error sees dashboard content (fail open)", async () => {
    server.use(
      http.get(`/api/v1/signup/${TENANT_ID}/state`, () =>
        HttpResponse.json({ detail: "Internal server error" }, { status: 500 }),
      ),
    );

    renderGuardWithContent();

    await waitFor(() => {
      expect(screen.getByTestId("dashboard-content")).toBeInTheDocument();
    });
    expect(replace).not.toHaveBeenCalled();
  });
});
