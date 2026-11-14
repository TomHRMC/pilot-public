# Implementation Prompt: MFA-WIRE-1 — Mobile MFA Wizard Step Content UI Design Spec

**Mode**: Pilot Voice UI Designer (`pilot-voice-ui-designer`)
**Batch**: MFA-WIRE-1 (Part C prerequisite — this spec must be Tom-approved before the React Native Engineer prompt is authored; Architect Rule §1.5)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.0 row 6 + §2.3 MFA-WIRE-1 card
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-mfa-wire-1-design.md` v1.1 ✅ APPROVED 2026-08-16 — §C step 4 (this task), §D (endpoint contracts), §F.3 (error map), §G-Q1/Q4/Q6, §H (surfaces), §I (component manifest), DoD
**Estimated session**: 1–1.5 hours
**Platform**: Mobile only (`apps/mobile` — Expo SDK 54 / React Native)
**Spec output**: `dev-docs/architecture-design/batch-designs/batch-mfa-wire-1-mobile-ui-design-spec.md`

---

## ⚠️ MANDATORY STOP: Read These First

- **`.roo/rules-pilot-voice-ui-designer/glove-friendly-ui.md`** — full document; 44×44pt minimum targets, 12pt spacing, WCAG AAA 7:1 contrast, bold weights for critical data
- **`.roo/rules-pilot-voice-ui-designer/voice-feedback-patterns.md`** — error/haptic patterns (voice-specific sections are not in scope; the error-feedback and fallback patterns are)
- **The design doc** — read §D.1–D.4 (endpoint contracts), §F.3 (the error codes you are speccing copy for), §G-Q1 (access-token header — the wizard calls real endpoints now), **§G-Q4 (manual-secret TOTP — NO QR code this batch)**, §H, §I, DoD items 6–7

Critical rules for this batch:

- **Flesh in place, locked props** — the mobile `MFAEnrollmentWizard` skeleton at `packages/ui/src/mfa-enrollment-wizard/mobile/MFAEnrollmentWizard.tsx` keeps its file and its locked prop interface (FE-B12 export block). You are speccing **step internals only** — no prop changes, no new shared exports.
- **Manual-secret TOTP only — no QR image** (design §G-Q4). QR rendering is MOB-B11 (P2 polish, blocked on a Rule 9.8 native-dep approval for `react-native-qrcode-svg`). Your spec must make the manual-entry path excellent: copyable secret, `otpauth://` URI fallback, clear authenticator-app instructions.
- **No Remove on mobile this batch** (DoD 4 scopes method-card Remove to web only). The mobile screen keeps its existing read-only methods summary — do **not** spec a Remove affordance (it would be a dead end). If you judge removal worth surfacing, use the existing **mobile escalation** §16 pattern (direct to web dashboard) as an informational note — compose, never invent.
- **Rule 9.4 — zero placeholder strings, no "coming soon".** Email MFA is deferred (pool has TOTP+SMS only) — the method chooser shows exactly two options.
- **Glove-friendly sizing everywhere** — code inputs, copy buttons, resend links: ≥44×44pt targets, ≥12pt separation, WCAG AAA contrast. The TOTP secret and 6-digit codes are "critical numerical data" → bold/heavy weights (rules §3).
- **SMS disclosure is already on the screen** (MOB-B10, `testID="sms-disclosure"`, "Message and data rates may apply") — preserve it; do not respec.

---

## Pre-Work: Read These Source Files

```
frontend/packages/ui/src/mfa-enrollment-wizard/mobile/MFAEnrollmentWizard.tsx          ← why: the skeleton you are fleshing — handleNext() currently advances steps with zero API calls; understand its step machine
frontend/packages/ui/src/mfa-enrollment-wizard/types.ts                                ← why: locked props + MFAEnrollmentPath + step enums (MFA_STEP_ORDER, MFA_PATH_LABELS you will constrain to totp/sms)
frontend/packages/ui/src/mfa-enrollment-wizard/web/MFAEnrollmentWizard.tsx             ← why: the web variant is the reference implementation — its step content/copy is the baseline you adapt for mobile (not copy blindly: mobile has no QR and different targets)
frontend/apps/mobile/app/(tabs)/(home)/settings/my-account/security/mfa.tsx            ← why: the host screen (MOB-B10) — methods summary, Add button, wizard container, SMS disclosure
frontend/apps/mobile/app/(tabs)/(home)/settings/my-account/security.tsx                ← why: upstream nav card with method count — unchanged, stay consistent
frontend/apps/mobile/features/login/components/MfaChallengeStep.tsx                    ← why: mobile login challenge (FE-B2) — 6-digit number-pad input + error haptics already established; compose the same input idiom in the wizard verify step
frontend/apps/mobile/features/login/components/MfaEnrollmentRequiredGate.tsx           ← why: force-enrollment gate — tone/button reference for the forceFlow variant
```

