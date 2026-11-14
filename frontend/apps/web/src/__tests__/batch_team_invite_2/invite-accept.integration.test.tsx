/**
 * TEAM-INVITE-2 Integration Tests — Invite Accept Flow
 *
 * Location: apps/web/src/__tests__/batch_team_invite_2/invite-accept.integration.test.tsx
 *
 * Verifies:
 *  1. Office flow end-to-end: landing → form → verify → /dashboard
 *  2. Technician flow: landing → form → verify → invite-joined-mobile
 *  3. Invalid token regression: neutral panel, no accept form
 *  4. No /signup link anywhere on the valid page
 */

import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterAll,
  afterEach,
  beforeEach,
} from "vitest";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { NotificationQueueProvider } from "@pilot/ui/notification-banner";
import { InviteLandingPage } from "@/features/users/components/InviteLandingPage";

// ── Hoisted mocks ─────────────────────────────────────────────────────────────
const { mockConfirmSignUp, mockResendSignUpCode, mockSignIn, mockReplace } =
  vi.hoisted(() => ({
    mockConfirmSignUp: vi.fn(),
    mockResendSignUpCode: vi.fn(),
    mockSignIn: vi.fn(),
    mockReplace: vi.fn(),
  }));

vi.mock("aws-amplify/auth", () => ({
  signUp: vi.fn().mockResolvedValue({
    isSignUpComplete: false,
    userId: "mock-user-id",
    nextStep: { signUpStep: "CONFIRM_SIGN_UP" },
  }),
  confirmSignUp: mockConfirmSignUp,
  resendSignUpCode: mockResendSignUpCode,
  fetchAuthSession: vi.fn().mockResolvedValue({ tokens: undefined }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: mockReplace, back: vi.fn() }),
}));

// ── MSW server ────────────────────────────────────────────────────────────────

const futureExpiry = new Date(
  Date.now() + 7 * 24 * 60 * 60 * 1000,
).toISOString();

const server = setupServer(
  http.get("/api/v1/invites/:token", ({ params }) => {
    if (params.token === "dev-invite-token-0001") {
      return HttpResponse.json({
        tenant_name: "Pilot Dev Tenant",
        email: "newguy@pilot.local",
        role_code: "technician",
        expires_at: futureExpiry,
      });
    }

    if (params.token === "dev-invite-token-0002") {
      return HttpResponse.json({
        tenant_name: "Pilot Dev Tenant",
        email: "sarah-office@pilot.local",
        role_code: "office_staff",
        expires_at: futureExpiry,
      });
    }

    return HttpResponse.json(
      {
        type: "https://errors.pilotfortrades.com/invite_invalid",
        title: "Invite invalid",
        status: 404,
        detail: "This invite link is no longer valid.",
      },
      { status: 404 },
    );
  }),
);

beforeAll(() => server.listen());
afterEach(() => {
  server.resetHandlers();
  mockConfirmSignUp.mockReset();
  mockResendSignUpCode.mockReset();
  mockSignIn.mockReset();
  mockReplace.mockReset();
});
afterAll(() => server.close());

// ── Helpers ───────────────────────────────────────────────────────────────────

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

function renderLanding(token: string) {
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
          <InviteLandingPage token={token} />
        </QueryClientProvider>
      </NotificationQueueProvider>
    </AuthContext.Provider>,
  );
}

const VALID_PASSWORD = "ValidPass1!xxx";

async function fillAndSubmitForm() {
  await waitFor(() => {
    expect(screen.getByTestId("invite-accept-form")).toBeInTheDocument();
  });

  fireEvent.change(screen.getByTestId("invite-password-input"), {
    target: { value: VALID_PASSWORD },
  });
  fireEvent.change(screen.getByTestId("invite-confirm-password-input"), {
    target: { value: VALID_PASSWORD },
  });
  fireEvent.click(screen.getByTestId("invite-accept-submit"));
}

