/**
 * FE-B30 Integration Test — DispatchToolbar: 4-Day tab removed
 *
 * Location: apps/web/src/__tests__/batch_fe_b30/dispatch_toolbar_4day_removed.integration.test.tsx
 *
 * Tests:
 * 1. "4 Day" tab is NOT in the rendered toolbar
 * 2. "Day", "Week", "Month" tabs are present
 * 3. Week-specific controls appear when viewTab="week"
 * 4. Month-specific controls (chip toggle) appear when viewTab="month"
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DispatchToolbar } from "../../features/dispatch-board/components/DispatchToolbar";

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

// Mock InFlightSyncIndicator so it doesn't pull in dependencies
vi.mock("@pilot/ui/sync-indicator", () => ({
  InFlightSyncIndicator: () => <div data-testid="sync-indicator" />,
}));

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
  activeDate: "2026-07-14",
  sseConnected: true,
  lastBoardFetch: null,
  onViewTabChange: vi.fn(),
  onNavigatePrev: vi.fn(),
  onNavigateNext: vi.fn(),
  onNavigateToToday: vi.fn(),
  onWeekDaysToggle: vi.fn(),
  onChipDisplayModeToggle: vi.fn(),
};

describe("DispatchToolbar FE-B30 — 4-Day tab removed", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("does NOT render a '4 Day' tab", () => {
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <DispatchToolbar {...baseProps} viewTab="day" />
      </Wrapper>,
    );
    expect(
      screen.queryByRole("tab", { name: /4 day/i }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("4 Day")).not.toBeInTheDocument();
  });

  it("renders Day, Week, and Month tabs only", () => {
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <DispatchToolbar {...baseProps} viewTab="day" />
      </Wrapper>,
    );
    expect(screen.getByRole("tab", { name: "Day" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Week" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Month" })).toBeInTheDocument();
  });

  it("shows week-specific 5-day/7-day toggle when viewTab='week'", () => {
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <DispatchToolbar {...baseProps} viewTab="week" weekDaysToShow={5} />
      </Wrapper>,
    );
    expect(screen.getByText("5-day")).toBeInTheDocument();
    expect(screen.getByText("7-day")).toBeInTheDocument();
    expect(screen.getByText("This Week")).toBeInTheDocument();
  });

  it("shows month-specific Customer/Tech chip toggle when viewTab='month'", () => {
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <DispatchToolbar
          {...baseProps}
          viewTab="month"
          chipDisplayMode="customer"
        />
      </Wrapper>,
    );
    expect(screen.getByText("Customer")).toBeInTheDocument();
    expect(screen.getByText("Tech")).toBeInTheDocument();
    expect(screen.getByText("Today")).toBeInTheDocument();
  });
});
