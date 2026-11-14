/**
 * DoubleOptinConfirmSubscreen — SIGNUP-C reply-YES confirmation panel
 *
 * Location: apps/web/src/features/signup/components/DoubleOptinConfirmSubscreen.tsx
 *
 * Replaces the deleted PhoneOtpSubscreen (fake 6-digit OTP grid). The real
 * consent is the inbound YES reply to the platform number — there is no
 * client-side code entry. This panel shows an optimistic "Text sent — reply
 * YES" state and reflects verified status when the parent's /state polling
 * detects consent_status='opted_in'.
 *
 * SIGNUP-UI-FIX-2 Task 4: added a "Resend text" secondary button with a
 * 60s client-mirrored cooldown (matching the backend 429). The parent owns
 * the `userEndpointId` and passes an `onResend` handler; this component
 * manages only the countdown UI + success/error feedback.
 *
 * Presentational component — all polling/navigation state lives in the
 * parent StayInformedStep. Props:
 *   - maskedPhone: pre-masked phone string (e.g. "+1 (•••) •••-4567")
 *   - confirmed:   true when polling detected the YES reply
 *   - onUseDifferentNumber: returns to the entry form
 *   - onSkipForNow:          advances to /signup/plan (phone already saved)
 *   - onResend:              re-triggers POST /phone/send-optin (optional —
 *                            omitted when no userEndpointId is available)
 *
 * Token audit (Section H): all colors from pilotPreset tokens — zero hex.
 */

"use client";

import React, { useEffect, useState } from "react";
import { DevicePhoneMobileIcon } from "@heroicons/react/24/outline";
import { CheckCircleIcon as CheckCircleSolidIcon } from "@heroicons/react/24/solid";

// SIGNUP-UI-FIX-2 Task 4: 60s client-mirrored cooldown (backend enforces 429).
const RESEND_COOLDOWN_SECONDS = 60;

interface DoubleOptinConfirmSubscreenProps {
  maskedPhone: string;
  confirmed: boolean;
  onUseDifferentNumber: () => void;
  onSkipForNow: () => void;
  /** SIGNUP-UI-FIX-2 Task 4: resend the opt-in SMS. Omitted when no
   * userEndpointId is available (e.g. component used in a context without
   * a prior consent response). When provided, a "Resend text" button
   * renders with a 60s countdown. */
  onResend?: () => Promise<ResendResult>;
}

/** Return type of onResend — lets the subscreen show success/error feedback. */
export interface ResendResult {
  ok: boolean;
  /** Error message to display when ok=false (already includes cooldown copy). */
  error?: string;
}

export function DoubleOptinConfirmSubscreen({
  maskedPhone,
  confirmed,
  onUseDifferentNumber,
  onSkipForNow,
  onResend,
}: DoubleOptinConfirmSubscreenProps) {
  const [cooldown, setCooldown] = useState(0);
  const [resending, setResending] = useState(false);
  const [resendError, setResendError] = useState<string | null>(null);
  const [resendSuccess, setResendSuccess] = useState(false);

  // Cooldown ticker — counts down once per second.
  useEffect(() => {
    if (cooldown <= 0) return;
    const t = setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [cooldown]);

  const handleResend = async () => {
    if (!onResend || cooldown > 0 || resending) return;
    setResending(true);
    setResendError(null);
    setResendSuccess(false);
    try {
      const result = await onResend();
      if (result.ok) {
        setResendSuccess(true);
        setCooldown(RESEND_COOLDOWN_SECONDS);
      } else {
        setResendError(result.error ?? "Couldn't resend. Try again.");
        // 429 → start the cooldown so the button stays disabled.
        if (
          result.error?.includes("wait") ||
          result.error?.includes("moment")
        ) {
          setCooldown(RESEND_COOLDOWN_SECONDS);
        }
      }
    } catch {
      setResendError("Couldn't resend. Try again.");
    } finally {
      setResending(false);
    }
  };

  return (
    <div
      data-testid="double-optin-confirm"
      className="rounded-xl border border-neutral-200 bg-white p-6 flex flex-col gap-4 shadow-sm"
    >
      {/* Header row */}
      <div className="flex items-center gap-3">
        <DevicePhoneMobileIcon
          className="w-6 h-6 text-brand-600"
          aria-hidden="true"
        />
        <h2 className="text-base font-semibold text-neutral-900">
          Check your phone
        </h2>
      </div>

      {/* Body text */}
      <p className="text-sm text-neutral-600">
        We texted{" "}
        <span className="font-semibold text-neutral-900">{maskedPhone}</span>.
        Reply <span className="font-semibold text-neutral-900">YES</span> to
        confirm and start receiving alerts.
      </p>

      {confirmed ? (
        // ── Confirmed success banner (replaces pending indicator) ───────────
        <div
          role="status"
          data-testid="double-optin-confirmed"
          className="flex items-center gap-3 rounded-lg bg-margin-50 border border-margin-200 px-4 py-3 text-sm text-margin-700"
        >
          <CheckCircleSolidIcon
            className="w-5 h-5 text-margin-600"
            aria-hidden="true"
          />
          {"Confirmed — you're opted in. Continuing to plan selection…"}
        </div>
      ) : (
        // ── Pending indicator + action links ───────────────────────────────
        <>
          <div
            className="flex items-center gap-2 text-sm text-neutral-500"
            aria-live="polite"
          >
            <svg
              className="animate-spin w-4 h-4 text-neutral-400 motion-reduce:animate-none"
              viewBox="0 0 24 24"
              fill="none"
              aria-hidden="true"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
            Waiting for your reply…
          </div>

          {/* SIGNUP-UI-FIX-2 Task 4: Resend text link + feedback */}
          {onResend && (
            <div className="flex flex-col gap-1">
              <button
                type="button"
                onClick={handleResend}
                disabled={cooldown > 0 || resending}
                aria-disabled={cooldown > 0 || resending}
                data-testid="double-optin-resend"
                aria-live="polite"
                className={`
                  text-left text-sm focus:outline-none focus-visible:underline
                  focus-visible:ring-2 focus-visible:ring-brand-600
                  focus-visible:ring-offset-1 rounded min-h-[24px]
                  ${
                    cooldown > 0 || resending
                      ? "text-neutral-400 cursor-not-allowed"
                      : "text-neutral-500 hover:text-neutral-700"
                  }
                `}
              >
                {resending
                  ? "Sending…"
                  : cooldown > 0
                    ? `Resend text (available in ${cooldown}s)`
                    : "Resend text"}
              </button>
              {resendSuccess && (
                <p
                  role="status"
                  data-testid="double-optin-resend-success"
                  className="text-xs text-margin-700"
                >
                  Text sent. Reply YES to confirm.
                </p>
              )}
              {resendError && (
                <p
                  role="alert"
                  data-testid="double-optin-resend-error"
                  className="text-xs text-fault-600"
                >
                  {resendError}
                </p>
              )}
            </div>
          )}

          <div className="flex flex-col gap-2 text-sm">
            <button
              type="button"
              onClick={onUseDifferentNumber}
              data-testid="double-optin-use-different-number"
              className="text-left text-neutral-500 hover:text-neutral-700 focus:outline-none focus-visible:underline focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-1 rounded"
            >
              Use a different number
            </button>
            <button
              type="button"
              onClick={onSkipForNow}
              data-testid="double-optin-skip-continue"
              className="text-left text-neutral-500 hover:text-neutral-700 focus:outline-none focus-visible:underline focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-1 rounded"
            >
              Skip for now → continue
            </button>
          </div>
        </>
      )}
    </div>
  );
}
