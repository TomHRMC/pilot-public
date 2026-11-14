/**
 * ExpiryCountdownBadge unit tests
 */

import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ExpiryCountdownBadge } from "./ExpiryCountdownBadge";

describe("<ExpiryCountdownBadge>", () => {
  it("renders nothing when daysUntilExpiry is null", () => {
    const { container } = render(
      <ExpiryCountdownBadge daysUntilExpiry={null} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when daysUntilExpiry is undefined", () => {
    const { container } = render(
      <ExpiryCountdownBadge daysUntilExpiry={undefined} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders amber token classes when daysUntilExpiry > 3", () => {
    const { container } = render(<ExpiryCountdownBadge daysUntilExpiry={5} />);
    const span = container.querySelector("span");
    expect(span?.className).toContain("bg-alert-50");
    expect(span?.className).toContain("border-alert-200");
    expect(span?.className).toContain("text-alert-600");
    // Must NOT have fault classes
    expect(span?.className).not.toContain("bg-fault-50");
  });

  it("renders red token classes when daysUntilExpiry === 3 (boundary)", () => {
    const { container } = render(<ExpiryCountdownBadge daysUntilExpiry={3} />);
    const span = container.querySelector("span");
    expect(span?.className).toContain("bg-fault-50");
    expect(span?.className).toContain("border-fault-200");
    expect(span?.className).toContain("text-fault-600");
    expect(span?.className).not.toContain("bg-alert-50");
  });

  it("renders red token classes when daysUntilExpiry < 3", () => {
    const { container } = render(<ExpiryCountdownBadge daysUntilExpiry={1} />);
    const span = container.querySelector("span");
    expect(span?.className).toContain("bg-fault-50");
    expect(span?.className).toContain("text-fault-600");
  });

  it("renders 'Auto-resolves in 7 days' for days=7", () => {
    render(<ExpiryCountdownBadge daysUntilExpiry={7} />);
    expect(screen.getByText("Auto-resolves in 7 days")).toBeInTheDocument();
  });

  it("renders 'Auto-resolves in 1 day' (singular) for days=1", () => {
    render(<ExpiryCountdownBadge daysUntilExpiry={1} />);
    expect(screen.getByText("Auto-resolves in 1 day")).toBeInTheDocument();
  });

  it("renders 'Auto-resolves today' for days=0", () => {
    render(<ExpiryCountdownBadge daysUntilExpiry={0} />);
    expect(screen.getByText("Auto-resolves today")).toBeInTheDocument();
  });

  it("has role=status for screen reader announcement", () => {
    render(<ExpiryCountdownBadge daysUntilExpiry={5} />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("uses custom testID when provided", () => {
    render(
      <ExpiryCountdownBadge daysUntilExpiry={5} testID="custom-expiry-badge" />,
    );
    expect(screen.getByTestId("custom-expiry-badge")).toBeInTheDocument();
  });
});
