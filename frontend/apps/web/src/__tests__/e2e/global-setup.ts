/**
 * Playwright Global Setup — SD-10 Tier 2
 *
 * Location: apps/web/src/__tests__/e2e/global-setup.ts
 *
 * Runs once before all Playwright specs. Authenticates as dev@pilot.local
 * (the E2E owner user seeded by seed_e2e_db.py) and saves the authenticated
 * browser storage state to playwright-auth.json so individual tests reuse it.
 *
 * Selector rationale:
 * - Email field: #login-email (id on <input> in LoginForm.tsx)
 * - Password field: #login-password (id on <input> in LoginForm.tsx)
 * - Submit: button[type="submit"] (in LoginForm.tsx)
 * - Post-login: /dashboard — DashboardPage renders <h1>Dashboard</h1>
 *
 * Rules (SD-10 prompt):
 * - NEXT_PUBLIC_USE_MOCK_AUTH must be "false" — real auth flow only
 * - waitForURL is the only acceptable "wait" here — no waitForTimeout
 */

import { chromium, type FullConfig } from "@playwright/test";

async function globalSetup(config: FullConfig) {
  const baseURL = config.projects[0].use.baseURL ?? "http://localhost:3000";

  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  // Navigate to the real login page
  await page.goto(`${baseURL}/login`);

  // Fill real Cognito credentials for the E2E owner user
  // dev@pilot.local is seeded by seed_e2e_db.py (Group C test tenant)
  await page.fill("#login-email", "dev@pilot.local");
  await page.fill(
    "#login-password",
    process.env.E2E_TEST_PASSWORD ?? "TestPassword123!",
  );
  await page.click('button[type="submit"]');

  // Wait for successful redirect to dashboard — confirms authentication succeeded
  // DashboardPage is at /dashboard per (authed)/dashboard/page.tsx
  await page.waitForURL("**/dashboard", { timeout: 15_000 });

  // Persist the authenticated session (cookies + localStorage) to disk.
  // All Playwright specs load this file via storageState in playwright.config.ts.
  await context.storageState({ path: "playwright-auth.json" });

  await browser.close();
}

export default globalSetup;
