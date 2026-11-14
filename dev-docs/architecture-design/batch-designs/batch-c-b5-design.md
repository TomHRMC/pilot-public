# C-B5 — Wizard Step 4/5 Conditional Logic + Cohort Cap + Checklist Item

**Batch**: C-B5
**Mode**: Pilot Python Engineer (Part A) + Pilot React Engineer (Part B)
**Prerequisite**: C-B4 ✅ (Stripe subscription creation + `create_charter_subscription()`)
**Source of truth**: `pilot-tech-impl-spec-v1.md` §4.1-4.3, §7.1-7.2
**Status**: Design complete — ready for prompt authoring
**Date**: August 4, 2026

---

## Overview

C-B5 wires the Charter subscription lifecycle into the signup wizard. Three changes:

1. **Step 4 (tier selection)**: On Charter tier selection, compute `free_period_ends_at`, assign `charter_member_number` with `signup_cap` enforcement (row lock + `is_active` flip), create Stripe Customer + Charter Subscription
2. **Step 5 (payment/confirmation)**: Branch on `requires_payment_method` — if false (Charter), skip Stripe Elements and go straight to confirmation
3. **Post-wizard checklist**: Add "Set up text messaging" item to the onboarding checklist (Charter-only, with cost disclosure)

This is a **mixed batch**: Part A (Python Engineer) runs first, Part B (React Engineer) runs after `pnpm sync-api-types`.

---

## A. Input Read Summary

| Input | Sections read | Key takeaways |
|---|---|---|
| `pilot-tech-impl-spec-v1.md` | §4.1 (free_period_ends_at), §4.2 (requires_payment_method), §4.3 (signup_cap), §7.1 (wizard changes), §7.2 (checklist item) | Step 4: persist `free_period_ends_at` + assign `charter_member_number` + enforce `signup_cap` in one transaction + create Stripe Customer + Subscription. Step 5: branch on `requires_payment_method`. Checklist: add "Set up text messaging" with cost disclosure. |
| `tenant_signup.py` | `_process_step_data()` lines 289-402 | Step 4 currently only sets `tenant.current_subscription_tier_id`. Step 5 calls `activate_trial()`. Both need expansion. |
| `signup.py` | Full file | Routes: POST /signup (step 1), PUT /step2-5, GET /state. Step 4 route = `advance_signup_step5()` (confusing naming — advances FROM step4_tier TO step5_confirm). |
| `onboarding_checklist.py` | Full file | Checklist has: account_created, legal_accepted, tier_selected, first_customer_added, catalog_setup, quickbooks_connected, calendar_connected, team_invited. No messaging item. |
| `onboarding.py` | Full file (107 lines) | `TenantOnboardingChecklist` model — `StandardAuditMixin`, PK=tenant_id. No `messaging_setup` column. |
| `stripe_subscriptions.py` | C-B4 functions | `create_stripe_customer()` + `create_charter_subscription()` exist (C-B4 ✅). |
| Live DB — `subscription_tier` | MCP query | Charter: `free_period_days=90`, `requires_payment_method=false`, `signup_cap=12`, `price_locked=true`, `is_active=true` |
| Live DB — `tenant` | MCP query | `free_period_ends_at`, `charter_member_number` (UNIQUE), `charter_eligible` columns exist (C-B2) |
| Live DB — `tenant_onboarding_checklist` | MCP query | 20 columns — no `messaging_setup` column. Migration needed. |
| Q#5 resolution | Spec appendix | Badge is **owner-only** — gated to owner RBAC in the frontend. |

---

## B. Migration Plan

**One migration required** — add `messaging_setup` column to `tenant_onboarding_checklist`.

### Pre-migration state (verified via MCP)

```sql
-- Current columns on tenant_onboarding_checklist (20 columns, no messaging_setup)
SELECT column_name FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'tenant_onboarding_checklist'
ORDER BY ordinal_position;
```

### Migration: Add `messaging_setup` column

```sql
-- Alembic blank migration
def upgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.add_column(
        'tenant_onboarding_checklist',
        sa.Column('messaging_setup', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    )
    op.execute("SET LOCAL session_replication_role = 'origin';")

def downgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")
    op.drop_column('tenant_onboarding_checklist', 'messaging_setup')
    op.execute("SET LOCAL session_replication_role = 'origin';")
```

