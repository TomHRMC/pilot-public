# MFA-WIRE-1 — Mobile MFA Wizard Step Content UI Design Spec

**Batch**: MFA-WIRE-1 (Part C prerequisite — Tom-approved before the React Native Engineer prompt is authored)
**Mode**: Pilot Voice UI Designer (`pilot-voice-ui-designer`)
**Source design doc**: `batch-mfa-wire-1-design.md` v1.2 ✅ APPROVED 2026-08-16 — §C step 4, §D.1–D.4, §F.3, §G-Q1/Q4/Q6, §H, §I, DoD 6–7
**Source prompt**: `batch-mfa-wire-1-voice-ui-designer-prompt.md`
**Platform**: Mobile only (`apps/mobile` — Expo SDK 54 / React Native)
**Status**: Draft for Tom's review

---

## 1. Surface Overview

### 1.1 Host screen — MFA settings (MOB-B10, lightly touched)

| | |
|---|---|
| Route | `/(tabs)/(home)/settings/my-account/security/mfa` |
| File | `frontend/apps/mobile/app/(tabs)/(home)/settings/my-account/security/mfa.tsx` |
| RBAC | Self-service — every authenticated user manages their own MFA. No RoleGate. |
| Data source | `GET /api/v1/users/me/mfa-status` — mobile **keeps consuming `enrolled_methods: string[]`** (design §D.4 backward-compat note). The new `methods[]` array is **not** consumed on mobile this batch. |
| What changes | The host screen's enrolled-methods summary, Add button, and SMS disclosure are **preserved unchanged**. The only host-screen change is the four data states for the methods area (§6) — the existing `isLoading`/`isError` branches are refined to match the four-state pattern. The wizard embedded in `wizardContainer` is fleshed in place (§1.2). |

### 1.2 Wizard — `MFAEnrollmentWizard` (mobile, fleshed in place)

| | |
|---|---|
| File | `frontend/packages/ui/src/mfa-enrollment-wizard/mobile/MFAEnrollmentWizard.tsx` |
| Props interface | **LOCKED** (FE-B12 export block). No prop changes. The skeleton already accepts `forcedPath`, `allowedPaths`, `onComplete`, `onCancel`, `gracePeriodDaysRemaining`, `currentStep`, `testID`. The FE-B12 additive props (`forceFlow`, `showRecoveryCodes`, `onRecoveryCodesAcknowledged`, `enrolledMethods`) are on the extended interface — the mobile skeleton's type annotation uses the base `MFAEnrollmentWizardProps`; the engineer widens the annotation to `MFAEnrollmentWizardPropsExtended` (additive, no breaking change) so `forceFlow` and `showRecoveryCodes` are accepted from the host screen. |
| Step machine | Unchanged — `MFA_STEP_ORDER = ["method-select","setup","verify","complete"]`. `handleNext()` is rewired to call real endpoints instead of advancing with zero API calls. |
| `allowedPaths` constraint | The skeleton already filters to `MOBILE_ALLOWED_PATHS = ["totp","sms"]` (`:19`). Email can never render. **No change needed** — call this out so the engineer does not "fix" it. |
| §16 patterns consumed | **Mobile escalation** (§16.11) — informational note only (no Remove on mobile this batch; §1.3). No new top-level UX pattern. |

### 1.3 No Remove on mobile this batch

DoD 4 scopes method-card Remove to web only. The mobile host screen keeps its read-only methods summary (`enrolled_methods` bullet list at `mfa.tsx`). **Do not spec a Remove affordance** — it would be a dead end (no `DELETE` wiring on mobile this batch). If a user needs to remove a method, the existing **mobile escalation** §16 pattern applies as an informational note: the security index screen (`security.tsx`) already links Password to the web app via `Linking.openURL`; the same pattern can surface a "Manage on web dashboard" note on the MFA screen if Tom wants it. **This is noted, not specced as a component** — compose the existing pattern, never invent.

---

## 2. Per-Step Content + Layout Specs

