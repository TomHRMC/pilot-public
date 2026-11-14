# C-B9 — Web UI Design Spec: Messaging Setup Page

**Mode**: Pilot Web UI Designer
**Batch**: C-B9 (10DLC Provisioning State Machine)
**Design doc**: `batch-c-b9-design.md` — read §H (Surface Mockup Reference) and §I (Component Manifest) before starting
**Output location**: `dev-docs/architecture-design/batch-designs/batch-c-b9-ui-design-spec.md`
**Platform**: Web dashboard only (`apps/web`) — `/settings/messaging` page

## What to Design

A **Messaging Setup page** at `/settings/messaging` that guides a tenant through the 10DLC provisioning flow — from entity type selection through brand registration, cost quote, Stripe Checkout payment, sole-prop OTP entry (if applicable), and active status.

This page is reached from the post-wizard checklist item "Set up text messaging" (added by C-B5). It replaces the current empty/placeholder messaging settings surface.

## Key Context

1. **Read the C-B9 design doc** `batch-c-b9-design.md` — especially §D (API endpoints), §H (Surface Mockup Reference), and §I (Component Manifest). The component manifest lists 8 components and 6 TanStack Query hooks that the design spec must reconcile with.

2. **The 12-state machine** drives the UI: `not_started → quoting → awaiting_payment → brand_submitted → awaiting_otp (sole prop only) → brand_verified → campaign_submitted → number_assigned → active`. The frontend polls `GET /messaging/status` to determine which panel to show. See §D.4 for the status response shape.

3. **Entity type selector**: "Does your business have an EIN?" → Yes (`standard`) / No (`sole_proprietor`). Inline help text explaining the difference (standard = automated, sole prop = OTP verification loop + ~1,000 msg/day cap).

4. **Brand registration form**: Pre-filled from `tenant_10dlc_profile` if it exists. Fields: legal_business_name, dba_name, ein (required for standard, hidden for sole prop), address fields, support_email, support_phone, **website** (new), **stock_symbol** (new, conditional — only if publicly traded), **vertical** (new, dropdown populated from Telnyx `/enum/vertical` endpoint — do not hardcode values).

5. **Quote display**: Itemized costs from `GET /messaging/quote` (C-B8 endpoint). Each line item visible (brand registration, campaign registration, phone number). "Passed through at cost — Pilot adds no markup" disclosure. Amounts are in **millicents** (1 millicent = $0.00001) — display as dollars with 2 decimal places. Total setup + recurring monthly.

6. **Stripe Checkout redirect**: "Continue to payment" button → calls `POST /messaging/checkout` → redirects to Stripe Checkout URL → returns to `/settings/messaging?status=paid` or `?status=cancelled`.

7. **OTP entry panel** (sole prop only): Appears when status is `awaiting_otp`. "The carrier is texting a PIN to {phone}. Enter it here." Input field + submit button. Timeout warning at T+18h.

8. **Status progress indicator**: Visual state machine progress showing current state + pending states. Should be clear which steps are done, in-progress, and remaining.

9. **Error/retry panel**: On `payment_failed` → "Payment failed. Try again?" button. On `brand_rejected` / `campaign_rejected` → error message + "Contact support" CTA.

10. **Success state**: On `active` → "Text messaging is active. Your number: {phone}." + link to SMS settings.

## §16 Pattern Consumption

| Pattern | How to apply |
|---|---|
| **Always-preview-before-send** (§16.7) | The itemized quote is displayed before the Stripe Checkout redirect — the tenant sees each cost line before paying |
| **Optimistic UI with pending badges** (§16.6) | State machine transitions are async; show pending indicators for in-flight transitions (brand_submitted, campaign_submitted) |
| **System-default/tenant-override** (§16.4) | Campaign fields (opt-in keywords, sample messages) are system defaults — the tenant does not customize them. Brand fields are tenant-specific. |

## Constraints

- **Token-only** — zero hex codes, use `pilotPreset` tokens
- **WCAG 2.2 AA** — color-independent status, ≥24×24px targets, `focus-visible` rings, `prefers-reduced-motion` fallbacks
- **Component-existence check** — confirm against `frontend/packages/ui/src/index.ts` that a component does not already exist before proposing a new one
- **Accessibility Notes subsection required** in the spec
- **Confirm against `frontend/packages/ui/src/index.ts`** that proposed components don't already exist

## Deliverable

A complete UI design spec at `dev-docs/architecture-design/batch-designs/batch-c-b9-ui-design-spec.md` covering:
- All 8 components from the Component Manifest (§I) with props, states, and token usage
- The state-driven panel switching logic (which panel shows for which `status` value)
- The entity type selector interaction
- The brand registration form layout
- The quote display layout
- The OTP entry panel
- The status progress indicator
- Error/retry states
- Accessibility Notes subsection
- The spec must be Tom-approved before the React Engineer prompt is authored
