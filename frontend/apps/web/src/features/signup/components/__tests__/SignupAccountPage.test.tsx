/**
 * SignupAccountPage unit tests — SIGNUP-GA-1
 *
 * Location: apps/web/src/features/signup/components/__tests__/SignupAccountPage.test.tsx
 *
 * Verifies:
 *  - password-policy Zod validation (rejects <12 chars / missing symbol; confirms match)
 *  - does NOT POST /api/v1/signup on submit (asserts Cognito signUp is called instead)
 *  - paste is allowed on password fields (WCAG §36)
 *  - UsernameExistsException surfaces the inline "already exists" + "Sign in instead" link
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// ── Hoisted mocks (vi.mock factories are hoisted above const declarations) ────
const {
  mockSignUp,
  mockPush,
  mockReplace,
  mockPost,
  mockGet,
  mockSignOut,
  mockAuthState,
} = vi.hoisted(() => ({
  mockSignUp: vi.fn(),
  mockPush: vi.fn(),
  mockReplace: vi.fn(),
  mockPost: vi.fn(),
  mockGet: vi.fn(),
  mockSignOut: vi.fn().mockResolvedValue(undefined),
  mockAuthState: { isAuthenticated: false },
}));

vi.mock("aws-amplify/auth", () => ({
  signUp: mockSignUp,
  // Include fetchAuthSession so apiClient's interceptor doesn't throw
  // (matches the global mock in vitest.setup.ts)
  fetchAuthSession: vi.fn().mockResolvedValue({ tokens: undefined }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, replace: mockReplace, back: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("@pilot/shared-api", () => ({
  apiClient: {
    post: mockPost,
    get: mockGet,
  },
}));

vi.mock("@pilot/ui/auth", () => ({
  useAuth: () => ({
    user: null,
    isAuthenticated: mockAuthState.isAuthenticated,
    role: null,
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: mockSignOut,
    refreshSession: vi.fn().mockResolvedValue("mock-token"),
  }),
}));

import SignupAccountPage from "@/app/signup/account/page";

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

function renderPage() {
  return render(
    <QueryClientProvider client={makeQueryClient()}>
      <SignupAccountPage />
    </QueryClientProvider>,
  );
}

const VALID_PASSWORD = "ValidPass1!xxx";

function fillValidForm() {
  fireEvent.change(screen.getByTestId("field-business-name"), {
    target: { value: "Apex Electric LLC" },
  });
  fireEvent.change(screen.getByTestId("field-trade"), {
    target: { value: "electrical" },
  });
  fireEvent.change(screen.getByTestId("field-business-size"), {
    target: { value: "solo" },
  });
  fireEvent.change(screen.getByTestId("field-zip"), {
    target: { value: "10001" },
  });
  fireEvent.change(screen.getByTestId("field-first-name"), {
    target: { value: "Mike" },
  });
  fireEvent.change(screen.getByTestId("field-last-name"), {
    target: { value: "Johnson" },
  });
  fireEvent.change(screen.getByTestId("field-email"), {
    target: { value: "mike@apex.example.com" },
  });
  fireEvent.change(screen.getByTestId("field-password"), {
    target: { value: VALID_PASSWORD },
  });
  fireEvent.change(screen.getByTestId("field-confirm-password"), {
    target: { value: VALID_PASSWORD },
  });
}

describe("SignupAccountPage — SIGNUP-GA-1", () => {
  const originalMockEnv = process.env.NEXT_PUBLIC_USE_MOCK_AUTH;

  beforeEach(() => {
    mockSignUp.mockReset();
    mockPost.mockReset();
    mockGet.mockReset();
    mockPush.mockReset();
    mockReplace.mockReset();
    mockSignOut.mockClear();
    mockAuthState.isAuthenticated = false;
    sessionStorage.clear();
    process.env.NEXT_PUBLIC_USE_MOCK_AUTH = "false";
    // Default: return trial tier list (General Release mode) for useSubscriptionTiers
    mockGet.mockResolvedValue({
      data: {
        tiers: [
          {
            tier_id: "t1",
            tier_name: "trial",
            is_trial: true,
            is_active: true,
            display_label: "Free Trial",
            monthly_price_cents: 0,
            trial_duration_days: 14,
            max_users: 1,
            max_sms_segments_per_month: 50,
            display_order: 0,
          },
          {
            tier_id: "t2",
            tier_name: "starter",
            is_trial: false,
            is_active: true,
            display_label: "Starter",
            monthly_price_cents: 9900,
            trial_duration_days: null,
            max_users: 5,
            max_sms_segments_per_month: 500,
            display_order: 1,
          },
        ],
      },
    });
  });

  afterEach(() => {
    process.env.NEXT_PUBLIC_USE_MOCK_AUTH = originalMockEnv;
  });

  it("renders all fields including password + confirm_password", () => {
    renderPage();
    expect(screen.getByTestId("field-business-name")).toBeTruthy();
    expect(screen.getByTestId("field-password")).toBeTruthy();
    expect(screen.getByTestId("field-confirm-password")).toBeTruthy();
  });

  it("rejects password shorter than 12 characters", async () => {
    renderPage();
    fillValidForm();
    fireEvent.change(screen.getByTestId("field-password"), {
      target: { value: "Short1!" },
    });
    fireEvent.change(screen.getByTestId("field-confirm-password"), {
      target: { value: "Short1!" },
    });

    fireEvent.click(screen.getByTestId("signup-account-continue"));

    await waitFor(() => {
      expect(screen.getByText(/at least 12 characters/i)).toBeTruthy();
    });
    // Cognito signUp must NOT have been called (validation failed)
    expect(mockSignUp).not.toHaveBeenCalled();
  });

  it("rejects password missing a symbol", async () => {
    renderPage();
    fillValidForm();
    fireEvent.change(screen.getByTestId("field-password"), {
      target: { value: "NoSymbol12345" },
    });
    fireEvent.change(screen.getByTestId("field-confirm-password"), {
      target: { value: "NoSymbol12345" },
    });

    fireEvent.click(screen.getByTestId("signup-account-continue"));

    await waitFor(() => {
      expect(screen.getByText(/at least one symbol/i)).toBeTruthy();
    });
    expect(mockSignUp).not.toHaveBeenCalled();
  });

  it("rejects when passwords do not match", async () => {
    renderPage();
    fillValidForm();
    fireEvent.change(screen.getByTestId("field-confirm-password"), {
      target: { value: "DifferentPass1!yyy" },
    });

    fireEvent.click(screen.getByTestId("signup-account-continue"));

    await waitFor(() => {
      expect(screen.getByText(/passwords do not match/i)).toBeTruthy();
    });
    expect(mockSignUp).not.toHaveBeenCalled();
  });

  it("does NOT POST /api/v1/signup on submit — calls Cognito signUp instead", async () => {
    mockSignUp.mockResolvedValue({
      isSignUpComplete: false,
      userId: "user-123",
      nextStep: {
        signUpStep: "CONFIRM_SIGN_UP",
        codeDeliveryDetails: {
          deliveryMedium: "EMAIL",
          destination: "mike@apex.example.com",
          attributeName: "email",
        },
      },
    });

    renderPage();
    fillValidForm();

    fireEvent.click(screen.getByTestId("signup-account-continue"));

    await waitFor(() => expect(mockSignUp).toHaveBeenCalledTimes(1));
    expect(mockPost).not.toHaveBeenCalled();
    expect(mockPush).toHaveBeenCalledWith("/signup/verify");
  });

  it("calls signUp with username=email, password, and userAttributes.email", async () => {
    mockSignUp.mockResolvedValue({
      isSignUpComplete: false,
      userId: "user-123",
      nextStep: {
        signUpStep: "CONFIRM_SIGN_UP",
        codeDeliveryDetails: {
          deliveryMedium: "EMAIL",
          destination: "mike@apex.example.com",
          attributeName: "email",
        },
      },
    });

    renderPage();
    fillValidForm();

    fireEvent.click(screen.getByTestId("signup-account-continue"));

    await waitFor(() => expect(mockSignUp).toHaveBeenCalledTimes(1));
    expect(mockSignUp).toHaveBeenCalledWith({
      username: "mike@apex.example.com",
      password: VALID_PASSWORD,
      options: { userAttributes: { email: "mike@apex.example.com" } },
    });
  });

  it("surfaces UsernameExistsException as inline 'already exists' + 'Sign in instead' link", async () => {
    const amplifyErr = new Error("User already exists");
    (amplifyErr as { name: string }).name = "UsernameExistsException";
    mockSignUp.mockRejectedValue(amplifyErr);

    renderPage();
    fillValidForm();

    fireEvent.click(screen.getByTestId("signup-account-continue"));

    await waitFor(() =>
      expect(
        screen.getByText(/an account with this email already exists/i),
      ).toBeTruthy(),
    );
    expect(screen.getByText(/sign in instead/i)).toBeTruthy();
    expect(mockPush).not.toHaveBeenCalled();
  });

  it("password field allows paste (no onPaste blocking) — WCAG §36", () => {
    renderPage();
    const passwordInput = screen.getByTestId("field-password");
    const confirmInput = screen.getByTestId("field-confirm-password");

    // Simulate a paste event — it should NOT be prevented.
    const pasteEvent = new Event("paste", {
      bubbles: true,
      cancelable: true,
    });
    const preventDefaultSpy = vi.spyOn(pasteEvent, "preventDefault");

    fireEvent(passwordInput, pasteEvent);
    fireEvent(confirmInput, pasteEvent);

    expect(preventDefaultSpy).not.toHaveBeenCalled();
  });

  it("password helper text is non-color-only (states the policy)", () => {
    renderPage();
    expect(screen.getByText(/at least 12 characters/i)).toBeTruthy();
    expect(screen.getByText(/one uppercase/i)).toBeTruthy();
    expect(screen.getByText(/one symbol/i)).toBeTruthy();
  });

  // ── SIGNUP-UI-FIX-1: Password reveal toggle ──────────────────────────────

  it("password reveal toggle: clicking changes input type from password to text", () => {
    renderPage();
    const passwordInput = screen.getByTestId(
      "field-password",
    ) as HTMLInputElement;
    const toggleBtn = screen.getByTestId("toggle-password-visibility");

    // Initially password type
    expect(passwordInput.type).toBe("password");
    expect(toggleBtn.getAttribute("aria-label")).toBe("Show password");

    // Click to reveal
    fireEvent.click(toggleBtn);
    expect(passwordInput.type).toBe("text");
    expect(toggleBtn.getAttribute("aria-label")).toBe("Hide password");

    // Click again to hide
    fireEvent.click(toggleBtn);
    expect(passwordInput.type).toBe("password");
    expect(toggleBtn.getAttribute("aria-label")).toBe("Show password");
  });

  it("confirm password reveal toggle: clicking changes input type from password to text", () => {
    renderPage();
    const confirmInput = screen.getByTestId(
      "field-confirm-password",
    ) as HTMLInputElement;
    const toggleBtn = screen.getByTestId("toggle-confirm-password-visibility");

    expect(confirmInput.type).toBe("password");
    expect(toggleBtn.getAttribute("aria-label")).toBe("Show password");

    fireEvent.click(toggleBtn);
    expect(confirmInput.type).toBe("text");
    expect(toggleBtn.getAttribute("aria-label")).toBe("Hide password");
  });

  it("password toggle button has type='button' (no form submit)", () => {
    renderPage();
    const toggleBtn = screen.getByTestId("toggle-password-visibility");
    expect(toggleBtn.getAttribute("type")).toBe("button");
  });

  // ── SIGNUP-UI-FIX-1: Mode-aware subtitle ──────────────────────────────────

  it("shows trial subtitle when a trial tier exists (General Release mode)", async () => {
    renderPage();
    await waitFor(() => {
      expect(
        screen.getByText(/Start your free 14-day trial/i),
      ).toBeInTheDocument();
    });
  });

  it("shows Charter subtitle when no trial tier exists (Charter mode)", async () => {
    // Override mockGet to return only a charter tier (no trial)
    mockGet.mockResolvedValue({
      data: {
        tiers: [
          {
            tier_id: "tf",
            tier_name: "charter",
            is_trial: false,
            is_active: true,
            display_label: "Charter",
            monthly_price_cents: 0,
            trial_duration_days: null,
            max_users: 5,
            max_sms_segments_per_month: 100,
            display_order: 0,
          },
        ],
      },
    });

    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/Join the Charter program/i)).toBeInTheDocument();
    });
  });

  // ── SIGNUP-UI-FIX-1: Stale session cleanup ────────────────────────────────

  it("calls signOut() on mount when isAuthenticated is true (stale session)", async () => {
    mockAuthState.isAuthenticated = true;
    renderPage();
    await waitFor(() => {
      expect(mockSignOut).toHaveBeenCalledTimes(1);
    });
  });

  it("does NOT call signOut() on mount when isAuthenticated is false", () => {
    mockAuthState.isAuthenticated = false;
    renderPage();
    expect(mockSignOut).not.toHaveBeenCalled();
  });
});