**NOT NULL with server_default=false** — existing rows get `false`. No backfill needed (single-step, safe for existing data).

### Seed Data Rollout

- **Layer 1 (core/platform)**: No seed change — `messaging_setup` defaults to `false` on all existing and new tenants. The checklist `ensure_checklist_exists()` function will pick it up automatically via the model.
- **Layer 2 (scenario)**: No scenario seed change — the column is a runtime state flag, not display data.

---

## C. Execution Order

### Part A — Backend (Python Engineer)

| # | Task | File(s) |
|---|---|---|
| 1 | Alembic migration: add `messaging_setup` column to `tenant_onboarding_checklist` | `backend/migrations/versions/` |
| 2 | Update `TenantOnboardingChecklist` model: add `messaging_setup` field | `backend/app/models/onboarding.py` |
| 3 | Update `OnboardingChecklistResponse` schema: add `messaging_setup` field | `backend/api/routes/onboarding_checklist.py` |
| 4 | Update `_get_checklist_impl()`: include `messaging_setup` in response | `backend/api/routes/onboarding_checklist.py` |
| 5 | Update `_process_step_data()` step4_tier handler: add `free_period_ends_at` computation, `charter_member_number` assignment + `signup_cap` enforcement (row lock), Stripe Customer + Subscription creation | `backend/services/tenant_signup.py` |
| 6 | Update `_process_step_data()` step5_confirm handler: branch on `requires_payment_method` — if false, skip trial activation (Charter uses Stripe trial, not the old trial system) | `backend/services/tenant_signup.py` |
| 7 | Update `get_signup_state()`: return `free_period_ends_at` + `requires_payment_method` + `charter_member_number` in `collected_data` | `backend/services/tenant_signup.py` |
| 8 | Write unit tests for step4_tier cohort cap + Stripe creation | `backend/tests/domains/identity_access/` |
| 9 | Write unit tests for step5_confirm conditional branching | `backend/tests/domains/identity_access/` |
| 10 | Write unit tests for checklist `messaging_setup` field | `backend/tests/domains/platform_infrastructure/` |
| 11 | Run `python export_openapi_json.py` | `backend/openapi.json` |
| 12 | Run `python generate_db_model_map.py app > db_models_map.md` | `backend/db_models_map.md` |
| 13 | Run ruff + full test suite (Phase 2) | — |

### Part B — Frontend (React Engineer)

| # | Task | File(s) |
|---|---|---|
| 1 | `pnpm sync-api-types` — get updated OpenAPI types | `packages/shared-types/` |
| 2 | Update signup wizard step 4: render `free_period_days` in plain language ("Free for 90 days. No card needed.") | `apps/web/src/features/signup/` |
| 3 | Update signup wizard step 5: branch on `requires_payment_method` — if false, skip Stripe Elements, show confirmation copy | `apps/web/src/features/signup/` |
| 4 | Add "Set up text messaging" checklist item (Charter-only, with cost disclosure) | `apps/web/src/features/onboarding/` |
| 5 | Add Charter Member badge component (owner-only RBAC, shows `charter_member_number`) | `apps/web/src/features/dashboard/` |
| 6 | Write web tests | `apps/web/src/features/` |
| 7 | Run `pnpm --filter pilot-web test` | — |

---

## D. New API Endpoints

**No new endpoints.** C-B5 modifies existing endpoints:
- `PUT /api/v1/signup/{tenant_id}/step4` — now creates Stripe Customer + Subscription (via `create_charter_subscription()` from C-B4)
- `PUT /api/v1/signup/{tenant_id}/step5` — now branches on `requires_payment_method`
- `GET /api/v1/signup/{tenant_id}/state` — now returns `free_period_ends_at`, `requires_payment_method`, `charter_member_number`
- `GET /api/v1/tenants/{tenant_id}/onboarding/checklist` — now includes `messaging_setup` field

---

## E. Pattern Reuse Decisions

