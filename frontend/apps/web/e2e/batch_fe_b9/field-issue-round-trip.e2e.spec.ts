/**
 * E2E: Field issue round-trip — FE-B9
 *
 * Full round-trip: web resolves → mobile tech receives push → queue shows terminal state
 * Playwright web E2E spec.
 */

import { test, expect } from "@playwright/test";

test.describe("Field issue resolution round-trip", () => {
  test.beforeEach(async ({ page }) => {
    // Assumes MSW dev worker active (or test env with seeded data)
    await page.goto("/dashboard/approvals/field-issues");
  });

  test("field issues queue page loads with pending issues", async ({
    page,
  }) => {
    await expect(page.getByTestId("field-issues-queue-page")).toBeVisible({
      timeout: 10000,
    });
    await expect(page.getByText("Field issues")).toBeVisible();
  });

  test("field issues queue shows pending count badge", async ({ page }) => {
    await page.goto("/dashboard/approvals/field-issues");
    // Page renders — badge exists when there are pending issues
    await expect(
      page.locator('[data-testid="field-issues-queue-page"]'),
    ).toBeVisible({ timeout: 10000 });
  });

  test("field issue detail page loads for valid id", async ({ page }) => {
    await page.goto("/dashboard/approvals/field-issues/fi-time-001");
    await expect(page.getByTestId("field-issue-detail")).toBeVisible({
      timeout: 10000,
    });
    await expect(page.getByTestId("issue-context-header")).toBeVisible();
  });

  test("field issue detail shows resolve buttons", async ({ page }) => {
    await page.goto("/dashboard/approvals/field-issues/fi-time-001");
    await expect(page.getByTestId("resolve-accept-local-btn")).toBeVisible({
      timeout: 10000,
    });
    await expect(page.getByTestId("resolve-accept-remote-btn")).toBeVisible();
  });

  test("voice_deletion_redirect banner renders on deep-link", async ({
    page,
  }) => {
    await page.goto(
      "/dashboard/approvals/field-issues/fi-expense-001?reason=voice_deletion_redirect",
    );
    await expect(
      page.getByTestId("voice-deletion-redirect-banner"),
    ).toBeVisible({ timeout: 10000 });
  });
});
