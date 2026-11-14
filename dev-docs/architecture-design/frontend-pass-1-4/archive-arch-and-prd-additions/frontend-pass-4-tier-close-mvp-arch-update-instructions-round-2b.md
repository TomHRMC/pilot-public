# Arch Doc v5 — Update Instructions Round 2B

**Date**: April 30, 2026
**Scope**: New §20 Subscription Tier + Stripe Integration Architecture (genuinely new domain) plus extensions to §3 Background Processing (notification preference center) and §4 Authentication & Authorization (onboarding state machine, operator role, account settings consolidation).
**Prerequisite**: Rounds 1 and 2A applied.

This round completes the v5 arch doc consolidation. After Round 2B, the arch doc covers all Pass 4 close architectural content.

---

## Edit 1 — §3.5 Notification Preference Center Architecture (new section)

Per the hybrid organizational choice, notification preference center extends §3 Background Processing rather than getting its own chapter. The notification dispatcher is fundamentally part of background processing infrastructure.

**Insertion point**: After §3.4 Profitability Rollup Worker (around line 583 in your post-Round-1 doc), before `## 4. Authentication & Authorization`.

**Content to insert**:

```markdown
### 3.5 Notification Preference Center Architecture

Pass 4 Tier 2 #5 introduced per-user notification preferences with category × channel granularity. The existing `notification_outbox` infrastructure (per §3.7 PRD; existing `poll_pending_notifications` Celery task per §3.2) is extended with a preference gate that consults user preferences before dispatching.

#### 3.5.1 Notification Category Registry

Every backend firing site classifies notifications into one of eight categories. Sub-trigger metadata drives the user-context-asymmetric forced-minimum semantics.

**Schema** (per A56):

```sql
notification_category (
    category_id              TEXT PRIMARY KEY,
        -- 'quote_approvals' | 'field_issues' | 'sync_conflicts' | 'job_activity'
        -- | 'customer_activity' | 'billing' | 'background_sync_alerts'
        -- | 'system_announcements'
    display_label            TEXT NOT NULL,
    description              TEXT NOT NULL,
    category_group_id        TEXT NULL,        -- Phase 2 forward-compatibility for grouping
    display_order            INTEGER NOT NULL
)

notification_category_sub_trigger (
    sub_trigger_id                       TEXT PRIMARY KEY,
        -- e.g., 'customer_activity.inbound_sms_reply',
        -- 'job_activity.assignment', 'system_announcements.critical'
    category_id                          TEXT NOT NULL REFERENCES notification_category,
    display_label                        TEXT,
    forced_minimum_push_uniform          BOOLEAN NOT NULL DEFAULT FALSE,
    forced_minimum_push_recipient_only   BOOLEAN NOT NULL DEFAULT FALSE
)
```

**Schema extension to `notification_outbox`**:

```sql
ALTER TABLE notification_outbox ADD COLUMN category_id TEXT NOT NULL
    REFERENCES notification_category(category_id);
ALTER TABLE notification_outbox ADD COLUMN sub_trigger_id TEXT NULL
    REFERENCES notification_category_sub_trigger(sub_trigger_id);
ALTER TABLE notification_outbox ADD COLUMN recipient_user_id_originating UUID NULL;
    -- The user the notification "belongs to" for forced-minimum-recipient-only semantics
    -- (e.g., the tech in a customer SMS conversation).
```

**Audit pass requirement**: every existing `notification_outbox.create()` call site (estimated 8 sites across the codebase) needs a category assignment. This is foundational work for A56 — without consistent classification, preferences can't be respected. Audit pass runs as part of A56 implementation.

#### 3.5.2 Default Policy and Preference Schema

Pilot ships system-default policies per category × channel; tenants can override; users can override within tenant policy.

**Schema**:

```sql
notification_default_policy (
    tenant_id        UUID NULL,                -- NULL = Pilot system default
    category_id      TEXT NOT NULL REFERENCES notification_category,
    channel          TEXT NOT NULL,            -- 'push' | 'email' | 'in_app'
    enabled          BOOLEAN NOT NULL,
    UNIQUE (tenant_id, category_id, channel)   -- with NULL handling for system defaults
)

notification_preference (
    tenant_id        UUID NOT NULL,
    user_id          UUID NULL,
        -- NULL = tenant-level override of system default
        -- Non-NULL = user-level override
    category_id      TEXT NOT NULL REFERENCES notification_category,
    channel          TEXT NOT NULL,
    enabled          BOOLEAN NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL,
    updated_at       TIMESTAMPTZ NOT NULL,
    UNIQUE (tenant_id, user_id, category_id, channel)   -- with NULL handling
)
```

**Pilot system defaults** (seeded at deployment):

| Category | Push | Email | In-app |
| :--- | :---: | :---: | :---: |
| Quote approvals | ON | ON | ON |
| Field issues | ON | ON | ON |
| Sync conflicts | OFF | ON | ON |
| Job activity | ON | OFF | ON |
| Customer activity | ON | OFF | ON |
| Billing | OFF | ON | ON |
| Background sync alerts | ON | OFF | ON |
| System announcements | OFF | ON | ON |

#### 3.5.3 Forced-Minimum Categories

Four categories cannot be muted by user override (push channel only; email and in-app remain user-configurable):

| Category × Sub-trigger | Forced minimum scope |
| :--- | :--- |
| Field issues (all sub-triggers) | All users (uniform forced-minimum) |
| Job activity → `assignment` sub-trigger | The tech being assigned (recipient-only) |
| System announcements → `critical` sub-trigger | All users (uniform forced-minimum) |
| Customer activity → `inbound_sms_reply` sub-trigger | The tech in the conversation (recipient-only) |

**The user-context-asymmetric forced-minimum** for Customer activity is new vocabulary for Pilot. Same category, different semantics depending on who's receiving:

- *Tech in the conversation*: push is forced minimum (cannot mute)
- *Owner receiving ambient awareness about another tech's conversation*: push is fully mutable
- *Other techs not in the conversation*: not in recipient list at all

The dispatcher implements this via per-recipient evaluation against the sub-trigger's `forced_minimum_push_recipient_only` flag plus comparison of `recipient_user_id_originating` to the candidate recipient.

#### 3.5.4 Three-Tier Resolution

Resolution chain for any user × category × channel:

1. If a row exists in `notification_preference` with `tenant_id`, `user_id`, `category_id`, `channel` → use that
2. Else if a row exists with `tenant_id`, `user_id IS NULL`, `category_id`, `channel` (tenant override) → use that
3. Else look up `notification_default_policy` with `tenant_id IS NULL` (Pilot system default) → use that
4. Else fallback constant (default OFF)

Implementation in `services/notification_resolver.py::get_effective_preference(tenant_id, user_id, category_id, channel)`.

**Forced-minimum override logic** (applies after resolution):

```python
effective_value = get_effective_preference(...)
sub_trigger = notification_outbox.sub_trigger_id

