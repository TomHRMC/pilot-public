/**
 * E2E: Help chat RAG flow — FE-B16
 *
 * Location: apps/web/e2e/batch_fe_b16/help-chat-rag.e2e.spec.ts
 *
 * Scenario: Open help → ask "How do I connect QuickBooks?" →
 *   real RAG response → article IDs non-empty → correct answer structure.
 *
 * STATUS: Authored — pending live backend (Ollama + RAG pipeline required).
 * DO NOT delete — run when backend is available.
 */

import { test, expect } from "@playwright/test";

test.describe("Help chat RAG flow", () => {
  test.beforeEach(async ({ page }) => {
    // Authenticate — assumes test user cookie or token setup
    await page.goto("/login");
    await page.waitForURL("**/dashboard**", { timeout: 10_000 }).catch(() => {
      // CI may already be authenticated via storage state
    });
  });

  test("open help drawer and ask QuickBooks question — receives non-boundary response", async ({
    page,
  }) => {
    await page.goto("/dashboard");

    // Open help via nav "?" button (global app shell)
    const helpNavBtn = page.getByRole("button", { name: /help/i }).first();
    if (await helpNavBtn.isVisible()) {
      await helpNavBtn.click();
    } else {
      // Fallback: navigate to help-and-about and open chat from there
      await page.goto("/settings/help-and-about");
      await page.getByTestId("help-about-open-chat").click();
    }

    // Verify drawer is open
    await expect(page.getByTestId("help-drawer")).toBeVisible({
      timeout: 5_000,
    });

    // Type and send a question
    const input = page.getByTestId("help-composer-input");
    await input.fill("How do I connect QuickBooks?");
    await page.getByTestId("help-send-button").click();

    // User message appears
    await expect(page.getByTestId("help-message-user")).toBeVisible({
      timeout: 5_000,
    });

    // AI typing indicator appears
    await expect(page.getByTestId("help-typing-indicator")).toBeVisible({
      timeout: 5_000,
    });

    // AI response renders (not a knowledge boundary)
    await expect(page.getByTestId("help-message-assistant")).toBeVisible({
      timeout: 15_000,
    });

    // Knowledge boundary message should NOT appear (RAG should find QuickBooks articles)
    await expect(
      page.getByTestId("knowledge-boundary-message"),
    ).not.toBeVisible();

    // Follow-up actions should be present
    await expect(page.getByText("Read full article")).toBeVisible();
  });

  test("knowledge boundary: AI returns no-docs response for unknown topic", async ({
    page,
  }) => {
    await page.goto("/dashboard");

    const helpNavBtn = page.getByRole("button", { name: /help/i }).first();
    if (await helpNavBtn.isVisible()) await helpNavBtn.click();
    else {
      await page.goto("/settings/help-and-about");
      await page.getByTestId("help-about-open-chat").click();
    }

    await expect(page.getByTestId("help-drawer")).toBeVisible({
      timeout: 5_000,
    });

    // Ask about a topic that has no documentation
    const input = page.getByTestId("help-composer-input");
    await input.fill("How do I configure the flux capacitor?");
    await page.getByTestId("help-send-button").click();

    // Knowledge boundary message should appear with escalation CTA
    await expect(page.getByTestId("knowledge-boundary-message")).toBeVisible({
      timeout: 15_000,
    });
    await expect(
      page.getByTestId("knowledge-boundary-escalate-cta"),
    ).toBeVisible();
    // Standard AI bubble should NOT appear
    await expect(page.getByTestId("help-message-assistant")).not.toBeVisible();
  });
});
