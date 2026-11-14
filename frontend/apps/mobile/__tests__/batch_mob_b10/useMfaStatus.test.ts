/**
 * useMfaStatus unit tests (MOB-B10)
 *
 * Verifies: enrolled_methods loaded correctly from GET /api/v1/users/me/mfa-status
 */
import { renderHook, waitFor } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { useMfaStatus } from "../../features/account-settings/hooks/useMfaStatus";

// ── Mocks ───────────────────────────────────────────────────────────────────

jest.mock("../../database", () => ({
  database: {
    write: jest.fn((fn: () => unknown) => fn()),
    get: jest.fn(() => ({
      create: jest.fn((fn: (r: Record<string, unknown>) => void) => {
        const record = { id: "mock-id", localSyncStatus: "pending" };
        fn(record);
        return Promise.resolve(record);
      }),
    })),
  },
}));

// ── Server ──────────────────────────────────────────────────────────────────

const server = setupServer(
  http.get("*/api/v1/users/me/mfa-status", () =>
    HttpResponse.json({
      enrolled_methods: [],
      tenant_policy_required: false,
      grace_period_active: false,
      grace_ends_at: null,
      enforcement_activated: false,
    }),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Wrapper ─────────────────────────────────────────────────────────────────

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return React.createElement(QueryClientProvider, { client: qc }, children);
}

// ── Tests ───────────────────────────────────────────────────────────────────

describe("useMfaStatus", () => {
  it("returns enrolled_methods: [] when server returns empty array", async () => {
    const { result } = renderHook(() => useMfaStatus(), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.data?.enrolled_methods).toEqual([]);
  });

  it("returns enrolled_methods: ['totp'] when server returns one method", async () => {
    server.use(
      http.get("*/api/v1/users/me/mfa-status", () =>
        HttpResponse.json({
          enrolled_methods: ["totp"],
          tenant_policy_required: false,
          grace_period_active: false,
          grace_ends_at: null,
          enforcement_activated: false,
        }),
      ),
    );

    const { result } = renderHook(() => useMfaStatus(), { wrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.data?.enrolled_methods).toEqual(["totp"]);
  });
});
