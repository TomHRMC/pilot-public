/**
 * useUnpublishTenantSite — Unit Tests
 *
 * Location: apps/web/src/features/tenant-site/hooks/__tests__/useUnpublishTenantSite.test.ts
 *
 * RULE 14: retry: false QueryClient. RULE 15: server.resetHandlers in afterEach.
 */

import { describe, it, expect, beforeAll, afterEach, afterAll } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import React from "react";
import { tenantSiteHandlers } from "../../../../mocks/handlers/tenantSiteHandlers";
import { useUnpublishTenantSite } from "../useUnpublishTenantSite";

const server = setupServer(...tenantSiteHandlers);
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

describe("useUnpublishTenantSite", () => {
  it("successfully unpublishes and returns warning string", async () => {
    const { result } = renderHook(() => useUnpublishTenantSite(), {
      wrapper: createWrapper(),
    });

    result.current.mutate();

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toMatchObject({
      status: "unpublished",
    });
    expect(result.current.data?.warning).toContain("NOT cleared");
  });

  it("surfaces error on 500", async () => {
    server.use(
      http.post("/api/v1/tenant-site/unpublish", () =>
        HttpResponse.json({ detail: "Server error" }, { status: 500 }),
      ),
    );

    const { result } = renderHook(() => useUnpublishTenantSite(), {
      wrapper: createWrapper(),
    });

    result.current.mutate();

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
