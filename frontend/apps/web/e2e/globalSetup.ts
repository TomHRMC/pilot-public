import { request, FullConfig } from "@playwright/test";

export default async function globalSetup(config: FullConfig) {
  const baseURL = config.projects[0].use.baseURL || "http://localhost:8000";
  const apiContext = await request.newContext({ baseURL });

  console.log("🚀 [E2E Setup] Verifying backend health...");
  const healthCheck = await apiContext.get("/api/v1/health/celery");
  if (!healthCheck.ok()) {
    throw new Error(
      "❌ Backend is not running or healthy. Cannot run E2E tests.",
    );
  }

  console.log("🏗️ [E2E Setup] Priming Test Tenant...");
  // Ensure the baseline test tenant and user exist using the test signup endpoint
  // If it already exists, your backend should cleanly reject or we can ignore the 422
  const response = await apiContext.post(
    "/api/v1/auth/signup/test?email=e2e-test-owner@example.com",
    {
      data: {
        tenant_name: "E2E Automated Testing Inc",
        first_name: "E2E",
        last_name: "Owner",
      },
    },
  );

  if (response.ok()) {
    console.log("✅ [E2E Setup] Test tenant primed successfully.");
  } else if (response.status() === 422 || response.status() === 409) {
    console.log("⚠️ [E2E Setup] Test tenant already exists. Proceeding.");
  } else {
    throw new Error(`❌ Failed to prime test tenant: ${response.status()}`);
  }
}
