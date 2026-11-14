/**
 * MonthDeferredState — Unit Tests
 *
 * Location: apps/web/src/features/dispatch-board/components/MonthDeferredState.test.tsx
 * Per batch-beta-v1-fixes-b5-design.md §I.1
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import { MonthDeferredState } from "./MonthDeferredState";

describe("MonthDeferredState", () => {
  it("renders 'Month view coming soon' heading", () => {
    render(<MonthDeferredState />);
    expect(
      screen.getByRole("heading", { name: /Month view coming soon/i }),
    ).toBeInTheDocument();
  });

  it("renders explanatory paragraph suggesting other views", () => {
    render(<MonthDeferredState />);
    expect(
      screen.getByText(/Switch to Day, 4-Day, or Week view/i),
    ).toBeInTheDocument();
  });

  it("renders calendar emoji decoration", () => {
    const { container } = render(<MonthDeferredState />);
    expect(container.textContent).toContain("📅");
  });
});
