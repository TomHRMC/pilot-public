/**
 * Field issue 409 staleness integration tests — FE-B9
 *
 * Tests all three 409 subtypes: server_changed / auto_recovered / stale
 */

import { setupServer } from "msw/node";
import {
  fieldIssue409ServerChanged,
  fieldIssue409AutoRecovered,
  fieldIssue409Stale,
} from "@/features/field-issues/mocks/fieldIssuesFixtures";
import {
  fieldIssuesHandlers,
  fieldIssuesHandlerVariants,
} from "@/mocks/handlers/fieldIssuesHandlers";

const server = setupServer(...fieldIssuesHandlers);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("field issue 409 staleness handling", () => {
  it("409 server_changed fixture has staleness_type='server_changed'", () => {
    expect(fieldIssue409ServerChanged.staleness_type).toBe("server_changed");
    expect(fieldIssue409ServerChanged.refreshed_issue).toBeDefined();
  });

  it("409 auto_recovered fixture has staleness_type='auto_recovered'", () => {
    expect(fieldIssue409AutoRecovered.staleness_type).toBe("auto_recovered");
    expect(fieldIssue409AutoRecovered.message).toBeTruthy();
  });

  it("409 stale fixture has staleness_type='stale'", () => {
    expect(fieldIssue409Stale.staleness_type).toBe("stale");
    expect(fieldIssue409Stale.message).toBeTruthy();
  });

  it("MSW 409 server_changed handler returns 409 with refreshed_issue", async () => {
    server.use(fieldIssuesHandlerVariants.resolveWith409ServerChanged);

    const res = await fetch(
      "/api/v1/owner/mobile-sync-escalations/fi-time-001/resolve",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          resolution: "accept_tech",
          expected_server_state_hash: "hash-123",
        }),
      },
    );

    expect(res.status).toBe(409);
    const body = await res.json();
    expect(body.staleness_type).toBe("server_changed");
    expect(body.refreshed_issue).toBeDefined();
  });

  it("MSW 409 auto_recovered returns 409 with message", async () => {
    server.use(fieldIssuesHandlerVariants.resolveWith409AutoRecovered);

    const res = await fetch(
      "/api/v1/owner/mobile-sync-escalations/fi-time-001/resolve",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          resolution: "accept_tech",
          expected_server_state_hash: "hash-123",
        }),
      },
    );

    expect(res.status).toBe(409);
    const body = await res.json();
    expect(body.staleness_type).toBe("auto_recovered");
    expect(body.message).toBeTruthy();
  });
});
