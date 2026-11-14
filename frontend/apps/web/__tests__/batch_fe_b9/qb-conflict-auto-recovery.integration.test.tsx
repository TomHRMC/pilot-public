/**
 * QB conflict auto-recovery integration test — FE-B9
 */

import { qbConflictHandlerVariants } from "@/mocks/handlers/qbConflictHandlers";
import { setupServer } from "msw/node";

const server = setupServer();
beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("QB conflict auto-recovery", () => {
  it("409 auto-recovery handler returns 409 with auto_recovered type", async () => {
    server.use(qbConflictHandlerVariants.resolveWith409AutoRecovery);

    const res = await fetch(
      "/api/v1/integrations/quickbooks/conflicts/qb-cust-001/resolve",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          resolution: "accept_local",
          expected_pilot_modified_at: "2026-05-25T10:00:00Z",
          expected_external_modified_at: "2026-05-25T09:45:00Z",
        }),
      },
    );

    expect(res.status).toBe(409);
    const body = await res.json();
    expect(body.staleness_type).toBe("auto_recovered");
    expect(body.message).toContain("resolved itself");
  });

  it("success handler returns 200 on resolve", async () => {
    const { qbConflictHandlers } =
      await import("@/mocks/handlers/qbConflictHandlers");
    server.use(...qbConflictHandlers);

    const res = await fetch(
      "/api/v1/integrations/quickbooks/conflicts/qb-cust-001/resolve",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          resolution: "accept_local",
          expected_pilot_modified_at: "2026-05-25T10:00:00Z",
          expected_external_modified_at: "2026-05-25T09:45:00Z",
        }),
      },
    );

    expect(res.status).toBe(200);
  });
});
