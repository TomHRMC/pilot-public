/**
 * MFAEnrollmentWizard — Web implementation (fleshed out from FE-B1 skeleton)
 *
 * Location: packages/ui/src/mfa-enrollment-wizard/web/MFAEnrollmentWizard.tsx
 *
 * FE-B1: Structural skeleton created.
 * FE-B12: Full TOTP/SMS/Email enrollment, recovery codes, force-flow, grace period.
 *
 * ⚠️ INTERFACE LOCKED after FE-B12 ships — FE-B13 embeds this component.
 *    Props backward-compatible: all new props are optional with defaults.
 *
 * RULE: Force-flow mode (forceFlow=true) hides Cancel button.
 * RULE: Recovery codes step auto-derived from status endpoint when showRecoveryCodes is undefined.
 * RULE: All API calls use fetch directly (no TanStack Query — wizard is a transient flow).
 */

"use client";

import React, { useState, useEffect, useRef } from "react";
import type {
  MFAEnrollmentPath,
  MFAEnrollmentStep,
  MFAWizardInternalStep,
  MfaEnrollStartPayload,
  MFAEnrollmentWizardPropsExtended,
} from "../types";
import {
  MFA_PATH_LABELS,
  MFA_PATH_DESCRIPTIONS,
  MFA_STEP_LABELS,
  MFA_STEP_ORDER,
} from "../types";

// ─── API helpers ──────────────────────────────────────────────────────────────

const API_BASE = "/api/v1/users";

/**
 * MfaApiError — structured error carrying the RFC 7807 `code` field.
 *
 * MFA-WIRE-1 (design §F.3, spec §9): the backend returns Problem Details
 * with a `code` field. The wizard maps each code to a specific copy string
 * and placement (top-of-wizard vs inline verify) per spec §9.
 *
 * `code` is null for network-level failures (no response body) — the wizard
 * falls back to a generic message in that case.
 */
export class MfaApiError extends Error {
  code: string | null;
  status: number;
  constructor(message: string, code: string | null, status: number) {
    super(message);
    this.name = "MfaApiError";
    this.code = code;
    this.status = status;
  }
}

/**
 * Parse a failed fetch response into an MfaApiError.
 * Reads the RFC 7807 `code` and `detail` fields from the JSON body.
 * Falls back to the response status text if the body is not JSON.
 */
async function parseMfaError(res: Response): Promise<MfaApiError> {
  let code: string | null = null;
  let detail = "";
  try {
    const body = (await res.json()) as { code?: string; detail?: string };
    code = body.code ?? null;
    detail = body.detail ?? "";
  } catch {
    // Non-JSON body (e.g. 502 from a proxy) — fall back to status text
  }
  const message = detail || res.statusText || "Request failed.";
  return new MfaApiError(message, code, res.status);
}

/**
 * Fetch Cognito tokens and return auth header object.
 *
 * MFA-WIRE-1 (design §G-Q1): Cognito user-scoped MFA APIs require the
 * **access token** in addition to the ID token. Both are sent on every
 * wizard API call:
 *   - `Authorization: Bearer {idToken}`  (existing — ID token)
 *   - `X-Cognito-Access-Token: {accessToken}`  (NEW — access token)
 *
 * If a token is missing (session expired), the request is still sent —
 * the backend maps the missing/invalid token to the correct RFC 7807
 * error code (design §F.3). Tokens are in-memory only; never logged.
 *
 * NOTE: The `fetch`→`apiClient` migration for this helper is deferred to
 * PLAT-DEBT (design §G-Q7). This batch only adds the access-token header.
 */
async function getAuthHeaders(): Promise<Record<string, string>> {
  const headers: Record<string, string> = {};
  try {
    const { fetchAuthSession } = await import("aws-amplify/auth");
    const session = await fetchAuthSession();
    const idToken = session.tokens?.idToken?.toString();
    const accessToken = session.tokens?.accessToken?.toString();
    if (idToken) headers["Authorization"] = `Bearer ${idToken}`;
    if (accessToken) headers["X-Cognito-Access-Token"] = accessToken;
  } catch {
    // not authenticated — request will 401; headers stay empty
  }
  return headers;
}

