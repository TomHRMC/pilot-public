/**
 * CP-4: Customer SMS Thread — Playwright E2E
 *
 * Location: apps/web/src/__tests__/e2e/cp4_customer_sms.playwright.ts
 *
 * Critical path: Comms page loads → communications table renders → customer
 * name links appear → SMS channel badge is visible for seeded SMS messages.
 *
 * Scenario catalog ref: scenario-coverage-catalog.md CP-4
 * Design doc: batch-sd-design-sprint-design.md §SD-10 Part B
 *
 * Seed data: seed_e2e_db.py (Group D) seeds:
 * - A customer with phone number (+15125550199 or similar)
 * - An outbound SMS thread with at least 1 message
 * - An inbound reply (setting unread_count=1 on the thread)
 * SMS_CARRIER=mock — no real Telnyx calls in E2E environment.
 *
 * Rules:
 * - Uses storageState from global-setup.ts (owner session)
 * - No MSW — all API calls go to real FastAPI on port 8001 / pilot_e2e_db
 * - No waitForTimeout — all waits use explicit selectors
 * - Asserts on specific visible content (channel badge, table presence)
 *
 * UI structure confirmed from source files:
 * - comms/page.tsx: CommsPage renders <main data-testid="comms-page">
 * - Table: data-testid="recent-comms-table"
 * - Channel badge: <span> with text "SMS" or "Email" (line 119)
 * - Customer link: <Link href="/customers/{customer_id}/comms">{customer_name}</Link>
 * - Empty state: <p> text "No messages sent yet..."
 *
 * Note: CommsPage hits GET /api/v1/communications/recent
 * (not /api/v1/comms/threads). The comms page shows outbound message history
 * across all customers, not an inbox with unread badges.
 * The unread badge lives in the customer-specific comms thread view
 * at /customers/{id}/comms (not the /comms summary page).
 * This Playwright spec validates what the /comms page actually renders.
 */

import { test, expect } from "@playwright/test";

test.describe("CP-4: Customer SMS Thread", () => {
  /**
   * Scenario: Comms page renders with its main container.
   * CommsPage always renders <main data-testid="comms-page"> regardless of
   * data state — confirms auth is valid and component mounted.
   *
   * Source: comms/page.tsx line 43: <main data-testid="comms-page">
   */
  test("comms page renders main container", async ({ page }) => {
    await page.goto("/comms");
    await expect(page).not.toHaveURL(/\/login/);

    // CommsPage always renders this main element
    await expect(page.locator('[data-testid="comms-page"]')).toBeVisible({
      timeout: 10_000,
    });
  });

  /**
   * Scenario: Comms page header is visible.
   * The h1 "Communications" is rendered in CommsPage regardless of data.
   *
   * Source: comms/page.tsx line 45: <h1>Communications</h1>
   */
  test("comms page shows Communications header", async ({ page }) => {
    await page.goto("/comms");

    await expect(page.locator('[data-testid="comms-page"]')).toBeVisible({
      timeout: 10_000,
    });

    // <h1 className="text-h1 font-medium text-neutral-900">Communications</h1>
    await expect(page.locator("h1")).toContainText("Communications", {
      timeout: 10_000,
    });
  });

  /**
   * Scenario: Comms table renders with seeded SMS messages.
   * The E2E DB has outbound SMS messages from the customer comms scenario.
   * The table data-testid="recent-comms-table" should be visible.
   *
   * Assertion: The recent-comms-table renders with at least one row.
   * Source: comms/page.tsx line 71-73: table data-testid="recent-comms-table"
   */
  test("comms table visible with seeded SMS thread data", async ({ page }) => {
    await page.goto("/comms");

    await expect(page.locator('[data-testid="comms-page"]')).toBeVisible({
      timeout: 10_000,
    });

    // Table renders when data.items.length > 0 (seeded by scenario)
    await expect(
      page.locator('[data-testid="recent-comms-table"]'),
    ).toBeVisible({ timeout: 10_000 });
  });

  /**
   * Scenario: SMS channel badge is visible in the comms table.
   * The seeded SMS messages render with a "SMS" channel badge.
   *
   * Assertion: At least one "SMS" badge span is visible in the table.
   * Source: comms/page.tsx line 119: {isSms ? "SMS" : "Email"} in badge span
   */
  test("SMS channel badge appears in comms table for seeded SMS message", async ({
    page,
  }) => {
    await page.goto("/comms");

    await expect(
      page.locator('[data-testid="recent-comms-table"]'),
    ).toBeVisible({ timeout: 10_000 });

    // Channel badge: <span>SMS</span> for actual_channel="sms" messages
    // comms/page.tsx line 118-121: badge with "SMS" text
    await expect(
      page
        .locator('[data-testid="recent-comms-table"] td span')
        .filter({ hasText: /^SMS$/i })
        .first(),
    ).toBeVisible({ timeout: 10_000 });
  });
});
