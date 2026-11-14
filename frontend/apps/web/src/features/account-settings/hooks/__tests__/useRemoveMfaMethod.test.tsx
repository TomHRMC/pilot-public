/**
 * useRemoveMfaMethod unit tests — MFA-WIRE-1 Part B (spec §8 row 6)
 *
 * Location: apps/web/src/features/account-settings/hooks/__tests__/useRemoveMfaMethod.test.tsx
 *
 * Verifies:
 *   - 204 invalidates ["users","me","mfa-status"]
 *   - Request carries the X-Cognito-Access-Token header
 *   - Error path exposes the RFC 7807 `code`
 */
import React from "react";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterEach,
  afterAll,
} from "vitest";
import { useRemoveMfaMethod } from "../useRemoveMfaMethod";

// Mock aws-amplify/auth so getCognitoAccessToken resolves a mock token
vi.mock("aws-amplify/auth", () => ({
  fetchAuthSession: vi.fn().mockResolvedValue({
    tokens: {
      accessToken: { toString: () => "mock-access-token" },
      idToken: { toString: () => "mock-id-token" },
    },
  }),
}));

// Track the access-token header on DELETE requests
let capturedAccessToken: string | null = null;

const server = setupServer(
  http.delete("/api/v1/users/me/mfa/methods/:methodId", ({ request }) => {
    capturedAccessToken = request.headers.get("x-cognito-access-token");
    return new HttpResponse(null, { status: 204 });
  }),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => {
  server.resetHandlers();
  capturedAccessToken = null;
});
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
  return { Wrapper, queryClient };
}

describe("useRemoveMfaMethod", () => {
  it("sends X-Cognito-Access-Token header and invalidates on 204", async () => {
    const { Wrapper, queryClient } = createWrapper();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useRemoveMfaMethod(), {
      wrapper: Wrapper,
    });

    result.current.mutate("mfa-method-totp");

    await waitFor(() => expect(result.current.isPending).toBe(false));

    // The access token header was sent
    expect(capturedAccessToken).toBe("mock-access-token");

    // The query was invalidated
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ["users", "me", "mfa-status"],
    });
  });

  it("exposes the RFC 7807 `code` on error", async () => {
    server.use(
      http.delete("/api/v1/users/me/mfa/methods/:methodId", () =>
        HttpResponse.json(
          { code: "cognito_unavailable", detail: "upstream failure" },
          { status: 502 },
        ),
      ),
    );

    const { Wrapper } = createWrapper();
    const { result } = renderHook(() => useRemoveMfaMethod(), {
      wrapper: Wrapper,
    });

    result.current.mutate("cognito-fail");

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.errorCode).toBe("cognito_unavailable");
    expect(result.current.errorDetail).toBe("upstream failure");
  });
});
