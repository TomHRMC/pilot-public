/**
 * useStripeConnectStatus — Unit Tests
 *
 * Location: apps/web/src/features/settings/hooks/__tests__/useStripeConnectStatus.test.ts
 */

import { describe, it, expect, beforeAll, afterEach, afterAll } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import React from "react";
import { stripeConnectHandlers } from "../../../../mocks/handlers/stripeConnectHandlers";
import { useStripeConnectStatus } from "../useStripeConnectStatus";

const server = setupServer(...stripeConnectHandlers);
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
    return React.createElement(
      QueryClientProvider,
      { client: queryClient },
      children,
    );
  }
  Wrapper.displayName = "TestWrapper";
  return Wrapper;
}

describe("useStripeConnectStatus", () => {
  it("returns data in expected shape when disconnected", async () => {
    const { result } = renderHook(() => useStripeConnectStatus(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toMatchObject({
      connected: false,
      account_id: null,
      account_name: null,
      charges_enabled: false,
      payouts_enabled: false,
    });
  });

  it("returns data in expected shape when connected", async () => {
    server.use(
      http.get("/api/v1/settings/billing/stripe-connect/status", () =>
        HttpResponse.json({
          connected: true,
          account_id: "acct_1234567890abcdef",
          account_name: "Acme Electric LLC",
          charges_enabled: true,
          payouts_enabled: true,
        }),
      ),
    );

    const { result } = renderHook(() => useStripeConnectStatus(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toMatchObject({
      connected: true,
      account_name: "Acme Electric LLC",
      charges_enabled: true,
    });
  });

  it("returns isError: true on 500", async () => {
    server.use(
      http.get("/api/v1/settings/billing/stripe-connect/status", () =>
        HttpResponse.json({ detail: "server error" }, { status: 500 }),
      ),
    );

    const { result } = renderHook(() => useStripeConnectStatus(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.data).toBeUndefined();
  });
});
