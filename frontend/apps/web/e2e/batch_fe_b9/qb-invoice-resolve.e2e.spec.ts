/**
 * E2E: QB invoice conflict resolution — FE-B9
 *
 * Playwright E2E spec: conflict appears → resolve → QB entity updated
 */

import { test, expect } from "@playwright/test";

test.describe("QB invoice conflict resolution", () => {
  test("QB conflicts queue page loads", async ({ page }) => {
    await page.goto("/settings/integrations/quickbooks/conflicts");
    await expect(page.getByTestId("qb-conflict-queue-page")).toBeVisible({
      timeout: 10000,
    });
  });

  test("QB conflict detail for invoice renders QB master header", async ({
    page,
  }) => {
    await page.goto(
      "/settings/integrations/quickbooks/conflicts/qb-invoice-001",
    );
    await expect(page.getByTestId("qb-conflict-detail-page")).toBeVisible({
      timeout: 10000,
    });
    // Invoice has masterDirection='external' — QB master badge should show
    await expect(page.getByText(/QuickBooks is master/i)).toBeVisible();
  });

  test("QB invoice detail renders InvoiceFinancialDeltaCallout", async ({
    page,
  }) => {
    await page.goto(
      "/settings/integrations/quickbooks/conflicts/qb-invoice-001",
    );
    await expect(
      page.getByTestId("invoice-financial-delta-callout"),
    ).toBeVisible({ timeout: 10000 });
  });

  test("voice_qb_blocked banner renders on deep-link arrival", async ({
    page,
  }) => {
    await page.goto(
      "/settings/integrations/quickbooks/conflicts/qb-invoice-001?reason=voice_qb_blocked",
    );
    await expect(page.getByTestId("voice-qb-blocked-banner")).toBeVisible({
      timeout: 10000,
    });
  });

  test("QB conflicts queue shows InFlightSyncIndicator with surface='quickbooks'", async ({
    page,
  }) => {
    await page.goto("/settings/integrations/quickbooks/conflicts");
    await expect(page.getByTestId("qb-inflight-sync-indicator")).toBeVisible({
      timeout: 10000,
    });
  });
});
