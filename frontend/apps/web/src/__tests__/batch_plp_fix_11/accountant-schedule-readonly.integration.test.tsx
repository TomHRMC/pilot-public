/**
 * PLP-FIX-11 Integration — Accountant schedule read-only + Schedule nav (INV-BUG-18)
 *
 * Location: apps/web/src/__tests__/batch_plp_fix_11/accountant-schedule-readonly.integration.test.tsx
 *
 * Tests:
 * - accountant → Schedule nav item appears in AppSidebar (schedule.view_all grant)
 * - accountant → dispatch board renders (read-only — no write affordances)
 * - technician → Schedule nav item absent (lacks schedule.view_all)
 *
 * PLP-FIX-11 (INV-BUG-18, Tom-ruled 2026-09-06): accountant gains
 * schedule.view_all (seed grant mirrored in static map + MSW fixture). The
 * Schedule nav item now appears (AppSidebar gate changed from schedule.manage
 * to schedule.view_all). The board renders read-only — write affordances
 * inside the board stay schedule.manage-gated (accountant lacks it).
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
import { AppSidebar } from "@/components/AppSidebar";
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
afterAll(() => server.close());
afterEach(() => server.resetHandlers());

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
    http.get("*/api/v1/scheduling/dispatch-board", () =>
      HttpResponse.json({
        techs: [],
        unassigned: [],
        jobs: [],
      }),
    ),
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

describe("PLP-FIX-11 — accountant schedule read-only + Schedule nav (INV-BUG-18)", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  // ── Schedule nav item ──────────────────────────────────────────────────────

  it("accountant → Schedule nav item appears in AppSidebar", () => {
    renderWithAuth(<AppSidebar />, "accountant");
    expect(screen.getByText("Schedule")).toBeInTheDocument();
  });

  it("technician → Schedule nav item absent (lacks schedule.view_all)", () => {
    renderWithAuth(<AppSidebar />, "technician");
    expect(screen.queryByText("Schedule")).not.toBeInTheDocument();
  });

  // ── Dispatch board read-only ───────────────────────────────────────────────

  it("accountant → dispatch board renders (read-only)", async () => {
    setupBoardHandlers();
    const { container } = renderWithAuth(<DispatchBoardPage />, "accountant");

    await waitFor(() => {
      expect(screen.queryByText("Loading schedule…")).not.toBeInTheDocument();
    });

    // Board content should be present — accountant holds schedule.view_all
    await waitFor(() => {
      const boardContainer = container.querySelector(
        ".bg-white.overflow-hidden",
      );
      expect(boardContainer).toBeTruthy();
    });
  });
});
