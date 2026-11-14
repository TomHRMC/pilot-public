/**
 * FE-B0 foundation smoke E2E test
 *
 * Location: apps/web/e2e/batch_fe_b0/foundation-smoke.e2e.spec.ts
 *
 * Prerequisites:
 *   - Web dev server running: pnpm --filter web dev
 *   - NEXT_PUBLIC_USE_MOCK_AUTH=true
 *   - NEXT_PUBLIC_MOCK_USER_ROLE=owner
 *
 * Run: pnpm --filter web e2e
 */

import { test, expect } from "@playwright/test";

test.describe("FE-B0 Foundation Smoke", () => {
  test("root redirects to /dashboard (or /login when unauthenticated)", async ({
    page,
  }) => {
    await page.goto("http://localhost:3000");
    // Without mock auth, root redirects to /dashboard which redirects to /login
    await expect(page).toHaveURL(/\/(login|dashboard)/);
  });

  test("mock-authenticated user lands on /dashboard and sees Dashboard heading", async ({
    page,
  }) => {
    // Use mock auth env — set in playwright.config.ts
    await page.goto("http://localhost:3000/dashboard");
    // In mock auth mode, RequireAuth passes through
    await expect(page.getByRole("heading", { name: /dashboard/i })).toBeVisible(
      {
        timeout: 10_000,
      },
    );
  });

  test("/schedule renders Schedule placeholder", async ({ page }) => {
    await page.goto("http://localhost:3000/schedule");
    await expect(page.getByRole("heading", { name: /schedule/i })).toBeVisible({
      timeout: 10_000,
    });
  });

  test("/settings renders Settings placeholder", async ({ page }) => {
    await page.goto("http://localhost:3000/settings");
    await expect(page.getByRole("heading", { name: /settings/i })).toBeVisible({
      timeout: 10_000,
    });
  });

  test("/login renders Login placeholder", async ({ page }) => {
    await page.goto("http://localhost:3000/login");
    await expect(page.getByRole("heading", { name: /login/i })).toBeVisible({
      timeout: 10_000,
    });
  });

  test("all 11 authed routes render without crash", async ({ page }) => {
    const routes = [
      "/dashboard",
      "/schedule",
      "/customers",
      "/quotes",
      "/invoices",
      "/reports",
      "/comms",
      "/operations",
      "/sync",
      "/notifications",
      "/settings",
    ];

    for (const route of routes) {
      await page.goto(`http://localhost:3000${route}`);
      // Page should not show a 500 error
      await expect(page.locator("h1")).toBeVisible({ timeout: 10_000 });
      const h1Text = await page.locator("h1").textContent();
      expect(h1Text).toBeTruthy();
    }
  });
});
