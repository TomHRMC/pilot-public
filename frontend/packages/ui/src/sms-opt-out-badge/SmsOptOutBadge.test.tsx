/**
 * SmsOptOutBadge — unit tests
 *
 * Location: packages/ui/src/sms-opt-out-badge/SmsOptOutBadge.test.tsx
 *
 * Tests per design doc G.1.
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { SmsOptOutBadge } from "./SmsOptOutBadge";

describe("SmsOptOutBadge", () => {
  it("non-null optedOutAt renders 'SMS opted out · [date]'", () => {
    render(
      <SmsOptOutBadge
        optedOutAt="2026-05-20T10:05:00Z"
        testID="opt-out-badge"
      />,
    );
    const badge = screen.getByTestId("opt-out-badge");
    expect(badge.textContent).toMatch(/SMS opted out/);
    expect(badge.textContent).toMatch(/May 20/);
  });

  it("optedOutAt=null renders 'SMS opted out' without a date", () => {
    render(<SmsOptOutBadge optedOutAt={null} testID="opt-out-badge" />);
    const badge = screen.getByTestId("opt-out-badge");
    expect(badge.textContent).toBe("SMS opted out");
  });

  it("compact=true omits the date", () => {
    render(
      <SmsOptOutBadge
        optedOutAt="2026-05-20T10:05:00Z"
        compact
        testID="opt-out-badge"
      />,
    );
    const badge = screen.getByTestId("opt-out-badge");
    expect(badge.textContent).toBe("SMS opted out");
  });

  it("has fault-color classes for visual treatment", () => {
    const { container } = render(<SmsOptOutBadge optedOutAt={null} />);
    const span = container.querySelector("span");
    expect(span?.className).toContain("bg-fault-50");
    expect(span?.className).toContain("border-fault-200");
  });
});
