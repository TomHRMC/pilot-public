# C-B9 — UI Design Spec: Messaging Setup Page (10DLC Provisioning)

**Batch**: C-B9 (10DLC Provisioning State Machine + Stripe Checkout Setup Charge + Sole-Prop OTP Loop)
**Mode**: Pilot Web UI Designer
**Platform**: Web dashboard only (`apps/web`)
**Route**: `/settings/messaging`
**Design doc**: `batch-c-b9-design.md` — §D (API endpoints), §H (Surface Mockup Reference), §I (Component Manifest)
**Date**: August 5, 2026
**Status**: Ready for Tom's review (revision 2 — incorporates Tom's feedback on charge timing, refund removal, phone number selection)

---

## 1. Surface Overview

### 1.1 — What this is

A **Messaging Setup page** at `/settings/messaging` that guides a tenant through the full 10DLC provisioning lifecycle — from entity type selection through brand registration, cost quote, Stripe Checkout payment, sole-proprietor OTP entry (if applicable), and active status.

This page replaces the current placeholder messaging settings surface. The existing DLC-1 profile form at `/settings/communications/sms-compliance` remains as a read-only "business profile" reference; the new `/settings/messaging` page is the active provisioning wizard.

### 1.2 — Route & shell

| Property | Value |
|---|---|
| Route | `/settings/messaging` |
| Layout | `settings/layout.tsx` — `max-w-3xl` container with `SettingsBreadcrumb`, `px-6 py-8`, `bg-neutral-50` |
| Parent shell | `(authed)/layout.tsx` — `h-12` header + `AppSidebar` (collapsible, 64–200px) + content area |
| RBAC | `<RoleGate role={["owner"]}>` — owner-only. The `settings.manage` permission maps to owner per the design-system reference §8. `office_staff` and `operator` can view (`settings.view`) but cannot mutate; the form panels are read-only for them. `tech` is hidden entirely (no settings access). |

### 1.3 — Entry point

Reached from the post-wizard checklist item "Set up text messaging" (added by C-B5). The checklist item links to `/settings/messaging`. Cost disclosure is inline on the checklist: "Carrier registration runs about $13–$37 depending on your business setup. That goes to the phone carrier — we don't take any of it."

### 1.4 — The 12-state machine drives the UI

The frontend polls `GET /api/v1/tenants/{tenant_id}/messaging/status` (§D.4) to determine which panel to render. The status response shape:

```json
{
  "registration_id": "uuid",
  "status": "awaiting_otp",
  "entity_type": "sole_proprietor",
  "telnyx_brand_id": "brand_abc123",
  "telnyx_campaign_id": null,
  "telnyx_phone_number": null,
  "quoted_setup_cents": 1500,
  "quoted_monthly_cents": 367,
  "otp_requested_at": "2026-08-05T14:00:00Z",
  "failure_reason": null,
  "updated_at": "2026-08-05T14:00:00Z"
}
```

**Status → panel mapping** (see §3 for full state-driven panel switching logic):

| `status` value | Panel rendered |
|---|---|
| `not_started` (404 on GET status) | `EntityTypeSelector` + `BrandRegistrationForm` |
| `quoting` | `CarrierQuoteDisplay` + `CheckoutRedirectButton` |
| `awaiting_payment` | `CarrierQuoteDisplay` (read-only) + "Waiting for payment confirmation" pending state |
| `payment_failed` | `ProvisioningErrorPanel` (payment failed variant) |
| `brand_submitted` | `ProvisioningStatusIndicator` (pending) — standard entity |
| `awaiting_otp` | `OtpEntryPanel` — sole prop only |
| `brand_verified` | `ProvisioningStatusIndicator` (pending — campaign submitting) |
| `campaign_submitted` | `ProvisioningStatusIndicator` (pending) |
| `awaiting_number_selection` | `PhoneNumberSelector` — tenant picks their number |
| `number_assigned` | `ProvisioningStatusIndicator` (pending — activating) |
| `active` | Success state — "Text messaging is active" |
| `brand_rejected` | `ProvisioningErrorPanel` (terminal — contact support) |
| `campaign_rejected` | `ProvisioningErrorPanel` (terminal — contact support) |
| `suspended` | `ProvisioningErrorPanel` (suspended variant) |

---

## 2. Page Layout & Container

### 2.1 — Page header

```
┌─────────────────────────────────────────────────────────┐
│  Settings > Branding > Messaging Setup    [?] HelpAnchor │  ← breadcrumb (from settings/layout.tsx)
├─────────────────────────────────────────────────────────┤
│  Text Messaging Setup                                    │  ← h1, text-h1 font-semibold text-neutral-900
│  Register your business with the carrier network to     │  ← p, text-body text-neutral-500
│  send compliant SMS messages. Carrier fees apply.       │
├─────────────────────────────────────────────────────────┤
│  [ProvisioningStatusIndicator — horizontal stepper]      │  ← always visible once status != not_started
├─────────────────────────────────────────────────────────┤
│                                                          │
│  [State-driven panel renders here]                       │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Pixel specs:**
- Page container: `max-w-3xl` (768px content max), `px-6 py-8`, `space-y-6` between sections
- H1: `text-h1 font-semibold text-neutral-900` (per typography scale §7)
- Subtitle: `text-body text-neutral-500 mt-1`
- `HelpAnchor` (from `@pilot/ui`) positioned top-right of the header row, `helpContext: { surface: "settings-messaging-setup" }`
- `ProvisioningStatusIndicator` below the header, full-width, `mb-6`

### 2.2 — Card / panel pattern

Every state-driven panel is a card:
- Container: `bg-white rounded-lg border border-neutral-200 shadow-sm p-6 space-y-4`
- Section heading inside card: `text-h2 font-semibold text-neutral-900`
- Section description: `text-sm text-neutral-500 mt-1`

---

## 3. State-Driven Panel Switching Logic

The `MessagingSetupPage` component orchestrates which panel renders based on the `status` field from `useProvisioningStatus`. The logic is a single switch:

```
status === undefined (404 / not_started)
  → render EntityTypeSelector + BrandRegistrationForm (combined initial panel)

status === "quoting"
  → render CarrierQuoteDisplay + CheckoutRedirectButton

status === "awaiting_payment"
  → render CarrierQuoteDisplay (read-only) + pending notice

status === "payment_failed"
  → render ProvisioningErrorPanel variant="payment_failed"

status === "brand_submitted"
  → render ProvisioningStatusIndicator (active step: brand) + pending copy

status === "awaiting_otp"
  → render OtpEntryPanel

status === "brand_verified"
  → render ProvisioningStatusIndicator (active step: campaign) + pending copy

status === "campaign_submitted"
  → render ProvisioningStatusIndicator (active step: campaign) + pending copy

status === "number_assigned"
  → render ProvisioningStatusIndicator (active step: activation) + pending copy

status === "active"
  → render success panel

status === "brand_rejected" | "campaign_rejected"
  → render ProvisioningErrorPanel variant="rejected"

status === "suspended"
  → render ProvisioningErrorPanel variant="suspended"
