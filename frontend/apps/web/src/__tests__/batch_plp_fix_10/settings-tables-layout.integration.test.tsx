/**
 * PLP-FIX-10 Integration — Settings tables layout (INV-BUG-15)
 *
 * Location: apps/web/src/__tests__/batch_plp_fix_10/settings-tables-layout.integration.test.tsx
 *
 * Tests:
 * - TeamSettingsPage table: table-fixed absent; overflow-x-auto wrapper with
 *   tabIndex={0} + role="region"; actions cell whitespace-nowrap
 * - PendingInvitesSection table: table-fixed absent; overflow-x-auto wrapper;
 *   long-email fixture row → Revoke button rendered and visible
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
} from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue, PilotRole } from "@pilot/ui/auth";
import { ROLE_PERMISSION_MAP } from "@pilot/ui/role-gate";
import { TeamSettingsPage } from "@/features/settings/components/TeamSettingsPage";
import { PendingInvitesSection } from "@/features/settings/components/PendingInvitesSection";

// ── Mocks ────────────────────────────────────────────────────────────────────

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/settings/team",
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

describe("PLP-FIX-10 — settings tables layout (INV-BUG-15)", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  describe("TeamSettingsPage members table", () => {
    it("table-fixed absent; overflow-x-auto wrapper with tabIndex + role=region; nowrap cells", async () => {
      server.use(
        // useTeamUsers hits GET /api/v1/users (not /users/team) and expects
        // TeamUserRaw[] shape (snake_case with user_id, role_code, etc.)
        http.get("*/api/v1/users", () =>
          HttpResponse.json([
            {
              user_id: "u1",
              email: "tom@example-domain.org",
              role_code: "owner",
              role_name: "Owner",
              permissions: ["*"],
              joined_at: "2026-01-15T00:00:00Z",
              is_active: true,
            },
          ]),
        ),
        http.get("*/api/v1/users/invites", () => HttpResponse.json([])),
      );

      const { container } = renderWithAuth(<TeamSettingsPage />, "owner");

      // Wait for the table to render
      await waitFor(() => {
        expect(screen.getByText("Team")).toBeInTheDocument();
      });

      const table = container.querySelector("table");
      expect(table).toBeTruthy();

      // table-fixed class should NOT be present
      expect(table?.className).not.toContain("table-fixed");

      // overflow-x-auto wrapper with tabIndex + role=region should exist
      const scrollRegion = container.querySelector('[role="region"]');
      expect(scrollRegion).toBeTruthy();
      expect(scrollRegion?.getAttribute("tabIndex")).toBe("0");
      expect(scrollRegion?.className).toContain("overflow-x-auto");

      // Email cell should have whitespace-nowrap
      const emailCell = screen.getByText("tom@example-domain.org");
      expect(emailCell.className).toContain("whitespace-nowrap");
    });
  });

  describe("PendingInvitesSection table", () => {
    it("table-fixed absent; overflow-x-auto wrapper; long-email row → Revoke visible", async () => {
      const longEmail =
        "very.long.email.address.that.should.not.be.truncated@example-domain.org";
      const futureExpiry = new Date(
        Date.now() + 7 * 24 * 60 * 60 * 1000,
      ).toISOString();

      server.use(
        http.get("*/api/v1/users/invites", () =>
          HttpResponse.json([
            {
              id: "invite-long-email",
              email: longEmail,
              role_code: "technician",
              invited_by: "u1",
              created_at: new Date().toISOString(),
              expires_at: futureExpiry,
              accepted_at: null,
              is_active: true,
              status: "pending",
            },
          ]),
        ),
      );

      const { container } = renderWithAuth(<PendingInvitesSection />, "owner");

      // Wait for the invite row to render
      await waitFor(() => {
        expect(
          screen.getByTestId("invite-row-invite-long-email"),
        ).toBeInTheDocument();
      });

      const table = container.querySelector("table");
      expect(table).toBeTruthy();

      // table-fixed class should NOT be present
      expect(table?.className).not.toContain("table-fixed");

      // overflow-x-auto wrapper with tabIndex + role=region
      const scrollRegion = container.querySelector('[role="region"]');
      expect(scrollRegion).toBeTruthy();
      expect(scrollRegion?.getAttribute("tabIndex")).toBe("0");
      expect(scrollRegion?.className).toContain("overflow-x-auto");

      // Revoke button should be rendered and visible
      expect(
        screen.getByTestId("revoke-invite-long-email"),
      ).toBeInTheDocument();

      // The long email should be in the DOM (full value, not truncated away)
      expect(screen.getByText(longEmail)).toBeInTheDocument();
    });
  });
});
