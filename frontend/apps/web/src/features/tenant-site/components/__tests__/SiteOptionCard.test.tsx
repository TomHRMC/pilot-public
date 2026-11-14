/**
 * SiteOptionCard — Unit Tests
 *
 * Location: apps/web/src/features/tenant-site/components/__tests__/SiteOptionCard.test.tsx
 *
 * Tests selected/unselected states, disabled card (Option 3), radio semantics.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { SiteOptionCard } from "../SiteOptionCard";

describe("SiteOptionCard", () => {
  it("renders title and description when not selected", () => {
    render(
      <SiteOptionCard
        kind="hosted_compliance"
        title="Hosted Compliance Site"
        description="We host a 3-page site"
        selected={false}
        onSelect={vi.fn()}
      />,
    );
    expect(screen.getByText("Hosted Compliance Site")).toBeInTheDocument();
    expect(screen.getByText("We host a 3-page site")).toBeInTheDocument();
  });

  it("has role=radio and aria-checked=false when not selected", () => {
    render(
      <SiteOptionCard
        kind="compliance_kit"
        title="Compliance Kit"
        description="Self-host"
        selected={false}
        onSelect={vi.fn()}
      />,
    );
    const card = screen.getByTestId("site-option-card-compliance_kit");
    expect(card).toHaveAttribute("role", "radio");
    expect(card).toHaveAttribute("aria-checked", "false");
  });

  it("has aria-checked=true when selected", () => {
    render(
      <SiteOptionCard
        kind="hosted_compliance"
        title="Hosted"
        description="desc"
        selected={true}
        onSelect={vi.fn()}
      />,
    );
    const card = screen.getByTestId("site-option-card-hosted_compliance");
    expect(card).toHaveAttribute("aria-checked", "true");
  });

  it("calls onSelect with kind on click", () => {
    const onSelect = vi.fn();
    render(
      <SiteOptionCard
        kind="compliance_kit"
        title="Kit"
        description="desc"
        selected={false}
        onSelect={onSelect}
      />,
    );
    fireEvent.click(screen.getByTestId("site-option-card-compliance_kit"));
    expect(onSelect).toHaveBeenCalledWith("compliance_kit");
  });

  it("calls onSelect on Enter key", () => {
    const onSelect = vi.fn();
    render(
      <SiteOptionCard
        kind="hosted_compliance"
        title="Hosted"
        description="desc"
        selected={false}
        onSelect={onSelect}
      />,
    );
    const card = screen.getByTestId("site-option-card-hosted_compliance");
    fireEvent.keyDown(card, { key: "Enter" });
    expect(onSelect).toHaveBeenCalledWith("hosted_compliance");
  });

  it("calls onSelect on Space key", () => {
    const onSelect = vi.fn();
    render(
      <SiteOptionCard
        kind="hosted_compliance"
        title="Hosted"
        description="desc"
        selected={false}
        onSelect={onSelect}
      />,
    );
    const card = screen.getByTestId("site-option-card-hosted_compliance");
    fireEvent.keyDown(card, { key: " " });
    expect(onSelect).toHaveBeenCalledWith("hosted_compliance");
  });

  it("renders status badge when provided", () => {
    render(
      <SiteOptionCard
        kind="hosted_compliance"
        title="Hosted"
        description="desc"
        selected={false}
        onSelect={vi.fn()}
        statusBadge={{ text: "Published", className: "bg-margin-100" }}
      />,
    );
    expect(screen.getByText("Published")).toBeInTheDocument();
  });

  it("renders children content", () => {
    render(
      <SiteOptionCard
        kind="compliance_kit"
        title="Kit"
        description="desc"
        selected={false}
        onSelect={vi.fn()}
      >
        <div data-testid="child-content">Panel content</div>
      </SiteOptionCard>,
    );
    expect(screen.getByTestId("child-content")).toBeInTheDocument();
  });

  it("disabled card has aria-disabled=true and does not call onSelect on click", () => {
    const onSelect = vi.fn();
    render(
      <SiteOptionCard
        kind="starter_site"
        title="Starter Site"
        description="Coming soon"
        selected={false}
        disabled
        onSelect={onSelect}
      />,
    );
    const card = screen.getByTestId("site-option-card-starter_site");
    expect(card).toHaveAttribute("aria-disabled", "true");
    expect(card).toHaveAttribute("tabIndex", "-1");
    // Clicking a disabled card should not fire onSelect
    // (the disabled branch doesn't attach onClick)
    fireEvent.click(card);
    expect(onSelect).not.toHaveBeenCalled();
  });
});
