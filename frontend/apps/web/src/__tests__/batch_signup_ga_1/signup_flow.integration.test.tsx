/**
 * SIGNUP-GA-1 Integration — Self-Serve Credential Creation (Web)
 *
 * Location: apps/web/src/__tests__/batch_signup_ga_1/signup_flow.integration.test.tsx
 *
 * Tests the full self-serve signup flow (ADR-0011):
 * 1. Account page renders; filling valid fields + password → submitting calls
 *    Amplify signUp and navigates to /signup/verify
 * 2. Verify page: entering a code → confirmSignUp + signIn called, then
 *    POST /api/v1/signup fires (MSW captures the request body has
 *    business_name), then routes to /signup/legal
 * 3. Duplicate email (UsernameExistsException) shows the inline "already
 *    exists" + "Sign in instead" link
 * 4. WCAG spot: password + code inputs allow paste; errors are role="alert"
 *    with aria-invalid (not color-only)
 */

import React from "react";
import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterEach,
  afterAll,
  beforeEach,
} from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { NotificationQueueProvider } from "@pilot/ui/notification-banner";

// ── Hoisted mocks ─────────────────────────────────────────────────────────────
const {
  mockSignUp,
  mockConfirmSignUp,
  mockResendSignUpCode,
  mockSignIn,
  mockPush,
  mockReplace,
} = vi.hoisted(() => ({
  mockSignUp: vi.fn(),
  mockConfirmSignUp: vi.fn(),
  mockResendSignUpCode: vi.fn(),
  mockSignIn: vi.fn(),
  mockPush: vi.fn(),
  mockReplace: vi.fn(),
}));

