# UI Design Spec Prompt: C-B5 — Wizard Step 4/5 + Checklist + Badge

**Mode**: Pilot Web UI Designer  
**Batch**: C-B5  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-c-b5-design.md` — read §H (Surface Mockup Reference) and §I (Component Manifest)  
**Output**: `dev-docs/architecture-design/batch-designs/batch-c-b5-ui-design-spec.md`

---

## What to Design

Four surfaces for the Charter program signup flow. All are web dashboard (`apps/web`) surfaces — no mobile.

### 1. Wizard Step 4 — Charter Tier Card

The tier selection screen shows only active tiers. During Charter, that's exactly one option. The card must communicate:
- Tier name: "Charter"
- Price: "$49/month"
- Free period: "Free for 90 days. No card needed." (plain language from `free_period_days`)
- The `charter_member_number` is NOT shown here (assigned server-side, shown later on dashboard)

**Existing code to reference**: `apps/web/src/features/signup/` — find the current step 4 tier picker component.

### 2. Wizard Step 5 — Payment / Confirmation (Two Branches)

Branch on `requires_payment_method` (returned by `GET /signup/{id}/state`):

- **`requires_payment_method = true`** (non-Charter): existing Stripe Elements payment form — unchanged, just made conditional
- **`requires_payment_method = false`** (Charter): skip payment entirely, show confirmation copy: *"You're set. No charge until {free_period_ends_at}."* with a "Complete Signup" button

The Elements component is **retained and made conditional**, not removed. Flipping the flag re-enables it with no code change.

### 3. Onboarding Checklist — "Set up text messaging" Item

Add a new item to the existing pinned setup-checklist widget:
- Label: "Set up text messaging"
- Links to the 10DLC flow (C-B9 — not yet built, so link can be a placeholder route)
- Cost disclosure inline: *"Carrier registration runs about $13–$37 depending on your business setup. That goes to the phone carrier — we don't take any of it."*
- Charter-only: only displayed when the tenant is on the Charter tier (conditional render)

**Existing code to reference**: `apps/web/src/features/onboarding/` — find the current checklist widget component.

### 4. Charter Member Badge — Owner-Only Dashboard Badge

A small badge/pill component shown on the dashboard:
- Text: "Charter Member #N" (where N = `charter_member_number`)
- **Owner-only RBAC**: visible only to the tenant owner, not to employees/techs
- Always renders the *current* `free_period_ends_at` as a date nearby (e.g., "Free until Aug 14, 2026"), never a countdown

**Q#5 resolved**: badge is owner-only. Gate with `<RoleGate permission="...">` or equivalent RBAC check.

---

## Reference Docs to Read

Before designing, read:

1. **`dev-docs/architecture-design/batch-designs/batch-c-b5-design.md`** — §H (Surface Mockup Reference) + §I (Component Manifest) — the Architect's scope and component list
2. **`dev-docs/marketing-analysis/pilot-tech-impl-spec-v1.md`** §7.1-7.2 — the spec's wizard + checklist requirements
3. **`dev-docs/architecture-design/mvp-arch.md`** §16 — locked platform patterns (compose these, don't invent new top-level UX)
4. **Existing signup wizard code**: `apps/web/src/features/signup/` — understand the current step 4/5 components before designing changes
5. **Existing onboarding checklist**: `apps/web/src/features/onboarding/` — understand the current checklist widget before adding the messaging item
6. **`frontend/packages/ui/src/index.ts`** — check if `Badge`, `Pill`, `RoleGate` already exist before proposing new components

---

## Design Constraints

- **Token-only**: zero hex codes — use `pilotPreset` tokens from the existing design system
- **WCAG 2.2 AA**: color-independent status, ≥24×24px targets, `focus-visible` rings, `prefers-reduced-motion` fallbacks
- **§16 pattern composition**: use existing patterns (optimistic UI, system-default/tenant-override, 409-and-refresh) — don't invent new top-level UX
- **Component-existence check**: verify against `frontend/packages/ui/src/index.ts` before proposing new components. The badge may be composable from existing `Badge`/`Pill` primitives.
- **Accessibility Notes subsection required** in the spec

---

## Output

Write the design spec to: `dev-docs/architecture-design/batch-designs/batch-c-b5-ui-design-spec.md`

The spec is **Tom-gated** — implementation (React Engineer) begins only on Tom's approval.
