/**
 * PeriodSelector unit tests — BETA-B6 additions
 *
 * Location: apps/web/src/features/profitability/components/PeriodSelector.test.tsx
 *
 * Tests the "Custom" pill and date range inputs added in BETA-B6.
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { PeriodSelector } from "./PeriodSelector";

describe("PeriodSelector — BETA-B6 Custom date range", () => {
  it("renders the Custom pill", () => {
    render(<PeriodSelector value="7d" onChange={vi.fn()} />);
    expect(screen.getByText("Custom")).toBeInTheDocument();
  });

  it("shows From and To date inputs when Custom is selected", () => {
    render(<PeriodSelector value="custom" onChange={vi.fn()} />);
    expect(screen.getByLabelText(/from/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/to/i)).toBeInTheDocument();
  });

  it("does not show date inputs when a non-custom period is selected", () => {
    render(<PeriodSelector value="7d" onChange={vi.fn()} />);
    expect(screen.queryByLabelText(/from/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/to/i)).not.toBeInTheDocument();
  });

  it("calls onCustomDatesChange with updated from date when From input changes", async () => {
    const user = userEvent.setup();
    const onCustomDatesChange = vi.fn();

    render(
      <PeriodSelector
        value="custom"
        onChange={vi.fn()}
        customDateFrom=""
        customDateTo="2026-06-30"
        onCustomDatesChange={onCustomDatesChange}
      />,
    );

    const fromInput = screen.getByLabelText(/from/i);
    await user.clear(fromInput);
    await user.type(fromInput, "2026-06-01");

    // Should be called with the new from value and the existing to value
    expect(onCustomDatesChange).toHaveBeenLastCalledWith(
      "2026-06-01",
      "2026-06-30",
    );
  });

  it("calls onCustomDatesChange with updated to date when To input changes", async () => {
    const user = userEvent.setup();
    const onCustomDatesChange = vi.fn();

    render(
      <PeriodSelector
        value="custom"
        onChange={vi.fn()}
        customDateFrom="2026-06-01"
        customDateTo=""
        onCustomDatesChange={onCustomDatesChange}
      />,
    );

    const toInput = screen.getByLabelText(/to/i);
    await user.clear(toInput);
    await user.type(toInput, "2026-06-30");

    expect(onCustomDatesChange).toHaveBeenLastCalledWith(
      "2026-06-01",
      "2026-06-30",
    );
  });

  it("renders all 5 period pills (7 days, 30 days, MTD, YTD, Custom)", () => {
    render(<PeriodSelector value="7d" onChange={vi.fn()} />);
    expect(screen.getByText("7 days")).toBeInTheDocument();
    expect(screen.getByText("30 days")).toBeInTheDocument();
    expect(screen.getByText("MTD")).toBeInTheDocument();
    expect(screen.getByText("YTD")).toBeInTheDocument();
    expect(screen.getByText("Custom")).toBeInTheDocument();
  });

  it("marks Custom pill as pressed when value is custom", () => {
    render(<PeriodSelector value="custom" onChange={vi.fn()} />);
    expect(screen.getByText("Custom")).toHaveAttribute("aria-pressed", "true");
  });

  it("calls onChange with 'custom' when Custom pill is clicked", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<PeriodSelector value="7d" onChange={onChange} />);
    await user.click(screen.getByText("Custom"));
    expect(onChange).toHaveBeenCalledWith("custom");
  });
});
