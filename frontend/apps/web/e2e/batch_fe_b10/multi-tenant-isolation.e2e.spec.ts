/**
 * multi-tenant-isolation E2E — web
 *
 * Tests: Tenant A threads not visible to Tenant B.
 * Design doc G.3
 */

import { test, expect } from "@playwright/test";

test.describe("Multi-tenant isolation", () => {
  test("Tenant A cannot see Tenant B customer comms", async ({ page }) => {
    // Log in as Tenant A user
    await page.goto("/auth/login");
    await page.fill('[data-testid="email-input"]', "tech-a@tenant-a.com");
    await page.fill('[data-testid="password-input"]', "test-password");
    await page.click('[data-testid="login-submit"]');

    // Navigate to customer comms for a customer that belongs to Tenant B
    await page.goto("/customers/customer-tenant-b-001/comms");

    // Should see either 404 or "No communication history" — NOT Tenant B's data
    const pageContent = await page.textContent("body");
    expect(pageContent).not.toContain("Tenant B Private Data");
    // Should show either 404 error or empty state
    const hasError = await page
      .locator('[data-testid="comms-history-error"]')
      .isVisible();
    const isEmpty = await page
      .locator('[data-testid="comms-history-empty"]')
      .isVisible();
    const isNotFound =
      page.url().includes("404") || page.url().includes("not-found");
    expect(hasError || isEmpty || isNotFound).toBe(true);
  });

  test("Unrouted queue only shows current tenant messages", async ({
    page,
  }) => {
    await page.goto("/auth/login");
    await page.fill('[data-testid="email-input"]', "owner@tenant-a.com");
    await page.fill('[data-testid="password-input"]', "test-password");
    await page.click('[data-testid="login-submit"]');

    await page.goto("/settings/integrations/sms/unrouted");
    await expect(page.locator('[data-testid="unrouted-queue"]')).toBeVisible();

    // All visible phone numbers should belong to Tenant A
    const rows = page.locator('[data-testid^="unrouted-row-"]');
    const count = await rows.count();
    for (let i = 0; i < count; i++) {
      const rowText = await rows.nth(i).textContent();
      // Tenant B phone numbers should NOT appear
      expect(rowText).not.toContain("tenant-b");
    }
  });
});