| Pattern | How it applies |
|---|---|
| **Cohort cap transaction** (spec §4.3) | `SELECT ... FOR UPDATE` on the tier row, assign `charter_member_number = count + 1`, if `count + 1 >= signup_cap` set `is_active = false` — all in the same transaction as the step4 advance. Race-free. |
| **409-and-refresh** (§16) | The existing wizard staleness guard (409 if DB state != expected state) is unchanged. |
| **System-default/tenant-override** (§16) | `requires_payment_method` is a tier-level default, not a tenant override. The wizard reads it from the tier to decide step 5 behavior. |
| **Optimistic UI** (§16) | Step 4 shows "Free for 90 days. No card needed." immediately on tier selection — no loading state needed since the tier data is already fetched. |
| **Idempotency** (§16) | The step4 handler must be idempotent — if the wizard is re-submitted (e.g., user hits back then forward), don't create a second Stripe Customer or assign a second `charter_member_number`. Check if `tenant.stripe_customer_id` already exists before creating. |
| **Sync routes** (Rule §21) | All changes are in existing `def` functions — no `async def` conversions. |

---

## F. Shared Module Interfaces

### services/tenant_signup.py — Updated `_process_step_data()` step4_tier handler

```python
elif current_state == "step4_tier":
    selected_tier_id = step_data.get("selected_tier_id")
    if not selected_tier_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="selected_tier_id is required for step 4",
        )

    # Lock the tier row for the cohort cap transaction
    tier = db.exec(
        select(SubscriptionTier)
        .where(SubscriptionTier.tier_id == selected_tier_id)
        .with_for_update()  # SELECT ... FOR UPDATE
    ).first()

    if not tier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Selected tier not found",
        )

    if not tier.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "type": "https://pilotfortrades.com/errors/tier-closed",
                "title": "Tier no longer available",
                "status": 409,
                "detail": "This tier has reached its signup cap and is no longer accepting new members.",
            },
        )

    tenant = db.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    # Set tier
    tenant.current_subscription_tier_id = tier.tier_id

    # Compute free_period_ends_at if the tier has a free period
    if tier.free_period_days and not tenant.free_period_ends_at:
        from datetime import UTC, datetime, timedelta
        tenant.free_period_ends_at = datetime.now(UTC) + timedelta(days=tier.free_period_days)

    # Assign charter_member_number if this is a charter tier (idempotent)
    if tier.tier_name == "charter" and not tenant.charter_member_number:
        # Count existing charter members
        from sqlalchemy import func
        existing_count = db.exec(
            select(func.count(Tenant.id))
            .where(Tenant.charter_member_number.isnot(None))
        ).one()
        tenant.charter_member_number = existing_count + 1

        # Enforce signup_cap — flip is_active if cap reached
        if tier.signup_cap and tenant.charter_member_number >= tier.signup_cap:
            tier.is_active = False
            db.add(tier)

    db.add(tenant)

    # Create Stripe Customer + Subscription (idempotent — check if already exists)
    if not tenant.stripe_customer_id:
        from services.stripe_subscriptions import create_stripe_customer, create_charter_subscription

        # Get billing email from signup
        billing_email = signup.owner_email
        stripe_customer_id = create_stripe_customer(db, tenant_id, billing_email)
        tenant.stripe_customer_id = stripe_customer_id
        db.add(tenant)

        # Create Charter subscription (only for charter tier)
        if tier.tier_name == "charter" and tenant.free_period_ends_at:
            create_charter_subscription(
                db=db,
                tenant_id=tenant_id,
                stripe_customer_id=stripe_customer_id,
                free_period_ends_at=tenant.free_period_ends_at,
                charter_member_number=tenant.charter_member_number,
            )
```

### services/tenant_signup.py — Updated step5_confirm handler

```python
elif current_state == "step5_confirm":
    if step_data.get("confirmed"):
        tenant = db.exec(select(Tenant).where(Tenant.id == tenant_id)).first()
        if tenant:
            # Get the selected tier
            from app.models.subscription import SubscriptionTier
            tier = db.exec(
                select(SubscriptionTier).where(
                    SubscriptionTier.tier_id == tenant.current_subscription_tier_id
                )
            ).first()

            if tier and tier.requires_payment_method:
                # Non-Charter: activate trial (old behavior)
                user_id = step_data.get("user_id")
                if user_id:
                    from services.trial_management import activate_trial
                    activate_trial(db, tenant_id, user_id)
            else:
                # Charter: trial is handled by Stripe (trial_end).
                # No trial activation needed — the Stripe subscription
                # was created in step 4 with trial_end = free_period_ends_at.
                # Just mark the onboarding checklist tier_selected = true.
                from services.onboarding_service import ensure_checklist_exists
                checklist = ensure_checklist_exists(db, tenant_id)
                checklist.tier_selected = True
                db.add(checklist)
```

