/**
 * TechAssignmentSection unit tests — UI-FIX-2B
 *
 * Location: apps/web/src/features/jobs/components/__tests__/TechAssignmentSection.test.tsx
 */

import { render, screen } from "@testing-library/react";
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { TechAssignmentSection } from "../TechAssignmentSection";
import type { TenantUserItem } from "../../../users/hooks/useTenantUsers";
import type { JobAssignment } from "../../hooks/useJobAssignments";

// Mock the hooks so we can control data without HTTP
vi.mock("../../hooks/useJobAssignments", () => ({
  useJobAssignments: vi.fn(),
  jobAssignmentsQueryKey: (jobId: string) => ["job-assignments", jobId],
}));
vi.mock("../../hooks/useAddJobAssignment", () => ({
  useAddJobAssignment: vi.fn(),
}));
vi.mock("../../hooks/useRemoveJobAssignment", () => ({
  useRemoveJobAssignment: vi.fn(),
}));
vi.mock("../../../users/hooks/useTenantUsers", () => ({
  useTenantUsers: vi.fn(),
  TENANT_USERS_QUERY_KEY: ["tenant-users"],
}));

import { useJobAssignments } from "../../hooks/useJobAssignments";
import { useAddJobAssignment } from "../../hooks/useAddJobAssignment";
import { useRemoveJobAssignment } from "../../hooks/useRemoveJobAssignment";
import { useTenantUsers } from "../../../users/hooks/useTenantUsers";

type MockReturnValue<T> = {
  data: T;
  isLoading: boolean;
  isError: boolean;
  refetch?: () => void;
};

type MockMutationReturnValue = {
  mutateAsync: ReturnType<typeof vi.fn>;
  isPending: boolean;
};

const MOCK_USERS: TenantUserItem[] = [
  {
    user_id: "user-001",
    email: "owner@example.com",
    first_name: "Tom",
    last_name: "Owner",
    display_color: "#4F86C6",
    role_code: "owner",
    role_name: "Owner",
    is_active: true,
    display_name: "Tom Owner",
  },
  {
    user_id: "user-002",
    email: "mike@example.com",
    first_name: "Mike",
    last_name: "Sparks",
    display_color: "#E8724A",
    role_code: "technician",
    role_name: "Field Technician",
    is_active: true,
    display_name: "Mike Sparks",
  },
];

const PRIMARY_ASSIGNMENT: JobAssignment = {
  id: "assign-001",
  job_id: "job-001",
  user_id: "user-002",
  role: "primary",
  ordinal: 1,
  assigned_at: "2026-07-21T10:00:00Z",
  is_active: true,
};

function makeAuthContext(role: "owner" | "technician"): AuthContextValue {
  // PLP-FIX-10: include schedule.view_all + schedule.manage to mirror prod
  // grants (owner has * wildcard in prod; static map doesn't include these).
  const ownerPerms = ["schedule.view_all", "schedule.manage", "users.view"];
  const techPerms: string[] = [];
  const perms = role === "owner" ? ownerPerms : techPerms;
  return {
    user: {
      id: role === "owner" ? "user-001" : "user-002",
      email: role === "owner" ? "owner@example.com" : "mike@example.com",
      role,
      tenantId: "tenant-001",
      displayName: role === "owner" ? "Tom Owner" : "Mike Sparks",
      accessToken: "tok",
      permissions: perms,
    } as AuthContextValue["user"],
    isAuthenticated: true,
    role,
    permissions: perms,
    signIn: vi.fn() as AuthContextValue["signIn"],
    confirmMfaChallenge: vi.fn() as AuthContextValue["confirmMfaChallenge"],
    signOut: vi.fn(),
    refreshSession: vi.fn() as AuthContextValue["refreshSession"],
  };
}

function renderWithProviders(
  ui: React.ReactElement,
  role: "owner" | "technician",
) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <AuthContext.Provider value={makeAuthContext(role)}>
      <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
    </AuthContext.Provider>,
  );
}

