/**
 * Revert-to-default E2E spec — FE-B11
 *
 * calendar_conflict_auto_expire_days set to 45 →
 * revert → confirm backend returns scope=system →
 * UI shows "Default · 30 days"
 *
 * Note: Requires running dev server with BE-B9 settings endpoints.
 * Test runner: Playwright
 */

import { test, expect } from "@playwright/test";

test.describe("Revert-to-default against dev backend", () => {
  test("set calendar auto-expire to 45 → revert → UI shows Default · 30 days", async ({
    page,
  }) => {
    // Navigate to calendar settings (integrations general)
    await page.goto("/settings/integrations/general");
    await page.waitForLoadState("networkidle");

    const autoExpireInput = page.getByTestId(
      "setting-input-calendar_conflict_auto_expire_days",
    );
    await expect(autoExpireInput).toBeVisible();

    // Set to 45
    await autoExpireInput.fill("45");
    await autoExpireInput.blur();

    // Wait for save
    await expect(
      page.getByTestId("setting-saved-calendar_conflict_auto_expire_days"),
    ).toBeVisible({ timeout: 5000 });

    // Should now show State 2 (tenant override)
    await expect(page.getByText("tenant override")).toBeVisible({
      timeout: 3000,
    });

    // Click revert
    await page
      .getByTestId("setting-revert-link-calendar_conflict_auto_expire_days")
      .click();

    // Confirm in dialog
    await expect(
      page.getByTestId(
        "setting-revert-dialog-calendar_conflict_auto_expire_days",
      ),
    ).toBeVisible();
    await page
      .getByTestId(
        "setting-revert-dialog-calendar_conflict_auto_expire_days-confirm",
      )
      .click();

    // UI returns to State 1 with "Default · 30 days"
    const annotation = page.getByTestId(
      "setting-default-calendar_conflict_auto_expire_days",
    );
    await expect(annotation).toBeVisible({ timeout: 5000 });
    await expect(annotation).toContainText("Default · 30");

    // No tenant override pill
    await expect(page.locator("text=tenant override")).toHaveCount(0);
  });
});
