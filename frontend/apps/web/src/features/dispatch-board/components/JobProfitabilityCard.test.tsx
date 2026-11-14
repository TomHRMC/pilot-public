/**
 * JobProfitabilityCard — Unit Tests
 *
 * Location: apps/web/src/features/dispatch-board/components/JobProfitabilityCard.test.tsx
 * Per batch-fe-b4-design.md §I.1
 * Target: 6 tests
 */

import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom";
import React from "react";
import { JobProfitabilityCard } from "./JobProfitabilityCard";
import type { ProjectedMargin } from "../hooks/useJobDetail";

const highMarginData: ProjectedMargin = {
  projected_margin_pct: 32,
  cost_to_date_cents: 285000,
  etc_hours_remaining: 2.5,
  revenue_cents: 450000,
  margin_bucket: "high",
  hours_worked: 8,
  quoted_hours: 10,
};

const belowLowMarginData: ProjectedMargin = {
  projected_margin_pct: 6,
  cost_to_date_cents: 420000,
  etc_hours_remaining: 5.0,
  revenue_cents: 380000,
  margin_bucket: "below-low",
  hours_worked: 12,
  quoted_hours: 10,
};

describe("JobProfitabilityCard", () => {
  it("renders revenue formatted as currency", () => {
    render(
      <JobProfitabilityCard projectedMargin={highMarginData} quoteLines={[]} />,
    );
    expect(screen.getByText("$4,500")).toBeInTheDocument();
  });

  it("renders cost to date", () => {
    render(
      <JobProfitabilityCard projectedMargin={highMarginData} quoteLines={[]} />,
    );
    expect(screen.getByText("$2,850")).toBeInTheDocument();
  });

  it("renders projected profit", () => {
    render(
      <JobProfitabilityCard projectedMargin={highMarginData} quoteLines={[]} />,
    );
    // Revenue - Cost = $4500 - $2850 = $1650
    expect(screen.getByText("$1,650")).toBeInTheDocument();
  });

  it("shows 'below-low' bucket with fault-color chip", () => {
    const { container } = render(
      <JobProfitabilityCard
        projectedMargin={belowLowMarginData}
        quoteLines={[]}
      />,
    );
    // MarginBucketChip should contain "Below target" text
    expect(screen.getByText("Below target")).toBeInTheDocument();
    // The chip should have fault styling
    const chip = container.querySelector(".bg-fault-50");
    expect(chip).toBeInTheDocument();
  });

  it("shows 'high' bucket with margin-color chip", () => {
    const { container } = render(
      <JobProfitabilityCard projectedMargin={highMarginData} quoteLines={[]} />,
    );
    expect(screen.getByText("Strong margin")).toBeInTheDocument();
    const chip = container.querySelector(".bg-margin-100");
    expect(chip).toBeInTheDocument();
  });

  it("expands ETC drill-down when toggle clicked", () => {
    render(
      <JobProfitabilityCard projectedMargin={highMarginData} quoteLines={[]} />,
    );
    // ETC table not visible initially
    expect(screen.queryByText("No ETC data available")).toBeNull();

    // Click the toggle
    fireEvent.click(screen.getByText("Show line-item breakdown"));

    // Now shows the ETC drill-down (empty state)
    expect(screen.getByText("No ETC data available")).toBeInTheDocument();
  });
});
