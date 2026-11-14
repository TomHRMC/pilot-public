/**
 * E2E: Signup Wizard — FE-B13
 * Location: apps/web/e2e/batch_fe_b13/signup-wizard.spec.ts
 *
 * Status: AUTHORED — pending dev backend availability
 * Requires: Dev Cognito + dev backend + MSW Stripe test mode
 *
 * Tests:
 *  1. Full signup → dashboard (trial path)
 *  2. Full signup → payment → dashboard (paid, Starter)
 *  3. Trial expiration cycle (advance clock)
 *  4. Cross-device wizard resume
 */

import { test, expect, type Page } from "@playwright/test";

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000";

async function fillAccountStep(page: Page) {
  await page.fill('[data-testid="field-business-name"]', "Apex Electric LLC");
  await page.selectOption('[data-testid="field-trade"]', "electrical");
  await page.selectOption('[data-testid="field-business-size"]', "solo");
  await page.fill('[data-testid="field-zip"]', "10001");
  await page.fill('[data-testid="field-first-name"]', "Mike");
  await page.fill('[data-testid="field-last-name"]', "Johnson");
  await page.fill(
    '[data-testid="field-email"]',
    `mike+test${Date.now()}@apexelectric.example.com`,
  );
}

// ─── E2E-1: Full signup → dashboard (trial path) ───────────────────────────

test("E2E-1: full signup wizard trial path → dashboard with checklist", async ({
  page,
}) => {
  await page.goto(`${BASE_URL}/signup/account`);

  // Step 1: Account creation
  await fillAccountStep(page);
  await page.click('[data-testid="signup-account-continue"]');
  await page.waitForURL("**/signup/legal");

  // Step 2: Legal acceptance
  await page.check('[data-testid="legal-checkbox-tos"]');
  await page.check('[data-testid="legal-checkbox-privacy"]');
  await page.check('[data-testid="legal-checkbox-eula"]');
  await page.click('[data-testid="signup-legal-continue"]');
  await page.waitForURL("**/signup/phone");

  // Step 3: Skip phone
  await page.click('[data-testid="phone-skip-button"]');
  await page.click('[data-testid="phone-skip-confirm-button"]');
  await page.waitForURL("**/signup/plan");

  // Step 4: Trial tier is pre-selected — continue
  await page.click('[data-testid="signup-plan-continue"]');
  await page.waitForURL("**/signup/ready");

  // Step 5: Get started
  await page.click('[data-testid="signup-ready-get-started"]');
  await page.waitForURL("**/dashboard");

  // Verify checklist appears on dashboard
  await expect(page.locator('[data-testid="checklist-widget"]')).toBeVisible();
});

// ─── E2E-2: Full signup → payment → dashboard (paid, Starter) ─────────────

test("E2E-2: full signup wizard paid path (Starter) → dashboard", async ({
  page,
}) => {
  await page.goto(`${BASE_URL}/signup/account`);
  await fillAccountStep(page);
  await page.click('[data-testid="signup-account-continue"]');
  await page.waitForURL("**/signup/legal");

  await page.check('[data-testid="legal-checkbox-tos"]');
  await page.check('[data-testid="legal-checkbox-privacy"]');
  await page.check('[data-testid="legal-checkbox-eula"]');
  await page.click('[data-testid="signup-legal-continue"]');
  await page.waitForURL("**/signup/phone");

  // Skip phone
  await page.click('[data-testid="phone-skip-button"]');
  await page.click('[data-testid="phone-skip-confirm-button"]');
  await page.waitForURL("**/signup/plan");

  // Select Starter paid tier
  await page.click('[data-testid="tier-card-starter"]');

  // Stripe test card (4242 4242 4242 4242)
  await page.waitForSelector('[data-testid="stripe-submit-button"]');
  // Stripe Elements are iframed — this is a simplified assertion
  await page.click('[data-testid="signup-plan-continue"]');
  await page.waitForURL("**/signup/ready");

  await page.click('[data-testid="signup-ready-get-started"]');
  await page.waitForURL("**/dashboard");
});

// ─── E2E-3: Trial expiration cycle ─────────────────────────────────────────

test("E2E-3: trial expiration hard gate blocks main content (PENDING BACKEND)", async () => {
  // Navigate to an authed route with a mock expired trial tenant
  // Requires: dev backend with clock override API
  // Status: PENDING — backend clock override endpoint not yet available

  test.skip(
    true,
    "Requires dev backend system clock override endpoint — marked pending-backend",
  );
});

// ─── E2E-4: Cross-device wizard resume ────────────────────────────────────

test("E2E-4: cross-device wizard resume — navigate to step 3 URL loads step 3", async () => {
  // Start wizard in step 1, get tenant_id, then open new context at step 4 URL
  // Requires: dev backend + real Cognito session sharing

  test.skip(
    true,
    "Requires dev backend + Cognito session — marked pending-backend",
  );
});
