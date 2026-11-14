/**
 * Field issue SSE invalidation integration test — FE-B9
 */

import { setupServer } from "msw/node";
import { fieldIssuesHandlers } from "@/mocks/handlers/fieldIssuesHandlers";

const server = setupServer(...fieldIssuesHandlers);
beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("Field issues SSE endpoint", () => {
  it("MSW SSE handler responds with event-stream content-type", async () => {
    const res = await fetch("/api/v1/owner/mobile-sync-escalations/stream");
    expect(res.headers.get("Content-Type")).toContain("text/event-stream");
  });

  it("field-issues MSW handlers include stream handler", () => {
    expect(fieldIssuesHandlers.length).toBeGreaterThan(0);
    // Handlers include SSE stream handler
    const paths = fieldIssuesHandlers.map((h) => {
      const info = h.info as { path?: string };
      return info?.path ?? "";
    });
    expect(paths.some((p) => p.includes("stream"))).toBe(true);
  });
});
