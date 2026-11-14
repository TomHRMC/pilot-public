# SIGNUP-C UI Design Spec — "Stay Informed" Screen (Signup Step 3 Redesign)

**Batch code**: SIGNUP-C
**Spec owner**: Pilot Web UI Designer
**Created**: 2026-07-31
**Status**: 🟡 Awaiting Tom approval — implementation starts only after approval
**Design doc**: `batch-signup-c-design.md` (§H Surface Mockup, §I Component Manifest)
**ADR**: ADR-0013 — Three-pathway SMS model; repurpose `CXXXXXX` as Pilot-sender platform notifications
**Compliance source**: `telnyx-10dlc-p4t-tenant-comms-campaign.md` §4/§5 — this screen's disclosure block IS the TCR consent screenshot
**React Engineer prompt**: `batch-signup-c-react-engr-prompt.md`

---

## 1. Surface Overview

| Field | Value |
|---|---|
| **Surface** | Signup wizard step 3 — reframed from "Verify your phone" → **"Stay Informed"** |
| **Route** | `/signup/phone` (route unchanged; step key in `WizardProgressBar` remains `"phone"`) |
| **Page file** | `apps/web/src/app/signup/phone/page.tsx` — page body renamed to `StayInformedStep` |
| **Layout shell** | `apps/web/src/app/signup/layout.tsx` — pre-auth shell, `max-w-lg` centered content, unchanged |
| **Who sees it** | Self-serve signup wizard users (GA path, post-legal-acceptance, pre-plan-selection). No RBAC gate — this is a pre-auth onboarding step. |
| **Purpose** | Pilot texts the **tenant owner** about account/billing/security/maintenance events (Pathway C — Pilot → owner platform notifications). This is **NOT** tenant→customer messaging (Pathway B, deferred to future per-tenant SMS-2 add-on). |
| **Phone requirement** | **Required** (Tom decision, `batch-signup-c-design.md` §G.5). The old `phone_skipped` path is removed. Phone is saved on `user.phone_number` for account/MFA reuse regardless of SMS consent. |
| **Consent default** | **UNCHECKED by default** (locked compliance decision, `batch-signup-c-design.md` §G.6). The reply-YES double-opt-in is the authoritative consent. |
| **Compliance role** | The disclosure block (`data-testid="signup-sms-consent-disclosure"`) renders the **TCR consent screenshot** for `CXXXXXX` campaign resubmission. Two screenshots required: unchecked-default and checked. See `telnyx-10dlc-p4t-tenant-comms-campaign.md` §5. |

### Screen states (state machine)

```
type StayInformedStep = "enter" | "confirm" | "confirmed";
```

| State | Trigger | What renders |
|---|---|---|
| `enter` | Initial mount | Phone field + consent checkbox + disclosure + Continue button |
| `confirm` | Consent checked + Continue clicked + POST consent + PUT step3 succeed | `DoubleOptinConfirmSubscreen` (waiting for YES reply) |
| `confirmed` | Polling detects `consent_status='opted_in'` (webhook YES received) | `DoubleOptinConfirmSubscreen` with success banner, auto-advances to `/signup/plan` after 1500ms |
| → `/signup/plan` | Consent **unchecked** + Continue clicked + PUT step3 succeed | Direct navigation (no confirmation sub-state) |
| → `/signup/plan` | "Skip for now → continue" clicked from `confirm` state | Direct navigation (phone saved, double-opt-in SMS already sent, webhook will process async YES) |
| → `enter` | "Use a different number" clicked from `confirm` state | Returns to entry form; phone field cleared; consent checkbox state retained |

---

## 2. Pixel Specs

All dimensions use Tailwind spacing scale. The content area is constrained by the layout shell's `max-w-lg` (512px) centered within `min-h-screen bg-neutral-50`.

### 2.1 Page root

| Element | Spec |
|---|---|
| Root container | `flex flex-col gap-8` (gap = 32px). Width = 512px (from layout `max-w-lg`). |
| `WizardProgressBar` | Reused unchanged, `currentStep="phone"`. Renders at top of root. |

### 2.2 Header section

| Element | Spec |
|---|---|
| Container | `flex flex-col gap-2` (gap = 8px) |
| H1 | `text-2xl font-bold text-neutral-900` — copy: **"Stay informed"** |
| Subtitle | `text-sm text-neutral-600` — copy: **"Add your mobile number so Pilot can text you about urgent account, billing, and security alerts."** |

### 2.3 Phone number field (required)

| Element | Spec |
|---|---|
| Field container | `flex flex-col gap-1` |
| Label | `text-sm font-medium text-neutral-700` — copy: **"Mobile number"** with required asterisk `text-fault-600` |
| Input | `type="tel"`, `inputMode="tel"`, `autoComplete="tel"`. `w-full rounded-lg border px-3 py-2.5 text-sm`. Default border: `border-neutral-300`. Placeholder: `+1 (555) 000-0000`. **Paste allowed** (no `onPaste` restriction — WCAG 2.2 SC 3.3.8). |
| Input — focus | `focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2 focus-visible:border-brand-600` |
| Input — error | `border-fault-600 bg-fault-50` (replaces default border) |
| Helper text | `text-xs text-neutral-500 mt-1` — copy: **"Required for your account — we'll also use this for optional alerts if you opt in below."** |
| Error text | `text-xs text-fault-600 mt-1` with leading `ExclamationCircleIcon` (outline, `w-4 h-4`, `text-fault-600`) + `role="alert"` + `aria-describedby="field-phone-number"`. Copy: **"Enter a valid mobile number (e.g., +1 555 123 4567)."** |
| `data-testid` | `field-phone-number` (input), `field-phone-number-error` (error text) |

