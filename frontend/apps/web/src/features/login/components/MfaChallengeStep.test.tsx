/**
 * MfaChallengeStep unit tests — web (FE-B2)
 *
 * Location: apps/web/src/features/login/components/MfaChallengeStep.test.tsx
 *
 * 6 tests per design doc §I.1
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import { MfaChallengeStep } from "./MfaChallengeStep";

const mockOnConfirm = vi.fn();
const mockOnCancel = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();
  mockOnConfirm.mockResolvedValue(undefined);
});

describe("MfaChallengeStep (web)", () => {
  it("renders correct copy for TOTP challenge", () => {
    render(
      <MfaChallengeStep
        challengeName="TOTP"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />,
    );
    expect(screen.getByText(/authenticator app/i)).toBeInTheDocument();
  });

  it("renders correct copy for SMS_MFA challenge", () => {
    render(
      <MfaChallengeStep
        challengeName="SMS_MFA"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />,
    );
    expect(screen.getByText(/sent to your phone/i)).toBeInTheDocument();
  });

  it("renders correct copy for EMAIL_OTP challenge", () => {
    render(
      <MfaChallengeStep
        challengeName="EMAIL_OTP"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />,
    );
    expect(screen.getByText(/sent to your email/i)).toBeInTheDocument();
  });

  it("code input accepts 6 digits", async () => {
    const user = userEvent.setup();
    render(
      <MfaChallengeStep
        challengeName="TOTP"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />,
    );
    const input = screen.getByLabelText("Verification code");
    await user.type(input, "123456");
    expect(input).toHaveValue("123456");
  });

  it("submit calls onConfirm with entered code", async () => {
    const user = userEvent.setup();
    render(
      <MfaChallengeStep
        challengeName="TOTP"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />,
    );
    await user.type(screen.getByLabelText("Verification code"), "654321");
    await user.click(screen.getByRole("button", { name: /verify/i }));
    await waitFor(() => {
      expect(mockOnConfirm).toHaveBeenCalledWith("654321");
    });
  });

  it("cancel button calls onCancel", async () => {
    const user = userEvent.setup();
    render(
      <MfaChallengeStep
        challengeName="TOTP"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />,
    );
    await user.click(screen.getByRole("button", { name: /cancel/i }));
    expect(mockOnCancel).toHaveBeenCalled();
  });

  it("'use recovery code' expands free-text input", async () => {
    const user = userEvent.setup();
    render(
      <MfaChallengeStep
        challengeName="TOTP"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />,
    );
    await user.click(screen.getByRole("button", { name: /recovery code/i }));
    expect(screen.getByLabelText("Recovery code")).toBeInTheDocument();
  });

  it("shows error message on rejection", async () => {
    render(
      <MfaChallengeStep
        challengeName="TOTP"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
        error="Incorrect code. Try again."
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Incorrect code. Try again.",
    );
  });
});
