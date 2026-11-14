/**
 * FE-B30 Integration Test — Month view: chip display modes + overflow + today highlight
 *
 * Location: apps/web/src/__tests__/batch_fe_b30/dispatch_month_view_chips.integration.test.tsx
 *
 * Tests:
 * 1. Customer mode (default) shows customer_name in chips
 * 2. Tech mode shows tech initials + job title
 * 3. Overflow: 3 jobs in a cell → 2 chips + "+1 more" shown
 * 4. Today cell has brand-50 background class + brand-600 day number ring
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import { MonthViewCell } from "../../features/dispatch-board/components/MonthViewCell";
import { MOCK_TECHS_B30 } from "../../mocks/handlers/dispatchBoardHandlers";
import type { DispatchBoardJob } from "../../features/dispatch-board/types-stub";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/",
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

const TODAY = new Date().toISOString().slice(0, 10);

function makeJob(overrides: Partial<DispatchBoardJob> = {}): DispatchBoardJob {
  return {
    id: `job-${Math.random()}`,
    title: "Electrical Repair",
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
    ...overrides,
  };
}

describe("MonthViewCell FE-B30 — chip display + overflow + today", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("customer mode shows customer_name in chips", () => {
    const jobs = [
      makeJob({ id: "j1", customer_name: "Acme Corp" }),
      makeJob({ id: "j2", customer_name: "Beta LLC" }),
    ];
    render(
      <MonthViewCell
        dateStr={TODAY}
        jobs={jobs}
        techs={MOCK_TECHS_B30}
        isToday={false}
        isInRange
        onDrillDown={vi.fn()}
        chipDisplayMode="customer"
      />,
    );
    expect(screen.getByText("Acme Corp")).toBeInTheDocument();
    expect(screen.getByText("Beta LLC")).toBeInTheDocument();
  });

  it("tech mode shows tech initials (JR) + job title", () => {
    const jobs = [
      makeJob({
        id: "j1",
        title: "Panel Upgrade",
        tech_id: MOCK_TECHS_B30[0]!.id, // Jake Rodriguez → JR
      }),
    ];
    render(
      <MonthViewCell
        dateStr={TODAY}
        jobs={jobs}
        techs={MOCK_TECHS_B30}
        isToday={false}
        isInRange
        onDrillDown={vi.fn()}
        chipDisplayMode="tech"
      />,
    );
    expect(screen.getByText("JR")).toBeInTheDocument();
    expect(screen.getByText("Panel Upgrade")).toBeInTheDocument();
  });

  it("shows max 2 chips + '+1 more' for 3 jobs", () => {
    const jobs = [
      makeJob({ id: "j1", customer_name: "Customer 1" }),
      makeJob({ id: "j2", customer_name: "Customer 2" }),
      makeJob({ id: "j3", customer_name: "Customer 3" }),
    ];
    render(
      <MonthViewCell
        dateStr={TODAY}
        jobs={jobs}
        techs={MOCK_TECHS_B30}
        isToday={false}
        isInRange
        onDrillDown={vi.fn()}
        chipDisplayMode="customer"
      />,
    );
    expect(screen.getByText("Customer 1")).toBeInTheDocument();
    expect(screen.getByText("Customer 2")).toBeInTheDocument();
    // Third chip is in overflow — Customer 3 should NOT be visible as a chip
    expect(screen.queryByText("Customer 3")).not.toBeInTheDocument();
    expect(screen.getByText("+1 more")).toBeInTheDocument();
  });

  it("today cell renders with brand ring classes and brand day number", () => {
    const { container } = render(
      <MonthViewCell
        dateStr={TODAY}
        jobs={[]}
        techs={MOCK_TECHS_B30}
        isToday={true}
        isInRange
        onDrillDown={vi.fn()}
        chipDisplayMode="customer"
      />,
    );
    // Today cell should have bg-brand-50 class
    const cell = container.querySelector('[aria-label*="today"]');
    expect(cell).toBeInTheDocument();
    expect(cell?.className).toContain("bg-brand-50");
    expect(cell?.className).toContain("ring-brand-200");

    // Today day number should be in a rounded-full bg-brand-600 badge
    const dayBadge = container.querySelector(".bg-brand-600.text-white");
    expect(dayBadge).toBeInTheDocument();
  });
});
