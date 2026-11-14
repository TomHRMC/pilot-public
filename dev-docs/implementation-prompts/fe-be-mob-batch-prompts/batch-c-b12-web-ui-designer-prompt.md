# Implementation Prompt: C-B12 — Charter Upgrade Forfeiture Modal UI Design Spec

**Mode**: Pilot Web UI Designer
**Batch**: C-B12 (Part B prerequisite — UI design spec must be Tom-approved before React Engineer prompt)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.0 row 14q
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-c-b12-design.md` §H (Surface Mockup Reference), §I (Component Manifest)
**Estimated session**: 1–2 hours
**Platform**: Web only (`apps/web`) — internal authenticated surface (billing settings page)

---

## ⚠️ MANDATORY STOP: Read These First

Before producing any design, read:

- **`.roo/rules-pilot-web-ui-designer/web-app-design-standards.md`** — full document; token rules, component hierarchy, accessibility, output format
- **`.roo/rules-pilot-web-ui-designer/pilot-design-system-reference.md`** — design system reference (badges, severity classes, form patterns)
- **`dev-docs/architecture-design/batch-designs/batch-c-b12-design.md`** — §H (Surface Mockup Reference), §I (Component Manifest), §G (Open Questions Resolved)

Critical rules for this batch:

- **Token-only**: Zero hex codes in the spec. All colors via `pilotPreset` token names (`brand-600`, `fault-600`, `neutral-900`, etc.).
- **Component-existence check**: Read `frontend/packages/ui/src/index.ts` before proposing any new shared component. The forfeiture modal is a domain-specific component (not shared), so it goes in `apps/web/src/features/settings/components/`.
- **§16 pattern**: This modal composes the **always-preview-before-send** pattern (§16.7) — it shows the exact price change before the user confirms. It is also a **destructive confirmation** (forfeiture is irreversible). Do NOT propose a new top-level UX pattern.
- **WCAG 2.2 AA**: Focus trap in modal, ≥24×24px targets, `focus-visible` rings, `prefers-reduced-motion` fallback, color-independent status (the warning is not just red — it has text + icon).
- **Safe default**: The Cancel button ("Keep my Charter rate") is the primary/safe action. The confirm button ("I understand — upgrade to Teams") is the destructive/secondary action. This is per spec §6.7 and Tom's decision.

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before designing:

```
frontend/apps/web/src/features/settings/components/BillingSettingsPage.tsx  ← why: the page where the upgrade CTA + modal will live — understand existing layout, tier picker, RBAC
frontend/apps/web/src/features/settings/hooks/useTenantSubscription.ts      ← why: the hook that provides subscription data (currentTier, charter fields) — understand what data is available
frontend/apps/web/src/features/dashboard/components/CharterMemberBadge.tsx   ← why: the dashboard badge — understand the Charter visual language (brand-700, "Charter Member #N")
frontend/packages/ui/src/index.ts                                            ← why: confirm what shared components exist (NotificationBanner, RoleGate, states)
frontend/apps/web/src/components/operator/cohort/ExtendFreePeriodModal.tsx   ← why: C-B11's preview-before-send modal — pattern reference for the forfeiture modal
frontend/apps/web/src/components/operator/cohort/CloseCohortButton.tsx       ← why: C-B11's destructive confirm modal — pattern reference for safe-default destructive confirmation
```

Also run these to locate related files:

```bash
grep -rn "CharterMemberBadge\|charter_member_number\|price_locked" frontend/apps/web/src/ --include="*.tsx" -l
grep -rn "Modal\|Dialog\|role=\"dialog\"" frontend/apps/web/src/features/settings/ --include="*.tsx" -l
grep -rn "fault-600\|destructive\|confirm" frontend/apps/web/src/components/operator/ --include="*.tsx" -l
```

---

## Background / Context

C-B12 builds the Charter → Teams upgrade flow. The backend (Part A) is complete — `POST /api/v1/tenants/{tenant_id}/subscription/upgrade-from-charter` is live with `billing_interval` (monthly/annual) as the request parameter.

**Tom decision (2026-08-07)**: Charter members can stay on $49/mo forever. When they upgrade to Teams, they become a "regular" customer and choose their billing interval:
- **Monthly**: $179/month
- **Annual**: $149/month effective ($1,788/year)

The Charter rate is gone for good — `charter_eligible = False` permanently, even if they later downgrade.

**Your task**: Produce a UI design spec for two surfaces:
1. **Charter Upgrade CTA** — a button/link on the BillingSettingsPage that opens the forfeiture modal (only visible to Charter members)
2. **CharterUpgradeModal** — a blocking forfeiture warning modal with billing interval selector + safe default

**Forfeiture modal copy** (from design doc §H, per spec §6.7 updated per Tom decision):

> **You'll lose your Charter rate.**
>
> You're on $49/month, locked. Moving to Teams means:
> - **$179/month** if you pay monthly
> - **$149/month** if you pay annually ($1,788/year)
>
> The Charter rate is gone for good — you can't get it back later, even if you move back to Starter.
>
> Billing interval: [ Monthly ] [ Annual ]
>
> [ Keep my Charter rate ]  [ I understand — upgrade to Teams ]

---

## What to Design

### Surface 1: Charter Upgrade CTA on BillingSettingsPage

**Route**: `/settings/billing` (existing page)
**RBAC**: `billing.view` (existing page gate) + the CTA is visible only when `currentTier.tierName === "charter"` and `charter_eligible === true`
**Placement**: In the "Current Plan" card (existing), replace the stale "Upgrade plan" button (currently shown for trial/starter only) with a Charter-specific "Upgrade to Teams" button.

**Design requirements**:
- The CTA button should use `brand-600` background (standard primary action)
- It should be clearly labeled "Upgrade to Teams" (not just "Upgrade plan")
- It should NOT appear for non-Charter members (trial, starter, teams)
- The existing stale tier picker modal (hardcoded "Pro" and "Growth" tiers at lines 137-140 of BillingSettingsPage.tsx) should be removed — it's legacy and wrong. The Charter upgrade flow replaces it.
- For trial/starter members, keep the existing "Upgrade plan" button but note it as a future enhancement (the generic tier picker is out of scope for C-B12 — just remove the stale hardcoded one and leave the button for now)

### Surface 2: CharterUpgradeModal

**Component**: New `CharterUpgradeModal` in `apps/web/src/features/settings/components/CharterUpgradeModal.tsx`
**Trigger**: Opens when the "Upgrade to Teams" CTA is clicked
**Type**: Blocking modal (`role="dialog"`, `aria-modal="true"`, focus trap, Escape to close = safe default)

**Design requirements**:
- **Warning header**: "You'll lose your Charter rate." in `text-h2 font-semibold text-neutral-900`
- **Warning icon**: `ExclamationTriangleIcon` (Heroicons outline, `w-6 h-6`, `text-alert-600`) next to the header
- **Current rate display**: "You're on $49/month, locked." in `text-body text-neutral-700`
- **Teams pricing display**: Two bullet points showing both options:
  - "$179/month if you pay monthly" — `text-body text-neutral-900`
  - "$149/month if you pay annually ($1,788/year)" — `text-body text-neutral-900`
- **Forfeiture warning**: "The Charter rate is gone for good — you can't get it back later, even if you move back to Starter." in `text-body text-fault-600` (with `ExclamationCircleIcon` `w-4 h-4` inline)
- **Billing interval selector**: A segmented control / radio group with two options:
  - "Monthly — $179/mo" (default selected)
  - "Annual — $149/mo (billed $1,788/yr)"
  - Use `role="radiogroup"` with `aria-label="Billing interval"`
  - Selected option: `bg-brand-50 border-brand-500 text-brand-700`
  - Unselected: `bg-white border-neutral-200 text-neutral-700`
  - Target size ≥24×24px for each option
- **Button bar** (bottom of modal):
  - **Primary (safe default)**: "Keep my Charter rate" — `bg-brand-600 text-white` — closes the modal, no action
  - **Secondary (destructive)**: "I understand — upgrade to Teams" — `bg-fault-600 text-white hover:bg-fault-700` — calls the upgrade endpoint
  - Both buttons ≥44px height (WCAG target size)
  - The safe default button is on the LEFT (standard for destructive confirmations)
- **Loading state**: When the upgrade mutation is in flight, the "I understand" button shows "Upgrading…" with `disabled` state + spinner
- **Error state**: If the upgrade fails (e.g., no payment method), show a `NotificationBanner` with `severity="error"` inside the modal above the button bar
- **Success state**: On success, close the modal and show a `NotificationBanner` with `severity="success"` on the billing page ("You're now on the Teams plan.")

**State coverage** (all four data states):
1. **Default**: Modal open, monthly selected, both buttons enabled
2. **Loading**: Upgrade mutation in flight — "I understand" button disabled + spinner
3. **Error**: Upgrade failed — `NotificationBanner` error inside modal
4. **Success**: Brief flash then modal closes + success banner on page

**Interaction states** (all five for each interactive element):
- Billing interval options: default, hover (`hover:border-brand-400`), focus-visible (`focus-visible:ring-2 focus-visible:ring-brand-500`), active (selected), disabled (N/A — always enabled)
- Buttons: default, hover, focus-visible, active, disabled (loading state)

**Animation**:
- Modal open: `transition: opacity 200ms ease-in-out` (fade in backdrop + modal)
- `@media (prefers-reduced-motion: reduce)` → no transition (instant appear)

---

## Output

Produce the design spec at:
```
dev-docs/architecture-design/batch-designs/batch-c-b12-ui-design-spec.md
```

Follow the output format from `web-app-design-standards.md` §8:
1. Surface overview (route, RBAC, who sees it)
2. Pixel specs (dimensions, padding, gap, border-radius for every component)
3. Token-only colors (zero hex codes)
4. Icon inventory (exact Heroicons names)
5. State coverage (loading, empty, error, populated)
6. Interaction spec (hover, focus, active, disabled for every interactive element)
7. Animation spec (with `prefers-reduced-motion` fallback)
8. Component manifest (table of every new/modified file with path + description)
9. Implementation notes (hook names, query keys, endpoint URLs)
10. **Accessibility Notes** subsection (color-independent status, target sizes, focus order, modal focus-trap/return)

**Component manifest** (from design doc §I — reconcile with your spec):

| Component | Destination | Purpose |
|---|---|---|
| `CharterUpgradeModal` | `apps/web/src/features/settings/components/CharterUpgradeModal.tsx` (NEW) | Blocking forfeiture warning modal with billing interval selector + safe default |
| `BillingSettingsPage` (updated) | `apps/web/src/features/settings/components/BillingSettingsPage.tsx` | Add "Upgrade to Teams" CTA for Charter members; remove stale tier picker |

---

## Handoff Gate

After producing the design spec, **STOP**. Do NOT implement any code. The design spec goes to Tom for approval. Implementation starts only after Tom confirms the spec is approved. State this explicitly at the end of the design spec output.

The React Engineer prompt (C-B12 Part B) will be authored only after Tom approves this spec.
