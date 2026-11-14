/**
 * MFAEnrollmentWizard — Mobile
 *
 * Location: packages/ui/src/mfa-enrollment-wizard/mobile/MFAEnrollmentWizard.tsx
 *
 * MFA-WIRE-1 Part C: fleshed in place from the FE-B12 skeleton.
 * Real enroll-start / enroll-confirm calls with the X-Cognito-Access-Token
 * header, manual-secret TOTP setup, SMS masked-destination + 30s resend,
 * 6-digit verify, recovery-codes complete step, §F.3 error + haptic table.
 *
 * All typography and spacing uses tokens from @pilot/ui/tokens.
 * Zero hex codes. All targets ≥44pt (glove-friendly). allowFontScaling on all Text.
 *
 * Design: batch-mfa-wire-1-design.md §D/§F.3/§G
 * UI spec: batch-mfa-wire-1-mobile-ui-design-spec.md (binding)
 */

import React, { useState, useRef, useEffect, useCallback } from "react";
import { View, Text, Pressable, TextInput, ScrollView } from "react-native";
import Svg, { Path } from "react-native-svg";
import * as Haptics from "expo-haptics";
import * as Clipboard from "expo-clipboard";
// aws-amplify/auth is imported dynamically inside getMfaAuthHeaders() to avoid
// pulling the entire Amplify SDK (which requires react-native-get-random-values)
// into the module graph at load time. A static top-level import breaks every
// test that imports @pilot/ui without mocking Amplify. The dynamic import is
// only evaluated when an API call is actually made (design §G-Q7).
import {
  mobileFontSizes,
  mobileLineHeights,
  fontWeights,
  spacing,
  radii,
  colors,
  lightTheme,
  fonts,
  touchTargets,
} from "../../tokens";
import type {
  MFAEnrollmentPath,
  MFAEnrollmentStep,
  MFAEnrollmentWizardPropsExtended,
  MfaEnrollStartPayload,
} from "../types";
import { MFA_STEP_LABELS } from "../types";

// Mobile supports TOTP and SMS (email requires browser — mobile links to web).
// This filter is already correct — do not "fix" it (spec §1.2).
const MOBILE_ALLOWED_PATHS: MFAEnrollmentPath[] = ["totp", "sms"];

const MOBILE_STEP_ORDER: MFAEnrollmentStep[] = [
  "method-select",
  "setup",
  "verify",
  "complete",
];

// ─── API helpers (STEP 1) ────────────────────────────────────────────────────
//
// Documented exception (design §G-Q7, Tom-approved): the mobile wizard uses
// `fetch` directly — same pattern as the web wizard — because it needs the
// custom X-Cognito-Access-Token header. apiClient migration is PLAT-DEBT.
// Base URL resolution mirrors apps/mobile's established pattern
// (EXPO_PUBLIC_API_URL env var).

// Resolved lazily (at call time, not module-eval time) so tests that set
// EXPO_PUBLIC_API_URL after import are picked up, and env changes are honored.
function apiBase(): string {
  return `${process.env.EXPO_PUBLIC_API_URL ?? ""}/api/v1/users`;
}

/**
 * MfaApiError — structured error carrying the RFC 7807 `code` field.
 * `code` is null for network-level failures (no response body).
 */
class MfaApiError extends Error {
  code: string | null;
  status: number;
  constructor(message: string, code: string | null, status: number) {
    super(message);
    this.name = "MfaApiError";
    this.code = code;
    this.status = status;
  }
}

async function parseMfaError(res: Response): Promise<MfaApiError> {
  let code: string | null = null;
  let detail = "";
  try {
    const body = (await res.json()) as { code?: string; detail?: string };
    code = body.code ?? null;
    detail = body.detail ?? "";
  } catch {
    // Non-JSON body — fall back to status text
  }
  const message = detail || res.statusText || "Request failed.";
  return new MfaApiError(message, code, res.status);
}

/**
 * Fetch Cognito tokens and return auth header object.
 *
 * Sends both:
 *   - Authorization: Bearer {idToken}  (ID token)
 *   - X-Cognito-Access-Token: {accessToken}  (access token — design §G-Q1)
 *
 * Tokens are in-memory only — never logged, never persisted (design §E).
 */
async function getMfaAuthHeaders(): Promise<Record<string, string>> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  try {
    // Dynamic import — evaluated only when an API call is made (see comment above)
    const { fetchAuthSession } = await import("aws-amplify/auth");
    const session = await fetchAuthSession();
    const idToken = session.tokens?.idToken?.toString();
    const accessToken = session.tokens?.accessToken?.toString();
    if (idToken) headers["Authorization"] = `Bearer ${idToken}`;
    if (accessToken) headers["X-Cognito-Access-Token"] = accessToken;
  } catch {
    // not authenticated — request will 401; headers stay minimal
  }
  return headers;
}

async function mfaEnrollStart(
  methodType: MFAEnrollmentPath,
): Promise<MfaEnrollStartPayload> {
  const authHeaders = await getMfaAuthHeaders();
  const res = await fetch(
    `${apiBase()}/me/mfa/methods/${methodType}/enroll-start`,
    {
      method: "POST",
      headers: authHeaders,
    },
  );
  if (!res.ok) throw await parseMfaError(res);
  return (await res.json()) as MfaEnrollStartPayload;
}

async function mfaEnrollConfirm(
  methodType: MFAEnrollmentPath,
  code: string,
): Promise<{ method_id: string; enrolled_at: string }> {
  const authHeaders = await getMfaAuthHeaders();
  const res = await fetch(
    `${apiBase()}/me/mfa/methods/${methodType}/enroll-confirm`,
    {
      method: "POST",
      headers: authHeaders,
      body: JSON.stringify({ code }),
    },
  );
  // 200 = idempotent replay (design §D.2) — treat as success
  if (!res.ok && res.status !== 200) throw await parseMfaError(res);
  return (await res.json()) as { method_id: string; enrolled_at: string };
}

async function mfaGenerateRecoveryCodes(): Promise<{
  codes: string[];
  set_id: string;
}> {
  const authHeaders = await getMfaAuthHeaders();
  const res = await fetch(`${apiBase()}/me/mfa/recovery-codes/generate`, {
    method: "POST",
    headers: authHeaders,
  });
  if (!res.ok) throw new Error("Failed to generate recovery codes.");
  return (await res.json()) as { codes: string[]; set_id: string };
}