# Uniform forced-minimum push
if sub_trigger.forced_minimum_push_uniform AND channel == 'push':
    return True  # Override regardless of user preference

# Recipient-only forced-minimum push
if (sub_trigger.forced_minimum_push_recipient_only
    AND channel == 'push'
    AND recipient_user_id == notification_outbox.recipient_user_id_originating):
    return True

return effective_value
```

#### 3.5.5 Delivery Dispatcher Preference Gate

The existing `poll_pending_notifications` Celery task (§3.2) is extended with the preference gate. For each pending `notification_outbox` entry, for each potential recipient (one notification may have multiple recipients):

1. Look up effective preference for `(category_id, channel)` via the three-tier chain
2. Apply forced-minimum override logic
3. If channel still disabled: skip the channel; log the suppression for support/debugging
4. If all channels for a recipient are skipped: skip the recipient
5. If all recipients are skipped: mark the outbox row as `suppressed_by_preferences`

**Performance**: cache effective preferences per (user, category, channel) for the duration of a single dispatcher poll cycle. Cache invalidated on settings change (write triggers cache eviction in `notification_resolver.py`).

**Composes with rate limiting** (existing per A35): a notification must clear both the rate limit AND the user's preferences to be delivered. Rate limit is system-level (no more than X per category per hour); preferences are user-level (subscription); they compose without conflict.

#### 3.5.6 In-App Banner Channel

The third notification channel is partially new infrastructure. Push and email use existing infrastructure; in-app banner needs new components.

**Schema**:

```sql
in_app_notification (
    notification_id      UUID PRIMARY KEY,
    tenant_id            UUID NOT NULL,
    user_id              UUID NOT NULL,
    category_id          TEXT NOT NULL REFERENCES notification_category,
    body                 TEXT NOT NULL,
    deep_link_target     TEXT NOT NULL,
        -- per-category deep-link mapping; see §3.5.7
    priority             TEXT NOT NULL,            -- 'standard' | 'critical'
    created_at           TIMESTAMPTZ NOT NULL,
    read_at              TIMESTAMPTZ NULL
)
```

**SSE delivery channel** (extends existing SSE infrastructure per §13.11):

- `/sse/notifications` — streams in-app notifications to active sessions for the authenticated user
- Connection authenticated via Cognito JWT (per §4.2)
- One persistent connection per active web session; mobile uses SSE when foregrounded, falls back to push when backgrounded

**Frontend components** (shared web/mobile):

- `<NotificationBanner />` — slide-down from top of active page; auto-dismiss 6s standard / 12s critical; click-to-navigate; ARIA `role="alert"`
- Notification center bell icon in app shell — badge count of unread from last 24 hours; opens panel with last 50 notifications

**APIs**:

- `POST /api/v1/notifications/in-app/mark-read` — mark notification(s) as read
- `GET /api/v1/notifications/in-app/recent?limit=50` — returns last 50 for the bell panel

#### 3.5.7 Push Deep-Link Mapping

Every notification category has a defined deep-link target so tapping a push opens the relevant entity:

| Category | Deep-link target |
| :--- | :--- |
| Quote approvals | `/quotes/approvals/{quote_id}` |
| Field issues | `/dashboard/approvals/field-issues/{escalation_id}` |
| Sync conflicts | `/settings/integrations/{integration}/conflicts/{id}` |
| Job activity | `/jobs/{job_id}` |
| Customer activity | `/customers/{customer_id}/comm-history#thread-{thread_id}` |
| Billing | `/settings/subscription/invoices` |
| Background sync alerts | mobile sync queue surface |
| System announcements | `/settings/announcements/{id}` (Phase 2 surface route reserved) |

Implementation: each `notification_outbox` entry stores its deep-link target alongside the body. Dispatcher includes deep-link in push payload. Frontend handles deep-link routing on tap.

#### 3.5.8 Tenant Defaults Sub-Surface

Owners edit tenant-level defaults at `Settings > Notifications > Tenant defaults` (separate sub-page from `Settings > Notifications > Preferences` to keep scope clear). Same matrix structure; edits affect tenant defaults, not the owner's user override.

RBAC: `notification_preference.tenant_default.edit` — owner only.

#### 3.5.9 Backend Module Structure

