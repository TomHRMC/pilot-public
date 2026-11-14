/**
 * useOperatorTenants hook unit tests
 *
 * Location: apps/web/src/features/operator/hooks/__tests__/useOperatorTenants.test.tsx
 *
 * C-B15 Part B: Tests data shape, query key, error state.
 * RULE 14: TanStack Query — retry: false, fresh QueryClient per test.
 */

import {
  describe,
  it,
  expect,
  beforeAll,
  afterAll,
  afterEach,
  beforeEach,
} from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import {
  useOperatorTenants,
  OPERATOR_TENANTS_QUERY_KEY,
} from "../useOperatorTenants";

const mockTenants = {
  tenants: [
    {
      tenant_id: "tenant-001",
      name: "Acme Electric",
      is_active: true,
      tier_name: "Charter",
      subscription_status: "trialing",
      created_at: "2026-08-01T00:00:00Z",
    },
  ],
};

const server = setupServer(
  http.get("/api/v1/operator/tenants", () => HttpResponse.json(mockTenants)),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  }
  return Wrapper;
}

describe("useOperatorTenants", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches and returns tenant list", async () => {
    const { result } = renderHook(() => useOperatorTenants(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.tenants).toHaveLength(1);
    expect(result.current.data?.tenants[0].name).toBe("Acme Electric");
  });

  it("uses the correct query key", () => {
    expect(OPERATOR_TENANTS_QUERY_KEY).toEqual(["operator-tenants"]);
  });

  it("surfaces error state on server failure", async () => {
    server.use(
      http.get("/api/v1/operator/tenants", () =>
        HttpResponse.json({ error: "server error" }, { status: 500 }),
      ),
    );

    const { result } = renderHook(() => useOperatorTenants(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.data).toBeUndefined();
  });
});
