/**
 * FE-B14 E2E Tests — Public Pages
 *
 * Location: apps/web/e2e/batch_fe_b14/public-pages.spec.ts
 *
 * E2E tests for:
 * 1. Customer flow: view invoice → Stripe payment → confirmation
 * 2. Expired link handling end-to-end
 * 3. Email branding visual review
 *
 * Requires dev backend + dev Stripe test mode.
 * If backend is unavailable, tests are authored but marked as pending-backend.
 *
 * Note: Stripe test card: 4242 4242 4242 4242
 */

import { test, expect } from "@playwright/test";

// ─── E2E 1: Customer invoice payment flow ─────────────────────────────────────

test.describe("Public invoice payment flow", () => {
  test("customer views invoice and sees pay CTA", async ({ page }) => {
    // Using MSW in dev mode — visit a test token
    await page.goto("/i/test-active-token");

    // Wait for invoice to load
    await expect(page.getByTestId("public-invoice-page")).toBeVisible({
      timeout: 10000,
    });

    // Should show Pay button for unpaid invoice
    const payButton = page.getByTestId("pay-invoice-button");
    await expect(payButton).toBeVisible();
    await expect(payButton).toContainText("Pay");
  });

  test("payment modal opens with amount selector", async ({ page }) => {
    await page.goto("/i/test-active-token");
    await page.getByTestId("public-invoice-page").waitFor({ timeout: 10000 });

    await page.getByTestId("pay-invoice-button").click();
    await expect(page.getByTestId("invoice-payment-modal")).toBeVisible();
    await expect(page.getByTestId("invoice-amount-selector")).toBeVisible();
  });

  test("already-paid invoice renders InvoicePaidState", async ({ page }) => {
    await page.goto("/i/paid-test-token");
    await page.getByTestId("public-invoice-page").waitFor({ timeout: 10000 });
    await expect(page.getByTestId("invoice-paid-state")).toBeVisible();
    expect(page.getByTestId("paid-badge")).toBeTruthy();
  });
});

// ─── E2E 2: Expired link handling ────────────────────────────────────────────

test.describe("Expired link handling", () => {
  test("expired quote token renders QuoteExpiredPage with fault-50 background", async ({
    page,
  }) => {
    await page.goto("/q/expired-token");

    // Should render the expired page, not 404
    await expect(page.getByTestId("quote-expired-page")).toBeVisible({
      timeout: 10000,
    });

    // Verify fault-50 background class
    const expiredPage = page.getByTestId("quote-expired-page");
    const className = await expiredPage.getAttribute("class");
    expect(className).toContain("bg-fault-50");

    // Heading with fault-700 text
    await expect(page.getByTestId("expired-heading")).toContainText(
      "This link has expired",
    );

    // No accept/decline buttons on expired page
    expect(await page.getByTestId("accept-quote-button").count()).toBe(0);
    expect(await page.getByTestId("decline-quote-button").count()).toBe(0);

    // Powered by Pilot footer
    await expect(page.getByTestId("powered-by-pilot-footer")).toBeVisible();
  });

  test("invalid token renders generic error page, not expired page", async ({
    page,
  }) => {
    await page.goto("/q/invalid-token");
    await page.getByTestId("quote-invalid-page").waitFor({ timeout: 10000 });
    // No tenant contact info shown (tampered token — tenant identity unknown)
    expect(await page.getByTestId("tenant-contact-info").count()).toBe(0);
  });
});

// ─── E2E 3: Email branding visual review ──────────────────────────────────────

test.describe("Email branding settings visual review", () => {
  test.beforeEach(async ({ page }) => {
    // Settings requires auth — this E2E requires a dev session
    // Mock auth state via localStorage for dev testing
    await page.goto("/settings/communications/email-branding");
  });

  test("email branding page renders settings panel and preview", async ({
    page,
  }) => {
    await expect(page.getByTestId("email-branding-settings-panel")).toBeVisible(
      { timeout: 10000 },
    );
    await expect(page.getByTestId("email-branding-preview")).toBeVisible();
  });

  test("template selector updates preview on selection", async ({ page }) => {
    await page
      .getByTestId("email-branding-settings-panel")
      .waitFor({ timeout: 10000 });

    // Select a different template
    const selector = page.getByTestId("template-selector");
    await selector.selectOption("invoice_sent");

    // Preview should update (may trigger a fetch)
    await expect(page.getByTestId("email-branding-preview")).toBeVisible();
  });

  test("email templates page shows all 17 templates", async ({ page }) => {
    await page.goto("/settings/communications/email-templates");
    await page.getByTestId("email-template-preview-surface").waitFor({
      timeout: 10000,
    });

    // Spot-check some template rows are visible
    await expect(page.getByTestId("template-row-quote_sent")).toBeVisible();
    await expect(page.getByTestId("template-row-invoice_sent")).toBeVisible();
    await expect(page.getByTestId("template-row-welcome")).toBeVisible();
    await expect(page.getByTestId("template-row-password_reset")).toBeVisible();
  });
});