### services/tenant_signup.py — Updated `get_signup_state()`

Add to the `collected_data` dict:

```python
"free_period_ends_at": (
    tenant.free_period_ends_at.isoformat()
    if tenant and tenant.free_period_ends_at
    else None
),
"requires_payment_method": (
    tier.requires_payment_method
    if tier
    else True  # default to true (safe)
),
"charter_member_number": (
    tenant.charter_member_number
    if tenant and tenant.charter_member_number
    else None
),
```

---

## G. Open Questions Resolved

| Question | Resolution | Source |
|---|---|---|
| **Q#5**: Should `charter_member_number` badge be visible to employees or owner-only? | **Owner-only.** The badge component is gated to owner RBAC in the frontend. | Spec appendix Q#5 |
| **Idempotency on step 4 re-submit** | Check `tenant.stripe_customer_id` before creating a new Stripe Customer. Check `tenant.charter_member_number` before assigning a new number. The `with_for_update()` lock prevents concurrent duplicate assignments. | Design decision |
| **Step 5 for Charter vs non-Charter** | Charter: skip `activate_trial()` (Stripe trial handles it), just mark checklist `tier_selected=true`. Non-Charter: keep existing `activate_trial()` behavior. | Spec §7.1 |
| **`messaging_setup` checklist item scope** | The column is added to all tenants but only displayed for Charter members (frontend conditional). The "Set up text messaging" item links to the 10DLC flow (C-B9). | Spec §7.2 |
| **Stripe Customer creation timing** | Created in step 4 (not step 5) because the Charter subscription needs a customer ID. The `create_stripe_customer()` function from the existing codebase is reused. | Spec §7.1 |
| **What if Stripe API fails during step 4?** | The `create_charter_subscription()` function (C-B4) is non-blocking on failure — it logs and returns. The wizard still advances. The Stripe subscription can be created manually by Tom later. This matches the existing `create_charter_subscription_schedule()` pattern. | Existing pattern in `stripe_subscriptions.py` |

---

## H. Surface Mockup Reference

**Design spec**: This batch requires a UI design spec from the **`pilot-web-ui-designer`** mode before the React Engineer starts. The spec must cover:

1. **Wizard step 4** — Charter tier card with "Free for 90 days. No card needed." copy
2. **Wizard step 5** — Two branches: (a) `requires_payment_method=true` → existing Stripe Elements, (b) `requires_payment_method=false` → confirmation copy "You're set. No charge until {date}."
3. **Onboarding checklist** — New "Set up text messaging" item with cost disclosure inline
4. **Charter Member badge** — Owner-only dashboard badge showing "Charter Member #N"

**Platform scope**: Web dashboard (`apps/web`) only — no mobile changes in this batch.

**§16 pattern consumption**:
- Optimistic UI: tier selection shows free-period copy immediately
- System-default/tenant-override: `requires_payment_method` is tier-level
- 409-and-refresh: existing wizard staleness guard unchanged

**Design spec output**: `dev-docs/architecture-design/batch-designs/batch-c-b5-ui-design-spec.md`

> **⚠️ Tom gate**: The React Engineer prompt must NOT be authored until the design spec is Tom-approved. The Python Engineer prompt can proceed independently.

---

## I. Component Manifest

| Component | Destination | New/Existing | Notes |
|---|---|---|---|
| `CharterTierCard` | `apps/web/src/features/signup/components/` | New | Step 4 tier card with free-period copy |
| `Step5Confirmation` | `apps/web/src/features/signup/components/` | New | Step 5 confirmation branch (no-card path) |
| `MessagingSetupChecklistItem` | `apps/web/src/features/onboarding/components/` | New | Checklist item with cost disclosure |
| `CharterMemberBadge` | `apps/web/src/features/dashboard/components/` | New | Owner-only badge showing charter_member_number |

> **Component-existence check**: Verify against `frontend/packages/ui/src/index.ts` before proposing new components. The badge may be composable from existing `Badge` + `Pill` primitives.
