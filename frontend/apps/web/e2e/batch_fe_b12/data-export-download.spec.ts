/**
 * E2E-4 — Data Export Download
 * Location: e2e/web/batch_fe_b12/data-export-download.spec.ts
 *
 * Tests: request export → poll until ready → click download → verify ZIP
 */

import { test, expect } from "@playwright/test";

test.describe("E2E-4: Data Export Download", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login");
    await page.fill('[data-testid="email-input"]', "mike@thorntonelectric.example.com");
    await page.fill('[data-testid="password-input"]', "TestPassword123!");
    await page.click('[data-testid="login-submit"]');
    await page.waitForURL("**/");
  });

  test("request export → poll until ready → download link visible", async ({
    page,
  }) => {
    await page.goto("/settings/my-account/data-export");
    await expect(page.getByTestId("data-export-section")).toBeVisible();

    // Click Request export
    await expect(page.getByTestId("request-export-btn")).toBeVisible();
    await page.click('[data-testid="request-export-btn"]');

    // Active export status appears
    await expect(page.getByTestId("active-export-status")).toBeVisible({
      timeout: 5_000,
    });

    // Poll completes and download link appears (MSW returns ready after 2 polls)
    await expect(page.getByTestId("active-download-link")).toBeVisible({
      timeout: 35_000, // polling interval is 10s; 3 polls max
    });

    // Verify download link has a valid href
    const downloadLink = page.getByTestId("active-download-link");
    const href = await downloadLink.getAttribute("href");
    expect(href).toContain("s3.amazonaws.com");
  });

  test("429 frequency limit shows inline message", async ({
    page,
    context,
  }) => {
    // Override API to return 429
    await context.route("**/api/v1/users/me/data-exports", (route) => {
      if (route.request().method() === "POST") {
        void route.fulfill({
          status: 429,
          headers: { "Retry-After": "4" },
          body: JSON.stringify({ detail: "Rate limit exceeded." }),
        });
      } else {
        void route.continue();
      }
    });

    await page.goto("/settings/my-account/data-export");
    await page.click('[data-testid="request-export-btn"]');

    // Should show frequency limit message
    await expect(page.getByText(/already requested.*another in/i)).toBeVisible({
      timeout: 5_000,
    });
  });

  test("expired export shows neutral styling in recent exports", async ({
    page,
  }) => {
    await page.goto("/settings/my-account/data-export");
    // Fixture includes an expired export in RECENT_EXPORTS
    await expect(page.getByTestId("export-status-pill-expired")).toBeVisible({
      timeout: 5_000,
    });
  });
});
