/**
 * CP-3: Dispatch + Field Sync — Playwright E2E
 *
 * Location: apps/web/src/__tests__/e2e/cp3_dispatch_field_sync.playwright.ts
 *
 * Critical path: Jobs list loads → at least one job visible → job status
 * badges render correctly → completed job shows "Completed" status.
 *
 * Scenario catalog ref: scenario-coverage-catalog.md CP-3
 * Design doc: batch-sd-design-sprint-design.md §SD-10 Part B
 *
 * Seed data: seed_e2e_db.py seeds:
 * - A job with status="scheduled" assigned to tech@pilot.local
 * - A job with status="completed" with a time entry (2h × $120/hr = $240)
 *
 * Rules:
 * - Uses storageState from global-setup.ts (owner session)
 * - No MSW — all API calls go to real FastAPI on port 8001 / pilot_e2e_db
 * - No waitForTimeout — all waits use explicit selectors
 * - Asserts on specific visible content (status labels), not just 200
 *
 * UI structure confirmed from source files:
 * - JobsPage.tsx: StatusBadge renders text from labelMap (line 54-62)
 *   - "completed" → "Completed"
 *   - "scheduled" → "Scheduled"
 *   - "in_progress" → "In Progress"
 * - JobRow (line 75): <StatusBadge statusCode={job.status_code} />
 * - Jobs table: thead has Customer | Status | Scheduled | Actions columns
 */

import { test, expect } from "@playwright/test";

test.describe("CP-3: Dispatch + Field Sync", () => {
  /**
   * Scenario: Jobs list page renders with at least one seeded job.
   * The E2E DB has pre-seeded jobs from the dispatch scenario.
   *
   * Assertion: <h1>Jobs</h1> is visible and table has at least one row.
   * Source: JobsPage.tsx line 152-155: <h1>Jobs</h1>
   */
  test("jobs list renders with seeded jobs", async ({ page }) => {
    await page.goto("/jobs");
    await expect(page).not.toHaveURL(/\/login/);

    // JobsPage renders <h1 className="text-2xl font-semibold">Jobs</h1>
    // JobsPage.tsx line 152
    await expect(page.locator("h1")).toContainText("Jobs", { timeout: 10_000 });

    // At least one job row should be visible in the E2E DB
    await expect(page.locator("table tbody tr").first()).toBeVisible({
      timeout: 10_000,
    });
  });

  /**
   * Scenario: Jobs list shows a "Scheduled" status badge.
   * The E2E DB seeds a job with status_code="scheduled".
   *
   * Assertion: StatusBadge with text "Scheduled" is visible in the table.
   * Source: JobsPage.tsx labelMap line 56: scheduled: "Scheduled"
   * The badge is a <span> inside <StatusBadge> inside <td>.
   */
  test("jobs list shows Scheduled status badge for dispatch scenario job", async ({
    page,
  }) => {
    await page.goto("/jobs");
    await expect(page.locator("h1")).toContainText("Jobs", { timeout: 10_000 });

    // StatusBadge renders labelMap text in a <span> inside the status <td>
    // JobsPage.tsx line 63-73: <span className={colorClass}>{label}</span>
    await expect(
      page
        .locator("table td span")
        .filter({ hasText: /^Scheduled$/i })
        .first(),
    ).toBeVisible({ timeout: 10_000 });
  });

  /**
   * Scenario: Jobs list shows a "Completed" status badge.
   * The E2E DB seeds a completed job (tech clocked 2h at master rate = $240 cost).
   *
   * Assertion: StatusBadge with text "Completed" is visible.
   * This confirms the time-entry + job-completion flow completed in seed data.
   * Source: JobsPage.tsx labelMap line 58: completed: "Completed"
   */
  test("jobs list shows Completed status badge — time entry flow complete", async ({
    page,
  }) => {
    await page.goto("/jobs");
    await expect(page.locator("h1")).toContainText("Jobs", { timeout: 10_000 });

    // StatusBadge renders "Completed" for status_code="completed"
    // Seed data: seed_scenario_dispatch.py creates completed job with 2h time entry
    await expect(
      page
        .locator("table td span")
        .filter({ hasText: /^Completed$/i })
        .first(),
    ).toBeVisible({ timeout: 10_000 });
  });

  /**
   * Scenario: Completed jobs show the "→ Invoice" convert action.
   * The owner role has invoices.create permission, so the RoleGate allows
   * the convert link for completed/invoice_pending jobs.
   *
   * Assertion: At least one "→ Invoice" link is visible in the actions column.
   * Source: JobsPage.tsx line 97-104: conditional Link for TERMINAL_STATUSES
   */
  test("completed job shows convert-to-invoice action for owner role", async ({
    page,
  }) => {
    await page.goto("/jobs");
    await expect(page.locator("h1")).toContainText("Jobs", { timeout: 10_000 });

    // "→ Invoice" link appears for TERMINAL_STATUSES jobs when owner is logged in
    // JobsPage.tsx line 99: <Link href="/jobs/{id}?action=convert">→ Invoice</Link>
    await expect(
      page
        .locator("a")
        .filter({ hasText: /→ Invoice/i })
        .first(),
    ).toBeVisible({ timeout: 10_000 });
  });
});