// ─── Error copy table (STEP 4 — spec §4 verbatim) ────────────────────────────

type ErrorPlacement = "top" | "inline" | "warning-top" | "setup-sms";

interface ResolvedError {
  placement: ErrorPlacement;
  copy: string;
  isWarning: boolean;
}

function resolveError(
  error: MfaApiError,
  path: MFAEnrollmentPath | undefined,
): ResolvedError {
  const code = error.code;
  switch (code) {
    case "mfa_access_token_required":
      return {
        placement: "top",
        copy: "Your session needs a fresh sign-in. Please sign out and back in, then try again.",
        isWarning: false,
      };
    case "mfa_access_token_invalid":
      return {
        placement: "top",
        copy: "Your session has expired. Sign in again to manage your MFA.",
        isWarning: false,
      };
    case "mfa_code_invalid":
      return {
        placement: "inline",
        copy: "That code didn't match — try again.",
        isWarning: false,
      };
    case "mfa_code_expired":
      return {
        placement: "inline",
        copy:
          path === "sms"
            ? "That code expired — resend a new one."
            : "That code expired — restart authenticator setup.",
        isWarning: false,
      };
    case "phone_number_required":
      return {
        placement: "setup-sms",
        copy: "We need a phone number on your profile to send text codes. Add one in Account → Profile, then come back.",
        isWarning: false,
      };
    case "phone_number_invalid":
      return {
        placement: "setup-sms",
        copy: "That phone number doesn't look right. Update it in Account → Profile, then try again.",
        isWarning: false,
      };
    case "sms_delivery_not_configured":
      return {
        placement: "warning-top",
        copy: "Text-message setup is temporarily unavailable — use an authenticator app instead.",
        isWarning: true,
      };
    case "cognito_unavailable":
      return {
        placement: "top",
        copy: "We couldn't reach the authentication service. Nothing was saved — try again.",
        isWarning: false,
      };
    default:
      // Network-level failure (code null) or unknown code
      return {
        placement: "top",
        copy: "Something went wrong. Please try again.",
        isWarning: false,
      };
  }
}

// ─── Inline SVG icons (spec §8.10 — Heroicons outline paths) ─────────────────

function ShieldCheckIcon({
  size = 24,
  color,
}: {
  size?: number;
  color: string;
}) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <Path
        d="M9 12.75L11.25 15L15 9.75M12 2.25L4.5 5.25V11.25C4.5 16.5 8.25 20.25 12 21.75C15.75 20.25 19.5 16.5 19.5 11.25V5.25L12 2.25Z"
        stroke={color}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </Svg>
  );
}

function DevicePhoneMobileIcon({
  size = 24,
  color,
}: {
  size?: number;
  color: string;
}) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <Path
        d="M10.5 1.5H8.25A2.25 2.25 0 006 3.75v16.5a2.25 2.25 0 002.25 2.25h7.5A2.25 2.25 0 0018 20.25V3.75a2.25 2.25 0 00-2.25-2.25H13.5m-3 0V3h3V1.5m-3 0h3m-3 18.75h3"
        stroke={color}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </Svg>
  );
}

function CheckIcon({ size = 28, color }: { size?: number; color: string }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <Path
        d="M4.5 12.75l6 6 9-13.5"
        stroke={color}
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </Svg>
  );
}

function ExclamationTriangleIcon({
  size = 20,
  color,
}: {
  size?: number;
  color: string;
}) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <Path
        d="M12 9v3.75m0 3.75h.007v.008H12v-.008zM12 2.25c.62 0 1.18.345 1.46.88l7.2 12.48a1.687 1.687 0 01-1.46 2.49H4.8a1.687 1.687 0 01-1.46-2.49l7.2-12.48c.28-.535.84-.88 1.46-.88z"
        stroke={color}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </Svg>
  );
}

// ─── Haptic helpers (spec §8.8) ───────────────────────────────────────────────

function hapticSuccess() {
  Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(
    () => {},
  );
}

function hapticError() {
  Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error).catch(
    () => {},
  );
}

// Warnings (503) get NO haptic — visual-only per voice-feedback §3.

// ─── Copy helper (expo-clipboard — Rule 9.8 approved 2026-08-17) ──────────────

