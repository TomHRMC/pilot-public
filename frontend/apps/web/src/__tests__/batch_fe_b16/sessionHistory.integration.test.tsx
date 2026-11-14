/**
 * Session history integration tests — FE-B16
 *
 * Location: apps/web/src/__tests__/batch_fe_b16/sessionHistory.integration.test.tsx
 */

import { describe, it, expect, beforeAll, afterEach, afterAll } from "vitest";
import { setupServer } from "msw/node";
import {
  helpSessionsListHandler,
  helpSessionDetailHandler,
} from "../../mocks/handlers/helpHandlers";
import { groupSessionsByRecency } from "../../features/help/hooks/useHelpSessions";
import {
  MOCK_SESSION_TODAY,
  MOCK_SESSION_LAST_7_DAYS,
  MOCK_SESSION_OLDER,
} from "../../mocks/fixtures/helpFixtures";

const server = setupServer(helpSessionsListHandler, helpSessionDetailHandler);
beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("Session history grouping", () => {
  it("groups sessions into Today / Last 7 days / Older", () => {
    const sessions = [
      MOCK_SESSION_TODAY,
      MOCK_SESSION_LAST_7_DAYS,
      MOCK_SESSION_OLDER,
    ];
    const groups = groupSessionsByRecency(sessions);
    const labels = groups.map((g) => g.label);
    expect(labels).toContain("Today");
    expect(labels).toContain("Last 7 days");
    expect(labels).toContain("Older");
  });

  it("today session is in Today group", () => {
    const groups = groupSessionsByRecency([MOCK_SESSION_TODAY]);
    expect(groups[0].label).toBe("Today");
    expect(groups[0].sessions[0].session_id).toBe("session-today-001");
  });

  it("older session is in Older group", () => {
    const groups = groupSessionsByRecency([MOCK_SESSION_OLDER]);
    expect(groups[0].label).toBe("Older");
  });
});