```
backend/
├── api/
│   ├── routes/
│   │   ├── notification_categories.py    # GET /api/v1/notifications/categories
│   │   ├── notification_preferences.py   # GET/PUT/DELETE preference matrix
│   │   ├── notification_in_app.py        # in-app banner endpoints
│   │   └── ...
│   └── ...
├── services/
│   ├── notification_resolver.py          # three-tier resolution + forced-minimum logic
│   ├── notification_dispatcher.py        # extended with preference gate
│   └── ...
└── tasks/
    └── notification_worker.py            # poll_pending_notifications (extended; existing per §3.2)
```
```

This adds approximately 200 lines to §3.

---

## Edit 2 — §4.7 Onboarding State Machine (new section)

**Insertion point**: After §4.6 Refresh Token TTL & Offline Scenario (around the line where §4.6 ends — find `**Operational guard**: the refresh token TTL must not be reduced below 7 days`), before `## 5. QuickBooks Integration`.

**Content to insert**:

```markdown
### 4.7 Onboarding State Machine

Pass 4 Tier 3 #10 introduced the tenant signup wizard with resumable state. The state machine handles tenant creation, legal acceptance recording, optional phone verification, subscription tier selection, and trial-to-paid conversion.

#### 4.7.1 Wizard State Model

**Schema**:

```sql
tenant_signup (
    tenant_id                UUID PRIMARY KEY,
    signup_state             TEXT NOT NULL,
        -- 'step1_account' | 'step2_legal' | 'step3_phone' | 'step4_tier'
        -- | 'step5_confirm' | 'complete'
    signup_started_at        TIMESTAMPTZ NOT NULL,
    signup_completed_at      TIMESTAMPTZ NULL,

    -- Collected during step 1 (then propagated to tenant + user records)
    business_name            TEXT NOT NULL,
    trade                    TEXT NOT NULL,
    business_size            TEXT NOT NULL,
    zip                      TEXT NOT NULL,
    time_zone                TEXT NOT NULL
)
```

**Tenant table extensions**:

```sql
ALTER TABLE tenant ADD COLUMN current_subscription_tier_id UUID NOT NULL
    REFERENCES subscription_tier;
ALTER TABLE tenant ADD COLUMN trial_started_at TIMESTAMPTZ NULL;
ALTER TABLE tenant ADD COLUMN trial_ends_at TIMESTAMPTZ NULL;
ALTER TABLE tenant ADD COLUMN trial_length_days_override INTEGER NULL;
    -- set by operator if differs from system default
ALTER TABLE tenant ADD COLUMN stripe_customer_id TEXT NULL;
    -- populated on first paid conversion
