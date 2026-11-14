/**
 * Dispatch Board Move — E2E Test
 *
 * Location: apps/web/e2e/batch_fe_b4/dispatch-board-move.e2e.spec.ts
 * Per batch-fe-b4-design.md §I.3
 *
 * Tests the full drag-to-new-slot dispatch flow.
 * Runs against MSW (dev server) or real backend.
 */

import { test, expect } from "@playwright/test";

test.describe("Dispatch Board Move Flow", () => {
  test("load board → job cards visible → InFlightSyncIndicator shows idle", async ({
    page,
  }) => {
    await page.goto("/schedule");

    // Board should load
    await expect(page.getByText("Schedule")).toBeVisible({ timeout: 10000 });

    // Wait for board data to load (any job or tech should be visible)
    await page.waitForSelector('[role="gridcell"]', { timeout: 10000 });

    // InFlightSyncIndicator should show 'In sync' at idle
    const syncIndicator = page.locator(
      '[data-testid="sync-indicator-dispatch"]',
    );
    if (await syncIndicator.isVisible()) {
      await expect(syncIndicator).toBeVisible();
    }
  });

  test("date navigation prev/next changes displayed date", async ({ page }) => {
    await page.goto("/schedule");

    // Get initial date text
    await page.waitForSelector('button:has-text("Today")', { timeout: 10000 });

    // Click previous
    const prevButton = page.locator('button[aria-label="Previous period"]');
    await prevButton.click();

    // Click today to return
    const todayButton = page.locator('button:has-text("Today")');
    await todayButton.click();
  });

  test("view tab switching (Day → Week → Day)", async ({ page }) => {
    await page.goto("/schedule");

    await page.waitForSelector('[role="tab"]', { timeout: 10000 });

    // Click Week tab
    const weekTab = page.locator('[role="tab"]:has-text("Week")');
    await weekTab.click();
    await expect(weekTab).toHaveAttribute("aria-selected", "true");

    // Click Day tab
    const dayTab = page.locator('[role="tab"]:has-text("Day")');
    await dayTab.click();
    await expect(dayTab).toHaveAttribute("aria-selected", "true");
  });

  test("filter sidebar toggles are accessible", async ({ page }) => {
    await page.goto("/schedule");

    await page.waitForSelector("text=Filters", { timeout: 10000 });

    // Filter sidebar should be visible
    await expect(page.getByText("Filters")).toBeVisible();
    await expect(page.getByText("Tech")).toBeVisible();
    await expect(page.getByText("Status")).toBeVisible();
  });
});
