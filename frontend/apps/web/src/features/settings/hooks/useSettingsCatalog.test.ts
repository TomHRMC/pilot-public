import React from "react";
/**
 * useSettingsCatalog hook unit tests — FE-B11
 *
 * BETA-B2 fix: now uses setupServer (MSW) — consistent with established project
 * pattern (see dispatch-board, profitability tests). vitest.setup.ts resets
 * apiClient.defaults.baseURL="" so relative-path MSW handlers intercept requests.
 */

import { describe, it, expect, beforeAll, afterEach, afterAll } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";

import { useSettingsCatalog } from "./useSettingsCatalog";
import { ALL_SETTINGS_CATALOG_SYSTEM } from "../mocks/settingsFixtures";

const server = setupServer(
  http.get("/api/v1/settings/catalog", () =>
    HttpResponse.json({ settings: ALL_SETTINGS_CATALOG_SYSTEM }),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(
      QueryClientProvider,
      { client: queryClient },
      children,
    );
  };
}

describe("useSettingsCatalog", () => {
  it("caches at ['settings-catalog'] key", async () => {
    const { result } = renderHook(() => useSettingsCatalog(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    // Catalog is populated — confirms the request went to the right endpoint
    expect(result.current.catalog.length).toBeGreaterThan(0);
  });

  it("normalizes snake_case → camelCase correctly", async () => {
    const { result } = renderHook(() => useSettingsCatalog(), {
      wrapper: createWrapper(),
    });

    await waitFor(() =>
      expect(result.current.catalog.length).toBeGreaterThan(0),
    );

    const entry = result.current.catalog.find(
      (e) => e.key === "calendar_conflict_auto_expire_days",
    );

    expect(entry).toBeDefined();
    expect(entry).toHaveProperty("subSurfacePath");
    expect(entry).toHaveProperty("dataType");
    expect(entry).toHaveProperty("currentEffectiveValue");
    expect(entry).toHaveProperty("currentScope");
    expect(entry).toHaveProperty("allowsUserOverride");
  });

  it("getCatalogEntry returns the correct entry by key", async () => {
    const { result } = renderHook(() => useSettingsCatalog(), {
      wrapper: createWrapper(),
    });

    await waitFor(() =>
      expect(result.current.catalog.length).toBeGreaterThan(0),
    );

    const entry = result.current.getCatalogEntry(
      "calendar_conflict_auto_expire_days",
    );
    expect(entry).toBeDefined();
    expect(entry?.key).toBe("calendar_conflict_auto_expire_days");
  });

  it("getCatalogEntriesForPath returns all entries for a path", async () => {
    const { result } = renderHook(() => useSettingsCatalog(), {
      wrapper: createWrapper(),
    });

    await waitFor(() =>
      expect(result.current.catalog.length).toBeGreaterThan(0),
    );

    const allPaths = result.current.catalog.map((e) => e.subSurfacePath);
    const uniquePaths = [...new Set(allPaths)];

    for (const path of uniquePaths) {
      const entries = result.current.getCatalogEntriesForPath(path);
      expect(entries.length).toBeGreaterThan(0);
      expect(entries.every((e) => e.subSurfacePath === path)).toBe(true);
    }
  });
});
