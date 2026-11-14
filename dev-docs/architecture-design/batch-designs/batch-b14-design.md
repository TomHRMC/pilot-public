# Batch B14 Design Document — Onboarding, Signup & Subscription

**Items**: A75, A73, A74, A76, A77, A78  
**Prerequisite Batches**: B9 (settings resolver), B10 (notification category infrastructure, billing category), B13b (schema clean)  
**Gates**: B15 (A76 Stripe webhook handler extended by A81)  
**Estimated Effort**: 21–26 days  
**Test Subfolder**: `tests/batch_b14/`  
**Schema Authority**: MCP `postgres-local` queries ran 2026-05-03 — all 8 new tables confirmed absent from live DB before design

---

## A. MIGRATION PLAN

### Pre-Existence Verification (MCP Confirmed)

All seven new tables confirmed **absent** from the live DB:

```sql
-- Query ran; result was empty array:
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN (
  'tenant_signup','tenant_legal_acceptance','subscription_tier',
  'tenant_tier_override','tenant_subscription_usage',
  'tenant_onboarding_checklist','mobile_push_permission_state',
  'stripe_webhook_event_processed'
);
-- → []
```

`tenant` table current columns (MCP confirmed): `created_at`, `updated_at`, `created_by`, `updated_by`, `id`, `name`, `is_active`. **None** of the 5 subscription/trial columns exist — all must be added by migration.

`mobile_device_push_token` table confirmed present with `device_id UUID NOT NULL`. A78 references `device_id` (not `id`) as the join key; confirmed correct.

---

### Migration 1 — A75: Subscription Tier Infrastructure

**Name**: `phase_fe_1_batch_b14_subscription_tier_infrastructure`

---

#### New Table: `subscription_tier`

**Mixin**: `StandardAuditMixin` — tier metadata is operator-managed and may be edited (price changes, deactivation). Needs full `created_at`, `updated_at`, `created_by`, `updated_by` audit trail.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `tier_id` | UUID | NOT NULL | `gen_random_uuid()` | PK |
| `tier_name` | TEXT | NOT NULL | — | `trial \| starter \| professional \| enterprise` |
| `display_label` | TEXT | NOT NULL | — | User-facing label |
| `monthly_price_cents` | INTEGER | NOT NULL | — | 0 for trial tier |
| `is_trial` | BOOLEAN | NOT NULL | `false` | TRUE only for the trial tier |
| `trial_duration_days` | INTEGER | NULL | — | System default trial length; set only for trial tier |
| `max_users` | INTEGER | NOT NULL | — | User count limit enforced at user-add |
| `max_sms_segments_per_month` | INTEGER | NULL | — | NULL = unlimited; otherwise quota-enforced |
| `is_active` | BOOLEAN | NOT NULL | `true` | FALSE = not available for new signups |
| `display_order` | INTEGER | NOT NULL | — | Order in tier picker UI |
| `stripe_price_id` | TEXT | NULL | — | Stripe Price ID for paid tiers; NULL for trial |
| `created_at` | TIMESTAMPTZ | NOT NULL | — | From `StandardAuditMixin` |
| `updated_at` | TIMESTAMPTZ | NOT NULL | — | From `StandardAuditMixin` |
| `created_by` | UUID | NULL | — | FK → `user.id` RESTRICT |
| `updated_by` | UUID | NULL | — | FK → `user.id` RESTRICT |

**Indexes**: `ix_subscription_tier_is_active` on `is_active`, `ix_subscription_tier_is_trial` on `is_trial`

**Triggers (3)**:
1. `audit_subscription_tier_changes AFTER INSERT OR DELETE OR UPDATE ON public.subscription_tier FOR EACH ROW EXECUTE FUNCTION audit.log_changes()`
2. `trg_subscription_tier_guard_created_immutable BEFORE UPDATE ON public.subscription_tier FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()`
3. `trg_subscription_tier_set_updated_at BEFORE UPDATE ON public.subscription_tier FOR EACH ROW EXECUTE FUNCTION public.set_updated_at()`

**Seed data** (inserted inline in migration `upgrade()`):

| tier_name | display_label | monthly_price_cents | is_trial | max_users | trial_duration_days | display_order |
|-----------|---------------|---------------------|----------|-----------|---------------------|---------------|
| `trial` | Trial | 0 | TRUE | 5 | 14 | 1 |
| `starter` | Starter | 14900 | FALSE | 5 | NULL | 2 |
| `professional` | Professional | 24900 | FALSE | 15 | NULL | 3 |
| `enterprise` | Enterprise | 44900 | FALSE | 50 | NULL | 4 |

---

#### New Table: `tenant_tier_override`

**Mixin**: `StandardAuditMixin` — operator override is mutable (can be updated or removed); full audit trail required for accountability.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `tenant_id` | UUID | NOT NULL | — | PK; FK → `tenant.id` RESTRICT |
| `override_tier_id` | UUID | NULL | — | FK → `subscription_tier.tier_id` RESTRICT; supersedes `tenant.current_subscription_tier_id` when set |
| `override_trial_length_days` | INTEGER | NULL | — | Supersedes `subscription_tier.trial_duration_days` when set |
| `override_reason` | TEXT | NULL | — | Required operator note (enforced at application layer) |
| `set_by_operator_user_id` | UUID | NOT NULL | — | FK → `user.id` RESTRICT; the operator who set this |
| `set_at` | TIMESTAMPTZ | NOT NULL | — | When the override was applied |
| `created_at` | TIMESTAMPTZ | NOT NULL | — | From `StandardAuditMixin` |
| `updated_at` | TIMESTAMPTZ | NOT NULL | — | From `StandardAuditMixin` |
| `created_by` | UUID | NULL | — | FK → `user.id` RESTRICT |
| `updated_by` | UUID | NULL | — | FK → `user.id` RESTRICT |

**Triggers (3)**: standard audit / immutable-guard / updated_at set on `tenant_tier_override`

---

#### New Table: `tenant_subscription_usage`

**Mixin**: `StandardAuditMixin` — usage counts update frequently as users are added/removed and SMS is sent; `updated_at` is needed to know when usage last changed.

> **Design Resolution**: The arch doc specifies `tenant_id UUID PRIMARY KEY`. However, with `rollover_sms_quota_periods` Celery task creating rows at billing cycle boundaries, a single-column PK would prevent historical period tracking and force UPDATE semantics. Resolution: use composite PK `(tenant_id, period_start)` to allow multiple period rows per tenant. The "current period" is the row with `period_end >= now()`. This matches the pattern of `sms_quota_period` and `subscription_usage` tables already in the schema.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `tenant_id` | UUID | NOT NULL | — | PK (composite with `period_start`); FK → `tenant.id` RESTRICT |
| `period_start` | TIMESTAMPTZ | NOT NULL | — | PK (composite); aligned to subscription billing cycle |
| `period_end` | TIMESTAMPTZ | NOT NULL | — | End of billing cycle |
| `current_user_count` | INTEGER | NOT NULL | `0` | Updated by user-add/remove events |
| `current_sms_segment_count` | INTEGER | NOT NULL | `0` | Updated by SMS-send events; links to `sms_quota_period` model |
| `created_at` | TIMESTAMPTZ | NOT NULL | — | From `StandardAuditMixin` |
| `updated_at` | TIMESTAMPTZ | NOT NULL | — | From `StandardAuditMixin` |
| `created_by` | UUID | NULL | — | FK → `user.id` RESTRICT |
| `updated_by` | UUID | NULL | — | FK → `user.id` RESTRICT |

