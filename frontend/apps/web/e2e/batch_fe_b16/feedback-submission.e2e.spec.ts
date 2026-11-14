/**
 * E2E: Feedback submission flow — FE-B16
 *
 * Location: apps/web/e2e/batch_fe_b16/feedback-submission.e2e.spec.ts
 *
 * Scenario: Open feedback form → select "Bug report" → fill text →
 *   submit → confirm.
 *
 * STATUS: Authored — pending live backend (feedback endpoint + email required).
 */

import { test, expect } from "@playwright/test";

test.describe("Feedback form submission", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login");
    await page
      .waitForURL("**/dashboard**", { timeout: 10_000 })
      .catch(() => {});
  });

  test("open feedback form from Help & About page and submit", async ({
    page,
  }) => {
    await page.goto("/settings/help-and-about");

    // Click "Send feedback" link
    await page.getByTestId("help-about-feedback-link").click();
    await page.waitForURL("**/feedback**", { timeout: 5_000 });

    // Select Bug report category
    await page.getByTestId("feedback-category-bug").click();

    // Fill feedback body
    await page
      .getByTestId("feedback-body-input")
      .fill(
        "Test bug: the QuickBooks connect button does not respond when OAuth returns.",
      );

    // Submit
    await page.getByTestId("feedback-submit-btn").click();

    // Success banner appears
    await expect(page.getByTestId("feedback-success-banner")).toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByText(/Thanks for your feedback/i)).toBeVisible();
  });

  test("feedback form validates empty body before submission", async ({
    page,
  }) => {
    await page.goto("/settings/help-and-about/feedback");

    // Submit without filling body
    await page.getByTestId("feedback-submit-btn").click();

    // Success banner should NOT appear
    await expect(page.getByTestId("feedback-success-banner")).not.toBeVisible({
      timeout: 2_000,
    });
  });

  test("feedback escalation from knowledge boundary pre-fills session_id", async ({
    page,
  }) => {
    await page.goto("/dashboard");

    // Open help
    const helpNavBtn = page.getByRole("button", { name: /help/i }).first();
    if (await helpNavBtn.isVisible()) await helpNavBtn.click();
    else {
      await page.goto("/settings/help-and-about");
      await page.getByTestId("help-about-open-chat").click();
    }

    await expect(page.getByTestId("help-drawer")).toBeVisible({
      timeout: 5_000,
    });

    // Ask unknown topic to trigger knowledge boundary
    await page
      .getByTestId("help-composer-input")
      .fill("How do I configure the flux capacitor?");
    await page.getByTestId("help-send-button").click();

    // Wait for knowledge boundary to appear
    await expect(page.getByTestId("knowledge-boundary-message")).toBeVisible({
      timeout: 15_000,
    });

    // Click "Tell us →" CTA
    await page.getByTestId("knowledge-boundary-escalate-cta").click();

    // Feedback modal should open
    await expect(page.getByTestId("feedback-modal")).toBeVisible({
      timeout: 3_000,
    });

    // Session ID hidden input should be populated
    const sessionInput = page.locator(
      '[data-testid="feedback-session-id-input"]',
    );
    await expect(sessionInput).toHaveValue(/.+/, { timeout: 2_000 });
  });
});
