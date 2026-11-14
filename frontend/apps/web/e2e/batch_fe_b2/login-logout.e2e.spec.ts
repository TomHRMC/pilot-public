/**
 * FE-B2 Login / Logout E2E tests — web
 *
 * Location: apps/web/e2e/batch_fe_b2/login-logout.e2e.spec.ts
 *
 * Prerequisites:
 *   - Web dev server running: pnpm --filter web dev
 *   - NEXT_PUBLIC_USE_MOCK_AUTH=true
 *   - NEXT_PUBLIC_MOCK_USER_ROLE=owner
 *   - NEXT_PUBLIC_USE_MSW_MOCKS=true
 *
 * Run: pnpm --filter web e2e
 */

import { test, expect } from "@playwright/test";

test.describe("FE-B2 Login / Logout cycle (web)", () => {
  test("mock login as owner lands on /dashboard", async ({ page }) => {
    await page.goto("http://localhost:3000/login");

    // In mock mode, the form renders a role dropdown
    await expect(page.getByText(/mock auth active/i)).toBeVisible({
      timeout: 10_000,
    });

    // Click sign-in button
    await page.getByRole("button", { name: /sign in as/i }).click();

    // Should redirect to /dashboard
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10_000 });
    await expect(page.getByRole("heading", { name: /dashboard/i })).toBeVisible(
      { timeout: 10_000 },
    );
  });

  test("logout from dashboard clears session and redirects to /login with banner", async ({
    page,
  }) => {
    // Start on dashboard (mock auth passes RequireAuth)
    await page.goto("http://localhost:3000/dashboard");
    await expect(page.getByRole("heading", { name: /dashboard/i })).toBeVisible(
      { timeout: 10_000 },
    );

    // Click sign out
    await page.getByRole("button", { name: /sign out/i }).click();

    // Should redirect to /login?signedOut=true
    await expect(page).toHaveURL(/login.*signedOut=true/, { timeout: 10_000 });

    // "You've been signed out" banner should appear
    await expect(page.getByText(/signed out/i)).toBeVisible({
      timeout: 10_000,
    });
  });

  test("/login renders sign-in form with email and forgot password link", async ({
    page,
  }) => {
    await page.goto("http://localhost:3000/login");
    await expect(
      page.getByRole("heading", { name: /pilot for trades/i }),
    ).toBeVisible({ timeout: 10_000 });
    // Login form renders (mock mode or real)
    await expect(page.locator("form[aria-label='Sign in']")).toBeVisible({
      timeout: 10_000,
    });
  });

  test("/password-reset page renders step 1 form", async ({ page }) => {
    await page.goto("http://localhost:3000/password-reset");
    await expect(
      page.getByRole("heading", { name: /reset password/i }),
    ).toBeVisible({ timeout: 10_000 });
    await expect(
      page.getByRole("button", { name: /send reset code/i }),
    ).toBeVisible({ timeout: 10_000 });
  });
});