### 2.4 Consent checkbox (unchecked by default)

| Element | Spec |
|---|---|
| Container | `flex items-start gap-3` (gap = 12px) |
| Checkbox | `type="checkbox"`, `h-5 w-5` (20px), `rounded`, `accent-brand-600`, `mt-0.5`. **`defaultChecked={false}`** — locked compliance decision. |
| Checkbox — focus | `focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2` |
| Label | `text-sm font-medium text-neutral-900 cursor-pointer` — copy: **"Yes — text me about urgent account, billing, and security alerts so I'm never caught off guard."** (benefit-forward; improves on design §H draft) |
| Label ↔ checkbox | Associated via `<label htmlFor="signup-sms-consent-checkbox">`. Full label text is the click target (well over 24×24px — see §10 Accessibility). |
| `data-testid` | `signup-sms-consent-checkbox` (checkbox), `signup-sms-consent-label` (label) |

### 2.5 SmsConsentDisclosure block (NEW component)

This block IS the TCR consent screenshot content. It is **always visible** beneath the checkbox (in both checked and unchecked states) — per `telnyx-10dlc-p4t-tenant-comms-campaign.md` §5, two screenshots are required (checked + unchecked default), so the disclosure must render in both.

| Element | Spec |
|---|---|
| Container | `rounded-lg border border-neutral-200 bg-neutral-50 p-4 flex gap-3 items-start`. `data-testid="signup-sms-consent-disclosure"`. |
| Leading icon | `InformationCircleIcon` (Heroicons 2.0, **outline** variant, `w-5 h-5`, `text-neutral-500`, `aria-hidden="true"`, `flex-shrink-0`) |
| Text block | `text-xs leading-relaxed text-neutral-700 flex-1` |
| Privacy Policy link | Inline within text. `text-brand-600 hover:text-brand-800 underline focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-1 rounded`. `href="https://www.pilotfortrades.com/legal/privacy"`, `target="_blank"`, `rel="noopener noreferrer"`. Trailing icon: `ArrowTopRightOnSquareIcon` (outline, `w-3 h-3` inline, `aria-hidden="true"`). |

**Full disclosure text** (single paragraph, all required 10DLC CTA language — verbatim compliance copy):

> Account alerts from Pilot for Trades. You'll receive account, billing & security alerts at the mobile number provided. Message frequency varies. Msg & data rates may apply. Reply HELP for help, STOP to opt out. See our Privacy Policy. Mobile information will not be shared with third parties or used for marketing purposes.

**Required-language checklist** (each element MUST appear in the rendered text):

| # | Required element | Present in text |
|---|---|---|
| 1 | Program name "Pilot for Trades" | ✅ "Account alerts from **Pilot for Trades**." |
| 2 | Message types "account, billing & security alerts" | ✅ "You'll receive **account, billing & security alerts** at the mobile number provided." |
| 3 | "Message frequency varies" | ✅ "**Message frequency varies**." |
| 4 | "Msg & data rates may apply" | ✅ "**Msg & data rates may apply**." |
| 5 | "Reply HELP for help, STOP to opt out" | ✅ "**Reply HELP for help, STOP to opt out**." |
| 6 | Privacy Policy link → `https://www.pilotfortrades.com/legal/privacy` | ✅ "See our **Privacy Policy**." (clickable link) |
| 7 | No-sharing statement | ✅ "**Mobile information will not be shared with third parties or used for marketing purposes.**" |

### 2.6 Primary button (Continue)

| Element | Spec |
|---|---|
| Button | `type="submit"`, `w-full py-3 px-6 rounded-lg text-sm font-semibold transition-colors`. Copy: **"Continue →"** |
| Default (enabled) | `bg-brand-600 hover:bg-brand-800 text-white` |
| Disabled (no valid phone) | `opacity-40 cursor-not-allowed bg-brand-600 text-white` (phone is required — button disabled until valid E.164 entered; consent checkbox state does NOT affect button enablement) |
| Focus | `focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2` |
| Submitting | Label changes to **"Saving…"** (consent unchecked) or **"Sending…"** (consent checked, POST consent in flight) |
| `data-testid` | `signup-stayinformed-continue` |

### 2.7 DoubleOptinConfirmSubscreen (replaces PhoneOtpSubscreen)

Renders when `phoneStep === "confirm"` or `phoneStep === "confirmed"`.

