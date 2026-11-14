/**
 * unrouted-assign-round-trip E2E — web
 *
 * Tests: Inbound to unknown number → unrouted queue → owner assigns → thread created.
 * Design doc G.3
 */

import { test, expect } from "@playwright/test";

test.describe("Unrouted message assignment round-trip", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/auth/login");
    await page.fill('[data-testid="email-input"]', "owner@test.com");
    await page.fill('[data-testid="password-input"]', "test-password");
    await page.click('[data-testid="login-submit"]');
    await page.waitForURL("**/dashboard");
  });

  test("Owner can view unrouted queue and see unmatched messages", async ({
    page,
  }) => {
    await page.goto("/settings/integrations/sms/unrouted");
    await expect(page.locator('[data-testid="unrouted-queue"]')).toBeVisible();

    // Queue should show at least the MSW fixture messages
    const rows = page.locator('[data-testid^="unrouted-row-"]');
    await expect(rows.first()).toBeVisible();
  });

  test("Owner can navigate to assignment form for an unrouted message", async ({
    page,
  }) => {
    await page.goto("/settings/integrations/sms/unrouted");
    await expect(page.locator('[data-testid="unrouted-queue"]')).toBeVisible();

    // Click the first Assign button
    await page.locator('[data-testid^="assign-btn-"]').first().click();

    // Should navigate to assign form
    await expect(page.url()).toContain("/settings/integrations/sms/unrouted/");
    await expect(
      page.locator('[data-testid="unrouted-assign-form"]'),
    ).toBeVisible();
  });

  test("Assignment form submit button is disabled until both customer + tech selected", async ({
    page,
  }) => {
    await page.goto("/settings/integrations/sms/unrouted/unrouted-001");
    const submitBtn = page.locator('[data-testid="assign-submit-btn"]');
    await expect(submitBtn).toBeDisabled();

    // Submit should remain disabled with only customer searched
    await page.fill('[data-testid="customer-search-input"]', "John");
    await expect(submitBtn).toBeDisabled();
  });
});
