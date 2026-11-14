/**
 * C-B5 Ready page — Charter vs non-Charter branch integration test
 *
 * Location: apps/web/src/__tests__/batch_c_b5/ready_page_charter.integration.test.tsx
 *
 * Verifies:
 *  - Charter path (requires_payment_method=false) renders Step5Confirmation
 *  - Non-Charter path (requires_payment_method=true) renders trial callout
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

import SignupReadyPage from "@/app/signup/ready/page";

const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => {
  server.resetHandlers();
  replace.mockReset();
  push.mockReset();
  sessionStorage.clear();
});
afterAll(() => server.close());

const TENANT = "tenant-cb5-ready-test-001";

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

function renderReadyPage() {
  return render(
    <AuthContext.Provider value={notAuthValue}>
      <QueryClientProvider client={makeQueryClient()}>
        <SignupReadyPage />
      </QueryClientProvider>
    </AuthContext.Provider>,
  );
}

describe("C-B5 — Ready page Charter branch", () => {
  it("Charter path (requires_payment_method=false) renders Step5Confirmation", async () => {
    sessionStorage.setItem(WIZARD_TENANT_ID_KEY, TENANT);

    server.use(
      http.get(`/api/v1/signup/${TENANT}/state`, () =>
        HttpResponse.json({
          tenant_id: TENANT,
          signup_state: "step5_confirm",
          collected_data: {
            owner_first_name: "Mike",
            business_name: "Apex Electric",
            phone_verified: true,
            requires_payment_method: false,
            free_period_ends_at: "2026-11-02T18:37:42Z",
            charter_member_number: 7,
          },
        }),
      ),
    );

    renderReadyPage();

    await waitFor(() => {
      expect(
        screen.getByTestId("charter-confirmation-callout"),
      ).toBeInTheDocument();
    });

    // The trial callout should NOT be present
    expect(screen.queryByTestId("trial-callout")).not.toBeInTheDocument();
  });

  it("non-Charter path (requires_payment_method=true) renders trial callout", async () => {
    sessionStorage.setItem(WIZARD_TENANT_ID_KEY, TENANT);

    server.use(
      http.get(`/api/v1/signup/${TENANT}/state`, () =>
        HttpResponse.json({
          tenant_id: TENANT,
          signup_state: "step5_confirm",
          collected_data: {
            owner_first_name: "Mike",
            business_name: "Apex Electric",
            phone_verified: true,
            requires_payment_method: true,
            free_period_ends_at: null,
            charter_member_number: null,
          },
        }),
      ),
    );

    renderReadyPage();

    await waitFor(() => {
      expect(screen.getByTestId("trial-callout")).toBeInTheDocument();
    });

    // The Charter confirmation callout should NOT be present
    expect(
      screen.queryByTestId("charter-confirmation-callout"),
    ).not.toBeInTheDocument();
  });
});
