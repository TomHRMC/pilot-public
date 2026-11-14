/**
 * MFA Enrollment Wizard — Types
 * Location: packages/ui/src/mfa-enrollment-wizard/types.ts
 *
 * Props interface locked in FE-B1. FE-B12 fleshes out the actual wizard logic
 * and adds optional props (backward-compatible — no prop removal or renaming).
 *
 * ⚠️ INTERFACE LOCKED after FE-B12 ships — FE-B13 embeds this component.
 */

export type MFAEnrollmentPath =
  | "totp" // Authenticator app (TOTP) — QR code scan
  | "sms" // SMS one-time code to phone number
  | "email"; // Email one-time code to account email

export type MFAEnrollmentStep =
  | "method-select" // Choose totp / sms / email
  | "setup" // Method-specific setup (QR scan, phone entry, etc.)
  | "verify" // Enter the code to confirm enrollment
  | "complete"; // Enrollment confirmed; wizard closes

// ─── FE-B12 additive internal step types ─────────────────────────────────────

export type MFAWizardInternalStep =
  | "method-select"
  | "setup-totp"
  | "setup-sms"
  | "setup-email"
  | "verify-totp"
  | "verify-sms"
  | "verify-email"
  | "recovery-codes"
  | "complete";

export interface MfaEnrollStartPayload {
  method_type: MFAEnrollmentPath;
  qr_code_uri?: string;
  secret?: string;
  destination_masked?: string;
}

export interface MfaWizardState {
  internalStep: MFAWizardInternalStep;
  selectedPath: MFAEnrollmentPath | null;
  enrollStartPayload: MfaEnrollStartPayload | null;
  codeInput: string;
  enrolledMethodId: string | null;
  recoveryCodes: string[] | null;
  recoveryCodesAcknowledged: boolean;
  isLoading: boolean;
  error: string | null;
}

// ─── FE-B1 skeleton interface — preserved exactly ─────────────────────────────

export interface MFAEnrollmentWizardProps {
  /**
   * Enrollment path preselected (e.g., tenant policy requires TOTP).
   * If not provided, user sees method-select step first.
   */
  forcedPath?: MFAEnrollmentPath;
  /**
   * Allowed enrollment paths.
   * Default: all three paths allowed.
   */
  allowedPaths?: MFAEnrollmentPath[];
  /**
   * Called when enrollment completes successfully.
   */
  onComplete: (enrolledPath: MFAEnrollmentPath) => void;
  /**
   * Called when user cancels or closes the wizard.
   * Wizards rendered during forced-enrollment flows should not provide
   * an escape — in that case, do not render a Cancel button and pass
   * a no-op or redirect handler here.
   */
  onCancel: () => void;
  /**
   * Days remaining in MFA enrollment grace period.
   * When > 3, shows info banner.
   * When 1–3, shows amber alert banner.
   * When 0, shows red "Enrollment required today" banner.
   * When undefined, no grace period UI is shown.
   */
  gracePeriodDaysRemaining?: number;
  /**
   * User's current step (for external state management).
   * If not provided, wizard manages step state internally.
   */
  currentStep?: MFAEnrollmentStep;
  testID?: string;
}

// ─── FE-B12 additive extensions (all optional — no breaking changes) ──────────

export interface MFAEnrollmentWizardPropsExtended extends MFAEnrollmentWizardProps {
  /**
   * Force-flow mode: renders full-page without cancel affordance.
   * Used by the /settings/my-account/security/mfa/enroll force-flow route.
   */
  forceFlow?: boolean;
  /**
   * Whether to show the recovery codes step.
   * Auto-derived from recovery-codes/status endpoint if undefined.
   * Pass false explicitly when adding a 2nd/3rd method.
   */
  showRecoveryCodes?: boolean;
  /** Callback after recovery codes are acknowledged */
  onRecoveryCodesAcknowledged?: () => void;
  /** Pre-enrolled methods (shown as already enrolled in method-select step) */
  enrolledMethods?: MFAEnrollmentPath[];
}

// ─── Display metadata ─────────────────────────────────────────────────────────

/** Display labels per enrollment path */
export const MFA_PATH_LABELS: Record<MFAEnrollmentPath, string> = {
  totp: "Authenticator app",
  sms: "Text message (SMS)",
  email: "Email code",
};

export const MFA_PATH_DESCRIPTIONS: Record<MFAEnrollmentPath, string> = {
  totp: "Use an authenticator app like Google Authenticator or Authy.",
  sms: "Receive a 6-digit code via SMS to your phone.",
  email: "Receive a 6-digit code to your account email.",
};

/** Step labels for the step indicator */
export const MFA_STEP_LABELS: Record<MFAEnrollmentStep, string> = {
  "method-select": "Choose method",
  setup: "Set up",
  verify: "Verify",
  complete: "Done",
};

export const MFA_STEP_ORDER: MFAEnrollmentStep[] = [
  "method-select",
  "setup",
  "verify",
  "complete",
];