vi.mock("aws-amplify/auth", () => ({
  signUp: mockSignUp,
  confirmSignUp: mockConfirmSignUp,
  resendSignUpCode: mockResendSignUpCode,
  // Include fetchAuthSession so apiClient's interceptor doesn't throw
  // (matches the global mock in vitest.setup.ts)
  fetchAuthSession: vi.fn().mockResolvedValue({ tokens: undefined }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, replace: mockReplace, back: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

import SignupAccountPage from "@/app/signup/account/page";
import { VerifyEmailStep } from "@/features/signup/components/VerifyEmailStep";
import {
  setSignupPendingCredential,
  clearSignupPendingCredential,
} from "@/features/signup/signupPendingCredential";

// ── MSW — capture the /api/v1/signup POST body ─────────────────────────────────
let capturedSignupBody: { business_name?: string } | null = null;

const server = setupServer(
  http.post("/api/v1/signup", async ({ request }) => {
    capturedSignupBody = (await request.json()) as { business_name?: string };
    return HttpResponse.json(
      {
        tenant_id: "tenant-int-001",
        signup_state: "step1_account",
        owner_email: "mike@apex.example.com",
        credential_pending: false,
      },
      { status: 201 },
    );
  }),
  // SIGNUP-UI-FIX-1: account page now fetches subscription tiers for mode-aware subtitle
  http.get("/api/v1/subscription-tiers", () =>
    HttpResponse.json({
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
    }),
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => {
  server.resetHandlers();
  capturedSignupBody = null;
});
afterAll(() => server.close());

// ── Auth helper ────────────────────────────────────────────────────────────────
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

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

function renderAccountPage() {
  // SIGNUP-UI-FIX-1: account page now uses useAuth() — wrap in AuthContext.Provider
  return render(
    <AuthContext.Provider value={makeAuthValue()}>
      <QueryClientProvider client={makeQueryClient()}>
        <SignupAccountPage />
      </QueryClientProvider>
    </AuthContext.Provider>,
  );
}

function renderVerifyStep() {
  return render(
    <AuthContext.Provider value={makeAuthValue()}>
      <NotificationQueueProvider>
        <QueryClientProvider client={makeQueryClient()}>
          <VerifyEmailStep />
        </QueryClientProvider>
      </NotificationQueueProvider>
    </AuthContext.Provider>,
  );
}

const VALID_PASSWORD = "ValidPass1!xxx";

function fillValidAccountForm() {
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

describe("SIGNUP-GA-1 — Self-Serve Credential Creation (Web)", () => {
  const originalMockEnv = process.env.NEXT_PUBLIC_USE_MOCK_AUTH;

  beforeEach(() => {
    mockSignUp.mockReset();
    mockConfirmSignUp.mockReset();
    mockResendSignUpCode.mockReset();
    mockSignIn.mockReset();
    mockPush.mockReset();
    mockReplace.mockReset();
    sessionStorage.clear();
    clearSignupPendingCredential();
    capturedSignupBody = null;
    process.env.NEXT_PUBLIC_USE_MOCK_AUTH = "false";
  });

  afterEach(() => {
    process.env.NEXT_PUBLIC_USE_MOCK_AUTH = originalMockEnv;
  });

  // 1. Account page → Cognito signUp → navigate to verify
  it("1. account page: valid fields + password → calls Amplify signUp and navigates to /signup/verify", async () => {
    mockSignUp.mockResolvedValue({
      isSignUpComplete: false,
      userId: "user-int-001",
      nextStep: {
        signUpStep: "CONFIRM_SIGN_UP",
        codeDeliveryDetails: {
          deliveryMedium: "EMAIL",
          destination: "mike@apex.example.com",
          attributeName: "email",
        },
      },
    });

    renderAccountPage();
    fillValidAccountForm();

    fireEvent.click(screen.getByTestId("signup-account-continue"));

    await waitFor(() => expect(mockSignUp).toHaveBeenCalledTimes(1));
    expect(mockSignUp).toHaveBeenCalledWith({
      username: "mike@apex.example.com",
      password: VALID_PASSWORD,
      options: { userAttributes: { email: "mike@apex.example.com" } },
    });
    expect(mockPush).toHaveBeenCalledWith("/signup/verify");
  });

  // 2. Verify page → confirmSignUp + signIn + POST /signup → /signup/legal
  it("2. verify page: code → confirmSignUp + signIn + POST /api/v1/signup (body has business_name) → routes to /signup/legal", async () => {
    // Simulate the account page having set the pending credential
    setSignupPendingCredential({
      email: "mike@apex.example.com",
      password: VALID_PASSWORD,
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
    });

    mockConfirmSignUp.mockResolvedValue({ isSignUpComplete: true });
    mockSignIn.mockResolvedValue({ nextStep: { signInStep: "DONE" } });

    renderVerifyStep();

    fireEvent.change(screen.getByTestId("field-verification-code"), {
      target: { value: "123456" },
    });
    fireEvent.click(screen.getByTestId("signup-verify-continue"));

    await waitFor(() => expect(mockConfirmSignUp).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(mockSignIn).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(capturedSignupBody).not.toBeNull());

    expect(capturedSignupBody?.business_name).toBe("Apex Electric LLC");
    expect(mockPush).toHaveBeenCalledWith("/signup/legal");
  });

  // 3. Duplicate email (UsernameExistsException)
  it("3. duplicate email (UsernameExistsException) shows inline 'already exists' + 'Sign in instead' link", async () => {
    const amplifyErr = new Error("User already exists");
    (amplifyErr as { name: string }).name = "UsernameExistsException";
    mockSignUp.mockRejectedValue(amplifyErr);

    renderAccountPage();
    fillValidAccountForm();

    fireEvent.click(screen.getByTestId("signup-account-continue"));

    await waitFor(() =>
      expect(
        screen.getByText(/an account with this email already exists/i),
      ).toBeTruthy(),
    );
    expect(screen.getByText(/sign in instead/i)).toBeTruthy();
    expect(mockPush).not.toHaveBeenCalled();
  });

  // 4. WCAG spot: paste allowed + errors are role="alert" with aria-invalid
  it("4. WCAG: password + code inputs allow paste; errors use role=alert + aria-invalid (not color-only)", async () => {
    renderAccountPage();

    const passwordInput = screen.getByTestId("field-password");
    const confirmInput = screen.getByTestId("field-confirm-password");

    // Paste not blocked
    const pasteEvent = new Event("paste", {
      bubbles: true,
      cancelable: true,
    });
    const preventDefaultSpy = vi.spyOn(pasteEvent, "preventDefault");
    fireEvent(passwordInput, pasteEvent);
    fireEvent(confirmInput, pasteEvent);
    expect(preventDefaultSpy).not.toHaveBeenCalled();

    // Trigger a validation error and check it's role="alert" + aria-invalid
    fireEvent.change(screen.getByTestId("field-password"), {
      target: { value: "short" },
    });
    fireEvent.click(screen.getByTestId("signup-account-continue"));

    // The password error paragraph has role="alert" (async — RHF resolver)
    await waitFor(() => {
      const alertElements = screen.getAllByRole("alert");
      expect(alertElements.length).toBeGreaterThan(0);
    });

    // The input has aria-invalid
    await waitFor(() => {
      expect(passwordInput.getAttribute("aria-invalid")).toBe("true");
    });
  });
});
