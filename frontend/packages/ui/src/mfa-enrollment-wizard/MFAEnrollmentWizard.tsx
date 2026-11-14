/**
 * MFAEnrollmentWizard — Web platform re-export
 *
 * Location: packages/ui/src/mfa-enrollment-wizard/MFAEnrollmentWizard.tsx
 *
 * Platform resolution: webpack/vitest resolves this .tsx file for web.
 * Metro resolves MFAEnrollmentWizard.native.tsx for mobile.
 *
 * MFA-WIRE-1 Part C: added platform-resolved entry points so the barrel
 * exports the correct implementation per platform. The barrel itself
 * (index.ts) now exports from "./MFAEnrollmentWizard" instead of
 * "./web/MFAEnrollmentWizard" — no change to the public API surface.
 */
export { MFAEnrollmentWizard } from "./web/MFAEnrollmentWizard";