async function mfaEnrollStart(
  methodType: MFAEnrollmentPath,
): Promise<MfaEnrollStartPayload> {
  const authHeaders = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE}/me/mfa/methods/${methodType}/enroll-start`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders },
    },
  );
  if (!res.ok) throw await parseMfaError(res);
  return res.json() as Promise<MfaEnrollStartPayload>;
}

async function mfaEnrollConfirm(
  methodType: MFAEnrollmentPath,
  code: string,
): Promise<{ method_id: string; enrolled_at: string }> {
  const authHeaders = await getAuthHeaders();
  const res = await fetch(
    `${API_BASE}/me/mfa/methods/${methodType}/enroll-confirm`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders },
      body: JSON.stringify({ code }),
    },
  );
  if (!res.ok) throw await parseMfaError(res);
  return res.json() as Promise<{ method_id: string; enrolled_at: string }>;
}

async function mfaGetRecoveryCodesStatus(): Promise<{
  unused_code_count: number;
}> {
  const authHeaders = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/me/mfa/recovery-codes/status`, {
    headers: authHeaders,
  });
  if (!res.ok) throw new Error("Failed to check recovery codes.");
  return res.json() as Promise<{ unused_code_count: number }>;
}

async function mfaGenerateRecoveryCodes(): Promise<{
  codes: string[];
  set_id: string;
}> {
  const authHeaders = await getAuthHeaders();
  const res = await fetch(`${API_BASE}/me/mfa/recovery-codes/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders },
  });
  if (!res.ok) throw new Error("Failed to generate recovery codes.");
  return res.json() as Promise<{ codes: string[]; set_id: string }>;
}

// ─── Step Indicator ────────────────────────────────────────────────────────────

function StepIndicator({
  steps,
  currentStep,
}: {
  steps: MFAEnrollmentStep[];
  currentStep: MFAEnrollmentStep;
}) {
  const currentIndex = steps.indexOf(currentStep);
  return (
    <nav aria-label="Enrollment steps" className="flex items-center gap-2">
      {steps.map((step, index) => {
        const isActive = step === currentStep;
        const isCompleted = index < currentIndex;
        return (
          <React.Fragment key={step}>
            <div
              className="flex items-center gap-1"
              aria-current={isActive ? "step" : undefined}
            >
              <div
                className={`w-2 h-2 rounded-full ${
                  isActive
                    ? "bg-brand-600"
                    : isCompleted
                      ? "bg-margin-600"
                      : "bg-neutral-300"
                }`}
                aria-hidden="true"
              />
              <span
                className={`text-xs ${isActive ? "text-brand-600 font-medium" : "text-neutral-400"}`}
              >
                {MFA_STEP_LABELS[step]}
              </span>
            </div>
            {index < steps.length - 1 && (
              <div className="w-4 h-px bg-neutral-200" aria-hidden="true" />
            )}
          </React.Fragment>
        );
      })}
    </nav>
  );
}

// ─── Grace Period Banner ───────────────────────────────────────────────────────

function GracePeriodBanner({ daysRemaining }: { daysRemaining: number }) {
  // Design doc Section H token audit:
  // >3 days: info-50 bg, info-700 text
  // 1-3 days: alert-50 bg, alert-700 text
  // 0 days: error-50 bg, error-700 text
  const isToday = daysRemaining === 0;
  const isUrgent = daysRemaining <= 3 && daysRemaining > 0;

  const className = isToday
    ? "bg-error-50 border border-error-200 text-error-700"
    : isUrgent
      ? "bg-alert-50 border border-alert-200 text-alert-700"
      : "bg-info-50 border border-info-200 text-info-700";

  const message = isToday
    ? "MFA enrollment is required today to continue using Pilot."
    : `Enrollment required in ${daysRemaining} day${daysRemaining === 1 ? "" : "s"}.`;

  return (
    <div role="alert" className={`rounded-md px-4 py-3 text-sm ${className}`}>
      {message}
    </div>
  );
}

// ─── Method Select Step ────────────────────────────────────────────────────────

function MethodSelectStep({
  allowedPaths,
  enrolledMethods,
  selectedPath,
  onSelect,
}: {
  allowedPaths: MFAEnrollmentPath[];
  enrolledMethods: MFAEnrollmentPath[];
  selectedPath: MFAEnrollmentPath | null;
  onSelect: (path: MFAEnrollmentPath) => void;
}) {
  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-h3 font-semibold text-neutral-900">
          Choose your authentication method
        </h2>
        <p className="mt-1 text-sm text-neutral-500">
          Select how you&apos;d like to verify your identity when signing in.
        </p>
      </div>
      <div
        className="flex flex-col gap-2"
        role="radiogroup"
        aria-label="MFA method"
      >
        {allowedPaths.map((path) => {
          const isEnrolled = enrolledMethods.includes(path);
          return (
            <button
              key={path}
              type="button"
              onClick={() => !isEnrolled && onSelect(path)}
              aria-pressed={selectedPath === path}
              disabled={isEnrolled}
              className={`
                text-left px-4 py-3 rounded-lg border-2 transition-colors
                focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2
                ${
                  isEnrolled
                    ? "border-margin-200 bg-margin-50 cursor-not-allowed opacity-70"
                    : selectedPath === path
                      ? "border-brand-600 bg-brand-50"
                      : "border-neutral-200 hover:border-neutral-300"
                }
              `}
            >
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-sm font-medium text-neutral-800">
                    {MFA_PATH_LABELS[path]}
                  </span>
                  <p className="text-xs text-neutral-500 mt-0.5">
                    {MFA_PATH_DESCRIPTIONS[path]}
                  </p>
                </div>
                {isEnrolled && (
                  <span className="ml-3 flex-shrink-0 rounded-full bg-margin-100 px-2 py-0.5 text-xs font-medium text-margin-700">
                    Enrolled
                  </span>
                )}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ─── TOTP Setup Step ───────────────────────────────────────────────────────────

function TotpSetupStep({ payload }: { payload: MfaEnrollStartPayload | null }) {
  if (!payload) return null;
  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-h3 font-semibold text-neutral-900">
          Set up authenticator app
        </h2>
        <p className="mt-1 text-sm text-neutral-500">
          Scan this QR code with your authenticator app (Google Authenticator,
          Authy, 1Password, etc.).
        </p>
      </div>
      {/* QR code rendered as img with data URI or external URL */}
      <div className="flex flex-col items-center gap-4 rounded-lg border border-neutral-200 p-6">
        <img
          src={`https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=${encodeURIComponent(payload.qr_code_uri ?? "")}`}
          alt={`QR code for TOTP setup. Secret: ${payload.secret ?? ""}`}
          width={180}
          height={180}
          className="rounded"
          data-testid="totp-qr-code"
        />
        {payload.secret && (
          <div className="w-full">
            <p className="text-xs text-neutral-500 mb-1">
              Can&apos;t scan? Enter this secret manually:
            </p>
            <code
              className="block rounded bg-neutral-50 border border-neutral-200 px-3 py-2 text-sm font-mono text-neutral-800 break-all"
              data-testid="totp-secret"
            >
              {payload.secret}
            </code>
          </div>
        )}
      </div>
      <p className="text-sm text-neutral-600">
        After scanning, click <strong>Continue</strong> to verify your setup.
      </p>
    </div>
  );
}

// ─── SMS Setup Step ────────────────────────────────────────────────────────────

function SmsSetupStep({ destination }: { destination: string }) {
  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-h3 font-semibold text-neutral-900">
          Verify your phone number
        </h2>
        <p className="mt-1 text-sm text-neutral-500">
          We&apos;ll send a 6-digit verification code to:
        </p>
      </div>
      <div
        className="rounded-lg border border-neutral-200 bg-neutral-50 px-4 py-3"
        data-testid="sms-destination"
      >
        <span className="font-mono text-sm text-neutral-900">
          {destination}
        </span>
      </div>
      {/* ── 10DLC-COMPLIANT SMS DISCLOSURE — MANDATORY — DO NOT REMOVE OR EDIT ── */}
      <p
        className="text-xs text-neutral-500 leading-relaxed"
        data-testid="sms-consent-disclosure"
      >
        By enrolling your phone number, you consent to receive one-time
        verification codes from Pilot for Trades. Message frequency: One message
        per sign-in attempt, login or enrollment event. Message and data rates
        may apply. Reply STOP to opt out. Reply HELP for help. Privacy policy:{" "}
        <a
          href="https://www.pilotfortrades.com/legal/privacy"
          target="_blank"
          rel="noopener noreferrer"
          className="underline hover:text-neutral-700"
        >
          www.pilotfortrades.com/legal/privacy
        </a>
        .
      </p>
      <p className="text-sm text-neutral-600">
        Click <strong>Send code</strong> to receive your verification code.
      </p>
    </div>
  );
}

// ─── Email Setup Step ──────────────────────────────────────────────────────────

function EmailSetupStep({ destination }: { destination: string }) {
  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-h3 font-semibold text-neutral-900">
          Verify your email
        </h2>
        <p className="mt-1 text-sm text-neutral-500">
          We&apos;ll send a 6-digit verification code to:
        </p>
      </div>
      <div
        className="rounded-lg border border-neutral-200 bg-neutral-50 px-4 py-3"
        data-testid="email-destination"
      >
        <span className="font-mono text-sm text-neutral-900">
          {destination}
        </span>
      </div>
      <p className="text-sm text-neutral-600">
        Click <strong>Send code</strong> to receive your verification code.
      </p>
    </div>
  );
}

// ─── Verify Step ──────────────────────────────────────────────────────────────

function VerifyStep({
  path,
  codeInput,
  error,
  isLoading,
  onCodeChange,
  onResend,
}: {
  path: MFAEnrollmentPath | null;
  codeInput: string;
  error: string | null;
  isLoading: boolean;
  onCodeChange: (val: string) => void;
  onResend?: () => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const headings: Record<MFAEnrollmentPath, string> = {
    totp: "Enter the code from your authenticator app",
    sms: "Enter the code we texted you",
    email: "Enter the code we emailed you",
  };

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-h3 font-semibold text-neutral-900">
          {path ? headings[path] : "Enter verification code"}
        </h2>
        <p className="mt-1 text-sm text-neutral-500">
          Enter the 6-digit verification code.
        </p>
      </div>

      <div>
        <input
          ref={inputRef}
          type="text"
          inputMode="numeric"
          pattern="[0-9]{6}"
          maxLength={6}
          autoComplete="one-time-code"
          value={codeInput}
          onChange={(e) => {
            const val = e.target.value.replace(/\D/g, "").slice(0, 6);
            onCodeChange(val);
          }}
          placeholder="000000"
          disabled={isLoading}
          aria-label="6-digit verification code"
          aria-invalid={!!error}
          aria-describedby={error ? "verify-error" : undefined}
          className={`
            w-full rounded-lg border px-4 py-3 text-center text-2xl font-mono tracking-widest
            focus:outline-none focus:ring-2 focus:ring-brand-600 focus:ring-offset-1
            disabled:opacity-50
            ${error ? "border-fault-500" : "border-neutral-300"}
          `}
          data-testid="mfa-code-input"
        />
        {error && (
          <p
            id="verify-error"
            role="alert"
            className="mt-2 text-sm text-fault-600"
            data-testid="mfa-code-error"
          >
            {error}
          </p>
        )}
      </div>

      {path !== "totp" && onResend && (
        <button
          type="button"
          onClick={onResend}
          disabled={isLoading}
          className="text-sm text-brand-600 hover:text-brand-800 focus:outline-none focus:underline disabled:opacity-50"
        >
          Resend code
        </button>
      )}
    </div>
  );
}

// ─── Recovery Codes Step ───────────────────────────────────────────────────────

function RecoveryCodesStep({
  codes,
  acknowledged,
  onAcknowledge,
}: {
  codes: string[];
  acknowledged: boolean;
  onAcknowledge: (val: boolean) => void;
}) {
  const handleCopyAll = async () => {
    await navigator.clipboard.writeText(codes.join("\n"));
  };

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-h3 font-semibold text-neutral-900">
          Save your recovery codes
        </h2>
        <p className="mt-1 text-sm text-neutral-500">
          Keep these recovery codes in a safe place. You can use them to access
          your account if you lose access to your authentication method.
        </p>
      </div>

      <div
        className="rounded-lg border border-neutral-200 bg-neutral-50 p-4"
        data-testid="recovery-codes-container"
      >
        <div className="grid grid-cols-2 gap-2">
          {codes.map((code) => (
            <code
              key={code}
              className="rounded bg-white border border-neutral-100 px-2 py-1.5 text-xs font-mono text-neutral-800 text-center"
            >
              {code}
            </code>
          ))}
        </div>
      </div>

      <button
        type="button"
        onClick={handleCopyAll}
        className="flex items-center gap-1.5 text-sm text-brand-600 hover:text-brand-800 focus:outline-none focus:underline"
        data-testid="copy-recovery-codes"
      >
        <svg
          className="w-4 h-4"
          fill="none"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        Copy all codes
      </button>

      <label className="flex items-start gap-3 cursor-pointer">
        <input
          type="checkbox"
          checked={acknowledged}
          onChange={(e) => onAcknowledge(e.target.checked)}
          className="mt-0.5 h-4 w-4 rounded border-neutral-300 text-brand-600 focus:ring-brand-600"
          data-testid="recovery-codes-checkbox"
        />
        <span
          className={`text-sm font-medium ${acknowledged ? "text-neutral-700" : "text-fault-700"}`}
        >
          I&apos;ve saved my recovery codes in a safe place.
        </span>
      </label>
    </div>
  );
}

// ─── Complete Step ─────────────────────────────────────────────────────────────

function CompleteStep({ path }: { path: MFAEnrollmentPath | null }) {
  return (
    <div className="flex flex-col items-center gap-4 py-8">
      <div className="w-12 h-12 rounded-full bg-margin-100 flex items-center justify-center">
        <svg
          className="w-6 h-6 text-margin-600"
          fill="none"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            d="M5 13l4 4L19 7"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>
      <h2 className="text-h3 font-semibold text-neutral-900">MFA enabled</h2>
      <p className="text-sm text-neutral-500 text-center max-w-xs">
        {path
          ? `Your account is now protected with ${MFA_PATH_LABELS[path]}.`
          : "Your account is now protected with multi-factor authentication."}
      </p>
    </div>
  );
}

// ─── Internal step to external step mapper ────────────────────────────────────

function internalToExternal(step: MFAWizardInternalStep): MFAEnrollmentStep {
  if (step === "method-select") return "method-select";
  if (step.startsWith("setup-")) return "setup";
  if (step.startsWith("verify-") || step === "recovery-codes") return "verify";
  return "complete";
}

const ALL_PATHS: MFAEnrollmentPath[] = ["totp", "sms", "email"];

// ─── Main Wizard ──────────────────────────────────────────────────────────────

/**
 * MFAEnrollmentWizard (web — fleshed out from FE-B1 skeleton)
 *
 * All original FE-B1 props work unchanged. New optional props added by FE-B12:
 * forceFlow, showRecoveryCodes, onRecoveryCodesAcknowledged, enrolledMethods.
 *
 * @example (FE-B1 skeleton usage — still works)
 * <MFAEnrollmentWizard onComplete={handleComplete} onCancel={handleCancel} />
 *
 * @example (FE-B12 force-flow usage)
 * <MFAEnrollmentWizard
 *   forceFlow={true}
 *   gracePeriodDaysRemaining={2}
 *   onComplete={handleComplete}
 *   onCancel={() => {}}
 * />
 */
export function MFAEnrollmentWizard({
  forcedPath,
  allowedPaths = ALL_PATHS,
  onComplete,
  onCancel,
  gracePeriodDaysRemaining,
  currentStep: externalStep,
  testID,
  // FE-B12 new optional props
  forceFlow = false,
  showRecoveryCodes: showRecoveryCodesProp,
  onRecoveryCodesAcknowledged,
  enrolledMethods = [],
}: MFAEnrollmentWizardPropsExtended) {
  const [internalStep, setInternalStep] = useState<MFAWizardInternalStep>(
    forcedPath ? `setup-${forcedPath}` : "method-select",
  );
  const [selectedPath, setSelectedPath] = useState<MFAEnrollmentPath | null>(
    forcedPath ?? null,
  );
  const [enrollStartPayload, setEnrollStartPayload] =
    useState<MfaEnrollStartPayload | null>(null);
  const [codeInput, setCodeInput] = useState("");
  const [recoveryCodes, setRecoveryCodes] = useState<string[] | null>(null);
  const [recoveryCodesAcknowledged, setRecoveryCodesAcknowledged] =
    useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<MfaApiError | null>(null);
  const [showRecoveryCodesResolved, setShowRecoveryCodesResolved] =
    useState<boolean>(showRecoveryCodesProp ?? true);

  // ─── Error-code → copy/placement mapping (spec §9) ───────────────────────
  // The backend returns RFC 7807 Problem Details with a `code` field.
  // Each code maps to a specific copy string and placement slot:
  //   - "top"    → top-of-wizard error banner (data-testid="wizard-error")
  //   - "inline" → inline verify error (id="verify-error")
  //   - "warning-top" → top-of-wizard warning banner (503 sms_delivery_not_configured)
  //
  // `null` code = network-level failure → generic top-of-wizard error.
  type ErrorPlacement = "top" | "inline" | "warning-top";

  function resolveErrorPlacement(
    err: MfaApiError,
    path: MFAEnrollmentPath | null,
  ): ErrorPlacement {
    switch (err.code) {
      case "mfa_code_invalid":
      case "mfa_code_expired":
        return "inline";
      case "sms_delivery_not_configured":
        return "warning-top";
      default:
        // SMS-setup-specific codes render at top during setup-sms
        if (
          path === "sms" &&
          (err.code === "phone_number_required" ||
            err.code === "phone_number_invalid")
        ) {
          return "top";
        }
        return "top";
    }
  }

  function resolveErrorCopy(
    err: MfaApiError,
    path: MFAEnrollmentPath | null,
  ): string {
    const authenticatorWord = path === "sms" ? "phone" : "authenticator app";
    switch (err.code) {
      case "mfa_access_token_required":
        return "Your session needs a fresh authentication token. Please sign out and sign back in, then try again.";
      case "mfa_access_token_invalid":
        return "Your session has expired. Please sign in again to manage your MFA methods.";
      case "mfa_code_invalid":
        return `That code doesn't match. Check your ${authenticatorWord} and try again.`;
      case "mfa_code_expired":
        if (path === "totp") {
          return "That code has expired. Restart authenticator setup.";
        }
        return "That code has expired. Tap 'Resend code' and try again.";
      case "phone_number_required":
        return "We need a phone number on your profile to send text-message codes. Add one at Account → Profile, then come back.";
      case "phone_number_invalid":
        return "That phone number doesn't look right. Update it at Account → Profile using the format +1 (555) 555-1234, then try again.";
      case "sms_delivery_not_configured":
        return "Text-message setup is temporarily unavailable — use an authenticator app instead.";
      case "cognito_unavailable":
        return "We couldn't reach the authentication service. Your enrollment was not completed. Please try again in a moment.";
      default:
        // Network-level failure (no code) or unknown code → generic
        return err.message || "Something went wrong. Please try again.";
    }
  }

  // On mount, if showRecoveryCodes is not explicitly provided, check status endpoint
  useEffect(() => {
    if (showRecoveryCodesProp !== undefined) {
      setShowRecoveryCodesResolved(showRecoveryCodesProp);
      return;
    }
    void mfaGetRecoveryCodesStatus()
      .then(({ unused_code_count }) => {
        setShowRecoveryCodesResolved(unused_code_count === 0);
      })
      .catch(() => {
        // Default to showing recovery codes if status check fails
        setShowRecoveryCodesResolved(true);
      });
  }, [showRecoveryCodesProp]);

  // If forcedPath provided, auto-start enrollment on mount
  useEffect(() => {
    if (forcedPath) {
      void handleStartEnrollment(forcedPath);
    }
  }, [forcedPath]);

  const currentInternalStep = internalStep;
  // External step prop maps to internal, but external wins for display
  const displayExternalStep: MFAEnrollmentStep = externalStep
    ? externalStep
    : internalToExternal(currentInternalStep);

  const visibleSteps: MFAEnrollmentStep[] = forcedPath
    ? (MFA_STEP_ORDER.filter(
        (s) => s !== "method-select",
      ) as MFAEnrollmentStep[])
    : MFA_STEP_ORDER;

  async function handleSelectPath(path: MFAEnrollmentPath) {
    setSelectedPath(path);
    await handleStartEnrollment(path);
  }

  async function handleStartEnrollment(path: MFAEnrollmentPath) {
    setIsLoading(true);
    setError(null);
    try {
      const payload = await mfaEnrollStart(path);
      setEnrollStartPayload(payload);
      setInternalStep(`setup-${path}` as MFAWizardInternalStep);
    } catch (err) {
      setError(
        err instanceof MfaApiError
          ? err
          : new MfaApiError(
              err instanceof Error
                ? err.message
                : "Failed to start enrollment.",
              null,
              0,
            ),
      );
    } finally {
      setIsLoading(false);
    }
  }

  async function handleContinueFromSetup() {
    if (!selectedPath) return;
    // For TOTP, just advance to verify (no code needed yet — user scans QR first)
    // For SMS/Email, "Continue" sends code and advances to verify
    if (selectedPath === "totp") {
      setInternalStep("verify-totp");
    } else {
      // Re-call enroll-start to send the code
      setIsLoading(true);
      setError(null);
      try {
        await mfaEnrollStart(selectedPath);
        setInternalStep(`verify-${selectedPath}` as MFAWizardInternalStep);
      } catch (err) {
        setError(
          err instanceof MfaApiError
            ? err
            : new MfaApiError(
                err instanceof Error ? err.message : "Failed to send code.",
                null,
                0,
              ),
        );
      } finally {
        setIsLoading(false);
      }
    }
  }

  async function handleVerify() {
    if (!selectedPath || codeInput.length !== 6) return;
    setIsLoading(true);
    setError(null);
    setCodeInput("");
    try {
      await mfaEnrollConfirm(selectedPath, codeInput);
      // Advance to recovery codes or complete
      if (showRecoveryCodesResolved) {
        setIsLoading(true);
        try {
          const result = await mfaGenerateRecoveryCodes();
          setRecoveryCodes(result.codes);
          setInternalStep("recovery-codes");
        } catch {
          // If recovery code generation fails, still advance to complete
          setInternalStep("complete");
          onComplete(selectedPath);
        } finally {
          setIsLoading(false);
        }
      } else {
        setInternalStep("complete");
        onComplete(selectedPath);
      }
    } catch (err) {
      setError(
        err instanceof MfaApiError
          ? err
          : new MfaApiError(
              err instanceof Error ? err.message : "Verification failed.",
              null,
              0,
            ),
      );
    } finally {
      setIsLoading(false);
    }
  }

  async function handleResendCode() {
    if (!selectedPath || selectedPath === "totp") return;
    setIsLoading(true);
    setError(null);
    try {
      await mfaEnrollStart(selectedPath);
    } catch (err) {
      setError(
        err instanceof MfaApiError
          ? err
          : new MfaApiError(
              err instanceof Error ? err.message : "Failed to resend code.",
              null,
              0,
            ),
      );
    } finally {
      setIsLoading(false);
    }
  }

  function handleRecoveryCodesComplete() {
    if (!selectedPath) return;
    setInternalStep("complete");
    onRecoveryCodesAcknowledged?.();
    onComplete(selectedPath);
  }

  const isSetupStep = currentInternalStep.startsWith("setup-");
  const isVerifyStep = currentInternalStep.startsWith("verify-");
  const isRecoveryStep = currentInternalStep === "recovery-codes";
  const isCompleteStep = currentInternalStep === "complete";
  const isMethodSelect = currentInternalStep === "method-select";

  const canContinueFromSetup = !isLoading && !!enrollStartPayload;
  const canVerify = !isLoading && codeInput.length === 6;
  const canCompleteRecovery = !isLoading && recoveryCodesAcknowledged;

  return (
    <div
      data-testid={testID ?? "mfa-enrollment-wizard"}
      className={`flex flex-col gap-6 p-8 max-w-md mx-auto ${forceFlow ? "min-h-screen justify-start pt-16" : ""}`}
      role="dialog"
      aria-label="MFA Enrollment"
      aria-modal="true"
    >
      {/* Grace period banner */}
      {gracePeriodDaysRemaining !== undefined && (
        <GracePeriodBanner daysRemaining={gracePeriodDaysRemaining} />
      )}

      {/* Step indicator */}
      <StepIndicator steps={visibleSteps} currentStep={displayExternalStep} />

      {/* Step content */}
      <div className="flex flex-col gap-4">
        {isMethodSelect && (
          <MethodSelectStep
            allowedPaths={allowedPaths}
            enrolledMethods={enrolledMethods}
            selectedPath={selectedPath}
            onSelect={handleSelectPath}
          />
        )}

        {currentInternalStep === "setup-totp" && (
          <TotpSetupStep payload={enrollStartPayload} />
        )}

        {currentInternalStep === "setup-sms" && (
          <SmsSetupStep
            destination={enrollStartPayload?.destination_masked ?? "your phone"}
          />
        )}

        {currentInternalStep === "setup-email" && (
          <EmailSetupStep
            destination={enrollStartPayload?.destination_masked ?? "your email"}
          />
        )}

        {isVerifyStep && (
          <VerifyStep
            path={selectedPath}
            codeInput={codeInput}
            error={
              error && resolveErrorPlacement(error, selectedPath) === "inline"
                ? resolveErrorCopy(error, selectedPath)
                : null
            }
            isLoading={isLoading}
            onCodeChange={(val) => {
              setCodeInput(val);
              setError(null);
            }}
            onResend={handleResendCode}
          />
        )}

        {isRecoveryStep && recoveryCodes && (
          <RecoveryCodesStep
            codes={recoveryCodes}
            acknowledged={recoveryCodesAcknowledged}
            onAcknowledge={setRecoveryCodesAcknowledged}
          />
        )}

        {isCompleteStep && <CompleteStep path={selectedPath} />}

        {/*
          Top-of-wizard error banner (spec §9).
          Renders when error is non-null AND placement is "top" or "warning-top"
          (inline errors are handled by VerifyStep above).
          - 503 sms_delivery_not_configured → warning style (alert tokens) +
            "Set up authenticator app" nudge button.
          - phone_number_required / phone_number_invalid → error style with a
            plain <a> link to /settings/my-account/profile.
          - mfa_code_expired on TOTP during setup → "Restart setup" affordance
            that re-invokes handleStartEnrollment(selectedPath).
          - All other top errors → standard fault error text.
        */}
        {error &&
          !isVerifyStep &&
          (resolveErrorPlacement(error, selectedPath) === "top" ||
            resolveErrorPlacement(error, selectedPath) === "warning-top") &&
          (() => {
            const placement = resolveErrorPlacement(error, selectedPath);
            const copy = resolveErrorCopy(error, selectedPath);
            const isWarning = placement === "warning-top";
            const isPhoneError =
              error.code === "phone_number_required" ||
              error.code === "phone_number_invalid";
            const isTotpExpiredSetup =
              error.code === "mfa_code_expired" &&
              selectedPath === "totp" &&
              isSetupStep;
            return (
              <div
                role="alert"
                data-testid="wizard-error"
                className={`flex items-start gap-3 rounded-md border px-4 py-3 text-sm ${
                  isWarning
                    ? "bg-alert-50 border-alert-200 text-alert-700"
                    : "text-fault-600"
                }`}
              >
                {isWarning && (
                  <svg
                    className="w-5 h-5 flex-shrink-0 text-alert-600"
                    fill="none"
                    viewBox="0 0 24 24"
                    aria-hidden="true"
                  >
                    <path
                      d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                )}
                <div className="flex flex-col gap-2">
                  <span>
                    {isPhoneError ? (
                      <>
                        {copy.split("Account → Profile")[0]}
                        <a
                          href="/settings/my-account/profile"
                          className="font-medium text-brand-600 underline hover:text-brand-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 rounded"
                        >
                          Account → Profile
                        </a>
                        {copy.split("Account → Profile")[1] ?? ""}
                      </>
                    ) : (
                      copy
                    )}
                  </span>
                  {isWarning && (
                    <button
                      type="button"
                      onClick={() => handleSelectPath("totp")}
                      className="self-start rounded-md bg-brand-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2"
                      data-testid="wizard-sms-fallback-totp"
                    >
                      Set up authenticator app
                    </button>
                  )}
                  {isTotpExpiredSetup && (
                    <button
                      type="button"
                      onClick={() =>
                        selectedPath && void handleStartEnrollment(selectedPath)
                      }
                      className="self-start rounded-md bg-brand-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2"
                      data-testid="wizard-totp-restart-setup"
                    >
                      Restart setup
                    </button>
                  )}
                </div>
              </div>
            );
          })()}
      </div>

      {/* Footer actions */}
      {!isCompleteStep && (
        <div className="flex items-center justify-between pt-4 border-t border-neutral-200">
          {/* Cancel button — hidden in force-flow mode */}
          {!forceFlow ? (
            <button
              type="button"
              onClick={onCancel}
              disabled={isLoading}
              className="text-sm text-neutral-500 hover:text-neutral-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-neutral-400 focus-visible:ring-offset-2 disabled:opacity-50"
              aria-label="Cancel MFA enrollment"
            >
              Cancel
            </button>
          ) : (
            <span />
          )}

          {/* Primary action */}
          {isSetupStep && canContinueFromSetup && (
            <button
              type="button"
              onClick={handleContinueFromSetup}
              disabled={isLoading}
              className="px-4 py-2 rounded-md bg-brand-600 text-white text-sm font-medium hover:bg-brand-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2 disabled:opacity-50"
              data-testid="wizard-continue"
            >
              {selectedPath === "totp" ? "Continue" : "Send code"}
            </button>
          )}

          {isVerifyStep && (
            <button
              type="button"
              onClick={handleVerify}
              disabled={!canVerify}
              className="px-4 py-2 rounded-md bg-brand-600 text-white text-sm font-medium hover:bg-brand-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2 disabled:opacity-50"
              data-testid="wizard-verify"
            >
              {isLoading ? "Verifying…" : "Verify"}
            </button>
          )}

          {isRecoveryStep && (
            <button
              type="button"
              onClick={handleRecoveryCodesComplete}
              disabled={!canCompleteRecovery}
              className="px-4 py-2 rounded-md bg-brand-600 text-white text-sm font-medium hover:bg-brand-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2 disabled:opacity-50"
              data-testid="wizard-complete-recovery"
            >
              Continue
            </button>
          )}
        </div>
      )}
    </div>
  );
}
