/**
 * useLoginFlow — web
 *
 * Location: apps/web/src/features/login/hooks/useLoginFlow.ts
 *
 * Encapsulates login form state, signIn call, MFA challenge handling,
 * error management, and post-login redirect.
 *
 * Step machine:
 *   'credentials' → 'mfa-challenge' → (done) calls onSuccess
 *   'credentials' → 'mfa-enrollment-required' (if tenant requires MFA but no methods enrolled)
 *
 * FE-B2: design doc §A.2 useLoginFlow hook specification
 */

import { useState, useCallback, useRef } from "react";
import type { SignInOutput } from "aws-amplify/auth";
import { useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@pilot/ui/auth";
import type { PilotRole } from "@pilot/ui/auth";

export type MfaMethod = "TOTP" | "SMS_MFA" | "EMAIL_OTP" | "SOFTWARE_TOKEN_MFA";

type LoginStep = "credentials" | "mfa-challenge" | "mfa-enrollment-required";

export interface UseLoginFlowResult {
  step: LoginStep;
  isLoading: boolean;
  error: string | null;
  mfaChallenge: { challengeName: MfaMethod; destination?: string } | null;
  submitCredentials: (email: string, password: string) => Promise<void>;
  submitMfaCode: (code: string) => Promise<void>;
  cancelMfa: () => void;
  clearError: () => void;
  /** Email retained for MFA step (needed for password reset "resend" context) */
  email: string;
}

function extractMfaMethod(
  signInStep: SignInOutput["nextStep"]["signInStep"],
): MfaMethod | null {
  switch (signInStep) {
    case "CONFIRM_SIGN_IN_WITH_TOTP_CODE":
      return "TOTP";
    case "CONFIRM_SIGN_IN_WITH_SMS_CODE":
      return "SMS_MFA";
    case "CONFIRM_SIGN_IN_WITH_EMAIL_CODE":
      return "EMAIL_OTP";
    default:
      return null;
  }
}

function extractDestination(
  nextStep: SignInOutput["nextStep"],
): string | undefined {
  if (
    "codeDeliveryDetails" in nextStep &&
    nextStep.codeDeliveryDetails?.destination
  ) {
    return nextStep.codeDeliveryDetails.destination;
  }
  return undefined;
}

export function useLoginFlow(
  onSuccess: (role: PilotRole) => void,
): UseLoginFlowResult {
  // PLP-FIX-7: whenSessionReady lets us await the resolved user (post-Cognito
  // backend fetch) before routing — eliminates the role race (INV-BUG-2).
  const { signIn, confirmMfaChallenge, whenSessionReady } = useAuth();
  // PLP-FIX-9 (INV-BUG-7): clear the query cache when a DIFFERENT user logs in
  // without an intervening sign-out (expired-session re-login as someone else).
  const queryClient = useQueryClient();
  const previousUserIdRef = useRef<string | null>(null);
  const [step, setStep] = useState<LoginStep>("credentials");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mfaChallenge, setMfaChallenge] = useState<{
    challengeName: MfaMethod;
    destination?: string;
  } | null>(null);
  const [email, setEmail] = useState("");

  const submitCredentials = useCallback(
    async (emailInput: string, password: string) => {
      setEmail(emailInput);
      setError(null);
      setIsLoading(true);

      try {
        const { nextStep } = await signIn(emailInput, password);

        if (nextStep.signInStep === "DONE") {
          // PLP-FIX-7: Await the resolved user from the auth context.
          // The AuthProvider's signIn already called fetchUserFromBackend
          // and setUser — whenSessionReady returns the userRef synchronously.
          // Delete the `?? "owner"` default — never default-route (INV-BUG-2).
          const user = whenSessionReady ? await whenSessionReady() : null;
          if (user) {
            // PLP-FIX-9 (INV-BUG-7): if this is a different user than the
            // previous session, clear the query cache so stale tenant-scoped
            // data from the prior user never renders. Same-user re-login
            // (e.g. token refresh) needs no clear.
            if (
              previousUserIdRef.current !== null &&
              previousUserIdRef.current !== user.id
            ) {
              queryClient.clear();
            }
            previousUserIdRef.current = user.id;
            onSuccess(user.role);
          } else {
            // User failed to resolve within the bounded wait — stay on /login.
            setError("Sign-in failed. Please try again.");
          }
          return;
        }

        // Check for MFA challenge
        const mfaMethod = extractMfaMethod(nextStep.signInStep);
        if (mfaMethod !== null) {
          setMfaChallenge({
            challengeName: mfaMethod,
            destination: extractDestination(nextStep),
          });
          setStep("mfa-challenge");
          return;
        }

        // MFA enrollment required
        if (
          nextStep.signInStep === "CONTINUE_SIGN_IN_WITH_MFA_SETUP_SELECTION" ||
          nextStep.signInStep === "CONTINUE_SIGN_IN_WITH_TOTP_SETUP"
        ) {
          setStep("mfa-enrollment-required");
          return;
        }

        // Any other unhandled next step
        setError("Sign-in requires additional steps. Please contact support.");
      } catch (err) {
        const message =
          err instanceof Error
            ? err.message
            : "Sign-in failed. Please try again.";
        setError(message);
      } finally {
        setIsLoading(false);
      }
    },
    [signIn, onSuccess, whenSessionReady, queryClient],
  );

  const submitMfaCode = useCallback(
    async (code: string) => {
      setError(null);
      setIsLoading(true);

      try {
        const { nextStep } = await confirmMfaChallenge(code);

        if (nextStep.signInStep === "DONE") {
          // PLP-FIX-7: Await the resolved user — same fix as submitCredentials.
          // Delete the `?? "owner"` default (INV-BUG-2).
          const user = whenSessionReady ? await whenSessionReady() : null;
          if (user) {
            // PLP-FIX-9 (INV-BUG-7): same different-user cache clear as submitCredentials
            if (
              previousUserIdRef.current !== null &&
              previousUserIdRef.current !== user.id
            ) {
              queryClient.clear();
            }
            previousUserIdRef.current = user.id;
            onSuccess(user.role);
          } else {
            setError("Sign-in failed. Please try again.");
          }
          return;
        }

        setError("Verification failed. Please try again.");
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Incorrect code. Try again.";
        setError(message);
      } finally {
        setIsLoading(false);
      }
    },
    [confirmMfaChallenge, onSuccess, whenSessionReady, queryClient],
  );

  const cancelMfa = useCallback(() => {
    setStep("credentials");
    setMfaChallenge(null);
    setError(null);
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    step,
    isLoading,
    error,
    mfaChallenge,
    submitCredentials,
    submitMfaCode,
    cancelMfa,
    clearError,
    email,
  };
}
