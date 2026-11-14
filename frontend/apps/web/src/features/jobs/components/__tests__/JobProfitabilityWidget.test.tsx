/**
 * JobProfitabilityWidget unit tests — FE-B21
 *
 * Location: apps/web/src/features/jobs/components/__tests__/JobProfitabilityWidget.test.tsx
 */

import { render, screen } from "@testing-library/react";
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { JobProfitabilityWidget } from "../JobProfitabilityWidget";

// ── Mock hooks ─────────────────────────────────────────────────────────────────

vi.mock("../../hooks/useJob", () => ({
  useJob: vi.fn(),
}));

vi.mock("../../hooks/useProjectedMargin", () => ({
  useProjectedMargin: vi.fn(),
  MARGIN_TARGET_PCT: 20,
}));

import { useJob } from "../../hooks/useJob";
import { useProjectedMargin } from "../../hooks/useProjectedMargin";

// ── Test helpers ───────────────────────────────────────────────────────────────

function makeContext(): AuthContextValue {
  return {
    user: {
      id: "u1",
      email: "a@b.com",
      role: "owner",
      tenantId: "t1",
      displayName: "Test Owner",
      accessToken: "tok",
    },
    isAuthenticated: true,
    role: "owner",
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

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <AuthContext.Provider value={makeContext()}>
      <QueryClientProvider client={makeQueryClient()}>
        {children}
      </QueryClientProvider>
    </AuthContext.Provider>
  );
}

const MOCK_JOB = {
  id: "job-1",
  tenant_id: "t1",
  customer_id: "cust-1",
  site_id: "site-1",
  status_id: "status-in-progress",
  scheduled_start_at: "2026-06-16T09:00:00Z",
  scheduled_end_at: "2026-06-16T17:00:00Z",
  estimated_duration_minutes: 480,
  external_calendar_event_id: null,
  actual_labor_cost_cents: 36000,
  actual_material_cost_cents: 20000,
  actual_profit_cents: 12000,
  is_active: true,
};

// ── Tests ──────────────────────────────────────────────────────────────────────

describe("JobProfitabilityWidget", () => {
  beforeEach(() => {
    vi.mocked(useJob).mockReset();
    vi.mocked(useProjectedMargin).mockReset();
  });

  it("renders labor and material actuals from job data", () => {
    vi.mocked(useJob).mockReturnValue({
      data: MOCK_JOB,
      isLoading: false,
      isError: false,
    } as never);

    vi.mocked(useProjectedMargin).mockReturnValue({
      data: {
        projected_margin_pct: 32,
        cost_to_date_cents: 285000,
        etc_hours_remaining: 2.5,
        revenue_cents: 450000,
        margin_bucket: "high",
        hours_worked: 8,
        quoted_hours: 10,
      },
      isLoading: false,
      isError: false,
    } as never);

    render(<JobProfitabilityWidget jobId="job-1" />, {
      wrapper: Wrapper,
    });

    // $360 (36000 cents)
    expect(screen.getByText(/\$360/)).toBeTruthy();
    // $200 (20000 cents)
    expect(screen.getByText(/\$200/)).toBeTruthy();
    // 32%
    expect(screen.getByText("32%")).toBeTruthy();
  });

  it("shows 'above target' indicator when margin >= 20%", () => {
    vi.mocked(useJob).mockReturnValue({
      data: MOCK_JOB,
      isLoading: false,
      isError: false,
    } as never);

    vi.mocked(useProjectedMargin).mockReturnValue({
      data: {
        projected_margin_pct: 25,
        cost_to_date_cents: 100000,
        etc_hours_remaining: 1,
        revenue_cents: 200000,
        margin_bucket: "medium",
        hours_worked: 4,
        quoted_hours: 5,
      },
      isLoading: false,
      isError: false,
    } as never);

    render(<JobProfitabilityWidget jobId="job-1" />, {
      wrapper: Wrapper,
    });

    expect(screen.getByTestId("above-target")).toBeTruthy();
    expect(screen.queryByTestId("below-target")).toBeNull();
    expect(screen.getByText(/above target/i)).toBeTruthy();
  });

  it("shows 'below target' indicator when margin < 20%", () => {
    vi.mocked(useJob).mockReturnValue({
      data: MOCK_JOB,
      isLoading: false,
      isError: false,
    } as never);

    vi.mocked(useProjectedMargin).mockReturnValue({
      data: {
        projected_margin_pct: 6,
        cost_to_date_cents: 420000,
        etc_hours_remaining: 5,
        revenue_cents: 380000,
        margin_bucket: "below-low",
        hours_worked: 12,
        quoted_hours: 10,
      },
      isLoading: false,
      isError: false,
    } as never);

    render(<JobProfitabilityWidget jobId="job-1" />, {
      wrapper: Wrapper,
    });

    expect(screen.getByTestId("below-target")).toBeTruthy();
    expect(screen.queryByTestId("above-target")).toBeNull();
    expect(screen.getByText(/below target/i)).toBeTruthy();
  });

  it("shows loading skeleton while data loads", () => {
    vi.mocked(useJob).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as never);

    vi.mocked(useProjectedMargin).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as never);

    render(<JobProfitabilityWidget jobId="job-1" />, {
      wrapper: Wrapper,
    });

    // When loading, no cost values or margin indicators should be visible
    expect(screen.queryByTestId("above-target")).toBeNull();
    expect(screen.queryByTestId("below-target")).toBeNull();
    // Skeleton divs are present (animate-pulse)
    const skeletons = document.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(0);
  });
});