```

**Polling behavior**: `useProvisioningStatus` uses TanStack Query `refetchInterval`. When `status` is one of `brand_submitted`, `awaiting_otp`, `brand_verified`, `campaign_submitted`, `number_assigned`, `awaiting_payment` — poll every **5 seconds**. When status is terminal (`active`, `brand_rejected`, `campaign_rejected`, `suspended`, `payment_failed`, `quoting`) — stop polling (`refetchInterval: false`).

**Stripe Checkout return handling**: On mount, check `searchParams.status`. If `status=paid` → show a transient `NotificationBanner` (success severity, auto-dismiss 5s) "Payment received — provisioning your brand now." If `status=cancelled` → show a transient `NotificationBanner` (warning severity, auto-dismiss 5s) "Payment cancelled. You can retry when ready." Then clear the query param via `router.replace('/settings/messaging')`.

---

## 4. Component Specs

### 4.1 — `MessagingSetupPage`

**File**: `apps/web/src/app/(authed)/settings/messaging/page.tsx`
**Type**: Thin server component (RULE 9) — renders `<MessagingSetupClient>` client component.

**Pixel specs**: Inherits `max-w-3xl px-6 py-8` from `settings/layout.tsx`.

**Client orchestrator** (`apps/web/src/components/settings/messaging/MessagingSetupClient.tsx`):
- `"use client"` — manages the state-driven panel switching
- Calls `useProvisioningStatus()` (TanStack Query with polling)
- Calls `use10DlcProfile()` to pre-fill the brand form (existing hook, reused)
- Renders `ProvisioningStatusIndicator` (always, once status exists) + the state-driven panel
- Handles Stripe Checkout return query params

**Data states** (all four required per §12):
1. `isPending` (initial status fetch) → `<LoadingState type="inline" label="Loading messaging setup..." />`
2. `isError` (status fetch failed) → `<ErrorState type="server" title="Could not load messaging status" description="Check your connection and try again." />` with retry button
3. Empty (404 = `not_started`) → `EntityTypeSelector` + `BrandRegistrationForm` (the initial provisioning panel)
4. Populated → state-driven panel per §3

---

### 4.2 — `EntityTypeSelector`

**File**: `apps/web/src/components/settings/messaging/EntityTypeSelector.tsx`

**Purpose**: "Does your business have an EIN?" → Yes (`standard`) / No (`sole_proprietor`). Determines the provisioning path.

**Layout**:
```
┌─────────────────────────────────────────────────┐
│  Business Type                                   │  ← text-h2 font-semibold text-neutral-900
│  Does your business have an EIN (Employer        │  ← text-sm text-neutral-500
│  Identification Number)?                         │
├─────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌──────────────────┐     │
│  │ ○ Yes, we have   │  │ ○ No, I'm a sole │     │  ← two selectable cards
│  │   an EIN         │  │   proprietor     │     │
│  │                  │  │                  │     │
│  │ Standard brand   │  │ OTP verification │     │  ← text-xs text-neutral-500
│  │ registration.    │  │ loop required.   │     │
│  │ Automated path.  │  │ ~1,000 msg/day   │     │
│  │                  │  │ cap.             │     │
│  └──────────────────┘  └──────────────────┘     │
│                                                  │
│  [ℹ] Standard: Automated brand registration     │  ← help text, bg-brand-50 border border-brand-200
│      with the carrier. Faster approval.          │     rounded-md p-3 text-sm text-brand-700
│                                                  │
│  [ℹ] Sole Proprietor: Carrier sends a PIN via   │  ← help text, bg-alert-50 border border-alert-200
│      SMS to your business phone. You enter it    │     rounded-md p-3 text-sm text-alert-700
│      here to verify. Lower throughput cap.       │
└─────────────────────────────────────────────────┘
```

**Pixel specs**:
- Card grid: `grid grid-cols-2 gap-4` (at 1280px); `grid-cols-1` at 768px
- Each selectable card: `border border-neutral-200 rounded-lg p-4 cursor-pointer transition-colors`
  - Selected state: `border-brand-500 bg-brand-50 ring-2 ring-brand-500`
  - Default: `border-neutral-200 bg-white hover:bg-neutral-50`
  - Focus-visible: `focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:outline-none`
  - Active: `border-brand-600 bg-brand-50`
- Radio indicator: `w-5 h-5` `CheckCircleIcon` (solid, Heroicons) when selected, `CircleStackIcon`-style empty circle — use `CheckCircleIcon` outline variant when unselected. Icon `w-5 h-5 text-neutral-400` (unselected) / `text-brand-600` (selected).
- Card title: `text-sm font-medium text-neutral-900`
- Card description: `text-xs text-neutral-500 mt-1`
- Help text blocks: `rounded-md p-3 text-sm`, `bg-brand-50 border border-brand-200 text-brand-700` (standard) / `bg-alert-50 border border-alert-200 text-alert-700` (sole prop). Icon: `InformationCircleIcon` (outline, `w-5 h-5`) inline-left.

**Interaction states** (all five):
| State | Standard card | Sole prop card |
|---|---|---|
| Default | `border-neutral-200 bg-white` | `border-neutral-200 bg-white` |
| Hover | `hover:bg-neutral-50` | `hover:bg-neutral-50` |
| Focus-visible | `focus-visible:ring-2 focus-visible:ring-brand-500` | `focus-visible:ring-2 focus-visible:ring-brand-500` |
| Active (pressed) | `border-brand-600 bg-brand-50` | `border-brand-600 bg-brand-50` |
| Selected | `border-brand-500 bg-brand-50 ring-2 ring-brand-500` | `border-brand-500 bg-brand-50 ring-2 ring-brand-500` |

**Accessibility**:
- Each card is a `<button role="radio" aria-checked={isSelected}>` inside a `<fieldset>` with `<legend>` "Business type"
- Target size: full card (min 44×44px hit area — card is much larger)
- Color is not the only signal: selected card has the `CheckCircleIcon` (solid) + `ring-2` border + `aria-checked="true"`

**Props**:
```typescript
interface EntityTypeSelectorProps {
  value: "standard" | "sole_proprietor" | null;
  onChange: (value: "standard" | "sole_proprietor") => void;
  disabled?: boolean;
}
```

---

### 4.3 — `BrandRegistrationForm`

**File**: `apps/web/src/components/settings/messaging/BrandRegistrationForm.tsx`

**Purpose**: Form for brand registration data. Pre-filled from `tenant_10dlc_profile` (via existing `use10DlcProfile` hook). Submits via `useInitiateProvisioning` mutation (`POST /messaging/provision`).

**Layout** (single-column form, `max-w-2xl` within the card):
```
┌─────────────────────────────────────────────────┐
│  Brand Registration                              │
│  This information is submitted to the carrier    │
│  (Telnyx) for 10DLC brand registration.          │
├─────────────────────────────────────────────────┤
│  Legal Business Name *                           │
│  [___________________________________]           │
│                                                  │
│  DBA Name (optional)                             │
│  [___________________________________]           │
│                                                  │
│  EIN / Tax ID *            ← only if entity=standard │
│  [_______________]                              │
│  Format: 12-3456789                              │
│                                                  │
│  ── HQ Address ──                                │
│  ┌─────────────────────────────────────────┐    │
│  │ Address Line 1                          │    │
│  │ [___________________________________]   │    │
│  │ Address Line 2 (optional)               │    │
│  │ [___________________________________]   │    │
│  │ [City________] [State__] [ZIP____]      │    │
│  └─────────────────────────────────────────┘    │
│                                                  │
│  Support Email              Support Phone        │
│  [__________________]      [__________________]  │
│                                                  │
│  Website *                                       │  ← NEW (C-B9)
│  [___________________________________]           │
│  Required by the carrier for brand registration. │
│                                                  │
│  Business Vertical *        ← NEW (C-B9), dropdown │
│  [▼ ELECTRICIAN                           ]      │
│  Populated from carrier enum endpoint.           │
│                                                  │
│  Stock Symbol (optional)    ← NEW (C-B9), conditional │
│  [_______________]                              │
│  Only if publicly traded.                        │
│                                                  │
│  [Cancel]                          [Get Quote →] │
└─────────────────────────────────────────────────┘
```

**Pixel specs** (per form pattern §5 of design-system reference):
- Container: `space-y-4`
- Label: `text-sm font-medium text-neutral-700 mb-1` (existing `LABEL_CLASS` pattern from `TenantDlcProfileForm.tsx`)
- Input: `w-full border border-neutral-200 rounded-md px-3 py-2 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-brand-400 focus:border-transparent` (matches existing form)
- Required indicator: `<span className="text-alert-600">*</span>`
- Helper text: `text-xs text-neutral-500 mt-1`
- Error text: `text-xs text-fault-600 mt-1` with `aria-describedby` linking to input
- HQ Address fieldset: `space-y-3 border border-neutral-100 rounded-md p-4` with `<legend>`
- City/State/ZIP grid: `grid grid-cols-2 gap-3 sm:grid-cols-3`
- Support email/phone grid: `grid grid-cols-1 sm:grid-cols-2 gap-4`
- Submit button: `bg-brand-600 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-brand-700`
- Cancel button: `border border-neutral-300 text-neutral-700 rounded-md px-4 py-2 text-sm font-medium hover:bg-neutral-50`

**Conditional fields**:
- `ein`: Required + visible when `entity_type === "standard"`. Hidden when `sole_proprietor`.
- `stock_symbol`: Always visible but labeled "(optional — only if publicly traded)". Helper text: "Only fill in if your company is publicly traded on a stock exchange."

**Vertical dropdown**:
- `<select>` element styled to match input classes
- Populated from a TanStack Query hook `useCarrierVerticals()` that calls `GET /api/v1/tenants/{tenant_id}/messaging/verticals` (proxies Telnyx `/enum/vertical`)
- **Do not hardcode vertical values** — per design doc §H.3 and Tom's T3 resolution
- Loading state: disabled select with "Loading verticals..." placeholder
- Error state: text input fallback with helper text "Enter your business vertical (e.g., ELECTRICIAN)"

**Validation** (client-side, before `POST /messaging/provision`):
- `legal_business_name`: required, non-empty
- `ein`: required when `entity_type === "standard"`, format `^\d{2}-?\d{7}$`
- `website`: required, valid URL format
- `vertical`: required (must be selected)
- `support_email`: valid email format
- `support_phone`: E.164 format (`+1...`)
- All address fields: required when entity is `standard` (carrier requires HQ address)

**Pre-fill behavior**:
- On mount, if `use10DlcProfile()` returns data, pre-fill all matching fields
- EIN is masked on read (`ein_masked`) — do not pre-fill; user re-enters to update (matches existing `TenantDlcProfileForm` behavior)
- New fields (`website`, `stock_symbol`, `vertical`) pre-fill from the extended profile response

**Submit behavior**:
- Calls `useInitiateProvisioning().mutateAsync(formData)`
- On success: status transitions to `quoting`, the page re-renders showing `CarrierQuoteDisplay`
- On 409 (already in non-retryable state): show `NotificationBanner` (error) "Messaging setup is already in progress. Refresh to see current status."
- On 422 (validation error): show field-level errors from RFC 7807 response
- Button shows "Getting quote..." with `disabled` state during mutation

**Interaction states** (submit button):
| State | Classes |
|---|---|
| Default | `bg-brand-600 text-white` |
| Hover | `hover:bg-brand-700` |
| Focus-visible | `focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:outline-none` |
| Active (pressed) | `bg-brand-700` |
| Disabled | `disabled:opacity-50 disabled:cursor-not-allowed` (when form invalid or mutation pending) |

**Accessibility**:
- Every field has a visible `<label htmlFor="...">` above it (no placeholder-as-label)
- Error text linked via `aria-describedby="{fieldId}-error"`
- Required fields marked with `*` and `aria-required="true"`
- Fieldset/legend for grouped address fields
- Form submit on Enter key

---

### 4.4 — `CarrierQuoteDisplay`

**File**: `apps/web/src/components/settings/messaging/CarrierQuoteDisplay.tsx`

**Purpose**: Itemized cost quote display. Reuses C-B8's `CarrierQuoteResponse` type. Implements the **always-preview-before-send** pattern (§16.7) — the tenant sees each cost line before paying.

**Layout**:
```
┌─────────────────────────────────────────────────┐
│  Cost Quote                                      │  ← text-h2 font-semibold text-neutral-900
│  Carrier registration fees — passed through at   │  ← text-sm text-neutral-500
│  cost. Pilot adds no markup.                     │
├─────────────────────────────────────────────────┤
│  One-Time Setup Costs                            │  ← text-sm font-medium text-neutral-700
│  ┌─────────────────────────────────────────┐    │
│  │ Brand registration           $4.00      │    │  ← flex justify-between, text-sm text-neutral-900
│  │ Campaign registration        $0.00      │    │
│  │ Phone number assignment      $0.00      │    │
│  │ ─────────────────────────────────────── │    │  ← border-t border-neutral-200
│  │ Setup total                  $4.00      │    │  ← font-medium
│  └─────────────────────────────────────────┘    │
│                                                  │
│  Recurring Monthly Costs                         │  ← text-sm font-medium text-neutral-700
│  ┌─────────────────────────────────────────┐    │
│  │ Phone number                 $0.30      │    │
│  │ Campaign maintenance         $0.00      │    │
│  │ ─────────────────────────────────────── │    │
│  │ Monthly total                $0.30/mo   │    │  ← font-medium
│  └─────────────────────────────────────────┘    │
│                                                  │
│  [ℹ] Per-message surcharges apply at carrier    │  ← bg-neutral-50 border border-neutral-200
│      rates (~$0.003/segment). Billed monthly.    │     rounded-md p-3 text-xs text-neutral-600
│                                                  │
│  Passed through at cost — Pilot adds no markup.  │  ← text-xs text-neutral-500 italic
└─────────────────────────────────────────────────┘
```

**Pixel specs**:
- Line item row: `flex justify-between py-1.5 text-sm text-neutral-900`
- Line item label: `text-neutral-700`
- Line item amount: `text-neutral-900 font-mono` (monospace for alignment)
- Separator: `border-t border-neutral-200 my-2`
- Total row: `flex justify-between py-1.5 text-sm font-medium text-neutral-900`
- Info callout: `bg-neutral-50 border border-neutral-200 rounded-md p-3 text-xs text-neutral-600` with `InformationCircleIcon` (outline, `w-4 h-4`) inline-left
- Disclosure: `text-xs text-neutral-500 italic mt-2`

**Money display** (per §12 stack awareness):
- Amounts arrive as `amount_millicents` (1 millicent = $0.00001) from the C-B8 temporal fee schedule
- **Display rule**: `amount_millicents / 100000` → format as USD with 2 decimal places for setup totals, 2 decimal places for monthly totals
- Per-segment surcharges: display as `~$0.003/segment` (3 decimal places — these are sub-cent rates)
- Setup total: `setup_total_millicents / 100000` → `$X.XX`
- Monthly total: `recurring_monthly_millicents / 100000` → `$X.XX/mo`

**Props**:
```typescript
interface CarrierQuoteDisplayProps {
  quote: CarrierQuoteResponse;  // from C-B8 shared types
  readOnly?: boolean;  // when status is awaiting_payment
}
```

**Data states**:
1. `isPending` (quote fetching) → skeleton matching the line-item layout (per §11 — skeleton over spinner)
2. `isError` → `<ErrorState type="server" title="Could not load quote" description="..." />` with retry
3. Empty (no line items) → `<EmptyState title="No quote available" description="Complete your brand registration to get a quote." />`
4. Populated → full quote display

---

### 4.5 — `CheckoutRedirectButton`

**File**: `apps/web/src/components/settings/messaging/CheckoutRedirectButton.tsx`

**Purpose**: "Continue to payment" button → calls `useCreateCheckout` mutation (`POST /messaging/checkout`) → redirects to Stripe Checkout URL.

**Layout**:
```
┌─────────────────────────────────────────────────┐
│  [Continue to Payment →]                        │  ← full-width button, bg-brand-600
│                                                 │
│  You'll be redirected to Stripe to complete     │  ← text-xs text-neutral-500
│  payment securely. Your card is charged upon    │
│  submission — this is how the carrier bills us. │
└─────────────────────────────────────────────────┘
```

**Pixel specs**:
- Button: `w-full bg-brand-600 text-white rounded-md px-4 py-3 text-sm font-medium hover:bg-brand-700 transition-colors flex items-center justify-center gap-2`
- Icon: `ArrowRightIcon` (outline, `w-5 h-5`) right of label
- Helper text: `text-xs text-neutral-500 mt-2 text-center`
- Container: `mt-4`

**Interaction states** (all five):
| State | Classes |
|---|---|
| Default | `bg-brand-600 text-white` |
| Hover | `hover:bg-brand-700` |
| Focus-visible | `focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:outline-none` |
| Active (pressed) | `bg-brand-700` |
| Disabled (pending) | `disabled:opacity-50 disabled:cursor-not-allowed` — label changes to "Redirecting to Stripe..." |

**Behavior**:
- On click: calls `useCreateCheckout().mutateAsync()`
- On success: `window.location.href = response.checkout_url` (full page redirect to Stripe)
- On 409 (status not `quoting`): `NotificationBanner` (error) "Quote expired or setup already in progress. Refresh the page."
- On 500 (Stripe error): `NotificationBanner` (error) "Payment system unavailable. Please try again in a moment."

**Accessibility**:
- Target size: `py-3` gives ~44px height — meets WCAG 2.5.8
- Button has `aria-label="Continue to Stripe payment"` for screen readers
- Loading state announced via `aria-busy="true"`

---

### 4.6 — `OtpEntryPanel`

**File**: `apps/web/src/components/settings/messaging/OtpEntryPanel.tsx`

**Purpose**: Sole-proprietor OTP entry. Appears when `status === "awaiting_otp"`. The carrier is texting a PIN to the brand's mobile number; the tenant enters it here.

**Layout**:
```
┌─────────────────────────────────────────────────┐
│  Verify Your Business                            │  ← text-h2 font-semibold text-neutral-900
│                                                  │
│  [📱] The carrier is texting a PIN to            │  ← text-sm text-neutral-900, DevicePhoneMobileIcon
│       {support_phone}. Enter it below to         │     (outline, w-5 h-5, text-brand-600) inline-left
│       verify your business.                      │
│                                                  │
│  ┌─┬─┬─┬─┬─┬─┐                                   │  ← 6-digit OTP input, individual cells
│  │ │ │ │ │ │ │                                   │
│  └─┴─┴─┴─┴─┴─┘                                   │
│                                                  │
│  [Submit PIN]                                    │  ← bg-brand-600
│                                                  │
│  ⏱ PIN expires in 5h 23m                         │  ← text-xs text-alert-600 (when < 6h remaining)
│  [ℹ] Didn't receive a PIN? Make sure your        │  ← text-xs text-neutral-500
│      business phone can receive SMS. The PIN     │
│      may take a few minutes to arrive.           │
└─────────────────────────────────────────────────┘
```

**Pixel specs**:
- Phone display: `text-sm text-neutral-900`, phone number formatted as `(302) 555-1234`
- OTP input: 6 individual `<input maxLength={1}>` cells, each `w-12 h-14 text-center text-xl font-mono border border-neutral-300 rounded-md focus:ring-2 focus:ring-brand-500 focus:border-brand-500`
- Cell gap: `gap-2`
- Container: `flex justify-center gap-2 my-4`
- Submit button: `bg-brand-600 text-white rounded-md px-6 py-2 text-sm font-medium hover:bg-brand-700`
- Timeout warning: `text-xs text-alert-600 mt-2 flex items-center gap-1` with `ClockIcon` (outline, `w-4 h-4`)
- Help text: `text-xs text-neutral-500 mt-2` with `InformationCircleIcon` (outline, `w-4 h-4`)

**OTP input behavior**:
- 6 separate input cells, auto-advance focus to next cell on input
- Backspace on empty cell moves focus to previous cell
- **Paste allowed** (WCAG 2.2 SC 3.3.8 — Accessible Authentication): pasting a 6-digit string fills all cells
- Input type: `text` with `inputMode="numeric" pattern="[0-9]*"` (numeric keyboard on mobile, but allows paste)
- All cells filled → auto-enable submit button

**Timeout warning**:
- `otp_requested_at` from status response
- At T+18h: show warning "⏱ PIN expires in Xh Ym" in `text-alert-600`
- At T+24h: backend transitions back to `quoting` (no re-charge) — the panel disappears, `CarrierQuoteDisplay` re-renders
- Time remaining calculated client-side: `24h - (now - otp_requested_at)`

**Submit behavior**:
- Calls `useSubmitOtp().mutateAsync({ otp_code: "123456" })`
- On success: status → `brand_verified`, panel switches to `ProvisioningStatusIndicator`
- On 400 (OTP rejected): field-level error "PIN rejected by carrier. Check the number and try again." in `text-fault-600`
- On 409 (wrong state): `NotificationBanner` (error) "OTP session expired. Restart setup."
- On 422 (format invalid): field-level error "PIN must be 6 digits."

**Interaction states** (submit button):
| State | Classes |
|---|---|
| Default | `bg-brand-600 text-white` |
| Hover | `hover:bg-brand-700` |
| Focus-visible | `focus-visible:ring-2 focus-visible:ring-brand-500` |
| Active | `bg-brand-700` |
| Disabled | `disabled:opacity-50` (when < 6 digits entered or mutation pending) |

**Accessibility**:
- OTP cells wrapped in `<fieldset>` with `<legend>` "Enter 6-digit PIN"
- Each cell: `<label htmlFor="otp-1" className="sr-only">Digit 1</label>` etc.
- `aria-describedby` on fieldset linking to help text
- Paste explicitly allowed — no `onPaste` prevention
- Target size: each cell is `w-12 h-14` (48×56px) — exceeds WCAG 2.5.8

---

### 4.7 — `ProvisioningStatusIndicator`

**File**: `apps/web/src/components/settings/messaging/ProvisioningStatusIndicator.tsx`

**Purpose**: Visual state machine progress indicator. Shows which steps are done, in-progress, and remaining. Always visible once provisioning has started (status != `not_started`).

**Layout** (horizontal stepper):
```
  ✓         ✓         ●         ○         ○         ○
 Brand → Payment → Verify → Campaign → Number → Active
