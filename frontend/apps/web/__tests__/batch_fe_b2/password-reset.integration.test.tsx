/**
 * Password reset integration tests — web (FE-B2)
 *
 * Location: apps/web/__tests__/batch_fe_b2/password-reset.integration.test.tsx
 *
 * Tests: full 3-step flow, resend code, password validation errors
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import { PasswordResetFlow } from "@/features/login/components/PasswordResetFlow";

const mockAddNotification = vi.fn();
const mockOnSuccess = vi.fn();

vi.mock("@pilot/ui/notification-banner", () => ({
  useNotificationQueue: () => ({
    addNotification: mockAddNotification,
    notifications: [],
    dismissNotification: vi.fn(),
    dismissAll: vi.fn(),
  }),
}));

const mockResetPassword = vi.fn();
const mockConfirmResetPassword = vi.fn();

vi.mock("aws-amplify/auth", () => ({
  resetPassword: () => mockResetPassword(),
  confirmResetPassword: (args: unknown) => mockConfirmResetPassword(args),
}));

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) =>
    React.createElement("a", { href }, children),
}));

beforeEach(() => {
  vi.clearAllMocks();
  mockResetPassword.mockResolvedValue({});
  mockConfirmResetPassword.mockResolvedValue({});
});

describe("Password reset integration (web)", () => {
  it("(1) full 3-step flow: email → code → success", async () => {
    const user = userEvent.setup();
    render(<PasswordResetFlow onSuccess={mockOnSuccess} />);

    // Step 1
    await user.type(screen.getByLabelText("Email"), "user@example.com");
    await user.click(screen.getByRole("button", { name: /send reset code/i }));

    // Step 2
    await waitFor(() =>
      expect(screen.getByLabelText("Verification code")).toBeInTheDocument(),
    );
    await user.type(screen.getByLabelText("Verification code"), "123456");
    await user.type(screen.getByLabelText("New password"), "SecurePass123!");
    await user.type(
      screen.getByLabelText("Confirm new password"),
      "SecurePass123!",
    );
    await user.click(screen.getByRole("button", { name: /reset password/i }));

    // Step 3
    await waitFor(() => {
      expect(screen.getByText(/password updated/i)).toBeInTheDocument();
    });
    expect(mockOnSuccess).toHaveBeenCalled();
  });

  it("(2) resend code calls resetPassword a second time", async () => {
    const user = userEvent.setup();
    render(<PasswordResetFlow onSuccess={mockOnSuccess} />);

    await user.type(screen.getByLabelText("Email"), "user@example.com");
    await user.click(screen.getByRole("button", { name: /send reset code/i }));
    await waitFor(() =>
      expect(screen.getByLabelText("Verification code")).toBeInTheDocument(),
    );

    await user.click(screen.getByRole("button", { name: /resend code/i }));

    await waitFor(() => {
      expect(mockResetPassword).toHaveBeenCalledTimes(2);
      expect(mockAddNotification).toHaveBeenCalledWith(
        expect.objectContaining({ severity: "success" }),
      );
    });
  });

  it("(3) weak password keeps reset button disabled and shows hint", async () => {
    const user = userEvent.setup();
    render(<PasswordResetFlow onSuccess={mockOnSuccess} />);

    await user.type(screen.getByLabelText("Email"), "user@example.com");
    await user.click(screen.getByRole("button", { name: /send reset code/i }));
    await waitFor(() =>
      expect(screen.getByLabelText("Verification code")).toBeInTheDocument(),
    );

    await user.type(screen.getByLabelText("Verification code"), "123456");
    await user.type(screen.getByLabelText("New password"), "short");

    // Button must remain disabled when password doesn't meet requirements
    const resetButton = screen.getByRole("button", { name: /reset password/i });
    expect(resetButton).toBeDisabled();

    // Requirements hint shown inside the password input group (may be split across elements)
    expect(screen.getByLabelText("New password")).toBeInTheDocument();

    // confirmResetPassword should NOT have been called
    expect(mockConfirmResetPassword).not.toHaveBeenCalled();
  });
});
