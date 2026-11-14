/**
 * PLP-FIX-10 Integration — Dispatch board gate (INV-BUG-13)
 *
 * Location: apps/web/src/__tests__/batch_plp_fix_10/board-gate.integration.test.tsx
 *
 * Tests:
 * - office_staff (schedule.view_all) → board content renders (toolbar, lanes)
 * - accountant (schedule.view_all — PLP-FIX-11 grant) → board content renders (read-only)
 * - owner (wildcard *) → board renders
 *
 * PLP-FIX-11 (INV-BUG-18, Tom-ruled 2026-09-06): accountant now holds
 * schedule.view_all (seed grant mirrored in static map + MSW fixture). The
 * accountant case is FLIPPED from "board hidden" to "board renders" —
 * write affordances inside the board stay schedule.manage-gated.
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
import { DispatchBoardPage } from "@/features/dispatch-board/components/DispatchBoardPage";

// ── Mocks ────────────────────────────────────────────────────────────────────

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/schedule",
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
  // PLP-FIX-11 (INV-BUG-18): schedule.view_all is now in the static
  // ROLE_PERMISSION_MAP for owner, office_staff, AND accountant (mirrors
  // the Part A seed grant). The manual push below is retained as a
  // defensive fallback for office_staff/owner in case the static map
  // is edited in a future batch. Accountant gets it from the static map.
  if (
    (role === "office_staff" || role === "owner") &&
    !perms.includes("schedule.view_all") &&
    !perms.includes("*")
  ) {
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

// ── MSW board data ───────────────────────────────────────────────────────────

function setupBoardHandlers() {
  server.use(
    http.get("*/api/v1/subscription-tiers/", () =>
      HttpResponse.json({
        tiers: [
          {
            tier_id: "tier-starter",
            tier_name: "starter",
            display_label: "Starter",
            monthly_price_cents: 4900,
            is_trial: false,
            trial_duration_days: null,
            max_users: 5,
            max_sms_segments_per_month: 100,
            display_order: 1,
            is_active: true,
            schedule_lanes: 5,
          },
        ],
      }),
    ),
    // The board endpoint is /api/v1/scheduling/dispatch-board (not /scheduling/board)
    http.get("*/api/v1/scheduling/dispatch-board", () =>
      HttpResponse.json({
        techs: [],
        unassigned: [],
        jobs: [],
      }),
    ),
    // The board hook fetches /api/v1/jobs/ in parallel for metadata enrichment
    http.get("*/api/v1/jobs/", () =>
      HttpResponse.json({
        items: [],
        total: 0,
        limit: 200,
        offset: 0,
      }),
    ),
    http.get("*/api/v1/users", () => HttpResponse.json([])),
  );
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("PLP-FIX-10 — dispatch board gate (INV-BUG-13)", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("office_staff (schedule.view_all) → board renders", async () => {
    setupBoardHandlers();
    renderWithAuth(<DispatchBoardPage />, "office_staff");

    // Wait for loading to resolve and board content to appear.
    // The DndContext tree renders inside RoleGate — the DispatchToolbar
    // is the first child. We check for the board's main container.
    await waitFor(() => {
      expect(screen.queryByText("Loading schedule…")).not.toBeInTheDocument();
    });

    // Board content should be present — the DndContext tree renders
    // (not null from RoleGate). The board's main container div has
    // bg-white overflow-hidden class.
    await waitFor(() => {
      const boardContainer = document.querySelector(
        ".bg-white.overflow-hidden",
      );
      expect(boardContainer).toBeTruthy();
    });
  });

  it("accountant (schedule.view_all — PLP-FIX-11 grant) → board renders (read-only)", async () => {
    setupBoardHandlers();
    const { container } = renderWithAuth(<DispatchBoardPage />, "accountant");

    // Wait for loading to resolve
    await waitFor(() => {
      expect(screen.queryByText("Loading schedule…")).not.toBeInTheDocument();
    });

    // PLP-FIX-11: accountant now holds schedule.view_all (seed grant mirrored
    // in static map + MSW fixture). The board renders — write affordances
    // inside the board stay schedule.manage-gated (accountant lacks it).
    await waitFor(() => {
      const boardContainer = container.querySelector(
        ".bg-white.overflow-hidden",
      );
      expect(boardContainer).toBeTruthy();
    });
  });

  it("owner (wildcard *) → board renders", async () => {
    setupBoardHandlers();
    renderWithAuth(<DispatchBoardPage />, "owner");

    await waitFor(() => {
      expect(screen.queryByText("Loading schedule…")).not.toBeInTheDocument();
    });

    // Board content should be present — owner has * in prod (MSW fixture)
    // but the static ROLE_PERMISSION_MAP doesn't include it. The makeAuth
    // helper adds schedule.view_all for owner to mirror prod grant truth.
    await waitFor(() => {
      const boardContainer = document.querySelector(
        ".bg-white.overflow-hidden",
      );
      expect(boardContainer).toBeTruthy();
    });
  });
});
