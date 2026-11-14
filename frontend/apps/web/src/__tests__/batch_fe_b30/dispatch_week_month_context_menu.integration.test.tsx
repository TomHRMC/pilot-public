/**
 * FE-B30 Integration Test — Context menus: Week + Month views
 *
 * Location: apps/web/src/__tests__/batch_fe_b30/dispatch_week_month_context_menu.integration.test.tsx
 *
 * Tests:
 * 1. Right-click on Week view job card → context menu appears
 * 2. "Job Properties" menu item calls onJobClick
 * 3. Right-click on Month view chip → context menu appears
 * 4. Pressing Escape closes the context menu
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DispatchWeekView } from "../../features/dispatch-board/components/DispatchWeekView";
import { MonthViewCell } from "../../features/dispatch-board/components/MonthViewCell";
import { MOCK_TECHS_B30 } from "../../mocks/handlers/dispatchBoardHandlers";
import type { DispatchBoardJob } from "../../features/dispatch-board/types-stub";

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
  apiClient: { patch: vi.fn().mockResolvedValue({ data: {} }) },
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

const mockJob: DispatchBoardJob = {
  id: "job-ctx-001",
  title: "Context Menu Test Job",
  customer_name: "Acme Corp",
  site_address: "123 Test St",
  scheduled_start_at: `${TODAY}T09:00:00.000Z`,
  scheduled_end_at: `${TODAY}T11:00:00.000Z`,
  tech_id: MOCK_TECHS_B30[0]!.id,
  status: "scheduled",
  priority: "standard",
  customer_type: "company",
  job_type_code: "install",
  job_type_label: "Install",
  updated_at: new Date().toISOString(),
};

describe("FE-B30 — Context menus (Week + Month views)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("right-click on week view job card shows context menu", () => {
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <DispatchWeekView
          weekStartDate={TODAY}
          daysToShow={7}
          techs={MOCK_TECHS_B30}
          jobs={[mockJob]}
          onJobDrop={vi.fn().mockResolvedValue(undefined)}
          onJobClick={vi.fn()}
          onNavigateToDate={vi.fn()}
        />
      </Wrapper>,
    );
    // aria-label is "Job: Context Menu Test Job"
    const jobCard = screen.getByRole("button", {
      name: /Job: Context Menu Test Job/i,
    });
    fireEvent.contextMenu(jobCard);
    expect(screen.getByRole("menu")).toBeInTheDocument();
  });

  it("clicking 'Job Properties' in week context menu calls onJobClick", () => {
    const mockOnJobClick = vi.fn();
    const Wrapper = createWrapper();
    render(
      <Wrapper>
        <DispatchWeekView
          weekStartDate={TODAY}
          daysToShow={7}
          techs={MOCK_TECHS_B30}
          jobs={[mockJob]}
          onJobDrop={vi.fn().mockResolvedValue(undefined)}
          onJobClick={mockOnJobClick}
          onNavigateToDate={vi.fn()}
        />
      </Wrapper>,
    );
    const jobCard = screen.getByRole("button", {
      name: /Job: Context Menu Test Job/i,
    });
    fireEvent.contextMenu(jobCard);
    const jobPropsItem = screen.getByRole("menuitem", {
      name: "Job Properties",
    });
    fireEvent.click(jobPropsItem);
    expect(mockOnJobClick).toHaveBeenCalledWith(
      expect.objectContaining({ id: mockJob.id }),
    );
  });

  it("right-click on month view chip shows context menu", () => {
    const mockOnJobClick = vi.fn();
    render(
      <MonthViewCell
        dateStr={TODAY}
        jobs={[mockJob]}
        techs={MOCK_TECHS_B30}
        isToday={false}
        isInRange
        onDrillDown={vi.fn()}
        chipDisplayMode="customer"
        onJobClick={mockOnJobClick}
      />,
    );
    const chip = screen.getByText("Acme Corp");
    fireEvent.contextMenu(chip);
    expect(screen.getByRole("menu")).toBeInTheDocument();
    expect(
      screen.getByRole("menuitem", { name: "Job Properties" }),
    ).toBeInTheDocument();
  });

  it("Escape key closes month view context menu", () => {
    render(
      <MonthViewCell
        dateStr={TODAY}
        jobs={[mockJob]}
        techs={MOCK_TECHS_B30}
        isToday={false}
        isInRange
        onDrillDown={vi.fn()}
        chipDisplayMode="customer"
        onJobClick={vi.fn()}
      />,
    );
    const chip = screen.getByText("Acme Corp");
    fireEvent.contextMenu(chip);
    expect(screen.getByRole("menu")).toBeInTheDocument();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });
});
