/**
 * Tenant isolation E2E spec — FE-B11
 *
 * Log in as Tenant A → modify background_sync_battery_floor_pct to 30 →
 * log out → log in as Tenant B → verify still showing system default 20
 *
 * SKIPPED: Requires multi-tenant test fixtures configured in playwright.config.ts.
 * Will be un-skipped when test environment supports multi-tenant login.
 * Test runner: Playwright
 */

import { test, expect } from "@playwright/test";

test.describe("Settings tenant isolation", () => {
  // Skipped pending multi-tenant E2E fixture setup
  test.skip("modify battery floor for Tenant A → Tenant B still sees default", async ({
    page,
  }) => {
    const TENANT_A_EMAIL = "owner@tenant-a.example.com";
    const TENANT_A_PASSWORD = "test-password-a";
    const TENANT_B_EMAIL = "owner@tenant-b.example.com";
    const TENANT_B_PASSWORD = "test-password-b";

    // ── Tenant A ──────────────────────────────────────────────────────────────

    await page.goto("/auth/login");
    await page.fill('[data-testid="email-input"]', TENANT_A_EMAIL);
    await page.fill('[data-testid="password-input"]', TENANT_A_PASSWORD);
    await page.click('[data-testid="login-submit"]');
    await page.waitForURL("**/dashboard");

    await page.goto("/settings/sync-storage/background-sync");
    await page.waitForLoadState("networkidle");

    const batteryInput = page.getByTestId(
      "setting-input-background_sync_battery_floor_pct",
    );
    await expect(batteryInput).toBeVisible();
    await batteryInput.fill("30");
    await batteryInput.blur();
    await expect(
      page.getByTestId("setting-saved-background_sync_battery_floor_pct"),
    ).toBeVisible({ timeout: 5000 });

    await page.goto("/auth/logout");
    await page.waitForURL("**/login");

    // ── Tenant B ──────────────────────────────────────────────────────────────

    await page.fill('[data-testid="email-input"]', TENANT_B_EMAIL);
    await page.fill('[data-testid="password-input"]', TENANT_B_PASSWORD);
    await page.click('[data-testid="login-submit"]');
    await page.waitForURL("**/dashboard");

    await page.goto("/settings/sync-storage/background-sync");
    await page.waitForLoadState("networkidle");

    // Tenant B should still see system default (20), not Tenant A's 30
    const tenantBAnnotation = page.getByTestId(
      "setting-default-background_sync_battery_floor_pct",
    );
    await expect(tenantBAnnotation).toBeVisible();
    await expect(tenantBAnnotation).toContainText("Default · 20");
    await expect(page.locator("text=tenant override")).toHaveCount(0);
  });
});