**Indexes**: `ix_tenant_subscription_usage_period_end` on `(tenant_id, period_end DESC)` — fast lookup for current period

**Triggers (3)**: standard audit / immutable-guard / updated_at set on `tenant_subscription_usage`

---

#### Column Additions to `tenant`

All 5 columns confirmed absent (MCP query showed `tenant` has only `id`, `name`, `is_active`, `created_at`, `updated_at`, `created_by`, `updated_by`). Use 3-part migration pattern (add nullable → backfill → constrain):

| Column | Type | Nullable | Default | FK Target | Notes |
|--------|------|----------|---------|-----------|-------|
| `current_subscription_tier_id` | UUID | NOT NULL (after backfill) | — | `subscription_tier.tier_id` RESTRICT | Backfill: set to the trial tier seed row for all existing tenants |
| `trial_started_at` | TIMESTAMPTZ | NULL | — | — | Set when trial begins |
| `trial_ends_at` | TIMESTAMPTZ | NULL | — | — | Trial expiry timestamp; read by `enforce_trial_expirations` |
| `trial_length_days_override` | INTEGER | NULL | — | — | Populated by operator; takes precedence over `subscription_tier.trial_duration_days` |
| `stripe_customer_id` | TEXT | NULL | — | — | Populated on first Stripe Customer record creation |

**Backfill strategy for `current_subscription_tier_id`**: SELECT the `tier_id` of the row in `subscription_tier` where `is_trial = TRUE` (seeded in the same migration) and UPDATE all existing `tenant` rows.

**Migration ordering within this file**: CREATE `subscription_tier` → SEED tier rows → ADD columns to `tenant` → BACKFILL `current_subscription_tier_id` → ALTER COLUMN NOT NULL → CREATE `tenant_tier_override` → CREATE `tenant_subscription_usage` → SEED new RBAC permissions.

**New RBAC permissions seeded** (added to `platform_role.permissions` for relevant roles):

| Permission String | Role(s) |
|------------------|---------|
| `subscription.view` | owner, accountant |
| `subscription.tier.change` | owner |

---

### Migration 2 — A73: Tenant Signup State Machine

**Name**: `phase_fe_1_batch_b14_tenant_signup_state_machine`

---

#### New Table: `tenant_signup`

**Mixin**: `StandardAuditMixin` — wizard state advances through stages; `signup_state` field is mutated on each step advance; full audit trail needed for signup forensics and support.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `tenant_id` | UUID | NOT NULL | — | PK; FK → `tenant.id` RESTRICT |
| `signup_state` | TEXT | NOT NULL | `'step1_account'` | `step1_account \| step2_legal \| step3_phone \| step4_tier \| step5_confirm \| complete` |
| `signup_started_at` | TIMESTAMPTZ | NOT NULL | — | When signup was initiated |
| `signup_completed_at` | TIMESTAMPTZ | NULL | — | Set when `signup_state = 'complete'` |
| `business_name` | TEXT | NOT NULL | — | Collected in step 1; propagated to `tenant.name` |
| `trade` | TEXT | NOT NULL | — | e.g., `electrical \| plumbing \| hvac` |
| `business_size` | TEXT | NOT NULL | — | e.g., `solo \| 2-5 \| 6-10` |
| `zip` | TEXT | NOT NULL | — | Used for tax jurisdiction auto-suggestion |
| `time_zone` | TEXT | NOT NULL | — | e.g., `America/New_York`; propagated to tenant settings |
| `created_at` | TIMESTAMPTZ | NOT NULL | — | From `StandardAuditMixin` |
| `updated_at` | TIMESTAMPTZ | NOT NULL | — | From `StandardAuditMixin` |
| `created_by` | UUID | NULL | — | FK → `user.id` RESTRICT |
| `updated_by` | UUID | NULL | — | FK → `user.id` RESTRICT |

**Check constraint**: `tenant_signup_state_chk CHECK (signup_state IN ('step1_account', 'step2_legal', 'step3_phone', 'step4_tier', 'step5_confirm', 'complete'))`

**Index**: `ix_tenant_signup_state` on `(signup_state)` — fast lookup of incomplete signups for Celery tasks

**Triggers (3)**: standard audit / immutable-guard / updated_at set on `tenant_signup`

**New RBAC permissions seeded**:

| Permission String | Role(s) |
|------------------|---------|
| `tenant.signup.complete` | (auto during signup — public route, no JWT required in wizard) |

---

### Migration 3 — A74: Legal Acceptance Recording

**Name**: `phase_fe_1_batch_b14_legal_acceptance_recording`

---

#### New Table: `tenant_legal_acceptance`

**Mixin**: `AppendOnlyMixin` — legal acceptance records are immutable once written; modifying an acceptance record would undermine its legal enforceability. `AppendOnlyMixin` provides `created_at` + `created_by` + 2-trigger set (`audit_changes` + `guard_created_immutable`).

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `acceptance_id` | UUID | NOT NULL | `gen_random_uuid()` | PK |
| `tenant_id` | UUID | NOT NULL | — | FK → `tenant.id` RESTRICT; index |
| `user_id` | UUID | NOT NULL | — | FK → `user.id` RESTRICT; the owner who accepted |
| `document_type` | TEXT | NOT NULL | — | `tos \| privacy \| eula \| marketing_email_optin` |
| `document_version_hash` | TEXT | NOT NULL | — | SHA-256 of document content at time of acceptance |
| `accepted_at` | TIMESTAMPTZ | NOT NULL | — | Client-reported acceptance timestamp |
| `ip_address` | INET | NOT NULL | — | Request IP from server |
| `user_agent` | TEXT | NOT NULL | — | Request User-Agent from server |
| `created_at` | TIMESTAMPTZ | NOT NULL | — | From `AppendOnlyMixin` |
| `created_by` | UUID | NULL | — | FK → `user.id` RESTRICT; from `AppendOnlyMixin` |

**Check constraint**: `tenant_legal_acceptance_document_type_chk CHECK (document_type IN ('tos', 'privacy', 'eula', 'marketing_email_optin'))`

**Indexes**: `ix_tenant_legal_acceptance_tenant_id` on `tenant_id`, `ix_tenant_legal_acceptance_user_document` on `(tenant_id, user_id, document_type)` — fast lookup for "has user accepted this doc?"

**Triggers (2)** (`AppendOnlyMixin`):
1. `audit_tenant_legal_acceptance_changes AFTER INSERT OR DELETE OR UPDATE ON public.tenant_legal_acceptance FOR EACH ROW EXECUTE FUNCTION audit.log_changes()`
2. `trg_tenant_legal_acceptance_guard_created_immutable BEFORE UPDATE ON public.tenant_legal_acceptance FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()`

**New RBAC permissions seeded**:

| Permission String | Role(s) |
|------------------|---------|
| `legal_acceptance.accept` | (auto during signup — public wizard route) |

---

### Migration 4 — A76: Stripe Webhook Dedup Table + RBAC

**Name**: `phase_fe_1_batch_b14_stripe_subscription_webhook`

---

#### New Table: `stripe_webhook_event_processed`

