/**
 * PasswordResetFlow unit tests — web (FE-B2)
 *
 * Location: apps/web/src/features/login/components/PasswordResetFlow.test.tsx
 *
 * 5 tests per design doc §I.1
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import { PasswordResetFlow } from "./PasswordResetFlow";

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
  fetchAuthSession: vi.fn().mockResolvedValue({ tokens: undefined }),
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

describe("PasswordResetFlow (web)", () => {
  it("step 1: email submitted calls resetPassword and transitions to step 2", async () => {
    const user = userEvent.setup();
    render(<PasswordResetFlow onSuccess={mockOnSuccess} />);

    await user.type(screen.getByLabelText("Email"), "user@example.com");
    await user.click(screen.getByRole("button", { name: /send reset code/i }));

    await waitFor(() => {
      expect(mockResetPassword).toHaveBeenCalled();
      expect(screen.getByLabelText("Verification code")).toBeInTheDocument();
    });
  });

  it("step 2: calls confirmResetPassword with email + code + password", async () => {
    const user = userEvent.setup();
    render(<PasswordResetFlow onSuccess={mockOnSuccess} />);

    // Step 1
    await user.type(screen.getByLabelText("Email"), "user@example.com");
    await user.click(screen.getByRole("button", { name: /send reset code/i }));
    await waitFor(() =>
      expect(screen.getByLabelText("Verification code")).toBeInTheDocument(),
    );

    // Step 2
    await user.type(screen.getByLabelText("Verification code"), "123456");
    await user.type(screen.getByLabelText("New password"), "SecurePass123!");
    await user.type(
      screen.getByLabelText("Confirm new password"),
      "SecurePass123!",
    );
    await user.click(screen.getByRole("button", { name: /reset password/i }));

    await waitFor(() => {
      expect(mockConfirmResetPassword).toHaveBeenCalledWith(
        expect.objectContaining({
          username: "user@example.com",
          confirmationCode: "123456",
          newPassword: "SecurePass123!",
        }),
      );
    });
  });

  it("password mismatch shows error notification", async () => {
    const user = userEvent.setup();
    render(<PasswordResetFlow onSuccess={mockOnSuccess} />);

    // Complete step 1
    await user.type(screen.getByLabelText("Email"), "user@example.com");
    await user.click(screen.getByRole("button", { name: /send reset code/i }));
    await waitFor(() =>
      expect(screen.getByLabelText("Verification code")).toBeInTheDocument(),
    );

    await user.type(screen.getByLabelText("Verification code"), "123456");
    await user.type(screen.getByLabelText("New password"), "SecurePass123!");
    await user.type(
      screen.getByLabelText("Confirm new password"),
      "Different123!",
    );
    await user.click(screen.getByRole("button", { name: /reset password/i }));

    expect(mockAddNotification).toHaveBeenCalledWith(
      expect.objectContaining({
        severity: "error",
        title: "Passwords do not match.",
      }),
    );
  });

  it("transitions to success step after confirmResetPassword succeeds", async () => {
    const user = userEvent.setup();
    render(<PasswordResetFlow onSuccess={mockOnSuccess} />);

    await user.type(screen.getByLabelText("Email"), "user@example.com");
    await user.click(screen.getByRole("button", { name: /send reset code/i }));
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

    await waitFor(() => {
      expect(screen.getByText(/password updated/i)).toBeInTheDocument();
    });
  });

  it("'Resend code' re-calls resetPassword without resetting step 2 inputs", async () => {
    const user = userEvent.setup();
    render(<PasswordResetFlow onSuccess={mockOnSuccess} />);

    // Step 1
    await user.type(screen.getByLabelText("Email"), "user@example.com");
    await user.click(screen.getByRole("button", { name: /send reset code/i }));
    await waitFor(() =>
      expect(screen.getByLabelText("Verification code")).toBeInTheDocument(),
    );

    // Type code
    await user.type(screen.getByLabelText("Verification code"), "999888");

    // Click resend
    await user.click(screen.getByRole("button", { name: /resend code/i }));

    await waitFor(() => {
      // resetPassword called a second time
      expect(mockResetPassword).toHaveBeenCalledTimes(2);
    });

    // Code input still has original value (not reset)
    expect(screen.getByLabelText("Verification code")).toHaveValue("999888");
  });
});
