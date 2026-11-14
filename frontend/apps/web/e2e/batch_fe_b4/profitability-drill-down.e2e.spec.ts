/**
 * Profitability Drill-Down — E2E Test
 *
 * Location: apps/web/e2e/batch_fe_b4/profitability-drill-down.e2e.spec.ts
 * Per batch-fe-b4-design.md §I.3
 *
 * Tests the profitability /reports flow.
 */

import { test, expect } from "@playwright/test";

test.describe("Profitability Drill-Down Flow", () => {
  test("open /reports → see profitability page with period selector", async ({
    page,
  }) => {
    await page.goto("/reports");

    // Page header
    await expect(page.getByText("Profitability")).toBeVisible({
      timeout: 10000,
    });

    // Period selector should be present
    await expect(page.getByText("30 days")).toBeVisible();
    await expect(page.getByText("7 days")).toBeVisible();
  });

  test("period selector changes period → active state updates", async ({
    page,
  }) => {
    await page.goto("/reports");

    await page.waitForSelector("text=30 days", { timeout: 10000 });

    // Click 7 days
    await page
      .locator('button[aria-pressed="false"]:has-text("7 days")')
      .click();

    // 7 days should now be active
    const sevenDayBtn = page.locator('button:has-text("7 days")');
    await expect(sevenDayBtn).toHaveAttribute("aria-pressed", "true");
  });

  test("live jobs section is visible when data loaded", async ({ page }) => {
    await page.goto("/reports");

    // Wait for data to load
    await page.waitForSelector("text=Active Jobs", { timeout: 10000 });
    await expect(page.getByText("Active Jobs")).toBeVisible();
  });

  test("metric cards show revenue, profit, avg margin", async ({ page }) => {
    await page.goto("/reports");

    await page.waitForSelector('[aria-label="Period summary metrics"]', {
      timeout: 10000,
    });

    // Metrics cards should show the three main numbers
    await expect(page.getByText("Revenue")).toBeVisible();
    await expect(page.getByText("Profit")).toBeVisible();
    await expect(page.getByText("Avg Margin")).toBeVisible();
  });
});
