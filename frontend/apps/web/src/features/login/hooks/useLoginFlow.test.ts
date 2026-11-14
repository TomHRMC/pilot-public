/**
 * useLoginFlow unit tests — web (FE-B2)
 *
 * Location: apps/web/src/features/login/hooks/useLoginFlow.test.ts
 *
 * 6 tests per design doc §I.1
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useLoginFlow } from "./useLoginFlow";

const mockSignIn = vi.fn();
const mockConfirmMfaChallenge = vi.fn();
const mockOnSuccess = vi.fn();

vi.mock("@pilot/ui/auth", () => ({
  useAuth: () => ({
    signIn: mockSignIn,
    confirmMfaChallenge: mockConfirmMfaChallenge,
    role: "owner",
    isAuthenticated: false,
    user: null,
    signOut: vi.fn(),
    refreshSession: vi.fn(),
    // PLP-FIX-7: whenSessionReady returns a mock owner user so the login
    // flow can await the resolved role.
    whenSessionReady: vi.fn().mockResolvedValue({
      id: "u1",
      email: "test@example.com",
      role: "owner",
      tenantId: "t1",
      displayName: "Test",
      accessToken: "tok",
      permissions: ["*"],
    }),
  }),
}));

// PLP-FIX-9: useLoginFlow now calls useQueryClient() for session-boundary
// cache clears (INV-BUG-7), so the test wrapper must provide a QueryClient.
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(
      QueryClientProvider,
      { client: queryClient },
      children,
    );
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("useLoginFlow (web)", () => {
  it("step transitions to mfa-challenge when signIn returns MFA nextStep", async () => {
    mockSignIn.mockResolvedValueOnce({
      nextStep: {
        signInStep: "CONFIRM_SIGN_IN_WITH_TOTP_CODE",
        codeDeliveryDetails: {},
      },
    });

    const { result } = renderHook(() => useLoginFlow(mockOnSuccess), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.submitCredentials("test@example.com", "pass");
    });

    expect(result.current.step).toBe("mfa-challenge");
    expect(result.current.mfaChallenge?.challengeName).toBe("TOTP");
  });

  it("step stays credentials on sign-in error", async () => {
    mockSignIn.mockRejectedValueOnce(new Error("Wrong password"));

    const { result } = renderHook(() => useLoginFlow(mockOnSuccess), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.submitCredentials("test@example.com", "bad");
    });

    expect(result.current.step).toBe("credentials");
    expect(result.current.error).toBe("Wrong password");
  });

  it("onSuccess fires with correct role after DONE nextStep", async () => {
    mockSignIn.mockResolvedValueOnce({ nextStep: { signInStep: "DONE" } });

    const { result } = renderHook(() => useLoginFlow(mockOnSuccess), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.submitCredentials("test@example.com", "pass");
    });

    expect(mockOnSuccess).toHaveBeenCalledWith("owner");
  });

  it("submitMfaCode calls confirmMfaChallenge", async () => {
    mockSignIn.mockResolvedValueOnce({
      nextStep: { signInStep: "CONFIRM_SIGN_IN_WITH_TOTP_CODE" },
    });
    mockConfirmMfaChallenge.mockResolvedValueOnce({
      nextStep: { signInStep: "DONE" },
    });

    const { result } = renderHook(() => useLoginFlow(mockOnSuccess), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.submitCredentials("test@example.com", "pass");
    });

    await act(async () => {
      await result.current.submitMfaCode("123456");
    });

    expect(mockConfirmMfaChallenge).toHaveBeenCalledWith("123456");
  });

  it("cancelMfa resets to credentials step", async () => {
    mockSignIn.mockResolvedValueOnce({
      nextStep: { signInStep: "CONFIRM_SIGN_IN_WITH_TOTP_CODE" },
    });

    const { result } = renderHook(() => useLoginFlow(mockOnSuccess), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.submitCredentials("test@example.com", "pass");
    });

    expect(result.current.step).toBe("mfa-challenge");

    act(() => {
      result.current.cancelMfa();
    });

    expect(result.current.step).toBe("credentials");
    expect(result.current.mfaChallenge).toBeNull();
  });

  it("isLoading is false after successful sign-in completes", async () => {
    mockSignIn.mockResolvedValueOnce({ nextStep: { signInStep: "DONE" } });

    const { result } = renderHook(() => useLoginFlow(mockOnSuccess), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.submitCredentials("test@example.com", "pass");
    });

    // After completion, isLoading must be false
    expect(result.current.isLoading).toBe(false);
    expect(mockOnSuccess).toHaveBeenCalled();
  });
});