async function copyToClipboard(value: string): Promise<boolean> {
  try {
    await Clipboard.setStringAsync(value);
    return true;
  } catch {
    return false;
  }
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * MFAEnrollmentWizard (mobile)
 *
 * Props widened from MFAEnrollmentWizardProps to MFAEnrollmentWizardPropsExtended
 * (additive — accepts forceFlow, showRecoveryCodes, enrolledMethods from host).
 * types.ts is LOCKED — no changes.
 */
export function MFAEnrollmentWizard({
  forcedPath,
  allowedPaths,
  onComplete,
  onCancel,
  gracePeriodDaysRemaining,
  currentStep: externalStep,
  forceFlow,
  showRecoveryCodes,
  testID,
}: MFAEnrollmentWizardPropsExtended) {
  const effectivePaths = (allowedPaths ?? MOBILE_ALLOWED_PATHS).filter((p) =>
    MOBILE_ALLOWED_PATHS.includes(p),
  );

  const [internalStep, setInternalStep] = useState<MFAEnrollmentStep>(
    forcedPath ? "setup" : "method-select",
  );
  const [selectedPath, setSelectedPath] = useState<
    MFAEnrollmentPath | undefined
  >(forcedPath);

  // API + form state
  const [enrollStartPayload, setEnrollStartPayload] =
    useState<MfaEnrollStartPayload | null>(null);
  const [codeInput, setCodeInput] = useState("");
  const [recoveryCodes, setRecoveryCodes] = useState<string[] | null>(null);
  const [recoveryCodesAcknowledged, setRecoveryCodesAcknowledged] =
    useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<MfaApiError | null>(null);
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);

  // SMS resend cooldown (30s — spec §8.4)
  const [resendSeconds, setResendSeconds] = useState(0);
  const resendIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Verify input ref for auto-focus
  const codeInputRef = useRef<TextInput | null>(null);

  const currentStep = externalStep ?? internalStep;

  const visibleSteps: MFAEnrollmentStep[] = forcedPath
    ? MOBILE_STEP_ORDER.filter((s) => s !== "method-select")
    : MOBILE_STEP_ORDER;

  const currentIndex = visibleSteps.indexOf(currentStep);

  // ── Resend cooldown management ──────────────────────────────────────────────

  const startResendCooldown = useCallback(() => {
    setResendSeconds(30);
    if (resendIntervalRef.current) clearInterval(resendIntervalRef.current);
    resendIntervalRef.current = setInterval(() => {
      setResendSeconds((s) => {
        if (s <= 1) {
          if (resendIntervalRef.current) {
            clearInterval(resendIntervalRef.current);
            resendIntervalRef.current = null;
          }
          return 0;
        }
        return s - 1;
      });
    }, 1000);
  }, []);

  useEffect(() => {
    return () => {
      if (resendIntervalRef.current) clearInterval(resendIntervalRef.current);
    };
  }, []);

  // ── Copy feedback timer ─────────────────────────────────────────────────────

  const flashCopyFeedback = useCallback((msg: string) => {
    setCopyFeedback(msg);
    setTimeout(() => setCopyFeedback(null), 2000);
  }, []);

  // ── Enroll-start (STEP 3) ───────────────────────────────────────────────────

  const handleStartEnrollment = useCallback(
    async (path: MFAEnrollmentPath) => {
      setIsLoading(true);
      setError(null);
      try {
        const payload = await mfaEnrollStart(path);
        setEnrollStartPayload(payload);
        if (path === "sms") {
          startResendCooldown();
        }
      } catch (e) {
        const apiError =
          e instanceof MfaApiError
            ? e
            : new MfaApiError("Network error", null, 0);
        setError(apiError);
        // Haptic: error for failures, none for 503 warning
        const resolved = resolveError(apiError, path);
        if (!resolved.isWarning) hapticError();
      } finally {
        setIsLoading(false);
      }
    },
    [startResendCooldown],
  );

  // ── Path selection (auto-advances + fires enroll-start) ─────────────────────

  function handleSelectPath(path: MFAEnrollmentPath) {
    setSelectedPath(path);
    setInternalStep("setup");
    setEnrollStartPayload(null);
    setError(null);
    setCodeInput("");
    void handleStartEnrollment(path);
  }

  // ── Resend (re-calls enroll-start — design §D.1) ────────────────────────────

  const handleResend = useCallback(() => {
    if (!selectedPath || resendSeconds > 0) return;
    setError(null);
    setCodeInput("");
    void handleStartEnrollment(selectedPath);
  }, [selectedPath, resendSeconds, handleStartEnrollment]);

  // ── Verify (enroll-confirm — STEP 3) ────────────────────────────────────────

  async function handleVerify() {
    if (!selectedPath || codeInput.length !== 6 || isLoading) return;
    setIsLoading(true);
    setError(null);
    try {
      await mfaEnrollConfirm(selectedPath, codeInput);
      hapticSuccess();

      // Fetch recovery codes if this is first enrollment
      if (showRecoveryCodes) {
        try {
          const result = await mfaGenerateRecoveryCodes();
          setRecoveryCodes(result.codes);
        } catch {
          // Recovery codes fetch failed — still advance; codes are non-blocking
          setRecoveryCodes(null);
        }
      }

      setInternalStep("complete");

      // If no recovery-codes gate, fire onComplete immediately (spec §8.5)
      if (!showRecoveryCodes) {
        onComplete(selectedPath);
      }
    } catch (e) {
      const apiError =
        e instanceof MfaApiError
          ? e
          : new MfaApiError("Network error", null, 0);
      setError(apiError);
      const resolved = resolveError(apiError, selectedPath);
      if (!resolved.isWarning) hapticError();
    } finally {
      setIsLoading(false);
    }
  }

  // ── Finish (recovery-codes acknowledgment gate) ─────────────────────────────

  function handleFinish() {
    if (selectedPath) onComplete(selectedPath);
  }

  // ── Continue from setup → verify ────────────────────────────────────────────

  function handleNext() {
    if (currentStep === "setup") {
      setInternalStep("verify");
      setError(null);
    } else if (currentStep === "verify") {
      void handleVerify();
    }
  }

  // ── Auto-focus code input on verify step ────────────────────────────────────

  useEffect(() => {
    if (currentStep === "verify" && codeInputRef.current) {
      const t = setTimeout(() => codeInputRef.current?.focus(), 200);
      return () => clearTimeout(t);
    }
  }, [currentStep]);

  // ── Resolved error for rendering ────────────────────────────────────────────

  const resolvedError = error ? resolveError(error, selectedPath) : null;
  const showTopError =
    resolvedError &&
    (resolvedError.placement === "top" ||
      resolvedError.placement === "warning-top");
  const showSetupSmsError =
    resolvedError && resolvedError.placement === "setup-sms";
  const showInlineError = resolvedError && resolvedError.placement === "inline";

  // Grouped secret for display + VoiceOver
  const groupedSecret = enrollStartPayload?.secret
    ? (enrollStartPayload.secret.match(/.{1,4}/g)?.join(" ") ?? "")
    : "";
  const secretVoiceOverLabel = enrollStartPayload?.secret
    ? `Secret key, grouped in fours: ${enrollStartPayload.secret.match(/.{1,4}/g)?.join(", ") ?? ""}`
    : "Secret key";

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <View
      testID={testID ?? "mfa-enrollment-wizard"}
      style={{ flex: 1, padding: spacing[6], gap: spacing[6] }}
    >
      {/* Force-flow warning banner (spec §8.7) */}
      {forceFlow && (
        <View
          accessibilityRole="alert"
          style={{
            backgroundColor: lightTheme.warning.bgMuted,
            borderWidth: 1,
            borderColor: colors.alert[200],
            borderRadius: radii.md,
            padding: spacing[3],
          }}
        >
          <Text
            allowFontScaling
            style={{
              fontSize: mobileFontSizes.body,
              lineHeight: mobileLineHeights.body,
              color: lightTheme.warning.textOnMuted,
            }}
          >
            Your organization requires MFA — enrollment is not optional.
          </Text>
        </View>
      )}

      {/* Grace period banner (preserved from skeleton) */}
      {gracePeriodDaysRemaining !== undefined && (
        <View
          accessibilityRole="alert"
          style={{
            borderRadius: radii.md,
            padding: spacing[3],
            backgroundColor:
              gracePeriodDaysRemaining === 0
                ? lightTheme.danger.bgMuted
                : gracePeriodDaysRemaining <= 3
                  ? lightTheme.warning.bgMuted
                  : lightTheme.brand.bgMuted,
          }}
        >
          <Text
            allowFontScaling
            style={{
              fontSize: mobileFontSizes.body,
              lineHeight: mobileLineHeights.body,
              color:
                gracePeriodDaysRemaining === 0
                  ? lightTheme.danger.textOnMuted
                  : gracePeriodDaysRemaining <= 3
                    ? lightTheme.warning.textOnMuted
                    : lightTheme.brand.textOnMuted,
            }}
          >
            {gracePeriodDaysRemaining === 0
              ? "MFA enrollment is required today."
              : `You have ${gracePeriodDaysRemaining} day${gracePeriodDaysRemaining === 1 ? "" : "s"} to complete MFA enrollment.`}
          </Text>
        </View>
      )}

      {/* Top-of-wizard blocking error / warning (STEP 4) */}
      {showTopError && resolvedError && (
        <View
          testID="wizard-error"
          accessibilityRole="alert"
          style={{
            borderRadius: radii.md,
            padding: spacing[3],
            borderWidth: 1,
            flexDirection: "row",
            gap: spacing[2],
            alignItems: "flex-start",
            backgroundColor: resolvedError.isWarning
              ? colors.alert[50]
              : colors.fault[50],
            borderColor: resolvedError.isWarning
              ? colors.alert[200]
              : colors.fault[200],
          }}
        >
          <ExclamationTriangleIcon
            color={
              resolvedError.isWarning ? colors.alert[800] : colors.fault[800]
            }
          />
          <Text
            allowFontScaling
            style={{
              flex: 1,
              fontSize: mobileFontSizes.body,
              lineHeight: mobileLineHeights.body,
              color: resolvedError.isWarning
                ? colors.alert[800]
                : colors.fault[800],
            }}
          >
            {resolvedError.copy}
          </Text>
          {/* 503 TOTP nudge button (spec §4) */}
          {resolvedError.isWarning && (
            <Pressable
              testID="sms-unavailable-totp-nudge"
              onPress={() => handleSelectPath("totp")}
              accessibilityRole="button"
              accessibilityLabel="Set up authenticator app"
              style={({ pressed }) => ({
                minHeight: touchTargets.mobile.sm,
                justifyContent: "center",
                paddingHorizontal: spacing[3],
                opacity: pressed ? 0.8 : 1,
              })}
            >
              <Text
                allowFontScaling
                style={{
                  fontSize: mobileFontSizes.body,
                  color: lightTheme.brand.textOnMuted,
                }}
              >
                Set up authenticator app
              </Text>
            </Pressable>
          )}
          {/* 502 retry button */}
          {!resolvedError.isWarning &&
            error?.code === "cognito_unavailable" && (
              <Pressable
                onPress={() => {
                  setError(null);
                  if (currentStep === "setup" && selectedPath) {
                    void handleStartEnrollment(selectedPath);
                  } else if (currentStep === "verify" && selectedPath) {
                    void handleVerify();
                  }
                }}
                accessibilityRole="button"
                accessibilityLabel="Try again"
                style={({ pressed }) => ({
                  minHeight: touchTargets.mobile.sm,
                  justifyContent: "center",
                  paddingHorizontal: spacing[3],
                  opacity: pressed ? 0.8 : 1,
                })}
              >
                <Text
                  allowFontScaling
                  style={{
                    fontSize: mobileFontSizes.body,
                    color: colors.fault[800],
                  }}
                >
                  Try again
                </Text>
              </Pressable>
            )}
        </View>
      )}

      {/* Step indicator (preserved from skeleton) */}
      <View
        style={{ flexDirection: "row", alignItems: "center", gap: spacing[2] }}
        accessibilityLabel="Enrollment steps"
      >
        {visibleSteps.map((step, index) => (
          <React.Fragment key={step}>
            <View
              style={{
                flexDirection: "row",
                alignItems: "center",
                gap: spacing[1],
              }}
              accessibilityLabel={MFA_STEP_LABELS[step]}
              accessibilityState={{ selected: step === currentStep }}
            >
              <View
                style={{
                  width: spacing[2],
                  height: spacing[2],
                  borderRadius: radii.full,
                  backgroundColor:
                    step === currentStep
                      ? colors.brand[600]
                      : index < currentIndex
                        ? colors.margin[600]
                        : colors.neutral[200],
                }}
              />
              <Text
                allowFontScaling
                style={{
                  fontSize: mobileFontSizes.caption,
                  lineHeight: mobileLineHeights.caption,
                  fontWeight:
                    step === currentStep
                      ? (String(fontWeights.medium) as "500")
                      : (String(fontWeights.regular) as "400"),
                  color:
                    step === currentStep
                      ? colors.brand[600]
                      : colors.neutral[400],
                }}
              >
                {MFA_STEP_LABELS[step]}
              </Text>
            </View>
            {index < visibleSteps.length - 1 && (
              <View
                style={{
                  width: spacing[4],
                  height: 1,
                  backgroundColor: colors.neutral[200],
                }}
              />
            )}
          </React.Fragment>
        ))}
      </View>

      {/* Step content */}
      <ScrollView
        style={{ flex: 1 }}
        contentContainerStyle={{ gap: spacing[4] }}
        keyboardShouldPersistTaps="handled"
      >
        {/* ── Step 1: Method chooser (spec §2.1) ─────────────────────────────── */}
        {currentStep === "method-select" && (
          <View style={{ gap: spacing[4] }}>
            <Text
              allowFontScaling
              style={{
                fontSize: mobileFontSizes.h2,
                lineHeight: mobileLineHeights.h2,
                fontWeight: String(fontWeights.medium) as "500",
                color: colors.neutral[900],
              }}
              accessibilityRole="header"
            >
              Choose authentication method
            </Text>
            {effectivePaths.map((path) => {
              const isSelected = selectedPath === path;
              return (
                <Pressable
                  key={path}
                  onPress={() => handleSelectPath(path)}
                  testID={`mfa-path-${path}`}
                  accessibilityRole="radio"
                  accessibilityState={{ checked: isSelected }}
                  accessibilityLabel={
                    path === "totp"
                      ? "Authenticator app, recommended"
                      : "Text message"
                  }
                  style={({ pressed }) => ({
                    minHeight: touchTargets.mobile.md,
                    padding: spacing[4],
                    borderRadius: radii.md,
                    borderWidth: 2,
                    borderColor: isSelected
                      ? colors.brand[600]
                      : colors.neutral[200],
                    backgroundColor: isSelected
                      ? colors.brand[50]
                      : "transparent",
                    opacity: pressed ? 0.8 : 1,
                    flexDirection: "row",
                    alignItems: "center",
                    gap: spacing[3],
                  })}
                >
                  {/* Leading icon circle */}
                  <View
                    style={{
                      width: 40,
                      height: 40,
                      borderRadius: radii.full,
                      backgroundColor: colors.brand[50],
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    {path === "totp" ? (
                      <ShieldCheckIcon color={colors.brand[600]} />
                    ) : (
                      <DevicePhoneMobileIcon color={colors.brand[600]} />
                    )}
                  </View>

                  {/* Label + description */}
                  <View style={{ flex: 1, gap: spacing[1] }}>
                    <View
                      style={{
                        flexDirection: "row",
                        alignItems: "center",
                        gap: spacing[2],
                      }}
                    >
                      <Text
                        allowFontScaling
                        style={{
                          fontSize: mobileFontSizes.bodyLg,
                          lineHeight: mobileLineHeights.bodyLg,
                          fontWeight: String(fontWeights.medium) as "500",
                          color: colors.neutral[900],
                        }}
                      >
                        {path === "totp" ? "Authenticator app" : "Text message"}
                      </Text>
                      {/* Recommended badge (TOTP only — text + green, never color alone) */}
                      {path === "totp" && (
                        <View
                          style={{
                            borderRadius: radii.full,
                            backgroundColor: colors.margin[50],
                            paddingHorizontal: spacing[2],
                            paddingVertical: spacing[1],
                          }}
                        >
                          <Text
                            allowFontScaling
                            style={{
                              fontSize: mobileFontSizes.caption,
                              lineHeight: mobileLineHeights.caption,
                              fontWeight: String(fontWeights.medium) as "500",
                              color: colors.margin[800],
                            }}
                          >
                            Recommended
                          </Text>
                        </View>
                      )}
                    </View>
                    <Text
                      allowFontScaling
                      style={{
                        fontSize: mobileFontSizes.caption,
                        lineHeight: mobileLineHeights.caption,
                        color: colors.neutral[600],
                      }}
                    >
                      {path === "totp"
                        ? "Use Google Authenticator, Authy, or 1Password."
                        : "Get a code by text message."}
                    </Text>
                  </View>
                </Pressable>
              );
            })}
          </View>
        )}

        {/* ── Step 2: Setup TOTP (spec §2.2 — manual secret, no QR) ──────────── */}
        {currentStep === "setup" && selectedPath === "totp" && (
          <View style={{ gap: spacing[4] }}>
            <Text
              allowFontScaling
              style={{
                fontSize: mobileFontSizes.h2,
                lineHeight: mobileLineHeights.h2,
                fontWeight: String(fontWeights.medium) as "500",
                color: colors.neutral[900],
              }}
              accessibilityRole="header"
            >
              Set up authenticator app
            </Text>

            {/* Instructions (3 ordered steps) */}
            <View style={{ gap: spacing[2] }}>
              {[
                "Install an authenticator app (Google Authenticator, Authy, or 1Password) if you don't have one.",
                "Open the app and choose Add account → Enter key manually.",
                "Enter the key below — it's grouped in fours to make it easier to type.",
              ].map((stepText, i) => (
                <View key={i} style={{ flexDirection: "row", gap: spacing[2] }}>
                  <View
                    style={{
                      width: 24,
                      height: 24,
                      borderRadius: radii.full,
                      backgroundColor: colors.brand[50],
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    <Text
                      allowFontScaling
                      style={{
                        fontSize: mobileFontSizes.caption,
                        fontWeight: String(fontWeights.medium) as "500",
                        color: colors.brand[800],
                        textAlign: "center",
                      }}
                    >
                      {i + 1}
                    </Text>
                  </View>
                  <Text
                    allowFontScaling
                    style={{
                      flex: 1,
                      fontSize: mobileFontSizes.body,
                      lineHeight: mobileLineHeights.body,
                      color: colors.neutral[800],
                    }}
                  >
                    {stepText}
                  </Text>
                </View>
              ))}
            </View>

            {/* Secret panel */}
            <View
              style={{
                backgroundColor: colors.neutral[100],
                borderRadius: radii.md,
                padding: spacing[4],
                borderWidth: 1,
                borderColor: colors.neutral[200],
                gap: spacing[2],
              }}
            >
              <Text
                allowFontScaling
                style={{
                  fontSize: mobileFontSizes.caption,
                  color: colors.neutral[600],
                }}
              >
                Your secret key
              </Text>
              <Text
                allowFontScaling
                testID="totp-secret"
                accessibilityLabel={secretVoiceOverLabel}
                selectable
                style={{
                  fontFamily: fonts.mono,
                  fontSize: mobileFontSizes.bodyLg,
                  fontWeight: String(fontWeights.medium) as "500",
                  color: colors.neutral[900],
                  letterSpacing: 2,
                }}
              >
                {isLoading && !enrollStartPayload
                  ? "Loading…"
                  : groupedSecret || "—"}
              </Text>

              {/* Copy key button (expo-clipboard — Rule 9.8 approved) */}
              <Pressable
                testID="totp-secret-copy"
                onPress={async () => {
                  if (!enrollStartPayload?.secret) return;
                  const ok = await copyToClipboard(enrollStartPayload.secret);
                  if (ok) {
                    hapticSuccess();
                    flashCopyFeedback("Copied ✓");
                  }
                }}
                accessibilityRole="button"
                accessibilityLabel="Copy secret key"
                disabled={!enrollStartPayload}
                style={({ pressed }) => ({
                  minHeight: touchTargets.mobile.md,
                  borderRadius: radii.md,
                  backgroundColor: colors.brand[600],
                  paddingHorizontal: spacing[4],
                  paddingVertical: spacing[3],
                  alignItems: "center",
                  justifyContent: "center",
                  opacity: pressed ? 0.8 : 1,
                })}
              >
                <Text
                  allowFontScaling
                  style={{
                    color: lightTheme.brand.text,
                    fontSize: mobileFontSizes.bodyLg,
                    fontWeight: String(fontWeights.medium) as "500",
                  }}
                >
                  {copyFeedback ?? "Copy key"}
                </Text>
              </Pressable>

              {/* Secondary: Copy setup link (otpauth URI) */}
              <Pressable
                testID="totp-uri-copy"
                onPress={async () => {
                  if (!enrollStartPayload?.qr_code_uri) return;
                  const ok = await copyToClipboard(
                    enrollStartPayload.qr_code_uri,
                  );
                  if (ok) {
                    hapticSuccess();
                    flashCopyFeedback("Link copied ✓");
                  }
                }}
                accessibilityRole="button"
                accessibilityLabel="Copy setup link for authenticator app"
                disabled={!enrollStartPayload?.qr_code_uri}
                style={({ pressed }) => ({
                  minHeight: touchTargets.mobile.sm,
                  alignItems: "center",
                  justifyContent: "center",
                  opacity: pressed ? 0.8 : 1,
                })}
              >
                <Text
                  allowFontScaling
                  style={{
                    fontSize: mobileFontSizes.caption,
                    color: colors.brand[600],
                  }}
                >
                  {copyFeedback === "Link copied ✓"
                    ? "Link copied ✓"
                    : "Copy setup link instead"}
                </Text>
              </Pressable>
            </View>
          </View>
        )}

        {/* ── Step 2: Setup SMS (spec §2.3 — masked destination + resend) ────── */}
        {currentStep === "setup" && selectedPath === "sms" && (
          <View style={{ gap: spacing[4] }}>
            <Text
              allowFontScaling
              style={{
                fontSize: mobileFontSizes.h2,
                lineHeight: mobileLineHeights.h2,
                fontWeight: String(fontWeights.medium) as "500",
                color: colors.neutral[900],
              }}
              accessibilityRole="header"
            >
              Verify your phone number
            </Text>

            {/* Setup-SMS blocking error (phone_number_required / invalid) */}
            {showSetupSmsError && resolvedError && (
              <View
                testID="wizard-error"
                accessibilityRole="alert"
                style={{
                  borderRadius: radii.md,
                  padding: spacing[3],
                  borderWidth: 1,
                  flexDirection: "row",
                  gap: spacing[2],
                  alignItems: "flex-start",
                  backgroundColor: colors.fault[50],
                  borderColor: colors.fault[200],
                }}
              >
                <ExclamationTriangleIcon color={colors.fault[800]} />
                <Text
                  allowFontScaling
                  style={{
                    flex: 1,
                    fontSize: mobileFontSizes.body,
                    lineHeight: mobileLineHeights.body,
                    color: colors.fault[800],
                  }}
                >
                  {resolvedError.copy}
                </Text>
              </View>
            )}

            {/* Masked destination readout */}
            <View
              style={{
                backgroundColor: colors.neutral[100],
                borderRadius: radii.md,
                padding: spacing[4],
                borderWidth: 1,
                borderColor: colors.neutral[200],
                gap: spacing[2],
              }}
            >
              <Text
                allowFontScaling
                style={{
                  fontSize: mobileFontSizes.caption,
                  color: colors.neutral[600],
                }}
              >
                Code sent to
              </Text>
              <Text
                allowFontScaling
                testID="sms-destination"
                selectable
                style={{
                  fontFamily: fonts.mono,
                  fontSize: mobileFontSizes.bodyLg,
                  fontWeight: String(fontWeights.medium) as "500",
                  color: colors.neutral[900],
                }}
              >
                {isLoading && !enrollStartPayload
                  ? "Loading…"
                  : (enrollStartPayload?.destination_masked ?? "—")}
              </Text>
            </View>

            {/* Resend affordance with 30s cooldown */}
            <Pressable
              testID="sms-resend"
              onPress={handleResend}
              disabled={resendSeconds > 0 || isLoading}
              accessibilityRole="button"
              accessibilityLabel={
                resendSeconds > 0
                  ? `Resend code in ${resendSeconds} seconds`
                  : "Resend verification code"
              }
              accessibilityState={{ disabled: resendSeconds > 0 }}
              style={({ pressed }) => ({
                minHeight: touchTargets.mobile.sm,
                alignItems: "center",
                opacity: pressed ? 0.8 : 1,
              })}
            >
              <Text
                allowFontScaling
                style={{
                  fontSize: mobileFontSizes.body,
                  color:
                    resendSeconds > 0 ? colors.neutral[400] : colors.brand[600],
                }}
              >
                {resendSeconds > 0
                  ? `Resend code in ${resendSeconds}s`
                  : "Resend code"}
              </Text>
            </Pressable>
          </View>
        )}

        {/* ── Step 3: Verify (spec §2.4 — 6-digit input) ─────────────────────── */}
        {currentStep === "verify" && selectedPath && (
          <View style={{ gap: spacing[4] }}>
            <Text
              allowFontScaling
              style={{
                fontSize: mobileFontSizes.h2,
                lineHeight: mobileLineHeights.h2,
                fontWeight: String(fontWeights.medium) as "500",
                color: colors.neutral[900],
              }}
              accessibilityRole="header"
            >
              {selectedPath === "totp"
                ? "Enter the code from your authenticator app"
                : "Enter the code we texted you"}
            </Text>

            {/* 6-digit input (mirrors MfaChallengeStep idiom) */}
            <TextInput
              ref={codeInputRef}
              testID="mfa-code-input"
              accessibilityLabel="6-digit verification code"
              accessibilityValue={{ text: `${codeInput.length} of 6 digits` }}
              keyboardType="number-pad"
              maxLength={6}
              value={codeInput}
              onChangeText={(t) => {
                setCodeInput(t.replace(/\D/g, ""));
                if (error) setError(null);
              }}
              placeholder="000000"
              placeholderTextColor={colors.neutral[400]}
              editable={!isLoading}
              textContentType="oneTimeCode"
              style={{
                borderWidth: 1,
                borderColor: showInlineError
                  ? colors.fault[400]
                  : colors.neutral[200],
                borderRadius: radii.md,
                paddingHorizontal: spacing[4],
                paddingVertical: spacing[3],
                fontSize: mobileFontSizes.h2,
                fontWeight: String(fontWeights.medium) as "500",
                color: colors.neutral[900],
                fontFamily: fonts.mono,
                textAlign: "center",
                letterSpacing: 4,
                minHeight: touchTargets.mobile.md,
              }}
            />

            {/* Inline error (spec §4) */}
            {showInlineError && resolvedError && (
              <Text
                allowFontScaling
                testID="mfa-code-error"
                accessibilityRole="alert"
                style={{
                  fontSize: mobileFontSizes.caption,
                  lineHeight: mobileLineHeights.caption,
                  color: colors.fault[800],
                }}
              >
                {resolvedError.copy}
              </Text>
            )}

            {/* SMS resend below error (spec §2.4) */}
            {selectedPath === "sms" && (
              <Pressable
                testID="sms-resend"
                onPress={handleResend}
                disabled={resendSeconds > 0 || isLoading}
                accessibilityRole="button"
                accessibilityLabel={
                  resendSeconds > 0
                    ? `Resend code in ${resendSeconds} seconds`
                    : "Resend verification code"
                }
                accessibilityState={{ disabled: resendSeconds > 0 }}
                style={({ pressed }) => ({
                  minHeight: touchTargets.mobile.sm,
                  alignItems: "center",
                  opacity: pressed ? 0.8 : 1,
                })}
              >
                <Text
                  allowFontScaling
                  style={{
                    fontSize: mobileFontSizes.body,
                    color:
                      resendSeconds > 0
                        ? colors.neutral[400]
                        : colors.brand[600],
                  }}
                >
                  {resendSeconds > 0
                    ? `Resend code in ${resendSeconds}s`
                    : "Resend code"}
                </Text>
              </Pressable>
            )}

            {/* TOTP restart setup link (spec §2.4) */}
            {selectedPath === "totp" && (
              <Pressable
                testID="totp-restart-setup"
                onPress={() => handleSelectPath("totp")}
                accessibilityRole="button"
                accessibilityLabel="Restart authenticator setup"
                style={({ pressed }) => ({
                  minHeight: touchTargets.mobile.sm,
                  alignItems: "center",
                  opacity: pressed ? 0.8 : 1,
                })}
              >
                <Text
                  allowFontScaling
                  style={{
                    fontSize: mobileFontSizes.body,
                    color: colors.brand[600],
                  }}
                >
                  Restart authenticator setup
                </Text>
              </Pressable>
            )}
          </View>
        )}

        {/* ── Step 4: Complete (+ recovery codes — spec §2.5) ────────────────── */}
        {currentStep === "complete" && selectedPath && (
          <View
            style={{
              flex: 1,
              alignItems: "center",
              justifyContent: "center",
              gap: spacing[4],
            }}
          >
            {/* Success icon */}
            <View
              style={{
                width: 48,
                height: 48,
                borderRadius: radii.full,
                backgroundColor: colors.margin[100],
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <CheckIcon color={colors.margin[600]} />
            </View>

            <Text
              allowFontScaling
              style={{
                fontSize: mobileFontSizes.h2,
                lineHeight: mobileLineHeights.h2,
                fontWeight: String(fontWeights.medium) as "500",
                color: colors.neutral[900],
              }}
              accessibilityRole="header"
            >
              MFA enabled
            </Text>
            <Text
              allowFontScaling
              style={{
                fontSize: mobileFontSizes.body,
                lineHeight: mobileLineHeights.body,
                color: colors.neutral[600],
                textAlign: "center",
              }}
            >
              Your account is now protected with{" "}
              {selectedPath === "totp" ? "Authenticator app" : "Text message"}.
            </Text>

            {/* Recovery codes block (only when showRecoveryCodes is true) */}
            {showRecoveryCodes && (
              <View style={{ gap: spacing[3], width: "100%" }}>
                <Text
                  allowFontScaling
                  style={{
                    fontSize: mobileFontSizes.body,
                    fontWeight: String(fontWeights.medium) as "500",
                    color: colors.neutral[900],
                  }}
                >
                  Save your recovery codes
                </Text>
                <Text
                  allowFontScaling
                  style={{
                    fontSize: mobileFontSizes.caption,
                    lineHeight: mobileLineHeights.caption,
                    color: colors.neutral[600],
                  }}
                >
                  Keep these somewhere safe. You can use them to sign in if you
                  lose access to your authenticator.
                </Text>

                {/* Codes panel */}
                <View
                  testID="recovery-codes-container"
                  style={{
                    backgroundColor: colors.neutral[100],
                    borderRadius: radii.md,
                    padding: spacing[4],
                    borderWidth: 1,
                    borderColor: colors.neutral[200],
                  }}
                >
                  <View
                    style={{
                      flexDirection: "row",
                      flexWrap: "wrap",
                      gap: spacing[2],
                    }}
                  >
                    {(recoveryCodes ?? []).map((code, i) => (
                      <View
                        key={i}
                        style={{
                          flexBasis: "48%",
                          backgroundColor: lightTheme.background.secondary,
                          borderRadius: radii.sm,
                          borderWidth: 1,
                          borderColor: colors.neutral[200],
                          padding: spacing[2],
                        }}
                      >
                        <Text
                          allowFontScaling
                          selectable
                          style={{
                            fontFamily: fonts.mono,
                            fontSize: mobileFontSizes.caption,
                            fontWeight: String(fontWeights.medium) as "500",
                            color: colors.neutral[900],
                            textAlign: "center",
                          }}
                        >
                          {code}
                        </Text>
                      </View>
                    ))}
                    {recoveryCodes === null && (
                      <Text
                        allowFontScaling
                        style={{
                          fontSize: mobileFontSizes.caption,
                          color: colors.neutral[600],
                        }}
                      >
                        Recovery codes unavailable.
                      </Text>
                    )}
                  </View>

                  {/* Copy all codes button */}
                  <Pressable
                    testID="copy-recovery-codes"
                    onPress={async () => {
                      if (!recoveryCodes) return;
                      const ok = await copyToClipboard(
                        recoveryCodes.join("\n"),
                      );
                      if (ok) {
                        hapticSuccess();
                        flashCopyFeedback("Copied ✓");
                      }
                    }}
                    accessibilityRole="button"
                    accessibilityLabel="Copy all recovery codes"
                    disabled={!recoveryCodes}
                    style={({ pressed }) => ({
                      marginTop: spacing[3],
                      minHeight: touchTargets.mobile.md,
                      borderRadius: radii.md,
                      backgroundColor: colors.brand[600],
                      alignItems: "center",
                      justifyContent: "center",
                      opacity: pressed ? 0.8 : 1,
                    })}
                  >
                    <Text
                      allowFontScaling
                      style={{
                        color: lightTheme.brand.text,
                        fontSize: mobileFontSizes.bodyLg,
                        fontWeight: String(fontWeights.medium) as "500",
                      }}
                    >
                      {copyFeedback ?? "Copy all codes"}
                    </Text>
                  </Pressable>
                </View>

                {/* Acknowledgment gate (checkbox) */}
                <Pressable
                  testID="recovery-codes-ack"
                  onPress={() => setRecoveryCodesAcknowledged((v) => !v)}
                  accessibilityRole="checkbox"
                  accessibilityState={{ checked: recoveryCodesAcknowledged }}
                  accessibilityLabel="I've saved my recovery codes in a safe place."
                  style={{
                    minHeight: touchTargets.mobile.sm,
                    flexDirection: "row",
                    alignItems: "center",
                    gap: spacing[2],
                  }}
                >
                  <View
                    style={{
                      width: 24,
                      height: 24,
                      borderWidth: 2,
                      borderColor: recoveryCodesAcknowledged
                        ? colors.brand[600]
                        : colors.neutral[400],
                      borderRadius: radii.sm,
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    {recoveryCodesAcknowledged && (
                      <CheckIcon size={16} color={colors.brand[600]} />
                    )}
                  </View>
                  <Text
                    allowFontScaling
                    style={{
                      fontSize: mobileFontSizes.body,
                      lineHeight: mobileLineHeights.body,
                      color: recoveryCodesAcknowledged
                        ? colors.neutral[800]
                        : colors.fault[800],
                    }}
                  >
                    {"I've saved my recovery codes in a safe place."}
                  </Text>
                </Pressable>

                {/* Finish button — disabled until acknowledged */}
                <Pressable
                  testID="mfa-wizard-finish"
                  onPress={handleFinish}
                  disabled={!recoveryCodesAcknowledged}
                  accessibilityRole="button"
                  accessibilityLabel="Finish MFA enrollment"
                  accessibilityState={{ disabled: !recoveryCodesAcknowledged }}
                  style={({ pressed }) => ({
                    minHeight: touchTargets.mobile.md,
                    borderRadius: radii.md,
                    backgroundColor: colors.brand[600],
                    alignItems: "center",
                    justifyContent: "center",
                    opacity: !recoveryCodesAcknowledged || pressed ? 0.5 : 1,
                  })}
                >
                  <Text
                    allowFontScaling
                    style={{
                      color: lightTheme.brand.text,
                      fontSize: mobileFontSizes.bodyLg,
                      fontWeight: String(fontWeights.medium) as "500",
                    }}
                  >
                    Finish
                  </Text>
                </Pressable>
              </View>
            )}
          </View>
        )}
      </ScrollView>

      {/* Footer (Cancel hidden when forceFlow — spec §8.7) */}
      {currentStep !== "complete" && (
        <View
          style={{
            flexDirection: "row",
            alignItems: "center",
            justifyContent: "space-between",
            paddingTop: spacing[4],
          }}
        >
          {/* Cancel — hidden in forceFlow mode */}
          {!forceFlow && (
            <Pressable
              onPress={onCancel}
              accessibilityRole="button"
              accessibilityLabel="Cancel MFA enrollment"
              style={({ pressed }) => ({
                minHeight: touchTargets.mobile.sm,
                justifyContent: "center",
                opacity: pressed ? 0.8 : 1,
              })}
            >
              <Text
                allowFontScaling
                style={{
                  fontSize: mobileFontSizes.body,
                  color: colors.neutral[400],
                }}
              >
                Cancel
              </Text>
            </Pressable>
          )}
          {forceFlow && <View />}

          {/* Continue / Verify — not on method-select (auto-advances) */}
          {currentStep !== "method-select" && (
            <Pressable
              onPress={handleNext}
              testID="mfa-wizard-next"
              accessibilityRole="button"
              accessibilityLabel={
                currentStep === "verify" ? "Verify" : "Continue"
              }
              disabled={
                currentStep === "setup"
                  ? !enrollStartPayload || isLoading
                  : currentStep === "verify"
                    ? codeInput.length !== 6 || isLoading
                    : isLoading
              }
              style={({ pressed }) => ({
                paddingHorizontal: spacing[4],
                paddingVertical: spacing[3],
                borderRadius: radii.md,
                backgroundColor: colors.brand[600],
                minHeight: touchTargets.mobile.md,
                alignItems: "center",
                justifyContent: "center",
                opacity: pressed ? 0.8 : 1,
              })}
            >
              <Text
                allowFontScaling
                style={{
                  color: lightTheme.brand.text,
                  fontSize: mobileFontSizes.bodyLg,
                  fontWeight: String(fontWeights.medium) as "500",
                }}
              >
                {currentStep === "verify"
                  ? isLoading
                    ? "Verifying…"
                    : "Verify"
                  : "Continue"}
              </Text>
            </Pressable>
          )}
        </View>
      )}
    </View>
  );
}
