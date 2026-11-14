/**
 * mswServerSmoke.test.ts — TEST-UPLIFT-1C STEP 2
 *
 * Location: apps/mobile/__tests__/meta/mswServerSmoke.test.ts
 *
 * Permanent fail-loud proof that the shared MSW server (mocks/server.ts) works
 * under jest-expo. Before TEST-UPLIFT-1C the barrel imported `voiceWsHandler`
 * whose `ws.link(...)` instantiated at module-evaluation time, poisoning the
 * Node/jsdom environment so no test could use the shared server. This smoke
 * test locks the restoration: if the barrel is ever re-poisoned, this test
 * fails immediately with `onUnhandledRequest: "error"`.
 *
 * The default barrel handler from mocks/handlers/health.ts serves
 * GET {wildcard}/api/v1/health/celery -> { status: "healthy", ... }.
 */

import { apiClient } from "@pilot/shared-api";
import { server } from "../../mocks/server";

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

it("shared MSW server intercepts an apiClient request under jest-expo", async () => {
  const res = await apiClient.get("/api/v1/health/celery");
  expect(res.data).toBeTruthy();
  // Assert specific content from the health handler fixture (Rule 15 —
  // assert by content, not just truthiness).
  expect(res.data.status).toBe("healthy");
});
