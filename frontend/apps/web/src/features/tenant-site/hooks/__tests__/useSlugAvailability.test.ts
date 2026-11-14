/**
 * useSlugAvailability — Unit Tests
 *
 * Location: apps/web/src/features/tenant-site/hooks/__tests__/useSlugAvailability.test.ts
 *
 * RULE 14: retry: false QueryClient. RULE 15: server.resetHandlers in afterEach.
 */

import { describe, it, expect, beforeAll, afterEach, afterAll } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import React from "react";
import { tenantSiteHandlers } from "../../../../mocks/handlers/tenantSiteHandlers";
import { useSlugAvailability } from "../useSlugAvailability";
import { tenantSiteKeys } from "../tenantSiteQueryKeys";

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

describe("useSlugAvailability", () => {
  it("is disabled when slug is empty", async () => {
    const { result } = renderHook(() => useSlugAvailability(""), {
      wrapper: createWrapper(),
    });

    // Should not fetch — stays in pending/idle state
    expect(result.current.fetchStatus).toBe("idle");
    expect(result.current.data).toBeUndefined();
  });

  it("returns available=true for a valid slug", async () => {
    const { result } = renderHook(() => useSlugAvailability("my-shop"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toMatchObject({
      available: true,
      reason: null,
      suggestion: null,
    });
  });

  it("returns available=false with reason=reserved for reserved slugs", async () => {
    const { result } = renderHook(() => useSlugAvailability("admin"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toMatchObject({
      available: false,
      reason: "reserved",
    });
  });

  it("returns available=false with reason=taken and a suggestion", async () => {
    const { result } = renderHook(() => useSlugAvailability("taken"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toMatchObject({
      available: false,
      reason: "taken",
      suggestion: "taken-2",
    });
  });

  it("returns available=false with reason=invalid for bad format", async () => {
    const { result } = renderHook(() => useSlugAvailability("UPPER"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toMatchObject({
      available: false,
      reason: "invalid",
    });
  });

  it("uses the correct query key including slug", () => {
    expect(tenantSiteKeys.slugAvailability("my-slug")).toEqual([
      "tenant-site",
      "slug-availability",
      "my-slug",
    ]);
  });
});