**Mixin**: `AppendOnlyMixin` — webhook dedup records are append-only; once written, they must never be modified (modifying them would break idempotency semantics). `AppendOnlyMixin` provides `created_at` + `created_by`.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `event_id` | TEXT | NOT NULL | — | PK; Stripe event ID e.g. `evt_1abc...` |
| `processed_at` | TIMESTAMPTZ | NOT NULL | — | When first processed |
| `event_type` | TEXT | NOT NULL | — | e.g. `invoice.paid`, `customer.subscription.created` |
| `created_at` | TIMESTAMPTZ | NOT NULL | — | From `AppendOnlyMixin` |
| `created_by` | UUID | NULL | — | FK → `user.id` RESTRICT; NULL for system-initiated (webhook arrival) |

**Triggers (2)** (`AppendOnlyMixin`):
1. `audit_stripe_webhook_event_processed_changes AFTER INSERT OR DELETE OR UPDATE ON public.stripe_webhook_event_processed FOR EACH ROW EXECUTE FUNCTION audit.log_changes()`
2. `trg_stripe_webhook_event_processed_guard_created_immutable BEFORE UPDATE ON public.stripe_webhook_event_processed FOR EACH ROW EXECUTE FUNCTION public.guard_created_fields_immutable()`

> **No `updated_at` trigger** — correct for `AppendOnlyMixin`; these rows are never modified.

No additional column additions to existing tables in this migration.

---

### Migration 5 — A77: Onboarding Checklist

**Name**: `phase_fe_1_batch_b14_onboarding_checklist`

---

#### New Table: `tenant_onboarding_checklist`

**Mixin**: `StandardAuditMixin` — checklist items toggle between states as the tenant completes setup actions; `updated_at` tracks when each item was last completed; `created_by`/`updated_by` traces which user triggered completion.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `tenant_id` | UUID | NOT NULL | — | PK; FK → `tenant.id` RESTRICT |
| `account_created` | BOOLEAN | NOT NULL | `false` | Auto-set on signup completion |
| `legal_accepted` | BOOLEAN | NOT NULL | `false` | Auto-set when all required docs accepted |
| `tier_selected` | BOOLEAN | NOT NULL | `false` | Auto-set on wizard step 4 completion |
| `first_customer_added` | BOOLEAN | NOT NULL | `false` | Auto-set on first `Customer` create |
| `first_customer_added_at` | TIMESTAMPTZ | NULL | — | When first customer was added |
| `catalog_setup` | BOOLEAN | NOT NULL | `false` | Auto-set on first catalog item added |
| `catalog_setup_at` | TIMESTAMPTZ | NULL | — | When catalog was first set up |
| `quickbooks_connected` | BOOLEAN | NOT NULL | `false` | Auto-set on QB OAuth complete |
| `quickbooks_skipped` | BOOLEAN | NOT NULL | `false` | Set when user clicks Skip |
| `calendar_connected` | BOOLEAN | NOT NULL | `false` | Auto-set on Calendar OAuth complete |
| `calendar_skipped` | BOOLEAN | NOT NULL | `false` | Set when user clicks Skip |
| `team_invited` | BOOLEAN | NOT NULL | `false` | Auto-set on first team invite sent |
| `team_skipped` | BOOLEAN | NOT NULL | `false` | Set when user clicks Skip |
| `checklist_hidden` | BOOLEAN | NOT NULL | `false` | Set when user clicks Hide widget |
| `checklist_dismissed_permanently` | BOOLEAN | NOT NULL | `false` | Set when user clicks "Don't show again" |
| `created_at` | TIMESTAMPTZ | NOT NULL | — | From `StandardAuditMixin` |
| `updated_at` | TIMESTAMPTZ | NOT NULL | — | From `StandardAuditMixin` |
| `created_by` | UUID | NULL | — | FK → `user.id` RESTRICT |
| `updated_by` | UUID | NULL | — | FK → `user.id` RESTRICT |

**Triggers (3)**: standard audit / immutable-guard / updated_at set on `tenant_onboarding_checklist`

**New RBAC permissions seeded**:

| Permission String | Role(s) |
|------------------|---------|
| `onboarding_checklist.skip_item` | owner, accountant |
| `onboarding_checklist.dismiss` | owner, accountant |

---

### Migration 6 — A78: Mobile Push Permission State

**Name**: `phase_fe_1_batch_b14_mobile_push_permission_state`

---

#### New Table: `mobile_push_permission_state`

**Mixin**: `StandardAuditMixin` — permission state changes over time (`granted → revoked_in_settings → granted`); `updated_at` reflects when state last changed; `created_by`/`updated_by` traces the app reporting the change.

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `tenant_id` | UUID | NOT NULL | — | PK (composite with `user_id`, `device_id`); FK → `tenant.id` RESTRICT |
| `user_id` | UUID | NOT NULL | — | PK (composite); FK → `user.id` RESTRICT |
| `device_id` | UUID | NOT NULL | — | PK (composite); FK → `mobile_device_push_token.device_id` RESTRICT |
| `permission_state` | TEXT | NOT NULL | `'not_asked'` | `not_asked \| granted \| denied_by_user_choice \| denied_by_os \| revoked_in_settings` |
| `last_state_change_at` | TIMESTAMPTZ | NOT NULL | — | When permission state last changed |
| `dismissable_banner_dismissed_at` | TIMESTAMPTZ | NULL | — | Tracks first dismissal; banner reappears after 7 days |
| `created_at` | TIMESTAMPTZ | NOT NULL | — | From `StandardAuditMixin` |
| `updated_at` | TIMESTAMPTZ | NOT NULL | — | From `StandardAuditMixin` |
| `created_by` | UUID | NULL | — | FK → `user.id` RESTRICT |
| `updated_by` | UUID | NULL | — | FK → `user.id` RESTRICT |

**Check constraint**: `mobile_push_permission_state_state_chk CHECK (permission_state IN ('not_asked', 'granted', 'denied_by_user_choice', 'denied_by_os', 'revoked_in_settings'))`

**Indexes**: `ix_mobile_push_perm_tenant_user` on `(tenant_id, user_id)` — list all devices for a user

**Triggers (3)**: standard audit / immutable-guard / updated_at set on `mobile_push_permission_state`

**New RBAC permissions seeded**:

| Permission String | Role(s) |
|------------------|---------|
| `mobile_push_permission.update` | owner, technician, office_staff, accountant (all roles — own device only) |

---

## B. EXECUTION ORDER

| # | Item | Rationale |
|---|------|-----------|
| 1 | **A75** — Subscription Tier Infrastructure | Foundation: `subscription_tier` must exist before A73 can add `current_subscription_tier_id` FK to `tenant`. `tenant_subscription_usage` usage tracking must exist before A76 can enforce user-add limits at conversion. `subscription.view` + `subscription.tier.change` RBAC permissions needed before A76 route can enforce them. |
| 2 | **A73** — Trial State Machine + Tenant Signup | Depends on A75 (tenant signup wizard step 4 references `subscription_tier`; `tenant.current_subscription_tier_id` FK added in A75 migration). Establishes the trial state machine and Celery task that all later items interact with. |
| 3 | **A74** — Legal Acceptance Recording | Depends on A73 (wizard step 2 writes to `tenant_legal_acceptance`; `tenant_signup` record must exist). Isolated table addition — simplest item in the batch once wizard state exists. |
| 4 | **A76** — Stripe Integration for Paid Conversion | Depends on A73 (wizard step 5 calls conversion; `tenant.stripe_customer_id` and `trial_ends_at` are managed by A73 service) and A75 (tier maps to Stripe `price_id`). Establishes `stripe_webhook_event_processed` dedup table and webhook handler that B15/A81 extends. |
| 5 | **A77** — Onboarding State Tracking + Checklist Resumability | Depends on A73 (wizard completion triggers checklist initialization). Auto-completion event handlers added to existing domain services for customer-create, QB OAuth, etc. Can run concurrently with A76 in practice but logically follows A73. |
| 6 | **A78** — Mobile Push Permission Tracking + Degraded-Mode Fallback | Depends on A77 (push permission flow starts when onboarding checklist is complete). References `mobile_device_push_token.device_id` (B8/A51 table — already exists). Simplest item; no blocking dependencies within B14. |

