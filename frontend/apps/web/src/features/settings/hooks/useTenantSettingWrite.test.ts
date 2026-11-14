import React from "react";
/**
 * useTenantSettingWrite hook unit tests — FE-B11
 *
 * BETA-B2 fix: now uses setupServer (MSW) — consistent with established project
 * pattern. vitest.setup.ts resets apiClient.defaults.baseURL="" so relative-path
 * MSW handlers intercept requests.
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
import { renderHook, act, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";

import { useTenantSettingWrite } from "./useTenantSettingWrite";
import { SETTINGS_CATALOG_QUERY_KEY } from "./queryKeys";

import type { CatalogEntry } from "@pilot/ui";

const server = setupServer(
  http.put("/api/v1/settings/:key", () =>
    HttpResponse.json({
      key: "calendar_conflict_auto_expire_days",
      value: 45,
      effective_value: 45,
      scope: "tenant",
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

const MOCK_CATALOG: CatalogEntry[] = [
  {
    key: "calendar_conflict_auto_expire_days",
    label: "Auto-expire",
    description: "",
    subSurfacePath: "/settings/integrations/general",
    dataType: "integer",
    validationRules: { min: 1, max: 365 },
    systemDefault: 30,
    currentEffectiveValue: 30,
    currentScope: "system",
    revertible: false,
    requiresRole: null,
    allowsUserOverride: false,
  },
];

describe("useTenantSettingWrite", () => {
  it("applies optimistic update before server response", async () => {
    const { wrapper, queryClient } = createWrapper();
    queryClient.setQueryData(SETTINGS_CATALOG_QUERY_KEY, MOCK_CATALOG);

    // Delay the response so we can observe optimistic update first
    server.use(
      http.put("/api/v1/settings/:key", async () => {
        await new Promise((r) => setTimeout(r, 200));
        return HttpResponse.json({
          key: "calendar_conflict_auto_expire_days",
          value: 45,
          effective_value: 45,
          scope: "tenant",
          updated_at: new Date().toISOString(),
        });
      }),
    );

    const { result } = renderHook(() => useTenantSettingWrite(), { wrapper });

    act(() => {
      result.current.mutate({
        key: "calendar_conflict_auto_expire_days",
        value: 45,
      });
    });

    // Optimistic update should be applied immediately
    await waitFor(() => {
      const catalog = queryClient.getQueryData<CatalogEntry[]>(
        SETTINGS_CATALOG_QUERY_KEY,
      );
      const entry = catalog?.find(
        (e) => e.key === "calendar_conflict_auto_expire_days",
      );
      expect(entry?.currentEffectiveValue).toBe(45);
    });
  });

  it("rolls back optimistic update on error", async () => {
    const { wrapper, queryClient } = createWrapper();
    queryClient.setQueryData(SETTINGS_CATALOG_QUERY_KEY, MOCK_CATALOG);

    server.use(
      http.put("/api/v1/settings/:key", () =>
        HttpResponse.json({ detail: "Server error" }, { status: 500 }),
      ),
    );

    const { result } = renderHook(() => useTenantSettingWrite(), { wrapper });

    await act(async () => {
      try {
        await result.current.mutateAsync({
          key: "calendar_conflict_auto_expire_days",
          value: 99,
        });
      } catch {}
    });

    await waitFor(() => {
      const catalog = queryClient.getQueryData<CatalogEntry[]>(
        SETTINGS_CATALOG_QUERY_KEY,
      );
      const entry = catalog?.find(
        (e) => e.key === "calendar_conflict_auto_expire_days",
      );
      // Should roll back to original value (30)
      expect(entry?.currentEffectiveValue).toBe(30);
    });
  });

  it("invalidates settings-catalog on success", async () => {
    const { wrapper, queryClient } = createWrapper();
    const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

    const { result } = renderHook(() => useTenantSettingWrite(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync({
        key: "calendar_conflict_auto_expire_days",
        value: 45,
      });
    });

    expect(invalidateSpy).toHaveBeenCalledWith(
      expect.objectContaining({ queryKey: SETTINGS_CATALOG_QUERY_KEY }),
    );
  });
});
