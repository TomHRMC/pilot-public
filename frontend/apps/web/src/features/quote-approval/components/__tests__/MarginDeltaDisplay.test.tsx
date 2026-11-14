/**
 * MarginDeltaDisplay unit tests
 *
 * Location: apps/web/src/features/quote-approval/components/__tests__/MarginDeltaDisplay.test.tsx
 */

import { render, screen } from "@testing-library/react";
import React from "react";
import { describe, it, expect } from "vitest";
import { MarginDeltaDisplay } from "../MarginDeltaDisplay";

describe("MarginDeltaDisplay", () => {
  it("renders current margin percent", () => {
    render(<MarginDeltaDisplay currentMarginPercent={42.5} />);
    expect(screen.getByText("42.5%")).toBeTruthy();
  });

  it("renders struck-through original margin when changed", () => {
    render(
      <MarginDeltaDisplay
        currentMarginPercent={38.0}
        preEditMarginPercent={42.5}
      />,
    );
    // Both margins should be shown
    expect(screen.getByText("38.0%")).toBeTruthy();
    expect(screen.getByText("42.5%")).toBeTruthy();
  });

  it("does not show struck-through when margin unchanged", () => {
    render(
      <MarginDeltaDisplay
        currentMarginPercent={42.5}
        preEditMarginPercent={42.5}
      />,
    );
    // Only one instance of the margin
    const margins = screen.getAllByText("42.5%");
    expect(margins.length).toBe(1);
  });

  it("shows 'below target' when below target margin", () => {
    render(
      <MarginDeltaDisplay
        currentMarginPercent={25.0}
        targetMarginPercent={30}
      />,
    );
    expect(screen.getByText(/below.*target/i)).toBeTruthy();
  });

  it("uses fault token class when below target", () => {
    const { container } = render(
      <MarginDeltaDisplay currentMarginPercent={25.0} />,
    );
    expect(container.innerHTML).toContain("text-fault-600");
  });

  it("uses margin token class when at/above target", () => {
    const { container } = render(
      <MarginDeltaDisplay currentMarginPercent={35.0} />,
    );
    expect(container.innerHTML).toContain("text-margin-600");
  });
});
