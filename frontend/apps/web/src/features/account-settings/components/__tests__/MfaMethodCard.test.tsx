/**
 * MfaMethodCard unit tests — MFA-WIRE-1 Part B (spec §2.3, §2.4)
 *
 * Location: apps/web/src/features/account-settings/components/__tests__/MfaMethodCard.test.tsx
 */
import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { MfaMethodCard } from "../MfaMethodCard";

// Mock @pilot/ui PendingBadge
vi.mock("@pilot/ui", () => ({
  PendingBadge: ({
    count,
    accessibilityLabel,
    className,
  }: {
    count: number;
    accessibilityLabel?: string;
    className?: string;
  }) => (
    <span
      data-testid="pending-badge"
      data-count={count}
      aria-label={accessibilityLabel}
      className={className}
    >
      Pending
    </span>
  ),
}));

const totpMethod = {
  method_id: "mfa-method-totp",
  method_type: "totp",
  enrolled_at: "2026-08-10T12:00:00.000Z",
  last_used_at: null,
  destination_masked: null,
};

const smsMethod = {
  method_id: "mfa-method-sms",
  method_type: "sms",
  enrolled_at: "2026-08-10T12:00:00.000Z",
  last_used_at: null,
  destination_masked: "••••0001",
};

describe("MfaMethodCard", () => {
  it("renders TOTP card with 'Authenticator app' label", () => {
    render(
      <MfaMethodCard
        method={totpMethod}
        isPending={false}
        onRemove={() => {}}
      />,
    );
    expect(screen.getByText("Authenticator app")).toBeInTheDocument();
    expect(screen.getByTestId("mfa-method-card-totp")).toBeInTheDocument();
  });

  it("renders SMS card with 'Text message' label and destination_masked", () => {
    render(
      <MfaMethodCard
        method={smsMethod}
        isPending={false}
        onRemove={() => {}}
      />,
    );
    expect(screen.getByText("Text message")).toBeInTheDocument();
    expect(screen.getByTestId("mfa-method-card-sms")).toBeInTheDocument();
    expect(screen.getByText(/••••0001/)).toBeInTheDocument();
  });

  it("does NOT render destination_masked for TOTP", () => {
    render(
      <MfaMethodCard
        method={totpMethod}
        isPending={false}
        onRemove={() => {}}
      />,
    );
    expect(screen.queryByText(/••••/)).not.toBeInTheDocument();
  });

  it("renders Remove button with correct aria-label", () => {
    render(
      <MfaMethodCard
        method={totpMethod}
        isPending={false}
        onRemove={() => {}}
      />,
    );
    const removeBtn = screen.getByTestId("mfa-method-remove-totp");
    expect(removeBtn).toBeInTheDocument();
    expect(removeBtn).toHaveAttribute(
      "aria-label",
      "Remove Authenticator app method",
    );
  });

  it("renders pending state with dim, badge, and aria-busy", () => {
    render(
      <MfaMethodCard
        method={totpMethod}
        isPending={true}
        onRemove={() => {}}
      />,
    );
    const card = screen.getByTestId("mfa-method-card-totp-pending");
    expect(card).toHaveAttribute("aria-busy", "true");
    expect(card.className).toContain("opacity-60");
    expect(card.className).toContain("pointer-events-none");
    expect(screen.getByTestId("pending-badge")).toBeInTheDocument();
    // Remove button hidden when pending
    expect(
      screen.queryByTestId("mfa-method-remove-totp"),
    ).not.toBeInTheDocument();
  });

  it("does NOT render last_used_at even when provided", () => {
    const methodWithLastUsed = {
      ...totpMethod,
      last_used_at: "2026-08-15T10:00:00.000Z",
    };
    render(
      <MfaMethodCard
        method={methodWithLastUsed}
        isPending={false}
        onRemove={() => {}}
      />,
    );
    // The secondary line should only contain "Enrolled ..." — no "Last used"
    expect(screen.queryByText(/last used/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/never used/i)).not.toBeInTheDocument();
  });
});