---

## C. NEW API ENDPOINTS

### A75 — Subscription Tier Infrastructure

#### `GET /api/v1/subscription-tiers`
- **Auth**: JWT required
- **Permission**: `subscription.view`
- **Request body**: None
- **Response**:
  ```json
  {
    "tiers": [
      {
        "tier_id": "uuid",
        "tier_name": "starter",
        "display_label": "Starter",
        "monthly_price_cents": 14900,
        "is_trial": false,
        "max_users": 5,
        "max_sms_segments_per_month": 100,
        "display_order": 2,
        "is_active": true
      }
    ]
  }
  ```
- **Route file**: `backend/api/routes/subscription_tiers.py`

#### `GET /api/v1/tenants/{tenant_id}/subscription`
- **Auth**: JWT required
- **Permission**: `subscription.view`
- **Response**:
  ```json
  {
    "current_tier": { "tier_id": "uuid", "tier_name": "trial", ... },
    "trial_ends_at": "2026-05-17T00:00:00Z",
    "stripe_customer_id": null,
    "usage": {
      "period_start": "2026-05-03T00:00:00Z",
      "period_end": "2026-06-03T00:00:00Z",
      "current_user_count": 2,
      "current_sms_segment_count": 14
    },
    "tier_override": null
  }
  ```
- **Route file**: `backend/api/routes/tenant_subscription.py`

#### `PUT /api/v1/tenants/{tenant_id}/subscription/upgrade`
- **Auth**: JWT required
- **Permission**: `subscription.tier.change`
- **Request body**:
  ```json
  { "target_tier_id": "uuid" }
  ```
- **Response**: delegates to A76 for Stripe; returns `{ "redirect_to_stripe": true }` if payment required, or tier update confirmation for operator overrides
- **Route file**: `backend/api/routes/tenant_subscription.py`

---

### A73 — Trial State Machine + Tenant Signup

#### `POST /api/v1/signup`
- **Auth**: **Public** (no JWT — user does not yet exist at initiation)
- **Permission**: None
- **Request body**:
  ```json
  {
    "business_name": "Johnson Electric",
    "trade": "electrical",
    "business_size": "2-5",
    "zip": "10001",
    "time_zone": "America/New_York",
    "owner_email": "tom@johnson.example.com",
    "owner_first_name": "Tom",
    "owner_last_name": "Johnson"
  }
  ```
- **Response**:
  ```json
  {
    "tenant_id": "uuid",
    "signup_state": "step1_account",
    "cognito_user_sub": "cognito-sub-string"
  }
  ```
- **Route file**: `backend/api/routes/signup.py`

#### `PUT /api/v1/signup/{tenant_id}/step{N}` (N = 2, 3, 4, 5)
- **Auth**: JWT required (issued after step 1 Cognito account creation)
- **Permission**: `tenant.signup.complete`
- **Request body varies per step**:
  - Step 2: `{ "documents_accepted": ["tos", "privacy", "eula"] }` — delegates to A74 legal acceptance
  - Step 3: `{ "phone_verified": true }` OR `{ "phone_skipped": true }`
  - Step 4: `{ "selected_tier_id": "uuid" }` — for trial selection
  - Step 5: `{ "confirmed": true }` for trial, OR `{ "stripe_payment_method_id": "pm_..." }` for paid conversion
- **Response**:
  ```json
  {
    "tenant_id": "uuid",
    "signup_state": "step3_phone",
    "next_step": "step4_tier"
  }
  ```
- **Route file**: `backend/api/routes/signup.py`

#### `GET /api/v1/signup/{tenant_id}/state`
- **Auth**: JWT required
- **Permission**: `tenant.signup.complete`
- **Response**:
  ```json
  {
    "tenant_id": "uuid",
    "signup_state": "step3_phone",
    "collected_data": {
      "business_name": "Johnson Electric",
      "trade": "electrical",
      "tier_selected": null
    }
  }
  ```
- **Route file**: `backend/api/routes/signup.py`

---

### A74 — Legal Acceptance Recording

#### `POST /api/v1/signup/{tenant_id}/legal/accept`
- **Auth**: JWT required
- **Permission**: `legal_acceptance.accept`
- **Request body**:
  ```json
  {
    "document_type": "tos",
    "document_version_hash": "sha256hex...",
    "accepted_at": "2026-05-03T14:30:00Z"
  }
  ```
- **Response**: `{ "acceptance_id": "uuid", "document_type": "tos", "accepted_at": "..." }`
- **Route file**: `backend/api/routes/signup.py` (co-located with signup wizard)

#### `GET /api/v1/signup/{tenant_id}/legal/required`
- **Auth**: JWT required
- **Permission**: `tenant.signup.complete`
- **Response**:
  ```json
  {
    "required_documents": [
      { "document_type": "tos", "current_version_hash": "sha256hex...", "already_accepted": false },
      { "document_type": "privacy", "current_version_hash": "sha256hex...", "already_accepted": false },
      { "document_type": "eula", "current_version_hash": "sha256hex...", "already_accepted": false }
    ]
  }
  ```
- **Route file**: `backend/api/routes/signup.py`

---

### A76 — Stripe Integration for Paid Conversion

#### `POST /api/v1/webhooks/stripe`
- **Auth**: **Public** (Stripe signature verified inside handler — not JWT)
- **Permission**: None (signature verification IS the auth gate)
- **Request body**: Raw Stripe webhook payload (JSON)
- **Stripe-Signature header**: Required; verified via `stripe.Webhook.construct_event()`
- **Response**: `{ "status": "received", "event_id": "evt_1abc..." }` — returns 200 immediately; processing is async
- **Route file**: `backend/api/routes/webhooks_stripe.py` (new file — separate from QB `webhooks.py`)

**Handled events**:
| Stripe Event | Action |
|---|---|
| `customer.subscription.created` | Confirm tier activation; update `tenant.current_subscription_tier_id` |
| `customer.subscription.updated` | Handle tier changes; update tier FK |
| `customer.subscription.deleted` | Mark subscription inactive; transition to `trial_expired` paywall (Phase 2 self-service cancellation) |
| `invoice.paid` | Confirm recurring billing success |
| `invoice.payment_failed` | Trigger retry notification; if exhausted → transition tenant to `payment_failed` paywall state |

#### `POST /api/v1/tenants/{tenant_id}/subscription/convert-from-trial`
- **Auth**: JWT required
- **Permission**: `subscription.tier.change`
- **Request body**:
  ```json
  {
    "stripe_payment_method_id": "pm_...",
    "target_tier_id": "uuid"
  }
  ```
- **Response**:
  ```json
  {
    "stripe_subscription_id": "sub_...",
    "status": "pending_webhook_confirmation"
  }
  ```
  - Tier is NOT updated immediately — confirmed only on `customer.subscription.created` webhook
- **Route file**: `backend/api/routes/tenant_subscription.py`