done      done    in-progress  pending   pending   pending
```

**Steps** (7 total, with sole-prop variant):
| Step # | Label | Standard path | Sole prop path |
|---|---|---|---|
| 1 | Brand | `quoting` → `awaiting_payment` → `brand_submitted` | same |
| 2 | Payment | `awaiting_payment` (done when `brand_submitted` reached) | same |
| 3 | Verify | `brand_verified` (automated for standard) | `awaiting_otp` → `brand_verified` (OTP) |
| 4 | Campaign | `campaign_submitted` | same |
| 5 | Number | `awaiting_number_selection` → `number_assigned` | same |
| 6 | Activate | `number_assigned` (provisioning) | same |
| 7 | Active | `active` | same |

**Pixel specs**:
- Container: `flex items-center justify-between w-full py-4`
- Step circle: `w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium`
  - Done: `bg-margin-100 text-margin-700` with `CheckIcon` (solid, `w-5 h-5`)
  - In-progress: `bg-brand-100 text-brand-700` with `ArrowPathIcon` (outline, `w-4 h-4`, spinning — see animation)
  - Pending: `bg-neutral-100 text-neutral-400` with step number
  - Error: `bg-fault-100 text-fault-600` with `XMarkIcon` (outline, `w-5 h-5`)
- Connector line between steps: `flex-1 h-0.5`
  - Done → next: `bg-margin-400`
  - In-progress → next: `bg-neutral-200`
  - Pending → next: `bg-neutral-200`
- Step label: `text-xs text-neutral-500 mt-1 text-center` (pending), `text-xs text-neutral-900 mt-1 text-center font-medium` (done/in-progress)
- Current step label: `text-xs text-brand-700 mt-1 text-center font-medium`

**Status → step mapping**:
| `status` | Step 1 (Brand) | Step 2 (Payment) | Step 3 (Verify) | Step 4 (Campaign) | Step 5 (Number) | Step 6 (Activate) | Step 7 (Active) |
|---|---|---|---|---|---|---|---|
| `quoting` | in-progress | pending | pending | pending | pending | pending | pending |
| `awaiting_payment` | done | in-progress | pending | pending | pending | pending | pending |
| `brand_submitted` | done | done | in-progress | pending | pending | pending | pending |
| `awaiting_otp` | done | done | in-progress | pending | pending | pending | pending |
| `brand_verified` | done | done | done | in-progress | pending | pending | pending |
| `campaign_submitted` | done | done | done | in-progress | pending | pending | pending |
| `awaiting_number_selection` | done | done | done | done | in-progress | pending | pending |
| `number_assigned` | done | done | done | done | done | in-progress | pending |
| `active` | done | done | done | done | done | done | done |
| `payment_failed` | done | error | pending | pending | pending | pending | pending |
| `brand_rejected` | error | done | pending | pending | pending | pending | pending |
| `campaign_rejected` | done | done | done | error | pending | pending | pending |

**Animation**:
- Spinning `ArrowPathIcon` for in-progress steps: `animate-spin` with `transition: transform 1s linear infinite`
- `@media (prefers-reduced-motion: reduce)` → `animate-spin` disabled, icon static
- Step transition (pending → in-progress): `transition: background-color 200ms ease-in-out, color 200ms ease-in-out`
- `@media (prefers-reduced-motion: reduce)` → no transition (instant color change)

**Props**:
```typescript
interface ProvisioningStatusIndicatorProps {
  status: MessagingStatus;
  entityType: "standard" | "sole_proprietor";
}
```

**Accessibility**:
- Color is not the only signal: done steps have `CheckIcon`, in-progress have spinning `ArrowPathIcon` + "in-progress" text, error steps have `XMarkIcon`
- Container: `<ol role="list" aria-label="Provisioning progress">` with each step as `<li>`
- Each step has `aria-current="step"` when in-progress
- `sr-only` text per step: "Brand registration: complete" / "Brand registration: in progress" / etc.

---

### 4.8 — `ProvisioningErrorPanel`

**File**: `apps/web/src/components/settings/messaging/ProvisioningErrorPanel.tsx`

**Purpose**: Error/retry panel for failed states. Three variants: `payment_failed` (retryable), `rejected` (terminal — contact support), `suspended` (terminal — contact support).

**Layout — `payment_failed` variant**:
```
┌─────────────────────────────────────────────────┐
│  [⚠] Payment Failed                              │  ← ExclamationTriangleIcon, text-fault-600
│                                                  │
│  Your payment could not be processed.            │  ← text-sm text-neutral-900
│  {failure_reason}                                │
│                                                  │
│  No charge was made. You can retry with a        │  ← text-sm text-neutral-500
│  different payment method.                       │
│                                                  │
│  [Try Again]                                     │  ← bg-brand-600
└─────────────────────────────────────────────────┘
```

**Layout — `rejected` variant** (brand_rejected / campaign_rejected):
```
┌─────────────────────────────────────────────────┐
│  [⚠] Registration Rejected                       │  ← ExclamationTriangleIcon, text-fault-600
│                                                  │
│  The carrier rejected your {brand/campaign}      │  ← text-sm text-neutral-900
│  registration.                                   │
│                                                  │
│  Reason: {failure_reason}                        │  ← text-sm text-neutral-700 font-mono
│                                                  │
│  Please contact support to resolve this:         │
│  [Contact Support]                               │  ← border border-brand-600 text-brand-700
└─────────────────────────────────────────────────┘
```

**Layout — `suspended` variant**:
```
┌─────────────────────────────────────────────────┐
│  [⚠] Messaging Suspended                         │
│                                                  │
│  Text messaging has been suspended.              │
│  {failure_reason}                                │
│                                                  │
│  Please contact support to resolve this:         │
│  [Contact Support]                               │
└─────────────────────────────────────────────────┘
```

**Pixel specs**:
- Card: `bg-white rounded-lg border border-fault-200 p-6 space-y-4`
- Header: `flex items-center gap-2 text-h2 font-semibold text-fault-600`
- Icon: `ExclamationTriangleIcon` (outline, `w-6 h-6 text-fault-600`)
- Body text: `text-sm text-neutral-900`
- Reason: `text-sm text-neutral-700 font-mono bg-neutral-50 rounded p-2`
- Retry button: `bg-brand-600 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-brand-700`
- Contact support button: `border border-brand-600 text-brand-700 rounded-md px-4 py-2 text-sm font-medium hover:bg-brand-50`

**`payment_failed` retry behavior**:
- Calls `useRetryProvisioning().mutateAsync()` (`POST /messaging/retry`)
- On success: status → `quoting`, `CarrierQuoteDisplay` re-renders with fresh quote
- On 409: `NotificationBanner` (error) "Cannot retry from current state. Refresh the page."

**Contact support**:
- Links to `mailto:support@pilotfortrades.com?subject=10DLC Registration Issue` (opens email client)
- Or links to the in-app help: `<HelpAnchor>` with `helpContext: { surface: "messaging-error", action: "contact_support" }`

**Interaction states** (retry button):
| State | Classes |
|---|---|
| Default | `bg-brand-600 text-white` |
| Hover | `hover:bg-brand-700` |
| Focus-visible | `focus-visible:ring-2 focus-visible:ring-brand-500` |
| Active | `bg-brand-700` |
| Disabled | `disabled:opacity-50` (during mutation) |

**Props**:
```typescript
interface ProvisioningErrorPanelProps {
  variant: "payment_failed" | "rejected" | "suspended";
  failureReason: string | null;
  onRetry?: () => void;  // for payment_failed variant
}
```

> **Note**: No refund is issued on `brand_rejected` / `campaign_rejected`. Telnyx does not refund Pilot for rejected registrations, so Pilot does not refund the tenant. The panel shows only the rejection reason + "Contact Support" CTA.

**Accessibility**:
- Card has `role="alert"` for the error announcement
- Icon has `aria-label="Warning"` (not hidden from screen readers)
- Color is not the only signal: `ExclamationTriangleIcon` + text label "Payment Failed" / "Registration Rejected" / "Messaging Suspended"

---

### 4.9 — Success State (inline in `MessagingSetupPage`)

When `status === "active"`:

```
┌─────────────────────────────────────────────────┐
│  [✓] Text Messaging is Active                    │  ← CheckCircleIcon (solid), text-margin-600
│                                                  │
│  Your dedicated SMS number is ready.             │  ← text-sm text-neutral-900
│                                                  │
│  Your number: (302) 555-1234                     │  ← text-lg font-medium text-neutral-900
│                                                  │
│  You can now send and receive SMS messages       │  ← text-sm text-neutral-500
│  with customers. Per-message carrier surcharges  │
│  apply (~$0.003/segment).                        │
│                                                  │
│  [Go to SMS Settings]                            │  ← border border-brand-600 text-brand-700
└─────────────────────────────────────────────────┘
```

**Pixel specs**:
- Card: `bg-white rounded-lg border border-margin-200 p-6 space-y-4`
- Header: `flex items-center gap-2 text-h2 font-semibold text-margin-600`
- Icon: `CheckCircleIcon` (solid, `w-6 h-6 text-margin-600`)
- Phone number: `text-lg font-medium text-neutral-900`
- Link button: `border border-brand-600 text-brand-700 rounded-md px-4 py-2 text-sm font-medium hover:bg-brand-50`
- Links to `/settings/communications/sms-compliance` (the existing SMS settings page)

---

### 4.10 — `PhoneNumberSelector`

**File**: `apps/web/src/components/settings/messaging/PhoneNumberSelector.tsx`

**Purpose**: Allows the tenant to search for and select an available phone number from the carrier's inventory. Appears after campaign approval, before number assignment. The tenant can search by area code or city to find a local number.

> **Backend dependency**: This component requires a new backend endpoint `GET /api/v1/tenants/{tenant_id}/messaging/available-numbers?area_code=302&limit=10` that proxies the carrier's available phone number lookup (Telnyx `GET /v2/available_phone_numbers`). It also requires a new state in the provisioning state machine — `awaiting_number_selection` — inserted between `campaign_submitted` (approved) and `number_assigned`. **This must be added to the C-B9 batch design (§D and §F) by the Pilot Architect before the React Engineer starts.** See handoff gate item 5.

**Layout**:
```
┌─────────────────────────────────────────────────┐
│  Choose Your Phone Number                        │  ← text-h2 font-semibold text-neutral-900
│  Select a local number for your SMS messaging.   │  ← text-sm text-neutral-500
│  This is the number customers will see.          │
├─────────────────────────────────────────────────┤
│  Search by area code or city                     │  ← label, text-sm font-medium text-neutral-700
│  [Area code: 302    ] [Search]                   │  ← input + button row
│                                                  │
│  Available Numbers                               │  ← text-sm font-medium text-neutral-700
│  ┌─────────────────────────────────────────┐    │
│  │ ○ (302) 555-1234    Wilmington, DE      │    │  ← radio-selectable rows
│  │ ○ (302) 555-5678    Dover, DE           │    │
│  │ ○ (302) 555-9012    Newark, DE          │    │
│  └─────────────────────────────────────────┘    │
│                                                  │
│  [ℹ] Local numbers build trust with customers.  │  ← bg-neutral-50 border border-neutral-200
│      Toll-free numbers are available on request. │     rounded-md p-3 text-xs text-neutral-600
│                                                  │
│  [Assign This Number]                            │  ← bg-brand-600, disabled until selection
└─────────────────────────────────────────────────┘
```

**Pixel specs**:
- Search row: `flex gap-3 items-end`
- Area code input: `w-32 border border-neutral-200 rounded-md px-3 py-2 text-sm text-neutral-900 focus:ring-2 focus:ring-brand-400 focus:border-transparent`
- Search button: `border border-neutral-300 text-neutral-700 rounded-md px-4 py-2 text-sm font-medium hover:bg-neutral-50`
- Available numbers list: `border border-neutral-200 rounded-md divide-y divide-neutral-100`
- Number row: `flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-neutral-50`
  - Selected: `bg-brand-50 ring-1 ring-brand-500`
  - Radio indicator: `w-5 h-5` `CheckCircleIcon` (solid when selected, outline when not)
- Phone number: `text-sm font-medium text-neutral-900 font-mono`
- City/state: `text-sm text-neutral-500`
- Assign button: `w-full bg-brand-600 text-white rounded-md px-4 py-3 text-sm font-medium hover:bg-brand-700`
- Info callout: `bg-neutral-50 border border-neutral-200 rounded-md p-3 text-xs text-neutral-600` with `InformationCircleIcon` (outline, `w-4 h-4`)

**Interaction states** (number row):
| State | Classes |
|---|---|
| Default | `hover:bg-neutral-50` |
| Hover | `hover:bg-neutral-50` |
| Focus-visible | `focus-visible:ring-2 focus-visible:ring-brand-500` |
| Active (pressed) | `bg-brand-50` |
| Selected | `bg-brand-50 ring-1 ring-brand-500` |

**Interaction states** (assign button):
| State | Classes |
|---|---|
| Default | `bg-brand-600 text-white` |
| Hover | `hover:bg-brand-700` |
| Focus-visible | `focus-visible:ring-2 focus-visible:ring-brand-500` |
| Active | `bg-brand-700` |
| Disabled | `disabled:opacity-50 disabled:cursor-not-allowed` (when no number selected or mutation pending) |

**Behavior**:
- On search: calls `useAvailablePhoneNumbers({ area_code }).refetch()` — queries `GET /messaging/available-numbers?area_code=302&limit=10`
- On select: highlights the row, enables the assign button
- On assign: calls `useAssignPhoneNumber().mutateAsync({ phone_number })` — `POST /messaging/assign-number`
  - On success: status → `number_assigned` → `active` (backend provisions + activates), panel switches to success state
  - On 409: `NotificationBanner` (error) "Number no longer available. Search again."
  - On 500: `NotificationBanner` (error) "Could not assign number. Please try again."

**Data states**:
1. `isPending` (search fetching) → skeleton rows (3 placeholder rows matching number row layout)
2. `isError` → `<ErrorState type="server" title="Could not search numbers" description="..." />` with retry
3. Empty (no results) → `<EmptyState title="No numbers found" description="Try a different area code." />`
4. Populated → list of available numbers

**Props**:
```typescript
interface PhoneNumberSelectorProps {
  onAssigned?: (phoneNumber: string) => void;
}
```

**Accessibility**:
- Number list is a `<fieldset>` with `<legend className="sr-only">Available phone numbers</legend>`
- Each number row is a `<label>` wrapping a radio `<input type="radio" name="phone-number">` + display text
- Target size: each row is `py-3` (~44px height) — meets WCAG 2.5.8
- Color is not the only signal: selected row has `CheckCircleIcon` (solid) + `ring-1 ring-brand-500` + `aria-checked="true"`
- Assign button has `aria-label="Assign selected phone number"` and `aria-disabled` when no selection

---

## 5. Icon Inventory

All icons are [Heroicons 2.0](https://heroicons.com/). No emoji in production UI.

| Component | Icon | Variant | Size | Purpose |
|---|---|---|---|---|
| `EntityTypeSelector` | `CheckCircleIcon` | solid | `w-5 h-5` | Selected radio indicator |
| `EntityTypeSelector` | `CheckCircleIcon` | outline | `w-5 h-5` | Unselected radio indicator |
| `EntityTypeSelector` | `InformationCircleIcon` | outline | `w-5 h-5` | Help text blocks |
| `BrandRegistrationForm` | (none — standard form fields) | — | — | — |
| `CarrierQuoteDisplay` | `InformationCircleIcon` | outline | `w-4 h-4` | Surcharge info callout |
| `CheckoutRedirectButton` | `ArrowRightIcon` | outline | `w-5 h-5` | Continue to payment |
| `OtpEntryPanel` | `DevicePhoneMobileIcon` | outline | `w-5 h-5` | Phone number display |
| `OtpEntryPanel` | `ClockIcon` | outline | `w-4 h-4` | Timeout warning |
| `OtpEntryPanel` | `InformationCircleIcon` | outline | `w-4 h-4` | Help text |
| `ProvisioningStatusIndicator` | `CheckIcon` | solid | `w-5 h-5` | Done step |
| `ProvisioningStatusIndicator` | `ArrowPathIcon` | outline | `w-4 h-4` | In-progress step (spinning) |
| `ProvisioningStatusIndicator` | `XMarkIcon` | outline | `w-5 h-5` | Error step |
| `ProvisioningErrorPanel` | `ExclamationTriangleIcon` | outline | `w-6 h-6` | Error header |
| `PhoneNumberSelector` | `CheckCircleIcon` | solid | `w-5 h-5` | Selected number radio indicator |
| `PhoneNumberSelector` | `CheckCircleIcon` | outline | `w-5 h-5` | Unselected number radio indicator |
| `PhoneNumberSelector` | `InformationCircleIcon` | outline | `w-4 h-4` | Local numbers info callout |
| Success state | `CheckCircleIcon` | solid | `w-6 h-6` | Active header |
| Page header | `HelpAnchor` (from `@pilot/ui`) | — | — | Contextual help |

---

## 6. State Coverage

Every component covers all four data states (§12):

| Component | `isPending` | `isError` | Empty | Populated |
|---|---|---|---|---|
| `MessagingSetupPage` | `<LoadingState>` inline | `<ErrorState>` with retry | 404 → initial panel | State-driven panel |
| `EntityTypeSelector` | N/A (controlled) | N/A | `value=null` (nothing selected) | Selected card highlighted |
| `BrandRegistrationForm` | Submit button disabled | Field errors from RFC 7807 | Empty form (new tenant) | Pre-filled from profile |
| `CarrierQuoteDisplay` | Skeleton (line-item shaped) | `<ErrorState>` with retry | `<EmptyState>` | Full quote |
| `CheckoutRedirectButton` | Button disabled, "Redirecting..." | `NotificationBanner` error | N/A | Enabled |
| `OtpEntryPanel` | Submit disabled | Field error / `NotificationBanner` | Empty cells | 6 digits entered |
| `ProvisioningStatusIndicator` | N/A (pure render from status) | N/A | N/A | Always populated |
| `ProvisioningErrorPanel` | Retry disabled | N/A | N/A | Error details shown |
| `PhoneNumberSelector` | Skeleton rows (3 placeholders) | `<ErrorState>` with retry | `<EmptyState>` "No numbers found" | List of available numbers |

---

## 7. Animation Spec

| Element | Transition | Duration | Easing | Reduced-motion fallback |
|---|---|---|---|---|
| `EntityTypeSelector` card selection | `transition: background-color, border-color` | 150ms | `ease-in-out` | Instant (no transition) |
| `ProvisioningStatusIndicator` in-progress spinner | `animate-spin` (transform rotate) | 1s | `linear` (infinite) | Static icon (no spin) |
| `ProvisioningStatusIndicator` step state change | `transition: background-color, color` | 200ms | `ease-in-out` | Instant |
| `CheckoutRedirectButton` hover | `transition: background-color` | 150ms | `ease-in-out` | Instant |
| `OtpEntryPanel` cell focus | `transition: border-color, box-shadow` | 100ms | `ease-in-out` | Instant |
| `NotificationBanner` (Stripe return) | Slide-in from top | 200ms | `ease-out` | Opacity-only fade |

**All transitions**: `@media (prefers-reduced-motion: reduce)` → disable transition/animation, apply final state instantly. The only exception is opacity-only fade for `NotificationBanner` (still allows a subtle appearance without motion).

---

## 8. §16 Pattern Consumption

| Pattern | How applied in this spec |
|---|---|
| **Always-preview-before-send** (§16.7) | `CarrierQuoteDisplay` shows the full itemized quote before `CheckoutRedirectButton` redirects to Stripe. The tenant sees every cost line (brand, campaign, number) before paying. No "pay first, see costs later." |
| **Optimistic UI with pending badges** (§16.6) | `ProvisioningStatusIndicator` shows spinning `ArrowPathIcon` for in-flight transitions (`brand_submitted`, `campaign_submitted`, `number_assigned`). The `useProvisioningStatus` hook polls every 5s during pending states. `<PendingBadge>` from `@pilot/ui` is available but the stepper's built-in spinner is the primary indicator here. |
| **System-default/tenant-override** (§16.4) | Campaign fields (opt-in keywords, sample messages) are system defaults — the tenant does not customize them. The `BrandRegistrationForm` only collects tenant-specific brand fields. Campaign registration is templated in the service layer (design doc §F.5). No UI for campaign customization. |

---

## 9. RBAC Visibility

| Surface | Permission | Roles | Treatment |
|---|---|---|---|
| `/settings/messaging` page | `settings.view` | owner, office_staff, operator | Page visible |
| `BrandRegistrationForm` (submit) | `settings.manage` | owner | `<RoleGate permission="settings.manage">` wraps the form. Non-owners see read-only display. |
| `CheckoutRedirectButton` | `settings.manage` | owner | Hidden for non-owners via `<RoleGate>` |
| `OtpEntryPanel` (submit) | `settings.manage` | owner | Hidden for non-owners |
| `ProvisioningErrorPanel` (retry) | `settings.manage` | owner | Retry button hidden for non-owners; error message visible |
| `EntityTypeSelector` | `settings.manage` | owner | Hidden for non-owners |
| `PhoneNumberSelector` (assign) | `settings.manage` | owner | Assign button hidden for non-owners; number list visible read-only |

**Note**: The existing `communications/layout.tsx` gates on `["owner", "office_staff"]`. The new `/settings/messaging` route should be gated on `["owner"]` for mutations but `["owner", "office_staff", "operator"]` for viewing. The page-level `RoleGate` allows viewing; individual action components are wrapped in `<RoleGate permission="settings.manage">`.

---

## 10. Responsive Behavior

Primary spec is 1280px+. Notes for reflow:

| Breakpoint | Behavior |
|---|---|
| 1280px+ (primary) | `EntityTypeSelector` cards side-by-side (`grid-cols-2`), form single-column `max-w-2xl`, stepper horizontal full-width |
| 1024px | `EntityTypeSelector` cards side-by-side (narrower), form single-column, stepper horizontal (labels may truncate) |
| 768px | `EntityTypeSelector` cards stack (`grid-cols-1`), form single-column, stepper horizontal with smaller circles (`w-6 h-6`), step labels hidden (show only on current step) |

**No mobile specs** — mobile is React Native (`pilot-voice-ui-designer`). Mobile users are directed to the web dashboard for messaging setup.

---

## 11. Implementation Notes

### 11.1 — TanStack Query hooks (8 new)

| Hook | File | Endpoint | Query/Mutation | Polling |
|---|---|---|---|---|
| `useInitiateProvisioning` | `apps/web/src/features/messaging/hooks/useInitiateProvisioning.ts` | `POST /messaging/provision` | Mutation | — |
| `useCreateCheckout` | `apps/web/src/features/messaging/hooks/useCreateCheckout.ts` | `POST /messaging/checkout` | Mutation | — |
| `useSubmitOtp` | `apps/web/src/features/messaging/hooks/useSubmitOtp.ts` | `POST /messaging/otp` | Mutation | — |
| `useProvisioningStatus` | `apps/web/src/features/messaging/hooks/useProvisioningStatus.ts` | `GET /messaging/status` | Query | `refetchInterval: 5000` when pending, `false` when terminal/interactive |
| `useRetryProvisioning` | `apps/web/src/features/messaging/hooks/useRetryProvisioning.ts` | `POST /messaging/retry` | Mutation | — |
| `useCarrierQuote` | (existing C-B8, reused) | `GET /messaging/quote` | Query | — |
| `useCarrierVerticals` | `apps/web/src/features/messaging/hooks/useCarrierVerticals.ts` | `GET /messaging/verticals` | Query | `staleTime: 3600000` (1h cache — verticals rarely change) |
| `useAvailablePhoneNumbers` | `apps/web/src/features/messaging/hooks/useAvailablePhoneNumbers.ts` | `GET /messaging/available-numbers` | Query | — |
| `useAssignPhoneNumber` | `apps/web/src/features/messaging/hooks/useAssignPhoneNumber.ts` | `POST /messaging/assign-number` | Mutation | — |

**Query keys**:
- `["messaging", "status"]` for `useProvisioningStatus`
- `["messaging", "quote"]` for `useCarrierQuote`
- `["messaging", "verticals"]` for `useCarrierVerticals`
- `["messaging", "available-numbers", areaCode]` for `useAvailablePhoneNumbers`
- `["messaging", "verticals"]` for `useCarrierVerticals`

**Invalidation**: `useInitiateProvisioning` and `useSubmitOtp` and `useRetryProvisioning` invalidate `["messaging", "status"]` on success.

### 11.2 — Money formatting

Amounts arrive as `amount_millicents` (BIGINT, 1 millicent = $0.00001). Display helper:

```typescript
function formatMillicentsAsUSD(millicents: number): string {
  return `$${(millicents / 100000).toFixed(2)}`;
}
function formatMillicentsPerSegment(millicents: number): string {
  return `$${(millicents / 100000).toFixed(3)}/segment`;
}
```

### 11.3 — Stripe Checkout return

On return from Stripe Checkout, the URL contains `?status=paid` or `?status=cancelled`. The `MessagingSetupClient` component:
1. Reads `searchParams.status` on mount
2. Shows `NotificationBanner` (success/warning) with auto-dismiss 5s
3. Calls `router.replace('/settings/messaging')` to clear the param
4. The `useProvisioningStatus` query refetches and shows the current state

### 11.4 — Existing component reuse

| Existing component | Reused as |
|---|---|
| `use10DlcProfile` hook | Pre-fills `BrandRegistrationForm` |
| `LoadingState` from `@pilot/ui/states` | Initial page load |
| `ErrorState` from `@pilot/ui/states` | Status/quote fetch errors |
| `EmptyState` from `@pilot/ui/states` | Empty quote |
| `RoleGate` from `@pilot/ui/role-gate` | RBAC wrapping on action components |
| `NotificationBanner` from `@pilot/ui` | Stripe return + mutation errors |
| `HelpAnchor` from `@pilot/ui` | Page header contextual help |

### 11.5 — MSW handlers

All 5 new endpoints + `/test` twins must be registered in `mocks/handlers/index.ts`. New handler file: `mocks/handlers/messagingProvisioningHandlers.ts`. The existing `dlcHandlers.ts` remains for the profile CRUD endpoints.

### 11.6 — SettingsSidebar update

The `SettingsSidebar.tsx` "Branding" group currently has:
```
{ label: "SMS & 10DLC", href: "/settings/communications/sms-compliance" }
```

**Update**: Add a new sub-item or update the existing one to link to `/settings/messaging`:
```
{ label: "SMS & 10DLC", href: "/settings/communications/sms-compliance" },  // existing — profile view
{ label: "Messaging Setup", href: "/settings/messaging" },                  // new — provisioning wizard
```

Or repoint "SMS & 10DLC" to `/settings/messaging` and keep the profile form accessible from within the messaging setup page. **Recommendation**: Add "Messaging Setup" as a new sub-item under "Branding" — the existing "SMS & 10DLC" remains for profile management.

### 11.7 — Route placement

The design doc §I specifies `apps/web/src/app/(dashboard)/settings/messaging/page.tsx`. However, the existing settings routes live under `(authed)/settings/`. **Use**: `apps/web/src/app/(authed)/settings/messaging/page.tsx` to match the existing route structure. The `(dashboard)` route group does not exist in the current app router.

---

## 12. Accessibility Notes

### 12.1 — Color-independent status

- Every status in `ProvisioningStatusIndicator` pairs color with an icon: done = `CheckIcon` (solid) + `bg-margin-100`, in-progress = spinning `ArrowPathIcon` + `bg-brand-100`, error = `XMarkIcon` + `bg-fault-100`. Color is never the sole signal (WCAG 1.4.1).
- `EntityTypeSelector` selected card has `CheckCircleIcon` (solid) + `ring-2 ring-brand-500` + `aria-checked="true"` — not just a color change.
- `ProvisioningErrorPanel` uses `ExclamationTriangleIcon` + text label "Payment Failed" / "Registration Rejected" — not just red.

### 12.2 — Target sizes

| Element | Size | Meets WCAG 2.5.8 (≥24×24px)? |
|---|---|---|
| `EntityTypeSelector` cards | Full card (~200×120px) | ✅ (exceeds 44×44) |
| `BrandRegistrationForm` submit | `px-4 py-2` (~40px height) | ✅ (width much larger) |
| `CheckoutRedirectButton` | `px-4 py-3` (~44px height) | ✅ |
| `OtpEntryPanel` cells | `w-12 h-14` (48×56px) | ✅ |
| `OtpEntryPanel` submit | `px-6 py-2` (~40px height) | ✅ |
| `ProvisioningErrorPanel` retry | `px-4 py-2` (~40px height) | ✅ |
| `ProvisioningStatusIndicator` circles | `w-8 h-8` (32×32px) | ✅ (decorative, not interactive) |
| `HelpAnchor` "?" | Padded to 24×24px minimum by the component | ✅ |

### 12.3 — Focus order & focus-visible

- All interactive elements use `focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:outline-none` (not `focus:`) per §11.
- Tab order: page header → `ProvisioningStatusIndicator` (not focusable, decorative) → state-driven panel content → action buttons.
- `EntityTypeSelector`: cards are focusable in DOM order (standard first, sole prop second).
- `OtpEntryPanel`: cells tab in order 1→6, then submit button. Auto-advance does not trap focus — user can still Tab/back-tab freely.
- `scroll-margin-top: 2rem` on the page container to prevent the sticky `h-12` header from obscuring focused content (WCAG 2.4.11).

### 12.4 — Form labels & errors

- Every form field has a visible `<label htmlFor="...">` above it (§5 form pattern). No placeholder-as-label.
- Error text: `text-fault-600` + `aria-describedby="{fieldId}-error"` linking error to field.
- Required fields: `*` visual indicator + `aria-required="true"`.

### 12.5 — OTP / Accessible Authentication (WCAG 2.2 SC 3.3.8)

- OTP input allows paste (no `onPaste` prevention). Pasting a 6-digit string fills all cells.
- No memorization puzzle — the PIN is delivered via SMS, not asked from memory.
- `inputMode="numeric"` for mobile keyboard, but `type="text"` to allow paste.

### 12.6 — Consistent help (WCAG 2.2 SC 3.2.6)

- `HelpAnchor` "?" is in the same relative position (top-right of page header) as other settings pages.

### 12.7 — Redundant entry (WCAG 2.2 SC 3.3.7)

- `BrandRegistrationForm` pre-fills from `tenant_10dlc_profile` — does not re-ask for data already entered during signup/onboarding.
- If the tenant navigates away and returns, the form retains its state via the profile query (no data loss).

---

## 13. Component Manifest

| # | File | Type | Description |
|---|---|---|---|
| 1 | `apps/web/src/app/(authed)/settings/messaging/page.tsx` | New | Thin server component — renders `<MessagingSetupClient>`. Metadata: title "Messaging Setup — Pilot". |
| 2 | `apps/web/src/components/settings/messaging/MessagingSetupClient.tsx` | New | Client orchestrator — manages state-driven panel switching, polling, Stripe return handling. |
| 3 | `apps/web/src/components/settings/messaging/EntityTypeSelector.tsx` | New | "Does your business have an EIN?" Yes/No selector with help text. |
| 4 | `apps/web/src/components/settings/messaging/BrandRegistrationForm.tsx` | New | Brand registration form (existing 10dlc_profile fields + new website/stock_symbol/vertical). Pre-fills from `use10DlcProfile`. |
| 5 | `apps/web/src/components/settings/messaging/CarrierQuoteDisplay.tsx` | New | Itemized cost quote display (reuses C-B8 `CarrierQuoteResponse` type). |
| 6 | `apps/web/src/components/settings/messaging/CheckoutRedirectButton.tsx` | New | "Continue to payment" button → Stripe Checkout redirect. |
| 7 | `apps/web/src/components/settings/messaging/OtpEntryPanel.tsx` | New | Sole-prop OTP entry (6-digit input with auto-advance + paste). |
| 8 | `apps/web/src/components/settings/messaging/ProvisioningStatusIndicator.tsx` | New | Horizontal stepper showing 7-step provisioning progress. |
| 9 | `apps/web/src/components/settings/messaging/ProvisioningErrorPanel.tsx` | New | Error/retry panel (3 variants: payment_failed, rejected, suspended). No refund text — Telnyx does not refund Pilot. |
| 10 | `apps/web/src/components/settings/messaging/PhoneNumberSelector.tsx` | New | Phone number search + selection interface. Appears at `awaiting_number_selection` status. |
| 11 | `apps/web/src/features/messaging/hooks/useInitiateProvisioning.ts` | New | TanStack Query mutation — `POST /messaging/provision`. |
| 12 | `apps/web/src/features/messaging/hooks/useCreateCheckout.ts` | New | TanStack Query mutation — `POST /messaging/checkout`. |
| 13 | `apps/web/src/features/messaging/hooks/useSubmitOtp.ts` | New | TanStack Query mutation — `POST /messaging/otp`. |
| 14 | `apps/web/src/features/messaging/hooks/useProvisioningStatus.ts` | New | TanStack Query — `GET /messaging/status` with conditional 5s polling. |
| 15 | `apps/web/src/features/messaging/hooks/useRetryProvisioning.ts` | New | TanStack Query mutation — `POST /messaging/retry`. |
| 16 | `apps/web/src/features/messaging/hooks/useCarrierVerticals.ts` | New | TanStack Query — `GET /messaging/verticals` (1h cache). |
| 17 | `apps/web/src/features/messaging/hooks/useAvailablePhoneNumbers.ts` | New | TanStack Query — `GET /messaging/available-numbers?area_code=X`. |
| 18 | `apps/web/src/features/messaging/hooks/useAssignPhoneNumber.ts` | New | TanStack Query mutation — `POST /messaging/assign-number`. |
| 19 | `apps/web/src/features/messaging/types.ts` | New | Shared types: `MessagingStatus`, `ProvisioningStatus`, `ProvisioningStep`, `AvailablePhoneNumber`, etc. |
| 20 | `apps/web/src/mocks/handlers/messagingProvisioningHandlers.ts` | New | MSW handlers for 7 new endpoints + `/test` twins. |
| 21 | `apps/web/src/mocks/handlers/index.ts` | Modified | Register `messagingProvisioningHandlers`. |
| 22 | `apps/web/src/features/settings/components/SettingsSidebar.tsx` | Modified | Add "Messaging Setup" sub-item under "Branding" linking to `/settings/messaging`. |
| 23 | `apps/web/src/app/(authed)/settings/communications/sms-compliance/page.tsx` | Modified | Add link to `/settings/messaging` ("Go to Messaging Setup") for tenants who need to provision. |

**No new `packages/ui` components** — all new components are web-app-specific (`apps/web/src/components/settings/messaging/`) or feature-specific (`apps/web/src/features/messaging/`). The existing `@pilot/ui` components (`LoadingState`, `ErrorState`, `EmptyState`, `RoleGate`, `NotificationBanner`, `HelpAnchor`) are composed, not duplicated.

---

## 14. Handoff Gate

This spec is ready for Tom's review. Implementation starts only after approval.

**Confirmed items (Tom, 2026-08-05)**:
1. ✅ **Route placement**: `(authed)/settings/messaging/` is correct — matches existing settings route structure.
2. ✅ **SettingsSidebar**: Add "Messaging Setup" as a new sub-item under "Branding" — confirmed.

**Open items for the Pilot Architect to resolve**:
3. **Verticals endpoint** — **Requirement for the Architect**: The `useCarrierVerticals` hook calls `GET /messaging/verticals`. This endpoint is not in the C-B9 design doc §D (which lists 5 endpoints). The Architect must get the Python Engineer to add a 6th endpoint that proxies Telnyx `/enum/vertical` through the carrier-agnostic `SmsCarrier` ABC (do not call Telnyx directly from the frontend — violates the adapter pattern per mvp-arch §17.1). Add to the C-B9 batch design §D and §F before the React Engineer starts.
4. **OTP timeout confirmation** — **Requirement for the Architect**: Confirm that the backend sends `otp_requested_at` in the `GET /messaging/status` response (it does per §D.4) and that 24h is the hard timeout for sole-prop OTP. The Architect must verify this against the Telnyx help center / API docs before the React Engineer implements the countdown.
5. **Phone number selection** — **Requirement for the Architect**: The `PhoneNumberSelector` component (§4.10) requires:
   - A new state `awaiting_number_selection` inserted between `campaign_submitted` (approved) and `number_assigned` in the state machine (§F.1 `VALID_TRANSITIONS`).
   - A new endpoint `GET /messaging/available-numbers?area_code=X&limit=10` that proxies the carrier's available phone number lookup (Telnyx `GET /v2/available_phone_numbers`) through the `SmsCarrier` ABC.
   - A new endpoint `POST /messaging/assign-number` that provisions the selected number via the carrier and transitions to `number_assigned` → `active`.
   - These must be added to the C-B9 batch design (§D, §F) by the Architect before the React Engineer starts. The UI design spec is complete; the backend design must catch up.
