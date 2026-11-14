/**
 * CharterTierCard unit tests — C-B5
 *
 * Location: apps/web/src/features/signup/components/__tests__/CharterTierCard.test.tsx
 *
 * Verifies:
 *  - Renders free-period callout from free_period_days
 *  - Selected state shows checkmark
 *  - CTA button calls onSelect
 */

import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CharterTierCard } from "../CharterTierCard";
import type { SubscriptionTierAPI } from "../../types";

const charterTier: SubscriptionTierAPI = {
  tier_id: "tier-charter-001",
  tier_name: "charter",
  display_label: "Charter",
  monthly_price_cents: 4900,
  is_trial: false,
  trial_duration_days: null,
  max_users: 12,
  max_sms_segments_per_month: 2000,
  display_order: 0,
  is_active: true,
  free_period_days: 90,
  requires_payment_method: false,
  signup_cap: 12,
};

describe("CharterTierCard", () => {
  it("renders free-period callout from free_period_days", () => {
    render(
      <CharterTierCard
        tier={charterTier}
        isSelected={false}
        onSelect={() => {}}
      />,
    );
    expect(screen.getByTestId("charter-free-period-callout")).toHaveTextContent(
      "Free for 90 days. No card needed.",
    );
  });

  it("selected state shows checkmark", () => {
    const { container } = render(
      <CharterTierCard
        tier={charterTier}
        isSelected={true}
        onSelect={() => {}}
      />,
    );
    // The card has role=radio with aria-checked=true
    const card = screen.getByTestId("charter-tier-card");
    expect(card).toHaveAttribute("aria-checked", "true");
    // The selected checkmark SVG is in the top-right corner
    const checkmark = container.querySelector(
      ".absolute.top-4.right-4 .bg-brand-600",
    );
    expect(checkmark).not.toBeNull();
  });

  it("CTA button calls onSelect", () => {
    const onSelect = vi.fn();
    render(
      <CharterTierCard
        tier={charterTier}
        isSelected={false}
        onSelect={onSelect}
      />,
    );
    const button = screen.getByTestId("charter-tier-select-button");
    fireEvent.click(button);
    expect(onSelect).toHaveBeenCalledTimes(1);
  });
});
