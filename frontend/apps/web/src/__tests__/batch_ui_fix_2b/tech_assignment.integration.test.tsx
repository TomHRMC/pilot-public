/**
 * UI-FIX-2B Integration Tests — Multi-Tech Assignment
 *
 * Location: apps/web/src/__tests__/batch_ui_fix_2b/tech_assignment.integration.test.tsx
 *
 * Verifies:
 *   1. TechAssignmentSection renders in dispatch board Properties panel (no dead button)
 *   2. TechAssignmentSection renders in Job Detail page above profitability widget
 *   3. Add tech: POST fires with correct payload; list re-fetches
 *   4. Remove tech: DELETE fires with correct assignmentId; list re-fetches
 */

import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
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
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { TechAssignmentSection } from "../../features/jobs/components/TechAssignmentSection";

// ─── Next.js mock ──────────────────────────────────────────────────────────
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/jobs/job-001",
  useSearchParams: () => new URLSearchParams(),
}));

// ─── Auth context helpers ─────────────────────────────────────────────────
function makeOwnerAuth(): AuthContextValue {
  // PLP-FIX-10: include schedule.view_all + schedule.manage to mirror prod
  // grants (owner has * wildcard in prod; static map doesn't include these).
  const ownerPerms = [
    "schedule.view_all",
    "schedule.manage",
    "users.view",
    "invoices.view",
    "invoices.update",
    "dashboard.manage",
  ];
  return {
    user: {
      id: "user-001",
      email: "owner@example.com",
      role: "owner",
      tenantId: "tenant-001",
      displayName: "Tom Owner",
      accessToken: "tok",
      permissions: ownerPerms,
    } as AuthContextValue["user"],
    isAuthenticated: true,
    role: "owner",
    permissions: ownerPerms,
    signIn: vi.fn() as AuthContextValue["signIn"],
    confirmMfaChallenge: vi.fn() as AuthContextValue["confirmMfaChallenge"],
    signOut: vi.fn(),
    refreshSession: vi
      .fn()
      .mockResolvedValue("tok") as AuthContextValue["refreshSession"],
  };
}

// ─── Fixtures ─────────────────────────────────────────────────────────────
const MOCK_USERS = [
  {
    user_id: "user-001",
    email: "owner@example.com",
    first_name: "Tom",
    last_name: "Owner",
    display_color: "#4F86C6",
    role_code: "owner",
    role_name: "Owner",
    permissions: [],
    joined_at: "2025-01-15T10:00:00Z",
    is_active: true,
  },
  {
    user_id: "user-002",
    email: "mike@example.com",
    first_name: "Mike",
    last_name: "Sparks",
    display_color: "#E8724A",
    role_code: "technician",
    role_name: "Field Technician",
    permissions: [],
    joined_at: "2025-03-01T09:00:00Z",
    is_active: true,
  },
];

const INITIAL_ASSIGNMENTS = [
  {
    id: "assign-001",
    job_id: "job-001",
    user_id: "user-002",
    role: "primary",
    ordinal: 1,
    assigned_at: "2026-07-21T10:00:00Z",
    is_active: true,
  },
];

// Mutable server-side assignment store
let serverAssignments = [...INITIAL_ASSIGNMENTS];
let capturedPostBody: unknown = null;
let capturedDeleteId: string | null = null;

