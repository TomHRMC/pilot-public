# Pilot for Trades Design System — Pass 4, Tier 2 #5: Notification Preference Center

**Version**: 1.0
**Status**: Locked
**Date**: April 27, 2026
**Author**: Tom (Founder) with Claude
**Scope**: Per-user, per-category, per-channel notification preference matrix UI. Tenant defaults plus user overrides plus forced-minimum semantics for safety-critical categories. Inherits all three Tier 2 #4 canonical mockups; the matrix UI itself is the only net-new design problem.
**Depends On**: Settings IA framework · Tier 2 #4 (Mockups A and C) · Tier 1.5 Flow 4 customer comms extension (forced-minimum push for Customer activity) · `mvp-arch.md` §3.7 Notifications & Comms · §13.11 Server-Sent Events · A35 (notification rate limiting) · A51 (push token registry)
**Backend additions**: A56 (notification category registry), A57 (preference matrix endpoints + in-app banner component), A58 (delivery dispatcher preference gate)
**Deliverable shape**: Shape C (Settings IA + per-setting spec) per Pass 4 framework doc

---

## Purpose

Notifications fire from many places across Pilot — quote approval requests, ETC variance alerts, calendar conflicts, mobile escalations, QB conflicts, dispatch changes, customer SMS replies, payments, sync alerts, system announcements. Today, each firing site uses `notification_outbox` directly with no per-user filtering: every owner gets every notification on every channel that's wired up. This is acceptable for solo operators but breaks down for multi-user shops where each user wants different categories on different channels.

Tier 2 #5 designs the preference matrix that gives each user control over what they receive and how. The hard work is two-fold: (1) consolidating roughly a dozen raw notification firing sites across Pass 1–4 surfaces into a smaller list of user-meaningful categories that fit a comprehensible matrix, and (2) defining the forced-minimum semantics for safety-critical categories where allowing user mute would create operational holes.

This spec also locks the **notification category registry** as canonical infrastructure — every backend firing site classifies its notifications into one of the eight categories. Without consistent classification, preferences can't be respected.

The in-app banner channel is partially new — SSE infrastructure exists for real-time delivery, but the banner UI component and the notification center bell don't exist yet. This spec formalizes the in-app banner as a third channel and captures the new component work in A57.

## Strategic direction

### The matrix UI is the easy part; the category list is the design problem

Rendering 8 categories × 3 channels = 24 cells in a table is straightforward. The real work is consolidating ~12 raw notification firings across Pass 1–4 surfaces into a smaller list of user-meaningful categories that users can reason about without a 30-row matrix. Decision 2 below locks this consolidation.

### Tenant default + user override — the three-tier pattern from Tier 2 #4

The notification preference matrix uses the three-tier resolution chain from Tier 2 #4 Mockup C. Tenant sets a default policy per category × channel; user can override their own preferences within tenant policy. Pilot ships with system defaults that tenants can override; users override within tenant boundaries. Three-tier resolution: user → tenant → system → fallback.

### Critical-path notifications cannot be fully disabled — but the semantics are user-context-dependent

Some notifications are operational requirements, not preferences. A tech being assigned a job needs to see the assignment; an owner-required quote approval can't sit invisible because the owner muted it; a tech in a customer SMS conversation needs to see customer replies. These categories have a forced-minimum push.

**Critically: forced-minimum semantics are user-context-dependent for some categories.** Customer activity (per Tier 1.5) has forced-minimum push *only for the tech in the conversation*; owners receiving ambient-awareness notifications about other techs' conversations can mute push. This asymmetric forced-minimum pattern is new to Pilot and lives in Decision 4.

### No quiet hours, no digests in MVP

Real features that real users will eventually want, but they're scope creep for MVP. Category-level toggles are the MVP control surface. Phase 2 adds time-of-day rules and digest delivery. Decision 9 documents the deferral explicitly.

### Channel infrastructure is admin-scoped, separate from preference UI

Setting up "what's our SendGrid sender domain?" is admin work that lives at `Settings > Integrations > Notification channels`. Per-user "do I want email for quote approvals?" lives at `Settings > Notifications > Preferences`. Same noun, two different surfaces, two different scopes. The Settings IA framework already established this split; this spec confirms it.

## Locked design decisions

### 1. Channel set — three channels for inbound user notifications

**Decision**: Three channels, all inbound to the logged-in user:

| Channel | Source infrastructure | Notes |
| :--- | :--- | :--- |
| **Push** | A51 mobile push token registry; APNs (iOS) + FCM (Android) | Per-device per-user; uses A51 push token registry from Tier 1 #3 |
| **Email** | SendGrid via existing `notification_outbox` infrastructure | Sent to user's account email; existing infrastructure |
| **In-app banner** | New component A57; backed by SSE per arch doc §13.11 | Renders in app shell while user is active; notification center bell archives last 50 |

