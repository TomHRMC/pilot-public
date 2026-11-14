/**
 * Catalog invalidation integration test — FE-B11
 *
 * BETA-B2 fix: now uses setupServer (MSW) — consistent with established project
 * pattern. vitest.setup.ts resets apiClient.defaults.baseURL="" so relative-path
 * MSW handlers intercept requests.
 */

import { describe, it, expect, beforeAll, afterEach, afterAll } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { useSettingsCatalog } from "../../src/features/settings/hooks/useSettingsCatalog";
import { useTenantSettingWrite } from "../../src/features/settings/hooks/useTenantSettingWrite";
import {
  ALL_SETTINGS_CATALOG_SYSTEM,
  ALL_SETTINGS_CATALOG_TENANT_OVERRIDES,
} from "../../src/features/settings/mocks/settingsFixtures";
import { createSettingsWrapper } from "../test-utils/settingsWrapper";

let catalogCallCount = 0;

const server = setupServer(
  http.get("/api/v1/settings/catalog", () => {
    catalogCallCount++;
    const catalog =
      catalogCallCount === 1
        ? ALL_SETTINGS_CATALOG_SYSTEM
        : ALL_SETTINGS_CATALOG_TENANT_OVERRIDES;
    return HttpResponse.json({ settings: catalog });
  }),
  http.put("/api/v1/settings/:key", () =>
    HttpResponse.json({
      key: "etc_variance_note_required_pct",
      value: 15,
      effective_value: 15,
      scope: "tenant",
      updated_at: new Date().toISOString(),
    }),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => {
  server.resetHandlers();
  catalogCallCount = 0;
});
afterAll(() => server.close());

describe("Catalog invalidation after write", () => {
  it("triggers catalog refetch after successful write", async () => {
    const { wrapper } = createSettingsWrapper();

    const { result: catalogResult } = renderHook(() => useSettingsCatalog(), {
      wrapper,
    });
    const { result: writeResult } = renderHook(() => useTenantSettingWrite(), {
      wrapper,
    });

    await waitFor(() => !catalogResult.current.isLoading);
    expect(catalogCallCount).toBe(1);

    await act(async () => {
      await writeResult.current.mutateAsync({
        key: "etc_variance_note_required_pct",
        value: 15,
      });
    });

    await waitFor(() => catalogCallCount >= 2);
    expect(catalogCallCount).toBeGreaterThanOrEqual(2);
  });
});
