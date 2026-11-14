/**
 * useCognitoSignUp — Cognito self-sign-up via Amplify (SIGNUP-GA-1 / ADR-0011)
 *
 * Location: apps/web/src/features/signup/hooks/useCognitoSignUp.ts
 *
 * Calls Cognito `signUp` (email + password) via a DYNAMIC import of
 * `aws-amplify/auth` — never a static top-level import (keeps Amplify out of
 * the SSR bundle; mirrors AuthProvider.tsx:194).
 *
 * Mock mode: when NEXT_PUBLIC_USE_MOCK_AUTH === "true", Amplify is not
 * configured (no real pool). The hook short-circuits to a fake
 * "CONFIRM_SIGN_UP" nextStep so local dev + tests never hit real Cognito.
 *
 * Error mapping: UsernameExistsException → thrown as a typed
 * `CognitoSignUpError` with `code: "UsernameExistsException"` so the account
 * page can surface the existing inline "already exists" + "Sign in instead"
 * UX (same as the legacy 409 path).
 */

"use client";

import { useMutation } from "@tanstack/react-query";
import type { SignUpOutput } from "aws-amplify/auth";

export type CognitoSignUpErrorCode =
  | "UsernameExistsException"
  | "InvalidPasswordException"
  | "LimitExceededException"
  | "unknown";

export class CognitoSignUpError extends Error {
  code: CognitoSignUpErrorCode;
  constructor(code: CognitoSignUpErrorCode, message: string) {
    super(message);
    this.name = "CognitoSignUpError";
    this.code = code;
  }
}

export interface CognitoSignUpVariables {
  email: string;
  password: string;
}

export interface CognitoSignUpResult {
  isSignUpComplete: boolean;
  userId?: string;
  nextStep: SignUpOutput["nextStep"];
}

function isMockMode(): boolean {
  return process.env.NEXT_PUBLIC_USE_MOCK_AUTH === "true";
}

export function useCognitoSignUp() {
  return useMutation<
    CognitoSignUpResult,
    CognitoSignUpError,
    CognitoSignUpVariables
  >({
    mutationFn: async ({ email, password }: CognitoSignUpVariables) => {
      // Mock-mode short-circuit — no real Cognito pool configured.
      if (isMockMode()) {
        return {
          isSignUpComplete: false,
          userId: "mock-user-id",
          nextStep: {
            signUpStep: "CONFIRM_SIGN_UP",
            codeDeliveryDetails: {
              deliveryMedium: "EMAIL",
              destination: email,
              attributeName: "email",
            },
          },
        };
      }

      const { signUp } = await import("aws-amplify/auth");

      try {
        const res = await signUp({
          username: email,
          password,
          options: { userAttributes: { email } },
        });
        return {
          isSignUpComplete: res.isSignUpComplete,
          userId: res.userId,
          nextStep: res.nextStep,
        };
      } catch (err: unknown) {
        // Amplify errors carry a `name` property matching the Cognito
        // exception class.
        const name = (err as { name?: string } | undefined)?.name ?? "unknown";
        const message =
          (err as { message?: string } | undefined)?.message ??
          "Sign-up failed. Please try again.";

        const code: CognitoSignUpErrorCode =
          name === "UsernameExistsException"
            ? "UsernameExistsException"
            : name === "InvalidPasswordException"
              ? "InvalidPasswordException"
              : name === "LimitExceededException"
                ? "LimitExceededException"
                : "unknown";

        throw new CognitoSignUpError(code, message);
      }
    },
    retry: false,
  });
}
