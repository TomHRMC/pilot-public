/**
 * InviteVerifyStep unit tests — TEAM-INVITE-2
 *
 * Location: apps/web/src/features/users/components/__tests__/InviteVerifyStep.test.tsx
 *
 * Verifies:
 *  - Office role: confirmSignUp → signIn → router.replace("/dashboard")
 *  - Technician role: confirmSignUp → no signIn → invite-joined-mobile panel
 *  - CodeMismatchException → inline error
 *  - Resend calls resendSignUpCode + cooldown
 *  - Non-DONE signInStep → router.replace("/login?confirmed=true&email=...")
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { NotificationQueueProvider } from "@pilot/ui/notification-banner";

// ── Hoisted mocks ─────────────────────────────────────────────────────────────
const { mockConfirmSignUp, mockResendSignUpCode, mockSignIn, mockReplace } =
  vi.hoisted(() => ({
    mockConfirmSignUp: vi.fn(),
    mockResendSignUpCode: vi.fn(),
    mockSignIn: vi.fn(),
    mockReplace: vi.fn(),
  }));

vi.mock("aws-amplify/auth", () => ({
  confirmSignUp: mockConfirmSignUp,
  resendSignUpCode: mockResendSignUpCode,
  fetchAuthSession: vi.fn().mockResolvedValue({ tokens: undefined }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: mockReplace, back: vi.fn() }),
}));

import { InviteVerifyStep } from "@/features/users/components/InviteVerifyStep";

function makeAuthValue(): AuthContextValue {
  return {
    user: null,
    isAuthenticated: false,
    role: null,
    signIn: mockSignIn,
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("mock-token"),
  };
}

function renderStep(email: string, password: string, roleCode: string | null) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    <AuthContext.Provider value={makeAuthValue()}>
      <NotificationQueueProvider>
        <QueryClientProvider client={queryClient}>
          <InviteVerifyStep
            email={email}
            password={password}
            roleCode={roleCode}
          />
        </QueryClientProvider>
      </NotificationQueueProvider>
    </AuthContext.Provider>,
  );
}

const EMAIL = "sarah-office@pilot.local";
const PASSWORD = "ValidPass1!xxx";

describe("InviteVerifyStep — TEAM-INVITE-2", () => {
  const originalMockEnv = process.env.NEXT_PUBLIC_USE_MOCK_AUTH;

  beforeEach(() => {
    mockConfirmSignUp.mockReset();
    mockResendSignUpCode.mockReset();
    mockSignIn.mockReset();
    mockReplace.mockReset();
    process.env.NEXT_PUBLIC_USE_MOCK_AUTH = "false";
  });

  afterEach(() => {
    process.env.NEXT_PUBLIC_USE_MOCK_AUTH = originalMockEnv;
  });

  it("office role: confirmSignUp → signIn → router.replace('/dashboard')", async () => {
    mockConfirmSignUp.mockResolvedValue({ isSignUpComplete: true });
    mockSignIn.mockResolvedValue({ nextStep: { signInStep: "DONE" } });

    renderStep(EMAIL, PASSWORD, "office_staff");

    fireEvent.change(screen.getByTestId("invite-code-input"), {
      target: { value: "123456" },
    });
    fireEvent.click(screen.getByTestId("invite-verify-submit"));

    await waitFor(() => expect(mockConfirmSignUp).toHaveBeenCalledTimes(1));
    expect(mockConfirmSignUp).toHaveBeenCalledWith({
      username: EMAIL,
      confirmationCode: "123456",
    });

    await waitFor(() => expect(mockSignIn).toHaveBeenCalledTimes(1));
    expect(mockSignIn).toHaveBeenCalledWith(EMAIL, PASSWORD);

    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith("/dashboard"));
  });

  it("technician role: confirmSignUp → no signIn → invite-joined-mobile panel", async () => {
    mockConfirmSignUp.mockResolvedValue({ isSignUpComplete: true });

    renderStep("newguy@pilot.local", PASSWORD, "technician");

    fireEvent.change(screen.getByTestId("invite-code-input"), {
      target: { value: "123456" },
    });
    fireEvent.click(screen.getByTestId("invite-verify-submit"));

    await waitFor(() => expect(mockConfirmSignUp).toHaveBeenCalledTimes(1));

    await waitFor(() => {
      expect(screen.getByTestId("invite-joined-mobile")).toBeInTheDocument();
    });

    expect(mockSignIn).not.toHaveBeenCalled();
    expect(mockReplace).not.toHaveBeenCalled();
    expect(screen.getByText(/open the pilot mobile app/i)).toBeInTheDocument();
  });

  it("null role: confirmSignUp → no signIn → invite-joined-mobile panel", async () => {
    mockConfirmSignUp.mockResolvedValue({ isSignUpComplete: true });

    renderStep("someone@pilot.local", PASSWORD, null);

    fireEvent.change(screen.getByTestId("invite-code-input"), {
      target: { value: "123456" },
    });
    fireEvent.click(screen.getByTestId("invite-verify-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("invite-joined-mobile")).toBeInTheDocument();
    });
    expect(mockSignIn).not.toHaveBeenCalled();
  });

  it("CodeMismatchException → inline error", async () => {
    const err = new Error("Code mismatch");
    (err as { name: string }).name = "CodeMismatchException";
    mockConfirmSignUp.mockRejectedValue(err);

    renderStep(EMAIL, PASSWORD, "office_staff");

    fireEvent.change(screen.getByTestId("invite-code-input"), {
      target: { value: "000000" },
    });
    fireEvent.click(screen.getByTestId("invite-verify-submit"));

    await waitFor(() => {
      expect(screen.getByText(/that code doesn't match/i)).toBeInTheDocument();
    });
    expect(mockReplace).not.toHaveBeenCalled();
  });

  it("ExpiredCodeException → inline error", async () => {
    const err = new Error("Expired");
    (err as { name: string }).name = "ExpiredCodeException";
    mockConfirmSignUp.mockRejectedValue(err);

    renderStep(EMAIL, PASSWORD, "office_staff");

    fireEvent.change(screen.getByTestId("invite-code-input"), {
      target: { value: "000000" },
    });
    fireEvent.click(screen.getByTestId("invite-verify-submit"));

    await waitFor(() => {
      expect(screen.getByText(/that code expired/i)).toBeInTheDocument();
    });
  });

  it("resend calls resendSignUpCode and shows cooldown", async () => {
    mockResendSignUpCode.mockResolvedValue({});

    renderStep(EMAIL, PASSWORD, "office_staff");

    fireEvent.click(screen.getByTestId("invite-resend-code"));

    await waitFor(() => expect(mockResendSignUpCode).toHaveBeenCalledTimes(1));
    expect(mockResendSignUpCode).toHaveBeenCalledWith({
      username: EMAIL,
    });

    await waitFor(() => {
      expect(screen.getByText(/resend code in 30s/i)).toBeInTheDocument();
    });
  });

  it("non-DONE signInStep → router.replace('/login?confirmed=true&email=...')", async () => {
    mockConfirmSignUp.mockResolvedValue({ isSignUpComplete: true });
    mockSignIn.mockResolvedValue({
      nextStep: { signInStep: "CONTINUE_SIGN_IN_WITH_MFA_SETUP" },
    });

    renderStep(EMAIL, PASSWORD, "office_staff");

    fireEvent.change(screen.getByTestId("invite-code-input"), {
      target: { value: "123456" },
    });
    fireEvent.click(screen.getByTestId("invite-verify-submit"));

    await waitFor(() =>
      expect(mockReplace).toHaveBeenCalledWith(
        `/login?confirmed=true&email=${encodeURIComponent(EMAIL)}`,
      ),
    );
  });

  it("paste is not blocked on the code input (WCAG §36)", () => {
    renderStep(EMAIL, PASSWORD, "office_staff");
    const input = screen.getByTestId("invite-code-input");
    const pasteEvent = new Event("paste", {
      bubbles: true,
      cancelable: true,
    });
    const preventDefaultSpy = vi.spyOn(pasteEvent, "preventDefault");
    fireEvent(input, pasteEvent);
    expect(preventDefaultSpy).not.toHaveBeenCalled();
  });
});
