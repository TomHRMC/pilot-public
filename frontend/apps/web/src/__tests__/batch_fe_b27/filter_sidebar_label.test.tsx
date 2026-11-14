/**
 * FE-B27 — FilterSidebar "Customer Type" label test
 *
 * Location: apps/web/src/__tests__/batch_fe_b27/filter_sidebar_label.test.tsx
 *
 * Verifies:
 * - FilterSidebar renders "Customer Type" group label
 * - FilterSidebar does NOT render standalone "Customer" as group label heading
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { FilterSidebar } from "@/features/dispatch-board/components/FilterSidebar";
import type {
  DispatchBoardJob,
  DispatchBoardTech,
} from "@/features/dispatch-board/types-stub";

const mockTechs: DispatchBoardTech[] = [
  {
    id: "tech-001",
    tech_id: "tech-001",
    name: "Jake Rivera",
    display_color: "#3B43D6",
    avatar_url: null,
  },
];

const mockJobs: DispatchBoardJob[] = [
  {
    id: "job-001",
    title: "Panel Upgrade",
    customer_name: "Bright Electric Co.",
    site_address: "123 Main St",
    scheduled_start_at: "2026-07-11T09:00:00Z",
    scheduled_end_at: "2026-07-11T12:00:00Z",
    tech_id: "tech-001",
    status: "scheduled",
    customer_type: "person",
    job_type_code: "electrical",
    job_type_label: "Electrical",
    priority: "standard",
    updated_at: "2026-07-11T08:00:00Z",
  },
];

const defaultFilters = {
  techIds: [],
  statuses: [],
  customerTypes: [],
  jobTypes: [],
  priorities: [],
};

function renderFilterSidebar() {
  return render(
    <FilterSidebar
      techs={mockTechs}
      jobs={mockJobs}
      filters={defaultFilters}
      onToggleTech={() => {}}
      onToggleStatus={() => {}}
      onToggleCustomerType={() => {}}
      onToggleJobType={() => {}}
      onTogglePriority={() => {}}
      onClearAll={() => {}}
    />,
  );
}

describe("FilterSidebar — FE-B27 Customer Type label rename (§Task 7)", () => {
  it("renders 'Customer Type' as a filter group label", () => {
    renderFilterSidebar();
    // h3 group label should say "Customer Type"
    const label = screen.getByText("Customer Type");
    expect(label).toBeInTheDocument();
  });

  it("does NOT render 'Customer' as a standalone group label heading", () => {
    renderFilterSidebar();
    // The h3 elements are the group labels — none should be exactly "Customer"
    const h3Elements = document.querySelectorAll("h3");
    const customerH3 = Array.from(h3Elements).find(
      (el) => el.textContent?.trim() === "Customer",
    );
    expect(customerH3).toBeUndefined();
  });
});
