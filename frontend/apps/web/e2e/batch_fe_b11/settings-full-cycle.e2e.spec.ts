/**
 * Settings full cycle E2E spec — FE-B11
 *
 * Full Tier 2 #4 modification cycle:
 * load Settings > Operations > Profitability rules →
 * edit etc_variance_note_required_pct from 10 to 15 →
 * verify UI shows scope=tenant →
 * revert → verify UI returns to scope=system with value 10
 *
 * Note: This E2E requires a running dev server and MSW in browser.
 * Test runner: Playwright
 */

import { test, expect } from "@playwright/test";

test.describe("Settings full modification cycle", () => {
  test("edit ETC variance → verify tenant scope → revert → verify system scope", async ({
    page,
  }) => {
    // Navigate to profitability rules
    await page.goto("/settings/operations/profitability-rules");
    await page.waitForLoadState("networkidle");

    // Verify initial State 1 (scope=system)
    const etcInput = page.getByTestId(
      "setting-input-etc_variance_note_required_pct",
    );
    await expect(etcInput).toBeVisible();

    const defaultAnnotation = page.getByTestId(
      "setting-default-etc_variance_note_required_pct",
    );
    await expect(defaultAnnotation).toBeVisible();
    await expect(defaultAnnotation).toContainText("Default · 10");

    // Edit the value
    await etcInput.fill("15");
    await etcInput.blur();

    // Wait for save indicator
    await expect(
      page.getByTestId("setting-saved-etc_variance_note_required_pct"),
    ).toBeVisible({ timeout: 5000 });

    // After save, should transition to State 2 (tenant override)
    await expect(page.getByText("tenant override")).toBeVisible({
      timeout: 3000,
    });

    // Click "Revert to default"
    const revertLink = page.getByTestId(
      "setting-revert-link-etc_variance_note_required_pct",
    );
    await expect(revertLink).toBeVisible();
    await revertLink.click();

    // Inline dialog should appear
    const revertDialog = page.getByTestId(
      "setting-revert-dialog-etc_variance_note_required_pct",
    );
    await expect(revertDialog).toBeVisible();

    // Confirm revert
    await page
      .getByTestId(
        "setting-revert-dialog-etc_variance_note_required_pct-confirm",
      )
      .click();

    // Should return to State 1 with value 10
    await expect(
      page.getByTestId("setting-default-etc_variance_note_required_pct"),
    ).toBeVisible({ timeout: 5000 });
    await expect(
      page.getByTestId("setting-default-etc_variance_note_required_pct"),
    ).toContainText("Default · 10");
  });
});