#### `POST /api/v1/tenants/{tenant_id}/subscription/change-tier`
- **Auth**: JWT required
- **Permission**: `subscription.tier.change`
- **Request body**: `{ "target_tier_id": "uuid" }`
- **Response**: `{ "status": "pending_webhook_confirmation" }`
- **Notes**: Primarily a Phase 2 self-service surface; backend implementation included for MVP completeness
- **Route file**: `backend/api/routes/tenant_subscription.py`

---

### A77 — Onboarding Checklist

#### `GET /api/v1/tenants/{tenant_id}/onboarding/checklist`
- **Auth**: JWT required
- **Permission**: `subscription.view` (owner/accountant; checklist is tenant-scoped)
- **Response**: Full `tenant_onboarding_checklist` row serialized as JSON
- **Route file**: `backend/api/routes/onboarding_checklist.py`

#### `PUT /api/v1/tenants/{tenant_id}/onboarding/checklist/skip/{item}`
- **Auth**: JWT required
- **Permission**: `onboarding_checklist.skip_item`
- **Path param `item`**: `quickbooks \| calendar \| team`
- **Response**: Updated checklist state
- **Route file**: `backend/api/routes/onboarding_checklist.py`

#### `PUT /api/v1/tenants/{tenant_id}/onboarding/checklist/hidden`
- **Auth**: JWT required
- **Permission**: `onboarding_checklist.dismiss`
- **Request body**: `{ "hidden": true }`
- **Response**: `{ "checklist_hidden": true }`
- **Route file**: `backend/api/routes/onboarding_checklist.py`

#### `PUT /api/v1/tenants/{tenant_id}/onboarding/checklist/dismissed`
- **Auth**: JWT required
- **Permission**: `onboarding_checklist.dismiss`
- **Request body**: None (action is permanent)
- **Response**: `{ "checklist_dismissed_permanently": true }`
- **Route file**: `backend/api/routes/onboarding_checklist.py`

---

### A78 — Mobile Push Permission State

#### `PUT /api/v1/users/me/devices/{device_id}/push-permission`
- **Auth**: JWT required
- **Permission**: `mobile_push_permission.update`
- **Request body**:
  ```json
  {
    "permission_state": "granted"
  }
  ```
- **Response**: Full `mobile_push_permission_state` record for the device
- **Route file**: `backend/api/routes/mobile_push_permission.py`

#### `GET /api/v1/users/me/devices/{device_id}/push-permission`
- **Auth**: JWT required
- **Permission**: `mobile_push_permission.update` (own device)
- **Response**:
  ```json
  {
    "device_id": "uuid",
    "permission_state": "not_asked",
    "last_state_change_at": "2026-05-03T14:30:00Z",
    "dismissable_banner_dismissed_at": null,
    "banner_should_appear": false
  }
  ```
- The `banner_should_appear` field is computed server-side: `TRUE` when `permission_state IN ('denied_by_user_choice', 'denied_by_os', 'revoked_in_settings')` AND (`dismissable_banner_dismissed_at IS NULL` OR `dismissable_banner_dismissed_at < now() - interval '7 days'` AND the permanent second-dismissal has not occurred)
- **Route file**: `backend/api/routes/mobile_push_permission.py`

---

## D. PATTERN REUSE DECISIONS

### §16.5 System-Default + Tenant-Override (Three-Tier Settings Resolver)

**Shared module**: `services/setting_resolver.py` — established in B9/A53.

**Applies to A75 (trial length resolution)**: When `enforce_trial_expirations` calculates a tenant's trial end date, the trial length comes from a two-tier chain:
1. Check `tenant_tier_override.override_trial_length_days` — if set, use it
2. Fall back to `subscription_tier.trial_duration_days` for the trial tier

This mirrors the pattern in `services/setting_resolver.py::get_effective_setting()` but operates on entity fields rather than the `tenant_settings` + `system_config` tables. The trial management service implements this inline without calling `get_effective_setting()` directly (different data sources), but follows the same resolution logic from §16.5.

**Applies to A75 (B14/A75 entry in shared module inventory)**: The impl plan §6 shared-module table lists `setting_resolver.py` as consumed by B14 (A75). The consumption is via the tier-limit enforcement check reading `subscription_tier.max_users` (itself a system-configured value) against `tenant_subscription_usage.current_user_count`.

```python
# services/tier_limit_enforcer.py — consumes setting_resolver pattern
from services.setting_resolver import get_effective_setting  # B9/A53

def check_user_add_allowed(db: Session, tenant_id: UUID) -> tuple[bool, dict]:
    """Returns (allowed, error_payload) for the user-add gate."""
    # Get effective tier (operator override first, then tenant's current tier)
    tier = _get_effective_tier(db, tenant_id)  # operator override pattern
    usage = _get_current_usage(db, tenant_id)
    if usage.current_user_count >= tier.max_users:
        return False, {
            "tier_limit_reached": True,
            "current_tier": tier.tier_name,
            "max_users": tier.max_users,
            "upgrade_url": f"/settings/subscription/upgrade"
        }
    return True, {}
```

---

### §17.1 Periodic Poll Task (Celery) — A73 Trial Expiration

**Applies to A73**: The `enforce_trial_expirations` Celery task follows the §17.1 periodic poll pattern exactly — no `bind=True`, no retry, processes a batch, returns count dict.

```python
# tasks/trial_management.py
from core.celery_app import celery_app
from core.db import get_db
from sqlmodel import Session, select

@celery_app.task(name="enforce_trial_expirations")
def enforce_trial_expirations() -> dict:
    """
    Hourly: transition expired trials to trial_expired paywall state.
    Also dispatches 4-step pre-expiration warning notifications.
    Per arch doc §4.7.5 and §20.8.
    """
    db: Session = next(get_db())
    # ...
```

**Beat schedule entry** (in `core/celery_app.py`):
```python
"enforce-trial-expirations-hourly": {
    "task": "enforce_trial_expirations",
    "schedule": crontab(minute=0),  # top of every hour
},
```

---

### §19.3 Stripe Webhook Pattern — A76

**Applies to A76**: The Stripe webhook handler follows the §19.3 Stripe-specific pattern. Key implementation points:

```python
# api/routes/webhooks_stripe.py
import stripe
from core.config import settings

def _verify_stripe_signature(request: Request, payload_bytes: bytes) -> None:
    """Raises stripe.error.SignatureVerificationError if invalid."""
    sig_header = request.headers.get("Stripe-Signature", "")
    stripe.Webhook.construct_event(
        payload_bytes, sig_header, settings.STRIPE_WEBHOOK_SECRET
    )
```

The dedup check against `stripe_webhook_event_processed` runs immediately after signature verification — per the canonical webhook pattern (§19.1 step 4):

```python
# Check dedup table before any processing
from sqlmodel import select
from app.models.billing_stripe import StripeWebhookEventProcessed

existing = db.exec(
    select(StripeWebhookEventProcessed)
    .where(StripeWebhookEventProcessed.event_id == event.id)
).first()
if existing:
    return {"status": "duplicate", "event_id": event.id}

# INSERT + process atomically
```

---

### `notification_outbox` Pattern — A73 Trial Warning Sequence

**Applies to A73**: The 4-step trial warning sequence (7d, 3d, 1d, 0d) routes through `notification_outbox` with `billing` category (established in B10/A56). The `enforce_trial_expirations` task dispatches warnings by writing to `notification_outbox` — it does NOT send emails directly.

