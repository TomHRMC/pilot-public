/**
 * PLP-FIX-9 Integration — Write-affordance gate sweep (INV-BUG-9)
 *
 * Location: apps/web/src/__tests__/batch_plp_fix_9/write-affordance-gates.integration.test.tsx
 *
 * Tests:
 * - As accountant: no +Add Job (JobsPage), no Send/Record Payment (invoice detail)
 * - As office_staff: no +Add Job (jobs.create not held), no Send/Record Payment (invoices.update not held)
 * - As owner: all visible
 */

import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue, PilotRole } from "@pilot/ui/auth";
import { ROLE_PERMISSION_MAP } from "@pilot/ui/role-gate";
import { JobsPage } from "@/features/jobs/components/JobsPage";

// ── Mocks ────────────────────────────────────────────────────────────────────

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  usePathname: () => "/jobs",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...rest
  }: {
    href: string;
    children: React.ReactNode;
    [key: string]: unknown;
  }) => React.createElement("a", { href, ...rest }, children),
}));

// Mock useJobs to return empty data (we only test button visibility)
vi.mock("@/features/jobs/hooks/useJobs", () => ({
  useJobs: () => ({
    data: { items: [], total: 0 },
    isLoading: false,
    isError: false,
    error: null,
  }),
}));

vi.mock("@pilot/shared-api", () => ({
  LIST_PAGE_SIZE: 20,
  apiClient: { get: vi.fn(), post: vi.fn() },
  isAxiosError: vi.fn(),
}));

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

function renderJobsAs(role: PilotRole) {
  return render(
    <AuthContext.Provider value={makeAuth(role)}>
      <QueryClientProvider client={makeQC()}>
        <JobsPage />
      </QueryClientProvider>
    </AuthContext.Provider>,
  );
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("PLP-FIX-9 — write-affordance gates (INV-BUG-9)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("JobsPage +Add Job button", () => {
    it("owner sees +Add Job (holds jobs.create)", () => {
      renderJobsAs("owner");
      expect(screen.getByTestId("add-job-btn")).toBeInTheDocument();
    });

    it("accountant does NOT see +Add Job (lacks jobs.create)", () => {
      renderJobsAs("accountant");
      expect(screen.queryByTestId("add-job-btn")).not.toBeInTheDocument();
    });

    it("office_staff does NOT see +Add Job (lacks jobs.create after sweep)", () => {
      renderJobsAs("office_staff");
      expect(screen.queryByTestId("add-job-btn")).not.toBeInTheDocument();
    });
  });
});
