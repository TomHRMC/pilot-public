/**
 * useStripeConnectDisconnect — Unit Tests
 *
 * Location: apps/web/src/features/settings/hooks/__tests__/useStripeConnectDisconnect.test.ts
 */

import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterEach,
  afterAll,
} from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import React from "react";
import { stripeConnectHandlers } from "../../../../mocks/handlers/stripeConnectHandlers";
import { useStripeConnectDisconnect } from "../useStripeConnectDisconnect";

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
  return { wrapper: Wrapper, queryClient };
}

describe("useStripeConnectDisconnect", () => {
  it("fires DELETE on mutate and completes successfully", async () => {
    let deleteWasCalled = false;
    server.use(
      http.delete("/api/v1/settings/billing/stripe-connect", () => {
        deleteWasCalled = true;
        return HttpResponse.json({
          disconnected: true,
          message: "Stripe account disconnected.",
        });
      }),
    );

    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useStripeConnectDisconnect(), {
      wrapper,
    });

    await act(async () => {
      result.current.mutate();
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(deleteWasCalled).toBe(true);
  });

  it("invalidates the status query on success", async () => {
    const { wrapper, queryClient } = createWrapper();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useStripeConnectDisconnect(), {
      wrapper,
    });

    await act(async () => {
      result.current.mutate();
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(invalidateSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        queryKey: expect.arrayContaining(["stripe-connect-status"]),
      }),
    );
  });
});
