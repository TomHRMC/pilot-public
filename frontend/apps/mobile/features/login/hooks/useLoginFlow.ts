/**
 * useLoginFlow — mobile
 *
 * Location: apps/mobile/features/login/hooks/useLoginFlow.ts
 *
 * Same as web hook but with haptic feedback on error.
 * Platform-specific side effects only.
 *
 * FE-B2: design doc §A.2 useLoginFlow hook (mobile)
 */

import { useState, useCallback } from "react";
import { Platform } from "react-native";
import * as Haptics from "expo-haptics";
import type { SignInOutput } from "aws-amplify/auth";
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
  const { signIn, confirmMfaChallenge, role } = useAuth();
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
          onSuccess(role ?? "owner");
          return;
        }

        const mfaMethod = extractMfaMethod(nextStep.signInStep);
        if (mfaMethod !== null) {
          setMfaChallenge({
            challengeName: mfaMethod,
            destination: extractDestination(nextStep),
          });
          setStep("mfa-challenge");
          return;
        }

        if (
          nextStep.signInStep === "CONTINUE_SIGN_IN_WITH_MFA_SETUP_SELECTION" ||
          nextStep.signInStep === "CONTINUE_SIGN_IN_WITH_TOTP_SETUP"
        ) {
          setStep("mfa-enrollment-required");
          return;
        }

        setError("Sign-in requires additional steps. Please contact support.");
      } catch (err) {
        // Log full error to Metro console so we can diagnose Amplify errors
        // Amplify errors have: name, message, underlyingError, recoverySuggestion
        console.error(
          "[useLoginFlow] signIn error full object:",
          JSON.stringify(err, null, 2),
        );
        console.error(
          "[useLoginFlow] err instanceof Error:",
          err instanceof Error,
        );
        if (err instanceof Error) {
          console.error(
            "[useLoginFlow] name:",
            err.name,
            "message:",
            err.message,
          );
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const cause = (err as any).underlyingError ?? (err as any).cause;
          if (cause) console.error("[useLoginFlow] underlying cause:", cause);
        }

        // Build user-facing message from all available error info
        let message = "Sign-in failed. Please try again.";
        if (err instanceof Error) {
          const errAny = err as {
            name?: string;
            message?: string;
            underlyingError?: Error;
            recoverySuggestion?: string;
          };
          const name =
            errAny.name && errAny.name !== "Error" ? errAny.name : null;
          const msg =
            errAny.message &&
            errAny.message !== "An unknown error has occurred."
              ? errAny.message
              : null;
          const suggestion = errAny.recoverySuggestion ?? null;
          const underlying = errAny.underlyingError?.message ?? null;

          if (msg) {
            message = name ? `${name}: ${msg}` : msg;
          } else if (name) {
            message = name;
          } else if (underlying) {
            message = `Network error: ${underlying}`;
          } else if (suggestion) {
            message = suggestion;
          } else {
            message = "Sign-in failed — check Metro console for details.";
          }
        }
        setError(message);
        // Haptic feedback on error (native only — expo-haptics is empty on web)
        if (Platform.OS !== "web") {
          void Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
        }
      } finally {
        setIsLoading(false);
      }
    },
    [signIn, onSuccess, role],
  );

  const submitMfaCode = useCallback(
    async (code: string) => {
      setError(null);
      setIsLoading(true);

      try {
        const { nextStep } = await confirmMfaChallenge(code);

        if (nextStep.signInStep === "DONE") {
          onSuccess(role ?? "owner");
          return;
        }

        setError("Verification failed. Please try again.");
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Incorrect code. Try again.";
        setError(message);
        void Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
      } finally {
        setIsLoading(false);
      }
    },
    [confirmMfaChallenge, onSuccess, role],
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
