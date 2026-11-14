/**
 * useCustomerDetail unit tests (MOB-B3)
 *
 * Location: apps/mobile/features/customers/hooks/__tests__/useCustomerDetail.test.ts
 */

import { renderHook, waitFor } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import {
  CUSTOMER_JOHN_SMITH,
  CUSTOMER_ACME_CORP,
} from "../../../../mocks/handlers/customersHandlers";
import { useCustomerDetail } from "../useCustomerDetail";

// ── Test server ───────────────────────────────────────────────────────────────

const capturedRequests: URL[] = [];

const server = setupServer(
  http.get("*/api/v1/customers/:customerId", ({ request, params }) => {
    capturedRequests.push(new URL(request.url));
    const { customerId } = params as { customerId: string };
    if (customerId === CUSTOMER_JOHN_SMITH.id) {
      return HttpResponse.json(CUSTOMER_JOHN_SMITH);
    }
    if (customerId === CUSTOMER_ACME_CORP.id) {
      return HttpResponse.json(CUSTOMER_ACME_CORP);
    }
    return HttpResponse.json({ detail: "Not found" }, { status: 404 });
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

describe("useCustomerDetail", () => {
  it("calls GET /api/v1/customers/{id} with correct ID", async () => {
    const { result } = renderHook(
      () => useCustomerDetail(CUSTOMER_JOHN_SMITH.id),
      { wrapper: makeWrapper() },
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(capturedRequests).toHaveLength(1);
    expect(capturedRequests[0].pathname).toMatch(
      new RegExp(`/api/v1/customers/${CUSTOMER_JOHN_SMITH.id}`),
    );
  });

  it("returns customer data on success", async () => {
    const { result } = renderHook(
      () => useCustomerDetail(CUSTOMER_JOHN_SMITH.id),
      { wrapper: makeWrapper() },
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.customer).toBeDefined();
    expect(result.current.customer?.display_name).toBe(
      CUSTOMER_JOHN_SMITH.display_name,
    );
    expect(result.current.customer?.type).toBe("residential");
    expect(result.current.customer?.email).toBe(CUSTOMER_JOHN_SMITH.email);
  });

  it("returns commercial customer data correctly", async () => {
    const { result } = renderHook(
      () => useCustomerDetail(CUSTOMER_ACME_CORP.id),
      { wrapper: makeWrapper() },
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.customer?.type).toBe("commercial");
    expect(result.current.customer?.company_name).toBe("Acme Corp");
    expect(result.current.customer?.first_name).toBeNull();
    expect(result.current.customer?.last_name).toBeNull();
  });

  it("returns isError=true on 404", async () => {
    const { result } = renderHook(() => useCustomerDetail("nonexistent-id"), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.customer).toBeUndefined();
  });

  it("does not fetch when customerId is empty string", async () => {
    const { result } = renderHook(() => useCustomerDetail(""), {
      wrapper: makeWrapper(),
    });

    // Query is disabled when customerId is falsy
    expect(result.current.isLoading).toBe(false);
    expect(capturedRequests).toHaveLength(0);
  });
});