```python
# Inside enforce_trial_expirations — for each tenant approaching expiry
from app.models.system import NotificationOutbox

warning_outbox = NotificationOutbox(
    tenant_id=tenant.id,
    recipient_user_id=owner_user_id,
    category_id="billing",
    sub_trigger_id="billing.trial_expiring",
    channel="push",
    body=f"Your trial ends in {days_remaining} days. Pick a plan to keep using Pilot.",
    deep_link_target="/settings/subscription/upgrade",
    priority="standard" if days_remaining > 1 else "critical",
)
db.add(warning_outbox)
```

**Forced-minimum push** on day-0 critical notification: uses `system_announcements.critical` sub-trigger (per arch doc §4.5 MFA grace period logic precedent) — cannot be suppressed by user preference.

---

### §8.2 Dual-Endpoint Architecture — All New Route Files

**Applies to all 5 new route files**: Every CRUD route follows the `_impl()` + test variant pattern. **Exception**: `POST /api/v1/webhooks/stripe` has NO test variant — webhook signatures cannot be faked in the test endpoint pattern; tests use `MockStripeWebhook` fixture instead.

```python
# api/routes/signup.py — example
def _initiate_signup_impl(
    data: SignupInitiateRequest,
    db: Session,
    request: Request,
) -> TenantSignupResponse:
    """Shared logic — no auth context at step 1."""
    ...

@router.post("/test", response_model=TenantSignupResponse)
def initiate_signup_test(data: SignupInitiateRequest, db: Session = Depends(get_db)):
    test_context = get_test_context()
    return _initiate_signup_impl(data, db, request=None)

@router.post("/", response_model=TenantSignupResponse)
def initiate_signup(data: SignupInitiateRequest, request: Request, db: Session = Depends(get_db)):
    return _initiate_signup_impl(data, db, request)
```

---

### §16.5 Notification Preference Three-Tier Resolution — A73 Trial Warnings

The `enforce_trial_expirations` task dispatches notifications via `notification_outbox`. The delivery dispatcher (`poll_pending_notifications` Celery task — B10/A56) applies the three-tier preference resolution chain before delivery. Trial warning notifications use `billing` category which is OFF for push, ON for email, ON for in-app by default — meaning email + in-app are delivered by default; push is OFF unless user opts in.

Day-0 (expiration day) notification is elevated to `system_announcements.critical` sub-trigger, which has `forced_minimum_push_uniform = TRUE` — guarantees push delivery regardless of user preference.

---

## E. SHARED MODULE INTERFACES

### `services/trial_management.py` (New in A73)

```python
# backend/services/trial_management.py
"""
Trial state machine and expiration enforcement service.
Used by: tenant signup wizard (A73), enforce_trial_expirations Celery task (A73),
         tier limit enforcer (A75), Stripe webhook handler (A76).
"""
from datetime import UTC, datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlmodel import Session, select


def compute_trial_end_date(
    db: Session,
    tenant_id: UUID,
    trial_start: datetime,
) -> datetime:
    """
    Resolve trial length using two-tier chain:
    1. tenant_tier_override.override_trial_length_days (operator override)
    2. subscription_tier.trial_duration_days (system default for trial tier)
    3. Hardcoded fallback: 14 days

    Returns:
        datetime (UTC): computed trial_ends_at timestamp
    """
    ...


def activate_trial(
    db: Session,
    tenant_id: UUID,
    initiating_user_id: UUID,
) -> None:
    """
    Set tenant.trial_started_at = now(), tenant.trial_ends_at = compute_trial_end_date().
    Creates tenant_subscription_usage row for the trial period.
    Called from wizard step 5 (trial confirmation path) and from signup completion.

    Args:
        db:                   Active DB session
        tenant_id:            Target tenant
        initiating_user_id:   Owner user completing the wizard
    """
    ...


def check_trial_expired(db: Session, tenant_id: UUID) -> bool:
    """
    Returns True if tenant is on trial tier AND trial_ends_at <= now().
    Used by API middleware paywall gate and enforce_trial_expirations task.
    """
    ...


def enforce_paywall(db: Session, tenant_id: UUID) -> dict:
    """
    Returns structured 402 payload for write-blocked trial-expired tenants.

    Returns:
        dict with keys: paywall=True, paywall_message=str, upgrade_url=str
        Returns empty dict {} if paywall does NOT apply.
    """
    ...


def dispatch_trial_warning(db: Session, tenant_id: UUID, days_remaining: int) -> None:
    """
    Write a notification_outbox row for a trial expiration warning.
    Category: 'billing'; sub_trigger: 'billing.trial_expiring'
    Day-0 uses system_announcements.critical (forced-minimum push).

    Args:
        db:              Active DB session
        tenant_id:       Target tenant
        days_remaining:  0 | 1 | 3 | 7 — determines copy and priority
    """
    ...
```

**File path**: `backend/services/trial_management.py`

---

### `services/stripe_subscriptions.py` (New in A76)

```python
# backend/services/stripe_subscriptions.py
"""
Stripe Subscriptions API integration.
Used by: tenant_subscription.py routes (A76), Stripe webhook handler (A76).
Requires: STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET in core.config.settings.
"""
from uuid import UUID
from sqlmodel import Session


def create_stripe_customer(db: Session, tenant_id: UUID, billing_email: str) -> str:
    """
    Create a Stripe Customer record for a tenant on first paid conversion.
    Stores stripe_customer_id on tenant row.

    Returns:
        str: Stripe Customer ID (cus_...)
    """
    ...


def create_stripe_subscription(
    db: Session,
    tenant_id: UUID,
    stripe_customer_id: str,
    stripe_price_id: str,
    stripe_payment_method_id: str,
) -> str:
    """
    Create a Stripe Subscription for a tenant.
    Does NOT update tenant tier — caller must wait for webhook confirmation.

    Returns:
        str: Stripe Subscription ID (sub_...)
    """
    ...


def handle_subscription_created(db: Session, stripe_event: dict) -> None:
    """
    Process customer.subscription.created webhook event.
    Updates tenant.current_subscription_tier_id based on Stripe price_id lookup.
    Clears trial_ends_at if converting from trial.
    """
    ...


def handle_invoice_payment_failed(db: Session, stripe_event: dict) -> None:
    """
    Process invoice.payment_failed webhook event.
    After Stripe exhausts retries (3 attempts/7 days), transitions tenant to
    payment_failed paywall state and dispatches billing notification.
    """
    ...
```

**File path**: `backend/services/stripe_subscriptions.py`

---

### `services/tier_limit_enforcer.py` (New in A75)

```python
# backend/services/tier_limit_enforcer.py
"""
Tier limit enforcement for user-add and SMS-send operations.
Used by: user invitation routes, SMS send service (A65/B11).
"""
from uuid import UUID
from sqlmodel import Session


def check_user_add_allowed(db: Session, tenant_id: UUID) -> tuple[bool, dict]:
    """
    Check whether adding a new user is permitted under the tenant's current tier.

    Resolution chain:
    1. tenant_tier_override.override_tier_id (operator override tier)
    2. tenant.current_subscription_tier_id (tenant's active tier)

    Returns:
        (True, {}) if allowed
        (False, {tier_limit_reached: True, current_tier: str, max_users: int,
                 upgrade_url: str}) if blocked — caller raises HTTP 403
    """
    ...


def increment_user_count(db: Session, tenant_id: UUID) -> None:
    """
    Increment current_user_count in tenant_subscription_usage for current period.
    Called after a successful user invitation acceptance.
    """
    ...


def decrement_user_count(db: Session, tenant_id: UUID) -> None:
    """
    Decrement current_user_count in tenant_subscription_usage for current period.
    Called after a user is deactivated/removed from the tenant. Floor: 0.
    """
    ...
```

