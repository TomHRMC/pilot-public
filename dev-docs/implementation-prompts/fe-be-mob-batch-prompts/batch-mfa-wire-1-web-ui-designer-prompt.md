# Implementation Prompt: MFA-WIRE-1 — Web MFA Method Cards + Remove Flow UI Design Spec

**Mode**: Pilot Web UI Designer (`pilot-web-ui-designer`)
**Batch**: MFA-WIRE-1 (Part B prerequisite — this spec must be Tom-approved before the React Engineer prompt is authored; Architect Rule §1.5)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.0 row 6 + §2.3 MFA-WIRE-1 card
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-mfa-wire-1-design.md` v1.1 ✅ APPROVED 2026-08-16 — §C step 3 (this task), §D (endpoint contracts), §E (pattern reuse), §F.3 (error map), §G (open questions), §H (surfaces), §I (component manifest), DoD
**Estimated session**: 1.5–2 hours
**Platform**: Web only (`apps/web`) — internal authenticated settings surfaces
**Spec output**: `dev-docs/architecture-design/batch-designs/batch-mfa-wire-1-web-ui-design-spec.md`

---

## ⚠️ MANDATORY STOP: Read These First

- **`.roo/rules-pilot-web-ui-designer/web-app-design-standards.md`** — full document; token rules (§3), icons (§5), component hierarchy (§6), output format (§8), WCAG 2.2 AA (§10), five interaction states + reduced motion (§11), data-state awareness (§12)
- **`.roo/rules-pilot-web-ui-designer/pilot-design-system-reference.md`** — form patterns (§5), modal patterns (§7), RBAC visibility (§8)
- **The design doc** — read §D.1–D.4 (what the backend actually returns now), §F.3 (the eight error codes you are speccing copy for), §G-Q1/Q2/Q7, §H, §I, and the DoD

Critical rules for this batch:

- **Token-only** — zero hex codes; all colors via `pilotPreset` token names.
- **Component-existence check** — read `frontend/packages/ui/src/index.ts` before proposing anything new. `MFAEnrollmentWizard` exists and its **interface is LOCKED** (FE-B12 export block: "INTERFACES LOCKED after FE-B12 ships"). The `allowedPaths` prop already exists. You compose and constrain — you do not change wizard props.
- **§16 composition, no new top-level UX** — the Remove flow consumes **optimistic UI** (§16.8: optimistic remove + rollback on non-204) and **409-and-refresh** for the last-method guard. Compose `PendingBadge` / `NotificationBanner` from `@pilot/ui` where they fit; do not invent new patterns.
- **WCAG 2.2 AA §10 Accessible Authentication is directly in scope** — every OTP/code input in the spec must be explicitly marked "paste allowed" (no memorization puzzles). Focus-visible rings, ≥24×24px targets, `prefers-reduced-motion` fallbacks, color-independent status.
- **Rule 9.4 — no "coming soon" strings.** Email MFA is deferred (design §G-Q2: pool has TOTP+SMS only). The email method is simply **absent** from every chooser — never rendered disabled, never teased.

---

## Pre-Work: Read These Source Files

```
frontend/apps/web/src/app/(authed)/settings/my-account/security/mfa/page.tsx          ← why: the surface being redesigned. Note: raw text summary ("Enrolled: totp, sms"), ALL_MFA_METHODS currently includes "email" (being constrained), wizard embedded in voluntary mode
frontend/apps/web/src/app/(authed)/settings/my-account/security/mfa/enroll/page.tsx   ← why: the force-flow variant (?mfa_required=1&grace_days=N) — same allowedPaths constraint applies
frontend/packages/ui/src/mfa-enrollment-wizard/web/MFAEnrollmentWizard.tsx            ← why: the locked wizard — understand its steps, where allowedPaths filters the chooser, where errors render today, and the existing DLC-2 SMS disclosure (testID sms-consent-disclosure — must be preserved)
frontend/packages/ui/src/mfa-enrollment-wizard/types.ts                               ← why: exact prop names + MFAEnrollmentPath type ("totp" | "sms" | "email") + step enums you are constraining to
frontend/apps/web/src/features/account-settings/components/SecurityIndexPage.tsx      ← why: upstream nav card showing method count — unchanged by this spec, but copy/visuals must stay consistent
frontend/apps/web/src/features/login/components/MfaChallengeStep.tsx                  ← why: the login-time challenge (FE-B2) — copy reference only ("Enter the code from your authenticator app." / "…sent to your phone."); NOT redesigned here
frontend/packages/ui/src/index.ts                                                     ← why: barrel — confirm PendingBadge / NotificationBanner / states exist before composing them
```

Also run:

```bash
grep -rn "allowedPaths" frontend/packages/ui/src/mfa-enrollment-wizard/ --include="*.tsx" --include="*.ts" -l
grep -rn "last_method_required\|mfa-status" frontend/apps/web/src --include="*.tsx" --include="*.ts" -l
```

---

## Background / Context

MFA-WIRE-1 wires the mocked MFA enrollment flow to real Cognito. **Step 0 (DevOps) and Part A (backend) are complete.** What changed for the UI:

1. **`GET /api/v1/users/me/mfa-status` gained an additive `methods[]` array** (design §D.4):

```jsonc
{
  "enrolled_methods": ["totp"],           // kept — mobile consumes it; do not design against it for new UI
  "methods": [
    { "method_id": "uuid", "method_type": "totp",
      "enrolled_at": "2026-08-17T…", "last_used_at": null,
      "destination_masked": null }         // SMS rows carry e.g. "•••0001"
  ],
  "tenant_policy_required": false, "grace_period_active": false,
  "grace_ends_at": null, "enforcement_activated": false
}
```

`last_used_at` is always null this batch (Cognito owns challenge telemetry) — the spec must decide whether to show "Never used"/"—" or omit the field; either is acceptable, state the choice.

2. **`DELETE /me/mfa/methods/{method_id}` is live** with real semantics (design §D.3): 204 on success (Cognito factor disabled + row deleted); **409 `last_method_required`** when the tenant policy requires MFA and this is the user's last method; **502 `cognito_unavailable`** on Cognito failure — in which case the row is *retained* (the card must stay on rollback).

3. **The eight RFC 7807 error codes** (design §F.3) need designed copy + placement:

| HTTP | `code` | Surfaces where it can appear |
|---|---|---|
| 400 | `mfa_access_token_required` | any mutation (session edge) |
| 401 | `mfa_access_token_invalid` | any mutation (stale session → re-sign-in nudge) |
| 400 | `mfa_code_invalid` | verify step |
| 400 | `mfa_code_expired` | verify step (pair with resend affordance) |
| 400 | `email_mfa_not_available` | unreachable in UI (email hidden) — no copy needed |
| 400 | `phone_number_required` / `phone_number_invalid` | SMS enroll-start |
| 503 | `sms_delivery_not_configured` | SMS enroll-start — **SMS delivery is not yet live** (AWS Support case pending, ADR-0015) |
| 502 | `cognito_unavailable` | any mutation |

The **503 `sms_delivery_not_configured`** state matters: until the AWS Support case resolves, SMS enroll-start fails with it. The spec must present this as a dignified inline notice — "Text-message setup is temporarily unavailable — use an authenticator app" with a TOTP nudge — **never** a silent failure and never a fake success (DoD 2).

4. **Email is deferred** (§G-Q2): `allowedPaths={["totp","sms"]}` on both pages; the page's `ALL_MFA_METHODS` drops `"email"`.

5. **`fetch`→`apiClient` migration is PLAT-DEBT** (§G-Q7) — not this batch; the wizard's helper only gains the `X-Cognito-Access-Token` header. No design impact, but do not spec anything that assumes an apiClient refactor.

---

## What to Design

### Surface 1 — Method cards + Remove flow on `/settings/my-account/security/mfa`

**Route**: `/settings/my-account/security/mfa` (existing page — redesign the summary area)
**RBAC**: self-service (`mfa.enroll_self` / `mfa.reset_self`) — every authenticated user manages their own MFA; **no RoleGate** on cards. Note the tenant-policy context instead (below).

Replace the raw "Enrolled: totp, sms" text block with a **method-card list** consuming `methods[]`:

- **Card anatomy** (spec exact pixel dims, padding, gap, radius per rules §8.2):
  - Leading icon: `ShieldCheckIcon` (Heroicons outline) for TOTP, label "Authenticator app"; `DevicePhoneMobileIcon` (outline) for SMS, label "Text message"
  - Secondary line: SMS → `destination_masked`; both → enrolled date (spec the date format, e.g. "Enrolled Aug 17, 2026")
  - Trailing **Remove** action — destructive-styled text button (`text-fault-600`), ≥24×24px hit area (prefer 44×44px), `focus-visible` ring
- **Remove flow**: click Remove → destructive confirm modal per design-system §7 (safe default = "Keep method" as the focused/primary-style button; confirm = "Remove method" `bg-fault-600`) → on confirm: **optimistic remove** (card disappears, `PendingBadge` or equivalent pending treatment per §16.8) → non-204 → rollback (card returns) + error banner
- **409 `last_method_required`** → compose 409-and-refresh: toast/`NotificationBanner` — "Your organization requires MFA. Add another method before removing this one." — and refresh the status query. This state only occurs when `tenant_policy_required` is true.
- **502 `cognito_unavailable`** → error banner ("We couldn't reach the authentication service — your method was NOT removed. Try again."), card stays.
- **Tenant-policy context**: when `tenant_policy_required` (and/or `grace_period_active`), spec a compact info banner above the cards (`bg-alert-50 border-alert-200 text-alert-700` + text label — color is never the only signal) telling the user MFA is required by their organization, with `grace_ends_at` when present.
- **Empty state**: zero methods → keep/refresh the existing empty copy + Add CTA + the DLC-2 SMS disclosure block (do not drop it).
- **Add-method chooser**: exactly two options — Authenticator app, Text message. Hide the Add button when both are enrolled (the `ALL_MFA_METHODS` = `["totp","sms"]` change).
- **Four data states** per rules §12: `isPending` → skeleton matching the card layout (not a bare spinner); `isError` → `ErrorState` with retry; empty; populated.
- Pass `allowedPaths={["totp","sms"]}` to the wizard on **both** this page and the force-flow page (call it out in implementation notes — it's a one-line prop change the React Engineer makes).

### Surface 2 — Force-flow page `/settings/my-account/security/mfa/enroll`

Same `allowedPaths` constraint; `forceFlow={true}` already removes cancel. Spec only what changes (chooser now shows two methods) + the force-flow context copy ("your organization requires MFA — enrollment is not optional" tone vs. the voluntary page). Reference the existing `MfaEnrollmentRequiredGate` for tone consistency.

### Surface 3 — Wizard internal error states (copy + placement table)

The wizard steps themselves are **not** being visually redesigned. Your deliverable here is a copy + presentation table for each §F.3 error: inline field error (`text-fault-600` + `aria-describedby`) vs. top-of-wizard banner, per four-class severity. Verify-step code inputs: **"paste allowed"** explicitly (WCAG 2.2 SC 3.3.8). `mfa_code_expired` pairs with the existing resend path. `phone_number_required` directs the user to add a phone number on their profile (note the destination — check `SecurityIndexPage`/profile routes and name it).

---

## Output Requirements

Write the spec to `dev-docs/architecture-design/batch-designs/batch-mfa-wire-1-web-ui-design-spec.md` following rules §8 in full (surface overview w/ RBAC, pixel specs, token-only colors, Heroicons inventory, state coverage, interaction spec, animation spec w/ reduced-motion fallbacks, **component manifest**, implementation notes) **plus the §10 Accessibility Notes subsection** (color-independent status, target sizes, focus order + focus-visible, modal focus-trap/return — the Remove confirm modal needs explicit focus-trap + focus-return-to-Remove-button behavior).

**Component manifest reconciliation** (Architect Rule §1.5.4): the method-card list is **surface-scoped** — inside the existing `mfa/page.tsx` or `apps/web/src/features/account-settings/components/` if you split it. It is **not** a new `packages/ui` export (design §I). Your manifest must reconcile exactly with design §I — no orphan components, no new shared exports.

## Handoff Gate (Rule §9 / Architect §1.5.5)

After producing the spec, **STOP**. Do not implement code. The spec goes to Tom for approval; Part B (React Engineer) is authored only after Tom approves. State this explicitly at the end of the spec.
