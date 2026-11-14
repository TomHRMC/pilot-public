# Arch Doc v5 — Audit Report and Update Instructions

**Date**: April 30, 2026
**Audited file**: `mvp-arch.md` (your current uploaded version, 3389 lines)
**Current state**: v4.2 (per header — Pass 4 Tier 1.5 patches applied)
**Target state**: v5 — consolidates all Pass 4 work through Tier 4 close

---

## Audit summary — what's there and what's not

Your arch doc has **good Pass 4 Tier 1 / Tier 1.5 coverage**. Specifically:

✅ §17 SMS Infrastructure chapter is in (carrier adapter, A2P 10DLC, threading, quota, voice integration)
✅ §16.10–§16.12 Tier 1 patterns added (bilateral integration conflict resolution, mobile-to-web escalation, background sync execution)
✅ §16.5 settings list extended for Pass 4 Tier 1 + Tier 1.5
✅ §13.5 has the diff payload + auto-expiry + voice-active resolution
✅ Cost analysis has SMS infrastructure line
✅ §4.5 wording fix applied (MFA available/required distinction)

**What's missing — ten content gaps:**

1. **Doc header** — version still says v4.2; needs v5 bump and "Pass 4 close" framing. Also has a duplicated `**Version**:` prefix that's a typo.
2. **§16.1 Pattern Inventory** — missing 4 patterns: 3 from Tier 1.5 (carrier-agnostic adapter, subscription quota with cap, lazy provisioning) and 1 from Tier 4 #12 (in-flight sync indicator). Currently has 11 patterns; should have 15.
3. **§16 sub-sections** — needs §16.13 In-Flight Sync Indicator (Tier 4 #12) plus the three Tier 1.5 patterns aren't formalized as their own sub-sections (they're only in §17 currently).
4. **§16.5 settings list** — Tier 2/3/4 settings missing (MFA policy settings, sync indicator threshold, email branding, voice persona override toggle, etc.).
5. **§4.5 MFA section** — has the wording fix but is now thin. Tier 2 #7 added substantial MFA detail (multi-method, recovery codes, login challenge, owner reset, tenant policy with grace period) — needs full architecture treatment.
6. **§5.4 QB Conflict Resolution** — still says "Pass 4 work required" remnant phrasing; that work IS done. Plus per-entity auto-expiry, financial-delta callout, in-flight sync indicator.
7. **§6.2 Voice Intent Registry** — missing 5 Pass 4 intents: `resolve_field_issue` (Tier 1 #1), `list_pending_qb_conflicts` (Tier 1 #2), `reply_to_customer_sms` (Tier 1.5), `open_help`, `ask_help_question` (Tier 4 #14).
8. **§3.2 Celery Beat Schedule** — missing Pass 4 tasks: QB conflict auto-expiry, SMS quota monitoring + rollover, trial expiration enforcement, MFA grace period reminders, help session anonymization, help article embedding.
9. **New chapters needed at Pass 4 close** (largest gap):
   - §18 Customer-Facing Public Surfaces Architecture (Tier 4 #13)
   - §19 Help System Architecture (Tier 4 #14)
   - §20 Subscription Tier + Stripe Integration Architecture (Tier 3 #10 + Tier 4 #13 payment)
   - §21 Onboarding State Machine Architecture (Tier 3 #10)
   - §22 Notification Preference Center Architecture (Tier 2 #5)
   - §23 Account Settings Architecture (Tier 2 #7 — MFA, sessions, data export)
   - **OR** combine some into existing chapters (recommendations below)
10. **Cost Analysis** — missing Pass 4 close additions: Stripe processing fees, OpenAI embeddings for help corpus (~$1/month), help corpus S3 storage, increased compute from RAG retrieval.
11. **TOC** — needs entries for any new chapters.

**Two structural decisions you need to make first**, before I can give exact paste blocks for the new chapters.

---

## Two structural decisions — please answer before applying new-chapter content

### Q1 — How to organize the new content

Pass 4 close adds a *lot* of architectural content. Two organizational approaches:

**Option A — Many new chapters (cleaner conceptually)**

Add 6 new chapters: §18 Customer-Facing Public Surfaces, §19 Help System, §20 Subscription Tier + Stripe, §21 Onboarding State Machine, §22 Notification Preference Center, §23 Account Settings (MFA + sessions + data export).

Pros: each topic has clear identity; easy to find specific content. Cons: TOC becomes longer; doc grows substantially (estimated 800–1000 new lines).

**Option B — Consolidate into existing chapters where possible**

Map content to existing chapters:
- Customer-Facing Public Surfaces → extends §7 API Design (new §7.10 public surface conventions)
- Help System → new §19 (genuinely new domain; deserves chapter)
- Subscription Tier + Stripe → extends §1 Infrastructure or new §18
- Onboarding State Machine → extends §4 Authentication (new §4.7)
- Notification Preference Center → extends §3 Background Processing (new §3.5)
- Account Settings → extends §4.5 MFA into §4.5/4.7/4.8

Pros: doc stays more compact; related content is co-located. Cons: some sections become large; finding things requires more navigation.

I'd recommend **Option C — hybrid**: 3 new top-level chapters (§18 Help System, §19 Customer-Facing Public Surfaces, §20 Subscription & Onboarding) plus extensions to existing chapters for MFA detail in §4.5, notification dispatcher in §3, and account settings in §4. This balances clean topic identity for the genuinely new domains with co-location for content that extends existing concerns.

**Which option do you want? A, B, or C?**

### Q2 — Should I provide paste-ready blocks for ALL new content now, or just the structural ones?

Given the volume (estimated 800–1000 lines of new content), three options:

**(a) Full paste-ready blocks for everything in this update doc** — most thorough; this update doc itself becomes very long.

**(b) Paste-ready for the smaller fixes (§16.1, §16.5, §4.5, §5.4, §6.2, §3.2, doc header), prose summaries for the new chapters with separate follow-up update docs** — manageable scope per round.

**(c) Phased approach** — this round: structural fixes + the largest gaps (§4.5 MFA, §5.4 QB resolution, §16.1 pattern inventory, voice intents). Next round: new chapter content.

I'd recommend **(c) phased approach**. Most of the structural fixes are mechanical and can land in this round. The new chapters benefit from a separate focused round where you can review and challenge content without it being mixed with the smaller updates.

**Which option do you want? A, B, or C?**

---

## Round 1 update instructions (assuming you confirm option C above)

Below are paste-ready blocks for everything that doesn't need new chapters. Apply these now; we'll do new chapters in round 2 once you confirm Q1 and Q2.

---

## Edit 1 — Doc header version bump (lines 3–6)

**Find** (lines 3–6):

```markdown
**Version**: **Version**: 4.2 (Pass 4 Tier 1.5 — Customer Comms SMS infrastructure added as §17; full v5 issued at Pass 4 close)
**Last Updated:** April 29, 2026
**Author:** Tom (Founder)
**Status:** ACTIVE — Reflects current implementation through Pass 3 design completion
```

(Note: the `**Version**:` prefix is duplicated. Typo to fix.)

**Replace with**:

```markdown
**Version**: 5 (Pass 4 design phase complete — consolidates v4.1, v4.2 patches plus all Tier 1, 1.5, 2, 3, 4 architectural additions; ready as backend implementation source of truth)
**Last Updated:** April 30, 2026
**Author:** Tom (Founder)
**Status:** ACTIVE — Reflects all Pass 1–4 design completion; design phase frozen; backend implementation source of truth
```

---

## Edit 2 — §16.1 Pattern Inventory expansion (lines 2655–2667)

**Find** the existing pattern inventory table.

**Replace the entire table body** (everything from `| Track-changes diff vocabulary` through `| Background sync execution pattern...`) with this expanded version:

```markdown
| Pattern | First Established | Reuse Count |
| :--- | :--- | :--- |
| Track-changes diff vocabulary (amber/green/red) | Flow 5 (Quote approval) | 5 (quote approval §14, calendar conflict §13.5, mobile sync §15, mobile-conflict escalation §16.11, QB conflict §5.4 / §16.10) |
| Four-class severity pattern | Flow 3 (Dispatch conflicts) | 3 (dispatch §13.4, calendar sync §13.5, mobile sync §15.6) |
| Confirm-as-turn for destructive voice actions | Flow 1 (Voice quote creation) | All destructive voice intents §6.2 |
| Pre-commit staleness check (409-and-refresh) | Flow 3 (Dispatch board edits) | 8+ endpoints across §13.7, §13.5, §14.4, §15.9, §5.4, §16.11 |
| System default + tenant override two-tier configuration | Flow 6 (Calendar conflict auto-expiry) | Calendar §13.5, QB conflicts §5.4, background sync §17, sync indicator threshold §16.13; available platform-wide |
| Mobile owner status row + deep-link | Pass 2 QB sync | Extended for calendar §13.5, mobile sync §15.3, field issues §16.11, in-flight sync indicators §16.13 |
| Optimistic UI with pending badges | Flow 7 (Mobile offline) | All mobile offline-capable operations §15; settings UIs (Tier 2 #4) |
| Always-preview-before-send for one-way-door actions | Flow 4 (Customer comms) | Customer comms PRD §3.7; SMS replies §17; extensible to any future irreversible action |
| Bilateral integration conflict resolution pattern (formalized §16.10) | Flow 6 (Calendar) | Calendar §13.5, QuickBooks §5.4 |
| Mobile-to-web escalation pattern | Pass 4 Tier 1 #1 (Owner mobile-conflict UI) | Field issues §16.11; extensible to time-off requests, safety incidents, catalog requests |
| Background sync execution pattern | Pass 4 Tier 1 #3 (Background sync for mobile) | Mobile data queue §15, push token registry §17.10; extensible to periodic data refresh, future tech-to-tech messaging |
| Carrier-agnostic adapter layer pattern | Pass 4 Tier 1.5 (SMS via Telnyx) | SMS §17.1; extensible to other external service integrations (payment, mapping, email) |
| Subscription quota with soft/hard cap pattern | Pass 4 Tier 1.5 (SMS quota) | SMS quota §17.6; available for any future per-event metered feature |
| Lazy provisioning of external resource at first use | Pass 4 Tier 1.5 (Telnyx number) | Telnyx number §17.3; extensible to dedicated voice processing slots, customer-facing portal subdomains |
| In-Flight Sync Indicator with Pending Count | Pass 4 Tier 4 #12 (Dispatch board sync indicator refinement) | Calendar §13.5, QuickBooks §5.4, mobile data sync §15, background sync §17; extensible to any future sync surface |
```

This expands from 11 patterns to 15.

---

## Edit 3 — Add §16.13 In-Flight Sync Indicator section

**Insertion point**: After §16.12 closes (around line 2916 — the last line of the Background Sync Execution Pattern section), before `## 17. SMS Infrastructure` at line 2917.

**Content to insert**:

```markdown
### 16.13 In-Flight Sync Indicator with Pending Count

A sync surface (calendar sync, QuickBooks sync, mobile data sync, background sync) renders its current state plus a count of pending operations that haven't yet completed. This pattern was formalized at Tier 4 #12 to address the operational gap where a binary "synced or syncing" indicator implied currency that wasn't always true between sync cycles.

**Five compositional states**:

| State | Pending count | Visual treatment |
| :--- | :--- | :--- |
| Synced (idle) | 0 | Green dot, "Synced · last 12s ago" |
| Synced (pending detected) | N>0, no active sync | Green dot below threshold (default 5); amber dot above. "Synced · 3 pending · syncing in 2m" |
| Syncing | N≥0 | Amber dot with pulse, "Syncing 3 changes..." |
| Sync error | N≥0 | Red dot, "Sync error · 3 pending · [Resolve]" with CTA to relevant resolution surface |
| Sync paused | N≥0 | Neutral dot, "Paused · 3 queued · [Resume]" |

**Hover/tap detail**: surfaces individual pending items as ambient awareness, capped at 5 items with "+N more" line for higher counts. Items are informational only — actions on individual items happen via the relevant resolution surface, not the indicator tooltip.

**Manual sync trigger**: inline "Sync now" link in the synced-with-pending state for owner-initiated immediate sync where applicable (calendar, QuickBooks, mobile foreground; not background sync because background sync is OS-scheduled).

**Tunable threshold** (per §16.5 system-default-with-tenant-override pattern):
- Tenant setting `tenant_sync_indicator_pending_amber_threshold` (default 5; range 1–100)
- System default `system_sync_indicator_pending_amber_threshold`
- Effective resolution: tenant → system → fallback constant 5

**Real-time updates** via SSE per §13.11. State changes (sync starts, completes, errors, count changes) push to active web sessions.

**Component design** (frontend): `<InFlightSyncIndicator surface="calendar|quickbooks|mobile|background">` is a single shared React/Gluestack component with surface-specific data hooks. Extends the L3 background indicator from the states catalog (Tier 3 #8/#9) — base `<BackgroundIndicator>` provides state-colored dot; `<InFlightSyncIndicator>` adds count display, hover detail, manual trigger, threshold awareness.

**Surface-specific count semantics**:

- **Calendar sync** (§13.5): pending changes detected in `calendar_sync_pending_change`; pending pushes from Pilot to external; resolve target on error: `/settings/integrations/calendar/conflicts`
- **QuickBooks sync** (§5.4): pending changes in `integration_sync_pending_change` (filtered for QB); resolve target: `/settings/integrations/quickbooks/conflicts`
- **Mobile-to-web data sync** (§15): count of items in mobile sync queue; resolve target: mobile sync queue surface (web for owners; on-device for tech) plus owner field-issues queue
- **Background sync** (§15.13 + §17.10 push token integration): count of items pending background sync from `mobile_sync_pending_operation` filtered for the device

**Mobile owner status row integration** (per §16.9): the existing mobile owner status row pattern incorporates the pending count when greater than zero. Format: `🟢 QuickBooks sync · 2 pending · next sync 1m` or `🔴 Calendar sync · sync error · [Resolve on web →]`.

This pattern earns its place in §16 because it generalizes across all four sync surfaces and is explicitly extensible to any future bilateral-sync integration (Salesforce, HubSpot, generic webhooks). Phase 2 surfaces inherit this pattern by default.
```

---

## Edit 4 — §16.5 settings list expansion (around lines 2765–2786)

**Find** the existing "Settings using this pattern" sub-lists in §16.5.

**Replace the entire "Settings using this pattern" block** (everything from `**Settings using this pattern** (Pass 3):` through `is currently the only SMS-related tenant setting using §16.5; SMS quota itself...not a tenant override`) with this expanded version:

```markdown
**Settings using this pattern (Pass 3):**

- `calendar_conflict_auto_expire_days` / `system_calendar_conflict_auto_expire_days`
- `calendar_conflict_pre_warning_days` / `system_calendar_conflict_warn_days_before`

**Settings using this pattern (Pass 4 Tier 1):**

- `background_sync_push_interval_minutes` / `system_background_sync_push_interval_minutes` (per Pass 4 Tier 1 #3 Decision 4)
- `qb_auto_expire_*_enabled` family (per-entity-type for customers, quotes, invoices, expenses) (per Pass 4 Tier 1 #2 Decision 9)
- `qb_auto_expire_*_direction` paired settings (`accept_local | accept_remote` per entity type)
- `qb_auto_expire_days` / `system_qb_auto_expire_days` (default 60; Pass 4 Tier 1 #2 Decision 9)
- `qb_pre_warning_days` / `system_qb_pre_warning_days` (default 14)

**Settings using this pattern (Pass 4 Tier 1.5):**

- `sms_quota_cap_policy` (`soft | hard`; default `soft`; tenant-only override; per Tier 1.5 Decision 8)

**Settings using this pattern (Pass 4 Tier 2):**

- `voice_persona_tone` / system default `balanced` — tenant tone setting; per-user override allowed via three-tier resolution (per Tier 2 #6)
- `voice_persona_tone_user_override_allowed` — tenant policy whether per-user override is allowed (default TRUE; tenant-only)

**Settings using this pattern (Pass 4 Tier 4):**

- `tenant_sync_indicator_pending_amber_threshold` / `system_sync_indicator_pending_amber_threshold` (default 5; range 1–100; per §16.13)

**Pass 4 introduces a three-tier resolution chain extension** (per Settings IA framework Decision 6 / Tier 2 #4 Mockup C): some settings allow per-user overrides on top of the tenant + system tiers. The resolver helper extends to:

```python
def get_effective_setting_for_user(tenant_id, user_id, key, fallback=None):
    """Three-tier resolver: user → tenant → system → fallback."""
    if setting_allows_user_override(tenant_id, key):
        user_value = get_user_setting_override(tenant_id, user_id, key)
        if user_value is not None:
            return user_value
    tenant_value = get_tenant_setting(tenant_id, key)
    if tenant_value is not None:
        return tenant_value
    system_value = get_platform_setting(f"system_{key}")
    if system_value is not None:
        return system_value
    return fallback
```

**Settings allowing per-user override** (Pass 4 Tier 2):

- `voice_persona_tone` (per Tier 2 #6) — when `voice_persona_tone_user_override_allowed` is TRUE
- `background_sync_enabled` (per Tier 1 #3) — user can override own device behavior

User-level settings stored in `user_setting_override` table (per A53 from Tier 2 #4). Schema:

```sql
user_setting_override (
    tenant_id    UUID NOT NULL,
    user_id      UUID NOT NULL,
    setting_key  TEXT NOT NULL,
    value        JSONB NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL,
    updated_at   TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (tenant_id, user_id, setting_key)
)
```

Available for any future setting where personal preference is appropriate within tenant policy.
```

---

## Edit 5 — §4.5 MFA section expansion (lines 695–698)

**Find** the existing §4.5 (single sentence about MFA availability).

**Replace the entire §4.5 section** with this expanded version:

```markdown
### 4.5 Multi-Factor Authentication

MFA is available for all tenant users (owners, staff, technicians); tenant policy controls whether it's required. Optional for end-customers. Pass 4 Tier 2 #7 introduced full multi-method MFA infrastructure with self-service enrollment and tenant-required policy.

**Supported methods** (Cognito-backed):

- **TOTP** (authenticator apps — Google Authenticator, Authy, 1Password, Apple Passwords) — most secure
- **SMS OTP** — convenient but less secure; vulnerable to SIM swap attacks (surfaced honestly in user UI)
- **Email OTP** — convenient but vulnerable if email account itself is compromised

Users enroll any combination of the three methods at first MFA enrollment. Multi-method enrollment is encouraged via the wizard pattern ("Enroll all three for the strongest lockout protection") to prevent the "lost my phone, locked out" support scenario.

**Recovery codes**: 10 single-use codes generated at first enrollment, displayed once. Hashed via bcrypt before storage in `user_mfa_recovery_code` table. Regenerable on demand (invalidates prior unused codes). Used as ultimate lockout fallback when all enrolled methods are inaccessible.

**Schema** (per A69):

```sql
user_mfa_method (
    mfa_method_id          UUID PRIMARY KEY,
    tenant_id              UUID NOT NULL,
    user_id                UUID NOT NULL,
    method_type            TEXT NOT NULL,  -- 'totp' | 'sms' | 'email'
    enrolled_at            TIMESTAMPTZ NOT NULL,
    last_used_at           TIMESTAMPTZ NULL,
    cognito_method_id      TEXT NOT NULL,
    verification_status    TEXT NOT NULL,  -- 'verified' | 'needs_reverification'
    metadata               JSONB,          -- last 4 digits of phone, etc.
    UNIQUE (tenant_id, user_id, method_type)
)

user_mfa_recovery_code (
    code_id                UUID PRIMARY KEY,
    tenant_id              UUID NOT NULL,
    user_id                UUID NOT NULL,
    code_hash              TEXT NOT NULL,  -- bcrypt-hashed
    generated_at           TIMESTAMPTZ NOT NULL,
    used_at                TIMESTAMPTZ NULL,
    set_id                 UUID NOT NULL   -- groups codes generated together
)
```

**Login challenge flow**:

1. User submits username + password to existing Cognito flow
2. Server checks if MFA is required (per tenant policy or user enrollment) and if user has any methods
3. If multiple methods enrolled: server returns method-selection challenge; user picks one
4. If single method: server initiates challenge with that method directly
5. User enters 6-digit code from chosen method (or 10-character recovery code as escape)
6. Server verifies via Cognito; on success, login completes

**Wrong-code handling**: 5 wrong attempts on a single method locks that method for 15 minutes; user can try a different enrolled method or wait. Per-method lockout is intentional (vs. account lockout) — allows legitimate users with one bad TOTP guess to switch to SMS rather than being fully locked out. After 3 lockouts in 24 hours, account flagged for owner review (Phase 2 enforcement).

**Tenant-required MFA policy** (per A68):

- Tenant setting `tenant_mfa_required` (default FALSE; owner-only edit at `Settings > Users & Roles > Security policy`)
- Tenant setting `tenant_mfa_required_grace_period_starts_at` — populated when policy enabled; drives 7-day grace window
- Tenant setting `tenant_mfa_grace_period_days` (default 7)

**Grace period behavior**:

- Day 0: policy enabled; all tenant users have 7 days to enroll at least one MFA method
- Daily reminder push + email at 9 AM tenant local time during grace period
- During grace, warning banner persistent in app; user with valid session continues working
- Login-trigger enforcement: any login during grace activates immediate enrollment for that session
- After grace: every login by an unenrolled user forces enrollment before any other action

**Existing authenticated sessions**: continue working through grace period until next login. Preserves in-flight tech work; eventual enforcement is guaranteed because tokens eventually expire (refresh token TTL per §4.6).

**Owner reset of user MFA** (support escape hatch, per A69): owner can remove all MFA methods + recovery codes for any user via `Settings > Users & Roles > [user detail] > Reset MFA`. User re-enrolls on next login. Notifies user via email + push. Audit log captures actor and target. Owner self-reset of own MFA also supported (with password re-verification).

**Forced-minimum push for grace-period reminders**: per §22 Notification Preference Center, day-7 final reminder uses forced-minimum push (System announcements critical sub-trigger). Days 0–6 reminders use standard notification preferences (user can mute push if they want).
```

---

## Edit 6 — §5.4 QuickBooks Conflict Resolution update (lines 778–793)

**Find** the existing §5.4.

**Replace the section content** (from "Detection" through "Pass 4 work required") with:

```markdown
### 5.4 Conflict Detection & Resolution

**Detection** (in `services/quickbooks_sync.py::detect_conflict()`):

```python
qb_changed     = qb_token != mapping.external_version_token
pilot_changed  = customer.updated_at.isoformat() != mapping.internal_version_token
CONFLICT       = qb_changed AND pilot_changed
```

**Resolution UI** (Pass 4 Tier 1 #2; backend in A49–A50): The QuickBooks conflict resolution UI inherits the design vocabulary established in §13.5 calendar conflict resolution, formalized as the bilateral integration conflict resolution pattern in §16.10.

- Surface: `Settings > Integrations > QuickBooks > Conflicts`
- Side-by-side two-column diff with field-level track-changes highlighting per §16.2
- Master-aware column ordering: Pilot-left for Quote conflicts; QB-left for Invoice conflicts; tenant override determines for Customer/Expense
- Two-button bottom action bar with master-aware primary-button treatment
- Deletion-conflict variants with distinct verb-based treatment (parallel to §13.5)
- Pre-commit staleness check per §16.4 with three 409 payload types: `server_changed`, `auto_recovered`, `stale`
- Voice scope: status-query-only via `list_pending_qb_conflicts` voice intent (per §6.2). No voice resolution due to accounting integrity stakes — refusal-with-redirect for resolution attempts.

**Schema extensions to `integration_sync_conflict`** (per A49):

```sql
ALTER TABLE integration_sync_conflict ADD COLUMN base_snapshot JSONB NOT NULL;
ALTER TABLE integration_sync_conflict ADD COLUMN field_diffs JSONB NOT NULL;
ALTER TABLE integration_sync_conflict ADD COLUMN pilot_modified_at TIMESTAMPTZ NOT NULL;
ALTER TABLE integration_sync_conflict ADD COLUMN pilot_modified_by_user_id UUID NULL;
ALTER TABLE integration_sync_conflict ADD COLUMN qb_modified_at TIMESTAMPTZ NOT NULL;
ALTER TABLE integration_sync_conflict ADD COLUMN qb_modified_by_external_user_label TEXT NULL;
ALTER TABLE integration_sync_conflict ADD COLUMN auto_expire_at TIMESTAMPTZ NULL;
ALTER TABLE integration_sync_conflict ADD COLUMN pre_warning_at TIMESTAMPTZ NULL;
```

**Resolution paths**:

- `accept_local` — push Pilot snapshot to QB
- `accept_remote` — write QB snapshot to Pilot
- `restore_and_accept_remote` — for `Deleted ↔ Modified`: restore Pilot entity from QB
- `recreate_and_keep_local` — for `Modified ↔ Deleted`: push Pilot snapshot back to QB
- `delete_both` — accept the deletion in both systems

**Per-entity auto-expiry** (per A50, Tier 1 #2 Decision 9): unlike calendar's ON-by-default, QB auto-expiry is OFF by default for all four entity types (Customers, Quotes, Invoices, Expenses) — accounting integrity stakes are higher and masters are heterogeneous. Tenants opt in per entity type with paired enable + direction settings (`qb_auto_expire_{entity}_enabled` + `qb_auto_expire_{entity}_direction`). When enabled, auto-expiry timing uses `qb_auto_expire_days` (default 60 — longer than calendar's 30 because accounting cadence is quarterly) and `qb_pre_warning_days` (default 14). Settings UI uses save-on-group-complete pattern (per Settings IA framework Decision 5) to prevent half-baked enable-without-direction state.

**Invoice-specific financial-delta callout** (per Tier 1 #2 Decision 6): for invoice conflicts only, the resolution view includes a financial-delta callout above the diff showing total amount delta, AR impact preview, tax-period spanning warning when applicable, and a deep-link out to the invoice in QB's web UI. This recognizes that invoice conflicts have downstream financial consequences (AR balances, tax filing) that calendar/customer/expense conflicts don't have.

**In-Flight Sync Indicator** (per §16.13): the QuickBooks sync surface uses the platform-wide pattern with QB-specific count semantics (pending entity changes in either direction).

**Auto-expiry Celery task**: `auto_expire_qb_conflicts_per_tenant` (per §3.2). Hourly cadence. Reads tenant per-entity settings, fires pre-warning notifications at `pre_warning_at`, commits to tenant-configured direction at `auto_expire_at`.
```

---

## Edit 7 — §6.2 Voice Intent Registry additions (around line 916)

**Find** the existing intents tables in §6.2. The last existing intent table ends with the calendar conflict resolution intents (around line 925).

**Add these new intent tables** at the bottom of §6.2 (after the calendar resolution table):

```markdown
**Field issue resolution intents** (Pass 4 Tier 1 #1 — confirm-as-turn applies; refusal-with-redirect for deletion-conflict variants):

| Intent | Handler | Example Utterance |
| :--- | :--- | :--- |
| `list_pending_field_issues` | `list_pending_field_issues_via_voice` | "Do I have any field issues?" |
| `resolve_field_issue` | `resolve_field_issue_via_voice` | "Resolve Mike's time entry — use his version" |

**QuickBooks conflict status intents** (Pass 4 Tier 1 #2 — status-query only; no voice resolution per Tier 1 #2 Decision 8):

| Intent | Handler | Example Utterance |
| :--- | :--- | :--- |
| `list_pending_qb_conflicts` | `list_pending_qb_conflicts_via_voice` | "Do I have any QuickBooks conflicts?" |

**Customer SMS reply intents** (Pass 4 Tier 1.5 — confirm-as-turn applies; always-preview-before-send per §16.7):

| Intent | Handler | Example Utterance |
| :--- | :--- | :--- |
| `reply_to_customer_sms` | `reply_to_customer_sms_via_voice` | "Reply to John saying running 30 minutes late" |

**Help intents** (Pass 4 Tier 4 #14 — routes to AI-mediated help with RAG context):

| Intent | Handler | Example Utterance |
| :--- | :--- | :--- |
| `open_help` | `open_help_via_voice` | "Open help" / "I have a question" |
| `ask_help_question` | `ask_help_question_via_voice` | "Help me with QuickBooks setup" / "How do I create a quote?" |
```

---

## Edit 8 — §3.2 Celery Beat Schedule additions (around lines 534–551)

**Find** the existing Celery Beat schedule table.

**Add these new task rows** at the bottom of the table (after `notify-system-template-updates`):

```markdown
| `auto-expire-qb-conflicts` | `auto_expire_qb_conflicts_per_tenant` | Hourly | Per-tenant QB conflict auto-expiry per `qb_auto_expire_{entity}_enabled` + `qb_auto_expire_{entity}_direction`; sends pre-warnings — see §5.4 |
| `monitor-sms-quota-thresholds` | `monitor_sms_quota_thresholds` | Hourly | Detect 80% and 100% SMS quota thresholds; dispatch notifications per Tier 2 #5 Billing category — see §17.6 |
| `rollover-sms-quota-periods` | `rollover_sms_quota_periods` | Daily | Create new `sms_quota_period` row at subscription billing cycle boundaries — see §17.6 |
| `enforce-trial-expirations` | `enforce_trial_expirations` | Hourly | Transition expired trials to `trial_expired` state; dispatch paywall notifications — see §20 (Subscription Tier Architecture) |
| `notify-mfa-grace-period-reminders` | `notify_mfa_grace_period_reminders` | Daily at 9 AM tenant local time | Per-tenant MFA enrollment reminders during grace period; daily-escalating copy from gentle (days 0–3) to urgent (days 4–6) to critical (day 7) — see §4.5 |
| `process-help-article-embeddings` | `process_help_article` | Event-driven (S3 upload) + weekly fallback | Re-embed help corpus chunks into pgvector when markdown content changes — see §19 (Help System Architecture) |
| `anonymize-help-sessions` | `anonymize_help_sessions` | Daily | Anonymize help chat sessions older than 90 days; PII detection + tenant-data scrubbing; roll into training corpus — see §19 |
| `cleanup-incomplete-stripe-payment-intents` | `cleanup_incomplete_stripe_payment_intents` | Daily | Clean up abandoned Stripe Payment Intents older than 24 hours that didn't complete |
```

**Add corresponding entries to §3.3 Task Modules** (around lines 555–570):

```markdown
| `tasks/qb_conflict_expiry.py` | `auto_expire_qb_conflicts_per_tenant` — auto-resolves stale QB conflicts per per-entity tenant configuration (§5.4) |
| `tasks/sms_quota.py` | `monitor_sms_quota_thresholds`, `rollover_sms_quota_periods` — SMS quota tracking + threshold notifications + period boundaries (§17.6) |
| `tasks/trial_management.py` | `enforce_trial_expirations` — transitions expired trials and dispatches paywall (§20) |
| `tasks/mfa_reminders.py` | `notify_mfa_grace_period_reminders` — daily escalating MFA enrollment reminders (§4.5) |
| `tasks/help_corpus.py` | `process_help_article` (event-driven), `anonymize_help_sessions` — help corpus embedding + chat session anonymization (§19) |
| `tasks/stripe_cleanup.py` | `cleanup_incomplete_stripe_payment_intents` — abandoned Stripe payment intent cleanup |
```

---

## Edit 9 — §13.5 calendar conflict resolution generalization note

**Find** the §13.5 section header (line 1971): `### 13.5 Bi-Directional Calendar Sync`

This section is comprehensive but doesn't explicitly call out that it serves as the reference instance of the bilateral integration conflict resolution pattern (§16.10). Add a short cross-reference paragraph at the top of §13.5.

**Find** (line 1973):

```markdown
The sync strategy closely mirrors the QuickBooks bi-directional pattern documented in Section 5. Modifications happen in both Pilot and the external calendar; a collision resolver handles conflicts.
```

**Replace with**:

```markdown
The sync strategy closely mirrors the QuickBooks bi-directional pattern documented in Section 5. Modifications happen in both Pilot and the external calendar; a collision resolver handles conflicts.

This section serves as the reference instance of the **bilateral integration conflict resolution pattern** (§16.10). The QuickBooks integration (§5.4) inherits this same pattern. Future bilateral integrations (Salesforce, HubSpot, generic webhook integrations) inherit by default with deviations requiring explicit justification per §16.10. Pattern attributes are domain-determined: calendar's auto-expiry default is ON because the master is unambiguous; QB's is OFF because masters are heterogeneous. Calendar supports voice resolution because stakes are time-shifted; QB does not because accounting integrity stakes are higher.
```

---

## Edit 10 — Cost Analysis Pass 4 close additions (around line 3148)

**Find** the existing Cost Analysis section (lines 3148–3196).

**Add new line items** to the Total Infrastructure Cost table. Insert after the existing `**SMS Infrastructure**` block (after line 3166):

```markdown
| **Stripe Processing** | Subscription billing fees (~2.9% + $0.30 per transaction) | est. ~$200 |
| | One-time invoice payment fees (~2.9% + $0.30) | est. ~$50 |
| **Subtotal Stripe** | | **~$250** (passed through to tenants in pricing; not net cost to Pilot) |
| **AI Help System** | OpenAI text-embedding-3-small (corpus: ~$1 one-time + queries) | $5 |
| | S3 help corpus storage | $2 |
| **Subtotal AI Help** | | **$7** |
```

**Update the GRAND TOTAL**:

**Find** (line 3178):

```markdown
| **GRAND TOTAL** | | **~$881/month** |
```

**Replace with**:

```markdown
| **GRAND TOTAL** (excluding pass-through Stripe fees) | | **~$888/month** |
```

**Update per-customer cost lines** (lines 3180–3181):

```markdown
**Per-customer cost:** $8.88/month
**Gross margin at $149/month:** 94.0%
```

**Add a Pass 4 close cost delta paragraph** after the existing Pass 4 Tier 1.5 cost delta:

```markdown
**Pass 4 close cost delta from Pass 4 Tier 1.5 baseline ($881/month)**:

- AI Help System added: $7/month for OpenAI embeddings (corpus + query embeddings) + S3 help corpus storage. Embedding model alternative (open-source Sentence-BERT) is feasible if avoiding OpenAI dependency is preferred, with ~equivalent monthly cost
- Stripe Processing fees are pass-through (tenant pays via subscription pricing or invoice surcharge); not net cost to Pilot but worth tracking — estimated $250/month at 100-tenant aggregate volume
- One-time costs not in monthly recurring: A2P 10DLC registration (~$50 brand + per-campaign fees), Stripe account setup, domain registration (`pilotfortrades.com`, optional `pilot.tr` short link), SendGrid sender domain SPF/DKIM/DMARC setup
```

**Update the Scaling Economics table**:

```markdown
| Scale | Monthly Cost | Per-Customer Cost | Gross Margin (at $149) |
| :--- | :--- | :--- | :--- |
| 100 customers | $888 | $8.88 | 94.0% |
| 500 customers | $1,672 | $3.34 | 97.8% |
| 1,000 customers | $2,957 | $2.96 | 98.0% |
```

(SMS scales linearly, AI Help embedding queries scale with active help usage but query embedding cost is negligible at scale.)

---

## Verification checklist after Round 1 edits

- [ ] Doc header version bumped to v5 (Edit 1; also fixes the duplicated `**Version**:` typo)
- [ ] §16.1 Pattern Inventory expanded to 15 patterns (Edit 2)
- [ ] §16.13 In-Flight Sync Indicator new section inserted before §17 (Edit 3)
- [ ] §16.5 settings list expanded with Pass 4 Tier 2/4 settings + three-tier resolution chain extension (Edit 4)
- [ ] §4.5 MFA section expanded from 1 sentence to comprehensive Pass 4 Tier 2 #7 architecture (Edit 5)
- [ ] §5.4 QB Conflict Resolution updated to reflect Tier 1 #2 implementation (no longer "Pass 4 work required") (Edit 6)
- [ ] §6.2 Voice Intent Registry has 4 new intent tables for Pass 4 (Edit 7)
- [ ] §3.2 Celery Beat Schedule has 8 new task rows + §3.3 Task Modules has 6 new file entries (Edit 8)
- [ ] §13.5 has cross-reference paragraph noting it's the reference instance of §16.10 (Edit 9)
- [ ] Cost Analysis has Stripe + AI Help line items + Pass 4 close cost delta (Edit 10)

---

## Items I want to flag as still needing content (Round 2)

After you confirm Q1 and Q2 above, Round 2 produces paste-ready blocks for:

**The new chapter content** (depending on your Q1 organizational choice):
- **§19 (or extension) Help System Architecture** — RAG pipeline, S3 corpus structure, embedding model, chat session capture, anonymization pipeline, voice integration
- **§18 (or extension) Customer-Facing Public Surfaces** — signed URL infrastructure, email branding, Stripe one-time payment with variance, customer comments storage, public link expiration
- **§20 (or extension) Subscription Tier + Stripe Subscription Architecture** — tier table, trial-as-tier, operator overrides, Stripe Subscriptions integration, webhooks, payment failure handling
- **§21 (or extension) Onboarding State Machine Architecture** — wizard state machine, legal acceptance recording, post-wizard checklist auto-completion detection, resumability
- **§22 (or extension) Notification Preference Center Architecture** — category registry, sub-trigger metadata, per-recipient delivery dispatcher gate, in-app banner channel, forced-minimum semantics
- **§23 (or extension) Account Settings Architecture** (likely consolidates with §4.5) — active sessions data model, data export pipeline, profile management, password change cross-device session invalidation

**Operator role + hidden Pilot routes** — small section flagging the operator-only RBAC tier and the path-based access control for `/admin/*` routes (or equivalent). Per Tier 3 #10 / Settings IA framework Decision 8 / Tier 4 #14 admin help corpus editing.

**Stripe Connect architectural decision** flagged as Phase 2 review point (per Tier 4 #13 Cross-Domain B). Worth a short note in Round 2's subscription chapter.

---

## Two questions to confirm before I generate Round 2 content

1. **Q1 organizational choice**: A (many new chapters), B (consolidate into existing), or C (hybrid — recommended)
2. **Q2 scope of Round 2**: produce all new chapter content in one large doc, or phase further (e.g., split into two rounds — Round 2A: customer-facing + help; Round 2B: subscription + onboarding + notification preferences + account settings)

Tell me your answers and I'll generate the appropriate Round 2 blocks.

In the meantime, applying Round 1 (these 10 edits) gets your arch doc substantially closer to v5 — most of the structural fixes and the small but critical content updates will be in place.
