/**
 * InviteVerifyStep — TEAM-INVITE-2
 *
 * Location: apps/web/src/features/users/components/InviteVerifyStep.tsx
 *
 * The 6-digit verification-code step of the invite-landing accept flow.
 * Mirrors `VerifyEmailStep.tsx` (confirm → signIn → route) — but NEVER calls
 * `POST /api/v1/signup` (that is the owner Path 3 provisioner; design §G.2).
 * The Post-Confirmation Lambda Path 2 attaches the invitee to the inviting
 * tenant at `ConfirmSignUp` time.
 *
 * Role-branched completion (design §G.1):
 *  - office_staff / accountant / owner → auto-signIn → router.replace("/dashboard")
 *  - technician / null → terminal "open the mobile app" panel (no web sign-in;
 *    technicians are blocked from web post-login per usePostLoginRedirect.ts).
 *
 * WCAG 2.2 AA (§36):
 *  - Paste MUST work on the code input (Accessible Authentication 3.3.8).
 *  - ≥44 px primary submit target.
 *  - aria-invalid + aria-describedby non-color-only errors.
 */

"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@pilot/ui/auth";
import { useNotificationQueue } from "@pilot/ui/notification-banner";

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

interface InviteVerifyStepProps {
  email: string;
  /** In-memory from the form step — never persisted. */
  password: string;
  /** From the public invite fetch — drives the §G.1 branch. */
  roleCode: string | null;
}

const OFFICE_ROLES = ["office_staff", "accountant", "owner"];

export function InviteVerifyStep({
  email,
  password,
  roleCode,
}: InviteVerifyStepProps) {
  const router = useRouter();
  const { signIn } = useAuth();
  const { addNotification } = useNotificationQueue();

  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  // "provisioning" covers the gap between confirmSignUp succeeding and the
  // role-branched completion (signIn / panel render). Button reads
  // "Setting up your account…" during this window (SIGNUP-UI-FIX-2 pattern).
  const [phase, setPhase] = useState<"verifying" | "provisioning">("verifying");
  const [isResending, setIsResending] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);
  // Terminal state for technician/null role (§G.1 State 3b).
  const [joinedMobile, setJoinedMobile] = useState(false);

  const isOfficeRole = roleCode ? OFFICE_ROLES.includes(roleCode) : false;

  // Cooldown ticker
  useEffect(() => {
    if (resendCooldown <= 0) return;
    const t = setTimeout(() => setResendCooldown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [resendCooldown]);

  const handleConfirm = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;

    setError(null);
    setIsSubmitting(true);
    setPhase("verifying");

    try {
      // 1. ConfirmSignUp (Amplify, dynamic import) — fires the Lambda Path 2.
      if (isMockMode()) {
        // Mock short-circuit — no real Cognito.
      } else {
        const { confirmSignUp } = await import("aws-amplify/auth");
        await confirmSignUp({
          username: email,
          confirmationCode: code.trim(),
        });
      }

      // Confirm succeeded — switch to the provisioning phase.
      setPhase("provisioning");

      // 2. Role-branched completion (design §G.1).
      if (isOfficeRole) {
        const { nextStep } = await signIn(email, password);
        if (nextStep.signInStep === "DONE") {
          router.replace("/dashboard");
        } else {
          // Defensive (§G.6): non-DONE step → route to /login.
          router.replace(
            `/login?confirmed=true&email=${encodeURIComponent(email)}`,
          );
        }
      } else {
        // technician / null → terminal mobile-app panel (no web sign-in).
        setJoinedMobile(true);
      }
    } catch (err: unknown) {
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
        id: `invite-resend-${Date.now()}`,
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

  // ─── Terminal: technician mobile-app panel (§G.1 State 3b) ──────────────
  if (joinedMobile) {
    return (
      <div
        data-testid="invite-joined-mobile"
        className="mt-8 rounded-lg border border-success-200 bg-success-50 px-6 py-8 text-center"
      >
        <h2 className="text-lg font-semibold text-neutral-900">
          You{"'"}re in, <span className="text-brand-600">{email}</span>!
        </h2>
        <p className="mt-2 text-sm text-neutral-600">
          Open the Pilot mobile app and sign in with this email to get started.
        </p>
      </div>
    );
  }

  return (
    <div data-testid="invite-verify-step" className="mt-8">
      <div className="mb-5">
        <h2 className="text-lg font-semibold text-neutral-900">
          Check your email
        </h2>
        <p className="mt-1 text-sm text-neutral-600">
          Enter the 6-digit code we sent to{" "}
          <strong className="text-neutral-800">{email}</strong>.
        </p>
      </div>

      <form onSubmit={handleConfirm} noValidate className="flex flex-col gap-5">
        <div className="flex flex-col gap-1">
          <label
            htmlFor="invite-verification-code"
            className="text-sm font-medium text-neutral-800"
          >
            Verification code <span className="text-fault-600">*</span>
          </label>
          <input
            id="invite-verification-code"
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
            aria-describedby={error ? "invite-verify-error" : undefined}
            data-testid="invite-code-input"
            className={`
              w-full rounded-lg border px-3 py-2.5 text-sm tracking-widest focus:outline-none
              focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2
              ${error ? "border-fault-600 bg-fault-50" : "border-neutral-300"}
            `}
          />
          {error && (
            <p
              id="invite-verify-error"
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
          data-testid="invite-verify-submit"
          aria-disabled={isSubmitting || code.trim().length === 0}
          aria-live="polite"
          className={`
            w-full py-3.5 px-6 rounded-lg text-sm font-semibold transition-colors
            focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2
            ${
              isSubmitting || code.trim().length === 0
                ? "opacity-40 cursor-not-allowed bg-brand-600 text-white"
                : "bg-brand-600 hover:bg-brand-800 text-white"
            }
          `}
        >
          {isSubmitting
            ? phase === "provisioning"
              ? "Setting up your account…"
              : "Verifying…"
            : "Verify"}
        </button>
      </form>

      <div className="mt-4">
        <button
          type="button"
          onClick={handleResend}
          disabled={resendCooldown > 0 || isResending}
          data-testid="invite-resend-code"
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
      </div>
    </div>
  );
}
