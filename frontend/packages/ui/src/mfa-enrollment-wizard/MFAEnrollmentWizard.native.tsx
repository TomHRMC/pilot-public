/**
 * MFAEnrollmentWizard — Mobile (React Native) platform re-export
 *
 * Location: packages/ui/src/mfa-enrollment-wizard/MFAEnrollmentWizard.native.tsx
 *
 * Platform resolution: Metro resolves this .native.tsx file for mobile.
 * Webpack/vitest resolves MFAEnrollmentWizard.tsx for web.
 *
 * MFA-WIRE-1 Part C: added platform-resolved entry points so the barrel
 * exports the correct implementation per platform. The barrel itself
 * (index.ts) now exports from "./MFAEnrollmentWizard" instead of
 * "./web/MFAEnrollmentWizard" — no change to the public API surface.
 */
export { MFAEnrollmentWizard } from "./mobile/MFAEnrollmentWizard";
