import React from "react";
/**
 * useTenantSettingRevert hook unit tests — FE-B11
 *
 * BETA-B2 fix: now uses setupServer (MSW) — consistent with established project
 * pattern. vitest.setup.ts resets apiClient.defaults.baseURL="" so relative-path
 * MSW handlers intercept requests.
 */

import { describe, it, expect, beforeAll, afterEach, afterAll } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";

import { useTenantSettingRevert } from "./useTenantSettingRevert";
import { SETTINGS_CATALOG_QUERY_KEY } from "./queryKeys";

import type { CatalogEntry } from "@pilot/ui";

const server = setupServer(
  http.delete("/api/v1/settings/:key/tenant-override", () =>
    HttpResponse.json({
      key: "calendar_conflict_auto_expire_days",
      value: null,
      effective_value: 30,
      scope: "system",
      updated_at: new Date().toISOString(),
    }),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return {
    wrapper: ({ children }: { children: React.ReactNode }) =>
      React.createElement(
        QueryClientProvider,
        { client: queryClient },
        children,
      ),
    queryClient,
  };
}

const TENANT_OVERRIDDEN_CATALOG: CatalogEntry[] = [
  {
    key: "calendar_conflict_auto_expire_days",
    label: "Auto-expire",
    description: "",
    subSurfacePath: "/settings/integrations/general",
    dataType: "integer",
    validationRules: { min: 1, max: 365 },
    systemDefault: 30,
    currentEffectiveValue: 45,
    currentScope: "tenant",
    revertible: true,
    requiresRole: null,
    allowsUserOverride: false,
  },
];

describe("useTenantSettingRevert", () => {
  it("optimistically transitions catalog entry to scope=system", async () => {
    const { wrapper, queryClient } = createWrapper();
    queryClient.setQueryData(
      SETTINGS_CATALOG_QUERY_KEY,
      TENANT_OVERRIDDEN_CATALOG,
    );

    // Delay response to observe optimistic update
    server.use(
      http.delete("/api/v1/settings/:key/tenant-override", async () => {
        await new Promise((r) => setTimeout(r, 200));
        return HttpResponse.json({
          key: "calendar_conflict_auto_expire_days",
          value: null,
          effective_value: 30,
          scope: "system",
          updated_at: new Date().toISOString(),
        });
      }),
    );

    const { result } = renderHook(() => useTenantSettingRevert(), { wrapper });

    act(() => {
      result.current.mutate({
        key: "calendar_conflict_auto_expire_days",
        systemDefault: 30,
      });
    });

    await waitFor(() => {
      const catalog = queryClient.getQueryData<CatalogEntry[]>(
        SETTINGS_CATALOG_QUERY_KEY,
      );
      const entry = catalog?.find(
        (e) => e.key === "calendar_conflict_auto_expire_days",
      );
      expect(entry?.currentScope).toBe("system");
      expect(entry?.currentEffectiveValue).toBe(30);
    });
  });

  it("calls DELETE endpoint (not PUT)", async () => {
    const { wrapper, queryClient } = createWrapper();
    queryClient.setQueryData(
      SETTINGS_CATALOG_QUERY_KEY,
      TENANT_OVERRIDDEN_CATALOG,
    );

    let capturedMethod = "";
    let capturedUrl = "";

    server.use(
      http.delete("/api/v1/settings/:key/tenant-override", ({ request }) => {
        capturedMethod = request.method;
        capturedUrl = request.url;
        return HttpResponse.json({
          key: "calendar_conflict_auto_expire_days",
          value: null,
          effective_value: 30,
          scope: "system",
          updated_at: new Date().toISOString(),
        });
      }),
    );

    const { result } = renderHook(() => useTenantSettingRevert(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync({
        key: "calendar_conflict_auto_expire_days",
        systemDefault: 30,
      });
    });

    expect(capturedMethod).toBe("DELETE");
    expect(capturedUrl).toContain("/tenant-override");
  });
});