| Element | Spec |
|---|---|
| Container | `rounded-xl border border-neutral-200 bg-white p-6 flex flex-col gap-4 shadow-sm`. `data-testid="double-optin-confirm"`. |
| Header row | `flex items-center gap-3` |
| Header icon | `DevicePhoneMobileIcon` (Heroicons 2.0, **outline** variant, `w-6 h-6` (24px), `text-brand-600`, `aria-hidden="true"`) |
| Title | `text-base font-semibold text-neutral-900` — copy: **"Check your phone"** |
| Body text | `text-sm text-neutral-600` — copy: **"We texted {masked phone}. Reply **YES** to confirm and start receiving alerts."** The `{masked phone}` portion is `font-semibold text-neutral-900`. The word **YES** is `font-semibold text-neutral-900`. |
| Phone masking | `maskPhone(phone: string): string` — preserves the leading country code (e.g., `+1`) and the last 4 digits; replaces all other digits with `•`. Example: `+15551234567` → `+1 (•••) •••-4567`. |
| Pending indicator | `flex items-center gap-2 text-sm text-neutral-500`. Spinner: `animate-spin w-4 h-4 text-neutral-400` (SVG, `aria-hidden="true"`). Label: **"Waiting for your reply…"** with `aria-live="polite"`. |
| Timeout hint (after 5 min) | `text-xs text-neutral-500` — copy: **"Still waiting? Make sure your phone can receive texts, or skip for now to continue."** Replaces pending indicator. |
| Action links row | `flex flex-col gap-2 text-sm` |
| "Use a different number" | `text-neutral-500 hover:text-neutral-700 focus:outline-none focus-visible:underline focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-1 rounded`. `data-testid="double-optin-use-different-number"`. |
| "Skip for now → continue" | `text-neutral-500 hover:text-neutral-700 focus:outline-none focus-visible:underline focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-1 rounded`. `data-testid="double-optin-skip-continue"`. |

### 2.8 Confirmed success state (within DoubleOptinConfirmSubscreen)

When `confirmed === true`, the pending indicator is replaced by a success banner and the action links are hidden. Auto-advance to `/signup/plan` after 1500ms.

| Element | Spec |
|---|---|
| Banner | `flex items-center gap-3 rounded-lg bg-margin-50 border border-margin-200 px-4 py-3 text-sm text-margin-700`. `role="status"`, `data-testid="double-optin-confirmed"`. |
| Icon | `CheckCircleIcon` (Heroicons 2.0, **solid** variant, `w-5 h-5` (20px), `text-margin-600`, `aria-hidden="true"`) |
| Text | **"Confirmed — you're opted in. Continuing to plan selection…"** |

### 2.9 Form-level error

| Element | Spec |
|---|---|
| Container | `flex items-start gap-2` |
| Icon | `ExclamationCircleIcon` (outline, `w-4 h-4`, `text-fault-600`, `flex-shrink-0`, `aria-hidden="true"`) |
| Text | `text-sm text-fault-600`, `role="alert"`, `data-testid="stayinformed-submit-error"`. Copy: **"Couldn't send confirmation text. Check your number or try again."** (POST consent failure) or **"Failed to save. Please try again."** (PUT step3 failure) |

---

## 3. Token-Only Colors

All colors reference `pilotPreset` token names. **Zero hex codes.** The React Engineer will fail the linter on any hardcoded color.

| Element | Token classes |
|---|---|
| Page background (from layout) | `bg-neutral-50` |
| H1 text | `text-neutral-900` |
| Subtitle text | `text-neutral-600` |
| Phone label | `text-neutral-700` |
| Required asterisk | `text-fault-600` |
| Phone input border (default) | `border-neutral-300` |
| Phone input border (focus) | `focus-visible:border-brand-600` |
| Phone input border (error) | `border-fault-600` |
| Phone input bg (error) | `bg-fault-50` |
| Phone input focus ring | `focus-visible:ring-brand-600` |
| Helper text | `text-neutral-500` |
| Error text | `text-fault-600` |
| Consent checkbox accent | `accent-brand-600` |
| Consent checkbox focus ring | `focus-visible:ring-brand-600` |
| Consent label | `text-neutral-900` |
| Disclosure container border | `border-neutral-200` |
| Disclosure container bg | `bg-neutral-50` |
| Disclosure icon | `text-neutral-500` |
| Disclosure text | `text-neutral-700` |
| Privacy Policy link | `text-brand-600 hover:text-brand-800` |
| Primary button (enabled) | `bg-brand-600 hover:bg-brand-800 text-white` |
| Primary button (disabled) | `bg-brand-600 text-white opacity-40` |
| Primary button focus ring | `focus-visible:ring-brand-600` |
| Confirm panel border | `border-neutral-200` |
| Confirm panel bg | `bg-white` |
| Confirm panel shadow | `shadow-sm` |
| Confirm header icon | `text-brand-600` |
| Confirm title | `text-neutral-900` |
| Confirm body text | `text-neutral-600` |
| Confirm masked phone / YES | `text-neutral-900` |
| Pending indicator text | `text-neutral-500` |
| Pending spinner | `text-neutral-400` |
| Action links | `text-neutral-500 hover:text-neutral-700` |
| Success banner bg | `bg-margin-50` |
| Success banner border | `border-margin-200` |
| Success banner text | `text-margin-700` |
| Success icon | `text-margin-600` |

---

## 4. Icon Inventory

