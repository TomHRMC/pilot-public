/**
 * E2E-3 — Password Change Cross-Device Verification
 * Location: e2e/web/batch_fe_b12/password-change-cross-device.spec.ts
 *
 * Verifies FE-B2 session-expired interceptor fires on next API request in
 * another context after password change. Does NOT build a new mechanism.
 */

import { test, expect } from "@playwright/test";

test.describe("E2E-3: Password Change Cross-Device 401 Handling", () => {
  test("changing password causes other tabs' next request to receive 401 and redirect to login", async ({
    browser,
  }) => {
    // Open two browser contexts (simulating two devices/tabs)
    const contextA = await browser.newContext();
    const contextB = await browser.newContext();

    const pageA = await contextA.newPage();
    const pageB = await contextB.newPage();

    try {
      // Both sign in
      await pageA.goto("/login");
      await pageA.fill(
        '[data-testid="email-input"]',
        "mike@thorntonelectric.example.com",
      );
      await pageA.fill('[data-testid="password-input"]', "TestPassword123!");
      await pageA.click('[data-testid="login-submit"]');
      await pageA.waitForURL("**/");

      await pageB.goto("/login");
      await pageB.fill(
        '[data-testid="email-input"]',
        "mike@thorntonelectric.example.com",
      );
      await pageB.fill('[data-testid="password-input"]', "TestPassword123!");
      await pageB.click('[data-testid="login-submit"]');
      await pageB.waitForURL("**/");

      // Change password in Page A
      await pageA.goto("/settings/my-account/password");
      await pageA.fill(
        '[data-testid="current-password-input"]',
        "TestPassword123!",
      );
      await pageA.fill('[data-testid="new-password-input"]', "NewPassword456!");
      await pageA.fill(
        '[data-testid="confirm-password-input"]',
        "NewPassword456!",
      );
      await pageA.click('[data-testid="change-password-submit"]');

      // Page A: success banner appears; still logged in
      await expect(pageA.getByTestId("password-change-success")).toBeVisible();

      // Page B: next API request should receive 401 → FE-B2 interceptor redirects to login
      // Navigate to trigger an API call in Page B
      await pageB.goto("/settings/my-account/profile");

      // FE-B2 session-expired interceptor should redirect to login
      // (or show the re-login modal, depending on FE-B2 implementation)
      await expect(
        pageB
          .getByTestId("email-input")
          .or(pageB.getByText(/session expired/i))
          .or(pageB.getByText(/sign in again/i)),
      ).toBeVisible({ timeout: 10_000 });
    } finally {
      await contextA.close();
      await contextB.close();
    }
  });
});
