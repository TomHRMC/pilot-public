/**
 * HelpAnchor unit tests — FE-B16
 *
 * Location: packages/ui/src/help-anchor/HelpAnchor.test.tsx
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { HelpAnchor } from "./web/HelpAnchor";
import type { HelpContextPayload } from "./types";

const mockPayload: HelpContextPayload = {
  route: "/settings/integrations/quickbooks",
  anchor_id: "qb-auto-expire",
  entity_type: null,
  recent_actions: ["opened_settings"],
  user_role: "owner",
  tenant_metadata: { size: "small", trade: "electrical" },
};

describe("HelpAnchor (web)", () => {
  it("renders with correct aria-label (default)", () => {
    const onOpen = vi.fn();
    render(<HelpAnchor contextPayload={mockPayload} onOpen={onOpen} />);
    expect(
      screen.getByRole("button", { name: "Open contextual help" }),
    ).toBeInTheDocument();
  });

  it("renders with custom label", () => {
    const onOpen = vi.fn();
    render(
      <HelpAnchor
        contextPayload={mockPayload}
        onOpen={onOpen}
        label="Help with sync direction"
      />,
    );
    expect(
      screen.getByRole("button", { name: "Help with sync direction" }),
    ).toBeInTheDocument();
  });

  it("calls onOpen with contextPayload when clicked", () => {
    const onOpen = vi.fn();
    render(<HelpAnchor contextPayload={mockPayload} onOpen={onOpen} />);
    fireEvent.click(screen.getByRole("button"));
    expect(onOpen).toHaveBeenCalledWith(mockPayload);
    expect(onOpen).toHaveBeenCalledTimes(1);
  });

  it("applies 'sm' size class", () => {
    const onOpen = vi.fn();
    render(
      <HelpAnchor contextPayload={mockPayload} onOpen={onOpen} size="sm" />,
    );
    const btn = screen.getByRole("button");
    expect(btn.className).toContain("h-4");
  });

  it("applies 'md' size class", () => {
    const onOpen = vi.fn();
    render(
      <HelpAnchor contextPayload={mockPayload} onOpen={onOpen} size="md" />,
    );
    const btn = screen.getByRole("button");
    expect(btn.className).toContain("h-5");
  });

  it("applies neutral-400 / brand-600-hover tokens", () => {
    const onOpen = vi.fn();
    render(<HelpAnchor contextPayload={mockPayload} onOpen={onOpen} />);
    const btn = screen.getByRole("button");
    expect(btn.className).toContain("text-neutral-400");
    expect(btn.className).toContain("hover:text-brand-600");
  });

  it("uses testId prop for data-testid attribute", () => {
    const onOpen = vi.fn();
    render(
      <HelpAnchor
        contextPayload={mockPayload}
        onOpen={onOpen}
        testId="qb-help-anchor"
      />,
    );
    expect(screen.getByTestId("qb-help-anchor")).toBeInTheDocument();
  });

  it("stops propagation on click (does not bubble)", () => {
    const onOpen = vi.fn();
    const parentClick = vi.fn();
    render(
      <div onClick={parentClick}>
        <HelpAnchor contextPayload={mockPayload} onOpen={onOpen} />
      </div>,
    );
    fireEvent.click(screen.getByRole("button"));
    expect(onOpen).toHaveBeenCalled();
    expect(parentClick).not.toHaveBeenCalled();
  });
});
