/**
 * InviteAcceptForm — TEAM-INVITE-2
 *
 * Location: apps/web/src/features/users/components/InviteAcceptForm.tsx
 *
 * The password + confirm step of the invite-landing accept flow. The invited
 * email is display-only (the invite already owns it — Redundant Entry 3.3.7).
 * On submit, calls Cognito `signUp` via `useCognitoSignUp` (mock-mode
 * short-circuits in dev/tests). On success, calls `onSignedUp(password)` to
 * advance the landing page to the verify phase.
 *
 * NEVER calls POST /api/v1/signup — that is the owner Path 3 provisioner
 * (design §G.2). The Post-Confirmation Lambda Path 2 attaches the invitee to
 * the inviting tenant at `ConfirmSignUp` time; no authenticated provisioning
 * call is needed.
 *
 * WCAG 2.2 AA (§36):
 *  - Paste MUST work on password inputs (Accessible Authentication 3.3.8) —
 *    no onPaste interception.
 *  - Email displayed as labeled text beside the form (Redundant Entry 3.3.7).
 *  - ≥44 px primary submit target.
 *  - aria-invalid + aria-describedby non-color-only errors.
 *  - Visible password-policy hint text.
 */

"use client";

import React, { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { EyeIcon, EyeSlashIcon } from "@heroicons/react/24/outline";
import { useCognitoSignUp } from "@/features/signup/hooks/useCognitoSignUp";
import {
  CognitoSignUpError,
  type CognitoSignUpErrorCode,
} from "@/features/signup/hooks/useCognitoSignUp";

// ─── Zod schema (v4 idioms) ───────────────────────────────────────────────────
// TEAM-INVITE-2 §G.5: keep in sync with the copy in
// frontend/apps/web/src/app/signup/account/page.tsx (passwordSchema).
// Do NOT extract a shared module — touches the owner wizard (churn risk).
const passwordSchema = z
  .string()
  .min(12, "Password must be at least 12 characters.")
  .refine((v) => /[A-Z]/.test(v), "Include at least one uppercase letter.")
  .refine((v) => /[a-z]/.test(v), "Include at least one lowercase letter.")
  .refine((v) => /\d/.test(v), "Include at least one number.")
  .refine(
    (v) => /[^A-Za-z0-9]/.test(v),
    "Include at least one symbol (e.g. ! @ # $).",
  );

const inviteAcceptSchema = z
  .object({
    password: passwordSchema,
    confirm_password: z.string().min(1, "Please confirm your password."),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: "Passwords do not match.",
    path: ["confirm_password"],
  });

type InviteAcceptFormValues = z.infer<typeof inviteAcceptSchema>;

interface InviteAcceptFormProps {
  /** From the public invite fetch — display only. */
  email: string;
  /** Advances the landing page to the verify phase. */
  onSignedUp: (password: string) => void;
}

function mapCognitoError(
  code: CognitoSignUpErrorCode,
  message: string,
  email: string,
): { text: string; showSignInInstead: boolean } {
  switch (code) {
    case "UsernameExistsException":
      return {
        text: `An account already exists for ${email}.`,
        showSignInInstead: true,
      };
    case "InvalidPasswordException":
      return { text: message, showSignInInstead: false };
    case "LimitExceededException":
      return {
        text: "Too many attempts. Wait a minute and try again.",
        showSignInInstead: false,
      };
    default:
      return {
        text: "Sign-up failed. Please try again.",
        showSignInInstead: false,
      };
  }
}

export function InviteAcceptForm({ email, onSignedUp }: InviteAcceptFormProps) {
  const cognitoSignUp = useCognitoSignUp();
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [submitError, setSubmitError] = useState<{
    text: string;
    showSignInInstead: boolean;
  } | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<InviteAcceptFormValues>({
    resolver: zodResolver(inviteAcceptSchema),
    defaultValues: {
      password: "",
      confirm_password: "",
    },
  });

  const onSubmit = async (values: InviteAcceptFormValues) => {
    setSubmitError(null);
    try {
      await cognitoSignUp.mutateAsync({
        email,
        password: values.password,
      });
      onSignedUp(values.password);
    } catch (err: unknown) {
      if (err instanceof CognitoSignUpError) {
        setSubmitError(mapCognitoError(err.code, err.message, email));
      } else {
        setSubmitError({
          text: "Sign-up failed. Please try again.",
          showSignInInstead: false,
        });
      }
    }
  };

  return (
    <div data-testid="invite-accept-form" className="mt-8">
      {/* Read-only email display (Redundant Entry 3.3.7) */}
      <div className="mb-5">
        <p className="text-xs font-medium uppercase tracking-wide text-neutral-500">
          Account email
        </p>
        <p className="mt-1 text-sm font-medium text-neutral-900">{email}</p>
      </div>

      <form
        onSubmit={handleSubmit(onSubmit)}
        noValidate
        className="flex flex-col gap-5"
      >
        {/* Password */}
        <div className="flex flex-col gap-1">
          <label
            htmlFor="invite-password"
            className="text-sm font-medium text-neutral-800"
          >
            Password <span className="text-fault-600">*</span>
          </label>
          <div className="relative">
            <input
              id="invite-password"
              type={showPassword ? "text" : "password"}
              autoComplete="new-password"
              placeholder="At least 12 characters"
              aria-invalid={!!errors.password}
              aria-describedby={
                errors.password
                  ? "invite-password-error"
                  : "invite-password-rules"
              }
              data-testid="invite-password-input"
              className={`
                w-full rounded-lg border px-3 py-2.5 pr-10 text-sm focus:outline-none
                focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2
                ${errors.password ? "border-fault-600 bg-fault-50" : "border-neutral-300"}
              `}
              {...register("password")}
            />
            <button
              type="button"
              onClick={() => setShowPassword((v) => !v)}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-neutral-400 hover:text-neutral-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-1 rounded"
              aria-label={showPassword ? "Hide password" : "Show password"}
            >
              {showPassword ? (
                <EyeSlashIcon className="w-5 h-5" />
              ) : (
                <EyeIcon className="w-5 h-5" />
              )}
            </button>
          </div>
          {/* Helper text — non-color-only (WCAG §36): states the policy. */}
          <p
            id="invite-password-rules"
            className="text-xs text-neutral-500 mt-0.5"
          >
            At least 12 characters with upper, lower, number, and symbol.
          </p>
          {errors.password && (
            <p
              id="invite-password-error"
              className="text-fault-600 text-xs mt-0.5"
              role="alert"
            >
              {errors.password.message}
            </p>
          )}
        </div>

        {/* Confirm password */}
        <div className="flex flex-col gap-1">
          <label
            htmlFor="invite-confirm-password"
            className="text-sm font-medium text-neutral-800"
          >
            Confirm password <span className="text-fault-600">*</span>
          </label>
          <div className="relative">
            <input
              id="invite-confirm-password"
              type={showConfirmPassword ? "text" : "password"}
              autoComplete="new-password"
              placeholder="Re-enter your password"
              aria-invalid={!!errors.confirm_password}
              aria-describedby={
                errors.confirm_password
                  ? "invite-confirm-password-error"
                  : undefined
              }
              data-testid="invite-confirm-password-input"
              className={`
                w-full rounded-lg border px-3 py-2.5 pr-10 text-sm focus:outline-none
                focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2
                ${errors.confirm_password ? "border-fault-600 bg-fault-50" : "border-neutral-300"}
              `}
              {...register("confirm_password")}
            />
            <button
              type="button"
              onClick={() => setShowConfirmPassword((v) => !v)}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-neutral-400 hover:text-neutral-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-1 rounded"
              aria-label={
                showConfirmPassword ? "Hide password" : "Show password"
              }
            >
              {showConfirmPassword ? (
                <EyeSlashIcon className="w-5 h-5" />
              ) : (
                <EyeIcon className="w-5 h-5" />
              )}
            </button>
          </div>
          {errors.confirm_password && (
            <p
              id="invite-confirm-password-error"
              className="text-fault-600 text-xs mt-0.5"
              role="alert"
            >
              {errors.confirm_password.message}
            </p>
          )}
        </div>

        {/* Submit-level error (Cognito) */}
        {submitError && (
          <div
            data-testid="invite-accept-error"
            role="alert"
            className="rounded-lg border border-fault-200 bg-fault-50 px-4 py-3 text-sm text-fault-700"
          >
            <p>{submitError.text}</p>
            {submitError.showSignInInstead && (
              <a
                href={`/login?email=${encodeURIComponent(email)}`}
                data-testid="invite-signin-instead"
                className="mt-1 inline-block font-medium text-brand-600 hover:text-brand-800 underline"
              >
                Sign in instead
              </a>
            )}
          </div>
        )}

        {/* Submit — ≥44 px (py-3.5 ≈ 14px*2 + line ≈ 20px = 48px) */}
        <button
          type="submit"
          disabled={isSubmitting}
          data-testid="invite-accept-submit"
          aria-disabled={isSubmitting}
          className={`
            w-full py-3.5 px-6 rounded-lg text-sm font-semibold transition-colors
            focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2
            ${
              isSubmitting
                ? "opacity-40 cursor-not-allowed bg-brand-600 text-white"
                : "bg-brand-600 hover:bg-brand-800 text-white"
            }
          `}
        >
          {isSubmitting ? "Creating…" : "Create your account"}
        </button>
      </form>
    </div>
  );
}
