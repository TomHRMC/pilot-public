/**
 * /signup/account — Step 1: Account Creation (PUBLIC — no JWT)
 *
 * Location: apps/web/src/app/signup/account/page.tsx
 *
 * RULE 3: Lives outside (authed) group — no JWT guard.
 * RULE 4: On mount, if tenant_id in sessionStorage, resume from backend state.
 *
 * SIGNUP-GA-1 (ADR-0011): this page now collects a PASSWORD (+ confirm) and
 * calls Cognito `SignUp` (via Amplify) BEFORE POSTing /api/v1/signup. On
 * success it routes to /signup/verify (email-confirmation step). The business/
 * owner fields + password are held in-memory (signupPendingCredential) so the
 * verify step can complete the wizard resolve-or-attach call after the
 * Post-Confirmation Lambda (Path 3) creates the tenant. The password is
 * NEVER written to sessionStorage.
 *
 * Fields: business_name, trade, business_size, zip, time_zone,
 *         owner_email, owner_first_name, owner_last_name,
 *         password, confirm_password
 *
 * Duplicate email (Cognito UsernameExistsException) returns the same
 * field-level inline error + "Sign in instead" link as the legacy 409 path.
 */

"use client";

import React, { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { EyeIcon, EyeSlashIcon } from "@heroicons/react/24/outline";
import { apiClient } from "@pilot/shared-api";
import { useAuth } from "@pilot/ui/auth";
import { WizardProgressBar } from "@/features/signup/components/WizardProgressBar";
import {
  WIZARD_TENANT_ID_KEY,
  signupStateToStep,
  stepToUrl,
  type WizardSignupState,
} from "@/features/signup/types";
import { useCognitoSignUp } from "@/features/signup/hooks/useCognitoSignUp";
import { useSubscriptionTiers } from "@/features/signup/hooks/useSubscriptionTiers";
import {
  setSignupPendingCredential,
  type SignupPendingCredential,
} from "@/features/signup/signupPendingCredential";

const TRADE_OPTIONS = [
  { value: "electrical", label: "Electrical" },
  { value: "plumbing", label: "Plumbing" },
  { value: "hvac", label: "HVAC" },
  { value: "other", label: "Other" },
];

const SIZE_OPTIONS = [
  { value: "solo", label: "Solo (just me)" },
  { value: "small", label: "Small (2–5 people)" },
  { value: "medium", label: "Medium (6–15 people)" },
  { value: "large", label: "Large (16+ people)" },
];

// ─── Zod schema (v4 idioms) ───────────────────────────────────────────────────
// Password policy mirrors the Cognito pool (aws-cognito-testing.md §4):
// min 12 chars, ≥1 upper, ≥1 lower, ≥1 number, ≥1 symbol.
// TEAM-INVITE-2 §G.5: keep in sync with the copy in InviteAcceptForm.tsx.

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

const signupAccountSchema = z
  .object({
    business_name: z.string().min(1, "Business name is required."),
    trade: z.string().min(1, "Trade is required."),
    business_size: z.string().min(1, "Business size is required."),
    zip: z
      .string()
      .min(1, "ZIP code is required.")
      .refine((v) => /^\d{5}(-\d{4})?$/.test(v.trim()), {
        message: "Enter a valid ZIP or postal code.",
      }),
    time_zone: z.string().min(1),
    owner_email: z.email("Enter a valid email address."),
    owner_first_name: z.string().min(1, "First name is required."),
    owner_last_name: z.string().min(1, "Last name is required."),
    password: passwordSchema,
    confirm_password: z.string().min(1, "Please confirm your password."),
  })
  .refine((data) => data.password === data.confirm_password, {
    message: "Passwords do not match.",
    path: ["confirm_password"],
  });

type SignupAccountFormValues = z.infer<typeof signupAccountSchema>;

export default function SignupAccountPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const isExpiredResume = searchParams.get("expired") === "true";

  const cognitoSignUp = useCognitoSignUp();
  const { isAuthenticated, signOut, user } = useAuth();

  // Password reveal toggle state (STEP 1 — SIGNUP-UI-FIX-1)
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // Mode-aware subtitle (STEP 5 — SIGNUP-UI-FIX-1):
  // If no trial tier exists, the app is in Charter mode.
  const { data: tiers } = useSubscriptionTiers();
  const hasTrialTier = !!tiers?.find((t) => t.is_trial);
  const subtitleText = hasTrialTier
    ? "Start your free 14-day trial — no credit card required."
    : "Join the Charter program — 90 days free, no credit card required.";

  const {
    register,
    handleSubmit,
    setError,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<SignupAccountFormValues>({
    resolver: zodResolver(signupAccountSchema),
    defaultValues: {
      business_name: "",
      trade: "",
      business_size: "",
      zip: "",
      time_zone:
        Intl.DateTimeFormat().resolvedOptions().timeZone || "America/New_York",
      owner_email: "",
      owner_first_name: "",
      owner_last_name: "",
      password: "",
      confirm_password: "",
    },
  });

  // Resume check: if tenant_id in sessionStorage OR user.tenantId, redirect
  // to current backend step.
  // SIGNUP-GA-B1: Model B — a `step1_account` user has finished the account
  // step and should be forwarded to /signup/legal (not kept on /signup/account).
  // SIGNUP-UI-FIX-1: fall back to user.tenantId when sessionStorage is cleared
  // (browser tab closed). Also gates the stale-session sign-out: only sign out
  // if the user has NO active signup (404 or complete).
  const [signupCheckDone, setSignupCheckDone] = useState(false);

  useEffect(() => {
    const storedTenantId =
      sessionStorage.getItem(WIZARD_TENANT_ID_KEY) ?? user?.tenantId ?? null;
    if (!storedTenantId) {
      setSignupCheckDone(true);
      return;
    }
    apiClient
      .get(`/api/v1/signup/${storedTenantId}/state`)
      .then((res) => {
        const current = res.data.signup_state as WizardSignupState;
        if (current === "complete") {
          sessionStorage.removeItem(WIZARD_TENANT_ID_KEY);
          router.replace("/dashboard");
          setSignupCheckDone(true);
          return;
        }
        // User is mid-wizard — redirect to the correct step.
        // Persist tenantId to sessionStorage for the target page.
        sessionStorage.setItem(WIZARD_TENANT_ID_KEY, storedTenantId);
        const target =
          stepToUrl[signupStateToStep[current]] ?? "/signup/account";
        if (target !== "/signup/account") {
          router.replace(target);
        }
        setSignupCheckDone(true);
      })
      .catch(() => {
        // 404 or error — no active signup for this tenant.
        // This is the "stale session" case: the user is authenticated but
        // has no signup record. Sign them out so they can start fresh.
        sessionStorage.removeItem(WIZARD_TENANT_ID_KEY);
        setSignupCheckDone(true);
      });
  }, [router, user]);

  // Stale session cleanup (STEP 6 — SIGNUP-UI-FIX-1):
  // Only sign out if the user is authenticated AND the signup check has
  // completed AND there's no active signup (the resume-check catch block
  // already cleared sessionStorage). This prevents signing out a user who
  // is mid-wizard and just needs to be redirected.
  useEffect(() => {
    if (isAuthenticated && signupCheckDone) {
      // If we reached here without redirecting, the user has no active
      // signup — sign them out so they can start a fresh SignUp.
      const hasStoredTenant = sessionStorage.getItem(WIZARD_TENANT_ID_KEY);
      if (!hasStoredTenant) {
        signOut().then(() => {
          // Session cleared — the form is now usable for a fresh signup.
        });
      }
    }
  }, [isAuthenticated, signOut, signupCheckDone]);

  const onSubmit = async (values: SignupAccountFormValues) => {
    const email = values.owner_email.trim().toLowerCase();

    // STEP 2: Cognito SignUp FIRST (before /api/v1/signup).
    // The Post-Confirmation Lambda (Path 3) fires on email confirmation,
    // creating the tenant; the wizard's resolve-or-attach call then
    // overwrites the placeholder name with business_name (design §D).
    const cognitoRes = await cognitoSignUp.mutateAsync({
      email,
      password: values.password,
    });

    if (cognitoRes.isSignUpComplete) {
      // Edge: Cognito auto-confirmed (shouldn't happen with email verification
      // required, but handle defensively). Treat as already confirmed —
      // proceed to the verify step which will detect DONE and continue.
    }

    // Hold business/owner fields + password IN MEMORY (never sessionStorage).
    const businessFields: SignupPendingCredential["businessFields"] = {
      business_name: values.business_name.trim(),
      trade: values.trade,
      business_size: values.business_size,
      zip: values.zip.trim(),
      time_zone: values.time_zone,
      owner_email: email,
      owner_first_name: values.owner_first_name.trim(),
      owner_last_name: values.owner_last_name.trim(),
    };
    setSignupPendingCredential({
      email,
      password: values.password,
      businessFields,
    });

    // Route to the email-verification step. The verify page will:
    //   confirmSignUp → auto signIn → POST /api/v1/signup → /signup/legal
    router.push("/signup/verify");
  };

  const onInvalid = () => {
    // RHF surfaces field errors via the resolver; nothing extra to do.
  };

  // Surface Cognito UsernameExistsException as the inline duplicate-email
  // error (same UX as the legacy 409 path).
  const handleCognitoError = (err: unknown) => {
    if (
      err &&
      typeof err === "object" &&
      "code" in err &&
      (err as { code: string }).code === "UsernameExistsException"
    ) {
      setError("owner_email", {
        type: "email_duplicate",
        message: "An account with this email already exists.",
      });
    }
    // Other Cognito errors surface as a generic submit error via the
    // mutation's isError state below.
  };

  const isDuplicateEmail = errors.owner_email?.type === "email_duplicate";
  // eslint-disable-next-line react-hooks/incompatible-library
  const emailValue = watch("owner_email");

  return (
    <div className="flex flex-col gap-8">
      <WizardProgressBar currentStep="account" />

      {isExpiredResume && (
        <div
          role="alert"
          className="rounded-lg bg-alert-50 border border-alert-200 px-4 py-3 text-sm text-alert-700"
        >
          Your session expired. Start over to create your account.
        </div>
      )}

      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-bold text-neutral-900">
          Create your Pilot account
        </h1>
        <p className="text-sm text-neutral-600">{subtitleText}</p>
      </div>

      <form
        onSubmit={handleSubmit(async (values) => {
          try {
            await onSubmit(values);
          } catch (err) {
            handleCognitoError(err);
          }
        }, onInvalid)}
        noValidate
        className="flex flex-col gap-5"
        data-testid="signup-account-form"
      >
        {/* Business name */}
        <div className="flex flex-col gap-1">
          <label
            htmlFor="business_name"
            className="text-sm font-medium text-neutral-800"
          >
            Business name <span className="text-fault-600">*</span>
          </label>
          <input
            id="business_name"
            type="text"
            autoComplete="organization"
            placeholder="Apex Electric LLC"
            aria-invalid={!!errors.business_name}
            aria-describedby={
              errors.business_name ? "business_name-error" : undefined
            }
            data-testid="field-business-name"
            className={`
              w-full rounded-lg border px-3 py-2.5 text-sm focus:outline-none
              focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2
              ${errors.business_name ? "border-fault-600 bg-fault-50" : "border-neutral-300"}
            `}
            {...register("business_name")}
          />
          {errors.business_name && (
            <p
              id="business_name-error"
              className="text-fault-600 text-xs mt-0.5"
              role="alert"
            >
              {errors.business_name.message}
            </p>
          )}
        </div>

        {/* Trade + business size row */}
        <div className="grid grid-cols-2 gap-4">
          <div className="flex flex-col gap-1">
            <label
              htmlFor="trade"
              className="text-sm font-medium text-neutral-800"
            >
              Trade <span className="text-fault-600">*</span>
            </label>
            <select
              id="trade"
              aria-invalid={!!errors.trade}
              data-testid="field-trade"
              className={`
                w-full rounded-lg border px-3 py-2.5 text-sm bg-white focus:outline-none
                focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2
                ${errors.trade ? "border-fault-600" : "border-neutral-300"}
              `}
              {...register("trade")}
            >
              <option value="">Select trade</option>
              {TRADE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
            {errors.trade && (
              <p className="text-fault-600 text-xs mt-0.5" role="alert">
                {errors.trade.message}
              </p>
            )}
          </div>

          <div className="flex flex-col gap-1">
            <label
              htmlFor="business_size"
              className="text-sm font-medium text-neutral-800"
            >
              Team size <span className="text-fault-600">*</span>
            </label>
            <select
              id="business_size"
              aria-invalid={!!errors.business_size}
              data-testid="field-business-size"
              className={`
                w-full rounded-lg border px-3 py-2.5 text-sm bg-white focus:outline-none
                focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2
                ${errors.business_size ? "border-fault-600" : "border-neutral-300"}
              `}
              {...register("business_size")}
            >
              <option value="">Select size</option>
              {SIZE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
            {errors.business_size && (
              <p className="text-fault-600 text-xs mt-0.5" role="alert">
                {errors.business_size.message}
              </p>
            )}
          </div>
        </div>

        {/* ZIP */}
        <div className="flex flex-col gap-1">
          <label htmlFor="zip" className="text-sm font-medium text-neutral-800">
            ZIP / Postal code <span className="text-fault-600">*</span>
          </label>
          <input
            id="zip"
            type="text"
            inputMode="numeric"
            autoComplete="postal-code"
            placeholder="10001"
            aria-invalid={!!errors.zip}
            aria-describedby={errors.zip ? "zip-error" : undefined}
            data-testid="field-zip"
            className={`
              w-full rounded-lg border px-3 py-2.5 text-sm focus:outline-none
              focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2
              ${errors.zip ? "border-fault-600 bg-fault-50" : "border-neutral-300"}
            `}
            {...register("zip")}
          />
          {errors.zip && (
            <p
              id="zip-error"
              className="text-fault-600 text-xs mt-0.5"
              role="alert"
            >
              {errors.zip.message}
            </p>
          )}
        </div>

        {/* Name row */}
        <div className="grid grid-cols-2 gap-4">
          <div className="flex flex-col gap-1">
            <label
              htmlFor="owner_first_name"
              className="text-sm font-medium text-neutral-800"
            >
              First name <span className="text-fault-600">*</span>
            </label>
            <input
              id="owner_first_name"
              type="text"
              autoComplete="given-name"
              placeholder="Mike"
              aria-invalid={!!errors.owner_first_name}
              data-testid="field-first-name"
              className={`
                w-full rounded-lg border px-3 py-2.5 text-sm focus:outline-none
                focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2
                ${errors.owner_first_name ? "border-fault-600 bg-fault-50" : "border-neutral-300"}
              `}
              {...register("owner_first_name")}
            />
            {errors.owner_first_name && (
              <p className="text-fault-600 text-xs mt-0.5" role="alert">
                {errors.owner_first_name.message}
              </p>
            )}
          </div>

          <div className="flex flex-col gap-1">
            <label
              htmlFor="owner_last_name"
              className="text-sm font-medium text-neutral-800"
            >
              Last name <span className="text-fault-600">*</span>
            </label>
            <input
              id="owner_last_name"
              type="text"
              autoComplete="family-name"
              placeholder="Johnson"
              aria-invalid={!!errors.owner_last_name}
              data-testid="field-last-name"
              className={`
                w-full rounded-lg border px-3 py-2.5 text-sm focus:outline-none
                focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2
                ${errors.owner_last_name ? "border-fault-600 bg-fault-50" : "border-neutral-300"}
              `}
              {...register("owner_last_name")}
            />
            {errors.owner_last_name && (
              <p className="text-fault-600 text-xs mt-0.5" role="alert">
                {errors.owner_last_name.message}
              </p>
            )}
          </div>
        </div>

        {/* Email */}
        <div className="flex flex-col gap-1">
          <label
            htmlFor="owner_email"
            className="text-sm font-medium text-neutral-800"
          >
            Work email <span className="text-fault-600">*</span>
          </label>
          <input
            id="owner_email"
            type="email"
            autoComplete="email"
            placeholder="mike@apexelectric.example.com"
            aria-invalid={!!errors.owner_email}
            aria-describedby={
              errors.owner_email ? "owner_email-error" : undefined
            }
            data-testid="field-email"
            className={`
              w-full rounded-lg border px-3 py-2.5 text-sm focus:outline-none
              focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2
              ${errors.owner_email ? "border-fault-600 bg-fault-50" : "border-neutral-300"}
            `}
            {...register("owner_email")}
          />
          {errors.owner_email && (
            <p
              id="owner_email-error"
              className="text-fault-600 text-xs mt-0.5"
              role="alert"
            >
              {errors.owner_email.message}
              {isDuplicateEmail && (
                <>
                  {" "}
                  <a
                    href={`/login?email=${encodeURIComponent(emailValue)}`}
                    className="text-brand-600 hover:text-brand-800 underline"
                  >
                    Sign in instead
                  </a>
                </>
              )}
            </p>
          )}
        </div>

        {/* Password */}
        <div className="flex flex-col gap-1">
          <label
            htmlFor="password"
            className="text-sm font-medium text-neutral-800"
          >
            Password <span className="text-fault-600">*</span>
          </label>
          <div className="relative">
            <input
              id="password"
              type={showPassword ? "text" : "password"}
              autoComplete="new-password"
              placeholder="At least 12 characters"
              aria-invalid={!!errors.password}
              aria-describedby={
                errors.password ? "password-error" : "password-rules"
              }
              data-testid="field-password"
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
              data-testid="toggle-password-visibility"
            >
              {showPassword ? (
                <EyeSlashIcon className="w-5 h-5" />
              ) : (
                <EyeIcon className="w-5 h-5" />
              )}
            </button>
          </div>
          {/* Helper text — non-color-only (WCAG §36): states the policy. */}
          <p id="password-rules" className="text-xs text-neutral-500 mt-0.5">
            At least 12 characters with one uppercase, one lowercase, one
            number, and one symbol.
          </p>
          {errors.password && (
            <p
              id="password-error"
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
            htmlFor="confirm_password"
            className="text-sm font-medium text-neutral-800"
          >
            Confirm password <span className="text-fault-600">*</span>
          </label>
          <div className="relative">
            <input
              id="confirm_password"
              type={showConfirmPassword ? "text" : "password"}
              autoComplete="new-password"
              placeholder="Re-enter your password"
              aria-invalid={!!errors.confirm_password}
              aria-describedby={
                errors.confirm_password ? "confirm_password-error" : undefined
              }
              data-testid="field-confirm-password"
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
              data-testid="toggle-confirm-password-visibility"
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
              id="confirm_password-error"
              className="text-fault-600 text-xs mt-0.5"
              role="alert"
            >
              {errors.confirm_password.message}
            </p>
          )}
        </div>

        {/* Generic Cognito error (non-duplicate) */}
        {cognitoSignUp.isError &&
          !isDuplicateEmail &&
          cognitoSignUp.error?.code !== "UsernameExistsException" && (
            <p role="alert" className="text-fault-600 text-sm">
              {cognitoSignUp.error?.message ??
                "Failed to create account. Please try again."}
            </p>
          )}

        {/* Submit */}
        <button
          type="submit"
          disabled={isSubmitting}
          data-testid="signup-account-continue"
          aria-disabled={isSubmitting}
          className={`
            w-full py-3 px-6 rounded-lg text-sm font-semibold transition-colors
            focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2
            ${
              isSubmitting
                ? "opacity-40 cursor-not-allowed bg-brand-600 text-white"
                : "bg-brand-600 hover:bg-brand-800 text-white"
            }
          `}
        >
          {isSubmitting ? "Creating account…" : "Continue →"}
        </button>

        <p className="text-xs text-neutral-500 text-center">
          Already have an account?{" "}
          <a
            href="/login"
            className="text-brand-600 hover:text-brand-800 underline"
          >
            Sign in
          </a>
        </p>
      </form>
    </div>
  );
}
