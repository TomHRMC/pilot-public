import { request, FullConfig } from "@playwright/test";

export default async function globalTeardown(config: FullConfig) {
  const baseURL = config.projects[0].use.baseURL || "http://localhost:8000";
  const apiContext = await request.newContext({ baseURL });

  console.log("🧹 [E2E Teardown] Cleaning up test data...");

  // 1. Fetch all test customers created during the run
  const customersRes = await apiContext.get("/api/v1/customers/test");
  if (customersRes.ok()) {
    const customers = await customersRes.json();
    for (const customer of customers) {
      // 2. Soft-delete them using the test endpoint
      await apiContext.delete(`/api/v1/customers/${customer.id}/test`);
    }
    console.log(
      `✅ [E2E Teardown] Soft-deleted ${customers.length} test customers.`,
    );
  }

  // Note: For a truly pristine DB, the most robust SDLC approach for local testing
  // is actually to have a script that drops and recreates the PostgreSQL schema
  // using Alembic rather than relying solely on API deletes, but this prevents
  // immediate test-data overflow.

  console.log("🛑 [E2E Teardown] Complete.");
}
