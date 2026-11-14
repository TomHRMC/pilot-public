/**
 * TierPickerCard (web) — unit tests
 * Location: packages/ui/src/tier-picker-card/TierPickerCard.test.tsx
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { TierPickerCard } from "./TierPickerCard";
import type { TierFeature } from "./types";

const BASE_FEATURES: TierFeature[] = [
  { label: "Voice quoting", included: true },
  { label: "QuickBooks sync", included: true, callout: "Bidirectional" },
  { label: "Unlimited technicians", included: false },
];

function renderCard(overrides = {}) {
  return render(
    <TierPickerCard
      tierName="growth"
      displayName="Growth Plan"
      monthlyPriceCents={14900}
      features={BASE_FEATURES}
      onSelect={vi.fn()}
      {...overrides}
    />,
  );
}

describe("TierPickerCard (web)", () => {
  it("renders displayName", () => {
    renderCard();
    expect(screen.getByText("Growth Plan")).toBeTruthy();
  });

  it("renders monthly price formatted as $149/mo", () => {
    renderCard();
    expect(screen.getByText("$149")).toBeTruthy();
    expect(screen.getByText("/mo")).toBeTruthy();
  });

  it("renders feature list with included features", () => {
    renderCard();
    expect(screen.getByText("Voice quoting")).toBeTruthy();
    expect(screen.getByText("QuickBooks sync")).toBeTruthy();
    expect(screen.getByText("Unlimited technicians")).toBeTruthy();
  });

  it("renders callout text when feature.callout provided", () => {
    renderCard();
    expect(screen.getByText("Bidirectional")).toBeTruthy();
  });

  it("isSelected=true applies selected visual treatment (aria-checked='true')", () => {
    const { container } = renderCard({ isSelected: true });
    const card = container.querySelector('[role="radio"]');
    expect(card?.getAttribute("aria-checked")).toBe("true");
  });

  it("isSelected=false sets aria-checked='false'", () => {
    const { container } = renderCard({ isSelected: false });
    const card = container.querySelector('[role="radio"]');
    expect(card?.getAttribute("aria-checked")).toBe("false");
  });

  it("isFeatured=true renders 'Recommended' badge", () => {
    renderCard({ isFeatured: true });
    expect(screen.getByText("Recommended")).toBeTruthy();
  });

  it("isFeatured=false does not render 'Recommended' badge", () => {
    renderCard({ isFeatured: false });
    expect(screen.queryByText("Recommended")).toBeNull();
  });

  it("calls onSelect with tierName when CTA button clicked", () => {
    const onSelect = vi.fn();
    renderCard({ onSelect });
    fireEvent.click(
      screen.getByRole("button", { name: /Select Growth Plan/i }),
    );
    expect(onSelect).toHaveBeenCalledWith("growth");
  });

  it("CTA label override is respected", () => {
    renderCard({ ctaLabel: "Choose this plan" });
    expect(screen.getByText("Choose this plan")).toBeTruthy();
  });

  it("shows 'Selected' as button text when isSelected=true", () => {
    renderCard({ isSelected: true });
    // CTA button displays "Selected" when card is selected
    const buttons = screen.getAllByRole("button");
    const selectedBtn = buttons.find((b) => b.textContent === "Selected");
    expect(selectedBtn).toBeTruthy();
  });

  it("applies testID when provided", () => {
    const { container } = renderCard({ testID: "tier-test" });
    expect(container.querySelector('[data-testid="tier-test"]')).toBeTruthy();
  });
});

// ─── FE-B13 Extended Props Tests ──────────────────────────────────────────────

describe("TierPickerCard — FE-B13 extended props", () => {
  it("isTrialTier=true + trialDurationDays=14 renders FREE and 'for 14 days'", () => {
    renderCard({
      tierName: "trial",
      displayName: "Free Trial",
      monthlyPriceCents: 0,
      isTrialTier: true,
      trialDurationDays: 14,
    });
    expect(screen.getByText("FREE")).toBeTruthy();
    expect(screen.getByText("for 14 days")).toBeTruthy();
  });

  it("isTrialTier=true hides dollar price display", () => {
    renderCard({
      tierName: "trial",
      monthlyPriceCents: 0,
      isTrialTier: true,
    });
    // $0 should not appear — only "FREE"
    expect(screen.queryByText("$0")).toBeNull();
    expect(screen.getByText("FREE")).toBeTruthy();
  });

  it("isCurrentTier=true renders '(current)' label", () => {
    renderCard({
      tierName: "trial",
      monthlyPriceCents: 0,
      isCurrentTier: true,
    });
    expect(screen.getByText("(current)")).toBeTruthy();
  });

  it("isCurrentTier=true does NOT call onSelect when clicked", () => {
    const onSelect = vi.fn();
    const { container } = renderCard({
      tierName: "trial",
      monthlyPriceCents: 0,
      isCurrentTier: true,
      onSelect,
    });
    const card = container.querySelector('[role="radio"]') as HTMLElement;
    fireEvent.click(card);
    expect(onSelect).not.toHaveBeenCalled();
  });

  it("recommendedBadgeLabel overrides default 'Recommended' text", () => {
    renderCard({
      isFeatured: true,
      recommendedBadgeLabel: "Best value",
    });
    expect(screen.getByText("Best value")).toBeTruthy();
    expect(screen.queryByText("Recommended")).toBeNull();
  });

  it("maxUsers=5 renders 'Up to 5 users' in feature list", () => {
    renderCard({ maxUsers: 5 });
    expect(screen.getByText("Up to 5 users")).toBeTruthy();
  });

  it("FE-B1 backward compat: minimal props compile and render without crash", () => {
    // This is the FE-B1 skeleton usage — must still work
    const { container } = render(
      <TierPickerCard
        tierName="growth"
        displayName="Growth Plan"
        monthlyPriceCents={14900}
        features={[{ label: "Voice quoting", included: true }]}
        isSelected={false}
        onSelect={vi.fn()}
      />,
    );
    expect(container.querySelector('[role="radio"]')).toBeTruthy();
  });

  it("open TierName extension: tierName='custom_enterprise' does not throw", () => {
    // TypeScript open extension allows string values beyond the union
    expect(() =>
      renderCard({
        tierName: "custom_enterprise" as string,
        displayName: "Custom Enterprise",
      }),
    ).not.toThrow();
  });
});
