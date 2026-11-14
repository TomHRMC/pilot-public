/**
 * useCustomerSites unit tests (MOB-B3)
 *
 * Location: apps/mobile/features/customers/hooks/__tests__/useCustomerSites.test.ts
 */

import { renderHook, waitFor } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import {
  CUSTOMER_JOHN_SMITH,
  SITE_MAIN_HOME,
  SITE_RENTAL_PROPERTY,
} from "../../../../mocks/handlers/customersHandlers";
import { useCustomerSites } from "../useCustomerSites";

// ── Test server ───────────────────────────────────────────────────────────────

const capturedRequests: URL[] = [];

const server = setupServer(
  http.get("*/api/v1/sites/", ({ request }) => {
    capturedRequests.push(new URL(request.url));
    const url = new URL(request.url);
    const customerId = url.searchParams.get("customer_id");
    if (customerId === CUSTOMER_JOHN_SMITH.id) {
      return HttpResponse.json([SITE_MAIN_HOME, SITE_RENTAL_PROPERTY]);
    }
    return HttpResponse.json([]);
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

describe("useCustomerSites", () => {
  it("calls GET /api/v1/sites/?customer_id={id}&limit=20", async () => {
    const { result } = renderHook(
      () => useCustomerSites(CUSTOMER_JOHN_SMITH.id),
      { wrapper: makeWrapper() },
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(capturedRequests).toHaveLength(1);
    expect(capturedRequests[0].pathname).toMatch(/\/api\/v1\/sites\//);
    expect(capturedRequests[0].searchParams.get("customer_id")).toBe(
      CUSTOMER_JOHN_SMITH.id,
    );
    expect(capturedRequests[0].searchParams.get("limit")).toBe("20");
  });

  it("returns array of sites for customer-001", async () => {
    const { result } = renderHook(
      () => useCustomerSites(CUSTOMER_JOHN_SMITH.id),
      { wrapper: makeWrapper() },
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.sites).toHaveLength(2);
    expect(result.current.sites[0].name).toBe("Main Home");
    expect(result.current.sites[0].address?.line1).toBe("123 Main St");
    expect(result.current.sites[1].name).toBe("Rental Property");
  });

  it("returns empty array when no sites for customer", async () => {
    const { result } = renderHook(() => useCustomerSites("customer-no-sites"), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.sites).toEqual([]);
  });

  it("returns isError=true on 500", async () => {
    server.use(
      http.get("*/api/v1/sites/", () => {
        return HttpResponse.json({ detail: "server error" }, { status: 500 });
      }),
    );

    const { result } = renderHook(
      () => useCustomerSites(CUSTOMER_JOHN_SMITH.id),
      { wrapper: makeWrapper() },
    );

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.sites).toEqual([]);
  });
});
