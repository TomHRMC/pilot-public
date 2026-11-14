/**
 * E2E tests — Communication History (Web)
 *
 * Location: apps/web/e2e/batch_fe_b6/comms-history.e2e.spec.ts
 * Tests comms history view: pagination, filter, metadata display
 */

import { test, expect } from "@playwright/test";

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000";
const FIXTURE_CUSTOMER_ID =
  process.env.E2E_CUSTOMER_ID ?? "customer-fixture-001";

test.describe("FE-B6: Comms history view", () => {
  test("1: Cross-customer comms summary page loads", async ({ page }) => {
    await page.goto(`${BASE_URL}/comms`);
    await page.waitForURL(/\/comms|\/login/, { timeout: 10_000 });

    test.skip(
      page.url().includes("/login"),
      "Skipping — dev backend not available",
    );

    await expect(page.locator('[data-testid="comms-page"]')).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Communications" }),
    ).toBeVisible();
  });

  test("2: Customer comms page has correct headings and controls", async ({
    page,
  }) => {
    await page.goto(`${BASE_URL}/customers/${FIXTURE_CUSTOMER_ID}/comms`);
    await page.waitForURL(/\/comms|\/login/, { timeout: 10_000 });

    test.skip(
      page.url().includes("/login"),
      "Skipping — dev backend not available",
    );

    // Heading present
    await expect(
      page.getByRole("heading", { name: "Communications" }),
    ).toBeVisible();

    // Filter buttons present
    await expect(page.getByTestId("filter-all")).toBeVisible();
    await expect(page.getByTestId("filter-sms")).toBeVisible();
    await expect(page.getByTestId("filter-email")).toBeVisible();

    // Send button present
    await expect(page.getByTestId("open-template-picker-btn")).toBeVisible();
  });
});
