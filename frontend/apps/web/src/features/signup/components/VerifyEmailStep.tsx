/**
 * VerifyEmailStep — email-confirmation step for the self-serve signup flow
 *
 * Location: apps/web/src/features/signup/components/VerifyEmailStep.tsx
 *
 * SIGNUP-GA-1 (ADR-0011): the user enters the 6-digit Cognito verification
 * code. On submit:
 *   1. confirmSignUp (Amplify, dynamic import) — fires the Post-Confirmation
 *      Lambda (Path 3) which creates the tenant + owner user.
 *   2. Auto-sign-in (signIn from useAuth) using the email+password held
 *      in-memory (signupPendingCredential). Wizard steps 2–5 are JWT-gated.
 *   3. POST /api/v1/signup (resolve-or-attach) — overwrites the placeholder
 *      tenant name with business_name; persists tenant_id to sessionStorage.
 *   4. router.push("/signup/legal").
 *
 * Hard-reload fallback: if the in-memory password is gone (full reload), the
 * user can still confirm the code, but after ConfirmSignUp we route to
 * /login?confirmed=true (manual sign-in) instead of auto-sign-in. The
 * password is NEVER persisted to sessionStorage.
 *
 * Error mapping (inline, non-color-only):
 *   CodeMismatchException → "That code doesn't match…"
 *   ExpiredCodeException   → "That code expired…" (surface resend)
 *   LimitExceededException → "Too many attempts…"
 *
 * Resend: resendSignUpCode with a 30–60s cooldown.
 */

"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiClient } from "@pilot/shared-api";
import { useAuth } from "@pilot/ui/auth";
import { useNotificationQueue } from "@pilot/ui/notification-banner";
import { WizardProgressBar } from "@/features/signup/components/WizardProgressBar";
import { WIZARD_TENANT_ID_KEY } from "@/features/signup/types";
import type {
  SignupInitiateRequest,
  SignupInitiateResponse,
} from "@/features/signup/types";
import {
  consumeSignupPendingCredential,
  peekSignupPendingCredential,
} from "@/features/signup/signupPendingCredential";

const RESEND_COOLDOWN_SECONDS = 30;

type VerifyErrorCode =
  | "CodeMismatchException"
  | "ExpiredCodeException"
  | "LimitExceededException"
  | "UserNotFoundException"
  | "unknown";

class VerifyError extends Error {
  code: VerifyErrorCode;
  constructor(code: VerifyErrorCode, message: string) {
    super(message);
    this.name = "VerifyError";
    this.code = code;
  }
}

function isMockMode(): boolean {
  return process.env.NEXT_PUBLIC_USE_MOCK_AUTH === "true";
}

function mapAmplifyError(err: unknown): VerifyError {
  const name = (err as { name?: string } | undefined)?.name ?? "unknown";
  const message =
    (err as { message?: string } | undefined)?.message ??
    "Verification failed. Please try again.";
  const code: VerifyErrorCode =
    name === "CodeMismatchException"
      ? "CodeMismatchException"
      : name === "ExpiredCodeException"
        ? "ExpiredCodeException"
        : name === "LimitExceededException"
          ? "LimitExceededException"
          : name === "UserNotFoundException"
            ? "UserNotFoundException"
            : "unknown";
  return new VerifyError(code, message);
}