**File path**: `backend/services/tier_limit_enforcer.py`

---

### `services/tenant_signup.py` (New in A73)

```python
# backend/services/tenant_signup.py
"""
Tenant signup wizard state machine.
Used by: signup.py routes (A73).
"""
from uuid import UUID
from fastapi import Request
from sqlmodel import Session

VALID_STATE_TRANSITIONS = {
    "step1_account": "step2_legal",
    "step2_legal":   "step3_phone",
    "step3_phone":   "step4_tier",
    "step4_tier":    "step5_confirm",
    "step5_confirm": "complete",
}


def initiate_signup(
    db: Session,
    request: Request,
    business_name: str,
    trade: str,
    business_size: str,
    zip_code: str,
    time_zone: str,
    owner_email: str,
    owner_first_name: str,
    owner_last_name: str,
) -> dict:
    """
    Step 1: Create Cognito user + Pilot tenant + tenant_signup record.
    Sets signup_state = 'step1_account'.
    Creates tenant_onboarding_checklist row with account_created=True.

    Returns:
        dict with tenant_id, signup_state, cognito_user_sub
    """
    ...


def advance_wizard_step(
    db: Session,
    tenant_id: UUID,
    current_state: str,
    step_data: dict,
    request: Request,
) -> dict:
    """
    Advance wizard from current_state to next state, performing step-specific
    work (legal acceptance, phone verification, tier selection, trial confirmation).

    Args:
        db:            Active DB session
        tenant_id:     Target tenant
        current_state: Expected current state (validated against DB — staleness guard)
        step_data:     Step-specific payload (varies by step)
        request:       FastAPI Request (for IP, User-Agent capture in A74)

    Returns:
        dict with tenant_id, signup_state, next_step

    Raises:
        HTTPException(409): If current DB state != current_state (resumability conflict)
        HTTPException(422): If step_data is invalid for the current step
    """
    ...


def get_signup_state(db: Session, tenant_id: UUID) -> dict:
    """Return current signup state and collected wizard data for resumability."""
    ...
```

**File path**: `backend/services/tenant_signup.py`

---

### `services/onboarding_service.py` (New in A77)

```python
# backend/services/onboarding_service.py
"""
Onboarding checklist auto-completion service.
Called by domain event handlers in customer, catalog, QB, calendar, and team modules.
"""
from uuid import UUID
from sqlmodel import Session


def mark_first_customer(db: Session, tenant_id: UUID) -> None:
    """
    Mark first_customer_added = True in tenant_onboarding_checklist.
    Idempotent — no-op if already marked.
    Called from customer create handler after successful commit.
    """
    ...


def mark_catalog_setup(db: Session, tenant_id: UUID) -> None:
    """Mark catalog_setup = True. Called from catalog item create handler."""
    ...


def mark_quickbooks_connected(db: Session, tenant_id: UUID) -> None:
    """Mark quickbooks_connected = True. Called from QB OAuth complete handler."""
    ...


def mark_calendar_connected(db: Session, tenant_id: UUID) -> None:
    """Mark calendar_connected = True. Called from Calendar OAuth complete handler."""
    ...


def mark_team_invited(db: Session, tenant_id: UUID) -> None:
    """Mark team_invited = True. Called from team invite send handler."""
    ...


def ensure_checklist_exists(db: Session, tenant_id: UUID) -> None:
    """
    Create tenant_onboarding_checklist row if it doesn't exist.
    Called during signup wizard completion (step5 → complete transition).
    Sets account_created = True, legal_accepted = True, tier_selected = True.
    """
    ...
```

**File path**: `backend/services/onboarding_service.py`

---

## F. OPEN QUESTIONS RESOLVED

### F1 — Should `subscription_tier` coexist with or replace the existing `product_plan` / `subscription` tables?

**Context**: The live DB has `product_plan`, `product_plan_version`, `subscription`, `subscription_status`, `subscription_usage` tables — a general-purpose SaaS billing schema. The arch doc §20 introduces `subscription_tier` as a new, simpler table specifically for the Pilot tier picker and trial-as-tier framing.

**Resolution**: **Introduce `subscription_tier` as a new, parallel table — do not repurpose `product_plan`.** The existing `product_plan` / `subscription` tables represent the general billing engine (multi-feature, TSTZRANGE validity, usage-based overage). `subscription_tier` is a simpler display-oriented table for the tier picker UI and trial logic. The arch doc §20.2 defines the schema explicitly. The `tenant.current_subscription_tier_id` FK points to `subscription_tier.tier_id`, NOT `product_plan.code`. Future reconciliation (Phase 2) may unify the two data models — for MVP, parallel is the correct approach to avoid disrupting the existing billing engine.

---

### F2 — Does `tenant_subscription_usage` use `tenant_id UUID PRIMARY KEY` or composite PK?

**Context**: Arch doc §20.3 states `tenant_subscription_usage: tenant_id UUID PRIMARY KEY`. However, the `rollover_sms_quota_periods` Celery task (§3.2) creates new usage rows at billing cycle boundaries, implying multiple rows per tenant over time.

**Resolution**: **Use composite PK `(tenant_id, period_start)`**. A single-column `tenant_id` PK would force UPDATE semantics for every billing cycle, losing historical period data. The existing `subscription_usage` table in the live DB uses a composite key pattern `(subscription_id, product_feature_code, period_start, period_end)`. This is consistent. Current-period queries use `WHERE tenant_id = :tid AND period_end >= now()`.

---

### F3 — Which notification category does the trial expiration warning sequence use?

**Context**: The impl plan §6.B14 states "uses B10 notification infrastructure 'billing' category or 'system announcements' category (final decision per Pilot operator)."

**Resolution**: **Use `billing` category for days 7, 3, 1; use `system_announcements.critical` sub-trigger for day-0 (expiration day).** Rationale: days 7/3/1 warnings are informational billing alerts — consistent with `billing` category defaults (OFF push, ON email, ON in-app). Day-0 paywall activation is an account-critical event warranting forced-minimum push; `system_announcements.critical` has `forced_minimum_push_uniform = TRUE` which guarantees push delivery regardless of user preference. This matches the precedent set by MFA reminders in §4.5 (day-7 final MFA reminder uses `system_announcements.critical`).

---

### F4 — Where does `stripe_webhook_event_processed` live in the ORM file structure?

**Context**: `db_models_map.md` does not list this table. It could go in `billing.py` or a new `billing_stripe.py`.

**Resolution**: **Add `StripeWebhookEventProcessed` class to `backend/app/models/billing.py`**, co-located with the rest of the billing infrastructure (`Subscription`, `Payment`, etc.). A separate `billing_stripe.py` file would be premature abstraction for a single table. The model file is already ~1000 lines but adding one class is acceptable for MVP.

---

### F5 — Does A76 need to add `stripe_price_id` to the existing `subscription` / `product_plan` tables, or only to `subscription_tier`?

**Context**: The existing `Subscription` model has `psp_provider` / `psp_subscription_id` / `psp_customer_id` but no `stripe_price_id`. The new `subscription_tier` table has `stripe_price_id`.

