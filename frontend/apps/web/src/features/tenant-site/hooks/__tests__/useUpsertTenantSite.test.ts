/**
 * useUpsertTenantSite — Unit Tests
 *
 * Location: apps/web/src/features/tenant-site/hooks/__tests__/useUpsertTenantSite.test.ts
 *
 * RULE 14: retry: false QueryClient. RULE 15: server.resetHandlers in afterEach.
 */

import {
  describe,
  it,
  expect,
  beforeAll,
  afterEach,
  afterAll,
  vi,
} from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import React from "react";
import { tenantSiteHandlers } from "../../../../mocks/handlers/tenantSiteHandlers";
import { useUpsertTenantSite } from "../useUpsertTenantSite";

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

describe("useUpsertTenantSite", () => {
  it("successfully upserts a site draft and returns the response", async () => {
    const { result } = renderHook(() => useUpsertTenantSite(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      site_kind: "hosted_compliance",
      slug: "my-new-shop",
      display_name: "My New Shop",
      tagline: null,
      public_email: null,
      public_phone: null,
      public_city: null,
      public_state: null,
      show_full_address: false,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toMatchObject({
      slug: "my-new-shop",
      site_kind: "hosted_compliance",
      status: "draft",
      display_name: "My New Shop",
    });
  });

  it("sends an Idempotency-Key header", async () => {
    let capturedHeaders: Record<string, string> = {};
    server.use(
      http.put("/api/v1/tenant-site", ({ request }) => {
        capturedHeaders = Object.fromEntries(request.headers.entries());
        return HttpResponse.json({
          id: "test-id",
          tenant_id: "test-tenant",
          slug: "test-slug",
          site_kind: "hosted_compliance",
          status: "draft",
          display_name: "Test",
          tagline: null,
          public_email: null,
          public_phone: null,
          public_city: null,
          public_state: null,
          public_address_line1: null,
          public_postal_code: null,
          show_full_address: false,
          template_version: "v1",
          published_at: null,
          unpublished_at: null,
          kit_sent_at: null,
          website_auto_populated: false,
          idempotency_key: null,
          site_url: null,
          requirements_emailed_at: null,
        });
      }),
    );

    const { result } = renderHook(() => useUpsertTenantSite(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      site_kind: "hosted_compliance",
      slug: "test-slug",
      display_name: "Test",
      tagline: null,
      public_email: null,
      public_phone: null,
      public_city: null,
      public_state: null,
      show_full_address: false,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(capturedHeaders["idempotency-key"]).toBeTruthy();
  });

  it("surfaces 409 slug-taken error", async () => {
    const { result } = renderHook(() => useUpsertTenantSite(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      site_kind: "hosted_compliance",
      slug: "taken",
      display_name: "Test",
      tagline: null,
      public_email: null,
      public_phone: null,
      public_city: null,
      public_state: null,
      show_full_address: false,
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });

  it("invalidates the config query on settle", async () => {
    const invalidateSpy = vi.spyOn(QueryClient.prototype, "invalidateQueries");

    const { result } = renderHook(() => useUpsertTenantSite(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({
      site_kind: "hosted_compliance",
      slug: "invalidate-test",
      display_name: "Test",
      tagline: null,
      public_email: null,
      public_phone: null,
      public_city: null,
      public_state: null,
      show_full_address: false,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          queryKey: ["tenant-site", "config"],
        }),
      );
    });
    invalidateSpy.mockRestore();
  });
});
