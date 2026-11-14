/**
 * E2E: Owner approval cycle
 *
 * Location: apps/web/e2e/batch_fe_b5/owner-approval-cycle.e2e.spec.ts
 * Framework: Playwright
 */

import { test, expect } from "@playwright/test";

test.describe("Owner Approval Cycle (FE-B5)", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login?mock_role=owner");
    await page.waitForURL("/");
  });

  test("owner views pending quotes inbox", async ({ page }) => {
    await page.goto("/quotes/pending");
    await expect(page.getByText("Pending Approval")).toBeVisible();
    await expect(page.getByRole("article").first()).toBeVisible();
  });

  test("owner clicks Review → sees quote detail with action bar", async ({
    page,
  }) => {
    await page.goto("/quotes/pending");
    await page
      .getByRole("link", { name: /review/i })
      .first()
      .click();
    await expect(page.getByTestId("quote-approval-action-bar")).toBeVisible();
    await expect(page.getByTestId("approve-btn")).toBeVisible();
  });

  test("owner approves quote → quote disappears from pending inbox", async ({
    page,
  }) => {
    await page.goto("/quotes/pending");
    const initialCount = await page.getByRole("article").count();
    expect(initialCount).toBeGreaterThan(0);

    await page
      .getByRole("link", { name: /review/i })
      .first()
      .click();
    await page.getByTestId("approve-btn").click();

    await page.goto("/quotes/pending");
    const newCount = await page.getByRole("article").count();
    expect(newCount).toBeLessThan(initialCount);
  });
});
