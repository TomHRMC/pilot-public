/**
 * Step5Confirmation unit tests — C-B5
 *
 * Location: apps/web/src/features/signup/components/__tests__/Step5Confirmation.test.tsx
 *
 * Verifies:
 *  - Renders "You are set. No charge until {date}." with formatted date
 *  - Complete Signup button calls onConfirm
 *  - Submitting state shows "Setting up..."
 */

import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Step5Confirmation } from "../Step5Confirmation";

const freePeriodEndsAt = "2026-11-02T18:37:42Z";

describe("Step5Confirmation", () => {
  it("renders confirmation callout with formatted date", () => {
    render(
      <Step5Confirmation
        freePeriodEndsAt={freePeriodEndsAt}
        ownerName="Mike"
        onConfirm={() => {}}
        isSubmitting={false}
        submitError={null}
      />,
    );
    const callout = screen.getByTestId("charter-confirmation-callout");
    // The formatted date should be "Nov 2, 2026"
    expect(callout).toHaveTextContent("Nov 2, 2026");
    expect(callout).toHaveTextContent("No charge until");
  });

  it("Complete Signup button calls onConfirm", () => {
    const onConfirm = vi.fn();
    render(
      <Step5Confirmation
        freePeriodEndsAt={freePeriodEndsAt}
        ownerName="Mike"
        onConfirm={onConfirm}
        isSubmitting={false}
        submitError={null}
      />,
    );
    const button = screen.getByTestId("step5-confirmation-complete");
    fireEvent.click(button);
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it("submitting state shows Setting up...", () => {
    render(
      <Step5Confirmation
        freePeriodEndsAt={freePeriodEndsAt}
        ownerName="Mike"
        onConfirm={() => {}}
        isSubmitting={true}
        submitError={null}
      />,
    );
    const button = screen.getByTestId("step5-confirmation-complete");
    expect(button).toHaveTextContent("Setting up");
    expect(button).toBeDisabled();
  });
});
