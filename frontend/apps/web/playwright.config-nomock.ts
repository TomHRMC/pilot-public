import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  // Wire in the setup and teardown scripts
  globalSetup: require.resolve("./e2e/globalSetup"),
  globalTeardown: require.resolve("./e2e/globalTeardown"),
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "html",
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    // CRITICAL FIX: Turn OFF mock auth and MSW so the frontend hits the real FastAPI backend
    command:
      "NEXT_PUBLIC_USE_MOCK_AUTH=false NEXT_PUBLIC_USE_MSW_MOCKS=false pnpm dev",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