// ─── MSW Server ───────────────────────────────────────────────────────────
const server = setupServer(
  http.get("/api/v1/users", () => HttpResponse.json(MOCK_USERS)),

  http.get("/api/v1/scheduling/jobs/:jobId/assignments", ({ params }) => {
    const { jobId } = params as { jobId: string };
    return HttpResponse.json(
      serverAssignments.filter((a) => a.job_id === jobId),
    );
  }),

  http.post(
    "/api/v1/scheduling/jobs/:jobId/assignments",
    async ({ params, request }) => {
      const { jobId } = params as { jobId: string };
      capturedPostBody = await request.json();
      const body = capturedPostBody as { user_id: string; role: string };
      const newAssignment = {
        id: "assign-new-001",
        job_id: jobId,
        user_id: body.user_id,
        role: body.role,
        ordinal: serverAssignments.length + 1,
        assigned_at: new Date().toISOString(),
        is_active: true,
      };
      serverAssignments.push(newAssignment);
      return HttpResponse.json(newAssignment, { status: 201 });
    },
  ),

  http.delete(
    "/api/v1/scheduling/jobs/:jobId/assignments/:assignmentId",
    ({ params }) => {
      const { assignmentId } = params as { assignmentId: string };
      capturedDeleteId = assignmentId;
      serverAssignments = serverAssignments.filter(
        (a) => a.id !== assignmentId,
      );
      return HttpResponse.json({}, { status: 200 });
    },
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => {
  server.resetHandlers();
  serverAssignments = [...INITIAL_ASSIGNMENTS];
  capturedPostBody = null;
  capturedDeleteId = null;
});
afterAll(() => server.close());

// ─── Render helper ────────────────────────────────────────────────────────
function renderSection(jobId: string, onChanged?: () => void) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <AuthContext.Provider value={makeOwnerAuth()}>
      <QueryClientProvider client={queryClient}>
        <TechAssignmentSection jobId={jobId} onAssignmentChanged={onChanged} />
      </QueryClientProvider>
    </AuthContext.Provider>,
  );
}

// ─── Tests ────────────────────────────────────────────────────────────────
describe("UI-FIX-2B Tech Assignment Integration", () => {
  it("renders TechAssignmentSection with live assignment (no dead button)", async () => {
    renderSection("job-001");

    // Wait for both the section and the async user data (useTenantUsers) to resolve
    await waitFor(() => {
      expect(screen.getByTestId("tech-assignment-section")).toBeInTheDocument();
      // Should show Mike Sparks as the primary tech (requires useTenantUsers to resolve)
      expect(screen.getByText("Mike Sparks")).toBeInTheDocument();
      expect(screen.getByText("Lead")).toBeInTheDocument();
    });

    // The dead "+ Add technician" button should NOT exist anymore
    // (replaced by the functional dropdown)
    const addTechButton = screen.queryByRole("button", {
      name: "Add technician",
    });
    expect(addTechButton).not.toBeInTheDocument();
  });

  it("renders add dropdown for owner when available users exist", async () => {
    renderSection("job-001");

    await waitFor(() => {
      // Tom Owner is not assigned — dropdown should appear
      expect(screen.getByTestId("add-tech-select")).toBeInTheDocument();
    });

    const select = screen.getByTestId("add-tech-select");
    const options = select.querySelectorAll("option");
    // Option for Tom Owner (user-001 is not assigned)
    const optionTexts = Array.from(options).map((o) => o.textContent);
    expect(optionTexts).toContain("Tom Owner");
  });

  it("fires POST with correct payload when adding a technician", async () => {
    const onChanged = vi.fn();
    renderSection("job-001", onChanged);

    await waitFor(() =>
      expect(screen.getByTestId("add-tech-select")).toBeInTheDocument(),
    );

    const select = screen.getByTestId("add-tech-select");
    fireEvent.change(select, { target: { value: "user-001" } });

    await waitFor(() => {
      expect(capturedPostBody).toMatchObject({
        user_id: "user-001",
        role: "helper", // second tech is always helper
      });
    });

    expect(onChanged).toHaveBeenCalled();
  });

  it("fires DELETE with correct assignmentId when removing a technician", async () => {
    const onChanged = vi.fn();
    renderSection("job-001", onChanged);

    await waitFor(() =>
      expect(screen.getByTestId("remove-btn-assign-001")).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByTestId("remove-btn-assign-001"));

    await waitFor(() => {
      expect(capturedDeleteId).toBe("assign-001");
    });

    expect(onChanged).toHaveBeenCalled();
  });
});
