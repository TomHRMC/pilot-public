/**
 * DeviationBadge — Unit Tests
 *
 * Location: apps/web/src/features/wip/components/__tests__/DeviationBadge.test.tsx
 *
 * Verifies each of the 4 variants renders the correct icon + text label.
 * Asserts by text/data-testid (not color) — the color-independence proof.
 *
 * Per batch-up-1-react-engr-prompt.md Test Requirements.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { DeviationBadge, selectDeviationVariant } from "../DeviationBadge";

const MARGIN_TARGET_PCT = 20.0;

describe("selectDeviationVariant", () => {
  it("returns 'none' when deviation is null", () => {
    expect(selectDeviationVariant(null, false, MARGIN_TARGET_PCT)).toBe("none");
  });

  it("returns 'over' when deviation < 0", () => {
    expect(selectDeviationVariant(-5.0, true, MARGIN_TARGET_PCT)).toBe("over");
  });

  it("returns 'under' when 0 <= deviation < (100 - margin_target) and not below target", () => {
    expect(selectDeviationVariant(50.0, false, MARGIN_TARGET_PCT)).toBe(
      "under",
    );
  });

  it("returns 'watch' when deviation >= (100 - margin_target) and below_margin_target", () => {
    // threshold = 100 - 20 = 80; deviation 85 >= 80 and below_margin_target true
    expect(selectDeviationVariant(85.0, true, MARGIN_TARGET_PCT)).toBe("watch");
  });

  it("returns 'under' when deviation >= threshold but below_margin_target is false", () => {
    expect(selectDeviationVariant(85.0, false, MARGIN_TARGET_PCT)).toBe(
      "under",
    );
  });
});

describe("DeviationBadge", () => {
  it("renders 'over' variant with correct text label", () => {
    render(
      <DeviationBadge
        budgetDeviationPct={-8.33}
        belowMarginTarget={true}
        marginTargetPct={MARGIN_TARGET_PCT}
      />,
    );
    expect(screen.getByTestId("deviation-badge-over")).toBeTruthy();
    expect(screen.getByText("8.3% over")).toBeTruthy();
  });

  it("renders 'under' variant with correct text label", () => {
    render(
      <DeviationBadge
        budgetDeviationPct={41.67}
        belowMarginTarget={false}
        marginTargetPct={MARGIN_TARGET_PCT}
      />,
    );
    expect(screen.getByTestId("deviation-badge-under")).toBeTruthy();
    expect(screen.getByText("41.7% under")).toBeTruthy();
  });

  it("renders 'watch' variant with correct text label", () => {
    // watch: deviation >= (100 - margin_target_pct=20) = 80, AND below_margin_target=true
    render(
      <DeviationBadge
        budgetDeviationPct={85.0}
        belowMarginTarget={true}
        marginTargetPct={MARGIN_TARGET_PCT}
      />,
    );
    expect(screen.getByTestId("deviation-badge-watch")).toBeTruthy();
    expect(screen.getByText("85.0% under")).toBeTruthy();
  });

  it("renders 'none' variant with 'No quote' label", () => {
    render(
      <DeviationBadge
        budgetDeviationPct={null}
        belowMarginTarget={false}
        marginTargetPct={MARGIN_TARGET_PCT}
      />,
    );
    expect(screen.getByTestId("deviation-badge-none")).toBeTruthy();
    expect(screen.getByText("No quote")).toBeTruthy();
  });

  it("icons have aria-hidden=true (text carries meaning)", () => {
    const { container } = render(
      <DeviationBadge
        budgetDeviationPct={-5.0}
        belowMarginTarget={true}
        marginTargetPct={MARGIN_TARGET_PCT}
      />,
    );
    const icons = container.querySelectorAll("svg[aria-hidden='true']");
    expect(icons.length).toBeGreaterThanOrEqual(1);
  });
});
