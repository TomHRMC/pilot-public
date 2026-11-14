/**
 * useCustomers unit tests (MOB-B3)
 *
 * Location: apps/mobile/features/customers/hooks/__tests__/useCustomers.test.ts
 *
 * Tests the hook calls GET /api/v1/customers/ with correct params.
 */

import { renderHook, waitFor } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import {
  ALL_CUSTOMER_FIXTURES,
  CUSTOMER_JOHN_SMITH,
} from "../../../../mocks/handlers/customersHandlers";
import { useCustomers } from "../useCustomers";

// ── Test server ───────────────────────────────────────────────────────────────

const capturedRequests: URL[] = [];

// Backend returns PaginatedCustomerResponse { items, total, limit, offset }
const server = setupServer(
  http.get("*/api/v1/customers/", ({ request }) => {
    capturedRequests.push(new URL(request.url));
    const url = new URL(request.url);
    const search = url.searchParams.get("search")?.toLowerCase() ?? "";
    const results = search
      ? ALL_CUSTOMER_FIXTURES.filter((c) =>
          c.display_name.toLowerCase().includes(search),
        )
      : ALL_CUSTOMER_FIXTURES;
    return HttpResponse.json({
      items: results,
      total: results.length,
      limit: 50,
      offset: 0,
    });
  }),
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => {
  server.resetHandlers();
  capturedRequests.length = 0;
});
afterAll(() => server.close());

function makeWrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: qc }, children);
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("useCustomers", () => {
  it("calls GET /api/v1/customers/?limit=50 with no search query", async () => {
    const { result } = renderHook(() => useCustomers(""), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(capturedRequests).toHaveLength(1);
    expect(capturedRequests[0].pathname).toMatch(/\/api\/v1\/customers\//);
    expect(capturedRequests[0].searchParams.get("limit")).toBe("50");
    expect(capturedRequests[0].searchParams.has("search")).toBe(false);
  });

  it("includes ?search= param when searchQuery is provided", async () => {
    const { result } = renderHook(() => useCustomers("john"), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(capturedRequests).toHaveLength(1);
    expect(capturedRequests[0].searchParams.get("search")).toBe("john");
    expect(capturedRequests[0].searchParams.get("limit")).toBe("50");
  });

  it("does NOT include ?search= param when searchQuery is empty string", async () => {
    const { result } = renderHook(() => useCustomers(""), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(capturedRequests[0].searchParams.has("search")).toBe(false);
  });

  it("does NOT include ?search= param when searchQuery is whitespace only", async () => {
    const { result } = renderHook(() => useCustomers("   "), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(capturedRequests[0].searchParams.has("search")).toBe(false);
  });

  it("returns customer list data from API", async () => {
    const { result } = renderHook(() => useCustomers(""), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.customers).toHaveLength(3);
    expect(result.current.customers[0].display_name).toBe(
      CUSTOMER_JOHN_SMITH.display_name,
    );
  });

  it("returns isError=true and empty array on 500", async () => {
    server.use(
      http.get("*/api/v1/customers/", () => {
        return HttpResponse.json({ detail: "server error" }, { status: 500 });
      }),
    );

    const { result } = renderHook(() => useCustomers(""), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.customers).toEqual([]);
  });
});
