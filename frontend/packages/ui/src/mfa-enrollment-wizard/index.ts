/**
 * MFA Enrollment Wizard — Public API barrel
 * Location: packages/ui/src/mfa-enrollment-wizard/index.ts
 *
 * FE-B1: Created skeleton. FE-B12: Fleshed out implementation + extended props.
 * ⚠️ INTERFACE LOCKED after FE-B12 ships — FE-B13 embeds this component.
 */

// Platform-resolved export (MFA-WIRE-1 Part C):
// Metro resolves MFAEnrollmentWizard.native.tsx → mobile wizard
// Webpack/vitest resolves MFAEnrollmentWizard.tsx → web wizard
export { MFAEnrollmentWizard } from "./MFAEnrollmentWizard";

// Type exports — FE-B1 originals (preserved exactly)
export type {
  MFAEnrollmentWizardProps,
  MFAEnrollmentPath,
  MFAEnrollmentStep,
} from "./types";

// Type exports — FE-B12 additive extensions
export type {
  MFAEnrollmentWizardPropsExtended,
  MFAWizardInternalStep,
  MfaEnrollStartPayload,
  MfaWizardState,
} from "./types";

export {
  MFA_PATH_LABELS,
  MFA_PATH_DESCRIPTIONS,
  MFA_STEP_LABELS,
  MFA_STEP_ORDER,
} from "./types";
