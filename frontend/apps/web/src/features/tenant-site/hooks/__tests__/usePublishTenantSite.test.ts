/**
 * usePublishTenantSite — Unit Tests
 *
 * Location: apps/web/src/features/tenant-site/hooks/__tests__/usePublishTenantSite.test.ts
 *
 * Tests the 409 overwrite-confirm branch: the error is surfaced (not swallowed)
 * and extractOverwriteConflict() returns the typed conflict payload.
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
import {
  usePublishTenantSite,
  extractOverwriteConflict,
} from "../usePublishTenantSite";

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

describe("usePublishTenantSite", () => {
  it("successfully publishes and returns published status", async () => {
    const { result } = renderHook(() => usePublishTenantSite(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ confirmWebsiteOverwrite: false });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toMatchObject({
      status: "published",
      site_url: "https://lang-electric.p4tsites.com",
      website_auto_populated: true,
    });
  });

  it("surfaces 409 error (does NOT swallow it)", async () => {
    server.use(
      http.post("/api/v1/tenant-site/publish", () =>
        HttpResponse.json(
          {
            type: "https://errors.pilotfortrades.com/website-overwrite-requires-confirmation",
            title: "Website overwrite requires confirmation",
            status: 409,
            current_url: "https://old-site.example.com",
            new_url: "https://new-shop.p4tsites.com",
            brand_status: "active",
            detail: "Confirm to replace the existing URL.",
          },
          { status: 409 },
        ),
      ),
    );

    const { result } = renderHook(() => usePublishTenantSite(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ confirmWebsiteOverwrite: false });

    await waitFor(() => expect(result.current.isError).toBe(true));
    // The error should be an AxiosError with 409 status
    const error = result.current.error as Error & {
      response?: { status: number };
    };
    expect(error.response?.status).toBe(409);
  });

  it("attaches conflict payload to the error object in onError", async () => {
    server.use(
      http.post("/api/v1/tenant-site/publish", () =>
        HttpResponse.json(
          {
            type: "https://errors.pilotfortrades.com/website-overwrite-requires-confirmation",
            title: "Website overwrite requires confirmation",
            status: 409,
            current_url: "https://old-site.example.com",
            new_url: "https://new-shop.p4tsites.com",
            brand_status: "in_flight",
            detail: "Confirm to replace the existing URL.",
          },
          { status: 409 },
        ),
      ),
    );

    const { result } = renderHook(() => usePublishTenantSite(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ confirmWebsiteOverwrite: false });

    await waitFor(() => expect(result.current.isError).toBe(true));

    const error = result.current.error as Error & {
      conflict?: { current_url: string; new_url: string; brand_status: string };
    };
    expect(error.conflict).toBeDefined();
    expect(error.conflict?.current_url).toBe("https://old-site.example.com");
    expect(error.conflict?.new_url).toBe("https://new-shop.p4tsites.com");
    expect(error.conflict?.brand_status).toBe("in_flight");
  });
});

describe("extractOverwriteConflict", () => {
  it("returns null for non-AxiosError", () => {
    expect(extractOverwriteConflict(new Error("plain error"))).toBeNull();
  });

  it("returns null for non-409 AxiosError", () => {
    const fakeError = {
      isAxiosError: true,
      response: { status: 500, data: {} },
    };
    expect(extractOverwriteConflict(fakeError)).toBeNull();
  });

  it("returns null for 409 without conflict fields", () => {
    const fakeError = {
      isAxiosError: true,
      response: { status: 409, data: { detail: "some other conflict" } },
    };
    expect(extractOverwriteConflict(fakeError)).toBeNull();
  });

  it("extracts conflict payload from 409 with current_url/new_url/brand_status", () => {
    const fakeError = {
      isAxiosError: true,
      response: {
        status: 409,
        data: {
          current_url: "https://old.example.com",
          new_url: "https://new.p4tsites.com",
          brand_status: "active",
          extra_field: "extra",
        },
      },
    };
    const conflict = extractOverwriteConflict(fakeError);
    expect(conflict).not.toBeNull();
    expect(conflict?.current_url).toBe("https://old.example.com");
    expect(conflict?.new_url).toBe("https://new.p4tsites.com");
    expect(conflict?.brand_status).toBe("active");
  });
});
