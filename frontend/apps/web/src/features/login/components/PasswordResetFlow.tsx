/**
 * PasswordResetFlow — web
 *
 * Location: apps/web/src/features/login/components/PasswordResetFlow.tsx
 *
 * Three-step Cognito forgotPassword flow:
 *   Step 1: request-reset — email input → calls resetPassword()
 *   Step 2: enter-code   — code + new password + confirm
 *   Step 3: success      — confirmation with link to /login
 *
 * Single page with internal step transitions (no URL params) per design doc §G.3.
 *
 * FE-B2: design doc §A.2 PasswordResetFlow (web)
 */

"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useNotificationQueue } from "@pilot/ui/notification-banner";

interface PasswordResetFlowProps {
  onSuccess: () => void;
}

type ResetStep = "request-reset" | "enter-code" | "success";

// Cognito password policy: min 12 chars, requires lowercase, uppercase, numbers, symbols
const PASSWORD_MIN_LENGTH = 12;
const PASSWORD_REGEX =
  /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z\d]).{12,}$/;

function maskEmail(email: string): string {
  const [local, domain] = email.split("@");
  if (!local || !domain) return email;
  const masked = local.slice(0, 1) + "***";
  return `${masked}@${domain}`;
}

export function PasswordResetFlow({ onSuccess }: PasswordResetFlowProps) {
  const { addNotification } = useNotificationQueue();
  const [step, setStep] = useState<ResetStep>("request-reset");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [passwordErrors, setPasswordErrors] = useState<string[]>([]);

  function validatePassword(pw: string): string[] {
    const errors: string[] = [];
    if (pw.length < PASSWORD_MIN_LENGTH) {
      errors.push(`At least ${PASSWORD_MIN_LENGTH} characters`);
    }
    if (!/[a-z]/.test(pw)) errors.push("One lowercase letter");
    if (!/[A-Z]/.test(pw)) errors.push("One uppercase letter");
    if (!/\d/.test(pw)) errors.push("One number");
    if (!/[^A-Za-z\d]/.test(pw)) errors.push("One special character");
    return errors;
  }

  async function handleRequestReset(e: React.FormEvent) {
    e.preventDefault();
    setIsLoading(true);
    try {
      const { resetPassword } = await import("aws-amplify/auth");
      await resetPassword({ username: email });
      setStep("enter-code");
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : "Failed to send reset code. Try again.";
      addNotification({
        id: `reset-error-${Date.now()}`,
        severity: "error",
        title: message,
      });
    } finally {
      setIsLoading(false);
    }
  }

  async function handleConfirmReset(e: React.FormEvent) {
    e.preventDefault();

    const errors = validatePassword(newPassword);
    setPasswordErrors(errors);
    if (errors.length > 0) return;

    if (newPassword !== confirmPassword) {
      addNotification({
        id: `reset-mismatch-${Date.now()}`,
        severity: "error",
        title: "Passwords do not match.",
      });
      return;
    }

    setIsLoading(true);
    try {
      const { confirmResetPassword } = await import("aws-amplify/auth");
      await confirmResetPassword({
        username: email,
        confirmationCode: code,
        newPassword,
      });
      setStep("success");
      onSuccess();
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : "Failed to reset password. Check your code and try again.";
      addNotification({
        id: `reset-confirm-error-${Date.now()}`,
        severity: "error",
        title: message,
      });
    } finally {
      setIsLoading(false);
    }
  }

  async function handleResendCode() {
    setIsLoading(true);
    try {
      const { resetPassword } = await import("aws-amplify/auth");
      await resetPassword({ username: email });
      addNotification({
        id: `resend-code-${Date.now()}`,
        severity: "success",
        title: "Code resent. Check your email.",
      });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to resend code.";
      addNotification({
        id: `resend-error-${Date.now()}`,
        severity: "error",
        title: message,
      });
    } finally {
      setIsLoading(false);
    }
  }

  if (step === "success") {
    return (
      <div className="flex flex-col gap-4 text-center" role="status">
        <div className="flex flex-col gap-2">
          <h2 className="text-h2 text-neutral-900">Password updated!</h2>
          <p className="text-body text-neutral-600">
            Your password has been successfully reset.
          </p>
        </div>
        <Link
          href="/login?passwordReset=true"
          className="inline-block rounded-md bg-brand-600 px-4 py-2 text-body-lg text-white hover:bg-brand-800 focus:outline-none focus:ring-2 focus:ring-brand-600 focus:ring-offset-2"
        >
          Sign in
        </Link>
      </div>
    );
  }

  if (step === "enter-code") {
    return (
      <form
        onSubmit={(e) => void handleConfirmReset(e)}
        aria-label="Confirm password reset"
        className="flex flex-col gap-4"
      >
        {/* Step indicator */}
        <div className="flex items-center gap-2">
          <span className="text-caption text-neutral-400">Step</span>
          <span aria-current="step" className="text-caption text-brand-600">
            2 / 2
          </span>
        </div>

        <p className="text-body text-neutral-600">
          Code sent to{" "}
          <span className="text-neutral-900">{maskEmail(email)}</span>
        </p>

        <div className="flex flex-col gap-1">
          <label htmlFor="reset-code" className="text-body-lg text-neutral-900">
            Verification code
          </label>
          <input
            id="reset-code"
            type="text"
            inputMode="numeric"
            autoComplete="one-time-code"
            maxLength={6}
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
            required
            disabled={isLoading}
            placeholder="000000"
            aria-required="true"
            className="w-full rounded-md border border-neutral-200 px-4 py-2 text-body text-neutral-900 placeholder:text-neutral-400 focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600 disabled:opacity-50"
          />
        </div>

        <div className="flex flex-col gap-1">
          <label
            htmlFor="new-password"
            className="text-body-lg text-neutral-900"
          >
            New password
          </label>
          <input
            id="new-password"
            type="password"
            autoComplete="new-password"
            value={newPassword}
            onChange={(e) => {
              setNewPassword(e.target.value);
              setPasswordErrors([]);
            }}
            required
            disabled={isLoading}
            aria-required="true"
            aria-describedby="password-requirements"
            className="w-full rounded-md border border-neutral-200 px-4 py-2 text-body text-neutral-900 focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600 disabled:opacity-50"
          />
          <ul
            id="password-requirements"
            className="text-caption text-neutral-400 mt-1 flex flex-col gap-0"
          >
            <li>
              Min. {PASSWORD_MIN_LENGTH} characters, with uppercase, lowercase,
              number, symbol
            </li>
          </ul>
          {passwordErrors.length > 0 && (
            <ul role="alert" className="text-caption text-fault-600 mt-1">
              {passwordErrors.map((err) => (
                <li key={err}>{err}</li>
              ))}
            </ul>
          )}
        </div>

        <div className="flex flex-col gap-1">
          <label
            htmlFor="confirm-password"
            className="text-body-lg text-neutral-900"
          >
            Confirm new password
          </label>
          <input
            id="confirm-password"
            type="password"
            autoComplete="new-password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            disabled={isLoading}
            aria-required="true"
            className="w-full rounded-md border border-neutral-200 px-4 py-2 text-body text-neutral-900 focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600 disabled:opacity-50"
          />
        </div>

        <button
          type="submit"
          disabled={
            isLoading ||
            !code ||
            !newPassword ||
            !confirmPassword ||
            !PASSWORD_REGEX.test(newPassword)
          }
          className="w-full rounded-md bg-brand-600 px-4 py-2 text-body-lg text-white hover:bg-brand-800 focus:outline-none focus:ring-2 focus:ring-brand-600 focus:ring-offset-2 disabled:opacity-50"
          aria-busy={isLoading}
        >
          {isLoading ? "Resetting…" : "Reset password"}
        </button>

        <button
          type="button"
          onClick={() => void handleResendCode()}
          disabled={isLoading}
          className="text-caption text-brand-600 hover:underline focus:outline-none disabled:opacity-50"
        >
          Resend code
        </button>
      </form>
    );
  }

  // Step 1: request-reset
  return (
    <form
      onSubmit={(e) => void handleRequestReset(e)}
      aria-label="Request password reset"
      className="flex flex-col gap-4"
    >
      {/* Step indicator */}
      <div className="flex items-center gap-2">
        <span className="text-caption text-neutral-400">Step</span>
        <span aria-current="step" className="text-caption text-brand-600">
          1 / 2
        </span>
      </div>

      <p className="text-body text-neutral-600">
        Enter your email and we&apos;ll send a reset code.
      </p>

      <div className="flex flex-col gap-1">
        <label htmlFor="reset-email" className="text-body-lg text-neutral-900">
          Email
        </label>
        <input
          id="reset-email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          disabled={isLoading}
          aria-required="true"
          placeholder="you@example.com"
          className="w-full rounded-md border border-neutral-200 px-4 py-2 text-body text-neutral-900 placeholder:text-neutral-400 focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600 disabled:opacity-50"
        />
      </div>

      <button
        type="submit"
        disabled={isLoading || !email}
        className="w-full rounded-md bg-brand-600 px-4 py-2 text-body-lg text-white hover:bg-brand-800 focus:outline-none focus:ring-2 focus:ring-brand-600 focus:ring-offset-2 disabled:opacity-50"
        aria-busy={isLoading}
      >
        {isLoading ? "Sending…" : "Send reset code"}
      </button>

      <Link
        href="/login"
        className="text-caption text-center text-brand-600 hover:underline focus:outline-none"
      >
        Back to sign in
      </Link>
    </form>
  );
}
