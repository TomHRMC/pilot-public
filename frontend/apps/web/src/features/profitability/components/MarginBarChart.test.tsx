/**
 * MarginBarChart — Unit Tests
 *
 * Location: apps/web/src/features/profitability/components/MarginBarChart.test.tsx
 * Per batch-fe-b4-design.md §I.1
 * Target: 5 tests
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import React from "react";
import { MarginBarChart } from "./MarginBarChart";
import type { MarginDistribution } from "../hooks/useProfitability";

const distribution: MarginDistribution = {
  "below-low": 2,
  low: 3,
  medium: 5,
  high: 4,
};

describe("MarginBarChart", () => {
  it("renders with accessible role=img", () => {
    render(
      <MarginBarChart
        distribution={distribution}
        activeBucket={null}
        onBucketSelect={vi.fn()}
      />,
    );
    expect(screen.getByRole("img")).toBeInTheDocument();
  });

  it("has a descriptive aria-label on the chart container", () => {
    render(
      <MarginBarChart
        distribution={distribution}
        activeBucket={null}
        onBucketSelect={vi.fn()}
      />,
    );
    const chart = screen.getByRole("img");
    // aria-label should describe the chart's purpose
    expect(chart.getAttribute("aria-label")).toBeTruthy();
    expect(chart.getAttribute("aria-label")!.length).toBeGreaterThan(10);
  });

  it("renders without error when activeBucket is set", () => {
    render(
      <MarginBarChart
        distribution={distribution}
        activeBucket="medium"
        onBucketSelect={vi.fn()}
      />,
    );
    expect(screen.getByRole("img")).toBeInTheDocument();
  });

  it("renders without error when all distribution values are 0", () => {
    render(
      <MarginBarChart
        distribution={{ "below-low": 0, low: 0, medium: 0, high: 0 }}
        activeBucket={null}
        onBucketSelect={vi.fn()}
      />,
    );
    expect(screen.getByRole("img")).toBeInTheDocument();
  });

  it("accepts onBucketSelect callback without throwing", () => {
    const onBucketSelect = vi.fn();
    expect(() =>
      render(
        <MarginBarChart
          distribution={distribution}
          activeBucket={null}
          onBucketSelect={onBucketSelect}
        />,
      ),
    ).not.toThrow();
  });
});
