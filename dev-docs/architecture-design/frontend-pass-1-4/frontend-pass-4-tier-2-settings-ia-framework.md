# Pilot for Trades Design System — Pass 4, Tier 2 Prerequisite: Settings IA Framework

**Version**: 1.0
**Status**: Locked
**Date**: April 27, 2026
**Author**: Tom (Founder) with Claude
**Scope**: Information architecture, visual treatment, layout pattern, and parity rules for all settings surfaces across web and mobile. Prerequisite for Tier 2 #4–#7. Establishes the system-default-with-tenant-override visual pattern as the second of two new platform patterns Pass 4 introduces (alongside mobile-to-web escalation from Tier 1 #1).
**Depends On**: All Pass 1–3 specs; Pass 4 Tier 1 #1, #2, #3 (which surfaced new settings) · `mvp-arch.md` §16.5 (System Default + Tenant Override Two-Tier Configuration)
**Backend additions**: None directly (settings backend lands in #4–#7); this spec only locks data shape conventions and IA

---

## Purpose

Pass 3 surfaced a lot of tenant configuration without designing the surfaces that expose it. Pass 4 Tier 1 added more. Tier 2 #4–#7 is where these settings get visible UI, but those four surfaces would each be reinventing IA, layout, and visual treatment for system-default-vs-tenant-override if there weren't a unifying framework. This doc is that framework. It locks:

1. The full settings IA tree across web and mobile, with every Pass 1–4 Tier 1 setting placed into a known home (no dangling settings; nothing surfacing for the first time in #4–#7 without a home decision)
2. The visual treatment for the system-default-with-tenant-override pattern from arch doc §16.5 — the pattern's first dedicated UI treatment
3. Page-level layout, save behavior, and revert-to-default affordance
4. Web vs mobile parity rules
5. Permission gates
6. Search / discoverability for a growing settings tree

Tier 2 #4 (configurable thresholds), #5 (notification preferences), #6 (voice persona tone), and #7 (account settings) inherit this framework wholesale. Each #4–#7 spec is a Shape C deliverable per the framework doc — short and focused on the specific settings within the locked IA.

## Strategic direction

### The settings tree is two-thirds tenant-shared, one-third user-personal

The IA must distinguish settings that affect everyone in the tenant (margin buckets, calendar auto-expiry, voice persona tone) from settings that are personal to the logged-in user (notification preferences, profile, password, MFA enrollment). These are two fundamentally different scopes, and the visual treatment + permission model differ accordingly. Tenant-shared settings are owner-editable only (with one exception: per-user overrides where explicitly allowed); user-personal settings are user-editable always.

### The system-default-with-tenant-override pattern needs a dedicated visual treatment

Arch doc §16.5 defines the pattern at the schema level — system_default key, tenant_setting nullable column, effective-value resolution helper. What §16.5 does not define is the UI treatment: how the user sees that a setting is currently inheriting from a system default vs being actively overridden, and how revert-to-default works as an affordance.

This spec defines that treatment. It's the second new platform pattern Pass 4 introduces (per the framework doc).

### Page-level layout pattern is shared across all settings sub-surfaces

Every settings sub-surface in #4–#7 uses the same page-level shell — same header treatment, same content area conventions, same save behavior. This is more important than it sounds: if every settings sub-surface invents its own save UX, the user has to relearn what "saved" means each time. Single shared shell, single mental model.

### Mobile gets a curated subset, not a full mirror

Web is the canonical settings surface. Mobile gets only the settings that are operationally relevant in the field: per-user notification preferences, the per-user override toggles (where allowed), profile basics, voice command settings. Tenant-level configuration, integrations management, and admin work stays web-only. This mirrors the broader mobile/web persona split locked in Pass 2.

### Settings discoverability scales with growth, not just MVP size

At MVP close, the settings tree has roughly 25–30 settings across 8–10 sub-surfaces. Phase 2 will at least double both numbers. The IA and search affordance need to handle 60+ settings without becoming unnavigable. Settings search (Decision 7 below) is built into the framework now to make this scale-resistant.

## Locked design decisions

### 1. Settings IA tree — web

The web settings surface (already established in Pass 2 §3.13 as a top-level nav section) gets a flat-then-tabbed structure under `/settings`. Top-level groups become sidebar items; each group has 1–N sub-pages.

```
/settings
├── Company                              (single page; basic tenant identity, branding)
├── Users & Roles                        (single page; user list + RBAC)
├── Subscription & Billing               (single page; plan, payment method, usage)
├── Catalog & Pricing                    (already established sub-tree)
│   ├── Items
│   ├── Markups
│   ├── Suppliers
│   └── Pricing rules
├── Operations                           (NEW IN PASS 4 — see Decision 2)
│   ├── Margin buckets                   (#4)
│   ├── Profitability rules              (#4)
│   └── Field operations                 (#4)
├── Sync & Storage                       (NEW IN PASS 4 — see Decision 2)
│   ├── Background sync                  (#4 — from Tier 1 #3)
│   ├── Offline limits                   (#4 — from Flow 7)
│   ├── Photos                           (#4 — from Flow 7)
│   └── Voice capture                    (#4 — from Flow 7)
├── Integrations                         (already exists from Flow 6)
│   ├── QuickBooks                       (existing 4-tab + auto-expiry per Tier 1 #2)
│   ├── Calendar                         (existing — Flow 6)
│   └── Notifications channels           (#5 — channel-level setup; preferences below)
├── Notifications                        (NEW IN PASS 4 — see #5)
│   └── Preferences                      (#5 — per-category × per-channel matrix)
├── Voice AI                             (already exists from Pass 2 §3.13)
│   ├── Transcripts                      (existing)
│   ├── Feedback                         (existing)
│   ├── Configuration                    (existing — wake word, etc.)
│   └── Persona tone                     (#6 — surfaces existing schema field)
├── Audit Log                            (already exists)
├── Field Mode                           (already exists from Pass 2 §7)
└── My Account                           (NEW IN PASS 4 — see Decision 3)
    ├── Profile
    ├── Password
    ├── MFA enrollment
    ├── My notification overrides        (#5 — user-level overrides)
    ├── Active sessions
    └── Data export
```

Three new top-level groups added by Pass 4: **Operations**, **Sync & Storage**, **Notifications**, plus **My Account** (which is conceptually distinct from tenant settings — see Decision 3). Existing groups extended with new sub-pages where #4–#7 add functionality.

**Rationale for grouping**:

- *Operations* groups settings that affect how jobs run day-to-day: margin policy, ETC variance thresholds, profitability chart rendering. These all live together because they're owner-decisions about operational policy.
- *Sync & Storage* consolidates the device-and-data-flow concerns: background sync, offline limits, photo retention, voice capture. Tier 1 #3 committed this grouping name; this framework confirms it.
- *Notifications* is split into channel-level setup (in *Integrations*, where SMS provider config and email-from-address live) and per-user-per-category preferences (in *Notifications > Preferences*). The split is intentional — channel infrastructure is admin-only; preferences are personal.
- *My Account* is the user-personal scope; everything else is tenant-shared.

### 2. Settings IA tree — mobile

Mobile settings live under the existing `Profile` / `Settings` entry point on the Today tab. Mobile shows only operationally-relevant subsets per the three-question inclusion rule from Decision 6:

```
Mobile > Settings
├── My Account                           (parity with web My Account)
│   ├── Profile (read + photo update only)
│   ├── Password change
│   ├── MFA management
│   ├── My notification preferences      (#5 — user-level)
│   └── Sign out
├── Sync & Storage                       (operationally relevant for techs)
│   ├── Background sync
│   │   ├── On/off (editable — own user override)
│   │   ├── WiFi only (read-only — tenant value)
│   │   └── Battery floor (read-only — tenant value)
│   ├── Offline limits (read-only — tenant value: "Hard limit: 72 hours")
│   └── Photos (read-only — tenant value: "Upload on WiFi only: yes")
├── Operations                           (read-only tenant policies that affect mobile UX)
│   ├── ETC variance notes (read-only — "Notes required when ETC increase exceeds 10%")
│   └── Quote approval (read-only — "Tech-created quotes require owner approval before sending")
├── Voice
│   ├── Persona tone (read-only — "AI is set to: balanced")
│   ├── Wake word sensitivity (per-user setting, editable)
│   └── Output volume (per-user setting, editable)
└── About                                (version, support, legal links — Tier 4 #14 territory)
```

**Mobile-NOT-included** (web-only per Decision 6's inclusion rule):
- Company, Users & Roles, Subscription, Catalog, Operations *editing* (margin/profitability rules — see exception below for read-only awareness items), Integrations management, Voice AI Transcripts/Feedback/Configuration, Audit Log, Field Mode toggle (web-side per Pass 2 §7).
- Tenant-level overrides for any setting (techs see their own user-level overrides only)

**The Operations mobile group** is read-only-only — the underlying tenant settings (`etc_variance_note_required_pct`, `require_approval_for_tech_quotes`) are edited on web but their *effective value* is surfaced on mobile because techs experience their consequences in the field. Decision 6's inclusion rule explains the criteria.

**Provenance annotation on mobile read-only values**: each read-only mobile setting renders the effective value plus a small annotation indicating where the value came from:
- *"Set by your tenant"* when a tenant override exists (per arch doc §16.5 resolution)
- *"Default value"* when inheriting from system default

This is the same State 1 vs State 2 distinction from Decision 4 below, rendered without the edit affordance. The annotation helps the tech understand the value comes from somewhere editable rather than being baked into the app, which matters when the tech wants to know whether to ask their owner to change it.

**Rationale**: Mobile settings are intentionally minimal. The tech needs to manage their own account, see/set their own preferences, and view (not edit) tenant policies that affect their work. Owner-on-mobile gets the same view because the mobile app is technician-primary by Pass 2's design — owners do tenant-level admin on web. The three-question inclusion rule (Decision 6) is the contract for whether any new setting belongs on mobile.

### 3. My Account is a distinct sibling group, not a sub-page of Users & Roles

**Decision**: `My Account` is a top-level settings group (not a sub-page of `Users & Roles`).

**Rationale**: `Users & Roles` is the admin surface for managing other users (an owner editing tech accounts, assigning roles, etc.). `My Account` is the personal-self-service surface where the logged-in user manages their own credentials, preferences, MFA, and exports their data. These are different mental models. Co-locating them creates the awkward case where a technician sees `Users & Roles` and thinks they can manage other users, then discovers they can only edit themselves.

The two surfaces share zero visual treatment beyond the framework-level page shell:
- `Users & Roles` is a list-detail surface (admin viewing all users, drilling into one)
- `My Account` is a tabbed personal-settings surface (the current user only)

This split exists in most B2B SaaS apps for the same reason; making it explicit here avoids future regret.

### 4. Visual treatment for system-default-with-tenant-override

**Decision**: The system-default-with-tenant-override pattern from arch doc §16.5 gets the following visual treatment in the settings UI:

**State 1 — Setting is inheriting from system default** (tenant has not overridden):

- Setting label rendered normally
- Value field shows the inherited value with a subtle annotation: *"Default · 30 days"* in muted neutral text
- Subtle "from system" icon (a small descend-arrow or default-marker glyph) to the left of the annotation
- Edit affordance: clicking the value field opens an editor (input, select, etc.) which transitions the setting to State 2 on save

**State 2 — Setting is actively overridden by tenant**:

- Setting label rendered normally
- Value field shows the tenant value with no muted annotation (it's a regular configured value)
- A "**Revert to default**" link sits to the right of the value field, in brand-indigo
- A small "tenant override" pill in the top-right of the field area (subtle but present) for ambient awareness when scanning a settings page

**State 3 — Pre-warning for time-bounded auto-actions** (e.g., calendar conflict auto-expiry):

- Same as State 1 or State 2 (whichever applies for the value)
- Plus a small inline "Effective: 30 days · Pre-warning at: 7 days" helper text below the field
- Indicates downstream effect ranges so the owner sees consequence without drilling into another setting

**Revert-to-default behavior**:

- Clicking "Revert to default" shows a small confirm-as-turn micro-confirmation: *"Revert this to the system default of 30 days? You can re-override it later."*
- On confirm, the tenant override is cleared (tenant_setting nullable column → NULL), the setting transitions to State 1, and a brief success toast: *"Reverted to default."*
- No undo. If the owner reconsiders, they re-override.

**Optimistic UI**: settings changes apply optimistically per the broader Pilot pattern (arch doc §16.8). When the owner edits a value and saves (whether by clicking Save or by save-on-blur), the UI immediately reflects the new value with a small pending indicator; the indicator clears on server confirmation. If the save fails, the field reverts with an error tooltip.

**Rationale**: Distinguishing inherited from overridden values is the central UX problem of system-default-with-tenant-override. State 1's muted annotation makes it ambient — owners scan and see "ah, this is just the default" without parsing. State 2's revert-to-default link is the affordance owners need to undo a decision without manually re-typing the system default. State 3's pre-warning helper text shows downstream effect without a drill-down.

### 5. Page-level layout pattern

**Decision**: Every settings sub-surface in #4–#7 uses this page shell:

**Header zone**:
- Page title (e.g., "Background sync")
- Breadcrumb to parent (e.g., `Settings > Sync & Storage > Background sync`)
- Subtitle/description: 1–2 sentence explainer of what this surface controls
- (No action buttons in header for most surfaces — saves are inline; see below)

**Content zone**:
- Settings rendered as a vertical list of fields, each with label + value + helper text (where useful)
- Settings grouped into named sections when there are >5 settings on a page (e.g., "Conflict resolution" + "Auto-expiry" sections within Calendar settings)
- Section headings are visually subordinate to the page title
- Within a section, fields use consistent right-alignment for value + revert-to-default affordances

**Save behavior** (three categories based on validity-coupling, not field count):

- **Save-on-blur (single field)** — toggles, selects, and single-value inputs with no dependencies on other fields. Edit commits when the field loses focus or the value changes. Optimistic UI per Decision 4. No save button. *Most settings are this category.*

- **Save-on-group-complete (logical group)** — for logically paired fields where validity requires the whole group. Save fires for the whole group atomically when the group reaches a complete-and-valid state, not when individual fields blur.
  - Canonical example: per-entity QB auto-expiry config from Tier 1 #2 Decision 9 — `qb_auto_expire_invoice_enabled` (toggle) paired with `qb_auto_expire_invoice_direction` (`accept_local | accept_remote`). The toggle alone is meaningless; direction alone is meaningless; both must be set together.
  - Behavior:
    - Toggle from OFF to ON → form enters "incomplete group" state; direction field becomes required and visually surfaces as required; no save fires
    - Direction picked → group is complete; save fires for the whole group atomically
    - Toggle from ON to OFF → group completes (direction becomes irrelevant); save fires; direction value is stored but unused
    - User abandons mid-group (navigates away or blurs without completing) → form reverts to last-saved state; no partial save
  - The "incomplete group" state is visually distinct (subtle border tint or required-indicator on the unfilled field) so the user understands they need to finish the group.

- **Explicit Save button (truly complex)** — multi-line text, settings with cross-field validation that needs whole-form context, settings where the user genuinely benefits from a discard option (rare). Save button is right-aligned and shows as primary indigo when the form is dirty, neutral when clean. Almost no MVP settings are this category.

**Footer zone**:
- For surfaces with explicit Save: pending-changes indicator pinned to the bottom of the viewport when the form is dirty, with Save and Discard actions
- For save-on-blur and save-on-group-complete surfaces: no footer

**Loading and error states**:
- Loading: skeleton rows for each setting field
- Error fetching settings: full-page error state with retry CTA (handled by Tier 3 #8 states catalog)
- Error saving a setting: per-field error tooltip; field reverts to last-saved value; toast at page level
- Error saving a group (group-complete category): all fields in the group revert to last-saved state with a group-level error toast

**Rationale**: The three-category split addresses validity-coupling specifically. Save-on-blur handles the 80% of settings that are independent toggles and selects — toggle, it saves. Save-on-group-complete handles the meaningful "enable X with parameters Y" patterns where partial saves would create half-baked database state (the QB auto-expiry direction without the enable, or vice versa). Explicit Save is reserved for the genuinely-multi-step rare cases. This avoids both the "every setting needs a Save button forever" UX cost and the "half-baked state in the database" data integrity cost. Optimistic UI everywhere matches the broader Pilot pattern. The pinned bottom save-bar is a familiar pattern from Notion, Linear, and Stripe Dashboard.

### 6. Web vs mobile parity rules

**Decision**: A tenant setting appears on mobile (read-only or editable per-user-override) if **all three** of these criteria are true:

1. **The setting affects what a tech can do or experience while using mobile.** Margin buckets affect the owner's profitability charts on web — they don't affect what the tech sees in the field. Offline limits affect when the tech's mobile capture will start blocking — they directly affect mobile use.

2. **The tech could be surprised by the value if they didn't see it.** A 72-hour offline hard limit is a surprise if it's not visible — the tech captures, captures, captures, and on hour 73 they suddenly can't. Same logic for `photo_upload_wifi_only` (the tech wonders why their photos aren't uploading on cellular). Margin policy doesn't surprise a tech because they don't see margin charts on mobile in the first place.

3. **The tech doesn't have direct edit access via per-user override.** If they have edit access (`background_sync_enabled` per-user override), the setting is editable on mobile, not read-only. Read-only mobile applies to settings techs can't edit themselves.

**Resolution rules from the three criteria**:

- A setting that fails any of the three is **web-only**
- A setting that meets 1+2 *and* has a per-user override allowed is **editable on mobile** for that user's own override (with the tenant value visible as the inherited starting point)
- A setting that meets 1+2 but has no per-user override is **read-only on mobile**

**Per-setting parity matrix** (every Pass 1–4 Tier 1 tenant setting evaluated against the three criteria):

| Setting | Affects mobile UX? | Could surprise? | User override? | Mobile placement |
| :--- | :---: | :---: | :---: | :--- |
| `margin_bucket_boundaries` | No | No | No | Web-only |
| `margin_target_pct` | No | No | No | Web-only |
| `etc_variance_note_required_pct` | Yes (tech sees the prompt to add a note) | Yes | No | Mobile read-only |
| `etc_variance_owner_notify_pct` | No (owner-facing) | No | No | Web-only |
| `report_chart_threshold` | No | No | No | Web-only |
| `tech_color_palette` | Marginal | No | No | Web-only |
| `require_approval_for_tech_quotes` | Yes (tech sees "Submit for approval" instead of "Send") | Yes | No | Mobile read-only |
| `max_discount_pct_owner` | No (owner-only feature) | No | No | Web-only |
| `background_sync_enabled` | Yes | Yes | Yes (per-user) | Mobile editable (own override) |
| `background_sync_wifi_only` | Yes | Yes | No | Mobile read-only |
| `background_sync_battery_floor_pct` | Yes | Yes | No | Mobile read-only |
| `background_sync_push_interval_minutes` | Marginal (tech doesn't directly experience push frequency) | No | No | Web-only |
| `offline_hard_limit_hours` | Yes (capture blocks at this point) | Yes | No | Mobile read-only |
| `photo_upload_wifi_only` | Yes | Yes | No | Mobile read-only |
| `photo_local_retention_days` | Marginal (tech rarely interacts with locally-cached photos directly) | Marginal | No | Web-only |
| `calendar_conflict_*` (auto-expiry) | No (owner resolves on web) | No | No | Web-only |
| `qb_auto_expire_*` (all variants) | No | No | No | Web-only |
| `voice_persona_tone` | Yes (tech hears the voice persona) | Yes | Yes (per-user) | Mobile editable (own override) |

**Generalized parity matrix by setting category** (governs the broader setting categories):

| Setting category | Web | Mobile | Rule |
| :--- | :---: | :---: | :--- |
| Tenant configuration meeting the three-question test | ✓ edit | ✓ read-only or editable per-user-override | Per the per-setting matrix above |
| Tenant configuration failing any of the three questions | ✓ edit | ✗ | Web-only |
| User profile (name, photo, contact info) | ✓ edit | ✓ edit | Parity |
| Password / MFA | ✓ edit | ✓ edit | Parity |
| Notification preferences (per-user) | ✓ edit own | ✓ edit own | Parity for personal preferences |
| Notification *channel infrastructure* (SMS provider, sender domain) | ✓ edit | ✗ | Admin-only; web only |
| Integrations management (QuickBooks, Calendar OAuth) | ✓ edit | ✓ status row + deep-link | Mobile owner status row pattern (§16.9) for status; resolution stays web |
| Catalog management | ✓ edit | ✗ | Web only |
| Audit Log | ✓ view | ✗ | Web only |
| Field Mode toggle | ✓ edit | n/a | Web-only feature |
| Account export / data download | ✓ edit | ✗ | Web only (large data flows poorly on mobile) |
| About / version / support links | ✓ edit (admin only — support contact) | ✓ view | Mobile shows the read view |

**Per-user override visibility rule**: a per-user override is visible to that user on both web and mobile only if the tenant-level setting *allows* user override. Tenant-level setting is the gatekeeper.

**Maintenance discipline for future settings**: when Tier 2 #4–#7 (or any Phase 2 setting) introduces a new tenant setting, the spec author runs the three-question test to determine mobile placement. The decision (web-only, mobile read-only, or mobile editable per-user-override) is documented in the setting's source spec.

**Rationale**: The three-question test replaces ad-hoc per-setting judgment calls with a consistent rule. Most tenant settings are owner-facing decisions about policy or display preferences — they fail criterion 1 because the tech doesn't experience them on mobile. The ones that pass tend to be settings about field-relevant behavior (offline limits, photo upload constraints, voice persona, ETC variance prompts, quote approval workflow). Surfacing those on mobile (read-only, with provenance annotation per Decision 2) prevents tech surprise and helps the tech understand "this comes from somewhere editable" without opening the door to mobile-side tenant editing. The parity matrix above documents the rule's outcome for every MVP setting; future settings get evaluated the same way.

### 7. Search and discoverability

**Decision**: A search input in the settings shell (web) lets the user type any term and see matching settings across the entire tree.

**Behavior**:
- Search input pinned to top of the settings sidebar (web)
- Type-ahead matches against setting names, descriptions, and synonyms (e.g., "margin" matches "margin buckets," "margin target," "max discount margin cap")
- Results show: setting name + current value + path (e.g., `Operations > Margin buckets`)
- Clicking a result navigates to the parent page and scrolls to the setting

**Mobile**: no search at MVP. Mobile's settings tree is small enough (< 15 leaves) that scrolling/tapping is faster than searching.

**Synonym dictionary**: a small dictionary maps common terms to setting-IDs:
- "margin" → all settings under Operations > Margin
- "approval" → require_approval_for_tech_quotes, max_discount_pct_owner, qb_auto_expire_*
- "conflict" → calendar_conflict_*, qb_auto_expire_*
- "offline" → offline_hard_limit_hours, photo_upload_wifi_only, photo_local_retention_days
- "background" → all background_sync_* settings
- "voice" → voice_persona_tone, voice configuration sub-surface
- "notifications" → all notification preference settings + channel infrastructure

**Rationale**: At MVP close the tree has 25–30 settings; Phase 2 will at least double this. Search is built into the framework now so the owner doesn't have to remember whether photo retention lives under "Sync & Storage" or "Catalog" or "Operations." The synonym dictionary handles the case where the owner thinks "approval setting" but the actual setting is named `require_approval_for_tech_quotes`.

**Backend implication**: settings search runs client-side against the loaded settings catalog (no backend search endpoint needed for the small MVP scale). The catalog is loaded once on settings page entry and cached for the session.

### 8. Permission gates

**Decision**: Settings access is gated by RBAC at the route level and by the field level for fine-grained control.

**Route-level gates** (route guard before page renders):

| Setting group | Roles allowed |
| :--- | :--- |
| Company, Users & Roles, Subscription, Catalog, Operations, Sync & Storage, Integrations, Notifications channel infrastructure, Voice AI (all sub-pages), Audit Log, Field Mode | owner, accountant |
| Notifications > Preferences | all (sees only own preferences) |
| My Account (all sub-pages) | all (sees only own account) |

**Field-level gates** (specific sensitive settings within otherwise-accessible surfaces):

- MFA enrollment within My Account: required in some configurations (Tier 2 #7 will spec)
- Account export: requires re-authentication step at action time (regardless of role)
- Tenant subscription / billing: owner-only (accountant sees but can't edit)

**Permission denial UX**: a setting that's role-gated and the user lacks permission is hidden from the IA tree entirely (not shown grayed-out). Users don't see settings they can't access. The exception is Notifications > Preferences and My Account, which all roles can access — those are visible to everyone with their own scoped views.

**Rationale**: Gray-out-but-show is informative for admin users; it confuses non-admin users by suggesting a feature they don't realize is restricted. Hiding cleanly avoids both a security smell (accidentally exposing the existence of admin features) and the UX confusion. The exception for personal settings is fine because every role has those.

## Settings inventory — every Pass 1–4 Tier 1 setting placed in IA

This consolidates the existing tenant settings ledger plus all Pass 4 Tier 1 additions, mapping each to its IA home. **Every setting Tier 2 #4–#7 will surface has a known location.** Settings are grouped by IA placement.

### Operations > Margin buckets

| Setting | Default | Source | Surface |
| :--- | :--- | :--- | :--- |
| `margin_bucket_boundaries` | `[10, 20, 30]` | A17 | #4 |
| `margin_target_pct` | 20% | A17 | #4 |

### Operations > Profitability rules

| Setting | Default | Source | Surface |
| :--- | :--- | :--- | :--- |
| `etc_variance_note_required_pct` | 10% | A14/A16 | #4 |
| `etc_variance_owner_notify_pct` | 50% | A14/A16 | #4 |
| `report_chart_threshold` | 8 | A15 | #4 |

### Operations > Field operations

| Setting | Default | Source | Surface |
| :--- | :--- | :--- | :--- |
| `tech_color_palette` | 12-hue system default | A18 | #4 |
| `require_approval_for_tech_quotes` | ON multi-user, OFF solo | A2 | #4 |
| `max_discount_pct_owner` | 15% | A3 | #4 |

### Sync & Storage > Background sync

| Setting | Default | Source | Surface |
| :--- | :--- | :--- | :--- |
| `background_sync_enabled` | TRUE (user override allowed) | A51 | #4 |
| `background_sync_wifi_only` | FALSE | A51 | #4 |
| `background_sync_battery_floor_pct` | 20 | A51 | #4 |
| `background_sync_push_interval_minutes` | 5 (system default + tenant override §16.5) | A51 | #4 |

### Sync & Storage > Offline limits

| Setting | Default | Source | Surface |
| :--- | :--- | :--- | :--- |
| `offline_hard_limit_hours` | 72 (nullable for unlimited) | Flow 7 D13 | #4 |

### Sync & Storage > Photos

| Setting | Default | Source | Surface |
| :--- | :--- | :--- | :--- |
| `photo_upload_wifi_only` | TRUE | A41 | #4 |
| `photo_local_retention_days` | 7 | A41 | #4 |

### Sync & Storage > Voice capture

| Setting | Default | Source | Surface |
| :--- | :--- | :--- | :--- |
| (Voice offline storage limits — TBD in #4 if surfacing tenant control) | — | A42 | #4 |

### Integrations > Calendar

| Setting | Default | Source | Surface |
| :--- | :--- | :--- | :--- |
| `calendar_conflict_auto_expire_days` | system default 30 (nullable) | A34 | #4 |
| `calendar_conflict_pre_warning_days` | system default 7 (nullable) | A34 | #4 |

### Integrations > QuickBooks

| Setting | Default | Source | Surface |
| :--- | :--- | :--- | :--- |
| `qb_auto_expire_customer_enabled` | FALSE | A50 | #4 |
| `qb_auto_expire_quote_enabled` | FALSE | A50 | #4 |
| `qb_auto_expire_invoice_enabled` | FALSE | A50 | #4 |
| `qb_auto_expire_expense_enabled` | FALSE | A50 | #4 |
| `qb_auto_expire_*_direction` (paired with each enabled) | varies by entity | A50 | #4 |
| `qb_auto_expire_days` | system default 60 | A50 | #4 |
| `qb_pre_warning_days` | system default 14 | A50 | #4 |
| `qb_sync_preference_customer` | (existing schema field) | §5.3 | #4 |
| `qb_sync_preference_expense` | (existing schema field) | §5.3 | #4 |

### Notifications > Preferences

| Setting | Default | Source | Surface |
| :--- | :--- | :--- | :--- |
| Per-category × per-channel preference matrix (push / email / both / off) | per-category defaults | A35 + #5 | #5 |

### Voice AI > Persona tone

| Setting | Default | Source | Surface |
| :--- | :--- | :--- | :--- |
| `voice_persona_tone` | `balanced` | A13 (Post-MVP — surfaced to UI in #6) | #6 |

### My Account

| Setting | Source | Surface |
| :--- | :--- | :--- |
| Profile (name, photo, contact info, phone) | existing user model | #7 |
| Password change | existing user model | #7 |
| MFA enrollment (Cognito MFA) | existing user model | #7 |
| Active sessions list with revoke | existing token model | #7 |
| Data export request | new endpoint A61-equivalent (flagged) | #7 |
| Per-user notification overrides | A35 + #5 | #5 / cross-references in #7 |

### Total inventory

26 distinct settings (counting QB auto-expiry direction settings as a paired family rather than 4 separate entries) across 9 IA sub-surfaces. Every Tier 2 #4 setting has a home in Operations or Sync & Storage. Notifications, Voice, and Account each have their own dedicated surface. **Nothing dangling.**

### Phase 2 settings flagged but not in MVP

These surface in Phase 2 and have no home reserved yet (will be added when surfaced):
- Per-tech color overrides
- Per-customer integration sync overrides
- Owner-defined automation rules (auto-accept QB invoices over X)
- Voice command custom phrasing
- Custom report scheduling
- Multi-language UI selection

## UX patterns established (for inheritance / reuse)

| Pattern | This spec | Inherits from / extends |
| :--- | :--- | :--- |
| **System-default-with-tenant-override visual treatment** | **NEW** (second of two new patterns Pass 4 introduces) | Arch doc §16.5 (data shape) |
| **Settings page-level layout pattern (header / content / save)** | **NEW** | — |
| **Three-category save behavior (save-on-blur / save-on-group-complete / explicit Save)** | **NEW** | — |
| Permission gating by hide-not-disable | **NEW** | — |
| Optimistic UI with pending badges | Reused | Arch doc §16.8 |
| Mobile-first-curation parity rule | **NEW** | Pass 2 mobile/web persona split |
| Settings search with synonym dictionary | **NEW** | — |

Five new patterns for the Tier 2 settings work. The system-default-with-tenant-override visual treatment is the platform-level pattern that extends arch doc §16.5; the others are framework-internal patterns that propagate across #4–#7.

## Cross-domain considerations

### A. Onboarding (Tier 3 #10) inherits the Settings IA

Tier 3 #10 surfaces tenant-configurable settings users need to know about during onboarding. The IA established here determines what onboarding can pull from — onboarding's "let's set up your margin policy" step navigates the user through Operations > Margin buckets. The settings tree is the source of truth; onboarding is one path through it.

### B. The Settings IA framework also informs first-time-user empty states (Tier 3 #9)

When a tenant has just completed onboarding, every settings sub-surface either has a system default or an onboarding-set value. There is no truly-empty state for settings (settings always have *some* value because of the system-default pattern). The "first-time" framing for settings is "you haven't customized this from the default yet" — which is just State 1 from Decision 4 above.

### C. Help / about / feedback (Tier 4 #14) integrates with Settings

Tier 4 #14's help/feedback surface deep-links into Settings in two directions:
- From Help → Settings: "configure this in Settings > X" links throughout help articles
- From Settings → Help: small "?" icons next to settings open contextual help articles

This is bidirectional cross-linking. The Settings IA established here gives Tier 4 #14 stable URLs to point at.

### D. Permission gating intersects with onboarding

A tenant in onboarding doesn't yet have the full role structure defined. The onboarding user (typically the future owner) gets de facto owner-role until onboarding completes and other users are added. This is a Tier 3 #10 concern but the permission gating in Decision 8 holds — the onboarding owner has access to everything, and as they add other users with non-owner roles, those users see only their permitted settings.

### E. Settings affecting voice intent grammar

Several settings (auto-expiry days, push interval, margin thresholds) affect voice intent grammar — voice readback may quote these values ("auto-expiring in 30 days, pre-warning 7 days before"). When a setting changes, the voice intent registry's response templates re-render against the current effective value. No special handling needed; voice templates already read effective settings at runtime.

### F. Search synonym dictionary lives in code, not settings

The synonym dictionary from Decision 7 lives in the frontend codebase (`packages/ui/src/settings-search/synonyms.ts`) rather than as a tenant- or user-configurable setting. Phase 2 may add a custom synonym layer per tenant (e.g., a tenant uses unusual internal vocabulary for margin), but MVP uses a fixed dictionary maintained by Pilot.

### G. Settings audit log

Every settings change is audited per the existing audit_log infrastructure. The audit row captures: setting name, previous value, new value, changed_by_user_id, changed_at, and whether the change was a tenant override or a revert-to-default. The Audit Log surface (`Settings > Audit Log`) renders these alongside other auditable events. No new infrastructure; existing audit capture covers it.

### H. Setting placement is code-level for MVP; data-driven in Phase 2

Decision 6's three-question test locks setting placements (web vs mobile, editable vs read-only, sub-surface assignment) at the code level for MVP. The per-setting matrix in Decision 6 is the source of truth, expressed in code through:

- The settings IA tree component (which sub-surface contains which setting)
- The mobile settings page components (which fields render at all on mobile)
- The permission checks (read-only vs editable affordance)
- The validation rules per setting

**A placement change is a frontend code change** in both web and mobile apps, followed by a deploy. Setting *values* themselves remain DB-changeable per arch doc §16.5 — only the placement and editability metadata is code-level.

**This is intentional for MVP.** With 26 settings and stable placements, the cost of a dynamic config table outweighs its benefit. Type safety, rendering co-location, and PR-reviewable change history are preserved. Frequency expectation: 1–3 placement changes per quarter once MVP stabilizes; each change is a small PR.

**Phase 2 may introduce a `setting_metadata` table** that stores placement attributes per setting (`setting_key`, `web_path`, `mobile_path`, `mobile_editable`, `requires_owner_role`, etc.), allowing placement changes via DB update or a small admin UI. The data shape from Decision 6 is forward-compatible: the per-setting matrix translates directly into rows in such a table when the time comes.

**Trigger for the migration**: when placement-change frequency exceeds roughly one change every two weeks for several months, the data-driven config table becomes worth building. Until then, code-level placement is the right cost trade-off.

**What stays in code even after the Phase 2 migration**: per-setting validation logic (range checks, custom rules) and the rendering treatments themselves (the components that render a toggle vs. a select vs. a numeric input). These are type-safety-critical and stay co-located with the rendering layer regardless of whether placement is data-driven.

## Deferred items (Phase 2 / for future iteration)

- **Settings versioning/history** (see all past values for a setting; revert to a previous value) — Phase 2
- **Bulk settings export/import** (move tenant config across environments) — Phase 2
- **Data-driven setting placement via `setting_metadata` table** (per Cross-Domain H) — Phase 2 when placement-change frequency justifies the infrastructure
- **Per-tenant custom synonym dictionary** for settings search — Phase 2
- **Settings change request workflow** (an accountant proposes a change for owner approval) — Phase 2
- **Settings analytics** (which settings are most-edited, which never get touched) — Phase 2
- **Settings recommendations** (proactive suggestions when default is suboptimal for tenant pattern) — Phase 2
- **Mobile settings search** — Phase 2 once mobile settings tree grows beyond ~15 leaves
- **Multi-language UI** for settings labels and descriptions — Phase 2

## Validation checklist

Before Tier 2 #4 starts:

- [ ] Settings IA tree (web + mobile) committed to dev team
- [ ] System-default-with-tenant-override visual treatment visually mocked (recommend a representative sample like calendar_conflict_auto_expire_days showing all three states)
- [ ] Page-level layout pattern (header / content / save behavior) committed
- [ ] Save behavior three-category model committed (save-on-blur, save-on-group-complete, explicit Save) with per-field/per-group decision criteria
- [ ] Web vs mobile parity matrix reviewed against existing mobile sitemap
- [ ] Permission gating route guards specified for each settings group
- [ ] Settings search synonym dictionary stubbed (initial entries listed in Decision 7)
- [ ] All 26 MVP settings have IA homes (per inventory above)
- [ ] No "dangling" settings — every setting from the v5 ledger placed in this IA

## What this spec does NOT cover

- The actual UI for any individual setting — that's #4–#7
- Notification channel infrastructure (SMS provider config, sender domain, etc.) — that's part of #5's broader scope
- The MFA enrollment flow specifics — #7
- Account export pipeline backend — flagged for #7's backend addition
- Onboarding-specific surface for first-time settings configuration — Tier 3 #10
- Help/about/feedback links into settings — Tier 4 #14

## Backend addition (none from this framework spec)

This spec doesn't add backend work directly. It establishes:

- The data shape conventions all Tier 2 #4–#7 backend additions follow (settings as system_default + tenant_setting nullable column, per arch doc §16.5)
- The existing audit_log captures settings changes (no new infrastructure needed)
- The settings catalog endpoint that powers settings search runs against the tenant's effective settings (a thin endpoint that #4 will likely add as part of its read endpoints)

The actual backend additions A52–A6N land in #4–#7 specs.

## Next: Tier 2 #4 — Settings UIs for Configurable Thresholds

Tier 2 #4 is the largest Tier 2 surface and the first to consume this framework. Its scope:

- Operations > Margin buckets, Profitability rules, Field operations
- Sync & Storage > Background sync, Offline limits, Photos, Voice capture
- Integrations > Calendar (auto-expiry settings)
- Integrations > QuickBooks (auto-expiry per-entity settings, sync preferences)

Approximately 18 distinct settings. The #4 spec is a Shape C deliverable per the framework doc — short and focused, applying this IA framework's visual treatment and layout pattern to each setting. Estimated 200–250 lines.

After #4, #5 (notification preferences), #6 (voice persona tone), and #7 (account settings) each apply the same framework to their narrower scopes.
