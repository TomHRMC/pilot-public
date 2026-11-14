/**
 * Playwright config — E2E Tier 2 (SD-10)
 *
 * Location: apps/web/playwright.config.ts
 *
 * Runs 5 critical-path Playwright browser tests against the live E2E backend
 * (pilot_e2e_db on port 5433, FastAPI on port 8001, Next.js on port 3000).
 *
 * NEXT_PUBLIC_USE_MOCK_AUTH must be "false" for all Playwright runs —
 * real auth flow is exercised via global-setup.ts storageState.
 *
 * These tests are NOT run on every PR. They run in the nightly E2E workflow
 * (.github/workflows/e2e-nightly.yml) after the Tier 1 pytest suite passes.
 *
 * Design decisions from batch-sd-design-sprint-design.md §SD-10 Part B:
 * - storageState saves authenticated session (avoids re-login per test)
 * - pilot_e2e_db seeded once before suite (no per-test resets)
 * - Max retries: 2 on CI, 0 locally
 * - Flaky policy: max 2 failures in 5 runs → quarantine + P2 bug
 */

import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  // SD-10: All Playwright E2E specs live in src/__tests__/e2e/
  testDir: "./src/__tests__/e2e",
  testMatch: "**/*.playwright.ts",

  // Do not run in parallel — E2E DB is shared state
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,

  reporter: [["list"], ["html", { open: "never" }]],

  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    // Pre-authenticated session — populated by global-setup.ts
    storageState: "playwright-auth.json",
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],

  // Global setup authenticates as dev@pilot.local and saves storageState
  globalSetup: "./src/__tests__/e2e/global-setup.ts",

  // 30s per test action, 60s total test timeout
  timeout: 60_000,
  expect: {
    timeout: 10_000,
  },
});
