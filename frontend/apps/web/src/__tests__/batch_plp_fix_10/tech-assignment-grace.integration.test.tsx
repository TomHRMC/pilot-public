/**
 * PLP-FIX-10 Integration — Tech assignment 403 grace (INV-BUG-10a)
 *
 * Location: apps/web/src/__tests__/batch_plp_fix_10/tech-assignment-grace.integration.test.tsx
 *
 * Tests:
 * - accountant (schedule.view_all — PLP-FIX-11 grant) → section renders read-only rows, no picker
 * - office_staff (schedule.view_all + schedule.manage) → assignments + picker render
 * - assignments GET → 403 → section renders null, no ErrorState
 * - assignments GET → 500 → ErrorState renders
 *
 * PLP-FIX-11 (INV-BUG-18, Tom-ruled 2026-09-06): accountant now holds
 * schedule.view_all (seed grant mirrored in static map + MSW fixture). The
 * accountant case is FLIPPED from "section null" to "section renders
 * read-only" — assignments + users queries 200; picker/remove stay
 * schedule.manage-gated (accountant lacks it).
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

describe("PLP-FIX-10 — tech assignment 403 grace (INV-BUG-10a)", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("accountant (schedule.view_all — PLP-FIX-11 grant) → section renders read-only rows, no picker", async () => {
    server.use(
      http.get("*/api/v1/scheduling/jobs/:jobId/assignments", () =>
        HttpResponse.json([{ id: "a1", user_id: "u-tech-1", role: "primary" }]),
      ),
      // PLP-FIX-11: accountant's *.view wildcard covers users.view (suffix
      // matcher; BE gate roles.py:292-294) → users query 200s post-grant.
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
    );

    renderWithAuth(<TechAssignmentSection jobId="job-1" />, "accountant");

    // PLP-FIX-11: section SHOULD render (accountant now holds schedule.view_all)
    await waitFor(() => {
      expect(screen.getByTestId("tech-assignment-section")).toBeInTheDocument();
    });

    // Assignment row should be present (read-only)
    expect(screen.getByTestId("tech-row-a1")).toBeInTheDocument();

    // PLP-FIX-11: accountant lacks schedule.manage → no picker, no remove button
    expect(screen.queryByTestId("add-tech-select")).not.toBeInTheDocument();
    expect(screen.queryByTestId("remove-btn-a1")).not.toBeInTheDocument();

    // No ErrorState
    expect(screen.queryByText(/Failed to load/i)).not.toBeInTheDocument();
  });

  it("office_staff (schedule.view_all + schedule.manage) → assignments + picker render", async () => {
    server.use(
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
          {
            user_id: "u-tech-2",
            display_name: "Maria Santos",
            is_active: true,
            display_color: "#10B981",
          },
        ]),
      ),
    );

    renderWithAuth(<TechAssignmentSection jobId="job-1" />, "office_staff");

    // Section should render
    await waitFor(() => {
      expect(screen.getByTestId("tech-assignment-section")).toBeInTheDocument();
    });

    // Picker should be present (office_staff has schedule.manage)
    expect(screen.getByTestId("add-tech-select")).toBeInTheDocument();
  });

  it("assignments GET → 403 → section renders null, no ErrorState", async () => {
    server.use(
      http.get("*/api/v1/scheduling/jobs/:jobId/assignments", () =>
        HttpResponse.json({ error: "Forbidden" }, { status: 403 }),
      ),
      http.get("*/api/v1/users", () => HttpResponse.json([])),
    );

    // Use office_staff so the section gate passes, but the assignments query 403s
    renderWithAuth(<TechAssignmentSection jobId="job-1" />, "office_staff");

    // Section should NOT render (403 → null defense-in-depth)
    await waitFor(() => {
      expect(
        screen.queryByTestId("tech-assignment-section"),
      ).not.toBeInTheDocument();
    });

    // No ErrorState
    expect(screen.queryByText(/Failed to load/i)).not.toBeInTheDocument();
  });

  it("assignments GET → 500 → ErrorState renders", async () => {
    server.use(
      http.get("*/api/v1/scheduling/jobs/:jobId/assignments", () =>
        HttpResponse.json({ error: "Server error" }, { status: 500 }),
      ),
      http.get("*/api/v1/users", () => HttpResponse.json([])),
    );

    renderWithAuth(<TechAssignmentSection jobId="job-1" />, "office_staff");

    // ErrorState should render for non-403 failures
    await waitFor(() => {
      expect(screen.getByText(/Failed to load/i)).toBeInTheDocument();
    });
  });
});
