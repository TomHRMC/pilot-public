/**
 * /signup/phone — Step 3: "Stay Informed" (SIGNUP-C)
 *
 * Location: apps/web/src/app/signup/phone/page.tsx
 *
 * Reframed from "Verify your phone" → "Stay Informed". Phone is REQUIRED
 * (phone_skipped removed). The SMS-alerts consent checkbox is UNCHECKED by
 * default; the reply-YES double-opt-in is the authoritative consent.
 *
 * State machine: "enter" → "confirm" → "confirmed" → /signup/plan
 *   - enter:    phone field + unchecked consent + disclosure + Continue
 *   - confirm:  DoubleOptinConfirmSubscreen (waiting for YES reply)
 *   - confirmed: success banner, auto-advance after 1500ms
 *
 * API flow (all apiClient, types from @pilot/shared-types):
 *   consent checked:  POST /phone/consent → POST /phone/send-optin → PUT /step3 → confirm
 *   consent unchecked: PUT /step3 (sms_consent:false) → /signup/plan
 *
 * RULE 4: On mount, verifies backend state ≥ step2_legal or redirects.
 */

"use client";

import React, { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { apiClient, getApiProblem } from "@pilot/shared-api";
import { useAuth } from "@pilot/ui/auth";
import { PhoneInput } from "@pilot/ui/phone-input";
import { WizardProgressBar } from "@/features/signup/components/WizardProgressBar";
import {
  SmsConsentDisclosure,
  SMS_CONSENT_DISCLOSURE_TEXT,
} from "@/features/signup/components/SmsConsentDisclosure";
import { DoubleOptinConfirmSubscreen } from "@/features/signup/components/DoubleOptinConfirmSubscreen";
import { ExclamationCircleIcon } from "@heroicons/react/24/outline";
import {
  WIZARD_TENANT_ID_KEY,
  signupStateToStep,
  stepToUrl,
  OnboardingStep,
  type WizardSignupState,
} from "@/features/signup/types";

type StayInformedStep = "enter" | "confirm" | "confirmed" | "poll_timeout";

// E.164: + followed by 7-15 digits (country code 1-9 + subscriber).
const PHONE_E164_RE = /^\+?[1-9]\d{6,14}$/;
const POLL_INTERVAL_MS = 3000;
const POLL_MAX_ATTEMPTS = 100; // 5 minutes
const CONFIRMED_ADVANCE_MS = 1500;

/** Preserves leading country code + last 4 digits; masks the rest. */
function maskPhone(phone: string): string {
  const digits = phone.replace(/\D/g, "");
  if (digits.length < 5) return phone;
  const countryCodeLen = phone.startsWith("+") ? digits.length - 10 : 0;
  const head = phone.startsWith("+") ? "+" : "";
  const cc = digits.slice(0, Math.max(1, countryCodeLen));
  const last4 = digits.slice(-4);
  const maskedLen = digits.length - cc.length - last4.length;
  const masked = "•".repeat(Math.max(0, maskedLen));
  return `${head}${cc} (${masked.slice(0, 3)}) ${masked.slice(3, 6)}-${last4}`;
}

/** SHA-256 hex of the disclosure text (Web Crypto API). */
async function computeDisclosureHash(text: string): Promise<string> {
  const data = new TextEncoder().encode(text);
  const buf = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(buf))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

export default function SignupPhonePage() {
  const router = useRouter();
  const { user } = useAuth();
  // SIGNUP-UI-FIX-1: fall back to user.tenantId when sessionStorage is cleared
  const [tenantId] = useState<string | null>(() =>
    typeof window !== "undefined"
      ? (sessionStorage.getItem(WIZARD_TENANT_ID_KEY) ?? user?.tenantId ?? null)
      : null,
  );
  const [phoneStep, setPhoneStep] = useState<StayInformedStep>("enter");
  const [phoneNumber, setPhoneNumber] = useState<string | null>(null);
  const [phoneTouched, setPhoneTouched] = useState(false);
  const [smsConsent, setSmsConsent] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  // TEST-UPLIFT-1B STEP 5: bounded polling escape state + fetch-error surface
  const [pollError, setPollError] = useState<string | null>(null);
  // SIGNUP-UI-FIX-2 Task 4: lift userEndpointId to state so the Resend
  // handler in the confirm subscreen can reuse it without re-submitting
  // the consent form.
  const [userEndpointId, setUserEndpointId] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── State guard (RULE 4) ────────────────────────────────────────────────
  useEffect(() => {
    if (!tenantId) {
      router.replace("/signup/account");
      return;
    }
    // SIGNUP-UI-FIX-1: persist tenantId to sessionStorage for subsequent steps
    if (!sessionStorage.getItem(WIZARD_TENANT_ID_KEY) && tenantId) {
      sessionStorage.setItem(WIZARD_TENANT_ID_KEY, tenantId);
    }
    apiClient
      .get(`/api/v1/signup/${tenantId}/state`)
      .then((res) => {
        const current = res.data.signup_state as WizardSignupState;
        if (current === "complete") {
          router.replace("/dashboard");
          return;
        }
        const belongsOn = signupStateToStep[current];
        if (belongsOn !== OnboardingStep.Phone) {
          router.replace(stepToUrl[belongsOn] ?? "/signup/account");
        }
      })
      .catch(() => {
        sessionStorage.removeItem(WIZARD_TENANT_ID_KEY);
        router.replace("/signup/account");
      });
  }, [router, tenantId]);

  // ── Polling for YES confirmation (confirm state) ────────────────────────
  // TEST-UPLIFT-1B STEP 5: Bounded polling — max attempts → escape state,
  // fetch errors → getApiProblem + error surface (never infinite hang).
  useEffect(() => {
    if (phoneStep !== "confirm" || !tenantId) return;
    let attempts = 0;
    pollRef.current = setInterval(async () => {
      attempts += 1;
      if (attempts > POLL_MAX_ATTEMPTS) {
        if (pollRef.current) clearInterval(pollRef.current);
        // Escape state: poll exhausted without opted_in → defined error UI
        setPollError(
          "We didn't receive your reply in time. Check your phone and try again, or contact support.",
        );
        setPhoneStep("poll_timeout");
        return;
      }
      try {
        const res = await apiClient.get(`/api/v1/signup/${tenantId}/state`);
        const status = res.data?.collected_data?.sms_consent_status;
        if (status === "opted_in") {
          if (pollRef.current) clearInterval(pollRef.current);
          setConfirmed(true);
          setPhoneStep("confirmed");
          setTimeout(() => router.push("/signup/plan"), CONFIRMED_ADVANCE_MS);
        }
      } catch (err: unknown) {
        // TEST-UPLIFT-1B: render fetch errors via getApiProblem instead of
        // silently swallowing — the 2026-08-10 hang was caused by swallowed
        // errors masking a backend that never returned the expected field.
        if (pollRef.current) clearInterval(pollRef.current);
        const problem = getApiProblem(err);
        setPollError(
          problem.detail ??
            "Couldn't check your confirmation status. Please try again.",
        );
        setPhoneStep("poll_timeout");
      }
    }, POLL_INTERVAL_MS);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [phoneStep, tenantId, router]);

  const phoneValid = phoneNumber != null && PHONE_E164_RE.test(phoneNumber);
  // PLP-FIX-4: PhoneInput emits null for partial/empty. Phone is required,
  // so show the error on blur whenever the number is not valid E.164.
  const showPhoneError = phoneTouched && !phoneValid;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setPhoneTouched(true);
    if (!phoneValid || !tenantId || !phoneNumber) return;

    setIsSubmitting(true);
    setSubmitError(null);
    const normalizedPhone = phoneNumber;
    const disclosureHash = await computeDisclosureHash(
      SMS_CONSENT_DISCLOSURE_TEXT,
    );

    try {
      if (smsConsent) {
        // 1. POST /phone/consent
        const consentRes = await apiClient.post(
          `/api/v1/signup/${tenantId}/phone/consent`,
          {
            phone_number: normalizedPhone,
            sms_consent: true,
            disclosure_hash: disclosureHash,
          },
        );
        const endpointId = consentRes.data.user_endpoint_id;
        setUserEndpointId(endpointId);

        // 2. POST /phone/send-optin
        await apiClient.post(`/api/v1/signup/${tenantId}/phone/send-optin`, {
          user_endpoint_id: endpointId,
        });

        // 3. PUT /step3 (phone required, sms_consent true)
        await apiClient.put(`/api/v1/signup/${tenantId}/step3`, {
          phone_number: normalizedPhone,
          sms_consent: true,
        });

        // 4. Enter confirm sub-state (optimistic "Text sent — reply YES")
        setPhoneStep("confirm");
      } else {
        // Consent unchecked: PUT /step3 with sms_consent:false → /signup/plan
        await apiClient.put(`/api/v1/signup/${tenantId}/step3`, {
          phone_number: normalizedPhone,
          sms_consent: false,
        });
        router.push("/signup/plan");
      }
    } catch (err: unknown) {
      // 429 resend cooldown vs generic consent/save failure
      const problem = getApiProblem(err);
      if (problem.status === 429) {
        setSubmitError(
          "We just sent a text. Wait a moment before trying again.",
        );
      } else if (smsConsent) {
        setSubmitError(
          problem.detail ??
            "Couldn't send confirmation text. Check your number or try again.",
        );
      } else {
        setSubmitError(problem.detail ?? "Failed to save. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUseDifferentNumber = () => {
    if (pollRef.current) clearInterval(pollRef.current);
    setPhoneStep("enter");
    setPhoneNumber(null);
    setConfirmed(false);
    setPollError(null);
    // consent checkbox state retained (per spec §9.1)
  };

  const handleSkipForNow = () => {
    if (pollRef.current) clearInterval(pollRef.current);
    router.push("/signup/plan");
  };

  // SIGNUP-UI-FIX-2 Task 4: Resend the opt-in SMS from the confirm subscreen.
  // Calls POST /phone/send-optin with the userEndpointId retained from the
  // consent response. Returns a ResendResult so the subscreen can show
  // success/error feedback + manage the 60s cooldown.
  const handleResend = async (): Promise<{
    ok: boolean;
    error?: string;
  }> => {
    if (!tenantId || !userEndpointId) {
      return { ok: false, error: "Couldn't resend. Try again." };
    }
    try {
      await apiClient.post(`/api/v1/signup/${tenantId}/phone/send-optin`, {
        user_endpoint_id: userEndpointId,
      });
      return { ok: true };
    } catch (err: unknown) {
      const problem = getApiProblem(err);
      if (problem.status === 429) {
        return {
          ok: false,
          error: "We just sent a text. Wait a moment before trying again.",
        };
      }
      return {
        ok: false,
        error: problem.detail ?? "Couldn't resend. Try again.",
      };
    }
  };

  const buttonLabel = isSubmitting
    ? smsConsent
      ? "Sending…"
      : "Saving…"
    : "Continue →";
  const buttonDisabled = !phoneValid || isSubmitting;

  return (
    <div className="flex flex-col gap-8">
      <WizardProgressBar currentStep="phone" />

      {phoneStep === "enter" && (
        <>
          <div className="flex flex-col gap-2">
            <h1 className="text-2xl font-bold text-neutral-900">
              Stay informed
            </h1>
            <p className="text-sm text-neutral-600">
              Add your mobile number so Pilot can text you about urgent account,
              billing, and security alerts.
            </p>
          </div>

          <form
            onSubmit={handleSubmit}
            className="flex flex-col gap-6"
            data-testid="signup-stayinformed-form"
          >
            {/* Phone number field (required) */}
            <div className="flex flex-col gap-1">
              <label
                htmlFor="field-phone-number"
                className="text-sm font-medium text-neutral-700"
              >
                Mobile number <span className="text-fault-600">*</span>
              </label>
              <PhoneInput
                id="field-phone-number"
                value={phoneNumber ?? ""}
                onChange={(e164) => {
                  setPhoneNumber(e164);
                  setSubmitError(null);
                }}
                onBlur={() => setPhoneTouched(true)}
                data-testid="field-phone-number"
                ariaInvalid={showPhoneError}
                ariaDescribedby={
                  showPhoneError ? "field-phone-number-error" : undefined
                }
                className={`w-full rounded-lg border px-3 py-2.5 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2 focus-visible:border-brand-600 ${
                  showPhoneError
                    ? "border-fault-600 bg-fault-50"
                    : "border-neutral-300"
                }`}
              />
              {!showPhoneError && (
                <p className="text-xs text-neutral-500 mt-1">
                  Required for your account — we{"'"}ll also use this for
                  optional alerts if you opt in below.
                </p>
              )}
              {showPhoneError && (
                <p
                  id="field-phone-number-error"
                  role="alert"
                  data-testid="field-phone-number-error"
                  className="text-xs text-fault-600 mt-1 flex items-center gap-1"
                >
                  <ExclamationCircleIcon
                    className="w-4 h-4 text-fault-600"
                    aria-hidden="true"
                  />
                  Enter a valid mobile number (e.g., +1 555 123 4567).
                </p>
              )}
            </div>

            {/* Consent checkbox (unchecked by default) + disclosure */}
            <div className="flex flex-col gap-3">
              <div className="flex items-start gap-3">
                <input
                  type="checkbox"
                  id="signup-sms-consent-checkbox"
                  checked={smsConsent}
                  onChange={(e) => setSmsConsent(e.target.checked)}
                  data-testid="signup-sms-consent-checkbox"
                  className="mt-0.5 h-5 w-5 rounded accent-brand-600 border-neutral-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2"
                />
                <label
                  htmlFor="signup-sms-consent-checkbox"
                  data-testid="signup-sms-consent-label"
                  className="text-sm font-medium text-neutral-900 cursor-pointer"
                >
                  Yes — text me about urgent account, billing, security, and
                  support updates so I{"'"}m never caught off guard.
                </label>
              </div>
              <SmsConsentDisclosure />
            </div>

            {/* Form-level error */}
            {submitError && (
              <div
                className="flex items-start gap-2"
                data-testid="stayinformed-submit-error"
              >
                <ExclamationCircleIcon
                  className="w-4 h-4 text-fault-600 flex-shrink-0 mt-0.5"
                  aria-hidden="true"
                />
                <p role="alert" className="text-sm text-fault-600">
                  {submitError}
                </p>
              </div>
            )}

            {/* Continue button */}
            <button
              type="submit"
              disabled={buttonDisabled}
              aria-disabled={buttonDisabled}
              data-testid="signup-stayinformed-continue"
              className={`w-full py-3 px-6 rounded-lg text-sm font-semibold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2 ${
                buttonDisabled
                  ? "opacity-40 cursor-not-allowed bg-brand-600 text-white"
                  : "bg-brand-600 hover:bg-brand-800 text-white"
              }`}
            >
              {buttonLabel}
            </button>
          </form>
        </>
      )}

      {(phoneStep === "confirm" || phoneStep === "confirmed") && (
        <DoubleOptinConfirmSubscreen
          maskedPhone={maskPhone(phoneNumber ?? "")}
          confirmed={confirmed}
          onUseDifferentNumber={handleUseDifferentNumber}
          onSkipForNow={handleSkipForNow}
          onResend={userEndpointId ? handleResend : undefined}
        />
      )}

      {/* TEST-UPLIFT-1B STEP 5: Bounded polling escape state — never an infinite spinner */}
      {phoneStep === "poll_timeout" && (
        <div className="flex flex-col gap-4" data-testid="signup-poll-timeout">
          <div>
            <h1 className="text-2xl font-bold text-neutral-900">
              Confirmation timed out
            </h1>
            <p className="text-sm text-neutral-600 mt-2">
              {pollError ??
                "We didn't receive your reply in time. Check your phone and try again."}
            </p>
          </div>
          <div className="flex gap-3">
            <button
              type="button"
              onClick={handleUseDifferentNumber}
              className="px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded-lg hover:bg-brand-700 transition-colors"
              data-testid="poll-timeout-retry"
            >
              Try again
            </button>
            <button
              type="button"
              onClick={handleSkipForNow}
              className="px-4 py-2 text-sm font-medium text-neutral-700 border border-neutral-200 rounded-lg hover:bg-neutral-50 transition-colors"
            >
              Continue without alerts
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