```

**State transitions**:

| State | Next state | Trigger |
| :--- | :--- | :--- |
| (none) | `step1_account` | `POST /api/v1/signup` initiates signup |
| `step1_account` | `step2_legal` | Account created in Cognito; tenant record created |
| `step2_legal` | `step3_phone` | All required legal documents accepted |
| `step3_phone` | `step4_tier` | Phone verified OR explicitly skipped |
| `step4_tier` | `step5_confirm` | Tier selected (Trial or paid) |
| `step5_confirm` | `complete` | Trial confirmation OR paid Stripe payment success |

**Resumability**: a user logging in with `signup_state != 'complete'` is routed to wherever they left off. Wizard pre-fills fields from already-collected state. Users can navigate back through completed steps to review/edit (within scope — already-created Cognito account can't be undone).

**APIs** (per A73):

- `POST /api/v1/signup` — initiate signup; creates tenant in `step1_account` state
- `PUT /api/v1/signup/{tenant_id}/step{N}` — advance the wizard one step at a time
- `GET /api/v1/signup/{tenant_id}/state` — get current signup state for resumability

#### 4.7.2 Legal Acceptance Recording

Per A74, every legal document acceptance is captured with audit-grade fidelity.

**Schema**:

```sql
tenant_legal_acceptance (
    acceptance_id            UUID PRIMARY KEY,
    tenant_id                UUID NOT NULL REFERENCES tenant,
    user_id                  UUID NOT NULL REFERENCES user,
    document_type            TEXT NOT NULL,
        -- 'tos' | 'privacy' | 'eula' | 'marketing_email_optin'
    document_version_hash    TEXT NOT NULL,
        -- sha256 of document content at time of acceptance
    accepted_at              TIMESTAMPTZ NOT NULL,
    ip_address               INET NOT NULL,
    user_agent               TEXT NOT NULL
)
```

Multiple rows per (tenant_id, user_id, document_type) are allowed if document version changes and user re-accepts.

**Document version hashing**: each legal document's content is hashed at deployment. Hash changes when document content changes. Tenants whose accepted hash differs from current are prompted to re-accept on next login (Phase 2 — re-acceptance flow not in MVP).

#### 4.7.3 Onboarding Checklist Resumability

Per A77, the post-wizard checklist persists across sessions and across users in the tenant.

**Schema**:

```sql
tenant_onboarding_checklist (
    tenant_id                          UUID PRIMARY KEY,
    account_created                    BOOLEAN NOT NULL DEFAULT FALSE,
    legal_accepted                     BOOLEAN NOT NULL DEFAULT FALSE,
    tier_selected                      BOOLEAN NOT NULL DEFAULT FALSE,
    first_customer_added               BOOLEAN NOT NULL DEFAULT FALSE,
    first_customer_added_at            TIMESTAMPTZ NULL,
    catalog_setup                      BOOLEAN NOT NULL DEFAULT FALSE,
    catalog_setup_at                   TIMESTAMPTZ NULL,
    quickbooks_connected               BOOLEAN NOT NULL DEFAULT FALSE,
    quickbooks_skipped                 BOOLEAN NOT NULL DEFAULT FALSE,
    calendar_connected                 BOOLEAN NOT NULL DEFAULT FALSE,
    calendar_skipped                   BOOLEAN NOT NULL DEFAULT FALSE,
    team_invited                       BOOLEAN NOT NULL DEFAULT FALSE,
    team_skipped                       BOOLEAN NOT NULL DEFAULT FALSE,
    checklist_hidden                   BOOLEAN NOT NULL DEFAULT FALSE,
    checklist_dismissed_permanently    BOOLEAN NOT NULL DEFAULT FALSE
)
```

**Auto-completion detection**: existing event handlers in customer-create, catalog-item-create, OAuth-complete, team-invite-send domains invoke `tenant_onboarding_checklist::mark_complete(tenant_id, item)` when the corresponding action occurs via any path. Adding a customer via voice command triggers the same auto-completion as adding via the checklist's "Add now" button.

**Persistence is per-tenant** (not per-user): once an item is complete, every user in the tenant sees it as complete. This matches user expectations for shared setup tasks.

#### 4.7.4 Mobile Push Permission Tracking

Per A78, mobile push permission state is tracked per-device.

**Schema**:

```sql
mobile_push_permission_state (
    tenant_id                            UUID NOT NULL,
    user_id                              UUID NOT NULL,
    device_id                            UUID NOT NULL REFERENCES mobile_device_push_token,
    permission_state                     TEXT NOT NULL,
        -- 'not_asked' | 'granted' | 'denied_by_user_choice'
        -- | 'denied_by_os' | 'revoked_in_settings'
    last_state_change_at                 TIMESTAMPTZ NOT NULL,
    dismissable_banner_dismissed_at      TIMESTAMPTZ NULL,
    PRIMARY KEY (tenant_id, user_id, device_id)
)
```

Mobile app reads `permission_state` on launch. If `not_asked` and onboarding is complete, mobile setup phase fires (with pre-explainer screen before OS prompt). State changes propagate via `PUT /api/v1/users/me/devices/{device_id}/push-permission`.

**Banner reappearance logic**: when state is denied, dismissable banner shows on Today tab; user can dismiss (recorded in `dismissable_banner_dismissed_at`); banner reappears once after 7 days from dismissal; doesn't reappear after second dismissal.

#### 4.7.5 Trial Expiration Enforcement

Per A73, the `enforce_trial_expirations` Celery task (registered in §3.2) handles trial transitions.

**Pipeline**:

1. Hourly: query tenants where `trial_ends_at <= now()` AND `current_subscription_tier_id` is the trial tier
2. Transition tenant to `trial_expired` state (in subscription tier metadata; tier doesn't change, but a trial-expired flag activates the paywall)
3. Dispatch paywall notification (push + email + in-app banner via §3.5)
4. Tenant enters read-only mode: existing data visible; new data creation blocked; SMS sending blocked; voice intents available but limited to read-only operations

**Read-only enforcement** runs at the API layer: for tenants in trial-expired state, the API gateway middleware checks the tier flag and returns a structured 402 (Payment Required) response with `{paywall: true, message: ...}` for any write operation. Frontend handles 402 by surfacing the paywall.

**Pre-expiration warnings**: separate notifications dispatched at:
- 7 days before expiration (gentle)
- 3 days before (more urgent)
- 1 day before (final)
- Day of expiration (paywall active)

Implemented as scheduled Celery tasks reading from `tenant.trial_ends_at`.

#### 4.7.6 Tax Setup Just-In-Time Sub-Flow

Tax setup is the only contextual gate during onboarding. Tenants can use Pilot fully without tax setup until they attempt to generate an invoice.

**Detection**: server-side check on every quote-to-invoice conversion attempt and direct invoice creation attempt. If tax setup is incomplete (no `tax_jurisdiction` configured for the tenant), returns 412 (Precondition Required) with a structured payload that frontend uses to render the contextual sub-flow.

**Auto-detection**: tenant's primary tax jurisdiction is suggested from the ZIP code captured during signup step 1. User confirms or changes during the sub-flow.

After tax setup completes, subsequent invoice operations bypass the gate — the sub-flow only fires once.
```

This adds approximately 220 lines to §4.

---

## Edit 3 — §4.3 Operator Role + Hidden Pilot Routes (extension)

The operator role is a special platform-level role outside tenant RBAC. It needs to be documented as part of the existing §4.3 Role-Based Access Control discussion.

**Find** the existing §4.3 section.

**Add a new sub-section §4.3.X at the end of §4.3** (just before `### 4.4 Post-Signup Lambda`):

