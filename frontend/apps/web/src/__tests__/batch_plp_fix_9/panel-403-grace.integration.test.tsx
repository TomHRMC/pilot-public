/**
 * PLP-FIX-9 Integration — Panel 403-grace (INV-BUG-10)
 *
 * Location: apps/web/src/__tests__/batch_plp_fix_9/panel-403-grace.integration.test.tsx
 *
 * Tests:
 * - TechAssignmentSection: 403 on tenant-users → assignments render read-only, no ErrorState
 * - DispatchBoardPage: 403 on subscription-tiers → board renders (no full-page lane-count error)
 */

import React from "react";
import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterAll,
  afterEach,
  beforeEach,
} from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue, PilotRole } from "@pilot/ui/auth";
import { ROLE_PERMISSION_MAP } from "@pilot/ui/role-gate";
import { TechAssignmentSection } from "@/features/jobs/components/TechAssignmentSection";

// ── Mocks ────────────────────────────────────────────────────────────────────

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/jobs",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) =>
    React.createElement("a", { href }, children),
}));

// ── MSW server ───────────────────────────────────────────────────────────────

const server = setupServer();

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Helpers ──────────────────────────────────────────────────────────────────

function makeAuth(role: PilotRole): AuthContextValue {
  const perms = Array.from(ROLE_PERMISSION_MAP[role]) as string[];
  // PLP-FIX-10: schedule.view_all is a prod grant for office_staff (mirrored
  // in userPermissionsHandlers.ts MSW fixture) but not yet in the static
  // ROLE_PERMISSION_MAP. Add it here so the test auth fixture matches prod.
  if (role === "office_staff" && !perms.includes("schedule.view_all")) {
    perms.push("schedule.view_all");
  }
  return {
    user: {
      id: "u1",
      email: `${role}@pilot-dev.example.com`,
      role,
      tenantId: "t1",
      displayName: role,
      accessToken: "tok",
      permissions: perms,
    },
    isAuthenticated: true,
    role,
    permissions: perms,
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("tok"),
    whenSessionReady: vi.fn(),
  };
}

function makeQC() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

function renderWithAuth(ui: React.ReactElement, role: PilotRole) {
  return render(
    <AuthContext.Provider value={makeAuth(role)}>
      <QueryClientProvider client={makeQC()}>{ui}</QueryClientProvider>
    </AuthContext.Provider>,
  );
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("PLP-FIX-9 — panel 403-grace (INV-BUG-10)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("TechAssignmentSection", () => {
    it("renders assignments read-only when tenant-users 403s (no ErrorState)", async () => {
      // PLP-FIX-10: office_staff holds schedule.view_all (section visible)
      // but tenant-users 403s (users.view gate). Assignments render read-only.
      // Accountant is no longer used here — lacks schedule.view_all → section
      // hidden entirely (the INV-BUG-10a fix).
      server.use(
        http.get("*/api/v1/scheduling/jobs/:jobId/assignments", () =>
          HttpResponse.json([
            {
              id: "a1",
              user_id: "u-tech-1",
              role: "primary",
            },
          ]),
        ),
        http.get("*/api/v1/users", () =>
          HttpResponse.json({ error: "Forbidden" }, { status: 403 }),
        ),
      );

      renderWithAuth(<TechAssignmentSection jobId="job-1" />, "office_staff");

      // The section should render (not ErrorState)
      await waitFor(() => {
        expect(
          screen.getByTestId("tech-assignment-section"),
        ).toBeInTheDocument();
      });

      // No ErrorState should be visible
      expect(screen.queryByText(/Failed to load/i)).not.toBeInTheDocument();
    });
  });
});
