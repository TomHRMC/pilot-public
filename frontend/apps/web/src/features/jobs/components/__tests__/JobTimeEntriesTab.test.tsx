/**
 * JobTimeEntriesTab unit tests — FE-B21
 *
 * Location: apps/web/src/features/jobs/components/__tests__/JobTimeEntriesTab.test.tsx
 *
 * Tests:
 * - Renders empty state when no entries
 * - Renders time entries list with hours + cost
 * - "+ Add Time Entry" button visible for owner; absent for tech (RoleGate)
 */

import { render, screen } from "@testing-library/react";
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { JobTimeEntriesTab } from "../JobTimeEntriesTab";

// ── Mock hooks ─────────────────────────────────────────────────────────────────

vi.mock("../../hooks/useJobTimeEntries", () => ({
  useJobTimeEntries: vi.fn(),
  JOB_TIME_ENTRIES_QUERY_KEY: (id: string) => ["job-time-entries", id],
}));

vi.mock("../../hooks/useAddTimeEntry", () => ({
  useAddTimeEntry: vi.fn(),
}));

import { useJobTimeEntries } from "../../hooks/useJobTimeEntries";
import { useAddTimeEntry } from "../../hooks/useAddTimeEntry";

// ── Helpers ────────────────────────────────────────────────────────────────────

function makeContext(
  role: "owner" | "office_staff" | "technician" | "accountant",
): AuthContextValue {
  return {
    user: {
      id: "u1",
      email: "a@b.com",
      role,
      tenantId: "t1",
      displayName: "Test",
      accessToken: "tok",
    },
    isAuthenticated: true,
    role,
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("tok"),
  };
}

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

function Wrapper({
  role,
  children,
}: {
  role: "owner" | "office_staff" | "technician" | "accountant";
  children: React.ReactNode;
}) {
  return (
    <AuthContext.Provider value={makeContext(role)}>
      <QueryClientProvider client={makeQueryClient()}>
        {children}
      </QueryClientProvider>
    </AuthContext.Provider>
  );
}

const MOCK_TIME_ENTRIES = [
  {
    id: "te-1",
    job_id: "job-1",
    user_id: "user-tech-1",
    started_at: "2026-06-16T09:00:00Z",
    ended_at: "2026-06-16T13:00:00Z",
    hours: 4,
    notes: "Panel work",
    hourly_rate_cents: 9000,
    total_cost_cents: 36000,
    hours_remaining_estimate: 2,
    hours_remaining_was_overridden: false,
    override_note: null,
    quote_line_id: null,
    etc_captured_at: "2026-06-16T13:00:00Z",
  },
];

// ── Tests ──────────────────────────────────────────────────────────────────────

describe("JobTimeEntriesTab", () => {
  beforeEach(() => {
    vi.mocked(useJobTimeEntries).mockReset();
    vi.mocked(useAddTimeEntry).mockReset();
    vi.mocked(useAddTimeEntry).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as never);
  });

  it("renders empty state when no entries", () => {
    vi.mocked(useJobTimeEntries).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as never);

    render(<JobTimeEntriesTab jobId="job-1" />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });

    expect(screen.getByText(/no time entries yet/i)).toBeTruthy();
  });

  it("renders time entries list with hours and cost", () => {
    vi.mocked(useJobTimeEntries).mockReturnValue({
      data: MOCK_TIME_ENTRIES,
      isLoading: false,
      isError: false,
    } as never);

    render(<JobTimeEntriesTab jobId="job-1" />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });

    // Hours shown
    expect(screen.getByText("4h")).toBeTruthy();
    // Total cost shown ($360.00 = 36000 cents)
    expect(screen.getByText("$360.00")).toBeTruthy();
    // Notes shown
    expect(screen.getByText("Panel work")).toBeTruthy();
  });

  it("shows '+ Add Time Entry' button for owner", () => {
    vi.mocked(useJobTimeEntries).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as never);

    render(<JobTimeEntriesTab jobId="job-1" />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });

    expect(screen.getByTestId("add-time-entry-btn")).toBeTruthy();
  });

  it("'+ Add Time Entry' button is hidden for tech (RoleGate)", () => {
    vi.mocked(useJobTimeEntries).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as never);

    render(<JobTimeEntriesTab jobId="job-1" />, {
      wrapper: ({ children }) => (
        <Wrapper role="technician">{children}</Wrapper>
      ),
    });

    expect(screen.queryByTestId("add-time-entry-btn")).toBeNull();
  });

  it("shows '+ Add Time Entry' button for office_staff", () => {
    vi.mocked(useJobTimeEntries).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as never);

    render(<JobTimeEntriesTab jobId="job-1" />, {
      wrapper: ({ children }) => (
        <Wrapper role="office_staff">{children}</Wrapper>
      ),
    });

    expect(screen.getByTestId("add-time-entry-btn")).toBeTruthy();
  });
});
