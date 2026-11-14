/**
 * VerifyEmailStep unit tests — SIGNUP-GA-1
 *
 * Location: apps/web/src/features/signup/components/__tests__/VerifyEmailStep.test.tsx
 *
 * Verifies:
 *  - confirmSignUp on submit
 *  - on success calls signIn then POSTs /api/v1/signup then routes to /signup/legal
 *  - CodeMismatchException renders the inline error
 *  - resend calls resendSignUpCode
 *  - hard-reload fallback (no password) routes to /login?confirmed=true
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { NotificationQueueProvider } from "@pilot/ui/notification-banner";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";

// ── Hoisted mocks ─────────────────────────────────────────────────────────────
const {
  mockConfirmSignUp,
  mockResendSignUpCode,
  mockSignIn,
  mockPush,
  mockReplace,
} = vi.hoisted(() => ({
  mockConfirmSignUp: vi.fn(),
  mockResendSignUpCode: vi.fn(),
  mockSignIn: vi.fn(),
  mockPush: vi.fn(),
  mockReplace: vi.fn(),
}));

vi.mock("aws-amplify/auth", () => ({
  confirmSignUp: mockConfirmSignUp,
  resendSignUpCode: mockResendSignUpCode,
  fetchAuthSession: vi.fn().mockResolvedValue({ tokens: undefined }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, replace: mockReplace, back: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

import { VerifyEmailStep } from "@/features/signup/components/VerifyEmailStep";
import {
  setSignupPendingCredential,
  clearSignupPendingCredential,
} from "@/features/signup/signupPendingCredential";

// ── MSW server for the /api/v1/signup POST ─────────────────────────────────────
const server = setupServer(
  http.post("/api/v1/signup", async ({ request }) => {
    const body = (await request.json()) as { business_name?: string };
    return HttpResponse.json(
      {
        tenant_id: "tenant-verify-test-001",
        signup_state: "step1_account",
        owner_email: body.business_name ? "mike@apex.example.com" : "",
        credential_pending: false,
      },
      { status: 201 },
    );
  }),
);

beforeEach(() => {
  server.listen({ onUnhandledRequest: "bypass" });
});
afterEach(() => {
  server.resetHandlers();
  server.close();
  clearSignupPendingCredential();
});

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

function renderStep() {
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
          <VerifyEmailStep />
        </QueryClientProvider>
      </NotificationQueueProvider>
    </AuthContext.Provider>,
  );
}

const PENDING_CRED = {
  email: "mike@apex.example.com",
  password: "ValidPass1!xxx",
  businessFields: {
    business_name: "Apex Electric LLC",
    trade: "electrical",
    business_size: "solo",
    zip: "10001",
    time_zone: "America/New_York",
    owner_email: "mike@apex.example.com",
    owner_first_name: "Mike",
    owner_last_name: "Johnson",
  },
};

describe("VerifyEmailStep — SIGNUP-GA-1", () => {
  const originalMockEnv = process.env.NEXT_PUBLIC_USE_MOCK_AUTH;

  beforeEach(() => {
    mockConfirmSignUp.mockReset();
    mockResendSignUpCode.mockReset();
    mockSignIn.mockReset();
    mockPush.mockReset();
    mockReplace.mockReset();
    process.env.NEXT_PUBLIC_USE_MOCK_AUTH = "false";
    setSignupPendingCredential(PENDING_CRED);
  });

  afterEach(() => {
    process.env.NEXT_PUBLIC_USE_MOCK_AUTH = originalMockEnv;
  });

  it("calls confirmSignUp on submit with username + confirmationCode", async () => {
    mockConfirmSignUp.mockResolvedValue({ isSignUpComplete: true });
    mockSignIn.mockResolvedValue({
      nextStep: { signInStep: "DONE" },
    });

    renderStep();
    fireEvent.change(screen.getByTestId("field-verification-code"), {
      target: { value: "123456" },
    });
    fireEvent.click(screen.getByTestId("signup-verify-continue"));

    await waitFor(() => expect(mockConfirmSignUp).toHaveBeenCalledTimes(1));
    expect(mockConfirmSignUp).toHaveBeenCalledWith({
      username: "mike@apex.example.com",
      confirmationCode: "123456",
    });
  });

  it("on success: calls signIn then POSTs /api/v1/signup then routes to /signup/legal", async () => {
    mockConfirmSignUp.mockResolvedValue({ isSignUpComplete: true });
    mockSignIn.mockResolvedValue({
      nextStep: { signInStep: "DONE" },
    });

    renderStep();
    fireEvent.change(screen.getByTestId("field-verification-code"), {
      target: { value: "123456" },
    });
    fireEvent.click(screen.getByTestId("signup-verify-continue"));

    await waitFor(() => expect(mockSignIn).toHaveBeenCalledTimes(1));
    expect(mockSignIn).toHaveBeenCalledWith("mike@apex.example.com", "ValidPass1!xxx");

    await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/signup/legal"));
  });

  it("CodeMismatchException renders the inline error", async () => {
    const err = new Error("Code mismatch");
    (err as { name: string }).name = "CodeMismatchException";
    mockConfirmSignUp.mockRejectedValue(err);

    renderStep();
    fireEvent.change(screen.getByTestId("field-verification-code"), {
      target: { value: "000000" },
    });
    fireEvent.click(screen.getByTestId("signup-verify-continue"));

    await waitFor(() =>
      expect(screen.getByText(/that code doesn't match/i)).toBeTruthy(),
    );
    expect(mockPush).not.toHaveBeenCalled();
  });

  it("ExpiredCodeException renders the expired error", async () => {
    const err = new Error("Expired");
    (err as { name: string }).name = "ExpiredCodeException";
    mockConfirmSignUp.mockRejectedValue(err);

    renderStep();
    fireEvent.change(screen.getByTestId("field-verification-code"), {
      target: { value: "000000" },
    });
    fireEvent.click(screen.getByTestId("signup-verify-continue"));

    await waitFor(() =>
      expect(screen.getByText(/that code expired/i)).toBeTruthy(),
    );
  });

  it("resend calls resendSignUpCode", async () => {
    mockResendSignUpCode.mockResolvedValue({});

    renderStep();
    fireEvent.click(screen.getByTestId("signup-verify-resend"));

    await waitFor(() => expect(mockResendSignUpCode).toHaveBeenCalledTimes(1));
    expect(mockResendSignUpCode).toHaveBeenCalledWith({
      username: "mike@apex.example.com",
    });
  });

  it("hard-reload fallback (no password) routes to /login?confirmed=true", async () => {
    // Simulate hard reload: password gone from in-memory store
    clearSignupPendingCredential();
    setSignupPendingCredential({
      ...PENDING_CRED,
      password: "",
    });

    mockConfirmSignUp.mockResolvedValue({ isSignUpComplete: true });

    renderStep();
    fireEvent.change(screen.getByTestId("field-verification-code"), {
      target: { value: "123456" },
    });
    fireEvent.click(screen.getByTestId("signup-verify-continue"));

    await waitFor(() =>
      expect(mockReplace).toHaveBeenCalledWith(
        expect.stringContaining("/login?confirmed=true"),
      ),
    );
    expect(mockSignIn).not.toHaveBeenCalled();
  });

  it("verification code input allows paste (WCAG §36)", () => {
    renderStep();
    const input = screen.getByTestId("field-verification-code");
    const pasteEvent = new Event("paste", {
      bubbles: true,
      cancelable: true,
    });
    const preventDefaultSpy = vi.spyOn(pasteEvent, "preventDefault");
    fireEvent(input, pasteEvent);
    expect(preventDefaultSpy).not.toHaveBeenCalled();
  });

  // ── SIGNUP-UI-FIX-2 Task 2: provisioning phase copy ──────────────────────

  it("button transitions 'Verify & continue →' → 'Verifying…' → 'Setting up your account…' across confirm + provisioning", async () => {
    // Use a controllable promise so we can assert the intermediate
    // "Setting up your account…" copy while signIn is in flight.
    let resolveSignIn: (val: unknown) => void;
    const signInPromise = new Promise((resolve) => {
      resolveSignIn = resolve;
    });
    mockConfirmSignUp.mockResolvedValue({ isSignUpComplete: true });
    mockSignIn.mockReturnValue(signInPromise);

    renderStep();

    const button = screen.getByTestId("signup-verify-continue");

    // Initial state: "Verify & continue →"
    expect(button).toHaveTextContent("Verify & continue →");

    // Enter code + submit
    fireEvent.change(screen.getByTestId("field-verification-code"), {
      target: { value: "123456" },
    });
    fireEvent.click(button);

    // Phase 1: "Verifying…" (confirmSignUp in flight → resolves quickly)
    await waitFor(() => expect(button).toHaveTextContent("Verifying…"));

    // Phase 2: confirm resolved → provisioning → "Setting up your account…"
    await waitFor(() =>
      expect(button).toHaveTextContent("Setting up your account…"),
    );

    // Button must be disabled during provisioning
    expect(button).toBeDisabled();

    // Button must have aria-live="polite" for the copy transition
    expect(button).toHaveAttribute("aria-live", "polite");

    // Release signIn → wizard advances
    resolveSignIn!({ nextStep: { signInStep: "DONE" } });

    await waitFor(() => expect(mockPush).toHaveBeenCalledWith("/signup/legal"));
  });
});
