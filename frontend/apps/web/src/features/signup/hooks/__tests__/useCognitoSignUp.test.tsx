/**
 * useCognitoSignUp unit tests — SIGNUP-GA-1
 *
 * Location: apps/web/src/features/signup/hooks/__tests__/useCognitoSignUp.test.ts
 *
 * Verifies:
 *  - calls Amplify `signUp` with { username: email, password, options.userAttributes.email }
 *  - surfaces UsernameExistsException as a typed CognitoSignUpError
 *  - mock-mode short-circuit returns CONFIRM_SIGN_UP without hitting Amplify
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

// Amplify mock — the hook dynamic-imports `aws-amplify/auth`.
const mockSignUp = vi.fn();
vi.mock("aws-amplify/auth", () => ({
  signUp: mockSignUp,
  fetchAuthSession: vi.fn().mockResolvedValue({ tokens: undefined }),
}));

import { useCognitoSignUp, CognitoSignUpError } from "../useCognitoSignUp";

function makeWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  }
  Wrapper.displayName = "Wrapper";
  return Wrapper;
}

describe("useCognitoSignUp", () => {
  const originalMockEnv = process.env.NEXT_PUBLIC_USE_MOCK_AUTH;

  beforeEach(() => {
    mockSignUp.mockReset();
    // Default: NOT mock mode (so the hook calls Amplify).
    process.env.NEXT_PUBLIC_USE_MOCK_AUTH = "false";
  });

  afterEach(() => {
    process.env.NEXT_PUBLIC_USE_MOCK_AUTH = originalMockEnv;
  });

  it("calls Amplify signUp with username=email, password, and userAttributes.email", async () => {
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

    const { result } = renderHook(() => useCognitoSignUp(), {
      wrapper: makeWrapper(),
    });

    await act(async () => {
      result.current.mutate({
        email: "mike@apex.example.com",
        password: "ValidPass1!xxx",
      });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockSignUp).toHaveBeenCalledTimes(1);
    expect(mockSignUp).toHaveBeenCalledWith({
      username: "mike@apex.example.com",
      password: "ValidPass1!xxx",
      options: { userAttributes: { email: "mike@apex.example.com" } },
    });

    expect(result.current.data?.isSignUpComplete).toBe(false);
    expect(result.current.data?.nextStep.signUpStep).toBe("CONFIRM_SIGN_UP");
  });

  it("surfaces UsernameExistsException as a typed CognitoSignUpError", async () => {
    const amplifyErr = new Error("User already exists");
    (amplifyErr as { name: string }).name = "UsernameExistsException";
    mockSignUp.mockRejectedValue(amplifyErr);

    const { result } = renderHook(() => useCognitoSignUp(), {
      wrapper: makeWrapper(),
    });

    await act(async () => {
      result.current.mutate({
        email: "dup@example.com",
        password: "ValidPass1!xxx",
      });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBeInstanceOf(CognitoSignUpError);
    expect((result.current.error as CognitoSignUpError).code).toBe(
      "UsernameExistsException",
    );
    expect(mockSignUp).toHaveBeenCalledTimes(1);
  });

  it("mock-mode short-circuits to CONFIRM_SIGN_UP without calling Amplify", async () => {
    process.env.NEXT_PUBLIC_USE_MOCK_AUTH = "true";

    const { result } = renderHook(() => useCognitoSignUp(), {
      wrapper: makeWrapper(),
    });

    await act(async () => {
      result.current.mutate({
        email: "mock@pilot-dev.example.com",
        password: "MockPass1!xxx",
      });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockSignUp).not.toHaveBeenCalled();
    expect(result.current.data?.nextStep.signUpStep).toBe("CONFIRM_SIGN_UP");
    expect(result.current.data?.isSignUpComplete).toBe(false);
  });

  it("maps InvalidPasswordException to the correct code", async () => {
    const amplifyErr = new Error("Password too weak");
    (amplifyErr as { name: string }).name = "InvalidPasswordException";
    mockSignUp.mockRejectedValue(amplifyErr);

    const { result } = renderHook(() => useCognitoSignUp(), {
      wrapper: makeWrapper(),
    });

    await act(async () => {
      result.current.mutate({
        email: "mike@apex.example.com",
        password: "weak",
      });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect((result.current.error as CognitoSignUpError).code).toBe(
      "InvalidPasswordException",
    );
  });
});
