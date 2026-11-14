/**
 * useTenantSite — Unit Tests
 *
 * Location: apps/web/src/features/tenant-site/hooks/__tests__/useTenantSite.test.ts
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
import { useTenantSite } from "../useTenantSite";
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

describe("useTenantSite", () => {
  it("returns unconfigured state with defaults when no site exists", async () => {
    const { result } = renderHook(() => useTenantSite(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toMatchObject({
      configured: false,
      site: null,
    });
    expect(result.current.data?.defaults).toMatchObject({
      display_name: "Lang Electric",
      public_email: "office@langelectric.example",
    });
  });

  it("returns configured state with site when row exists", async () => {
    server.use(
      http.get("/api/v1/tenant-site", () =>
        HttpResponse.json({
          configured: true,
          site: {
            id: "00000000-0000-0000-0000-000000000001",
            tenant_id: "00000000-0000-0000-0000-0000000000a1",
            slug: "lang-electric",
            site_kind: "hosted_compliance",
            status: "draft",
            display_name: "Lang Electric",
            tagline: "Test tagline",
            public_email: "office@langelectric.example",
            public_phone: "+15551234567",
            public_city: "Richmond",
            public_state: "VA",
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
          },
          defaults: {
            display_name: "Lang Electric",
            display_name_source: "tenant_override",
            public_email: "office@langelectric.example",
            public_email_source: "tenant_override",
            public_phone: "+15551234567",
            public_phone_source: "tenant_override",
            public_city: "Richmond",
            public_city_source: "tenant_override",
            public_state: "VA",
            public_state_source: "tenant_override",
          },
        }),
      ),
    );

    const { result } = renderHook(() => useTenantSite(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.configured).toBe(true);
    expect(result.current.data?.site?.slug).toBe("lang-electric");
    expect(result.current.data?.site?.status).toBe("draft");
  });

  it("surfaces error state on 500", async () => {
    server.use(
      http.get("/api/v1/tenant-site", () =>
        HttpResponse.json({ detail: "Server error" }, { status: 500 }),
      ),
    );

    const { result } = renderHook(() => useTenantSite(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.data).toBeUndefined();
  });

  it("uses the correct query key", () => {
    expect(tenantSiteKeys.config).toEqual(["tenant-site", "config"]);
    expect(tenantSiteKeys.all).toEqual(["tenant-site"]);
  });
});
