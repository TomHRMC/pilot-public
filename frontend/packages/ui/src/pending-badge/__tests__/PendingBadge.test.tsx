/**
 * PendingBadge Unit Tests
 *
 * Location: packages/ui/src/pending-badge/__tests__/PendingBadge.test.tsx
 *
 * Tests: count=0 renders null; all 4 variants; onPress fires; ARIA label; testID present
 * Per batch-fe-b7-design.md Section I.1.
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { vi } from "vitest";
import { PendingBadge } from "../web/PendingBadge";
import type { PendingBadgeVariant } from "../types";

describe("PendingBadge (web)", () => {
  it("renders null when count is 0", () => {
    const { container } = render(<PendingBadge count={0} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders badge when count > 0", () => {
    render(<PendingBadge count={3} />);
    expect(screen.getByText("3")).toBeDefined();
  });

  it("caps display at 99+ for count > 99", () => {
    render(<PendingBadge count={150} />);
    expect(screen.getByText("99+")).toBeDefined();
  });

  const variants: PendingBadgeVariant[] = [
    "pending",
    "syncing",
    "failed",
    "conflict",
  ];
  it.each(variants)("renders variant=%s without error", (variant) => {
    const { container } = render(<PendingBadge count={1} variant={variant} />);
    expect(container.firstChild).not.toBeNull();
  });

  it("applies default pending variant when no variant provided", () => {
    render(<PendingBadge count={1} testID="badge" />);
    const badge = screen.getByTestId("badge");
    expect(badge).toBeDefined();
    // Default pending has amber class
    expect(badge.className).toContain("bg-alert-400");
  });

  it("applies correct class for failed variant", () => {
    render(<PendingBadge count={2} variant="failed" testID="badge-failed" />);
    const badge = screen.getByTestId("badge-failed");
    expect(badge.className).toContain("bg-fault-600");
  });

  it("applies animate-pulse for syncing variant", () => {
    render(<PendingBadge count={1} variant="syncing" testID="badge-syncing" />);
    const badge = screen.getByTestId("badge-syncing");
    expect(badge.className).toContain("animate-pulse");
  });

  it("fires onPress when tapped", () => {
    const onPress = vi.fn();
    render(<PendingBadge count={2} onPress={onPress} testID="badge-press" />);
    const button = screen.getByTestId("badge-press");
    fireEvent.click(button);
    expect(onPress).toHaveBeenCalledTimes(1);
  });

  it("renders a button element when onPress is provided", () => {
    render(<PendingBadge count={1} onPress={() => {}} />);
    const buttons = screen.getAllByRole("button");
    expect(buttons.length).toBeGreaterThan(0);
  });

  it("uses custom accessibilityLabel when provided", () => {
    render(
      <PendingBadge count={5} accessibilityLabel="5 items need attention" />,
    );
    const el = screen.getByLabelText("5 items need attention");
    expect(el).toBeDefined();
  });

  it("defaults accessibilityLabel to '{count} pending sync'", () => {
    render(<PendingBadge count={3} />);
    const el = screen.getByLabelText("3 pending sync");
    expect(el).toBeDefined();
  });

  it("applies extra className to span", () => {
    render(<PendingBadge count={1} className="my-class" testID="badge-cls" />);
    const badge = screen.getByTestId("badge-cls");
    expect(badge.className).toContain("my-class");
  });
});
