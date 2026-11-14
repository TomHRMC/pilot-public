"use client";

/**
 * OtpEntryPanel — C-B9
 *
 * Location: apps/web/src/components/settings/messaging/OtpEntryPanel.tsx
 *
 * Sole-proprietor OTP entry. Appears when status is awaiting_otp.
 * 6-digit input with auto-advance + paste support (WCAG 2.2 SC 3.3.8).
 *
 * UI spec §4.6. RULE 5: zero hex codes. RULE 11: no hand-memo.
 */

import React, { useRef, useState, useEffect } from "react";
import {
  DevicePhoneMobileIcon,
  ClockIcon,
  InformationCircleIcon,
} from "@heroicons/react/24/outline";
import { useSubmitOtp } from "@/features/messaging/hooks/useSubmitOtp";
import { useNotificationQueue } from "@pilot/ui";
import { formatPhoneNumber } from "@/features/messaging/types";

export interface OtpEntryPanelProps {
  /** The brand's support phone number (where the PIN was sent). */
  supportPhone: string | null;
  /** ISO timestamp of when the OTP was requested. */
  otpRequestedAt: string | null;
}

const OTP_TIMEOUT_MS = 24 * 60 * 60 * 1000; // 24 hours
const OTP_WARNING_MS = 18 * 60 * 60 * 1000; // 18 hours — show warning

export function OtpEntryPanel({
  supportPhone,
  otpRequestedAt,
}: OtpEntryPanelProps) {
  const submitOtp = useSubmitOtp();
  const { addNotification } = useNotificationQueue();
  const [digits, setDigits] = useState<string[]>(["", "", "", "", "", ""]);
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [timeRemainingMs, setTimeRemainingMs] = useState<number | null>(null);
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  // Countdown timer
  useEffect(() => {
    if (!otpRequestedAt) return;
    const update = () => {
      const elapsed = Date.now() - new Date(otpRequestedAt).getTime();
      setTimeRemainingMs(Math.max(0, OTP_TIMEOUT_MS - elapsed));
    };
    update();
    const interval = setInterval(update, 60000); // update every minute
    return () => clearInterval(interval);
  }, [otpRequestedAt]);

  const isComplete = digits.every((d) => d.length === 1);
  const isPending = submitOtp.isPending;

  function handleChange(index: number, value: string) {
    setFieldError(null);
    // Only accept single digits
    const digit = value.replace(/\D/g, "").slice(-1);
    const newDigits = [...digits];
    newDigits[index] = digit;
    setDigits(newDigits);

    // Auto-advance to next cell
    if (digit && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  }

  function handleKeyDown(index: number, e: React.KeyboardEvent) {
    // Backspace on empty cell moves to previous
    if (e.key === "Backspace" && !digits[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  }

  function handlePaste(e: React.ClipboardEvent) {
    e.preventDefault();
    const pasted = e.clipboardData
      .getData("text")
      .replace(/\D/g, "")
      .slice(0, 6);
    if (pasted.length > 0) {
      const newDigits = ["", "", "", "", "", ""];
      for (let i = 0; i < pasted.length && i < 6; i++) {
        newDigits[i] = pasted[i];
      }
      setDigits(newDigits);
      // Focus the last filled cell or the next empty one
      const focusIndex = Math.min(pasted.length, 5);
      inputRefs.current[focusIndex]?.focus();
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!isComplete) return;
    setFieldError(null);

    const otpCode = digits.join("");
    try {
      await submitOtp.mutateAsync({ otp_code: otpCode });
      // Success — status will transition to brand_verified via polling
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response
        ?.status;
      if (status === 400) {
        setFieldError(
          "PIN rejected by carrier. Check the number and try again.",
        );
      } else if (status === 409) {
        addNotification({
          id: `otp-409-${Date.now()}`,
          severity: "error",
          title: "OTP session expired. Restart setup.",
        });
      } else if (status === 422) {
        setFieldError("PIN must be 6 digits.");
      } else {
        setFieldError("Could not verify PIN. Please try again.");
      }
    }
  }

  // Format time remaining
  const showWarning =
    timeRemainingMs !== null && timeRemainingMs < OTP_WARNING_MS;
  const hoursLeft =
    timeRemainingMs !== null
      ? Math.floor(timeRemainingMs / (60 * 60 * 1000))
      : 0;
  const minutesLeft =
    timeRemainingMs !== null
      ? Math.floor((timeRemainingMs % (60 * 60 * 1000)) / (60 * 1000))
      : 0;

  return (
    <div
      className="bg-white rounded-lg border border-neutral-200 shadow-sm p-6 space-y-4"
      data-testid="otp-entry-panel"
    >
      <div>
        <h2 className="text-h2 font-semibold text-neutral-900">
          Verify Your Business
        </h2>
      </div>

      <div className="flex items-start gap-2 text-sm text-neutral-900">
        <DevicePhoneMobileIcon className="w-5 h-5 text-brand-600 shrink-0 mt-0.5" />
        <p>
          The carrier is texting a PIN to{" "}
          <strong>{formatPhoneNumber(supportPhone)}</strong>. Enter it below to
          verify your business.
        </p>
      </div>

      <form onSubmit={(e) => void handleSubmit(e)}>
        <fieldset
          aria-describedby="otp-help"
          className="flex justify-center gap-2 my-4"
        >
          <legend className="sr-only">Enter 6-digit PIN</legend>
          {digits.map((digit, index) => (
            <div key={index}>
              <label htmlFor={`otp-${index + 1}`} className="sr-only">
                Digit {index + 1}
              </label>
              <input
                ref={(el) => {
                  inputRefs.current[index] = el;
                }}
                id={`otp-${index + 1}`}
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength={1}
                value={digit}
                onChange={(e) => handleChange(index, e.target.value)}
                onKeyDown={(e) => handleKeyDown(index, e)}
                onPaste={handlePaste}
                disabled={isPending}
                className="w-12 h-14 text-center text-xl font-mono border border-neutral-300 rounded-md focus:ring-2 focus:ring-brand-500 focus:border-brand-500 focus:outline-none"
                data-testid={`otp-digit-${index + 1}`}
              />
            </div>
          ))}
        </fieldset>

        {fieldError && (
          <p
            id="otp-error"
            className="text-xs text-fault-600 mt-2 text-center"
            role="alert"
          >
            {fieldError}
          </p>
        )}

        <div className="flex justify-center">
          <button
            type="submit"
            disabled={!isComplete || isPending}
            className="bg-brand-600 text-white rounded-md px-6 py-2 text-sm font-medium hover:bg-brand-700 focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:outline-none active:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed"
            data-testid="otp-submit"
          >
            {isPending ? "Verifying..." : "Submit PIN"}
          </button>
        </div>
      </form>

      {showWarning && (
        <p className="text-xs text-alert-600 mt-2 flex items-center justify-center gap-1">
          <ClockIcon className="w-4 h-4" />
          PIN expires in {hoursLeft}h {minutesLeft}m
        </p>
      )}

      <div
        id="otp-help"
        className="text-xs text-neutral-500 mt-2 flex items-start gap-1"
      >
        <InformationCircleIcon className="w-4 h-4 shrink-0 mt-0.5" />
        <p>
          Did not receive a PIN? Make sure your business phone can receive SMS.
          The PIN may take a few minutes to arrive.
        </p>
      </div>
    </div>
  );
}
