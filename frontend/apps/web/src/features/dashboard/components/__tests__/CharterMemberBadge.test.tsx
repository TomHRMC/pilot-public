/**
 * CharterMemberBadge unit tests — C-B5
 *
 * Location: apps/web/src/features/dashboard/components/__tests__/CharterMemberBadge.test.tsx
 *
 * Verifies:
 *  - Renders "Charter Member #N" + "Free until {date}"
 *  - Returns null when charterMemberNumber is null
 *  - Omits "Free until" when freePeriodEndsAt is null
 */

import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { CharterMemberBadge } from "../CharterMemberBadge";

const freePeriodEndsAt = "2026-11-02T18:37:42Z";

describe("CharterMemberBadge", () => {
  it("renders member number + free until date", () => {
    render(
      <CharterMemberBadge
        charterMemberNumber={7}
        freePeriodEndsAt={freePeriodEndsAt}
      />,
    );
    const badge = screen.getByTestId("charter-member-badge");
    expect(badge).toHaveTextContent("Charter Member #7");
    expect(badge).toHaveTextContent("Free until Nov 2, 2026");
    // aria-label includes both pieces
    expect(badge).toHaveAttribute(
      "aria-label",
      "Charter Member number 7, free until Nov 2, 2026",
    );
  });

  it("returns null when charterMemberNumber is null", () => {
    const { container } = render(
      <CharterMemberBadge
        charterMemberNumber={null as unknown as number}
        freePeriodEndsAt={freePeriodEndsAt}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("omits Free until when freePeriodEndsAt is null", () => {
    render(
      <CharterMemberBadge charterMemberNumber={3} freePeriodEndsAt={null} />,
    );
    const badge = screen.getByTestId("charter-member-badge");
    expect(badge).toHaveTextContent("Charter Member #3");
    expect(badge).not.toHaveTextContent("Free until");
    expect(badge).toHaveAttribute("aria-label", "Charter Member number 3");
  });
});
