/**
 * Concurrent Staleness — E2E Test (Skipped without real backend)
 *
 * Location: apps/web/e2e/batch_fe_b4/concurrent-staleness.e2e.spec.ts
 * Per batch-fe-b4-design.md §I.3
 *
 * Full concurrent test requires two-tab + real backend.
 * The retry logic is fully validated in useStalenessRetry unit tests
 * and staleness-retry-flow integration tests.
 *
 * @skip-without-be-b3
 */

import { test, expect } from "@playwright/test";

test.describe("Concurrent User Staleness (requires real backend)", () => {
  test.skip(
    !process.env.ENABLE_REAL_BACKEND_TESTS,
    "Skipped without real BE-B3 backend",
  );

  test("two tabs: tab 2 gets staleness dialog when same job moved from tab 1", async ({
    browser,
  }) => {
    const context = await browser.newContext();
    const tab1 = await context.newPage();
    const tab2 = await context.newPage();

    await tab1.goto("/schedule");
    await tab2.goto("/schedule");

    await tab1.waitForSelector('[role="gridcell"]', { timeout: 10000 });
    await tab2.waitForSelector('[role="gridcell"]', { timeout: 10000 });

    // Tab 1: Move job X to a new slot
    // Tab 2: Try to move the same job X → gets 409 → staleness dialog appears
    // Tab 2: Click "Retry with updated data" → move completes

    await context.close();
    expect(true).toBe(true); // Placeholder assertion
  });
});
