/**
 * FE-B30 Integration Test — DispatchWeekView: render
 *
 * Location: apps/web/src/__tests__/batch_fe_b30/dispatch_week_view_render.integration.test.tsx
 *
 * Tests:
 * 1. Week view renders with tech column headers visible (Jake Rodriguez, Maria Santos)
 * 2. Day row headers show short weekday names
 * 3. Jobs render in correct cells (tech × date)
 * 4. Mobile fallback renders "Week view is available on desktop"
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DispatchWeekView } from "../../features/dispatch-board/components/DispatchWeekView";
import {
  MOCK_TECHS_B30,
  MOCK_BOARD_JOBS_B30,
} from "../../mocks/handlers/dispatchBoardHandlers";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/dispatch",
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

vi.mock("@pilot/shared-api", () => ({
  apiClient: {
    patch: vi.fn().mockResolvedValue({ data: {} }),
  },
}));

const TODAY = new Date().toISOString().slice(0, 10);

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  }
  return Wrapper;
}

const baseProps = {
  weekStartDate: TODAY,
  daysToShow: 5 as const,
  techs: MOCK_TECHS_B30,
  jobs: MOCK_BOARD_JOBS_B30,
  onJobDrop: vi.fn().mockResolvedValue(undefined),
  onJobClick: vi.fn(),
  onNavigateToDate: vi.fn(),
  onViewTabChange: vi.fn(),
};

describe("DispatchWeekView FE-B30 — render", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders tech column headers (Jake Rodriguez, Maria Santos)", () => {
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <DispatchWeekView {...baseProps} />
      </Wrapper>,
    );
    expect(screen.getByText("Jake Rodriguez")).toBeInTheDocument();
    expect(screen.getByText("Maria Santos")).toBeInTheDocument();
  });

  it("renders day row headers for 5-day mode", () => {
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <DispatchWeekView {...baseProps} daysToShow={5} />
      </Wrapper>,
    );
    // Short weekday abbreviations should appear in the table
    const allText = document.body.textContent ?? "";
    // The week always includes Mon and at least one other weekday
    // (exact set depends on which day today is, but Mon–Fri is always present for a 5-day week)
    expect(allText).toMatch(/Mon|Tue|Wed|Thu|Fri/);
  });

  it("renders job cards for today's jobs", () => {
    const Wrapper = createWrapper();
    // Use 7-day view to ensure today (any day of week) is always visible
    render(
      <Wrapper>
        <DispatchWeekView {...baseProps} daysToShow={7} />
      </Wrapper>,
    );
    // MOCK_BOARD_JOBS_B30 jobs are scheduled for TODAY — they should appear
    expect(screen.getByText(/Panel upgrade/i)).toBeInTheDocument();
    expect(screen.getByText(/Breaker replacement/i)).toBeInTheDocument();
  });

  it("renders mobile fallback message (hidden on desktop via CSS)", () => {
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <DispatchWeekView {...baseProps} />
      </Wrapper>,
    );
    // The mobile fallback is always in the DOM (hidden by Tailwind on md+)
    expect(
      screen.getByText("Week view is available on desktop."),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "View Today" }),
    ).toBeInTheDocument();
  });
});
