/**
 * EmptyState (web) — unit tests
 * Location: packages/ui/src/states/web/EmptyState.test.tsx
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { EmptyState } from "./EmptyState";
import { EMPTY_STATE_DEFAULTS } from "../types";

describe("EmptyState (web)", () => {
  it("renders 'no-data' type with default title", () => {
    render(<EmptyState type="no-data" />);
    expect(
      screen.getByText(EMPTY_STATE_DEFAULTS["no-data"].title),
    ).toBeTruthy();
  });

  it("renders 'no-results' type with default content", () => {
    render(<EmptyState type="no-results" />);
    expect(
      screen.getByText(EMPTY_STATE_DEFAULTS["no-results"].title),
    ).toBeTruthy();
  });

  it("renders 'not-yet-set-up' type with default content", () => {
    render(<EmptyState type="not-yet-set-up" />);
    expect(
      screen.getByText(EMPTY_STATE_DEFAULTS["not-yet-set-up"].title),
    ).toBeTruthy();
  });

  it("renders 'permission-denied' type with default content", () => {
    render(<EmptyState type="permission-denied" />);
    expect(
      screen.getByText(EMPTY_STATE_DEFAULTS["permission-denied"].title),
    ).toBeTruthy();
  });

  it("renders 'filtered-empty' type with default content", () => {
    render(<EmptyState type="filtered-empty" />);
    expect(
      screen.getByText(EMPTY_STATE_DEFAULTS["filtered-empty"].title),
    ).toBeTruthy();
  });

  it("overrides title via title prop", () => {
    render(<EmptyState type="no-data" title="Custom title" />);
    expect(screen.getByText("Custom title")).toBeTruthy();
  });

  it("overrides description via description prop", () => {
    render(<EmptyState type="no-data" description="Custom description" />);
    expect(screen.getByText("Custom description")).toBeTruthy();
  });

  it("calls onCta when CTA button is clicked", () => {
    const onCta = vi.fn();
    render(<EmptyState type="no-data" ctaLabel="Click me" onCta={onCta} />);
    fireEvent.click(screen.getByText("Click me"));
    expect(onCta).toHaveBeenCalledTimes(1);
  });

  it("renders secondary CTA when secondaryCtaLabel provided", () => {
    const onSecondaryCta = vi.fn();
    render(
      <EmptyState
        type="no-data"
        ctaLabel="Primary"
        onCta={() => {}}
        secondaryCtaLabel="Learn more"
        onSecondaryCta={onSecondaryCta}
      />,
    );
    fireEvent.click(screen.getByText("Learn more"));
    expect(onSecondaryCta).toHaveBeenCalledTimes(1);
  });

  it("does not render CTA button when neither ctaLabel nor onCta provided", () => {
    render(<EmptyState type="no-data" />);
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("renders with role='region' for accessibility", () => {
    render(<EmptyState type="no-data" />);
    expect(screen.getByRole("region")).toBeTruthy();
  });

  it("applies testID to root element", () => {
    const { container } = render(
      <EmptyState type="no-data" testID="my-empty" />,
    );
    expect(container.querySelector('[data-testid="my-empty"]')).toBeTruthy();
  });

  it("defaults testID based on type when not provided", () => {
    const { container } = render(<EmptyState type="no-data" />);
    expect(
      container.querySelector('[data-testid="empty-state-no-data"]'),
    ).toBeTruthy();
  });
});
