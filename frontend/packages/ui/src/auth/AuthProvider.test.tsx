/**
 * AuthProvider unit tests — FE-B2 additions
 *
 * Location: packages/ui/src/auth/AuthProvider.test.tsx
 *
 * Tests: signIn returns nextStep; MFA nextStep; confirmMfaChallenge
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "./AuthProvider";
import { useAuth } from "./useAuth";
import type { PilotUser } from "./types";

// Mock aws-amplify/auth
vi.mock("aws-amplify/auth", () => ({
  signIn: vi.fn(),
  confirmSignIn: vi.fn(),
  signOut: vi.fn(),
  fetchAuthSession: vi.fn(),
  getCurrentUser: vi.fn(),
}));

const mockUser: Pick<PilotUser, "role" | "email" | "displayName"> = {
  role: "owner",
  email: "test@pilot-dev.example.com",
  displayName: "Test User",
};

// PLP-FIX-9: AuthProvider now calls useQueryClient() for session-boundary
// cache clears (INV-BUG-7), so the test wrapper must provide a QueryClient.
function makeQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
}

function wrapper({ children }: { children: React.ReactNode }) {
  // Use mock mode so Amplify isn't called
  return (
    <QueryClientProvider client={makeQueryClient()}>
      <AuthProvider mockUser={mockUser}>{children}</AuthProvider>
    </QueryClientProvider>
  );
}

// Override env for mock mode
beforeEach(() => {
  vi.stubEnv("NEXT_PUBLIC_USE_MOCK_AUTH", "true");
});

describe("AuthProvider — FE-B2 signIn upgrade", () => {
  it("signIn returns { nextStep: { signInStep: 'DONE' } } in mock mode", async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    let nextStep: { signInStep: string } | undefined;

    await act(async () => {
      const res = await result.current.signIn("test@pilot-dev.example.com", "password");
      nextStep = res.nextStep as { signInStep: string };
    });

    expect(nextStep?.signInStep).toBe("DONE");
  });

  it("confirmMfaChallenge returns DONE in mock mode", async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    let nextStep: { signInStep: string } | undefined;

    await act(async () => {
      const res = await result.current.confirmMfaChallenge("123456");
      nextStep = res.nextStep as { signInStep: string };
    });

    expect(nextStep?.signInStep).toBe("DONE");
  });

  it("signOut sets isAuthenticated to false in mock mode", async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    expect(result.current.isAuthenticated).toBe(true);

    await act(async () => {
      await result.current.signOut();
    });

    expect(result.current.isAuthenticated).toBe(false);
  });
});
