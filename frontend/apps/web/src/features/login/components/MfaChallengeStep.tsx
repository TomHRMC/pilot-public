/**
 * MfaChallengeStep — web
 *
 * Location: apps/web/src/features/login/components/MfaChallengeStep.tsx
 *
 * Minimal MFA code-entry UI for the login challenge. Handles already-enrolled
 * users confirming their MFA code during sign-in.
 *
 * NOT the full MFAEnrollmentWizard (FE-B12). This handles the *challenge* at
 * login only.
 *
 * FE-B2: design doc §A.2 MfaChallengeStep
 */

"use client";

import React, { useState, useRef } from "react";
import type { MfaMethod } from "../hooks/useLoginFlow";

interface MfaChallengeStepProps {
  challengeName: MfaMethod;
  /** Destination hint from Cognito (e.g., "****1234" for SMS, email domain for EMAIL_OTP) */
  destination?: string;
  onConfirm: (code: string) => Promise<void>;
  onCancel: () => void;
  isLoading?: boolean;
  error?: string | null;
}

function getChallengeLabel(challengeName: MfaMethod): string {
  switch (challengeName) {
    case "TOTP":
      return "Enter the code from your authenticator app.";
    case "SMS_MFA":
      return "Enter the code sent to your phone.";
    case "EMAIL_OTP":
      return "Enter the code sent to your email.";
    case "SOFTWARE_TOKEN_MFA":
      return "Enter the code from your authenticator app.";
    default:
      return "Enter the verification code.";
  }
}

export function MfaChallengeStep({
  challengeName,
  destination,
  onConfirm,
  onCancel,
  isLoading = false,
  error,
}: MfaChallengeStepProps) {
  const [code, setCode] = useState("");
  const [showRecovery, setShowRecovery] = useState(false);
  const [recoveryCode, setRecoveryCode] = useState("");
  const codeInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const submitCode = showRecovery ? recoveryCode : code;
    if (!submitCode.trim()) return;
    await onConfirm(submitCode.trim());
  };

  const label = getChallengeLabel(challengeName);

  return (
    <form onSubmit={(e) => void handleSubmit(e)} aria-label="MFA verification">
      <div className="flex flex-col gap-4">
        <div>
          <p className="text-body text-neutral-600">{label}</p>
          {destination && (
            <p className="text-caption text-neutral-400 mt-1">
              Code sent to{" "}
              <span className="text-neutral-600">{destination}</span>
            </p>
          )}
        </div>

        {!showRecovery ? (
          <div className="flex flex-col gap-1">
            <label htmlFor="mfa-code" className="text-body-lg text-neutral-900">
              Verification code
            </label>
            <input
              ref={codeInputRef}
              id="mfa-code"
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
              placeholder="000000"
              disabled={isLoading}
              aria-describedby={error ? "mfa-error" : undefined}
              className="w-full rounded-md border border-neutral-200 px-4 py-2 text-body text-neutral-900 placeholder:text-neutral-400 focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600 disabled:opacity-50"
            />
          </div>
        ) : (
          <div className="flex flex-col gap-1">
            <label
              htmlFor="recovery-code"
              className="text-body-lg text-neutral-900"
            >
              Recovery code
            </label>
            <input
              id="recovery-code"
              type="text"
              autoComplete="off"
              maxLength={10}
              value={recoveryCode}
              onChange={(e) => setRecoveryCode(e.target.value)}
              placeholder="XXXX-XXXX"
              disabled={isLoading}
              aria-describedby={error ? "mfa-error" : undefined}
              className="w-full rounded-md border border-neutral-200 px-4 py-2 text-body text-neutral-900 placeholder:text-neutral-400 focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600 disabled:opacity-50"
            />
          </div>
        )}

        {error && (
          <p
            id="mfa-error"
            role="alert"
            className="text-caption text-fault-600"
          >
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={
            isLoading || (showRecovery ? !recoveryCode : code.length < 6)
          }
          className="w-full rounded-md bg-brand-600 px-4 py-2 text-body-lg text-white hover:bg-brand-800 focus:outline-none focus:ring-2 focus:ring-brand-600 focus:ring-offset-2 disabled:opacity-50"
        >
          {isLoading ? "Verifying…" : "Verify"}
        </button>

        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={() => {
              setShowRecovery((v) => !v);
              setCode("");
              setRecoveryCode("");
            }}
            className="text-caption text-brand-600 hover:underline focus:outline-none"
          >
            {showRecovery ? "Use verification code" : "Use a recovery code"}
          </button>

          <button
            type="button"
            onClick={onCancel}
            className="text-caption text-neutral-400 hover:text-neutral-600 hover:underline focus:outline-none"
          >
            Cancel
          </button>
        </div>
      </div>
    </form>
  );
}