SMS is **not** an inbound user channel for Pilot users (it's outbound-to-customer per Tier 1.5). Reasons: SMS provider cost, redundancy with push for actively-using mobile users, separate regulatory/compliance overhead.

**In-app banner is partially net-new infrastructure**: SSE delivery exists per arch doc §13.11, but the banner UI component and notification center bell are new work captured in A57.

**Rationale**: Three channels cover the realistic preference space — "I want to know now and away from screen" (push), "I want a record I can reference later" (email), "I want to know while I'm working but don't want to leave my current page" (in-app banner). Adding SMS would mean a fourth channel with a meaningful per-message cost; the user value over push for actively-using-the-app users is marginal.

### 2. Category list — eight user-meaningful categories

**Decision**: Eight categories that consolidate the underlying notification firings:

| Category | What fires here (sub-triggers) | Source surfaces |
| :--- | :--- | :--- |
| **Quote approvals** | Tech submits quote for approval; owner approves / declines; quote expires while pending | Flow 5 (quote approval workflow) |
| **Field issues** | Mobile escalation sent to owner; owner resolves an escalation (loop closure to tech); escalation auto-recovers during owner triage | Tier 1 #1 (owner mobile-conflict resolution) |
| **Sync conflicts** | Calendar sync conflict detected; QB sync conflict detected; auto-expiry pre-warning fires; auto-resolve completes | Flow 6 (calendar) and Tier 1 #2 (QuickBooks) |
| **Job activity** | Job assigned to tech; job status changed; ETC variance exceeds owner-notify threshold; dispatch reassignment | Flow 2 (profitability), Flow 3 (dispatch board), A1 |
| **Customer activity** | Customer replies to outbound SMS (Tier 1.5); customer accepts or declines a quote; customer-initiated webhook arrives; customer marks an outbound message as STOP/opt-out | Flow 4 + Tier 1.5 (customer comms), Flow 5 (quote acceptance) |
| **Billing** | Invoice sent successfully; payment received; payment failed; subscription renewed; SMS quota threshold (80%, 100%); SMS overage incurred | A4 (existing invoice infrastructure); Tier 1.5 (SMS quota) |
| **Background sync alerts** | Persistent background sync failure (>3 consecutive); auth expired while offline; storage limit reached | Tier 1 #3 (background sync), Flow 7 (offline operations) |
| **System announcements** | Pilot platform announcements (planned downtime, new features, breaking changes, security incidents) | Pilot operator |

**Consolidation note**: I considered finer categorizations (separate "ETC variance" from "job assignment," separate "QB conflicts" from "calendar conflicts") but consolidated where the underlying decision the user is making is the same. A tech who wants push for "anything happening on my jobs" doesn't want to think about whether ETC variance is a separate category from reassignment. Eight categories is the empirical sweet spot for a matrix that fits one screen.

**Categories explicitly NOT separated**:
- Quote approvals vs quote expiry → both under Quote approvals
- Calendar vs QB conflicts → both under Sync conflicts (the user-relevant fact is "sync needs my attention," not which integration)
- Job assignment vs reassignment vs ETC variance → all under Job activity
- Different billing event types (invoice send, payment, SMS quota) → all under Billing
- Customer SMS reply vs customer quote acceptance → both under Customer activity (the user-relevant fact is "the customer is engaging with us")

### 3. Default policy — Pilot system defaults per category × channel

**Decision**: Each category × channel cell has a Pilot-set system default. Tenants override defaults; users override within tenant policy.

**Default policy (Pilot system defaults)**:

| Category | Push | Email | In-app |
| :--- | :---: | :---: | :---: |
| Quote approvals | ON | ON | ON |
| Field issues | ON | ON | ON |
| Sync conflicts | OFF | ON | ON |
| Job activity | ON | OFF | ON |
| **Customer activity** | **ON** | OFF | ON |
| Billing | OFF | ON | ON |
| Background sync alerts | ON | OFF | ON |
| System announcements | OFF | ON | ON |

**Pattern in the defaults**:
- Push defaults ON for things the user needs to act on relatively quickly (approvals, escalations, jobs, customer activity, sync alerts)
- Push defaults OFF for things with longer time horizons or reference-material nature (sync conflicts, billing, system announcements) — email is the better channel
- Email defaults ON for everything with a paper-trail dimension (approvals, escalations, billing, sync conflicts, system announcements)
- In-app banner defaults ON for everything (lowest-cost channel; ambient awareness; user can dismiss without leaving current page)

**Tenant override** can re-set defaults per category × channel. Example: a tenant operating in cellular-restricted environments might set Job activity push default to OFF tenant-wide.

**User override** can be set per category × channel within the constraints of forced-minimum (Decision 4) and tenant policy.

### 4. Forced-minimum categories — push always on, with user-context asymmetry

**Decision**: Four categories have a forced-minimum push that cannot be turned off by user override. Email and in-app remain user-configurable for these. **Three of the four have uniform forced-minimum across all users; one has user-context-dependent semantics.**

| Category | Forced-minimum scope | Rationale |
| :--- | :--- | :--- |
| **Field issues** | All users (the originating tech and resolving owner both need timely awareness) | The originating tech needs to know when their captured work is resolved; the owner needs to know about new escalations |
| **Job activity (assignment-only sub-trigger)** | The tech being assigned (only) | The tech needs to know they've been assigned a new job; reassignment, ETC variance, and status changes are NOT forced-minimum |
| **System announcements (critical-only sub-trigger)** | All users | Security incidents, breaking-change deployments — Pilot operator can mark an announcement as "critical" forcing push delivery; non-critical announcements use the standard preference resolution |
| **Customer activity (inbound SMS reply sub-trigger only)** | The tech in the conversation thread (only) | Per Tier 1.5 — the tech in the conversation needs to see customer replies in time to act; customer SMS replies are forced-minimum push for the originating tech only. **Owners receiving ambient-awareness Customer activity notifications about other techs' conversations are NOT forced — they can mute push.** |

The user can still turn email and in-app banner off for these categories. Tenant override cannot suppress the forced-minimum either — it's a Pilot platform invariant.

**The user-context asymmetry for Customer activity is new vocabulary for Pilot.** Same category, different forced-minimum semantics depending on who's receiving:
- *Tech in the conversation:* push is forced minimum (cannot mute)
- *Owner receiving ambient awareness about another tech's conversation:* push is fully mutable
- *Other techs not in the conversation:* not in the recipient list at all

Implementation: A58's delivery dispatcher gates each user-channel pair against the forced-minimum check, evaluating per-recipient. If the recipient is the originating tech AND the trigger is "inbound SMS reply" AND the channel is push → forced-minimum applies; otherwise standard preference resolution.

**UI treatment**: when the user attempts to turn off a forced-minimum cell:
- The toggle resists the change
- An inline explainer surfaces below the toggle: "*Push for [Customer activity] can't be turned off when you're the tech in a conversation — you need to see customer replies. Email and in-app banners are still configurable.*"
- For the owner viewing Customer activity in the matrix UI, the cell shows as fully editable (no lock icon) because the forced-minimum doesn't apply to them
- The cell renders with a small lock glyph and `(locked)` annotation only for users where forced-minimum applies

**Rationale**: Some notifications aren't preferences, they're operational requirements. The alternative — letting users mute genuinely operational alerts — creates support burden ("why didn't anyone tell me?") and undermines trust in the platform's communication layer. The user-context asymmetry handles the realistic case where the same category contains both must-see (for the tech in the conversation) and informational (for the ambient-awareness owner) sub-triggers.

**Scope discipline**: only four categories qualify, and three have uniform semantics. ETC variance, sync conflicts, billing — none qualify. Users can mute those entirely if they want.

### 5. Matrix UI layout — web

**Decision**: A single tabular page at `Settings > Notifications > Preferences` rendering 8 categories × 3 channels = 24 cells. Layout:

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Notification preferences                                                 │
│ ─────────────────────────                                                │
│                                                                          │
│ Choose how you want to be notified for each category. Tenant defaults    │
│ shown when you haven't set your own preference.                          │
│                                                                          │
│ [ Mute all push (non-critical) ]  [ Mute all email ]  [ Reset to default ]│
│                                                                          │
│                              Push        Email       In-app              │
│                            ─────────   ─────────   ─────────             │
│ Quote approvals            [ ● on ]    [ ● on ]    [ ● on ]              │
│   Tenant default: on         (default)   (default)   (default)           │
│                                                                          │
│ Field issues               [ 🔒 on ]   [ ● on ]    [ ● on ]              │
│   Tenant default: on         (locked)    (default)   (default)           │
│                                                                          │
│ Sync conflicts             [ ◯ off ]   [ ● on ]    [ ● on ]              │
│   Tenant default: on         (your)      (default)   (default)           │
│                            [ Match tenant default ]                      │
│                                                                          │
│ Customer activity (you)    [ 🔒 on ]   [ ● on ]    [ ● on ]              │
│   Push locked when in        (locked)    (default)   (default)           │
│   a conversation                                                         │
│                                                                          │
│ Customer activity          [ ● on ]    [ ● on ]    [ ● on ]              │
│ (other techs)                (default)   (default)   (default)           │
│                                                                          │
│ Job activity               [ 🔒 on ]   [ ● on ]    [ ● on ]              │
│   Push locked for            (locked)    (default)   (default)           │
│   new assignments only                                                   │
│                                                                          │
│ ...                                                                      │
└──────────────────────────────────────────────────────────────────────────┘
```

**Visual treatment per cell**:
- **Toggle on / off** — inherits Tier 2 #4 toggle component
- **Annotation below toggle** — small text indicating the value's scope: `(default)` for system default, `(tenant)` for tenant override, `(your)` for user override, `(locked)` for forced-minimum where the rule applies to this user
- **Forced-minimum cells** — lock glyph; toggle resists state change per Decision 4; explainer text appears below the row
- **Per-row revert link** — small "Match tenant default" link below the row when any cell in the row has a user override; clicking reverts all three cells in the row to inherit tenant value
- **Per-cell revert** — clicking the annotation `(your)` opens a small popover with "Revert to tenant default" affordance

**User-context asymmetric categories** (Customer activity, per Decision 4): rendered as **two separate rows** in the matrix:
- "Customer activity (you)" — for messages where the user is the tech in the conversation; push is locked
- "Customer activity (other techs)" — for ambient-awareness notifications about other techs' conversations; push is editable

This is the cleanest way to surface the asymmetric semantics. The alternative — a single row with a complex disclosure — is harder to reason about. Two rows is verbose but clear. For users who never receive ambient-awareness customer activity (e.g., a tech who's not also an owner), the second row simply doesn't render.

**Page-level controls** at the top of the page:
- **"Mute all push (non-critical)"** — sets push to OFF across all non-forced-minimum categories (user override layer); does not change tenant policy
- **"Mute all email"** — same for email
- **"Reset to tenant defaults"** — clears all user overrides for this user

The "non-critical" qualifier on the push mute makes clear that forced-minimum push categories aren't affected; users won't expect "mute all push" to suppress field-issue alerts.

**Save behavior**: Save-on-blur per Settings IA framework Decision 5. Each cell saves independently when toggled. Optimistic UI per arch doc §16.8.

**Rationale**: The matrix is dense but bounded — 24 cells fit comfortably on one page even at typical web viewport sizes. Adding the user-context-asymmetric Customer activity row brings the total to 9 visible category rows for users who can receive both contexts (owners). Per-row revert is a usability nicety for the common case "I muted this whole category, now I want it back to defaults." Per-cell revert handles the precision case. Page-level controls handle "I'm focusing for two hours, kill push" without forcing 8 individual toggles.

### 6. Matrix UI layout — mobile

**Decision**: Mobile renders the same matrix at `Mobile > Settings > My Account > My notification preferences`. Layout adapts to phone width — vertical stack within categories instead of horizontal triple:

```
┌─────────────────────────────────┐
│ Notification preferences        │
│ ─────────────────────────       │
│                                 │
│ Quote approvals                 │
│   Push       [ ● on ]           │
│   Email      [ ● on ]           │
│   In-app     [ ● on ]           │
│   ─                             │
│                                 │
│ Field issues                    │
│   Push       [ 🔒 on ]          │
│     Locked                      │
│   Email      [ ● on ]           │
│   In-app     [ ● on ]           │
│   ─                             │
│                                 │
│ Customer activity (you)         │
│   Push       [ 🔒 on ]          │
│     Locked when in a            │
│     conversation                │
│   Email      [ ● on ]           │
│   In-app     [ ● on ]           │
│   ─                             │
│                                 │
│ ...                             │
└─────────────────────────────────┘
```

Each category becomes a vertical stack of three rows on mobile (one per channel) instead of a horizontal triple. Save behavior, scope annotations, and forced-minimum lock treatment all inherit unchanged. The user-context asymmetric Customer activity rendering becomes "Customer activity (you)" / "Customer activity (other techs)" as separate category cards.

Page-level controls render as a horizontal action bar at the top of the page (before the first category card).

**Rationale**: 8-row × 3-column matrix doesn't fit phone width comfortably. Vertical stack within categories preserves the mental model (which category am I configuring?) without requiring horizontal scroll. Category boundary marked with thin separator.

### 7. Per-tenant default editing — owner-only sub-surface

**Decision**: A separate sub-page at `Settings > Notifications > Tenant defaults` lets owners edit the tenant-level defaults that all users inherit. This is **separate from** the per-user preference matrix to avoid confusion between "I'm setting my own preferences" and "I'm setting the team's defaults."

**Layout**: same matrix structure as Decision 5 / 6, but:
- Edits affect tenant-level defaults, not the owner's user override
- All cells render as `(default)` when matching system defaults or `(tenant)` when overridden from system
- A "Reset to system defaults" page-level control reverts all tenant overrides to inherit Pilot system defaults
- Forced-minimum semantics are visible but display as `(platform default)` rather than `(locked)` — tenants can't override the forced-minimum because it's a platform invariant

**RBAC**: only `owner` and `accountant` roles can access this page.

**Rationale**: Mixing tenant-default editing with personal-preference editing on the same page would create scope confusion. Two separate pages, each focused on a single decision scope.

### 8. In-app banner channel UX

**Decision**: The in-app banner is a slim slide-down notification that appears at the top of the active page when a notification arrives via SSE (per arch doc §13.11). Auto-dismisses after 6 seconds; manually dismissable; clickable to navigate to the relevant entity.

**Component behavior**:
- **Trigger**: SSE event arrives for the active session with notification payload
- **Render**: slides down from top of page; brand-indigo accent stripe on the left edge; category icon + brief message + dismiss X
- **Auto-dismiss**: 6 seconds for non-critical; 12 seconds for critical (e.g., field issue escalations)
- **Click action**: navigates to the relevant entity (e.g., field issue resolution view, customer thread, quote approval detail)
- **Stacking**: maximum 3 banners visible simultaneously; oldest dismisses when a new one arrives if at capacity
- **Disabled when on a quiet page**: certain pages (e.g., the dispatch board's full-screen mode, voice command listening state) suppress banners temporarily; banners queue for when normal UI returns

**Notification center bell** (companion surface):
- Bell icon in the app shell (web header, mobile top bar)
- Badge count of unread in-app notifications from the last 24 hours
- Tapping the bell opens a panel with the last 50 in-app notifications, each clickable to navigate to the entity
- Notifications older than 24 hours archived but still accessible via the panel
- Mark-as-read on click; clearable per-notification; "mark all read" affordance

**Mobile and web parity**: banner component is shared between web and mobile. Slight visual variation for mobile width but same behavior model.

**Rationale**: The in-app banner gives ambient awareness without requiring users to leave their current task. The bell provides historical reference for users who dismissed banners or were away from screen when they fired. Together they form the in-app channel — neither alone is sufficient (banners are ephemeral; bell is non-disruptive). The 6-second / 12-second dismissal timing balances visibility against intrusion.

### 9. Phase 2 deferrals (locked)

**Quiet hours** — per-user time-of-day rules. Real demand. Phase 2.

**Digest delivery** — daily/weekly email summaries instead of per-event. Phase 2.

**Per-event-instance preferences** — "for *this specific* QB invoice conflict, send me a push." Phase 2.

**Notification routing rules** — "send Field issues to my owner email, not my personal email." Phase 2; requires multi-email-per-user infrastructure.

**Per-tech notification routing for owners** — "notify me when *this specific tech* hits ETC variance." Phase 2.

**Notification snoozing** — "mute push for 4 hours then resume." Phase 2.

**Channel priority / fallback** — "if push fails, fall back to email." Phase 2; current model is independent channels.

**Notification analytics** — opt-out heatmap, most-changed preferences. Phase 2.

**Tenant-wide preference templates** — "apply 'field tech' template to all newly added users." Phase 2.

**Slack / Microsoft Teams as inbound channels** — Phase 2; would need OAuth integration parallel to QB / Calendar.

**SMS as inbound user channel** — explicit MVP scope cut per Tier 1.5; SMS is outbound-to-customer only.

### 10. Matrix UI proportionality vs. growth

**Decision**: The 8-category list is sized for MVP. As Phase 2 adds new categories, the matrix must remain navigable.

**Threshold**: when category count reaches 12+, the matrix gets pagination or grouping. Specifically:
- 8–11 categories: single-page matrix as designed (Customer activity counted as 1 logical category even when rendered as 2 rows for asymmetric semantics)
- 12+ categories: split into category groups (e.g., "Operations" vs "Finance" vs "System") with collapsible sections

The data shape (`category_id` plus optional `category_group_id`) is forward-compatible — Phase 2 implements the grouping when it lands as a UI-only change.

**Rationale**: Eight categories is comfortable; 12+ starts to feel like work. Building grouping infrastructure now is over-engineering. Forward-compatible data shape makes the migration a UI-only change.

## UX patterns established (for inheritance / reuse)

| Pattern | This spec | Inherits from / extends |
| :--- | :--- | :--- |
| Notification category × channel matrix UI (8 × 3) | **NEW** | Mockups A and C from Tier 2 #4; three-tier resolution from Settings IA framework |
| **User-context-asymmetric forced-minimum semantics** | **NEW** | Tier 2 #4 forced-minimum baseline (which had only uniform-across-users semantics) |
| Per-row revert + per-cell revert affordance pair | **NEW** | Mockup A's revert-to-default (extended for matrix context) |
| Page-level "mute all" controls with non-critical qualifier | **NEW** | — |
| Mobile matrix vertical-stack adaptation | **NEW** | — |
| In-app banner channel as third notification surface | **NEW** | Arch doc §13.11 SSE infrastructure |
| Notification center bell with 24-hour visibility window | **NEW** | — |
| Two-page settings split (personal preferences vs tenant defaults) | **NEW** | Settings IA framework Decision 1 (web tree) |
| Three-tier scope annotation pattern (`default`/`tenant`/`your`/`locked`) | Reused | Three-tier resolution chain from Settings IA framework |
| Forced-minimum on safety-critical categories | Reused | Tier 1.5 (Customer activity for tech in conversation) |
| Optimistic UI with pending badges | Reused | Arch doc §16.8 |
| Save-on-blur for simple toggles | Reused | Settings IA framework Decision 5 |

Eight new patterns, four reused. The user-context-asymmetric forced-minimum is the most architecturally significant new pattern — it's likely to apply to future categories where the same notification has different operational urgency depending on who's receiving (Phase 2 candidates: tech-flagged safety incidents, customer-initiated rescheduling).

## Cross-domain considerations

### A. Tier 1.5 integration confirmed

The Customer activity category covers inbound SMS replies per Tier 1.5. The forced-minimum push for the originating tech (asymmetric semantics) is the central interaction between Tier 1.5 and Tier 2 #5. A58's delivery dispatcher implements the per-recipient forced-minimum check.

### B. Settings IA framework integration

The notification preferences sub-surface lives at `Settings > Notifications > Preferences` (per Settings IA framework Decision 1 web tree). The tenant defaults sub-surface lives at `Settings > Notifications > Tenant defaults`. Both surfaces use the page-level layout pattern from Settings IA framework Decision 5 (header / content / save behavior).

The settings catalog (A52 from Tier 2 #4) extends to include notification preference settings — each category × channel combination is a settings catalog entry searchable via the settings search affordance.

### C. Notification category metadata for Tier 4 #14 help links

Each category has a brief description that surfaces as helper text on the matrix UI ("Job activity covers tech assignments, status changes, and ETC variance alerts"). Tier 4 #14's help system can deep-link from a help article like "Why am I getting so many quote approval emails?" directly into the matrix UI via anchor link `#quote-approvals`. The data shape supports this; Tier 4 #14 surfaces the help links.

### D. New tenants and new users — bootstrapped preferences

When a tenant signs up, default tenant policy is initialized from Pilot's system defaults (Decision 3). When a user is added to a tenant, no user overrides exist yet — they inherit tenant policy. Both are zero-config; A57's write endpoints handle the upsert pattern naturally.

### E. Audit log for preference changes

Per Settings IA framework Cross-Domain G, every preference change writes to `audit_log` with `setting_key` of the form `notification_preference.{category}.{channel}.{scope}` (where scope is `tenant` or `user`), and the old/new values. Existing audit infrastructure covers this; no new tables.

### F. Rate limiting vs. preferences — they compose

A35 already rate-limits notifications at the system level (no more than X per category per hour). Preferences are a separate filter — A35 prevents spam, preferences prevent unwanted-by-this-user. They compose: a notification must clear both A35 (rate limit) and the user's preferences (subscription) to be delivered. A58's dispatcher gate runs both checks.

### G. The category registry is the gating dependency

A56 below creates the category registry. Every existing backend firing site needs to declare its category. Audit pass needed during A56 implementation: estimated 8 firing sites across the codebase as of v5.2 (notification_outbox.create() call sites in dispatch board, calendar sync, QB sync, mobile sync, customer comms, Flow 2 ETC variance, Flow 5 quote approval, Tier 1.5 customer SMS).

### H. The delivery dispatcher must respect preferences AND forced-minimum semantics

Today's `poll_pending_notifications` Celery task sends every notification on every wired channel. A58 below updates this dispatcher to:
1. Look up the recipient's effective preference for `(category_id, channel)`
2. Skip the channel if `enabled = FALSE`
3. Override skip if forced-minimum applies for this user-context (e.g., recipient is the tech in a conversation, channel is push, category is Customer activity, sub-trigger is inbound_sms_reply)
4. Skip the entire entry if no channels remain enabled

The forced-minimum check requires the dispatcher to know the sub-trigger context for each notification — A56's category schema needs sub-trigger metadata.

### I. Settings UIs for notification preferences differ from Tier 2 #4 settings

Tier 2 #4 settings are mostly per-tenant configuration (margin policy, calendar auto-expiry, etc.). Tier 2 #5 has both tenant-level (defaults) and user-level (overrides) editing on dedicated surfaces. The Settings IA framework's three-tier resolution chain (Mockup C) is the right pattern, but the matrix UI presents it as a 24-cell grid rather than a list of independent settings rows.

This is consistent with the IA framework — matrix is just a denser rendering of the same underlying setting model. Each cell is an independently-resolvable setting key (`notification_preference.quote_approvals.push`).

### J. Push deep-link target hardening

Push notifications from notification_outbox include a deep-link target so tapping the push opens the relevant entity. Each notification category needs a defined deep-link mapping:

| Category | Deep-link target |
| :--- | :--- |
| Quote approvals | `/quotes/approvals/{quote_id}` (web) or quote detail screen (mobile) |
| Field issues | `/dashboard/approvals/field-issues/{escalation_id}` (web) |
| Sync conflicts | `/settings/integrations/{integration}/conflicts/{id}` (web) |
| Job activity | `/jobs/{job_id}` (web or mobile) |
| Customer activity | `/customers/{customer_id}/comm-history#thread-{thread_id}` (web) or thread screen (mobile) |
| Billing | `/settings/subscription/invoices` (web) |
| Background sync alerts | mobile sync queue surface |
| System announcements | `/settings/announcements/{id}` (web; new sub-surface — see Decision below) |

Implementation: each `notification_outbox` entry stores its deep-link target alongside the body. A58 hands the deep-link to the push payload. Frontend handles the deep-link routing on tap.

A note on system announcements: a new minor sub-surface `Settings > Announcements` is needed to host the historical announcement archive. Out of MVP scope for full design but the route is reserved.

### K. In-app banner accessibility

The in-app banner needs to be screen-reader announced when it appears. ARIA `role="alert"` on the banner container ensures screen readers announce the notification text. Critical announcements (12-second dismiss) get `aria-live="assertive"`; standard announcements get `aria-live="polite"`. A57's banner component spec includes accessibility requirements.

## Deferred items (Phase 2 / for future iteration)

See Decision 9 for the full list. Beyond those:

- **Sub-trigger granularity in the matrix** — letting users separately mute "ETC variance" within Job activity. Phase 2 if observed user demand.
- **Custom notification rules** — "notify me on Field issues only when the captured operation is a time entry." Phase 2; complex rule engine work.
- **Notification grouping in the bell** — "3 customer messages from Mike" instead of 3 individual entries. Phase 2.
- **Push action buttons** — "Approve / Decline" actions directly in push notifications. Phase 2; APNs/FCM action support is platform-specific and adds work.
- **In-app banner positioning preferences** — top vs bottom. MVP fixed at top; Phase 2 if requested.
- **Notification soundscape** — different sounds per category. Phase 2; OS-level notification customization not part of MVP.

## Validation checklist

Before implementation begins:

- [ ] All 8 categories from Decision 2 audited against existing `notification_outbox` firing sites — every site has a category assignment
- [ ] Default policy table from Decision 3 reviewed against expected tenant operational patterns
- [ ] Forced-minimum categories from Decision 4 confirmed with dev team — four categories, with Customer activity having user-context-asymmetric semantics
- [ ] Customer activity sub-trigger metadata defined for the asymmetric forced-minimum check (`inbound_sms_reply` is the only forced-minimum sub-trigger; others are not)
- [ ] Matrix UI mocked at full viewport width and at mobile width (per Decisions 5 and 6)
- [ ] User-context-asymmetric Customer activity rendering tested for users who only receive one context (tech-only) vs both (owner)
- [ ] Page-level "Mute all push (non-critical)" / "Mute all email" / "Reset to tenant defaults" controls implemented
- [ ] Per-row and per-cell revert affordances implemented
- [ ] Owner-only "Tenant defaults" sub-surface implemented per Decision 7
- [ ] In-app banner component scoped per Decision 8 — shared between web and mobile, slide-down with 6/12-second auto-dismiss, ARIA accessibility, click-to-navigate
- [ ] Notification center bell with 24-hour window and 50-item history implemented
- [ ] A56 notification category registry endpoints specified
- [ ] A57 preference matrix endpoints + in-app banner component specified
- [ ] A58 delivery dispatcher gate specified with forced-minimum check
- [ ] Audit log entries for preference changes verified per Cross-Domain E
- [ ] Bootstrapping behavior for new tenants and new users verified per Cross-Domain D
- [ ] Forced-minimum override resistance tested in UI with proper inline explainer
- [ ] Push deep-link mapping per Cross-Domain J implemented for all 8 categories

## Backend additions (new for Tier 2 #5)

### A56. Notification Category Registry

**Triggered by**: Decision 2's eight-category classification, Decision 4's forced-minimum semantics, and Cross-Domain G's audit-pass requirement.

**Scope**:
- New table: `notification_category`
  - `category_id` TEXT PRIMARY KEY (e.g., `quote_approvals`, `field_issues`, `sync_conflicts`, `job_activity`, `customer_activity`, `billing`, `background_sync_alerts`, `system_announcements`)
  - `display_label` TEXT NOT NULL — user-facing label shown in the matrix UI
  - `description` TEXT NOT NULL — helper text shown below the category row
  - `category_group_id` TEXT NULL — Phase 2 forward-compatibility for grouping
  - `display_order` INTEGER NOT NULL — display order in the matrix UI
- New table: `notification_category_sub_trigger`
  - `sub_trigger_id` TEXT PRIMARY KEY (e.g., `customer_activity.inbound_sms_reply`, `job_activity.assignment`, `system_announcements.critical`)
  - `category_id` TEXT FK
  - `display_label` TEXT (for help/admin surfaces; not shown in matrix UI)
  - `forced_minimum_push_uniform` BOOLEAN NOT NULL DEFAULT FALSE — applies to all users
  - `forced_minimum_push_recipient_only` BOOLEAN NOT NULL DEFAULT FALSE — applies only to the originating recipient (e.g., tech in conversation)
- Schema extension to `notification_outbox`:
  - Add `category_id` TEXT NOT NULL FK
  - Add `sub_trigger_id` TEXT NULL FK
  - Add `recipient_user_id_originating` UUID NULL — the user the notification "belongs to" for forced-minimum-recipient-only semantics (e.g., the tech in the conversation thread)
- Audit pass: every `notification_outbox.create()` call site reviewed and assigned a category + sub_trigger. Estimated 8 firing sites in the v5.2 codebase.
- New table: `notification_default_policy`
  - `tenant_id` UUID NULL (NULL = Pilot system default)
  - `category_id` TEXT FK
  - `channel` TEXT (`push` | `email` | `in_app`)
  - `enabled` BOOLEAN NOT NULL
  - Unique constraint on (`tenant_id`, `category_id`, `channel`)
  - System defaults seeded per Decision 3 with tenant_id NULL
- API: `GET /api/v1/notifications/categories` — returns the registry with current effective tenant defaults
- API: `GET /api/v1/notifications/sub-triggers` — returns sub-triggers (mostly used by admin / debugging)

**Effort estimate**: Medium — 4 days. The category registry itself is a small schema; the audit pass over existing firing sites is the cost driver. Each firing site needs a code change to declare its category and (where applicable) sub-trigger.

### A57. Notification Preference Matrix Endpoints + In-App Banner Component

**Triggered by**: Decisions 5, 6, 7, 8 — the matrix UI's read and write paths plus the in-app banner channel infrastructure.

**Scope**:

**Preference matrix endpoints**:
- New table: `notification_preference`
  - `tenant_id` UUID NOT NULL
  - `user_id` UUID NULL (NULL = tenant-level override of system default; non-NULL = user-level override)
  - `category_id` TEXT FK
  - `channel` TEXT (`push` | `email` | `in_app`)
  - `enabled` BOOLEAN NOT NULL
  - `created_at`, `updated_at` TIMESTAMPTZ
  - Unique constraint on (`tenant_id`, `user_id`, `category_id`, `channel`) with NULL handling
- API: `GET /api/v1/notifications/preferences?user_id=...` — returns the user's full effective matrix (8 × 3 = 24 cells), each with `effective_value`, `scope` (`system | tenant | user | locked`), and the inheritance chain
- API: `PUT /api/v1/notifications/preferences/{category}/{channel}` — write a user-level preference
  - Request: `{enabled: bool}`
  - Response 200 with new effective value
  - Response 403 if attempting to disable a forced-minimum push (Decision 4) — for user-context-asymmetric categories, the 403 only applies when the user's context triggers the forced-minimum
- API: `DELETE /api/v1/notifications/preferences/{category}/{channel}` — clear user override (revert to tenant or system default)
- API: `PUT /api/v1/notifications/tenant-policy/{category}/{channel}` — owner sets tenant-level default (RBAC: owner only)
- API: `DELETE /api/v1/notifications/tenant-policy/{category}/{channel}` — clear tenant override (revert to system default)
- API: `POST /api/v1/notifications/preferences/mute-all-push-non-critical` — bulk-mute all non-forced-minimum push for the requesting user
- API: `POST /api/v1/notifications/preferences/mute-all-email` — bulk-mute all email for the requesting user
- API: `POST /api/v1/notifications/preferences/reset-to-tenant-defaults` — clear all user overrides for the requesting user
- Audit log entry on every write per Cross-Domain E

**In-app banner component**:
- Server-Sent Events channel `/sse/notifications` per arch doc §13.11 streams in-app notifications to the active session
- New endpoint: `POST /api/v1/notifications/in-app/mark-read` — mark notification(s) as read
- New endpoint: `GET /api/v1/notifications/in-app/recent?limit=50` — returns last 50 in-app notifications for the bell panel
- Shared web/mobile component: `<NotificationBanner />` slides down from top with auto-dismiss (6s standard / 12s critical), click-to-navigate, ARIA `role="alert"` accessibility
- Notification center bell component: badge count of unread; panel with last 50; mark-as-read on click
- New table: `in_app_notification`
  - `notification_id` UUID PK
  - `tenant_id` UUID
  - `user_id` UUID
  - `category_id` TEXT FK
  - `body` TEXT
  - `deep_link_target` TEXT (per Cross-Domain J)
  - `priority` TEXT (`standard | critical`)
  - `created_at`, `read_at` TIMESTAMPTZ NULL

**Effort estimate**: Medium — 5–6 days. The endpoints are simple CRUD; the in-app banner component (shared between web and mobile, with SSE integration, accessibility, and bell archive) is the cost driver.

### A58. Delivery Dispatcher Preference Gate

**Triggered by**: Cross-Domain H — the existing dispatcher must respect preferences and forced-minimum semantics.

**Scope**:
- Update `tasks/notification_worker.py::poll_pending_notifications` to consult `notification_preference` and forced-minimum rules before dispatching
- For each pending `notification_outbox` entry, for each potential recipient, for each channel:
  1. Look up the recipient's effective preference for `(category_id, channel)` via the three-tier resolution chain
  2. If `enabled = FALSE`, check forced-minimum rules:
     - If the channel is push AND the category-sub-trigger is forced-minimum-uniform → override and dispatch
     - If the channel is push AND the category-sub-trigger is forced-minimum-recipient-only AND `recipient_user_id_originating == this_recipient_user_id` → override and dispatch
     - Otherwise → skip the channel
  3. If all channels are skipped for a recipient, log the suppression and skip the recipient
- Emit a structured log entry when a notification is filtered by preferences (for support / debugging)
- Forced-minimum push (Decision 4) bypasses the gate for push only — email and in-app still respect preferences
- Per-recipient evaluation is critical: a single notification may have multiple recipients (e.g., owner + tech), each with different forced-minimum context
- Performance: cache effective preferences per (user, category, channel) for the duration of a single dispatcher poll cycle

**Effort estimate**: Medium — 3–4 days. The logic is small but the per-recipient evaluation across multiple users adds complexity. Testing surface is large — every existing firing site needs end-to-end verification that preference filtering doesn't accidentally suppress something it shouldn't, and that forced-minimum overrides work for both uniform and asymmetric cases.

### Total Tier 2 #5 backend additions

A56 (4 days) + A57 (5–6 days) + A58 (3–4 days) = **12–14 days**.

Cumulative through Tier 2 #5: A1–A66 from prior versions, plus A56–A58 reserved and now filled. Note: A56–A58 sit numerically *before* A59–A66 (Tier 1.5) because they were reserved in the ledger numbering scheme during the Tier 1.5 work — see backend ledger v5.2 update instructions for the reservation explanation.

---

## What this surface does NOT cover

- Voice persona tone setting UI — Tier 2 #6
- Account settings UI (profile, password, MFA) — Tier 2 #7
- Notification channel infrastructure (SendGrid sender domain config, etc.) — admin-only at `Settings > Integrations > Notification channels`; existing infrastructure
- SMS as inbound user channel — explicit MVP scope cut per Tier 1.5; SMS is outbound-to-customer only
- Quiet hours, digests, snoozing — Phase 2 (Decision 9)
- Push notification action buttons (Approve / Decline directly in push) — Phase 2
- Notification grouping in the bell — Phase 2
- Custom notification rules / sub-trigger granularity in the matrix — Phase 2

## Cumulative effects on Pass 4 totals

**Backend additions ledger**: A56–A58 added (3 additions). These were reserved during Tier 1.5 numbering and now filled. Cumulative through Tier 2 #5: A1–A66 with A56–A58 now filled.

**Backend day estimate update**:
- Pre-Tier-2-#5 cumulative remaining MVP (after Tier 1.5): 171–229.5 days
- Tier 2 #5 additions: 12–14 days
- New cumulative remaining MVP: **183–243.5 days**

**Framework doc**: Tier 2 #5 status flips from `pending (next)` to `locked` in the Pass 4 progress detail. Tier 2 #6 (voice persona tone) becomes the next surface.

**No new arch doc patterns**: Tier 2 #5 reuses existing platform vocabulary. The user-context-asymmetric forced-minimum semantics is a new pattern but it lives in Tier 2 #5's spec rather than getting its own §16 entry — it's specific to notification preferences rather than a platform-wide pattern. If a Phase 2 surface needs the same asymmetric semantics, the §16 entry can be created at that time.

**No new PRD additions for Tier 2 #5 specifically** beyond the implicit notification preference scope already captured in §3.7. The PRD's Cross-cutting platform UX vocabulary section may want a brief addition for the asymmetric-forced-minimum pattern, but it's not gating implementation.

## Next: Tier 2 #6 — Voice Persona Tone Setting UI

Tier 2 #6 is small. The voice persona tone setting (`voice_persona_tone`) already exists in the schema (A13, post-MVP marked but the field is in the database); Tier 2 #6 surfaces it to the UI as a tenant-level setting. Estimated 100–150 lines per the framework's Shape C deliverable definition. Inherits Mockup A wholesale. Single setting, single page.

After Tier 2 #6, Tier 2 closes with #7 (account settings — profile, password, MFA enrollment, integrations management).
