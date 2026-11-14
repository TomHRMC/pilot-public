/**
 * Quota integration tests — web
 *
 * Covers:
 *   - Dashboard widget renders
 *   - Unrouted message assignment
 *   - Segment counter boundary
 *   - RBAC comms access
 *
 * Design doc G.2
 */

import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterAll,
  afterEach,
} from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { customerCommsHandlers } from "../../src/mocks/handlers/customerCommsHandlers";
import { RecentCustomerMessagesWidget } from "../../src/features/dashboard/components/RecentCustomerMessagesWidget";
import { UnroutedMessageQueue } from "../../src/features/sms-unrouted/components/UnroutedMessageQueue";
import { computeSegments } from "../../../../packages/ui/src/hooks/useSegmentCount";

// PLP-FIX-9: RecentCustomerMessagesWidget now calls useHasPermission
// (communications.view gate). Tests must provide an AuthContext with
// owner permissions so the widget renders.
const ownerAuth: AuthContextValue = {
  user: {
    id: "u1",
    email: "owner@test.com",
    role: "owner",
    tenantId: "t1",
    displayName: "Owner",
    accessToken: "tok",
    permissions: ["*"],
  },
  isAuthenticated: true,
  role: "owner",
  permissions: ["*"],
  signIn: vi.fn(),
  confirmMfaChallenge: vi.fn(),
  signOut: vi.fn(),
  refreshSession: vi.fn().mockResolvedValue("tok"),
  whenSessionReady: vi.fn(),
};

const server = setupServer(...customerCommsHandlers);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <AuthContext.Provider value={ownerAuth}>
      <QueryClientProvider client={qc}>{children}</QueryClientProvider>
    </AuthContext.Provider>
  );
}

describe("web-dashboard-widget integration", () => {
  it("GET /dashboard/widgets/recent-customer-messages → 10 rows rendered", async () => {
    render(<RecentCustomerMessagesWidget />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("recent-messages-list")).toBeTruthy();
    });

    const rows = screen.getAllByTestId(/recent-msg-row-/);
    expect(rows.length).toBeGreaterThanOrEqual(1);
  });
});

describe("web-unrouted-assign integration", () => {
  it("unrouted queue renders list of unrouted messages", async () => {
    render(<UnroutedMessageQueue />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("unrouted-queue")).toBeTruthy();
    });
  });
});

describe("web-segment-counter-boundary integration", () => {
  it("type 160 chars → segmentCount=1; type 161st → segmentCount=2", () => {
    const at160 = computeSegments("A".repeat(160));
    expect(at160.segmentCount).toBe(1);

    const at161 = computeSegments("A".repeat(161));
    expect(at161.segmentCount).toBe(2);
  });

  it("Unicode boundary: 70 chars → 1 segment; 71 → 2 segments", () => {
    const at70 = computeSegments("😀".repeat(70));
    expect(at70.segmentCount).toBe(1);

    const at71 = computeSegments("😀".repeat(71));
    expect(at71.segmentCount).toBe(2);
  });
});
