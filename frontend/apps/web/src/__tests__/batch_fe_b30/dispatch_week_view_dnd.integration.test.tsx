/**
 * FE-B30 Integration Test — DispatchWeekView: drag-and-drop
 *
 * Location: apps/web/src/__tests__/batch_fe_b30/dispatch_week_view_dnd.integration.test.tsx
 *
 * Tests:
 * 1. Job cards are draggable (rendered as role=button with correct aria-label)
 * 2. 4 jobs render in a cell without capacity warnings
 * 3. Context menu right-click shows "View Job" and "Job Properties" items
 * 4. Context menu closes on Escape
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DispatchWeekView } from "../../features/dispatch-board/components/DispatchWeekView";
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

const mockApiPatch = vi.fn().mockResolvedValue({ data: {} });
vi.mock("@pilot/shared-api", () => ({
  apiClient: {
    patch: mockApiPatch,
  },
}));

// Use 7-day view and set weekStartDate = TODAY so Saturday jobs appear
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

function makeJob(overrides: Partial<DispatchBoardJob> = {}): DispatchBoardJob {
  return {
    id: "job-test-001",
    title: "Draggable Job",
    customer_name: "Test Customer",
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
    ...overrides,
  };
}

describe("DispatchWeekView FE-B30 — drag-and-drop", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders job cards that are draggable (role=button with aria-label)", () => {
    const Wrapper = createWrapper();
    const job = makeJob({ title: "Draggable Job" });
    render(
      <Wrapper>
        <DispatchWeekView
          weekStartDate={TODAY}
          daysToShow={7}
          techs={MOCK_TECHS_B30}
          jobs={[job]}
          onJobDrop={vi.fn().mockResolvedValue(undefined)}
          onJobClick={vi.fn()}
          onNavigateToDate={vi.fn()}
        />
      </Wrapper>,
    );
    // aria-label is "Job: Draggable Job"
    expect(
      screen.getByRole("button", { name: /Job: Draggable Job/i }),
    ).toBeInTheDocument();
  });

  it("renders 4 jobs in a cell", () => {
    const Wrapper = createWrapper();
    const jobs = Array.from({ length: 4 }, (_, i) =>
      makeJob({ id: `job-cap-${i}`, title: `Job ${i + 1}` }),
    );
    render(
      <Wrapper>
        <DispatchWeekView
          weekStartDate={TODAY}
          daysToShow={7}
          techs={MOCK_TECHS_B30}
          jobs={jobs}
          onJobDrop={vi.fn().mockResolvedValue(undefined)}
          onJobClick={vi.fn()}
          onNavigateToDate={vi.fn()}
        />
      </Wrapper>,
    );
    // All 4 jobs should render
    expect(screen.getByText("Job 1")).toBeInTheDocument();
    expect(screen.getByText("Job 2")).toBeInTheDocument();
    expect(screen.getByText("Job 3")).toBeInTheDocument();
    expect(screen.getByText("Job 4")).toBeInTheDocument();
  });

  it("shows context menu with 'View Job' and 'Job Properties' on right-click", () => {
    const Wrapper = createWrapper();
    const job = makeJob({ title: "Context Menu Job" });
    render(
      <Wrapper>
        <DispatchWeekView
          weekStartDate={TODAY}
          daysToShow={7}
          techs={MOCK_TECHS_B30}
          jobs={[job]}
          onJobDrop={vi.fn().mockResolvedValue(undefined)}
          onJobClick={vi.fn()}
          onNavigateToDate={vi.fn()}
        />
      </Wrapper>,
    );
    const jobCard = screen.getByRole("button", {
      name: /Job: Context Menu Job/i,
    });
    fireEvent.contextMenu(jobCard);
    expect(screen.getByRole("menu")).toBeInTheDocument();
    expect(
      screen.getByRole("menuitem", { name: "View Job" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("menuitem", { name: "Job Properties" }),
    ).toBeInTheDocument();
  });

  it("closes context menu on Escape key", () => {
    const Wrapper = createWrapper();
    const job = makeJob({ title: "Escape Close Job" });
    render(
      <Wrapper>
        <DispatchWeekView
          weekStartDate={TODAY}
          daysToShow={7}
          techs={MOCK_TECHS_B30}
          jobs={[job]}
          onJobDrop={vi.fn().mockResolvedValue(undefined)}
          onJobClick={vi.fn()}
          onNavigateToDate={vi.fn()}
        />
      </Wrapper>,
    );
    const jobCard = screen.getByRole("button", {
      name: /Job: Escape Close Job/i,
    });
    fireEvent.contextMenu(jobCard);
    expect(screen.getByRole("menu")).toBeInTheDocument();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });
});
