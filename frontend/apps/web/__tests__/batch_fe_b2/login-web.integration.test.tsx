/**
 * Web login integration tests — FE-B2
 *
 * Location: apps/web/__tests__/batch_fe_b2/login-web.integration.test.tsx
 *
 * Tests full login flows: happy path, wrong password, network error, MFA challenge
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { LoginForm } from "@/features/login/components/LoginForm";

const mockSignIn = vi.fn();
const mockConfirmMfaChallenge = vi.fn();
const mockAddNotification = vi.fn();
const mockOnSuccess = vi.fn();
const mockSignOut = vi.fn();

vi.mock("@pilot/ui/auth", () => ({
  useAuth: () => ({
    signIn: mockSignIn,
    confirmMfaChallenge: mockConfirmMfaChallenge,
    signOut: mockSignOut,
    role: "owner",
    isAuthenticated: false,
    user: null,
    refreshSession: vi.fn(),
    // PLP-FIX-7: whenSessionReady returns a mock owner user so the login
    // flow can await the resolved role.
    whenSessionReady: vi.fn().mockResolvedValue({
      id: "u1",
      email: "owner@pilot-dev.example.com",
      role: "owner",
      tenantId: "t1",
      displayName: "Owner",
      accessToken: "tok",
      permissions: ["*"],
    }),
  }),
}));

vi.mock("@pilot/ui/notification-banner", () => ({
  useNotificationQueue: () => ({
    addNotification: mockAddNotification,
    notifications: [],
    dismissNotification: vi.fn(),
    dismissAll: vi.fn(),
  }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn() }),
}));

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) =>
    React.createElement("a", { href }, children),
}));

// PLP-FIX-9: LoginForm uses useLoginFlow which now calls useQueryClient()
// for session-boundary cache clears (INV-BUG-7), so tests must provide a QueryClient.
function makeQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

function renderWithProvider(ui: React.ReactElement) {
  return render(
    <QueryClientProvider client={makeQueryClient()}>{ui}</QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mockConfirmMfaChallenge.mockResolvedValue({
    nextStep: { signInStep: "DONE" },
  });
});

async function fillAndSubmit(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText("Email"), "owner@pilot-dev.example.com");
  await user.type(screen.getByLabelText("Password"), "TestPass123!");
  await user.click(screen.getByRole("button", { name: /sign in/i }));
}

describe("Login web integration", () => {
  it("(1) happy path: successful login calls onSuccess with role", async () => {
    mockSignIn.mockResolvedValueOnce({ nextStep: { signInStep: "DONE" } });
    const user = userEvent.setup();
    renderWithProvider(<LoginForm onSuccess={mockOnSuccess} />);
    await fillAndSubmit(user);

    await waitFor(() => {
      expect(mockOnSuccess).toHaveBeenCalledWith("owner");
    });
  });

  it("(2) wrong password: enqueues error notification", async () => {
    mockSignIn.mockRejectedValueOnce(
      new Error("Incorrect username or password."),
    );
    const user = userEvent.setup();
    renderWithProvider(<LoginForm onSuccess={mockOnSuccess} />);
    await fillAndSubmit(user);

    await waitFor(() => {
      expect(mockAddNotification).toHaveBeenCalledWith(
        expect.objectContaining({ severity: "error" }),
      );
      expect(mockOnSuccess).not.toHaveBeenCalled();
    });
  });

  it("(3) network error: enqueues error notification", async () => {
    mockSignIn.mockRejectedValueOnce(new Error("Network request failed"));
    const user = userEvent.setup();
    renderWithProvider(<LoginForm onSuccess={mockOnSuccess} />);
    await fillAndSubmit(user);

    await waitFor(() => {
      expect(mockAddNotification).toHaveBeenCalledWith(
        expect.objectContaining({ severity: "error" }),
      );
    });
  });

  it("(4) MFA challenge: TOTP step renders code input → submit → DONE → onSuccess", async () => {
    mockSignIn.mockResolvedValueOnce({
      nextStep: { signInStep: "CONFIRM_SIGN_IN_WITH_TOTP_CODE" },
    });
    mockConfirmMfaChallenge.mockResolvedValueOnce({
      nextStep: { signInStep: "DONE" },
    });

    const user = userEvent.setup();
    renderWithProvider(<LoginForm onSuccess={mockOnSuccess} />);
    await fillAndSubmit(user);

    // MFA step renders
    await waitFor(() => {
      expect(screen.getByLabelText("Verification code")).toBeInTheDocument();
    });

    // Enter code and submit
    await user.type(screen.getByLabelText("Verification code"), "123456");
    await user.click(screen.getByRole("button", { name: /verify/i }));

    await waitFor(() => {
      expect(mockConfirmMfaChallenge).toHaveBeenCalledWith("123456");
      expect(mockOnSuccess).toHaveBeenCalledWith("owner");
    });
  });
});
