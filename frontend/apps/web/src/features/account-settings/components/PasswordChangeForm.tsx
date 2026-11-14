/**
 * PasswordChangeForm — FE-B12
 *
 * Location: apps/web/src/features/account-settings/components/PasswordChangeForm.tsx
 *
 * Three-field explicit-save form. Uses useFormSaveStrategy({ mode: 'explicit' }).
 *
 * RULE: Wrong current password → field-level error, NOT toast.
 * RULE: Success → success NotificationBanner (margin tokens); form clears.
 * RULE: Other-device invalidation relies on FE-B2's 401 interceptor — no new mechanism.
 *
 * Design doc Section H token audit:
 * - Success banner: bg-margin-50 border-margin-200 text-margin-700
 */

"use client";

import React, { useState } from "react";
import { useChangePassword } from "../hooks/useChangePassword";

export function PasswordChangeForm() {
  const { changePassword, isPending, reset } = useChangePassword();

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [fieldError, setFieldError] = useState<{
    field: "current" | "new" | "confirm" | null;
    message: string;
  } | null>(null);
  const [showSuccess, setShowSuccess] = useState(false);

  const canSubmit =
    !isPending &&
    currentPassword.length > 0 &&
    newPassword.length > 0 &&
    confirmPassword.length > 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFieldError(null);
    setShowSuccess(false);

    // Client-side confirm mismatch
    if (newPassword !== confirmPassword) {
      setFieldError({
        field: "confirm",
        message: "New passwords don't match.",
      });
      return;
    }

    try {
      await changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      // Success: clear form + show banner
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setShowSuccess(true);
      reset();
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Password change failed.";
      // Wrong current password → current password field error
      if (
        message.toLowerCase().includes("current password") ||
        message.toLowerCase().includes("incorrect")
      ) {
        setFieldError({
          field: "current",
          message: "Current password is incorrect.",
        });
      } else {
        setFieldError({ field: "new", message });
      }
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col gap-5 max-w-md"
      data-testid="password-change-form"
      noValidate
    >
      {/* Success banner — design doc Section H tokens */}
      {showSuccess && (
        <div
          role="status"
          aria-live="polite"
          className="rounded-md border border-margin-200 bg-margin-50 px-4 py-3 text-sm text-margin-700"
          data-testid="password-change-success"
        >
          <strong>Password changed.</strong> You&apos;re still signed in here,
          but you&apos;ll need to sign in again on other devices.
        </div>
      )}

      {/* Current password */}
      <div className="flex flex-col gap-1.5">
        <label
          htmlFor="current-password"
          className="text-sm font-medium text-neutral-700"
        >
          Current password
        </label>
        <input
          id="current-password"
          type="password"
          autoComplete="current-password"
          value={currentPassword}
          onChange={(e) => {
            setCurrentPassword(e.target.value);
            if (fieldError?.field === "current") setFieldError(null);
          }}
          disabled={isPending}
          aria-invalid={fieldError?.field === "current"}
          aria-describedby={
            fieldError?.field === "current"
              ? "current-password-error"
              : undefined
          }
          className={`rounded-lg border px-3 py-2 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-brand-600 disabled:opacity-50 ${
            fieldError?.field === "current"
              ? "border-fault-500"
              : "border-neutral-300"
          }`}
          data-testid="current-password-input"
        />
        {fieldError?.field === "current" && (
          <p
            id="current-password-error"
            role="alert"
            className="text-xs text-fault-600"
            data-testid="current-password-error"
          >
            {fieldError.message}
          </p>
        )}
      </div>

      {/* New password */}
      <div className="flex flex-col gap-1.5">
        <label
          htmlFor="new-password"
          className="text-sm font-medium text-neutral-700"
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
            if (fieldError?.field === "new") setFieldError(null);
          }}
          disabled={isPending}
          aria-invalid={fieldError?.field === "new"}
          aria-describedby={
            fieldError?.field === "new" ? "new-password-error" : undefined
          }
          className={`rounded-lg border px-3 py-2 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-brand-600 disabled:opacity-50 ${
            fieldError?.field === "new"
              ? "border-fault-500"
              : "border-neutral-300"
          }`}
          data-testid="new-password-input"
        />
        {fieldError?.field === "new" && (
          <p
            id="new-password-error"
            role="alert"
            className="text-xs text-fault-600"
            data-testid="new-password-error"
          >
            {fieldError.message}
          </p>
        )}
      </div>

      {/* Confirm new password */}
      <div className="flex flex-col gap-1.5">
        <label
          htmlFor="confirm-password"
          className="text-sm font-medium text-neutral-700"
        >
          Confirm new password
        </label>
        <input
          id="confirm-password"
          type="password"
          autoComplete="new-password"
          value={confirmPassword}
          onChange={(e) => {
            setConfirmPassword(e.target.value);
            if (fieldError?.field === "confirm") setFieldError(null);
          }}
          disabled={isPending}
          aria-invalid={fieldError?.field === "confirm"}
          aria-describedby={
            fieldError?.field === "confirm"
              ? "confirm-password-error"
              : undefined
          }
          className={`rounded-lg border px-3 py-2 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-brand-600 disabled:opacity-50 ${
            fieldError?.field === "confirm"
              ? "border-fault-500"
              : "border-neutral-300"
          }`}
          data-testid="confirm-password-input"
        />
        {fieldError?.field === "confirm" && (
          <p
            id="confirm-password-error"
            role="alert"
            className="text-xs text-fault-600"
            data-testid="confirm-password-error"
          >
            {fieldError.message}
          </p>
        )}
      </div>

      {/* Disclosure text */}
      <p className="text-xs text-neutral-400">
        Changing your password will sign you out on all other devices.
      </p>

      {/* Submit */}
      <button
        type="submit"
        disabled={!canSubmit}
        className="self-start rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-brand-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
        data-testid="change-password-submit"
      >
        {isPending ? "Changing…" : "Change password"}
      </button>
    </form>
  );
}