async function fillAndSubmitVerify() {
  await waitFor(() => {
    expect(screen.getByTestId("invite-verify-step")).toBeInTheDocument();
  });

  fireEvent.change(screen.getByTestId("invite-code-input"), {
    target: { value: "123456" },
  });
  fireEvent.click(screen.getByTestId("invite-verify-submit"));
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("TEAM-INVITE-2 — Invite Accept Flow", () => {
  const originalMockEnv = process.env.NEXT_PUBLIC_USE_MOCK_AUTH;

  beforeEach(() => {
    process.env.NEXT_PUBLIC_USE_MOCK_AUTH = "true";
  });

  afterEach(() => {
    process.env.NEXT_PUBLIC_USE_MOCK_AUTH = originalMockEnv;
  });

  it("office flow end-to-end: landing → form → verify → /dashboard", async () => {
    // Mock mode short-circuits Cognito signUp (no Amplify needed).
    // For the verify step, we need confirmSignUp + signIn to resolve.
    process.env.NEXT_PUBLIC_USE_MOCK_AUTH = "false";
    mockConfirmSignUp.mockResolvedValue({ isSignUpComplete: true });
    mockSignIn.mockResolvedValue({ nextStep: { signInStep: "DONE" } });

    renderLanding("dev-invite-token-0002");

    // Landing renders with tenant name + email
    await waitFor(() => {
      expect(screen.getByTestId("invite-landing-page")).toBeInTheDocument();
    });
    expect(screen.getByText("Pilot Dev Tenant")).toBeInTheDocument();
    expect(
      screen.getAllByText("sarah-office@pilot.local").length,
    ).toBeGreaterThanOrEqual(1);

    // Fill the accept form
    await fillAndSubmitForm();

    // Verify step appears
    await fillAndSubmitVerify();

    // confirmSignUp called with the office email
    await waitFor(() => expect(mockConfirmSignUp).toHaveBeenCalledTimes(1));
    expect(mockConfirmSignUp).toHaveBeenCalledWith({
      username: "sarah-office@pilot.local",
      confirmationCode: "123456",
    });

    // signIn called → router.replace("/dashboard")
    await waitFor(() => expect(mockSignIn).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith("/dashboard"));
  });

  it("technician flow: landing → form → verify → invite-joined-mobile", async () => {
    process.env.NEXT_PUBLIC_USE_MOCK_AUTH = "false";
    mockConfirmSignUp.mockResolvedValue({ isSignUpComplete: true });

    renderLanding("dev-invite-token-0001");

    await waitFor(() => {
      expect(screen.getByTestId("invite-landing-page")).toBeInTheDocument();
    });

    await fillAndSubmitForm();
    await fillAndSubmitVerify();

    await waitFor(() => expect(mockConfirmSignUp).toHaveBeenCalledTimes(1));

    // No signIn for technician
    await waitFor(() => {
      expect(screen.getByTestId("invite-joined-mobile")).toBeInTheDocument();
    });
    expect(mockSignIn).not.toHaveBeenCalled();
    expect(mockReplace).not.toHaveBeenCalledWith("/dashboard");
  });

  it("invalid token regression: neutral panel, no accept form", async () => {
    renderLanding("garbage-token-xyz");

    await waitFor(() => {
      expect(screen.getByTestId("invite-invalid-page")).toBeInTheDocument();
    });

    expect(
      screen.getByText("This invite link is no longer valid."),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("invite-accept-form")).toBeNull();
  });

  it("no /signup link anywhere on the valid page", async () => {
    process.env.NEXT_PUBLIC_USE_MOCK_AUTH = "true";

    renderLanding("dev-invite-token-0002");

    await waitFor(() => {
      expect(screen.getByTestId("invite-landing-page")).toBeInTheDocument();
    });

    // The form is present
    expect(screen.getByTestId("invite-accept-form")).toBeInTheDocument();

    // No link pointing to /signup
    expect(
      screen.queryByRole("link", { name: /create your account/i }),
    ).toBeNull();

    // No href="/signup" in the document
    const allLinks = document.querySelectorAll('a[href="/signup"]');
    expect(allLinks.length).toBe(0);
  });
});