export function VerifyEmailStep() {
  const router = useRouter();
  const { signIn } = useAuth();
  const { addNotification } = useNotificationQueue();

  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  // SIGNUP-UI-FIX-2 Task 2: "provisioning" phase covers the gap between
  // confirmSignUp succeeding and the wizard advancing — auto-sign-in +
  // POST /api/v1/signup + Post-Confirmation Lambda. During this window the
  // button reads "Setting up your account…" (not "Verifying…").
  const [phase, setPhase] = useState<"verifying" | "provisioning">("verifying");
  const [isResending, setIsResending] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);

  // Read the pending credential (email + password + business fields) held
  // in-memory from the account page. Peek (don't consume) so a re-render
  // or failed submit doesn't lose it. Lazy-init state reads it once on mount.
  const [pending] = useState(() => peekSignupPendingCredential());
  const hasPassword = !!pending?.password;
  const email = pending?.email ?? "";

  // Cooldown ticker
  useEffect(() => {
    if (resendCooldown <= 0) return;
    const t = setTimeout(() => setResendCooldown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [resendCooldown]);

  // If there's no pending credential at all (e.g. user navigated directly),
  // send them back to the account page to start over.
  useEffect(() => {
    if (!pending) {
      router.replace("/signup/account");
    }
  }, [router, pending]);

  const handleConfirm = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;

    setError(null);
    setIsSubmitting(true);
    setPhase("verifying");

    try {
      // 1. ConfirmSignUp (Amplify, dynamic import) — fires the Lambda.
      if (isMockMode()) {
        // Mock short-circuit — no real Cognito.
      } else {
        const { confirmSignUp } = await import("aws-amplify/auth");
        await confirmSignUp({
          username: email,
          confirmationCode: code.trim(),
        });
      }

      // SIGNUP-UI-FIX-2 Task 2: confirm succeeded — switch to the
      // provisioning phase. The remaining steps (auto-sign-in, POST
      // /api/v1/signup, Lambda provisioning) take a perceptible moment;
      // the button now reads "Setting up your account…" instead of
      // staying on "Verifying…".
      setPhase("provisioning");

      // 2. Auto-sign-in (if we have the password in memory) OR route to
      //    /login?confirmed=true (hard-reload fallback).
      if (hasPassword && pending) {
        const { nextStep } = await signIn(email, pending.password);
        if (nextStep.signInStep !== "DONE") {
          // Defensive: a brand-new self-serve owner has no MFA yet, so DONE
          // is expected. If a non-DONE step returns, route to /login with a
          // friendly message rather than crashing.
          router.replace(
            `/login?confirmed=true&email=${encodeURIComponent(email)}`,
          );
          return;
        }
      } else {
        // Password gone (hard reload) — manual sign-in.
        router.replace(
          `/login?confirmed=true&email=${encodeURIComponent(email)}`,
        );
        return;
      }

      // 3. POST /api/v1/signup (resolve-or-attach) — now authenticated.
      const cred = consumeSignupPendingCredential();
      if (cred) {
        const body: SignupInitiateRequest = {
          business_name: cred.businessFields.business_name,
          trade: cred.businessFields.trade,
          business_size: cred.businessFields.business_size,
          zip: cred.businessFields.zip,
          time_zone: cred.businessFields.time_zone,
          owner_email: cred.businessFields.owner_email,
          owner_first_name: cred.businessFields.owner_first_name,
          owner_last_name: cred.businessFields.owner_last_name,
        };
        const response = await apiClient.post<SignupInitiateResponse>(
          "/api/v1/signup",
          body,
        );
        sessionStorage.setItem(WIZARD_TENANT_ID_KEY, response.data.tenant_id);
      }

      // 4. Hand off to the wizard (JWT-gated).
      router.push("/signup/legal");
    } catch (err: unknown) {
      // Amplify errors → inline mapped messages.
      if (err && typeof err === "object" && ("name" in err || "code" in err)) {
        const mapped = mapAmplifyError(err);
        if (mapped.code === "CodeMismatchException") {
          setError("That code doesn't match. Check your email and try again.");
        } else if (mapped.code === "ExpiredCodeException") {
          setError("That code expired. Request a new one.");
        } else if (mapped.code === "LimitExceededException") {
          setError("Too many attempts. Wait a minute and try again.");
        } else if (mapped.code === "UserNotFoundException") {
          setError(
            "We couldn't find that account. Check your email or start over.",
          );
        } else {
          setError(mapped.message);
        }
      } else {
        setError("Verification failed. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResend = async () => {
    if (!email || resendCooldown > 0) return;
    setIsResending(true);
    try {
      if (!isMockMode()) {
        const { resendSignUpCode } = await import("aws-amplify/auth");
        await resendSignUpCode({ username: email });
      }
      addNotification({
        id: `signup-resend-${Date.now()}`,
        severity: "success",
        title: "A new code was sent to your email.",
      });
      setResendCooldown(RESEND_COOLDOWN_SECONDS);
    } catch (err: unknown) {
      const mapped = mapAmplifyError(err);
      setError(mapped.message);
    } finally {
      setIsResending(false);
    }
  };

  return (
    <div className="flex flex-col gap-8">
      <WizardProgressBar currentStep="verify" />

      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-bold text-neutral-900">
          Verify your email
        </h1>
        <p className="text-sm text-neutral-600">
          {email
            ? `Enter the 6-digit code we sent to ${email}.`
            : "Enter the 6-digit code we sent to your email."}
        </p>
      </div>

      <form
        onSubmit={handleConfirm}
        noValidate
        className="flex flex-col gap-5"
        data-testid="signup-verify-form"
      >
        <div className="flex flex-col gap-1">
          <label
            htmlFor="verification-code"
            className="text-sm font-medium text-neutral-800"
          >
            Verification code <span className="text-fault-600">*</span>
          </label>
          <input
            id="verification-code"
            type="text"
            inputMode="numeric"
            autoComplete="one-time-code"
            value={code}
            onChange={(e) => {
              setCode(e.target.value);
              setError(null);
            }}
            placeholder="123456"
            maxLength={6}
            aria-invalid={!!error}
            aria-describedby={error ? "verify-error" : undefined}
            data-testid="field-verification-code"
            className={`
              w-full rounded-lg border px-3 py-2.5 text-sm tracking-widest focus:outline-none
              focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2
              ${error ? "border-fault-600 bg-fault-50" : "border-neutral-300"}
            `}
          />
          {error && (
            <p
              id="verify-error"
              className="text-fault-600 text-xs mt-0.5"
              role="alert"
            >
              {error}
            </p>
          )}
        </div>

        <button
          type="submit"
          disabled={isSubmitting || code.trim().length === 0}
          data-testid="signup-verify-continue"
          aria-disabled={isSubmitting || code.trim().length === 0}
          className={`
            w-full py-3 px-6 rounded-lg text-sm font-semibold transition-colors
            focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2
            ${
              isSubmitting || code.trim().length === 0
                ? "opacity-40 cursor-not-allowed bg-brand-600 text-white"
                : "bg-brand-600 hover:bg-brand-800 text-white"
            }
          `}
          // SIGNUP-UI-FIX-2 Task 2: aria-live announces the copy transition
          // from "Verifying…" → "Setting up your account…" so screen-reader
          // users know provisioning is in progress (not stuck on verify).
          aria-live="polite"
        >
          {isSubmitting
            ? phase === "provisioning"
              ? "Setting up your account…"
              : "Verifying…"
            : "Verify & continue →"}
        </button>
      </form>

      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={handleResend}
          disabled={resendCooldown > 0 || isResending}
          data-testid="signup-verify-resend"
          className={`
            text-sm font-medium focus:outline-none focus-visible:ring-2
            focus-visible:ring-brand-600 focus-visible:ring-offset-2 rounded
            ${
              resendCooldown > 0 || isResending
                ? "text-neutral-400 cursor-not-allowed"
                : "text-brand-600 hover:text-brand-800 underline"
            }
          `}
        >
          {isResending
            ? "Sending…"
            : resendCooldown > 0
              ? `Resend code in ${resendCooldown}s`
              : "Resend code"}
        </button>
        <a
          href="/signup/account"
          className="text-sm text-neutral-500 hover:text-neutral-700 underline focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2 rounded"
        >
          Use a different email
        </a>
      </div>
    </div>
  );
}
