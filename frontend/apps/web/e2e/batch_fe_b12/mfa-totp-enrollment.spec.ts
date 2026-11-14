/**
 * E2E-1 — TOTP Enrollment
 * Location: e2e/web/batch_fe_b12/mfa-totp-enrollment.spec.ts
 *
 * Tests the full TOTP enrollment flow using MSW fixture handlers.
 * MSW accepts any 6-digit code except "000000"/"111111" as valid.
 */

import { test, expect } from "@playwright/test";

test.describe("E2E-1: TOTP Enrollment", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login");
    await page.fill('[data-testid="email-input"]', "mike@thorntonelectric.example.com");
    await page.fill('[data-testid="password-input"]', "TestPassword123!");
    await page.click('[data-testid="login-submit"]');
    await page.waitForURL("**/");
  });

  test("full TOTP enrollment: QR renders, OTP confirms, recovery codes shown, complete", async ({
    page,
  }) => {
    await page.goto("/settings/my-account/security/mfa");
    await expect(page.getByTestId("add-mfa-method-btn")).toBeVisible();

    // Start enrollment
    await page.click('[data-testid="add-mfa-method-btn"]');
    await expect(page.getByTestId("mfa-enrollment-wizard")).toBeVisible();

    // Select TOTP
    await page.click("text=Authenticator app");
    await expect(page.getByTestId("totp-qr-code")).toBeVisible();
    await expect(page.getByTestId("totp-secret")).toBeVisible();

    // Advance to verify
    await page.click('[data-testid="wizard-continue"]');
    await expect(page.getByTestId("mfa-code-input")).toBeVisible();

    // Enter valid 6-digit code (MSW accepts any except 000000/111111)
    await page.fill('[data-testid="mfa-code-input"]', "123456");
    await page.click('[data-testid="wizard-verify"]');

    // Recovery codes appear (10 codes)
    await expect(page.getByTestId("recovery-codes-container")).toBeVisible();
    const codes = await page
      .locator('[data-testid="recovery-codes-container"] code')
      .all();
    expect(codes).toHaveLength(10);

    // Must acknowledge before continuing
    const continueBtn = page.getByTestId("wizard-complete-recovery");
    await expect(continueBtn).toBeDisabled();

    await page.click('[data-testid="recovery-codes-checkbox"]');
    await expect(continueBtn).not.toBeDisabled();

    await continueBtn.click();

    // Wizard closes
    await expect(page.getByTestId("mfa-wizard-container")).not.toBeVisible();
  });

  test("wrong code (000000) shows inline error", async ({ page }) => {
    await page.goto("/settings/my-account/security/mfa");
    await page.click('[data-testid="add-mfa-method-btn"]');
    await page.click("text=Authenticator app");
    await expect(page.getByTestId("totp-qr-code")).toBeVisible();
    await page.click('[data-testid="wizard-continue"]');
    await page.fill('[data-testid="mfa-code-input"]', "000000");
    await page.click('[data-testid="wizard-verify"]');
    await expect(page.getByTestId("mfa-code-error")).toBeVisible();
    await expect(page.getByTestId("mfa-code-error")).toContainText(
      /doesn't match/i,
    );
  });
});
