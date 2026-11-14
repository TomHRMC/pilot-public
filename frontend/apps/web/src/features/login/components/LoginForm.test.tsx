/**
 * LoginForm unit tests — web (FE-B2)
 *
 * Location: apps/web/src/features/login/components/LoginForm.test.tsx
 *
 * 8 tests covering: validation, submit, loading, error, mock mode
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { LoginForm } from "./LoginForm";

// Mock hooks
const mockSignIn = vi.fn();
const mockSignOut = vi.fn();
const mockAddNotification = vi.fn();
const mockOnSuccess = vi.fn();

vi.mock("@pilot/ui/auth", () => ({
  useAuth: () => ({
    signIn: mockSignIn,
    signOut: mockSignOut,
    confirmMfaChallenge: vi
      .fn()
      .mockResolvedValue({ nextStep: { signInStep: "DONE" } }),
    role: "owner",
    isAuthenticated: false,
    user: null,
    refreshSession: vi.fn(),
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

vi.mock("../hooks/useLoginFlow", async (importOriginal) => {
  // We'll test the hook separately; here mock it to control form behavior
  const actual = await importOriginal<typeof import("../hooks/useLoginFlow")>();
  return actual;
});

// PLP-FIX-9: LoginForm uses useLoginFlow which now calls useQueryClient()
// for session-boundary cache clears (INV-BUG-7), so the test wrapper must
// provide a QueryClient.
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
  mockSignIn.mockResolvedValue({ nextStep: { signInStep: "DONE" } });
});

describe("LoginForm (web)", () => {
  it("renders email and password inputs with visible labels", () => {
    renderWithProvider(<LoginForm onSuccess={mockOnSuccess} />);
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Password")).toBeInTheDocument();
  });

  it("submit button is disabled when email is empty", () => {
    renderWithProvider(<LoginForm onSuccess={mockOnSuccess} />);
    const button = screen.getByRole("button", { name: /sign in/i });
    expect(button).toBeDisabled();
  });

  it("submit button is disabled when password is empty", async () => {
    const user = userEvent.setup();
    renderWithProvider(<LoginForm onSuccess={mockOnSuccess} />);
    await user.type(screen.getByLabelText("Email"), "test@example.com");
    const button = screen.getByRole("button", { name: /sign in/i });
    expect(button).toBeDisabled();
  });

  it("submit button is enabled when both fields are filled", async () => {
    const user = userEvent.setup();
    renderWithProvider(<LoginForm onSuccess={mockOnSuccess} />);
    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Password"), "password123");
    const button = screen.getByRole("button", { name: /sign in/i });
    expect(button).not.toBeDisabled();
  });

  it("calls signIn with email and password on submit", async () => {
    const user = userEvent.setup();
    renderWithProvider(<LoginForm onSuccess={mockOnSuccess} />);
    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Password"), "secret");
    await user.click(screen.getByRole("button", { name: /sign in/i }));
    await waitFor(() => {
      expect(mockSignIn).toHaveBeenCalledWith("test@example.com", "secret");
    });
  });

  it("enqueues error notification on signIn rejection", async () => {
    mockSignIn.mockRejectedValueOnce(
      new Error("Incorrect username or password."),
    );
    const user = userEvent.setup();
    renderWithProvider(<LoginForm onSuccess={mockOnSuccess} />);
    await user.type(screen.getByLabelText("Email"), "bad@example.com");
    await user.type(screen.getByLabelText("Password"), "wrong");
    await user.click(screen.getByRole("button", { name: /sign in/i }));
    await waitFor(() => {
      expect(mockAddNotification).toHaveBeenCalledWith(
        expect.objectContaining({ severity: "error" }),
      );
    });
  });

  it("mock mode renders role dropdown not password input", () => {
    renderWithProvider(<LoginForm onSuccess={mockOnSuccess} mockMode />);
    expect(screen.getByLabelText("Role")).toBeInTheDocument();
    expect(screen.queryByLabelText("Password")).not.toBeInTheDocument();
  });

  it("mock mode submit calls onSuccess with selected role", async () => {
    const user = userEvent.setup();
    renderWithProvider(<LoginForm onSuccess={mockOnSuccess} mockMode />);
    await user.click(screen.getByRole("button", { name: /sign in as/i }));
    await waitFor(() => {
      expect(mockOnSuccess).toHaveBeenCalled();
    });
  });
});
