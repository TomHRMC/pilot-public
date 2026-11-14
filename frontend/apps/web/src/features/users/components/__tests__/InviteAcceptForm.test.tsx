/**
 * InviteAcceptForm unit tests — TEAM-INVITE-2
 *
 * Location: apps/web/src/features/users/components/__tests__/InviteAcceptForm.test.tsx
 *
 * Verifies:
 *  - Renders invited email + both password inputs + policy hint
 *  - Zod rejects <12 chars / missing symbol / mismatched confirm
 *  - Happy path: valid passwords → submit → onSignedUp called with password
 *  - UsernameExistsException → "Sign in instead" link
 *  - Paste is not blocked (WCAG §36)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// ── Hoisted mocks ─────────────────────────────────────────────────────────────
const { mockMutateAsync } = vi.hoisted(() => ({
  mockMutateAsync: vi.fn(),
}));

vi.mock("@/features/signup/hooks/useCognitoSignUp", () => ({
  useCognitoSignUp: () => ({
    mutateAsync: mockMutateAsync,
    isError: false,
    error: null,
  }),
  CognitoSignUpError: class CognitoSignUpError extends Error {
    code: string;
    constructor(code: string, message: string) {
      super(message);
      this.name = "CognitoSignUpError";
      this.code = code;
    }
  },
}));

import { InviteAcceptForm } from "@/features/users/components/InviteAcceptForm";
import { CognitoSignUpError } from "@/features/signup/hooks/useCognitoSignUp";

function renderForm(
  email: string,
  onSignedUp: (password: string) => void = vi.fn(),
) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <InviteAcceptForm email={email} onSignedUp={onSignedUp} />
    </QueryClientProvider>,
  );
}

const VALID_PASSWORD = "ValidPass1!xxx";

describe("InviteAcceptForm — TEAM-INVITE-2", () => {
  const originalMockEnv = process.env.NEXT_PUBLIC_USE_MOCK_AUTH;

  beforeEach(() => {
    mockMutateAsync.mockReset();
    process.env.NEXT_PUBLIC_USE_MOCK_AUTH = "true";
  });

  afterEach(() => {
    process.env.NEXT_PUBLIC_USE_MOCK_AUTH = originalMockEnv;
  });

  it("renders the invited email, both password inputs, and the policy hint", () => {
    renderForm("newguy@pilot.local");

    expect(screen.getByText("newguy@pilot.local")).toBeInTheDocument();
    expect(screen.getByTestId("invite-password-input")).toBeInTheDocument();
    expect(
      screen.getByTestId("invite-confirm-password-input"),
    ).toBeInTheDocument();
    expect(screen.getByText(/at least 12 characters/i)).toBeInTheDocument();
  });

  it("Zod rejects passwords shorter than 12 chars (submit does not call mutation)", async () => {
    const onSignedUp = vi.fn();
    renderForm("newguy@pilot.local", onSignedUp);

    fireEvent.change(screen.getByTestId("invite-password-input"), {
      target: { value: "Short1!" },
    });
    fireEvent.change(screen.getByTestId("invite-confirm-password-input"), {
      target: { value: "Short1!" },
    });
    fireEvent.click(screen.getByTestId("invite-accept-submit"));

    await waitFor(() => {
      expect(screen.getByText(/at least 12 characters/i)).toBeInTheDocument();
    });
    expect(mockMutateAsync).not.toHaveBeenCalled();
    expect(onSignedUp).not.toHaveBeenCalled();
  });

  it("Zod rejects missing symbol", async () => {
    renderForm("newguy@pilot.local");

    fireEvent.change(screen.getByTestId("invite-password-input"), {
      target: { value: "NoSymbol12345" },
    });
    fireEvent.change(screen.getByTestId("invite-confirm-password-input"), {
      target: { value: "NoSymbol12345" },
    });
    fireEvent.click(screen.getByTestId("invite-accept-submit"));

    await waitFor(() => {
      expect(screen.getByText(/at least one symbol/i)).toBeInTheDocument();
    });
    expect(mockMutateAsync).not.toHaveBeenCalled();
  });

  it("Zod rejects mismatched confirm password", async () => {
    renderForm("newguy@pilot.local");

    fireEvent.change(screen.getByTestId("invite-password-input"), {
      target: { value: VALID_PASSWORD },
    });
    fireEvent.change(screen.getByTestId("invite-confirm-password-input"), {
      target: { value: "DifferentPass1!xx" },
    });
    fireEvent.click(screen.getByTestId("invite-accept-submit"));

    await waitFor(() => {
      expect(screen.getByText(/passwords do not match/i)).toBeInTheDocument();
    });
    expect(mockMutateAsync).not.toHaveBeenCalled();
  });

  it("happy path: valid passwords → submit → onSignedUp called with the password", async () => {
    const onSignedUp = vi.fn();
    mockMutateAsync.mockResolvedValue({
      isSignUpComplete: false,
      userId: "mock-user-id",
      nextStep: { signUpStep: "CONFIRM_SIGN_UP" },
    });

    renderForm("newguy@pilot.local", onSignedUp);

    fireEvent.change(screen.getByTestId("invite-password-input"), {
      target: { value: VALID_PASSWORD },
    });
    fireEvent.change(screen.getByTestId("invite-confirm-password-input"), {
      target: { value: VALID_PASSWORD },
    });
    fireEvent.click(screen.getByTestId("invite-accept-submit"));

    await waitFor(() => expect(onSignedUp).toHaveBeenCalledTimes(1));
    expect(onSignedUp).toHaveBeenCalledWith(VALID_PASSWORD);
  });

  it("UsernameExistsException → 'Sign in instead' link with href=/login?email=...", async () => {
    mockMutateAsync.mockRejectedValue(
      new CognitoSignUpError("UsernameExistsException", "User already exists"),
    );

    renderForm("sarah-office@pilot.local");

    fireEvent.change(screen.getByTestId("invite-password-input"), {
      target: { value: VALID_PASSWORD },
    });
    fireEvent.change(screen.getByTestId("invite-confirm-password-input"), {
      target: { value: VALID_PASSWORD },
    });
    fireEvent.click(screen.getByTestId("invite-accept-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("invite-accept-error")).toBeInTheDocument();
    });

    expect(
      screen.getByText(/an account already exists for/i),
    ).toBeInTheDocument();

    const signInLink = screen.getByTestId("invite-signin-instead");
    expect(signInLink).toBeInTheDocument();
    expect(signInLink.getAttribute("href")).toBe(
      "/login?email=sarah-office%40pilot.local",
    );
  });

  it("LimitExceededException → 'Too many attempts' error", async () => {
    mockMutateAsync.mockRejectedValue(
      new CognitoSignUpError("LimitExceededException", "Too many requests"),
    );

    renderForm("newguy@pilot.local");

    fireEvent.change(screen.getByTestId("invite-password-input"), {
      target: { value: VALID_PASSWORD },
    });
    fireEvent.change(screen.getByTestId("invite-confirm-password-input"), {
      target: { value: VALID_PASSWORD },
    });
    fireEvent.click(screen.getByTestId("invite-accept-submit"));

    await waitFor(() => {
      expect(screen.getByText(/too many attempts/i)).toBeInTheDocument();
    });
    expect(screen.queryByTestId("invite-signin-instead")).toBeNull();
  });

  it("paste is not blocked on the password input (WCAG §36)", () => {
    renderForm("newguy@pilot.local");
    const input = screen.getByTestId("invite-password-input");
    const pasteEvent = new Event("paste", {
      bubbles: true,
      cancelable: true,
    });
    const preventDefaultSpy = vi.spyOn(pasteEvent, "preventDefault");
    fireEvent(input, pasteEvent);
    expect(preventDefaultSpy).not.toHaveBeenCalled();
  });
});
