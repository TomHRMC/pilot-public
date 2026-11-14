/**
 * E2E: Kickback cycle
 *
 * Location: apps/web/e2e/batch_fe_b5/kickback-cycle.e2e.spec.ts
 * Framework: Playwright
 */

import { test, expect } from "@playwright/test";

test.describe("Kickback Cycle (FE-B5)", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login?mock_role=owner");
    await page.waitForURL("/");
  });

  test("owner kicks back a quote with comment", async ({ page }) => {
    await page.goto("/quotes/pending");
    await page
      .getByRole("link", { name: /review/i })
      .first()
      .click();

    await page.getByTestId("kickback-btn").click();
    await expect(page.getByRole("dialog")).toBeVisible();

    // Submit disabled without comment
    await expect(page.getByTestId("kickback-submit-btn")).toBeDisabled();

    await page
      .getByLabel(/overall comment/i)
      .fill(
        "Please update the labor rate — it should reflect the $135/hr schedule.",
      );

    await expect(page.getByTestId("kickback-submit-btn")).toBeEnabled();
    await page.getByTestId("kickback-submit-btn").click();
    await expect(page.getByRole("dialog")).not.toBeVisible();
  });
});
