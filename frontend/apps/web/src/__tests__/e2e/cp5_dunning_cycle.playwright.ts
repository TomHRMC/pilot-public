/**
 * CP-5: Dunning Cycle — Playwright E2E
 *
 * Location: apps/web/src/__tests__/e2e/cp5_dunning_cycle.playwright.ts
 *
 * Critical path: Invoices list → click "Overdue Only" toggle → table shows
 * invoices that are past due_at AND not paid/void/writeoff → overdue badge
 * is visible on at least one row.
 *
 * Scenario catalog ref: scenario-coverage-catalog.md CP-5
 * Design doc: batch-sd-design-sprint-design.md §SD-10 Part B
 *
 * Seed data: seed_e2e_db.py (Group D) seeds an invoice with:
 * - status_code="issued"
 * - due_at = 3 days in the past
 * - balance_due_cents > 0
 * This makes isOverdue() return true in the UI, showing the Overdue badge.
 * The dunning reminder logic is tested at Tier 1 (pytest); this test validates
 * the frontend filter and badge rendering for the overdue state.
 *
 * Rules:
 * - Uses storageState from global-setup.ts (owner session)
 * - No MSW — all API calls go to real FastAPI on port 8001 / pilot_e2e_db
 * - No waitForTimeout — all waits use explicit selectors / expect().toBeVisible()
 * - Asserts on specific visible content (Overdue badge, overdue-toggle)
 *
 * UI structure confirmed from source files:
 * - InvoicesPage.tsx line 222-232: data-testid="overdue-toggle" button
 * - InvoicesPage.tsx line 53-59: isOverdue() helper function
 * - InvoicesPage.tsx line 285-288: <span>Overdue</span> badge (fault-100 colors)
 * - InvoicesPage.tsx line 84: showOverdueOnly state → ?overdue=true param
 * - InvoicesPage.tsx line 135: h1 "Invoices"
 */

import { test, expect } from "@playwright/test";

test.describe("CP-5: Dunning / Overdue Invoice", () => {
  /**
   * Scenario: Invoices page renders and the "Overdue Only" toggle is present.
   * The toggle is always rendered in InvoicesPageContent regardless of data.
   *
   * Assertion: data-testid="overdue-toggle" is visible.
   * Source: InvoicesPage.tsx line 222: data-testid="overdue-toggle"
   */
  test("invoices page has Overdue Only toggle", async ({ page }) => {
    await page.goto("/invoices");
    await expect(page).not.toHaveURL(/\/login/);

    await expect(page.locator("h1")).toContainText("Invoices", {
      timeout: 10_000,
    });

    // The overdue toggle is always rendered — no conditional
    await expect(page.locator('[data-testid="overdue-toggle"]')).toBeVisible({
      timeout: 10_000,
    });
  });

  /**
   * Scenario: Overdue filter returns invoices past their due date.
   * The E2E DB has a seeded invoice with due_at in the past and status=issued.
   *
   * Steps:
   * 1. Navigate to /invoices
   * 2. Click the "Overdue Only" toggle (data-testid="overdue-toggle")
   * 3. Assert at least one invoice row is visible in the filtered result
   * 4. Assert the "Overdue" badge span is visible on that row
   *
   * Source: isOverdue() line 53-59, badge line 285-288 in InvoicesPage.tsx
   */
  test("overdue toggle filters to show past-due invoice with Overdue badge", async ({
    page,
  }) => {
    await page.goto("/invoices");

    await expect(page.locator("h1")).toContainText("Invoices", {
      timeout: 10_000,
    });

    // Click the Overdue Only toggle
    const overdueToggle = page.locator('[data-testid="overdue-toggle"]');
    await expect(overdueToggle).toBeVisible({ timeout: 10_000 });
    await overdueToggle.click();

    // After enabling filter, the overdue invoice should appear
    // The E2E DB seeds an invoice with due_at 3 days in the past, status=issued
    await expect(page.locator("table tbody tr").first()).toBeVisible({
      timeout: 10_000,
    });

    // isOverdue() returns true → renders "Overdue" badge span
    // InvoicesPage.tsx line 285-288: <span>Overdue</span> in fault-100 style
    await expect(
      page
        .locator("table td span")
        .filter({ hasText: /^Overdue$/i })
        .first(),
    ).toBeVisible({ timeout: 10_000 });
  });

  /**
   * Scenario: Overdue toggle is a toggle — clicking it again removes the filter.
   * aria-pressed attribute reflects the toggle state.
   *
   * Source: InvoicesPage.tsx line 229: aria-pressed={showOverdueOnly}
   */
  test("overdue toggle state reflects aria-pressed attribute", async ({
    page,
  }) => {
    await page.goto("/invoices");

    await expect(page.locator("h1")).toContainText("Invoices", {
      timeout: 10_000,
    });

    const overdueToggle = page.locator('[data-testid="overdue-toggle"]');
    await expect(overdueToggle).toBeVisible({ timeout: 10_000 });

    // Initial state: aria-pressed="false"
    await expect(overdueToggle).toHaveAttribute("aria-pressed", "false");

    // Click to enable overdue filter
    await overdueToggle.click();

    // Toggled state: aria-pressed="true"
    await expect(overdueToggle).toHaveAttribute("aria-pressed", "true");
  });
});
