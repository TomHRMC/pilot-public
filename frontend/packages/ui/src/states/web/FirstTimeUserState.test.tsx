/**
 * FirstTimeUserState (web) — unit tests
 * Location: packages/ui/src/states/web/FirstTimeUserState.test.tsx
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { FirstTimeUserState } from "./FirstTimeUserState";
import { FTU_DEFAULTS } from "../types";

const ALL_SURFACES = [
  "dashboard",
  "quotes",
  "schedule",
  "customers",
  "invoices",
  "reports",
  "comms",
  "settings",
] as const;

describe("FirstTimeUserState (web)", () => {
  it.each(ALL_SURFACES)("renders '%s' type with default heading", (surface) => {
    render(<FirstTimeUserState type={surface} />);
    expect(screen.getByText(FTU_DEFAULTS[surface].heading)).toBeTruthy();
  });

  it("overrides heading via headingText prop", () => {
    render(<FirstTimeUserState type="quotes" headingText="Custom heading" />);
    expect(screen.getByText("Custom heading")).toBeTruthy();
  });

  it("overrides body via bodyText prop", () => {
    render(<FirstTimeUserState type="dashboard" bodyText="Custom body copy" />);
    expect(screen.getByText("Custom body copy")).toBeTruthy();
  });

  it("overrides CTA label via ctaLabel prop", () => {
    render(<FirstTimeUserState type="customers" ctaLabel="Custom CTA" />);
    expect(screen.getByText("Custom CTA")).toBeTruthy();
  });

  it("calls onCta when CTA button is clicked", () => {
    const onCta = vi.fn();
    render(<FirstTimeUserState type="dashboard" onCta={onCta} />);
    fireEvent.click(screen.getByText(FTU_DEFAULTS["dashboard"].ctaLabel));
    expect(onCta).toHaveBeenCalledTimes(1);
  });

  it("renders secondary CTA when secondaryCtaLabel provided", () => {
    const onSecondaryCta = vi.fn();
    render(
      <FirstTimeUserState
        type="quotes"
        secondaryCtaLabel="Watch demo"
        onSecondaryCta={onSecondaryCta}
      />,
    );
    fireEvent.click(screen.getByText("Watch demo"));
    expect(onSecondaryCta).toHaveBeenCalledTimes(1);
  });

  it("renders heading as h2 element", () => {
    render(<FirstTimeUserState type="schedule" />);
    const h2 = screen.getByRole("heading", { level: 2 });
    expect(h2).toBeTruthy();
  });

  it("renders section with role='region'", () => {
    render(<FirstTimeUserState type="invoices" />);
    expect(screen.getByRole("region")).toBeTruthy();
  });

  it("applies testID when provided", () => {
    const { container } = render(
      <FirstTimeUserState type="reports" testID="my-ftu" />,
    );
    expect(container.querySelector('[data-testid="my-ftu"]')).toBeTruthy();
  });
});
