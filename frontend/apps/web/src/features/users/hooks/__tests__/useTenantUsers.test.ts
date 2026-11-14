/**
 * useTenantUsers unit tests — UI-FIX-2B
 *
 * Location: apps/web/src/features/users/hooks/__tests__/useTenantUsers.test.ts
 */

import { describe, it, expect, beforeAll, afterEach, afterAll } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import React from "react";

import { useTenantUsers } from "../useTenantUsers";

const MOCK_USERS = [
  {
    user_id: "user-001",
    email: "owner@example.com",
    first_name: "Tom",
    last_name: "Owner",
    display_color: "#4F86C6",
    role_code: "owner",
    role_name: "Owner",
    permissions: [],
    joined_at: "2025-01-15T10:00:00Z",
    is_active: true,
  },
  {
    user_id: "user-002",
    email: "mike@example.com",
    first_name: null,
    last_name: null,
    display_color: null,
    role_code: "technician",
    role_name: "Field Technician",
    permissions: [],
    joined_at: "2025-03-01T09:00:00Z",
    is_active: true,
  },
];

const server = setupServer(
  http.get("/api/v1/users", () => {
    return HttpResponse.json(MOCK_USERS);
  }),
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(
      QueryClientProvider,
      { client: queryClient },
      children,
    );
  };
}

describe("useTenantUsers", () => {
  it("calls GET /api/v1/users and returns mapped items", async () => {
    const { result } = renderHook(() => useTenantUsers(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toHaveLength(2);
    expect(result.current.data![0].user_id).toBe("user-001");
    expect(result.current.data![0].display_color).toBe("#4F86C6");
  });

  it("computes display_name from first_name + last_name when both present", async () => {
    const { result } = renderHook(() => useTenantUsers(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data![0].display_name).toBe("Tom Owner");
  });

  it("falls back display_name to email when first_name and last_name are null", async () => {
    const { result } = renderHook(() => useTenantUsers(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    // user-002 has null first/last — should fallback to email
    expect(result.current.data![1].display_name).toBe("mike@example.com");
  });
});