```markdown
#### 4.3.X Operator Role and Hidden Pilot Routes

Pass 4 introduced the **operator role** — a special platform-level role outside tenant RBAC, exclusively for the Pilot operator (Tom). The operator role manages cross-tenant settings via hidden Pilot routes that bypass standard tenant scoping.

**Why a special role**: operator-controlled values (per-tenant trial length override, per-tenant subscription tier override without payment, tenant suspension/restoration, tenant deletion with data purge, system default settings) cannot reasonably be managed through the standard RBAC model. Tenants shouldn't see these settings at all (security boundary), and the operator needs cross-tenant access (data scoping boundary).

**Operator-role permissions**:

| Permission | Purpose |
| :--- | :--- |
| `operator.tenant.override_trial_length` | Set per-tenant trial length override |
| `operator.tenant.override_subscription_tier` | Force a tenant onto a specific subscription tier without payment |
| `operator.tenant.suspend` | Suspend tenant access (e.g., for non-payment, ToS violation) |
| `operator.tenant.delete` | Permanently delete a tenant and all associated data |
| `operator.help_content.edit` | (Phase 2) Admin UI for editing help corpus directly |
| `operator.email_template.edit` | (Phase 2) Admin UI for editing email templates directly |
| `operator.subscription_tier.create_or_edit` | Manage available subscription tiers |
| `operator.feature_flag.toggle` | Operator-level feature flag management |

**Hidden Pilot routes**:

- Path prefix: `/admin/*` (or equivalent — final path TBD)
- Routes are accessible only to users with the `operator` role
- Standard Cognito authentication still applies; operator role is a Cognito user pool group attribute
- Routes bypass tenant scoping (no `require_tenant_isolation()` dependency)
- Routes have stricter rate limiting and audit logging

**MVP implementation strategy**: for MVP, operator-admin functions are managed via direct DB updates (Tom acts as the operator). Hidden Pilot routes are deferred operator infrastructure work. The data model includes operator-controlled fields (`tenant_tier_override.override_trial_length_days`, `tenant_tier_override.override_subscription_tier_id`, etc.); the UI for setting them is genuinely separate operator infrastructure outside Pass 4 design framework.

**Tenant tier override schema**:

```sql
tenant_tier_override (
    tenant_id                       UUID PRIMARY KEY REFERENCES tenant,
    override_tier_id                UUID NULL REFERENCES subscription_tier,
        -- if set, supersedes tenant.current_subscription_tier_id
    override_trial_length_days      INTEGER NULL,
        -- if set, supersedes system_default_trial_length_days
    override_reason                 TEXT NULL,
        -- operator note
    set_by_operator_user_id         UUID NOT NULL REFERENCES user,
    set_at                          TIMESTAMPTZ NOT NULL
)
```

Read by tenant signup flow and trial expiration flow (per §4.7.1).

**Why deferred**: as a solo operator, building admin UI for content editing, tier creation, etc. is real work that doesn't directly enable shipping MVP. Direct DB management is acceptable for the early-customer phase. Phase 2 introduces hidden Pilot routes when operator workload justifies it.
```

This adds approximately 60 lines to §4.3.

---

## Edit 4 — §4.8 Account Settings Architecture (new section)

Per the hybrid Q1 choice, account settings consolidates with §4 Authentication content. The §4.5 MFA section already covers MFA; §4.8 covers active sessions and data export.

**Insertion point**: After §4.7 Onboarding State Machine (just added in Edit 2), before `## 5. QuickBooks Integration`.

**Content to insert**:

```markdown
### 4.8 Account Settings — Active Sessions and Data Export

Pass 4 Tier 2 #7 introduced active sessions management and personal data export request. MFA is covered in §4.5; profile and password management use existing user model. This section covers the two new capabilities.

#### 4.8.1 Active Sessions List + Revoke

Per A70, users can view all currently-logged-in sessions for their account with device + browser + last-active timestamp + approximate location. Per-session revoke and "Revoke all other sessions" affordances.

**Schema** (extends existing token storage):

```sql
user_session_metadata (
    session_id              UUID PRIMARY KEY,
    tenant_id               UUID NOT NULL,
    user_id                 UUID NOT NULL REFERENCES user,
    device_fingerprint      TEXT NOT NULL,
        -- User-Agent + characteristics
    display_label           TEXT NOT NULL,
        -- e.g., "Chrome on macOS", "Pilot mobile on iPhone"
    ip_address              INET NOT NULL,
    geolocation             TEXT NULL,
        -- approximate; city/state from IP geolocation
    created_at              TIMESTAMPTZ NOT NULL,
    last_active_at          TIMESTAMPTZ NOT NULL,
    revoked_at              TIMESTAMPTZ NULL
)
```

Populated on login from User-Agent parsing + IP geolocation lookup (MaxMind GeoLite2 free tier or equivalent — city-level accuracy adequate; not security-critical).

**APIs**:

- `GET /api/v1/users/me/sessions` — list all active sessions for requesting user
- `DELETE /api/v1/users/me/sessions/{session_id}` — revoke specific session (invalidates Cognito refresh token; clears access token cache)
- `POST /api/v1/users/me/sessions/revoke-others` — bulk revoke all sessions except the current one

**Revoke behavior**: revoking a session immediately invalidates the refresh token; the next API request from that session returns 401, forcing re-login.

**The "Revoke all other sessions" affordance** is the user's primary self-service security action when suspecting account compromise. UI placement is intentionally prominent on the Active Sessions page.

**Password change auto-revoke** (per Tier 2 #7 Decision 3): on successful password change, all sessions other than the current one are auto-revoked as a security best practice. User remains logged in on the changing device; other devices require re-login.

#### 4.8.2 Personal Data Export Request

Per A71, users can request a full export of their accessible tenant data with RBAC-scoped contents. Background job compiles the export; download link emailed to user when ready.

**Schema**:

```sql
data_export_request (
    export_id            UUID PRIMARY KEY,
    tenant_id            UUID NOT NULL,
    user_id              UUID NOT NULL REFERENCES user,
    requested_at         TIMESTAMPTZ NOT NULL,
    status               TEXT NOT NULL,
        -- 'pending' | 'processing' | 'ready' | 'expired' | 'failed'
    s3_path              TEXT NULL,                        -- set when ready
    signed_url           TEXT NULL,                        -- 7-day signed S3 URL
    expires_at           TIMESTAMPTZ NULL,
    data_scope           TEXT NOT NULL,
        -- 'full_tenant' (owner/accountant) | 'user_specific' (technician)
    failure_reason       TEXT NULL
)
```

**Frequency limit**: maximum one pending or recent (within 24 hours) request per user. Enforced at request time.

**Export pipeline** (`tasks/data_export_pipeline.py`):

1. Celery task processes pending exports
2. Queries data per RBAC scope (owner: full tenant; technician: only own jobs/time/expenses/communications)
3. Streams to S3 in chunks (avoids in-memory bloat for large tenants — important for tenants with years of data)
4. Generates CSV files per entity type: customers.csv, jobs.csv, quotes.csv, invoices.csv, time_entries.csv, expenses.csv, communications.csv
5. Bundles into ZIP with `MANIFEST.json` containing metadata (export request time, requesting user, tenant_id, data scope)
6. Generates signed S3 URL with 7-day expiration
7. Sends email to requesting user with download link via existing notification infrastructure
8. Updates `data_export_request.status` to `ready`

**APIs**:

- `POST /api/v1/users/me/data-exports` — request new export (subject to 24-hour frequency limit)
- `GET /api/v1/users/me/data-exports` — list recent exports for requesting user
- `GET /api/v1/users/me/data-exports/{export_id}` — get specific export status

**Email template**: new transactional email "Your data export is ready" with download link + expiration date (template `data_export_ready` per §18.8).

**Backend module**: `tasks/data_export_pipeline.py` for the Celery task; `services/data_export_compiler.py` for the streaming CSV/ZIP generation logic.
```

This adds approximately 110 lines to §4.

---

## Edit 5 — Insert §20 Subscription Tier + Stripe Integration Architecture (new chapter)

**Insertion point**: After §19 Help System Architecture closes (the `### 19.12 Phase 2 Considerations` section ends), before `## Cost Analysis`.

**Content to insert**:

```markdown
## 20. Subscription Tier + Stripe Integration Architecture

Pass 4 Tier 3 #10 introduced the multi-tier subscription model with trial-as-tier framing and Stripe Subscriptions integration. Pass 4 Tier 4 #13 introduced Stripe Payment Intents for one-time invoice payments. This chapter covers the subscription tier infrastructure, Stripe integration architecture, payment flows, webhooks, and tier limit enforcement.

### 20.1 Strategic Direction

Three architectural principles drive the design:

- **Trial-as-tier framing**: the trial is a subscription tier with `is_trial=true`, $0 price, time-bounded duration. Full feature parity with Starter. No special "trial mode" branching in the codebase — every code path that asks "what tier is this tenant on?" gets a clean answer via the tier system.
- **Data-driven tier configuration**: tier metadata (name, price, included user count, included SMS segments) lives in the `subscription_tier` table. Adding/editing tiers is a DB update, not a code change. MVP launches with four tiers (Trial, Starter, Professional, Enterprise) differentiated by user count only; feature differentiation between tiers is Phase 2.
- **Stripe Subscriptions for recurring billing; Stripe Payment Intents for one-time invoice payments**: same Stripe account, parallel API surfaces. Per §18.5, customer payments on invoices use Payment Intents; per §20.4, tenant subscription billing uses Subscriptions. Both API surfaces share the webhook handler.

### 20.2 Subscription Tier Schema

**Schema** (per A75):

```sql
subscription_tier (
    tier_id                          UUID PRIMARY KEY,
    tier_name                        TEXT NOT NULL,
        -- 'trial' | 'starter' | 'professional' | 'enterprise' | ...
    display_label                    TEXT NOT NULL,        -- user-facing label
    monthly_price_cents              INTEGER NOT NULL,     -- 0 for trial
    is_trial                         BOOLEAN NOT NULL,     -- true only for trial tier
    trial_duration_days              INTEGER NULL,         -- set for trial tier; system default
    max_users                        INTEGER NOT NULL,
    max_sms_segments_per_month       INTEGER NULL,
        -- null = unlimited; otherwise enforced (overage billing per §17.6)
    is_active                        BOOLEAN NOT NULL DEFAULT TRUE,
        -- true if available for new signups
    display_order                    INTEGER NOT NULL,     -- order in tier picker UI
    stripe_price_id                  TEXT NULL,
        -- Stripe Price ID for paid tiers; null for trial
    created_at                       TIMESTAMPTZ NOT NULL,
    updated_at                       TIMESTAMPTZ NOT NULL
)
```

**MVP seed data**:

| tier_name | display_label | monthly_price_cents | is_trial | max_users | trial_duration_days |
| :--- | :--- | :--- | :--- | :--- | :--- |
| trial | Trial | 0 | TRUE | 5 | 14 (default; operator-overridable) |
| starter | Starter | 14900 | FALSE | 5 | NULL |
| professional | Professional | 24900 | FALSE | 15 | NULL |
| enterprise | Enterprise | 44900 | FALSE | 50 | NULL |

Tier prices are placeholders subject to market validation. Adding new tiers is a DB insert; the tier picker UI reads from the table at render time.

### 20.3 Subscription Usage Tracking

**Schema** (per A75):

```sql
tenant_subscription_usage (
    tenant_id              UUID PRIMARY KEY REFERENCES tenant,
    period_start           TIMESTAMPTZ NOT NULL,
        -- aligned to subscription billing cycle
    period_end             TIMESTAMPTZ NOT NULL,
    current_user_count     INTEGER NOT NULL,
    current_sms_segment_count INTEGER NOT NULL
        -- links to A65 SMS quota model in §17.6
)
```

**MVP scope**: tracks two metrics — current user count and current SMS segment count. Other dimensions (voice intent count, quote count, customer count, API call count) are deferred to Phase 2 because they create infrastructure that may not match what eventually gets monetized.

**Update triggers**:

- User-add events update `current_user_count`
- SMS-send events update `current_sms_segment_count` (per §17.6)

**Period rollover**: scheduled Celery task `rollover_sms_quota_periods` (per §3.2) creates new usage rows at subscription billing cycle boundaries.

### 20.4 Stripe Subscriptions Integration

Per A76, Stripe Subscriptions handle recurring billing for paid tiers.

**Stripe Customer record creation**: at first paid conversion, Pilot creates a Stripe Customer record with the tenant's billing email and metadata. Stored as `tenant.stripe_customer_id`. Reused for subsequent tier changes.

**Subscription lifecycle**:

1. Tenant selects paid tier in onboarding wizard (or `Settings > Subscription & Billing > Upgrade plan`)
2. Frontend uses Stripe Elements to collect card details
3. Backend creates Stripe Subscription via Stripe API with the tier's Stripe Price ID
4. Stripe processes initial payment; webhook fires `customer.subscription.created`
5. Backend confirms tier activation; tenant's `current_subscription_tier_id` updates
6. Recurring billing handled by Stripe; webhook fires `invoice.paid` on each cycle

**Conversion from trial**: when a trial tenant converts, the transition is:

1. Tenant submits Stripe Payment Method via Stripe Elements
2. Backend creates Stripe Customer + Subscription (with the chosen paid tier's Price ID)
3. On webhook confirmation, tenant transitions: `is_trial=true` → `is_trial=false`; `trial_ends_at` cleared; `current_subscription_tier_id` updated
4. No interruption to data or feature access — same tenant, same data, different tier

**APIs**:

- `POST /api/v1/tenants/{tenant_id}/subscription/convert-from-trial` — initiate conversion; expects Stripe Payment Method ID from frontend
- `POST /api/v1/tenants/{tenant_id}/subscription/change-tier` — change between paid tiers (Phase 2 surface; backend supports for MVP)

### 20.5 Stripe Payment Intents Integration (One-Time Invoice Payments)

Per §18.5 (Customer-Facing Public Surfaces) and A81, Stripe Payment Intents handle one-time invoice payments from customers via the public invoice link.

**Architecture summary** (full detail in §18.5):

- Customer enters payment amount on public invoice page (can vary from invoice total; comment required when variance)
- Frontend calls `POST /api/v1/public/invoices/{token}/payment-intent` with amount
- Backend creates Stripe Payment Intent; returns client_secret
- Frontend uses Stripe Elements to collect card and submit
- Stripe processes; webhook fires `payment_intent.succeeded` (or `payment_intent.payment_failed`)
- Backend records payment with actual amount + variance + comment

Same Stripe account as Subscriptions. Same Stripe Customer record (created on first interaction with the tenant — either subscription or invoice payment, whichever comes first).

### 20.6 Stripe Webhook Handler

Single webhook endpoint handles events from both Subscriptions and Payment Intents:

- Endpoint: `POST /api/v1/webhooks/stripe`
- Signature verification using Stripe webhook signing secret stored in Secrets Manager (per §9.1)
- Failure to verify signature returns 401 (Stripe retries per its policy)

**Handled events**:

| Event | Handler |
| :--- | :--- |
| `customer.subscription.created` | Confirm tier activation; record `stripe_customer_id` if first interaction |
| `customer.subscription.updated` | Handle tier changes (e.g., upgrade from Starter to Professional) |
| `customer.subscription.deleted` | Handle cancellation (Phase 2 self-service flow; MVP requires support contact) |
| `invoice.paid` | Confirm recurring subscription payment success |
| `invoice.payment_failed` | Trigger Stripe retry sequence; if exhausted, transition tenant to "payment failed" state |
| `payment_intent.succeeded` | Record one-time invoice payment per §18.5 |
| `payment_intent.payment_failed` | Surface failure to customer-facing UI per §18.5 |

**Idempotency**: webhook events are idempotent — processing the same event ID twice produces the same result. Stripe may retry events; handler uses event ID as idempotency key against `stripe_webhook_event_processed` table (deduplication).

### 20.7 Tier Limit Enforcement

**User-add flow**:

1. Tenant attempts to add a new user (invitation flow)
2. Backend checks `tenant_subscription_usage.current_user_count >= tier.max_users`
3. If limit reached: return 403 with structured payload `{tier_limit_reached: true, current_tier: ..., max_users: ..., upgrade_url: ...}`
4. Frontend renders Er3 (validation error per Tier 3 #8/#9 states catalog) with "Upgrade tier" CTA

**SMS-send flow**: per §17.6 SMS quota model.

**Phase 2**: feature-based limits as tier differentiation expands beyond user count. Schema accommodates additional limits via per-tier feature flags table (Phase 2).

### 20.8 Trial Expiration Read-Only State

When a tenant's trial expires (per §4.7.5), they enter "trial expired" state with read-only access plus paywall:

**Read-only enforcement** (API gateway middleware):

- For tenants in trial-expired state, write operations return 402 (Payment Required) with `{paywall: true, paywall_message: "..."}`
- Frontend handles 402 by surfacing the paywall (same tier picker UI as wizard step 4)
- Read operations continue working — data is preserved through expiration

**Conversion at trial end**: same flow as conversion during trial (per §20.4) — customer picks paid tier, submits payment, transitions to paid state.

### 20.9 Operator Overrides

Per §4.3.X Operator Role, operator can override per-tenant tier values:

- `tenant_tier_override.override_tier_id` — force tenant to a specific tier without payment
- `tenant_tier_override.override_trial_length_days` — extend trial for specific tenant
- `tenant_tier_override.override_reason` — required operator note
- Audit-logged

For MVP, operator manages via direct DB updates (per §4.3.X). Phase 2 introduces hidden Pilot routes for operator admin UI.

### 20.10 Backend Module Structure

```
backend/
├── api/
│   ├── routes/
│   │   ├── webhooks_stripe.py            # Stripe webhook handler (Subscriptions + Payment Intents)
│   │   ├── subscription_tiers.py         # GET /api/v1/subscription-tiers — tier picker data
│   │   ├── tenant_subscription.py        # GET/PUT /api/v1/tenants/{tenant_id}/subscription
│   │   └── ...
│   └── ...
├── services/
│   ├── stripe_subscriptions.py           # Subscription creation + lifecycle
│   ├── stripe_payment_intents.py         # One-time payment integration (per §18.5)
│   ├── tier_limit_enforcer.py            # User-add and SMS-send limit checks
│   ├── trial_management.py               # Trial state machine; expiration enforcement
│   └── ...
└── tasks/
    ├── enforce_trial_expirations.py      # per §3.2
    └── stripe_cleanup.py                  # cleanup_incomplete_stripe_payment_intents (per §3.2)
```

### 20.11 Phase 2 Considerations

Out of MVP scope:

- Stripe Customer Portal for self-service payment method management (MVP has read-only display)
- Annual billing tier discount
- Coupon / promo code support
- Self-service tier upgrade with proration
- Stripe Connect for direct-to-tenant invoice payment routing (architectural review point — Tom should review before MVP launch given financial implications; see §18.5)
- Per-customer pricing overrides
- Multi-currency support
- Self-service tenant cancellation (MVP requires support contact for cancellation)
- Feature-based limits beyond user count and SMS quota
- Usage-based pricing per category (voice intent count, quote count, etc.)
```

This adds approximately 380 lines.

---

## Edit 6 — TOC additions for Round 2B

**Find** the existing TOC (post-Round-2A state).

**Add new entries**:

Under §3 Background Processing entries:

```markdown
  - [3.5 Notification Preference Center Architecture](#35-notification-preference-center-architecture)
```

Under §4 Authentication & Authorization entries:

```markdown
  - [4.7 Onboarding State Machine](#47-onboarding-state-machine)
  - [4.8 Account Settings — Active Sessions and Data Export](#48-account-settings--active-sessions-and-data-export)
```

Within §4.3 RBAC sub-entries (if your TOC goes that deep):

```markdown
    - [4.3.X Operator Role and Hidden Pilot Routes](#43x-operator-role-and-hidden-pilot-routes)
```

After §19 Help System Architecture entries, before Cost Analysis:

```markdown
- [20. Subscription Tier + Stripe Integration Architecture](#20-subscription-tier--stripe-integration-architecture)
  - [20.1 Strategic Direction](#201-strategic-direction)
  - [20.2 Subscription Tier Schema](#202-subscription-tier-schema)
  - [20.3 Subscription Usage Tracking](#203-subscription-usage-tracking)
  - [20.4 Stripe Subscriptions Integration](#204-stripe-subscriptions-integration)
  - [20.5 Stripe Payment Intents Integration (One-Time Invoice Payments)](#205-stripe-payment-intents-integration-one-time-invoice-payments)
  - [20.6 Stripe Webhook Handler](#206-stripe-webhook-handler)
  - [20.7 Tier Limit Enforcement](#207-tier-limit-enforcement)
  - [20.8 Trial Expiration Read-Only State](#208-trial-expiration-read-only-state)
  - [20.9 Operator Overrides](#209-operator-overrides)
  - [20.10 Backend Module Structure](#2010-backend-module-structure)
  - [20.11 Phase 2 Considerations](#2011-phase-2-considerations)
```

---

## Verification checklist after Round 2B

- [ ] §3.5 Notification Preference Center Architecture inserted in §3 (Edit 1)
- [ ] §4.7 Onboarding State Machine inserted in §4 (Edit 2)
- [ ] §4.3.X Operator Role and Hidden Pilot Routes inserted in §4.3 (Edit 3)
- [ ] §4.8 Account Settings — Active Sessions and Data Export inserted in §4 (Edit 4)
- [ ] §20 Subscription Tier + Stripe Integration Architecture chapter inserted between §19 and Cost Analysis (Edit 5)
- [ ] All TOC entries added per Edit 6
- [ ] Cross-references resolve (e.g., §17.6 SMS quota referenced in §20.3; §18.5 Stripe payment intents referenced in §20.5; §3.5 referenced in §4.7.5)
- [ ] Document growth: approximately 970 lines added (200 §3.5 + 220 §4.7 + 60 §4.3.X + 110 §4.8 + 380 §20)

After Round 2B, your arch doc grows from ~4370 lines (post-Round-2A) to ~5340 lines.

---

## Pass 4 close arch doc — final state

After Rounds 1, 2A, and 2B are all applied, the arch doc is at v5 with full coverage of Pass 4 close architectural content:

- 20 main chapters (was 17 in v4.2)
- 16 platform UX patterns formalized in §16 (was 11 in v4.2)
- 4 new top-level chapters: §17 SMS Infrastructure, §18 Customer-Facing Public Surfaces, §19 Help System, §20 Subscription Tier + Stripe Integration
- Multiple sub-section additions: §3.5 (notification preference center), §4.5 (MFA expansion), §4.7 (onboarding state machine), §4.8 (account settings), §16.13 (in-flight sync indicator)
- Cost analysis updated for Pass 4 close
- All cross-references resolve
- Document grows from 3389 lines (v4.2 input) to ~5340 lines (v5 output) — ~58% growth, proportional to the scope of Pass 4 additions

The arch doc is now the consolidated v5 — ready as backend implementation source of truth alongside the v6 backend additions ledger.

---

## What comes next

After applying Round 2B, we have one remaining consolidation: the **framework doc third and final rewrite** per its own update model. This captures the Pass 4 close state and pivots the doc toward implementation phase.

The framework doc rewrite is meaningfully smaller than the arch doc work — estimated 350–500 lines of full doc content (vs. the 1900+ lines added to arch doc across all rounds). It's a single deliverable, not phased.

Tell me when you've applied Round 2B and want to proceed to the framework doc rewrite.
