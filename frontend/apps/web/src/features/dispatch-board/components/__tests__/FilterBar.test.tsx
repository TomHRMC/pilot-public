/**
 * FilterBar — unit tests
 *
 * Location: apps/web/src/features/dispatch-board/components/__tests__/FilterBar.test.tsx
 * DISPATCH-B2
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { FilterBar } from "../FilterBar";
import type { FilterBarProps } from "../FilterBar";
import type { DispatchBoardJob, DispatchBoardTech } from "../../types-stub";
import type { DispatchBoardFilters } from "../../store";

const DEFAULT_FILTERS: DispatchBoardFilters = {
  techIds: [],
  statuses: [],
  customerTypes: [],
  jobTypes: [],
  priorities: [],
};

const MOCK_TECHS: DispatchBoardTech[] = [
  {
    id: "tech-001",
    tech_id: "tech-001",
    name: "Jake Rivera",
    display_color: "#3B43D6",
    avatar_url: null,
  },
];

const MOCK_JOBS: DispatchBoardJob[] = [
  {
    id: "job-001",
    title: "Panel Upgrade",
    customer_name: "Acme Corp",
    site_address: "123 Main St",
    scheduled_start_at: "2026-07-27T09:00:00Z",
    scheduled_end_at: "2026-07-27T11:00:00Z",
    tech_id: "tech-001",
    status: "scheduled",
    // DISPATCH-B3: real values
    priority: "standard",
    customer_type: "company",
    site_type: "commercial",
    job_type_code: "panel_upgrade",
    job_type_label: "Panel Upgrade",
    updated_at: "2026-07-27T08:00:00Z",
  },
];

function makeProps(overrides: Partial<FilterBarProps> = {}): FilterBarProps {
  return {
    techs: MOCK_TECHS,
    jobs: MOCK_JOBS,
    filters: DEFAULT_FILTERS,
    collapsed: false,
    onToggleCollapsed: vi.fn(),
    onToggleTech: vi.fn(),
    onToggleStatus: vi.fn(),
    onToggleCustomerType: vi.fn(),
    onToggleJobType: vi.fn(),
    onTogglePriority: vi.fn(),
    onResetStatus: vi.fn(),
    onClearAll: vi.fn(),
    ...overrides,
  };
}

describe("FilterBar", () => {
  describe("expanded render", () => {
    it("renders status pills", () => {
      render(<FilterBar {...makeProps()} />);
      expect(screen.getByRole("button", { name: /all/i })).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /unassigned/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /scheduled/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /confirmed/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /in progress/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /completed/i }),
      ).toBeInTheDocument();
    });

    it("renders priority segmented control", () => {
      render(<FilterBar {...makeProps()} />);
      // DISPATCH-B3: Standard/Urgent/Emergency (was Rush/Warranty/Standard)
      expect(
        screen.getByRole("button", { name: /standard/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /urgent/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /emergency/i }),
      ).toBeInTheDocument();
    });

    it("renders Techs popover trigger button", () => {
      render(<FilterBar {...makeProps()} />);
      expect(
        screen.getByRole("button", { name: /techs/i }),
      ).toBeInTheDocument();
    });

    it("renders customer type pills", () => {
      render(<FilterBar {...makeProps()} />);
      // DISPATCH-B3: Person/Company (was Commercial/Residential)
      expect(
        screen.getByRole("button", { name: /person/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /company/i }),
      ).toBeInTheDocument();
    });

    it("'All' status pill is active (bg-white class) when statuses is empty", () => {
      render(<FilterBar {...makeProps()} />);
      const allBtn = screen.getByRole("button", { name: /^all$/i });
      expect(allBtn.className).toMatch(/bg-white/);
    });

    it("'All' pill is NOT active when a status is selected", () => {
      const props = makeProps({
        filters: { ...DEFAULT_FILTERS, statuses: ["scheduled"] },
      });
      render(<FilterBar {...props} />);
      const allBtn = screen.getByRole("button", { name: /^all$/i });
      expect(allBtn.className).not.toMatch(/bg-white/);
    });

    it("clicking a status pill calls onToggleStatus with correct union value", () => {
      const onToggleStatus = vi.fn();
      render(<FilterBar {...makeProps({ onToggleStatus })} />);
      fireEvent.click(screen.getByRole("button", { name: /scheduled/i }));
      expect(onToggleStatus).toHaveBeenCalledWith("scheduled");
    });

    it("clicking 'In Progress' pill calls onToggleStatus with 'in_progress'", () => {
      const onToggleStatus = vi.fn();
      render(<FilterBar {...makeProps({ onToggleStatus })} />);
      fireEvent.click(screen.getByRole("button", { name: /in progress/i }));
      expect(onToggleStatus).toHaveBeenCalledWith("in_progress");
    });

    it("clicking 'All' pill calls onResetStatus (not onClearAll)", () => {
      const onResetStatus = vi.fn();
      const onClearAll = vi.fn();
      const props = makeProps({
        filters: { ...DEFAULT_FILTERS, statuses: ["scheduled", "confirmed"] },
        onResetStatus,
        onClearAll,
      });
      render(<FilterBar {...props} />);
      fireEvent.click(screen.getByRole("button", { name: /^all$/i }));
      expect(onResetStatus).toHaveBeenCalledTimes(1);
      expect(onClearAll).not.toHaveBeenCalled();
    });

    it("job type row is absent when jobs have no job_type_code data", () => {
      const jobsNoType: DispatchBoardJob[] = [
        // DISPATCH-B3: no job_type_code → no job type pill rendered
        { ...MOCK_JOBS[0], job_type_code: null, job_type_label: null },
      ];
      render(<FilterBar {...makeProps({ jobs: jobsNoType })} />);
      // No job-type pill should appear; "Panel Upgrade" would appear if present
      expect(
        screen.queryByRole("button", { name: /panel upgrade/i }),
      ).not.toBeInTheDocument();
    });

    it("job type row is present when jobs have job_type_code data", () => {
      render(<FilterBar {...makeProps()} />);
      // MOCK_JOBS has job_type_code "panel_upgrade" / label "Panel Upgrade"
      expect(
        screen.getByRole("button", { name: /panel upgrade/i }),
      ).toBeInTheDocument();
    });

    it("active count text is hidden when no filters are active", () => {
      render(<FilterBar {...makeProps()} />);
      expect(screen.queryByText(/filter.*active/i)).not.toBeInTheDocument();
    });

    it("active count text shown with correct count when filters are active", () => {
      const props = makeProps({
        filters: {
          ...DEFAULT_FILTERS,
          statuses: ["scheduled"],
          // DISPATCH-B3: urgent (was rush)
          priorities: ["urgent"],
        },
      });
      render(<FilterBar {...props} />);
      expect(screen.getByText("2 filters active")).toBeInTheDocument();
    });

    it("'Clear all' is hidden when no filters are active", () => {
      render(<FilterBar {...makeProps()} />);
      expect(
        screen.queryByRole("button", { name: /clear all/i }),
      ).not.toBeInTheDocument();
    });

    it("'Clear all' is visible when a filter is active", () => {
      const props = makeProps({
        filters: { ...DEFAULT_FILTERS, statuses: ["scheduled"] },
      });
      render(<FilterBar {...props} />);
      expect(
        screen.getByRole("button", { name: /clear all/i }),
      ).toBeInTheDocument();
    });

    it("'Clear all' calls onClearAll", () => {
      const onClearAll = vi.fn();
      const props = makeProps({
        filters: { ...DEFAULT_FILTERS, statuses: ["scheduled"] },
        onClearAll,
      });
      render(<FilterBar {...props} />);
      fireEvent.click(screen.getByRole("button", { name: /clear all/i }));
      expect(onClearAll).toHaveBeenCalledTimes(1);
    });

    it("collapse toggle button is visible and calls onToggleCollapsed", () => {
      const onToggleCollapsed = vi.fn();
      render(<FilterBar {...makeProps({ onToggleCollapsed })} />);
      // Collapse toggle has title "Collapse filters"
      const collapseBtn = screen.getByTitle("Collapse filters");
      fireEvent.click(collapseBtn);
      expect(onToggleCollapsed).toHaveBeenCalledTimes(1);
    });
  });

  describe("collapsed render", () => {
    it("shows only Filters toggle and count badge when collapsed=true with active filters", () => {
      const props = makeProps({
        collapsed: true,
        filters: { ...DEFAULT_FILTERS, statuses: ["scheduled"] },
      });
      render(<FilterBar {...props} />);
      // Only the collapse toggle is visible — no status pills
      expect(
        screen.queryByRole("button", { name: /unassigned/i }),
      ).not.toBeInTheDocument();
      expect(screen.getByText("· 1")).toBeInTheDocument();
    });

    it("calls onToggleCollapsed when collapsed toggle is clicked", () => {
      const onToggleCollapsed = vi.fn();
      render(
        <FilterBar {...makeProps({ collapsed: true, onToggleCollapsed })} />,
      );
      const expandBtn = screen.getByTitle("Expand filters");
      fireEvent.click(expandBtn);
      expect(onToggleCollapsed).toHaveBeenCalledTimes(1);
    });
  });
});
