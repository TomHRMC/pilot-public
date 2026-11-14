/**
 * useAuthMe unit tests — web (C-B11 Part B)
 *
 * Location: apps/web/src/features/auth/hooks/__tests__/useAuthMe.test.tsx
 *
 * Tests: returns platform user, returns tenant user.
 * RULE 14: TanStack Query — retry: false, fresh QueryClient per test.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { useAuthMe, AUTH_ME_QUERY_KEY } from "../useAuthMe";

const platformResponse = {
  user_type: "platform",
  user_id: "uuid-platform",
  email: "tom@pilotfortrades.com",
  first_name: "Tom",
  last_name: "Owner",
  platform_role_code: "owner",
  redirect_to: "/operator/cohort",
};

const tenantResponse = {
  user_type: "tenant",
  user_id: "uuid-tenant",
  email: "dev@pilot.local",
  first_name: "Dev",
  last_name: "User",
  tenant_id: "uuid-tenant-id",
  role_code: "owner",
  redirect_to: "/dashboard",
};

const server = setupServer();

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

describe("useAuthMe (web)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns platform user with redirect_to=/operator/cohort", async () => {
    server.use(
      http.get("/api/v1/operator/auth/me", () =>
        HttpResponse.json(platformResponse),
      ),
    );

    const { result } = renderHook(() => useAuthMe(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.user_type).toBe("platform");
    expect(result.current.data?.platform_role_code).toBe("owner");
    expect(result.current.data?.redirect_to).toBe("/operator/cohort");
  });

  it("returns tenant user with redirect_to=/dashboard", async () => {
    server.use(
      http.get("/api/v1/operator/auth/me", () =>
        HttpResponse.json(tenantResponse),
      ),
    );

    const { result } = renderHook(() => useAuthMe(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.user_type).toBe("tenant");
    expect(result.current.data?.tenant_id).toBe("uuid-tenant-id");
    expect(result.current.data?.redirect_to).toBe("/dashboard");
  });

  it("uses the correct query key", () => {
    expect(AUTH_ME_QUERY_KEY).toEqual(["auth", "me"]);
  });
});
