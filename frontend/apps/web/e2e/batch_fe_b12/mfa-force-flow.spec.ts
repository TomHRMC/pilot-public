/**
 * E2E-2 — MFA Force-Flow on Tenant Policy Activation
 * Location: e2e/web/batch_fe_b12/mfa-force-flow.spec.ts
 */

import { test, expect } from "@playwright/test";

test.describe("E2E-2: MFA Force-Flow", () => {
  test("force-flow enrollment: Cancel button absent, grace period banner shown", async ({
    page,
  }) => {
    // Navigate to force-flow route with grace_days param (as FE-B2 interceptor would set)
    await page.goto(
      "/settings/my-account/security/mfa/enroll?mfa_required=1&grace_days=2",
    );

    // Wizard renders in force-flow mode
    await expect(page.getByTestId("mfa-force-flow-wizard")).toBeVisible();

    // Cancel button must NOT be present
    await expect(
      page.getByRole("button", { name: /cancel/i }),
    ).not.toBeVisible();

    // Grace period banner should show (2 days → alert/amber)
    const banner = page.getByRole("alert");
    await expect(banner).toBeVisible();
    await expect(banner).toContainText("2 days");
  });

  test("force-flow: completing enrollment redirects to intended page", async ({
    page,
  }) => {
    await page.goto(
      "/settings/my-account/security/mfa/enroll?mfa_required=1&grace_days=3&return_to=/",
    );
    await expect(page.getByTestId("mfa-force-flow-wizard")).toBeVisible();

    // Select TOTP and complete enrollment
    await page.click("text=Authenticator app");
    await page.waitForSelector('[data-testid="totp-qr-code"]');
    await page.click('[data-testid="wizard-continue"]');
    await page.fill('[data-testid="mfa-code-input"]', "123456");
    await page.click('[data-testid="wizard-verify"]');

    // Recovery codes
    await page.waitForSelector('[data-testid="recovery-codes-container"]');
    await page.click('[data-testid="recovery-codes-checkbox"]');
    await page.click('[data-testid="wizard-complete-recovery"]');

    // Should redirect to return_to param
    await page.waitForURL("/");
  });
});