**Resolution**: **Only `subscription_tier.stripe_price_id` is needed for B14.** The Stripe Subscriptions API is called with the Price ID from `subscription_tier.stripe_price_id` — no change to the existing `Subscription` model needed. The existing `Subscription.psp_subscription_id` field stores the Stripe Subscription ID when the webhook confirms activation. The existing `Subscription.psp_customer_id` field stores the Stripe Customer ID. No new columns on `subscription` needed in B14.

---

### F6 — What is the `device_id` join key to `mobile_device_push_token` for A78?

**Context**: `mobile_push_permission_state` references `mobile_device_push_token` to track push permission per device. The `mobile_device_push_token` table has both `id UUID` (PK, auto-gen) and `device_id UUID` (MCP confirmed).

**Resolution**: **FK from `mobile_push_permission_state.device_id` → `mobile_device_push_token.device_id`** (NOT `.id`). The `device_id` is the stable client-generated device identifier that persists across token rotations. Using `device_id` as the join key means push permission state survives token refreshes. This matches the arch doc §4.7.4 schema.

> **⚠️ Pre-implementation check required**: PostgreSQL requires a UNIQUE constraint on the referenced column for a FK. The A78 migration must first verify whether `mobile_device_push_token.device_id` has a unique constraint. If not, `ALTER TABLE mobile_device_push_token ADD CONSTRAINT uq_mobile_device_push_token_device_id UNIQUE (device_id)` must precede the FK creation in the A78 migration.

---

### F7 — Should the `tenant_signup` endpoints be co-located in a single `signup.py` router or split?

**Context**: A73 (signup wizard), A74 (legal acceptance), both route via `/api/v1/signup/...`.

**Resolution**: **Single `backend/api/routes/signup.py` router file for all signup-related endpoints** (A73 wizard state + A74 legal acceptance). Both A73 and A74 operate under the `/api/v1/signup/{tenant_id}/...` prefix. Splitting into two files would add cross-file import complexity for no organizational benefit at 8 total endpoints. The router is registered with prefix `/api/v1/signup` in `main.py`.

---

### F8 — Does the paywall middleware run in the request path for B14, or is it deferred to a later batch?

**Context**: Arch doc §4.7.5 states "the API gateway middleware checks the tier flag and returns a structured 402 for any write operation" for trial-expired tenants.

**Resolution**: **Implement paywall enforcement in B14 as an application-layer `Depends()` callable, NOT middleware.** Middleware-level enforcement would require reading the `tenant` table on every request, adding DB latency to all endpoints. Instead, implement `services/trial_management.py::enforce_paywall()` as a FastAPI dependency that route handlers opt into. Write endpoints for core business operations include this dependency. Read-only endpoints (GET) never include it. This approach is lazy (reads only when needed) and explicit (enforced per-route rather than globally). Example:

```python
# core/paywall.py — new file in B14
from fastapi import Depends, HTTPException
from core.auth import AuthenticatedUser
from services.trial_management import enforce_paywall

def require_not_paywalled(
    current_user: AuthenticatedUser = Depends(require_permission("*")),
    db: Session = Depends(get_db),
) -> AuthenticatedUser:
    """Raises HTTP 402 with paywall payload if tenant is trial-expired."""
    payload = enforce_paywall(db, current_user.tenant_id)
    if payload:
        raise HTTPException(status_code=402, detail=payload)
    return current_user
```

---

## G. EXTERNAL DEPENDENCY STATUS

### Stripe (A76)

| Dependency | Required For | Mock Strategy | Tom Must Action |
|---|---|---|---|
| **Stripe account** | A76 Stripe Customer + Subscription creation | `stripe-mock` docker container OR Stripe test mode keys (`STRIPE_SECRET_KEY=sk_test_...`) | Create Stripe account; configure Products + Prices matching seed tier data; retrieve test + live API keys. **Lead time: 1–3 days** (email verification). |
| **Stripe webhook signing secret** | A76 `POST /api/v1/webhooks/stripe` signature verification | `MockStripeWebhook` test fixture bypasses signature check in dev | Get webhook signing secret from Stripe Dashboard → Webhooks → Add endpoint. Register endpoint URL after staging deployment. |
| **Stripe Price IDs** | A76 Subscription creation; `subscription_tier.stripe_price_id` seed data | Placeholder `price_test_xxx` IDs in dev seed data | Create Products + Prices in Stripe Dashboard matching tier prices (14900, 24900, 44900 cents/month); update `subscription_tier.stripe_price_id` via staging/prod migration. |
| **Stripe Elements (frontend)** | A76 card collection UI | No backend action; mock payment form in dev | Frontend concern only — backend does not render Stripe Elements. |

**Mock strategy for A76 backend tests**: All Stripe API calls in `services/stripe_subscriptions.py` go through a `StripeClient` wrapper whose base URL comes from `settings.STRIPE_BASE_URL`. Dev/test environments point to `http://stripe-mock:12111` via `stripe-mock` docker service; production uses `https://api.stripe.com`.

```python
# core/config.py additions for B14:
STRIPE_SECRET_KEY: str = ""
STRIPE_WEBHOOK_SECRET: str = ""
STRIPE_BASE_URL: str = "https://api.stripe.com"  # override in tests
```

---

### AWS Cognito (A73)

| Dependency | Required For | Mock Strategy | Tom Must Action |
|---|---|---|---|
| **Cognito User Pool** | A73 `POST /api/v1/signup` — creates Cognito user account | Existing test endpoint pattern (`TEST_ENDPOINT_ENABLED=true`) bypasses Cognito for unit tests | No new Cognito config required; existing User Pool is used. |
| **Post-Confirmation Lambda** | A73 — Lambda creates `user` + `tenant` records on Cognito confirmation (per arch doc §4.4) | In dev, the Lambda behavior is simulated directly in the signup route | Verify Lambda is deployed and functional before end-to-end staging test of signup flow. **Lead time: 0 — already deployed.** |

---

### SendGrid (A73 — trial warning emails)

| Dependency | Required For | Mock Strategy | Tom Must Action |
|---|---|---|---|
| **SendGrid API key** | A73 trial expiration warning emails dispatched via `notification_outbox` | `notification_outbox` rows created correctly; email delivery suppressed in dev when `SENDGRID_API_KEY=""` | Already configured from B10/B11 work. No new action required. |
| **`trial_expiring` email template copy** | A73 — 4-step warning email body (7d, 3d, 1d, 0d variants) | Template IDs exist in seeded `notification_template` data; copy can be placeholder during dev | **Tom must author 4 email copy variants** before staging deployment. Template rendering pipeline added in B15/A82; coordinate timing. |

---

### Legal Document Copy (A74)

| Dependency | Required For | Mock Strategy | Tom Must Action |
|---|---|---|---|
| **ToS / Privacy Policy / EULA legal text** | A74 `document_version_hash` is SHA-256 of actual document content | Dev uses placeholder document text; hash computed from placeholder | **Tom must have legal documents drafted and finalized before production launch.** `document_version_hash` values in `GET /api/v1/signup/{tenant_id}/legal/required` response must match final published document content. **Lead time: recommend initiating legal review 4–6 weeks before MVP launch.** |

---

### No External Dependencies

- **A75** (subscription tier tables): pure DB + ORM work; no external services
- **A77** (onboarding checklist): pure DB + event handler wiring; no external services
- **A78** (mobile push permission): pure DB + REST API; no external services; push delivery uses existing B8/A51 FCM/APNs token infrastructure

---

*Document end — Batch B14 Design. All six input reads completed before authoring. All schema questions resolved from live MCP queries. No sections left blank.*