All icons are [Heroicons 2.0](https://heroicons.com/). No emoji in production web UI.

| Icon | Heroicons name | Variant | Size | Used in |
|---|---|---|---|---|
| Disclosure leading | `InformationCircleIcon` | outline | `w-5 h-5` (20px) | `SmsConsentDisclosure` |
| Privacy Policy external link | `ArrowTopRightOnSquareIcon` | outline | `w-3 h-3` (12px, inline) | `SmsConsentDisclosure` |
| Phone validation error | `ExclamationCircleIcon` | outline | `w-4 h-4` (16px) | Phone field error + form-level error |
| Confirm header | `DevicePhoneMobileIcon` | outline | `w-6 h-6` (24px) | `DoubleOptinConfirmSubscreen` |
| Confirmed success | `CheckCircleIcon` | solid | `w-5 h-5` (20px) | `DoubleOptinConfirmSubscreen` confirmed state |
| Pending spinner | (custom SVG circle) | — | `w-4 h-4` (16px) | `DoubleOptinConfirmSubscreen` pending indicator. Standard `animate-spin` SVG; `aria-hidden="true"`. |

> **Note:** Heroicons does not export a spinner. Use the standard Tailwind `animate-spin` pattern on a simple SVG circle with `stroke-current`. This is a utility SVG, not a Heroicon — acceptable per the "custom SVG required" fallback in §5 of the design standards.

---

## 5. State Coverage

Per §12 of the design standards, every surface covers four data states minimum.

### 5.1 Page-level data states

| State | Trigger | Render |
|---|---|---|
| **Loading** (`isPending`) | On mount, fetching `/api/v1/signup/{tenantId}/state` to verify wizard position | Skeleton: `flex flex-col gap-8` with `WizardProgressBar` + `animate-pulse` placeholder blocks matching the form layout (H1 height + subtitle height + input height + checkbox height + disclosure height + button height). Reduces layout shift vs. a bare spinner. |
| **Error** (`isError`) | `/state` fetch fails | Existing behavior: clear `sessionStorage` `WIZARD_TENANT_ID_KEY`, redirect to `/signup/account`. No new error UI needed — this is a guard-redirect, not a user-facing error. |
| **Empty** | N/A — this is a form, not a list. The "empty" analog is the initial form state (phone empty, consent unchecked). | Entry state renders with empty phone field, unchecked consent, full disclosure visible. |
| **Populated** | `/state` succeeds, user is on step 3 | Entry state renders. If returning from a resumed session, pre-fill phone from `collected_data.phone_number` if present. |

### 5.2 Form interaction states

| State | Trigger | Render |
|---|---|---|
| **Phone empty** | No phone entered | Continue button disabled (`opacity-40 cursor-not-allowed`). No error text. |
| **Phone invalid** | Non-E.164 format entered + blur or submit | Inline error with `ExclamationCircleIcon` + `text-fault-600` + `role="alert"`. Input border `border-fault-600 bg-fault-50`. |
| **Phone valid** | E.164 format (e.g., `+15551234567`) | Error cleared. Continue button enabled. Input border `border-neutral-300`. |
| **Consent unchecked (default)** | Initial render | Checkbox unchecked. Disclosure visible. Continue button enabled (if phone valid). On Continue → PUT step3 with `sms_consent: false` → navigate to `/signup/plan`. |
| **Consent checked** | User clicks checkbox/label | Checkbox checked. Disclosure visible. On Continue → POST consent + PUT step3 → transition to `confirm` state. |
| **Submitting (consent unchecked)** | Continue clicked | Button label: "Saving…". Button disabled. |
| **Submitting (consent checked)** | Continue clicked | Button label: "Sending…". Button disabled. POST `/phone/consent` in flight. |
| **Submit error (POST consent)** | POST `/phone/consent` fails (422 invalid phone, 409 endpoint exists, network) | Form-level error with `ExclamationCircleIcon`. Copy: "Couldn't send confirmation text. Check your number or try again." |
| **Submit error (PUT step3)** | PUT `/step3` fails | Form-level error. Copy: "Failed to save. Please try again." |
| **429 resend cooldown** | User goes back (Use different number) and re-submits quickly | Form-level error. Copy: "We just sent a text. Wait a moment before trying again." |

### 5.3 Confirmation sub-state data states

| State | Trigger | Render |
|---|---|---|
| **Waiting** | `confirm` state, polling `/state` | Pending indicator: spinner + "Waiting for your reply…". Action links visible. |
| **Confirmed** | Polling detects `consent_status='opted_in'` | Success banner with `CheckCircleIcon`. Action links hidden. Auto-advance after 1500ms. |
| **Timeout** | 5 minutes elapsed without confirmation | Timeout hint replaces pending indicator: "Still waiting? Make sure your phone can receive texts, or skip for now to continue." Action links remain visible. |
| **Use different number** | User clicks "Use a different number" | Return to `enter` state. Phone field cleared. Consent checkbox state retained. |
| **Skip for now** | User clicks "Skip for now → continue" | Navigate to `/signup/plan`. Phone already saved (step3 done). Double-opt-in SMS already sent — webhook will process async YES reply. |

---

## 6. Interaction Spec

All five states (default, hover, focus-visible, active, disabled) for every interactive element.

### 6.1 Phone input

| State | Spec |
|---|---|
| Default | `border-neutral-300`, `bg-white`, `text-sm text-neutral-900` |
| Hover | (no change — text inputs don't have a distinct hover in this system) |
| Focus-visible | `focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2 focus-visible:border-brand-600` |
| Active | (same as focus-visible) |
| Disabled | N/A — phone input is never disabled |

### 6.2 Consent checkbox

| State | Spec |
|---|---|
| Default (unchecked) | `accent-brand-600`, `border-neutral-300` |
| Hover | Label `cursor-pointer` — hover on label or checkbox shows pointer |
| Focus-visible | `focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2` |
| Active | (same as focus-visible) |
| Disabled | N/A — checkbox is never disabled |
| Checked | `accent-brand-600` fills with brand color |

### 6.3 Continue button

| State | Spec |
|---|---|
| Default (enabled) | `bg-brand-600 text-white` |
| Hover | `hover:bg-brand-800` |
| Focus-visible | `focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2` |
| Active | `bg-brand-800` (pressed) |
| Disabled (no valid phone) | `opacity-40 cursor-not-allowed bg-brand-600 text-white` — no hover effect |
| Submitting | `opacity-40 cursor-not-allowed` + label "Saving…"/"Sending…" |

### 6.4 Privacy Policy link (in disclosure)

| State | Spec |
|---|---|
| Default | `text-brand-600 underline` |
| Hover | `hover:text-brand-800` |
| Focus-visible | `focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-1 rounded` |
| Active | `text-brand-800` |
| Disabled | N/A |

### 6.5 "Use a different number" link

| State | Spec |
|---|---|
| Default | `text-neutral-500` |
| Hover | `hover:text-neutral-700` |
| Focus-visible | `focus-visible:underline focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-1 rounded` |
| Active | `text-neutral-700` |
| Disabled | N/A |

### 6.6 "Skip for now → continue" link

Same spec as §6.5.

---

## 7. Animation Spec

| Element | Transition | Reduced-motion fallback |
|---|---|---|
| Continue button color | `transition-colors` (Tailwind default: `transition-duration: 150ms`, `transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1)`) | `@media (prefers-reduced-motion: reduce)` → no transition (instant color change) |
| Confirm sub-state entry | `transition: opacity 200ms ease-in-out` (fade in from `opacity-0` to `opacity-100`) | `@media (prefers-reduced-motion: reduce)` → no transition (instant appear) |
| Confirmed success banner | `transition: opacity 200ms ease-in-out` (fade in) | `@media (prefers-reduced-motion: reduce)` → no transition (instant appear) |
| Pending spinner | `animate-spin` (Tailwind default: `animation: spin 1s linear infinite`) | `@media (prefers-reduced-motion: reduce)` → `animation: none` (static or opacity-only; the spinner is decorative — `aria-hidden="true"` — so a static frame is acceptable) |
| Loading skeleton | `animate-pulse` (Tailwind default: `animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite`) | `@media (prefers-reduced-motion: reduce)` → `animation: none` (static skeleton) |

> **Reduced-motion implementation note:** Wrap all transitions in a `motion-safe:` variant or use a `@media (prefers-reduced-motion: reduce)` override. The `animate-spin` and `animate-pulse` utilities should be paired with `motion-reduce:animate-none` (Tailwind's built-in variant).

---

## 8. Component Manifest

Reconciled with `batch-signup-c-design.md` §I. No orphan components.

| # | Component | Path | New/Change | Description |
|---|---|---|---|---|
| 1 | `StayInformedStep` (page body) | `apps/web/src/app/signup/phone/page.tsx` | **Change** | Reframe from "Verify your phone" → "Stay Informed". Replace OTP flow with consent + double-opt-in. Phone required, consent unchecked by default. Manages `enter`/`confirm`/`confirmed` state machine, API calls (POST consent, PUT step3, poll /state), and transitions. |
| 2 | `SmsConsentDisclosure` | `apps/web/src/features/signup/components/SmsConsentDisclosure.tsx` | **New** | Presentational component rendering the full 10DLC CTA disclosure block. Zero props (text is compliance-mandated and static). Exports `SMS_CONSENT_DISCLOSURE_TEXT` constant for SHA-256 hash computation. `data-testid="signup-sms-consent-disclosure"` on root. **Verified not in `packages/ui/src/index.ts`** — `SmsOptOutBadge` (FE-B10) is an opt-out status badge, not a consent disclosure; `NotificationPreferenceMatrix` (FE-B12) is a toggle grid. No existing component to reuse. |
| 3 | `DoubleOptinConfirmSubscreen` | `apps/web/src/features/signup/components/DoubleOptinConfirmSubscreen.tsx` | **New (replaces `PhoneOtpSubscreen`)** | Replaces the fake 6-digit OTP grid with a "reply YES" double-opt-in confirmation panel. Presentational: props `maskedPhone`, `confirmed`, `onUseDifferentNumber`, `onSkipForNow`. The old `PhoneOtpSubscreen.tsx` file is **deleted**. |
| 4 | `PhoneOtpSubscreen` | `apps/web/src/features/signup/components/PhoneOtpSubscreen.tsx` | **Delete** | Removed — the fake OTP grid is replaced by `DoubleOptinConfirmSubscreen`. The `/phone/send-otp` and `/phone/confirm-otp` endpoints it called do not exist in the backend. |
| 5 | `WizardProgressBar` | `apps/web/src/features/signup/components/WizardProgressBar.tsx` | **No change** | Reused as-is, `currentStep="phone"`. Step key `"phone"` and label `"Phone"` retained (route is still `/signup/phone`; the user does enter their phone on this step). |

### Component placement rationale (per §6 design standards)

| Component | Placement | Reason |
|---|---|---|
| `SmsConsentDisclosure` | `apps/web/src/features/signup/components/` | Domain-specific (signup-only compliance text). Not generic enough for `packages/ui` — the disclosure text is Pilot-specific and compliance-mandated. |
| `DoubleOptinConfirmSubscreen` | `apps/web/src/features/signup/components/` | Domain-specific (signup flow only). The double-opt-in confirmation is a signup-step concern, not a reusable platform pattern. |

---

## 9. Implementation Notes

### 9.1 API flow

**When consent is checked (opt-in path):**
1. Compute `disclosure_hash` = `SHA-256(SMS_CONSENT_DISCLOSURE_TEXT)` using Web Crypto API (`crypto.subtle.digest('SHA-256', new TextEncoder().encode(text))`)
2. `POST /api/v1/signup/{tenantId}/phone/consent` with `{ phone_number, sms_consent: true, disclosure_hash }` → creates `user_endpoint` (channel=`sms`, `consent_status='unknown'`, `verification_status='pending'`), sends platform double-opt-in SMS, writes audit (`action='attested'`). Returns `{ user_endpoint_id, verification_status: "pending" }`.
3. `PUT /api/v1/signup/{tenantId}/step3` with `{ phone_number, sms_consent: true }` → advances wizard.
4. Transition to `confirm` state. Start polling.

**When consent is unchecked (no opt-in):**
1. `PUT /api/v1/signup/{tenantId}/step3` with `{ phone_number, sms_consent: false }` → saves phone on `user.phone_number`, advances wizard. No `user_endpoint` SMS row, no double-opt-in SMS.
2. Navigate to `/signup/plan`.

**Polling for YES confirmation:**
- Poll `GET /api/v1/signup/{tenantId}/state` every **3 seconds** while in `confirm` state.
- Check `collected_data.sms_consent_status` (or equivalent field exposed by the backend) for `'opted_in'`.
- On detection → set `confirmed = true` → render success banner → `setTimeout(() => router.push("/signup/plan"), 1500)`.
- Max poll duration: **5 minutes** (100 polls). After timeout, show timeout hint (§5.3).
- Cleanup: `clearInterval` on unmount, state change, or navigation.
- Per `batch-signup-c-design.md` §E: "webhook confirmation updates status via existing polling on /state." Polling is the specified mechanism for this short-lived confirmation wait (not a real-time dashboard surface).

**"Skip for now → continue":**
- Step3 is already done (PUT step3 succeeded before entering `confirm` state). Just `router.push("/signup/plan")`.
- The double-opt-in SMS was already sent. If the user replies YES later, the webhook (`webhooks_sms.py`) will flip `user_endpoint.consent_status='opted_in'` async — the user doesn't lose the ability to opt in by skipping.

**"Use a different number":**
- `setPhoneStep("enter")`, `setPhoneNumber("")`. Consent checkbox state is **retained** (not reset) — the user's intent to opt in is preserved; they just need to correct the number.

### 9.2 Phone validation

- E.164 format: `+` followed by 10–15 digits. Regex: `/^\+?[1-9]\d{6,14}$/`.
- Validate on blur and on submit. Show inline error (with `ExclamationCircleIcon`) if invalid.
- The `Continue` button is disabled until a valid phone is entered. Consent checkbox state does **not** affect button enablement.

### 9.3 Disclosure hash

- `SmsConsentDisclosure` exports `SMS_CONSENT_DISCLOSURE_TEXT` (the exact string rendered in the disclosure paragraph).
- The parent page imports this constant, computes `SHA-256` via Web Crypto API, and sends the hex-encoded hash as `disclosure_hash` in the POST `/phone/consent` request.
- The backend stores this hash in `user_sms_consent_audit.consent_text_hash` for TCPA audit trail.
- **Critical:** the hash must be computed from the exact rendered string (including punctuation, spacing). Any mismatch between the hashed text and the rendered text breaks the audit trail. The `SMS_CONSENT_DISCLOSURE_TEXT` constant is the single source of truth.

### 9.4 Session storage

- `WIZARD_TENANT_ID_KEY` (existing) — `sessionStorage` key for the current `tenant_id`. Read on mount, same as existing page.
- No new session storage keys.

### 9.5 Existing imports to remove

- Remove import of `PhoneOtpSubscreen` from `page.tsx`.
- Remove `PhoneStep` type (`"enter" | "verify" | "verified" | "skip-confirm"`) — replaced by `StayInformedStep` (`"enter" | "confirm" | "confirmed"`).
- Remove `handleSendOtp`, `handleSkipConfirm`, `handleSkipCancel`, `handleSkipConfirmed` handlers — replaced by consent-aware submit + double-opt-in flow.

### 9.6 Test IDs (for the React Engineer's test suite)

| Element | `data-testid` |
|---|---|
| Form | `signup-stayinformed-form` |
| Phone input | `field-phone-number` (retained from existing) |
| Phone error | `field-phone-number-error` |
| Consent checkbox | `signup-sms-consent-checkbox` |
| Consent label | `signup-sms-consent-label` |
| Disclosure block | `signup-sms-consent-disclosure` (required by task) |
| Continue button | `signup-stayinformed-continue` |
| Confirm subscreen | `double-optin-confirm` |
| Use different number | `double-optin-use-different-number` |
| Skip for now | `double-optin-skip-continue` |
| Confirmed success | `double-optin-confirmed` |
| Submit error | `stayinformed-submit-error` |

### 9.7 Composable shared components (checked against `packages/ui/src/index.ts`)

| Need | Component | Status |
|---|---|---|
| Loading skeleton | `animate-pulse` utility (Tailwind) | Used directly — no `LoadingState` needed for a form skeleton |
| Error state (page-level) | N/A — guard-redirect on `/state` failure | Existing behavior retained |
| Notification banner | `NotificationBanner` from `@pilot/ui` | Not needed — form-level inline errors suffice for this single-step form |
| Role gate | `RoleGate` from `@pilot/ui` | Not needed — pre-auth onboarding step, no RBAC |
| Help anchor | `HelpAnchor` from `@pilot/ui` | Not needed on signup steps (pre-auth, no help system) |

No new shared component proposed for `packages/ui`. Both new components are feature-specific and live in `apps/web/src/features/signup/components/`.

---

## 10. Accessibility Notes (WCAG 2.2 AA)

The React Engineer's Definition of Done requires **zero axe-core violations**. The following accessibility decisions are baked into this design spec.

### 10.1 Color is never the only signal

| Element | Color + non-color signal |
|---|---|
| Phone validation error | `text-fault-600` (red) **+** `ExclamationCircleIcon` (outline) **+** `role="alert"` text "Enter a valid mobile number…" |
| Form-level submit error | `text-fault-600` (red) **+** `ExclamationCircleIcon` (outline) **+** `role="alert"` text |
| Consent checkbox checked state | `accent-brand-600` (brand fill) **+** standard browser checkmark glyph inside the checkbox |
| Confirmed success | `bg-margin-50` / `text-margin-700` (green) **+** `CheckCircleIcon` (solid) **+** `role="status"` text "Confirmed — you're opted in." |
| Disabled Continue button | `opacity-40` (muted) **+** `cursor-not-allowed` **+** `aria-disabled="true"` |

No status is communicated by color alone. All error/success states pair color with an icon and text.

### 10.2 Target sizes ≥ 24×24px (WCAG 2.2 SC 2.5.8)

| Element | Target size | Notes |
|---|---|---|
| Consent checkbox | 20×20px visual (`h-5 w-5`) | The `<label htmlFor="signup-sms-consent-checkbox">` association makes the **entire label text** (full width × line height, well over 24×24px) a click target. The checkbox itself is 20px; the label extends the hit area. |
| Continue button | Full width × 48px (`w-full py-3`) | Well over 24×24px. |
| Privacy Policy link | Text link with `rounded` + `focus-visible:ring-offset-1` | The link text "Privacy Policy" + icon is ≥24×24px. `focus-visible:ring-offset-1` ensures the focus ring doesn't clip. |
| "Use a different number" / "Skip for now" links | Full-width text links in a `flex flex-col gap-2` | Each link is full width × line height (≥24px). `rounded` + `focus-visible:ring-offset-1` for focus ring clearance. |
| Phone input | Full width × 40px (`w-full py-2.5`) | Well over 24×24px. |

### 10.3 Focus-visible treatment (WCAG 2.2 SC 2.4.11 + 2.4.7)

- All interactive elements use `focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2` (or `ring-offset-1` for inline links) — keyboard users get a visible ring; mouse users don't see a persistent ring on click.
- The signup layout has no sticky header or `NotificationBanner` portal on this route (pre-auth shell), so focus is never obscured by overlapping content. No `scroll-margin-top` adjustment needed.
- **Focus order** (tab sequence): Phone input → Consent checkbox → Privacy Policy link (within disclosure) → Continue button. This is the natural DOM order. In the `confirm` state: "Use a different number" → "Skip for now → continue".
- **Modal focus-trap**: N/A — no modal on this screen. The skip-confirm dialog from the old page is removed (phone is required; no skip on entry state).

### 10.4 Form field labels (WCAG 2.2 SC 3.3.2 + 1.3.1)

- Phone input has a visible `<label htmlFor="field-phone-number">` above it: "Mobile number *". Placeholder is **not** used as a label (banned per §10 design standards).
- Error text is linked via `aria-describedby="field-phone-number-error"` on the input, with `role="alert"` on the error `<p>`.
- Helper text is linked via `aria-describedby` on the input.
- Consent checkbox has a visible `<label htmlFor="signup-sms-consent-checkbox">` wrapping the benefit-forward text.

### 10.5 Accessible authentication (WCAG 2.2 SC 3.3.8)

- **Paste allowed** on the phone input — no `onPaste` handler, no `onDrop` restriction. The input is `type="tel"` with `inputMode="tel"` and `autoComplete="tel"`. A user can paste a phone number from their contacts/clipboard.
- No memorization puzzle — the phone is a standard tel input, not an OTP/code field.
- The old 6-digit OTP grid (which could be argued to inhibit paste) is **removed entirely**.

### 10.6 Consistent help + redundant entry (WCAG 2.2 SC 3.2.6 + 3.3.7)

- `HelpAnchor` is not present on signup steps (pre-auth, no help system) — consistent across all signup steps.
- **Carry-forward**: if the user navigates back to this step from a resumed session, the phone field is pre-filled from `collected_data.phone_number` (if the backend exposes it). The consent checkbox is **not** pre-checked (unchecked-by-default is the compliance posture — even on resume, the user must actively opt in). No data is re-asked.

### 10.7 Reduced motion (WCAG 2.2 SC 2.3.3)

- All transitions (§7) have `@media (prefers-reduced-motion: reduce)` fallbacks: no transition (instant appear/color change).
- `animate-spin` (pending spinner) and `animate-pulse` (loading skeleton) are paired with `motion-reduce:animate-none` (Tailwind's built-in variant). The spinner is decorative (`aria-hidden="true"`), so a static frame is acceptable.

### 10.8 Live regions

| Element | `aria-live` | Purpose |
|---|---|---|
| Pending indicator "Waiting for your reply…" | `aria-live="polite"` | Announces the waiting state to screen readers without interrupting |
| Confirmed success banner | `role="status"` (implies `aria-live="polite"`) | Announces confirmation when YES is received |
| Error text | `role="alert"` (implies `aria-live="assertive"`) | Announces validation/submit errors immediately |

### 10.9 Disclosure block accessibility

- The disclosure container has `data-testid="signup-sms-consent-disclosure"` and is a `<section aria-label="SMS consent disclosure">` (or `<div role="region" aria-label="...">`) so screen readers can navigate to it.
- The Privacy Policy link has a descriptive `aria-label="Pilot for Trades Privacy Policy (opens in new tab)"` and `rel="noopener noreferrer"`.
- The `ArrowTopRightOnSquareIcon` after the link is `aria-hidden="true"` (decorative — the `aria-label` on the link conveys the external-link semantics).

---

## 11. Responsive Behavior

Per §4 design standards: desktop-first at 1280px. The signup layout shell constrains content to `max-w-lg` (512px) centered, so the design is inherently single-column.

| Viewport | Behavior |
|---|---|
| **1280px+** (primary) | Content centered at 512px within `min-h-screen bg-neutral-50`. All elements single-column. |
| **1024px** | Same as 1280px — content centered at 512px. |
| **768px** | Content full-width with `px-4` padding (from layout `main` classes). All elements remain single-column. `WizardProgressBar` step labels are `hidden sm:block` — at 768px (`sm:` breakpoint = 640px) labels are visible. Below 640px, only dots show. |
| **< 640px** | WizardProgressBar shows dots only (labels hidden). All form elements full-width. No layout reflow needed — everything is single-column by design. |

No multi-column layout on this screen — no table or grid to reflow.

---

## 12. Visual System Consistency (Sibling Match)

This screen matches the visual system of the sibling signup steps (`legal/page.tsx` and `plan/page.tsx`):

| Element | This screen | Sibling (legal/plan) | Match |
|---|---|---|---|
| Root container | `flex flex-col gap-8` | `flex flex-col gap-8` | ✅ |
| `WizardProgressBar` | `currentStep="phone"` | `currentStep="legal"`/`"plan"` | ✅ (same component) |
| H1 | `text-2xl font-bold text-neutral-900` | `text-2xl font-bold text-neutral-900` | ✅ |
| Subtitle | `text-sm text-neutral-600` | `text-sm text-neutral-600` | ✅ |
| Primary button | `w-full py-3 px-6 rounded-lg text-sm font-semibold bg-brand-600 hover:bg-brand-800 text-white` | Same | ✅ |
| Disabled button | `opacity-40 cursor-not-allowed bg-brand-600 text-white` | Same | ✅ |
| Error text | `text-fault-600 text-sm` with `role="alert"` | Same | ✅ |
| Focus-visible ring | `focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2` | Same | ✅ |
| Checkbox style | `accent-brand-600` with `focus-visible:ring-brand-600` | `LegalCheckboxGroup` uses `accent-brand-600 focus:ring-brand-600` | ✅ (upgraded to `focus-visible` per §11 design standards) |

---

## 13. Compliance Screenshot Checklist

Per `telnyx-10dlc-p4t-tenant-comms-campaign.md` §5, Tom must capture two screenshots after this screen deploys to production:

| # | Screenshot | State | URL |
|---|---|---|---|
| 1 | `signup-stayinformed-checked.png` | Phone entered, consent checkbox **checked**, disclosure visible | `https://pilotfortrades.com/compliance/signup-stayinformed-checked.png` |
| 2 | `signup-stayinformed-unchecked.png` | Default state: phone empty or entered, consent checkbox **unchecked**, disclosure visible | `https://pilotfortrades.com/compliance/signup-stayinformed-unchecked.png` |

The disclosure block (`data-testid="signup-sms-consent-disclosure"`) must be fully visible and legible in both screenshots. The unchecked default is the key compliance signal — it removes any pre-checked-box objection from the TCR reviewer.

---

## Handoff Gate

**This spec is ready for Tom's review. Implementation starts only after approval.**

The React Engineer prompt (`batch-signup-c-react-engr-prompt.md`) references this spec path and is gated on Tom approving it. No `.tsx` or `.ts` files have been written by this design pass — output is a markdown design spec only.
