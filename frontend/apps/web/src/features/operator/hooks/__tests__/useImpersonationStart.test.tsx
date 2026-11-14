/**
 * useImpersonationStart + useImpersonationEnd hook unit tests
 *
 * Location: apps/web/src/features/operator/hooks/__tests__/useImpersonationStart.test.tsx
 *
 * C-B15 Part B: Tests correct method/URL/payload; error surfaces.
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
  vi,
} from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { useImpersonationStart } from "../useImpersonationStart";
import { useImpersonationEnd } from "../useImpersonationEnd";

const server = setupServer(
  http.post("/api/v1/operator/impersonation/start", async ({ request }) => {
    const body = (await request.json()) as { tenant_id: string };
    return HttpResponse.json({
      tenant_id: body.tenant_id,
      tenant_name: "Acme Electric",
      impersonator_user_id: "uuid-platform",
      role_code: "owner",
      started_at: "2026-08-08T16:00:00Z",
    });
  }),
  http.post("/api/v1/operator/impersonation/end", () =>
    HttpResponse.json({ ended: true }),
  ),
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

describe("useImpersonationStart", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("sends POST to /api/v1/operator/impersonation/start with correct payload", async () => {
    const { result } = renderHook(() => useImpersonationStart(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.mutateAsync({ tenantId: "tenant-001" });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.tenant_id).toBe("tenant-001");
    expect(result.current.data?.tenant_name).toBe("Acme Electric");
    expect(result.current.data?.role_code).toBe("owner");
  });

  it("surfaces error on 403", async () => {
    server.use(
      http.post("/api/v1/operator/impersonation/start", () =>
        HttpResponse.json(
          {
            type: "https://errors.pilotfortrades.com/forbidden",
            title: "Forbidden",
            status: 403,
          },
          { status: 403 },
        ),
      ),
    );

    const { result } = renderHook(() => useImpersonationStart(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      try {
        await result.current.mutateAsync({ tenantId: "tenant-forbidden" });
      } catch {
        // expected
      }
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

describe("useImpersonationEnd", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("sends POST to /api/v1/operator/impersonation/end and returns ended: true", async () => {
    const { result } = renderHook(() => useImpersonationEnd(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.mutateAsync({ tenantId: "tenant-001" });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.ended).toBe(true);
  });
});