---

## Background / Context

MFA-WIRE-1 wires the mocked MFA enrollment flow to real Cognito. Step 0 + Part A are complete; the mobile wizard skeleton now needs production step content. Backend contract highlights for your copy decisions:

- **TOTP enroll-start** returns `{ method_type, qr_code_uri, secret }` — mobile renders the **`secret`** (grouped, copyable) + the `qr_code_uri` (an `otpauth://` string) as a secondary "copy link" fallback. No QR image.
- **SMS enroll-start** returns `{ method_type, destination_masked }` — show the masked destination ("Code sent to •••0001") with a **Resend** affordance (re-calling enroll-start resends the code — design §D.1 re-enrollment row).
- **Verify** accepts a 6-digit code; errors: 400 `mfa_code_invalid` ("That code didn't match — try again"), 400 `mfa_code_expired` ("That code expired — resend a new one" + resend affordance).
- **503 `sms_delivery_not_configured`** on SMS enroll-start until the AWS Support case resolves (ADR-0015) — present as a dignified notice: "Text-message setup is temporarily unavailable — use an authenticator app." Never a silent failure, never a fake success.
- **502 `cognito_unavailable`** — "We couldn't reach the authentication service. Nothing was saved — try again."
- **401 `mfa_access_token_invalid`** — session stale → nudge re-sign-in.
- **Complete step** shows **recovery codes** when `showRecoveryCodes` is true (first enrollment) — these are one-time-view secrets: spec a copy/acknowledge pattern ("Save these somewhere safe" + explicit acknowledgment before finishing).
- The wizard will send the new `X-Cognito-Access-Token` header from the Amplify session (§G-Q1) — engineering detail, no design impact.

---

## What to Design

Spec the **step internals** of the mobile wizard, in step order (`MFA_STEP_ORDER`), for both the voluntary host screen and the `forceFlow` variant:

1. **Method chooser** — two large options only: "Authenticator app" (recommended badge is acceptable — state it if used) and "Text message". 44×44pt+ rows, icon + label + short description, 12pt separation.
2. **Setup — TOTP (manual secret)** — step-by-step authenticator instructions (install/open app → add account → enter key manually); the **secret displayed grouped** (e.g. 4-char groups) in bold/heavy weight on a high-contrast panel with a **Copy** button (44×44pt, success feedback on copy); secondary "Copy setup link" for the `otpauth://` URI; then advance to verify.
3. **Setup — SMS** — masked destination readout + Resend (with a cooldown/disabled treatment — spec duration, e.g. 30s) + the preserved SMS disclosure.
4. **Verify** — 6-digit `number-pad` input matching the established `MfaChallengeStep` idiom (large targets, error haptics on failure, inline error copy from the table above); paste/autofill-friendly (one-time-code autofill where the OS provides it — note it for the engineer).
5. **Complete** — success confirmation + recovery-codes block when applicable (copy affordance + acknowledgment gate before finishing).

Also spec:

- **Error presentation table** — every §F.3 code above: inline vs. blocking notice, exact copy, haptic pattern (compose the voice-feedback §3 vocabulary: success = one short vibration; failure/retry = two long).
- **503 SMS-unavailable path** on the chooser/setup-sms steps (copy above) — include the TOTP nudge.
- **Four data states** for the host screen's methods area (loading / error w/ retry / empty / populated) — the host screen itself is only lightly touched (its summary stays; `enrolled_methods` remains its data source — mobile keeps consuming `enrolled_methods`, NOT the new `methods[]` array, per design §D.4 backward-compat note).
- **`allowedPaths`-equivalent constraint on mobile** — if the skeleton's chooser derives from `MFA_PATH_LABELS`, spec the two-method constraint explicitly so no email option can render.

**Component manifest reconciliation** (Architect Rule §1.5.4): exactly one file — `packages/ui/src/mfa-enrollment-wizard/mobile/MFAEnrollmentWizard.tsx` (flesh in place). No new components, no new exports. Your manifest must reconcile with design §I — no orphans.

## Output Requirements

Write the spec to `dev-docs/architecture-design/batch-designs/batch-mfa-wire-1-mobile-ui-design-spec.md`. Include: surface overview (route, who sees it), per-step content + layout specs (targets in points, spacing, typography weights), token/color references from the mobile style constants (`@/constants/style-constants` — read it; no hex codes), the error/haptic table, state coverage, an **Accessibility Notes** subsection (VoiceOver labels, target sizes, contrast ratios — WCAG AAA per your rules), and the component manifest.

## Handoff Gate (Architect Rule §1.5.5)

After producing the spec, **STOP**. Do not implement code. The spec goes to Tom for approval; Part C (React Native Engineer) is authored only after Tom approves. State this explicitly at the end of the spec.
