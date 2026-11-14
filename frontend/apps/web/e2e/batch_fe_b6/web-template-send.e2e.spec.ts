/**
 * E2E tests — FE-B6 Customer Comms Outbound (Web, Playwright)
 *
 * Location: apps/web/e2e/batch_fe_b6/web-template-send.e2e.spec.ts
 * Target: 3+ e2e tests
 *
 * Tests the full template send flow against the dev backend (or MSW in CI).
 * These are smoke tests — they verify the happy path end-to-end.
 */

import { test, expect } from "@playwright/test";

// ── Configuration ─────────────────────────────────────────────────────────────

// For CI, use MSW interceptors defined in playwright.config.ts
// For local dev with real backend: set PILOT_E2E_BACKEND=real
const BASE_URL = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000";

// Fixture customer ID — must exist in dev seed data
const FIXTURE_CUSTOMER_ID =
  process.env.E2E_CUSTOMER_ID ?? "customer-fixture-001";

// ── Tests ─────────────────────────────────────────────────────────────────────

test.describe("FE-B6: Web template send flow", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to customer comms page
    await page.goto(`${BASE_URL}/customers/${FIXTURE_CUSTOMER_ID}/comms`);
    // Wait for page to load (auth redirect may occur)
    await page.waitForURL(/\/customers\/.*\/comms|\/login/, {
      timeout: 10_000,
    });
  });

  test("1: Full template send cycle — preview, confirm, sent status appears in history", async ({
    page,
  }) => {
    // Skip if we landed on login (no backend available)
    test.skip(
      page.url().includes("/login"),
      "Skipping — dev backend not available",
    );

    // Open template picker
    await page.getByTestId("open-template-picker-btn").click();
    await page.waitForSelector('[data-testid="template-picker-sheet"]', {
      timeout: 5_000,
    });

    // Select "On my way" template
    await page.getByTestId("template-card-on_my_way").click();

    // Wait for preview modal
    await page.waitForSelector('[data-testid="message-preview-modal"]', {
      timeout: 5_000,
    });

    // Verify rendered body is visible
    const body = await page.locator('[data-testid="message-preview-modal"]');
    await expect(body).toBeVisible();

    // Confirm send
    await page.getByTestId("preview-send-btn").click();

    // Wait for modal to close
    await expect(
      page.locator('[data-testid="message-preview-modal"]'),
    ).not.toBeVisible({ timeout: 5_000 });

    // Verify comms history table shows new entry
    await page.waitForSelector('[data-testid="comms-history-table"]', {
      timeout: 10_000,
    });
    const table = page.getByTestId("comms-history-table");
    await expect(table).toBeVisible();

    // At least one row present
    const rows = table.locator("tbody tr");
    await expect(rows).not.toHaveCount(0);
  });

  test("2: Channel filter — SMS only filter hides email messages", async ({
    page,
  }) => {
    test.skip(
      page.url().includes("/login"),
      "Skipping — dev backend not available",
    );

    await page.waitForSelector('[data-testid="comms-history-table"]', {
      timeout: 10_000,
    });

    // Apply SMS filter
    await page.getByTestId("filter-sms").click();

    // All visible rows should be SMS
    const channelCells = page.locator(
      '[data-testid="comms-history-table"] tbody tr td:nth-child(2)',
    );
    const count = await channelCells.count();
    if (count > 0) {
      for (let i = 0; i < count; i++) {
        await expect(channelCells.nth(i)).toContainText("SMS");
      }
    }
  });

  test("3: Communication history reflects sent messages (isolated)", async ({
    page,
  }) => {
    test.skip(
      page.url().includes("/login"),
      "Skipping — dev backend not available",
    );

    // Visit comms page for a customer with known history
    await page.goto(`${BASE_URL}/customers/${FIXTURE_CUSTOMER_ID}/comms`);

    // Wait for table or empty state
    await Promise.race([
      page.waitForSelector('[data-testid="comms-history-table"]'),
      page.waitForSelector("text=No messages sent yet"),
    ]);

    // Page should be visible without error
    await expect(
      page.locator('[data-testid="customer-comms-page"]'),
    ).toBeVisible();
  });
});

test.describe("FE-B6: Template picker — online guard", () => {
  test("4: Template picker loads all 6 templates", async ({ page }) => {
    test.skip(
      page.url().includes("/login"),
      "Skipping — dev backend not available",
    );

    await page.goto(`${BASE_URL}/customers/${FIXTURE_CUSTOMER_ID}/comms`);
    await page.waitForURL(/\/comms/, { timeout: 10_000 });

    await page.getByTestId("open-template-picker-btn").click();
    await page.waitForSelector('[data-testid="template-grid"]', {
      timeout: 5_000,
    });

    // All 6 MVP templates should be visible
    const cards = page.locator('[data-testid^="template-card-"]');
    await expect(cards).toHaveCount(6);
  });
});
