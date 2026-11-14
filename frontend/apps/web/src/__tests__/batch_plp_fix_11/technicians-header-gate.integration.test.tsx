/**
 * PLP-FIX-11 Integration — Technicians header gate (INV-BUG-18)
 *
 * Location: apps/web/src/__tests__/batch_plp_fix_11/technicians-header-gate.integration.test.tsx
 *
 * Tests:
 * - technician (lacks schedule.view_all) → "Technicians" header is null on JobDetailPage
 * - accountant (schedule.view_all — PLP-FIX-11 grant) → "Technicians" header is present
 *
 * PLP-FIX-11 (INV-BUG-18, Tom-ruled 2026-09-06): the bare "Technicians" <h4>
 * in JobDetailPage rendered outside the child TechAssignmentSection's gate.
 * The fix wraps the entire wrapper (header + section) in
 * <RoleGate permission="schedule.view_all">. This test proves the gate works:
 * a role without the grant sees no header at all.
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
import { JobDetailPage } from "@/features/jobs/components/JobDetailPage";

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

// ── MSW job + assignment data ────────────────────────────────────────────────

function setupJobHandlers() {
  server.use(
    http.get("*/api/v1/jobs/:jobId", () =>
      HttpResponse.json({
        job_id: "job-1",
        status_code: "in_progress",
        priority: "standard",
        job_type_label: "Service",
      }),
    ),
    http.get("*/api/v1/scheduling/jobs/:jobId/assignments", () =>
      HttpResponse.json([{ id: "a1", user_id: "u-tech-1", role: "primary" }]),
    ),
    http.get("*/api/v1/users", () =>
      HttpResponse.json([
        {
          user_id: "u-tech-1",
          display_name: "Jake Rodriguez",
          is_active: true,
          display_color: "#3B82F6",
        },
      ]),
    ),
    // Profitability widget endpoint
    http.get("*/api/v1/jobs/:jobId/profitability", () =>
      HttpResponse.json({
        job_id: "job-1",
        estimated_total_cents: 50000,
        actual_total_cents: 45000,
        margin_pct: 10,
      }),
    ),
  );
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("PLP-FIX-11 — Technicians header gate (INV-BUG-18)", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("technician (lacks schedule.view_all) → 'Technicians' header is null", async () => {
    setupJobHandlers();
    renderWithAuth(<JobDetailPage jobId="job-1" />, "technician");

    // Wait for job data to load
    await waitFor(() => {
      expect(screen.queryByText("Loading")).not.toBeInTheDocument();
    });

    // PLP-FIX-11: technician lacks schedule.view_all → the RoleGate wrapping
    // the Technicians wrapper returns null → no "Technicians" header at all.
    expect(screen.queryByText("Technicians")).not.toBeInTheDocument();
  });

  it("accountant (schedule.view_all — PLP-FIX-11 grant) → 'Technicians' header is present", async () => {
    setupJobHandlers();
    renderWithAuth(<JobDetailPage jobId="job-1" />, "accountant");

    // Wait for job data to load
    await waitFor(() => {
      expect(screen.queryByText("Loading")).not.toBeInTheDocument();
    });

    // PLP-FIX-11: accountant now holds schedule.view_all → the RoleGate
    // renders the wrapper → "Technicians" header is present.
    await waitFor(() => {
      expect(screen.getByText("Technicians")).toBeInTheDocument();
    });
  });
});