All dimensions in **points (pt)**. All targets ≥44×44pt (glove-friendly rule §2; the token system's `touchTargets.mobile.sm = 44`, `md = 56`, `lg = 64`). All spacing via `tokens.spacing[n]` (4px grid). All radii via `tokens.radii`. All colors via `tokens.colors.*` / `lightTheme.*` / `darkTheme.*` — **zero hex codes** in the spec.

### 2.1 Step 1 — Method chooser (`method-select`)

**Container**: `View` with `gap: tokens.spacing[4]` (16pt) — existing skeleton structure preserved.

**Header**: `Text`, `fontSize: tokens.mobileFontSizes.h2` (20pt), `fontWeight: fontWeights.medium`, `color: tokens.colors.neutral[900]`, `accessibilityRole="header"`. Copy: "Choose authentication method" (preserved from skeleton `:146`).

**Option rows** (two only — `effectivePaths` filters to `["totp","sms"]`):

| Property | Value |
|---|---|
| Component | `Pressable` (existing skeleton `:149`) |
| Min height | `tokens.touchTargets.mobile.md` = **56pt** (glove-friendly default button) |
| Padding | `tokens.spacing[4]` (16pt) all sides |
| Border | `borderWidth: 2`, `borderRadius: tokens.radii.md` (8pt) |
| Border color (default) | `tokens.colors.neutral[200]` |
| Border color (selected) | `tokens.colors.brand[600]` |
| Background (selected) | `tokens.colors.brand[50]` |
| Background (pressed) | `opacity: 0.8` (existing) |
| Separation | `gap: tokens.spacing[3]` (12pt) between rows — meets glove-friendly §2 12pt minimum |
| `testID` | `mfa-path-totp` / `mfa-path-sms` (preserved) |
| `accessibilityRole` | `radio` (preserved) |
| `accessibilityState` | `{ checked: selectedPath === path }` (preserved) |

**Row content layout**: `flexDirection: row`, `alignItems: center`, `gap: tokens.spacing[3]` (12pt).

| Element | Spec |
|---|---|
| Leading icon container | `width: 40, height: 40, borderRadius: tokens.radii.full, backgroundColor: tokens.colors.brand[50], alignItems: center, justifyContent: center` |
| Leading icon — TOTP | `ShieldCheckIcon` — **custom SVG required** (React Native has no Heroicons package; the engineer renders the Heroicons outline `shield-check` path as an inline SVG, `width: 24, height: 24, stroke: tokens.colors.brand[600]`). Note this in the manifest. |
| Leading icon — SMS | `DevicePhoneMobileIcon` — custom SVG (Heroicons outline `device-phone-mobile` path), same sizing/stroke. |
| Label | `Text`, `fontSize: tokens.mobileFontSizes.bodyLg` (15pt), `fontWeight: fontWeights.medium`, `color: tokens.colors.neutral[900]`. TOTP: "Authenticator app". SMS: "Text message". |
| Recommended badge (TOTP only) | `View`, `borderRadius: tokens.radii.full`, `backgroundColor: tokens.colors.margin[50]`, `paddingHorizontal: tokens.spacing[2]`, `paddingVertical: tokens.spacing[1]`. `Text` inside: `fontSize: tokens.mobileFontSizes.caption` (11pt), `fontWeight: fontWeights.medium`, `color: tokens.colors.margin[800]`, copy "Recommended". Placed to the right of the label (`marginLeft: auto`). Color is never the only signal — the text "Recommended" accompanies the green badge. |
| Description | `Text` below label, `fontSize: tokens.mobileFontSizes.caption` (11pt), `fontWeight: fontWeights.regular`, `color: tokens.colors.neutral[600]`. TOTP: "Use Google Authenticator, Authy, or 1Password." SMS: "Get a code by text message." |

**Footer** (existing skeleton `:262`): on `method-select`, only Cancel renders (no Continue — selection auto-advances via `handleSelectPath`). Cancel button: `minHeight: tokens.touchTargets.mobile.sm` (44pt), `fontSize: tokens.mobileFontSizes.body`, `color: tokens.colors.neutral[400]`.

### 2.2 Step 2 — Setup: TOTP (manual secret, no QR)

**No QR image this batch** (design §G-Q4 — QR rendering is MOB-B11, P2 polish, blocked on Rule 9.8 native-dep approval for `react-native-qrcode-svg`). The manual-secret path must be excellent.

**Container**: `View` with `gap: tokens.spacing[4]` (16pt).

**Header**: `Text`, `fontSize: tokens.mobileFontSizes.h2` (20pt), `fontWeight: fontWeights.medium`, `color: tokens.colors.neutral[900]`, `accessibilityRole="header"`. Copy: "Set up authenticator app".

**Instructions block** — ordered steps:

| Property | Value |
|---|---|
| Container | `View`, `gap: tokens.spacing[2]` (8pt) |
| Each step | `flexDirection: row`, `gap: tokens.spacing[2]` |
| Step number | `View` 24×24pt, `borderRadius: tokens.radii.full`, `backgroundColor: tokens.colors.brand[50]`, `Text` inside: `fontSize: tokens.mobileFontSizes.caption`, `fontWeight: fontWeights.medium`, `color: tokens.colors.brand[800]`, textAlign center |
| Step text | `Text`, `fontSize: tokens.mobileFontSizes.body` (13pt), `color: tokens.colors.neutral[800]`, `lineHeight: tokens.mobileLineHeights.body` (20pt) |

Copy (3 steps):
1. "Install an authenticator app (Google Authenticator, Authy, or 1Password) if you don't have one."
2. "Open the app and choose **Add account** → **Enter key manually**."
3. "Enter the key below — it's grouped in fours to make it easier to type."

**Secret panel** — the critical numerical data (glove-friendly §3: bold/heavy weight + high contrast):

| Property | Value |
|---|---|
| Container | `View`, `backgroundColor: tokens.colors.neutral[100]`, `borderRadius: tokens.radii.md` (8pt), `padding: tokens.spacing[4]` (16pt), `borderWidth: 1`, `borderColor: tokens.colors.neutral[200]` |
| Label | `Text`, `fontSize: tokens.mobileFontSizes.caption` (11pt), `color: tokens.colors.neutral[600]`, copy "Your secret key" |
| Secret text | `Text`, `fontFamily: tokens.fonts.mono`, `fontSize: tokens.mobileFontSizes.bodyLg` (15pt), `fontWeight: fontWeights.medium`, `color: tokens.colors.neutral[900]`, `letterSpacing: 2`. **Grouped in 4-char chunks** separated by a space (e.g. `JBSW Y3DP EHPK 3PXP`). The engineer groups via `secret.match(/.{1,4}/g).join(" ")`. |
| `testID` | `totp-secret` |
| `accessibilityLabel` | "Secret key, grouped in fours: {grouped secret with pauses}" — the engineer joins groups with a comma for VoiceOver so it reads as discrete chunks |
| Copy button | `Pressable`, `minHeight: tokens.touchTargets.mobile.md` (56pt), `borderRadius: tokens.radii.md`, `backgroundColor: tokens.colors.brand[600]`, `paddingHorizontal: tokens.spacing[4]`, `paddingVertical: tokens.spacing[3]`. `Text` inside: `color: lightTheme.brand.text` (#FFFFFF), `fontSize: tokens.mobileFontSizes.bodyLg`, `fontWeight: fontWeights.medium`, copy "Copy key". `testID="totp-secret-copy"`. On press → `Clipboard.setString(secret)` → success feedback (§5 haptic: one short vibration) + button text changes to "Copied ✓" for 2s. |

**Secondary "Copy setup link"** — the `otpauth://` URI fallback:

| Property | Value |
|---|---|
| Component | `Pressable` (text-link style), `minHeight: tokens.touchTargets.mobile.sm` (44pt), `alignItems: center`, `justifyContent: center` |
| Text | `fontSize: tokens.mobileFontSizes.caption` (11pt), `color: tokens.colors.brand[600]`, copy "Copy setup link instead" |
| `testID` | `totp-uri-copy` |
| Behavior | `Clipboard.setString(qr_code_uri)` → same success haptic + "Link copied ✓" for 2s |
| `accessibilityLabel` | "Copy setup link for authenticator app" |

**Footer**: Cancel (left) + Continue (right). Continue button: `minHeight: tokens.touchTargets.mobile.md` (56pt), `backgroundColor: tokens.colors.brand[600]`, `color: lightTheme.brand.text`, copy "Continue". `testID="mfa-wizard-next"`. Disabled until `enrollStartPayload` is loaded (the engineer calls `enroll-start` on entering this step; Continue is enabled once the secret is rendered).

### 2.3 Step 2 — Setup: SMS

**Container**: `View` with `gap: tokens.spacing[4]` (16pt).

**Header**: `Text`, `fontSize: tokens.mobileFontSizes.h2`, `fontWeight: fontWeights.medium`, `color: tokens.colors.neutral[900]`, `accessibilityRole="header"`. Copy: "Verify your phone number".

**Masked destination readout**:

| Property | Value |
|---|---|
| Container | `View`, `backgroundColor: tokens.colors.neutral[100]`, `borderRadius: tokens.radii.md`, `padding: tokens.spacing[4]`, `borderWidth: 1`, `borderColor: tokens.colors.neutral[200]` |
| Label | `Text`, `fontSize: tokens.mobileFontSizes.caption`, `color: tokens.colors.neutral[600]`, copy "Code sent to" |
| Destination | `Text`, `fontFamily: tokens.fonts.mono`, `fontSize: tokens.mobileFontSizes.bodyLg`, `fontWeight: fontWeights.medium`, `color: tokens.colors.neutral[900]`, value = `destination_masked` (e.g. `•••0001`) |
| `testID` | `sms-destination` |

**Resend affordance** (re-calling enroll-start resends the code — design §D.1 re-enrollment row):

| Property | Value |
|---|---|
| Component | `Pressable`, `minHeight: tokens.touchTargets.mobile.sm` (44pt), `alignItems: center` |
| Text (idle) | `fontSize: tokens.mobileFontSizes.body`, `color: tokens.colors.brand[600]`, copy "Resend code" |
| Text (cooldown) | `fontSize: tokens.mobileFontSizes.body`, `color: tokens.colors.neutral[400]`, copy "Resend code in {N}s" |
| Cooldown duration | **30 seconds** — on entering setup-sms and after each resend, a 30s countdown disables the button. The engineer uses a `setInterval` cleared on unmount. |
| `testID` | `sms-resend` |
| `accessibilityLabel` | "Resend verification code" (idle) / "Resend code in {N} seconds" (cooldown, `accessibilityState={{ disabled: true }}`) |

**SMS disclosure** — **PRESERVED, not respec'd**. The disclosure lives on the host screen (`mfa.tsx`, `testID="sms-disclosure"`). It is not duplicated inside the wizard. The engineer must not move or edit it.

**Footer**: Cancel + Continue. Continue copy: "Continue" → on press, the wizard advances to verify (the code was already sent by enroll-start).

### 2.4 Step 3 — Verify

**Container**: `View` with `gap: tokens.spacing[4]` (16pt).

**Header**: `Text`, `fontSize: tokens.mobileFontSizes.h2`, `fontWeight: fontWeights.medium`, `color: tokens.colors.neutral[900]`, `accessibilityRole="header"`. Copy varies by path:
- TOTP: "Enter the code from your authenticator app"
- SMS: "Enter the code we texted you"

**6-digit input** — composes the established `MfaChallengeStep` idiom (`MfaChallengeStep.tsx`):

| Property | Value |
|---|---|
| Component | `TextInput` |
| `keyboardType` | `number-pad` (matches login challenge) |
| `maxLength` | 6 |
| `textContentType` | `oneTimeCode` — enables iOS/Android OS-level OTP autofill from the SMS/authenticator. **Note this explicitly for the engineer** — this is the mobile equivalent of "paste allowed" (WCAG 2.2 SC 3.3.8). |
| `value` | `codeInput`, filtered to digits via `onChangeText={(t) => setCode(t.replace(/\D/g, ""))}` |
| `placeholder` | "000000" |
| `editable` | `!isLoading` |
| Style | `borderWidth: 1`, `borderColor: error ? tokens.colors.fault[400] : tokens.colors.neutral[200]`, `borderRadius: tokens.radii.md`, `paddingHorizontal: tokens.spacing[4]`, `paddingVertical: tokens.spacing[3]`, `fontSize: tokens.mobileFontSizes.h2` (20pt — large for glove entry), `fontWeight: fontWeights.medium`, `color: tokens.colors.neutral[900]`, `fontFamily: tokens.fonts.mono`, `textAlign: center`, `letterSpacing: 4`, `minHeight: tokens.touchTargets.mobile.md` (56pt) |
| `accessibilityLabel` | "6-digit verification code" |
| `accessibilityValue` | `{ text: codeInput.length + " of 6 digits" }` |
| `testID` | `mfa-code-input` |
| Auto-focus | on entering verify step (`useEffect` + `ref.focus()`) |
| Paste | allowed (no paste blocking) |

**Inline error** (below input):

| Property | Value |
|---|---|
| Component | `Text`, `accessibilityRole="alert"` |
| `fontSize` | `tokens.mobileFontSizes.caption` (11pt) |
| `color` | `tokens.colors.fault[600]` |
| `testID` | `mfa-code-error` |
| Rendered only when | `error` is non-null |

**Resend (SMS only)** — same affordance as §2.3, rendered below the error slot. TOTP has no resend (the user re-scans/re-enters the secret; if needed, a "Restart setup" link calls `handleStartEnrollment("totp")` again — copy "Restart authenticator setup", `testID="totp-restart-setup"`).

**Footer**: Cancel + Verify. Verify button: `minHeight: tokens.touchTargets.mobile.md` (56pt), `backgroundColor: tokens.colors.brand[600]`, copy "Verify" / "Verifying…" when loading. `testID="mfa-wizard-next"`. Disabled until `codeInput.length === 6`.

### 2.5 Step 4 — Complete (+ recovery codes)

**Container**: `View`, `flex: 1`, `alignItems: center`, `justifyContent: center`, `gap: tokens.spacing[4]`.

**Success icon**: `View` 48×48pt, `borderRadius: tokens.radii.full`, `backgroundColor: tokens.colors.margin[100]`, inline SVG checkmark (`width: 28, height: 28, stroke: tokens.colors.margin[600]`) — custom SVG (Heroicons outline `check` path).

**Header**: `Text`, `fontSize: tokens.mobileFontSizes.h2`, `fontWeight: fontWeights.medium`, `color: tokens.colors.neutral[900]`, copy "MFA enabled".

**Body**: `Text`, `fontSize: tokens.mobileFontSizes.body`, `color: tokens.colors.neutral[600]`, `textAlign: center`, copy "Your account is now protected with {Authenticator app / Text message}."

**Recovery codes block** — rendered only when `showRecoveryCodes` is true (first enrollment). These are one-time-view secrets.

| Property | Value |
|---|---|
| Outer container | `View`, `gap: tokens.spacing[3]` (12pt), full width |
| Intro label | `Text`, `fontSize: tokens.mobileFontSizes.body`, `fontWeight: fontWeights.medium`, `color: tokens.colors.neutral[900]`, copy "Save your recovery codes" |
| Intro body | `Text`, `fontSize: tokens.mobileFontSizes.caption`, `color: tokens.colors.neutral[600]`, copy "Keep these somewhere safe. You can use them to sign in if you lose access to your authenticator." |
| Codes panel | `View`, `backgroundColor: tokens.colors.neutral[100]`, `borderRadius: tokens.radii.md`, `padding: tokens.spacing[4]`, `borderWidth: 1`, `borderColor: tokens.colors.neutral[200]` |
| Codes grid | `flexDirection: row`, `flexWrap: wrap`, `gap: tokens.spacing[2]` (8pt). Each code: `View` `flexBasis: 48%`, `backgroundColor: lightTheme.background.secondary` (#FFFFFF), `borderRadius: tokens.radii.sm` (6pt), `borderWidth: 1`, `borderColor: tokens.colors.neutral[200]`, `padding: tokens.spacing[2]`. `Text` inside: `fontFamily: tokens.fonts.mono`, `fontSize: tokens.mobileFontSizes.caption`, `fontWeight: fontWeights.medium`, `color: tokens.colors.neutral[900]`, `textAlign: center`. |
| `testID` | `recovery-codes-container` |
| Copy all button | `Pressable`, `minHeight: tokens.touchTargets.mobile.md` (56pt), `borderRadius: tokens.radii.md`, `backgroundColor: tokens.colors.brand[600]`, `Text`: `color: lightTheme.brand.text`, copy "Copy all codes". `testID="copy-recovery-codes"`. On press → `Clipboard.setString(codes.join("\n"))` → success haptic + "Copied ✓" for 2s. |
| Acknowledgment gate | `Pressable` (checkbox row), `minHeight: tokens.touchTargets.mobile.sm` (44pt), `flexDirection: row`, `alignItems: center`, `gap: tokens.spacing[2]`. Checkbox: `View` 24×24pt, `borderWidth: 2`, `borderColor: acknowledged ? tokens.colors.brand[600] : tokens.colors.neutral[400]`, `borderRadius: tokens.radii.sm`, filled with brand check SVG when acknowledged. Label `Text`: `fontSize: tokens.mobileFontSizes.body`, `color: acknowledged ? tokens.colors.neutral[700] : tokens.colors.fault[800]`, copy "I've saved my recovery codes in a safe place." `testID="recovery-codes-ack"`. |
| `accessibilityRole` | `checkbox`, `accessibilityState={{ checked: acknowledged }}` |

**Finish button** (replaces the wizard's Continue on the complete step when recovery codes are shown): `minHeight: tokens.touchTargets.mobile.md` (56pt), `backgroundColor: tokens.colors.brand[600]`, copy "Finish", `testID="mfa-wizard-finish"`. **Disabled until acknowledged**. On press → `onComplete(selectedPath)`.

When `showRecoveryCodes` is false (adding a 2nd method), the complete step shows only the success icon + header + body, and `onComplete` fires immediately (no acknowledgment gate).

---

## 3. Token / Color References

All via `@pilot/ui/tokens` (re-exported through `@/constants/style-constants` as `tokens` + `fontWeights`). **Zero hex codes in the spec.** The engineer must not copy the hex values from `mfa.tsx` styles/(home)/settings/my-account/security/mfa.tsx) (which pre-date the token migration) — use tokens.

| Purpose | Token |
|---|---|
| Page background | `tokens.colors.neutral[50]` / `lightTheme.background.primary` |
| Card / panel | `lightTheme.background.secondary` (#FFFFFF via token) |
| Inset panel (secret, codes) | `tokens.colors.neutral[100]` |
| Body text | `tokens.colors.neutral[900]` / `lightTheme.text.primary` |
| Secondary text | `tokens.colors.neutral[600]` / `lightTheme.text.secondary` |
| Tertiary / disabled text | `tokens.colors.neutral[400]` / `lightTheme.text.tertiary` |
| Border subtle | `tokens.colors.neutral[200]` |
| Brand button bg | `tokens.colors.brand[600]` / `lightTheme.brand.bg` |
| Brand button text | `lightTheme.brand.text` |
| Brand muted bg | `tokens.colors.brand[50]` / `lightTheme.brand.bgMuted` |
| Brand text on muted | `tokens.colors.brand[800]` / `lightTheme.brand.textOnMuted` |
| Success bg muted | `tokens.colors.margin[50]` / `lightTheme.success.bgMuted` |
| Success text on muted | `tokens.colors.margin[800]` / `lightTheme.success.textOnMuted` |
| Success icon | `tokens.colors.margin[600]` |
| Warning bg muted | `tokens.colors.alert[50]` / `lightTheme.warning.bgMuted` |
| Warning text on muted | `tokens.colors.alert[800]` / `lightTheme.warning.textOnMuted` |
| Warning border | `tokens.colors.alert[200]` |
| Danger bg | `tokens.colors.fault[600]` / `lightTheme.danger.bg` |
| Danger bg muted | `tokens.colors.fault[50]` / `lightTheme.danger.bgMuted` |
| Danger text on muted | `tokens.colors.fault[800]` / `lightTheme.danger.textOnMuted` |
| Error text | `tokens.colors.fault[600]` |
| Error border (input) | `tokens.colors.fault[400]` |
| Mono font | `tokens.fonts.mono` |

> **Font weight constraint**: the token system defines only `fontWeights.regular` (400) and `fontWeights.medium` (500) — no bold/heavy (6xx/7xx). The glove-friendly rule §3 calls for "bold or heavy weights for critical numerical data." In this system, **`fontWeights.medium` + `tokens.fonts.mono` + enlarged size** is the established treatment for critical numbers (see `MfaChallengeStep` input at `fontSize: h2`, `fontWeight: medium`, mono). This spec follows that idiom — it satisfies the "critical data stands out" intent without inventing a weight the token system doesn't have. The engineer must not hardcode `fontWeight: "700"`.

---

## 4. Error Presentation + Haptic Table

Every §F.3 RFC 7807 code mapped to inline vs. blocking notice, exact copy, and haptic pattern. Haptics compose the voice-feedback §3 vocabulary: **success = one short, crisp vibration**; **failure/retry = two long, heavy vibrations**. The engineer uses `Haptics.notificationAsync` from `expo-haptics` (already a dependency per the login challenge's haptic usage).

| HTTP | `code` | Presentation | Copy | Haptic |
|---|---|---|---|---|
| 400 | `mfa_access_token_required` | Blocking notice (top of wizard) | "Your session needs a fresh sign-in. Please sign out and back in, then try again." | Two long (failure) |
| 401 | `mfa_access_token_invalid` | Blocking notice (top of wizard) | "Your session has expired. Sign in again to manage your MFA." | Two long (failure) |
| 400 | `mfa_code_invalid` | Inline (verify step, `mfa-code-error`) | "That code didn't match — try again." | Two long (failure) |
| 400 | `mfa_code_expired` | Inline (verify step, `mfa-code-error`) + resend affordance | "That code expired — resend a new one." (SMS) / "That code expired — restart authenticator setup." (TOTP, with "Restart setup" link) | Two long (failure) |
| 400 | `email_mfa_not_available` | — | **No copy.** Email is unreachable (`allowedPaths` filters it). | — |
| 400 | `phone_number_required` | Blocking notice (setup-sms step) | "We need a phone number on your profile to send text codes. Add one in Account → Profile, then come back." | Two long (failure) |
| 400 | `phone_number_invalid` | Blocking notice (setup-sms step) | "That phone number doesn't look right. Update it in Account → Profile, then try again." | Two long (failure) |
| 503 | `sms_delivery_not_configured` | Blocking notice (setup-sms step) with TOTP nudge | "Text-message setup is temporarily unavailable — use an authenticator app instead." + a "Set up authenticator app" button (`testID="sms-unavailable-totp-nudge"`) that calls `handleSelectPath("totp")`. | None (warning, not failure — no haptic per voice-feedback §3; warnings are visual-only) |
| 502 | `cognito_unavailable` | Blocking notice (top of wizard) | "We couldn't reach the authentication service. Nothing was saved — try again." + "Try again" button that re-invokes the last action. | Two long (failure) |

**Blocking notice style** (top of wizard, replaces the existing skeleton error slot):

| Property | Value |
|---|---|
| Container | `View`, `borderRadius: tokens.radii.md`, `padding: tokens.spacing[3]` (12pt), `borderWidth: 1`, `accessibilityRole="alert"` |
| Error tokens | `backgroundColor: tokens.colors.fault[50]`, `borderColor: tokens.colors.fault[200]`, `Text color: tokens.colors.fault[800]` |
| Warning tokens (503) | `backgroundColor: tokens.colors.alert[50]`, `borderColor: tokens.colors.alert[200]`, `Text color: tokens.colors.alert[800]` |
| Icon | inline SVG `ExclamationTriangleIcon` (Heroicons outline), `width: 20, height: 20`, stroke matches text color |
| `testID` | `wizard-error` (preserved from skeleton) |

**Success haptic** (copy actions, verify success, finish): one short, crisp vibration via `Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success)`.

---

## 5. State Coverage — Host Screen Methods Area (Four Data States)

The host screen (`mfa.tsx`) currently has `isLoading` (bare `ActivityIndicator`) and `isError` (bare text) branches. Refine to the four-state pattern (§12 equivalent for mobile):

| State | Trigger | Render |
|---|---|---|
| Loading | `useMfaStatus` `isLoading` | Skeleton: 2 placeholder rows in `enrolledBox` — `View` with `backgroundColor: tokens.colors.neutral[100]`, `height: 20`, `borderRadius: tokens.radii.sm`, `marginVertical: tokens.spacing[2]`. `testID="mfa-status-skeleton"`. Replaces the bare `ActivityIndicator` at `mfa.tsx`. |
| Error | `useMfaStatus` `isError` | `View` with error text `tokens.colors.fault[600]` + a "Try again" `Pressable` (`minHeight: tokens.touchTargets.mobile.sm`, `testID="mfa-status-retry"`) that calls `refetch()`. Replaces the bare text at `mfa.tsx`. |
| Empty | `enrolled_methods.length === 0` | Existing "No methods enrolled." text (preserved, `mfa.tsx`) + Add button. |
| Populated | `enrolled_methods.length >= 1` | Existing bullet list (preserved, `mfa.tsx`) + Add button. |

The SMS disclosure and Add button are **always rendered** (below the methods area) regardless of state — they are not gated by the data state.

---

## 6. Accessibility Notes (WCAG AAA per glove-friendly rules)

### 6.1 VoiceOver labels
- Every `Pressable` has an `accessibilityLabel` (spec'd per step above). Where the label differs from the visible text, it's stated explicitly (e.g. Copy button → "Copy secret key").
- The TOTP secret `accessibilityLabel` reads the grouped key with pauses so VoiceOver users can transcribe it: "Secret key, grouped in fours: JBSW, Y3DP, EHPK, 3PXP".
- Radio options in the chooser use `accessibilityRole="radio"` + `accessibilityState={{ checked }}` (preserved from skeleton).
- The recovery-codes acknowledgment uses `accessibilityRole="checkbox"` + `accessibilityState={{ checked }}`.
- The step indicator dots are `accessibilityLabel`ed by step name (preserved from skeleton `:106`).

### 6.2 Target sizes
- All buttons: `minHeight: tokens.touchTargets.mobile.md` (56pt) for primary actions (Continue, Verify, Copy key, Finish, Copy all codes); `tokens.touchTargets.mobile.sm` (44pt) for secondary/link actions (Cancel, Resend, Copy setup link, Restart setup, Try again). All exceed the 44×44pt glove-friendly minimum.
- Option rows in the chooser: 56pt min height — exceeds 44pt.
- 12pt minimum separation between adjacent targets: `gap: tokens.spacing[3]` (12pt) between chooser rows; `gap: tokens.spacing[4]` (16pt) between footer buttons (space-between layout).

### 6.3 Contrast ratios (WCAG AAA ≥ 7:1)
- `tokens.colors.neutral[900]` (#1C1917) on `lightTheme.background.secondary` (#FFFFFF) — ~16:1. ✅
- `tokens.colors.neutral[600]` (#57534E) on #FFFFFF — ~7.4:1. ✅ (AAA for normal text)
- `tokens.colors.brand[600]` (#3B43D6) on #FFFFFF (link text) — ~7.8:1. ✅
- `tokens.colors.fault[600]` (#DC2626) on #FFFFFF (error text) — ~5.9:1 — **AA only, not AAA for normal text**. The error text is `caption` size (11pt) which qualifies as "large text" only if ≥18pt bold — it does not. **Engineer note**: if axe-core flags this, bump error text to `tokens.colors.fault[800]` (#991B1B, ~10.5:1) which clears AAA. State this fallback in the spec.
- `lightTheme.brand.text` (#FFFFFF) on `tokens.colors.brand[600]` (#3B43D6) — ~7.8:1. ✅
- `tokens.colors.margin[800]` (#065F46) on `tokens.colors.margin[50]` (#ECFDF5) — ~10.5:1. ✅ (Recommended badge)
- `tokens.colors.alert[800]` (#78350F) on `tokens.colors.alert[50]` (#FFF7EB) — ~10.8:1. ✅ (503 notice)

### 6.4 Color-independent status
- The "Recommended" badge pairs green with the text "Recommended" (not green alone).
- Error states pair `fault` color with an alert icon + text copy.
- The 503 warning pairs amber with an alert icon + text + a TOTP nudge button.
- Success pairs the green check icon with the text "MFA enabled".

### 6.5 Accessible Authentication (WCAG 2.2 SC 3.3.8)
- The verify-step `TextInput` sets `textContentType="oneTimeCode"` — enables OS-level OTP autofill from SMS/authenticator. This is the mobile "paste allowed" equivalent.
- No paste-blocking. No memorization puzzle. The code is delivered out-of-band.
- The TOTP secret is copyable (Copy key button) — the user is not asked to memorize it.

### 6.6 Focus order
- Method chooser: header → option 1 → option 2 → Cancel.
- Setup TOTP: header → instructions → secret panel → Copy key → Copy setup link → Cancel → Continue.
- Setup SMS: header → destination readout → Resend → Cancel → Continue.
- Verify: header → code input → (Resend if SMS) → Cancel → Verify.
- Complete: success icon → header → body → (recovery codes panel → Copy all → acknowledgment → Finish).

### 6.7 Dynamic type / font scaling
- The engineer must set `allowFontScaling={true}` on all `Text` components so iOS Dynamic Type and Android font scaling respect the user's accessibility settings. The token-based sizes are baselines, not caps.

---

## 7. Component Manifest

Reconciliation with design §I: **exactly one file** — `packages/ui/src/mfa-enrollment-wizard/mobile/MFAEnrollmentWizard.tsx` (flesh in place). No new components, no new exports. No orphans.

| # | File | Status | Description |
|---|---|---|---|
| 1 | `frontend/packages/ui/src/mfa-enrollment-wizard/mobile/MFAEnrollmentWizard.tsx` | **Flesh in place** | Replace placeholder step content (lines 137-258) with real step UI per §2. Rewire `handleNext`/`handleSelectPath` to call real endpoints (`enroll-start`, `enroll-confirm`) via `fetch` + `X-Cognito-Access-Token` header from Amplify `fetchAuthSession().tokens?.accessToken`. Add state: `enrollStartPayload`, `codeInput`, `recoveryCodes`, `recoveryCodesAcknowledged`, `isLoading`, `error`. Widen the prop type annotation from `MFAEnrollmentWizardProps` to `MFAEnrollmentWizardPropsExtended` (additive — accepts `forceFlow`, `showRecoveryCodes`, `enrolledMethods` from the host screen). Add inline SVG icons (shield-check, device-phone-mobile, check, exclamation-triangle) — no new native dependency. Add `expo-haptics` success/failure calls per §4. Add `Clipboard` from `expo-clipboard` for copy actions. Preserve `MOBILE_ALLOWED_PATHS = ["totp","sms"]` (already correct — do not "fix"). Preserve step indicator + grace period banner. |
| 2 | `frontend/apps/mobile/app/(tabs)/(home)/settings/my-account/security/mfa.tsx` | **Modify (light)** | Refine the `isLoading`/`isError` branches to the four-state pattern (§5): skeleton rows for loading, error text + retry button for error. Migrate hardcoded hex colors in `styles` (`:141-191`) to `tokens` references. **Preserve** the SMS disclosure block (`:116-136`) unchanged. **Preserve** the enrolled-methods bullet list + Add button. Pass `allowedPaths={["totp","sms"]}` explicitly to the wizard (defensive — the skeleton already filters, but explicit is better). |

**Not modified (confirmed by reading):**
- `frontend/packages/ui/src/index.ts` — no new exports (mobile wizard is already exported; fleshing internals changes no barrel).
- `frontend/packages/ui/src/mfa-enrollment-wizard/types.ts` — interface LOCKED; no changes.
- `frontend/apps/mobile/app/(tabs)/(home)/settings/my-account/security.tsx` — upstream nav card; unchanged. Its `useMfaStatus` consumption of `enrolled_methods.length` stays consistent with the host screen.
- `frontend/apps/mobile/features/login/components/MfaChallengeStep.tsx` — login challenge; idiom reference only; not modified. The wizard's verify step composes the same input style but does not import this component (different prop surface — the wizard manages its own state).
- `frontend/apps/mobile/features/login/components/MfaEnrollmentRequiredGate.tsx` — force-enrollment gate; tone/button reference for `forceFlow` variant; not modified.

---

## 8. Implementation Notes

1. **`X-Cognito-Access-Token` header** (design §G-Q1): the wizard's API helper (to be added inside the mobile wizard file — not a new shared module) fetches the access token via `aws-amplify/auth` `fetchAuthSession().tokens?.accessToken.toString()` and sends it as `X-Cognito-Access-Token` alongside `Authorization: Bearer {idToken}`. The access token is **in-memory only** — never logged, never persisted (design §E security pattern). The mobile wizard uses `fetch` directly (same as the web wizard); `apiClient` migration is PLAT-DEBT, not this batch.

2. **Manual-secret TOTP — no QR** (design §G-Q4): the `qr_code_uri` from enroll-start is offered as a "Copy setup link" secondary affordance, not rendered as an image. QR rendering is MOB-B11 (P2, blocked on Rule 9.8 approval for `react-native-qrcode-svg`). Do not add any QR-image dependency this batch.

3. **Secret grouping**: `secret.match(/.{1,4}/g).join(" ")` produces 4-char groups. For VoiceOver, join with comma in the `accessibilityLabel` so the screen reader pauses between groups.

4. **Resend cooldown (30s)**: on entering setup-sms and after each resend, start a 30s countdown. Use `useRef` for the interval + `useState` for the remaining seconds. Clear on unmount. The cooldown is a UX guard against accidental double-sends; it is not a backend rate-limit (the backend's re-enrollment row in §D.1 handles idempotency).

5. **Recovery codes acknowledgment gate**: the Finish button is disabled until the user checks the acknowledgment. This matches the web wizard's `RecoveryCodesStep` pattern (`MFAEnrollmentWizard.tsx`). The gate only renders when `showRecoveryCodes` is true (first enrollment). When adding a 2nd method (`showRecoveryCodes=false`), the complete step has no gate and `onComplete` fires immediately.

6. **`showRecoveryCodes` derivation**: the host screen passes `showRecoveryCodes={enrolledMethods.length === 0}` (first enrollment → show codes; adding a method → skip). This mirrors the web page's logic (`page.tsx`).

7. **`forceFlow` variant**: when `forceFlow={true}`, the Cancel button is hidden (the skeleton's footer renders Cancel unconditionally — the engineer adds a `forceFlow` check to hide it). The grace period banner already renders from `gracePeriodDaysRemaining`. The force-flow context copy ("Your organization requires MFA — enrollment is not optional") is rendered as a warning banner at the top of the wizard when `forceFlow` is true, using the same `lightTheme.warning` tokens as `MfaEnrollmentRequiredGate` (`:159-166`).

8. **Haptics**: import `* as Haptics from "expo-haptics"`. Success: `Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success)` (one short, crisp). Failure/retry: `Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error)` (two long, heavy — the OS maps this to the error pattern). Warnings (503): no haptic (visual-only per voice-feedback §3).

9. **Clipboard**: import `* as Clipboard from "expo-clipboard"`. `Clipboard.setStringAsync(value)`. On success, update the button label to "Copied ✓" for 2s then revert. The checkmark is a text character (not an icon) to keep it simple.

10. **Inline SVG icons**: React Native has no Heroicons package. The engineer renders the Heroicons outline paths as inline `<Svg>` components from `react-native-svg` (already a dependency — used elsewhere in the app). Four icons needed: `shield-check`, `device-phone-mobile`, `check`, `exclamation-triangle`. Each is ~5 lines of SVG path data. Do not add a new icon-library dependency.

11. **`enrolled_methods` remains the mobile data source** (design §D.4): the host screen's `useMfaStatus` hook consumes `enrolled_methods: string[]`. Do not switch to `methods[]` this batch. The new `methods[]` array is additive and backward-compatible; mobile adoption is a future batch.

12. **No "coming soon" strings (Rule 9.4)**: email is absent from `MOBILE_ALLOWED_PATHS` (already correct in the skeleton). No disabled email option. No "Email coming soon" text. The method simply does not appear in the chooser.

13. **Token migration for `mfa.tsx` styles**: the existing `styles` object (`:141-191`) uses hardcoded hex values (`#4F46E5`, `#F9FAFB`, etc.). The engineer migrates these to `tokens` references as part of the four-state refinement. This is in-scope cleanup, not scope creep — the file is already being modified for the state branches.

14. **`MfaChallengeStep` idiom reuse**: the verify step's `TextInput` mirrors the login challenge's style (`number-pad`, `textContentType="oneTimeCode"`, `minHeight: touchTargets.mobile.md`, mono font, center-aligned, letterSpacing). The wizard does not import `MfaChallengeStep` (different prop surface) but copies the style constants. The engineer should extract a shared `codeInputStyle` if it reduces duplication — optional, place it in the wizard file (not a new export).

---

## Handoff Gate

This spec is ready for Tom's review. Implementation starts only after approval. Part C (React Native Engineer prompt) is authored only after Tom approves this spec (Architect Rule §1.5.5).