function makeMockAssignmentsReturn(
  data: JobAssignment[],
): MockReturnValue<JobAssignment[]> {
  return { data, isLoading: false, isError: false, refetch: vi.fn() };
}

function makeMockUsersReturn(
  data: TenantUserItem[],
): MockReturnValue<TenantUserItem[]> {
  return { data, isLoading: false, isError: false };
}

function makeMockMutation(): MockMutationReturnValue {
  return { mutateAsync: vi.fn().mockResolvedValue({}), isPending: false };
}

describe("TechAssignmentSection", () => {
  beforeEach(() => {
    vi.mocked(useAddJobAssignment).mockReturnValue(
      makeMockMutation() as unknown as ReturnType<typeof useAddJobAssignment>,
    );
    vi.mocked(useRemoveJobAssignment).mockReturnValue(
      makeMockMutation() as unknown as ReturnType<
        typeof useRemoveJobAssignment
      >,
    );
    vi.mocked(useTenantUsers).mockReturnValue(
      makeMockUsersReturn(MOCK_USERS) as ReturnType<typeof useTenantUsers>,
    );
  });

  it('renders "No technician assigned" when assignments list is empty', () => {
    vi.mocked(useJobAssignments).mockReturnValue(
      makeMockAssignmentsReturn([]) as unknown as ReturnType<
        typeof useJobAssignments
      >,
    );

    renderWithProviders(<TechAssignmentSection jobId="job-001" />, "owner");

    expect(screen.getByText(/no technician assigned/i)).toBeInTheDocument();
  });

  it("renders tech name and Lead badge for primary assignment", () => {
    vi.mocked(useJobAssignments).mockReturnValue(
      makeMockAssignmentsReturn([PRIMARY_ASSIGNMENT]) as unknown as ReturnType<
        typeof useJobAssignments
      >,
    );

    renderWithProviders(<TechAssignmentSection jobId="job-001" />, "owner");

    expect(screen.getByText("Mike Sparks")).toBeInTheDocument();
    expect(screen.getByText("Lead")).toBeInTheDocument();
  });

  it("shows ✕ remove button for owner (schedule.manage permission)", () => {
    vi.mocked(useJobAssignments).mockReturnValue(
      makeMockAssignmentsReturn([PRIMARY_ASSIGNMENT]) as unknown as ReturnType<
        typeof useJobAssignments
      >,
    );

    renderWithProviders(<TechAssignmentSection jobId="job-001" />, "owner");

    expect(
      screen.getByRole("button", { name: /remove Mike Sparks/i }),
    ).toBeInTheDocument();
  });

  it("hides ✕ remove button for tech role (no schedule.manage permission)", () => {
    vi.mocked(useJobAssignments).mockReturnValue(
      makeMockAssignmentsReturn([PRIMARY_ASSIGNMENT]) as unknown as ReturnType<
        typeof useJobAssignments
      >,
    );

    renderWithProviders(
      <TechAssignmentSection jobId="job-001" />,
      "technician",
    );

    expect(
      screen.queryByRole("button", { name: /remove Mike Sparks/i }),
    ).not.toBeInTheDocument();
  });

  it('"+ Add technician" dropdown hidden when no available users remain', () => {
    const bothAssigned: JobAssignment[] = [
      { ...PRIMARY_ASSIGNMENT, user_id: "user-001", id: "assign-001" },
      {
        id: "assign-002",
        job_id: "job-001",
        user_id: "user-002",
        role: "helper",
        ordinal: 2,
        assigned_at: "2026-07-21T10:00:00Z",
        is_active: true,
      },
    ];

    vi.mocked(useJobAssignments).mockReturnValue(
      makeMockAssignmentsReturn(bothAssigned) as unknown as ReturnType<
        typeof useJobAssignments
      >,
    );

    renderWithProviders(<TechAssignmentSection jobId="job-001" />, "owner");

    // No available users → dropdown should not appear
    expect(screen.queryByTestId("add-tech-select")).not.toBeInTheDocument();
  });
});
