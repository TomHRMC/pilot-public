/**
 * SignupCompletionGuard unit tests — SIGNUP-UI-FIX-1
 *
 * Location: apps/web/src/components/__tests__/SignupCompletionGuard.test.tsx
 *
 * Verifies:
 *  1. Renders children when signup_state === 'complete' (no redirect)
 *  2. Redirects to the correct wizard step when signup_state !== 'complete'
 *  3. Fails open on API error (renders children, no redirect)
 *  4. Renders null while loading (tenantId present + query pending)
 *  5. Does not fire query when tenantId is null (no user)
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
import { SignupCompletionGuard } from "../SignupCompletionGuard";

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
const TENANT_ID = "tenant-guard-test-001";

function makeAuthValue(tenantId: string | null): AuthContextValue {
  return {
    user: tenantId
      ? {
          id: "u1",
          email: "test@example.com",
          role: "owner",
          tenantId,
          displayName: "Test",
          accessToken: "tok",
        }
      : null,
    isAuthenticated: !!tenantId,
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

function renderGuard(tenantId: string | null) {
  return render(
    <QueryClientProvider client={makeQueryClient()}>
      <AuthContext.Provider value={makeAuthValue(tenantId)}>
        <SignupCompletionGuard>
          <div data-testid="guard-content">Dashboard Content</div>
        </SignupCompletionGuard>
      </AuthContext.Provider>
    </QueryClientProvider>,
  );
}

// ── Tests ───────────────────────────────────────────────────────────────────

describe("SignupCompletionGuard — SIGNUP-UI-FIX-1", () => {
  it("renders children when signup_state is 'complete' (no redirect)", async () => {
    server.use(
      http.get(`/api/v1/signup/${TENANT_ID}/state`, () =>
        HttpResponse.json({ signup_state: "complete" }),
      ),
    );

    renderGuard(TENANT_ID);

    await waitFor(() => {
      expect(screen.getByTestId("guard-content")).toBeInTheDocument();
    });
    expect(replace).not.toHaveBeenCalled();
  });

  it("redirects to /signup/plan when signup_state is 'step3_phone'", async () => {
    server.use(
      http.get(`/api/v1/signup/${TENANT_ID}/state`, () =>
        HttpResponse.json({ signup_state: "step3_phone" }),
      ),
    );

    renderGuard(TENANT_ID);

    await waitFor(() => {
      expect(replace).toHaveBeenCalledWith("/signup/plan");
    });
  });

  it("redirects to /signup/legal when signup_state is 'step1_account'", async () => {
    server.use(
      http.get(`/api/v1/signup/${TENANT_ID}/state`, () =>
        HttpResponse.json({ signup_state: "step1_account" }),
      ),
    );

    renderGuard(TENANT_ID);

    await waitFor(() => {
      expect(replace).toHaveBeenCalledWith("/signup/legal");
    });
  });

  it("fails open on API error — renders children, no redirect", async () => {
    server.use(
      http.get(`/api/v1/signup/${TENANT_ID}/state`, () =>
        HttpResponse.json({ error: "server error" }, { status: 500 }),
      ),
    );

    renderGuard(TENANT_ID);

    await waitFor(() => {
      expect(screen.getByTestId("guard-content")).toBeInTheDocument();
    });
    expect(replace).not.toHaveBeenCalled();
  });

  it("renders null while loading (tenantId present + query pending)", () => {
    // Handler that never resolves — keeps query in pending state
    server.use(
      http.get(
        `/api/v1/signup/${TENANT_ID}/state`,
        () => new Promise(() => {}),
      ),
    );

    renderGuard(TENANT_ID);

    // While loading, children should NOT be rendered
    expect(screen.queryByTestId("guard-content")).not.toBeInTheDocument();
  });

  it("does not fire query when tenantId is null (no user) — renders children", () => {
    renderGuard(null);

    // No tenantId → query is disabled → children render immediately
    expect(screen.getByTestId("guard-content")).toBeInTheDocument();
    expect(replace).not.toHaveBeenCalled();
  });
});
