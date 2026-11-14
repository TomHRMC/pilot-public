# Pilot for Trades Design System — Pass 4, Tier 2 #4: Settings UIs for Configurable Thresholds

**Version**: 1.0
**Status**: Locked
**Date**: April 27, 2026
**Author**: Tom (Founder) with Claude
**Scope**: Settings UIs for the configurable thresholds across Operations, Sync & Storage, and Integrations sub-surfaces. Largest Tier 2 surface, ~18 distinct settings across 7 sub-surfaces. Establishes the system-default-with-tenant-override visual treatment and save-on-group-complete pattern for inheritance by Tier 2 #5–#7.
**Depends On**: Pass 4 Tier 2 Settings IA framework · Arch doc §16.5 (System Default + Tenant Override) · Pass 1 design tokens · Pass 4 Tier 1 #1–#3 (which surfaced the new settings)
**Backend additions**: A52 (settings catalog endpoint), A53 (effective settings resolution endpoint), A54 (tenant settings write endpoints), A55 (per-user override write endpoints)
**Deliverable shape**: Shape C (Settings IA + per-setting spec) per Pass 4 framework doc

---

## Purpose

The Settings IA framework locked the IA tree, the system-default-with-tenant-override visual treatment, the page-level layout, the three-category save behavior, and the per-setting mobile parity rule. Tier 2 #4 applies all of that to the actual Operations, Sync & Storage, and Integrations settings sub-surfaces — making 18 specific settings configurable through the UI for the first time.

This spec is structured around **per-setting locked specs** (one short block per setting) plus three **canonical mockup descriptions** that demonstrate the visual treatments on representative settings:

1. The system-default-with-tenant-override treatment, demonstrated on `calendar_conflict_auto_expire_days`
2. The save-on-group-complete treatment, demonstrated on the QB per-entity auto-expiry config
3. The per-user override treatment, demonstrated on `background_sync_enabled`

#5–#7 inherit these mockups directly. Their specs are smaller because the visual work is done here.

## Strategic direction

### Per-setting brevity, not per-setting prose

Each setting gets a 4–6 line locked spec block: name, scope, data type, validation, save category, location in IA, any cross-references. Settings without unusual constraints don't need prose explanation — the framework already locked the patterns. Settings with unusual constraints (e.g., margin bucket boundaries having a monotonicity validation rule) get a brief callout.

### One mockup per pattern, applied wholesale

The framework's State 1 / State 2 visual treatment for system-default-with-tenant-override needs one canonical mockup. Likewise for save-on-group-complete and per-user override. Three mockups total. Every other setting in this spec inherits from one of these three; #5–#7 inherit too. This avoids a 30-screen proliferation where each setting gets its own mockup and minor visual variants creep in.

### Sequencing within the spec mirrors framework inheritance

Sub-surface ordering: Calendar auto-expiry first (canonical §16.5 case → establishes visual treatment for the spec); QuickBooks per-entity auto-expiry second (save-on-group-complete canonical case); Background sync third (per-user override canonical case); then the simpler sub-surfaces inherit the established visuals.

### Mobile read-only renders use the same components, not parallel implementations

Mobile-read-only displays of tenant settings (per IA framework Decision 6) reuse the web settings field components rendered in read-only mode, not separate mobile-specific components. The provenance annotation ("Set by your tenant" / "Default value") is a prop on the same component. This is a frontend implementation note that matters here because it constrains the component design — every settings field component must support a read-only mode.

## Locked design decisions

### 1. Three canonical mockups establish the visual treatments

#### Mockup A — System-default-with-tenant-override (canonical: calendar auto-expiry)

The State 1 (inheriting) and State 2 (overridden) treatment from IA framework Decision 4 rendered on `calendar_conflict_auto_expire_days`:

**State 1 — Inheriting from system default:**

```
┌─────────────────────────────────────────────────────────────────┐
│ Auto-expire calendar conflicts                                  │
│ ─────────────────────────────                                   │
│                                                                 │
│ How long before unresolved sync conflicts auto-resolve to       │
│ Pilot's version.                                                │
│                                                                 │
│   ↘  Default · 30 days                              [ Edit ]   │
│                                                                 │
│ Effective: 30 days · Pre-warning at: 7 days                     │
└─────────────────────────────────────────────────────────────────┘
```

- The descend-arrow glyph (`↘`) plus *"Default"* text marks State 1
- Value rendered in muted neutral text
- `[ Edit ]` affordance is a brand-indigo-tinted text button
- Helper text below the field shows the *effective* value plus the related pre-warning value (so the owner sees consequence without drilling into another setting)

**State 2 — Tenant override:**

```
┌─────────────────────────────────────────────────────────────────┐
│ Auto-expire calendar conflicts             [tenant override]    │
│ ─────────────────────────────                                   │
│                                                                 │
│ How long before unresolved sync conflicts auto-resolve to       │
│ Pilot's version.                                                │
│                                                                 │
│   45 days                              [ Revert to default ]    │
│                                                                 │
│ Effective: 45 days · Pre-warning at: 7 days                     │
└─────────────────────────────────────────────────────────────────┘
```

- `[tenant override]` pill in the top-right of the field area, subtle but present
- Value rendered in normal neutral text (not muted) — it's a real configured value
- `[ Revert to default ]` is a brand-indigo text link to the right of the value
- Edit affordance: clicking the value field opens the editor inline (no separate Edit button needed once overridden)

**State 3 — Mid-edit (during inline editor):**

```
┌─────────────────────────────────────────────────────────────────┐
│ Auto-expire calendar conflicts             [tenant override]    │
│ ─────────────────────────────                                   │
│                                                                 │
│ How long before unresolved sync conflicts auto-resolve to       │
│ Pilot's version.                                                │
│                                                                 │
│   [   45   ] days                       [ Cancel ]  [ Save ]    │
│                                                                 │
│ Range: 1–365 days. System default: 30.                          │
└─────────────────────────────────────────────────────────────────┘
```

- Numeric input replaces the static value
- Save / Cancel actions appear inline only during edit
- Helper text shifts to validation guidance ("Range: 1–365 days. System default: 30.")
- Save commits immediately on blur (per save-on-blur category from IA framework Decision 5); Cancel discards
- Note: the explicit Save button here is for clarity-during-edit only, not the "explicit Save category." It's UX scaffolding inside an inline edit, not a form-level save button

**Revert-to-default micro-confirmation** (when owner clicks `[ Revert to default ]`):

```
┌──────────────────────────────────────────────────────────────────┐
│ Revert to default?                                               │
│                                                                  │
│ This will revert "Auto-expire calendar conflicts" from           │
│ 45 days back to the system default of 30 days.                   │
│ You can re-override it later.                                    │
│                                                                  │
│                       [ Cancel ]  [ Revert to default ]          │
└──────────────────────────────────────────────────────────────────┘
```

Inline modal-feel popover. After confirm, the field transitions to State 1 and a brief success toast surfaces: *"Reverted to default."*

#### Mockup B — Save-on-group-complete (canonical: QB invoice auto-expiry)

The save-on-group-complete pattern from IA framework Decision 5, rendered on the QuickBooks per-entity auto-expiry config:

**Initial state — group inactive:**

```
┌──────────────────────────────────────────────────────────────────┐
│ Invoice conflicts                                                │
│ ─────────────                                                    │
│                                                                  │
│ When a sync conflict on an invoice goes unresolved...            │
│                                                                  │
│   Auto-expire after a delay     [ ◯ off  ]                       │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

- Single toggle; group has only one field visible
- Toggle is in OFF state; no group to complete

**Mid-completion state — toggle ON, direction not picked:**

```
┌──────────────────────────────────────────────────────────────────┐
│ Invoice conflicts                                                │
│ ─────────────                                                    │
│                                                                  │
│ When a sync conflict on an invoice goes unresolved...            │
│                                                                  │
│   Auto-expire after a delay     [ ● on   ]                       │
│                                                                  │
│   Direction (required)                                           │
│   ┌─────────────────────────────────────────────────────┐       │
│   │ ◯ Accept Pilot version                               │       │
│   │ ◯ Accept QuickBooks version (recommended for invoices)│       │
│   └─────────────────────────────────────────────────────┘       │
│                                                                  │
│   ⚠ Pick a direction to complete this setting.                  │
└──────────────────────────────────────────────────────────────────┘
```

- Toggle ON; direction field surfaces with a "(required)" annotation in red
- Subtle border tint on the direction field group (incomplete-group visual state)
- Inline message at the bottom of the group: "Pick a direction to complete this setting."
- No save fires yet — group is incomplete
- Direction recommendation ("recommended for invoices") inherits from Tier 1 #2's master-aware treatment (QB is the master for Invoices per arch doc §5.3)

**Completed state — toggle ON, direction picked:**

```
┌──────────────────────────────────────────────────────────────────┐
│ Invoice conflicts                                                │
│ ─────────────                                                    │
│                                                                  │
│ When a sync conflict on an invoice goes unresolved...            │
│                                                                  │
│   Auto-expire after a delay     [ ● on   ]                       │
│                                                                  │
│   Direction                                                      │
│   ● Accept QuickBooks version (recommended for invoices)         │
│   ◯ Accept Pilot version                                         │
│                                                                  │
│   Effective: auto-expires after 60 days · Pre-warning at: 14     │
└──────────────────────────────────────────────────────────────────┘
```

- Toggle ON, direction picked; group is complete
- Save fired atomically when the user picked a direction (no Save button shown)
- Subtle border tint clears (no incomplete-group state)
- Helper text below shows the effective auto-expiry interval and pre-warning, both inherited from the parent QB settings (`qb_auto_expire_days`, `qb_pre_warning_days` — see settings F4–F5 below)

**Toggle OFF transition:**

When the user toggles OFF after the group was complete, save fires immediately for the whole group; direction value is preserved in the database but unused. If the user toggles ON again later, the previously-stored direction pre-fills (subtle UX nicety; saves a click).

#### Mockup C — Per-user override (canonical: background sync enabled)

The per-user override treatment from IA framework Decision 6, rendered on `background_sync_enabled`:

**Web view (owner editing tenant default):**

```
┌──────────────────────────────────────────────────────────────────┐
│ Background sync                                                  │
│ ─────────────                                                    │
│                                                                  │
│ Sync your team's data while Pilot is closed. Uses minimal        │
│ battery and data.                                                │
│                                                                  │
│   Enabled for the team           [ ● on ]                        │
│                                                                  │
│   Per-user override allowed?     [ ● yes ]                       │
│                                                                  │
│   When per-user override is allowed, each user can disable       │
│   background sync on their own device via mobile settings.       │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

- Two toggles: tenant default + whether per-user override is allowed
- The "per-user override allowed?" toggle is a meta-control — it doesn't change anyone's value, it just allows individual users to override
- Helper text explains the consequence

**Mobile view (tech editing their own override):**

```
┌─────────────────────────────────┐
│ Background sync                 │
│ ───────────                     │
│                                 │
│ Sync your data while Pilot      │
│ is closed.                      │
│                                 │
│   Enabled                       │
│   ● on (your override)          │
│                                 │
│   Tenant default: on            │
│   [ Match tenant default ]      │
│                                 │
└─────────────────────────────────┘
```

- Tech sees their current override value
- Tenant default shown below for context
- "Match tenant default" link reverts the override to inherit the tenant value (not the system default — the tenant value)
- If the tenant has set "Per-user override allowed?" to NO, the toggle is disabled with a "Set by your tenant" annotation; the override editor is hidden

**Three-tier resolution chain on the read side:**

`get_effective_setting_for_user(tenant_id, user_id, key)`:
1. User override exists → return user override
2. Tenant override exists → return tenant override
3. System default exists → return system default
4. Hardcoded fallback → return fallback

This extends arch doc §16.5's two-tier resolution to three tiers when a setting allows per-user override. **Captured as A55 below.**

### 2. Settings sub-surface — Integrations > Calendar (auto-expiry)

Two settings live here. Both inherit Mockup A (system-default-with-tenant-override).

**A1. `calendar_conflict_auto_expire_days`**

| Attribute | Value |
| :--- | :--- |
| Label | Auto-expire calendar conflicts |
| Description | How long before unresolved sync conflicts auto-resolve to Pilot's version. |
| Data type | Integer (days), nullable to disable |
| Range | 1–365, or NULL to disable |
| System default | 30 |
| Save category | Save-on-blur |
| Source | A34 (Flow 6) |
| Cross-ref | Mockup A |

**A2. `calendar_conflict_pre_warning_days`**

| Attribute | Value |
| :--- | :--- |
| Label | Pre-warning notice |
| Description | Days before auto-expiry to send a pre-warning notification to the owner. |
| Data type | Integer (days), nullable to disable |
| Range | 1 to (auto_expire_days - 1), or NULL to disable |
| System default | 7 |
| Save category | Save-on-blur |
| Source | A34 (Flow 6) |
| Validation | Cross-field: must be less than `calendar_conflict_auto_expire_days` |

**Sub-surface composition**: `Settings > Integrations > Calendar > Auto-expiry`. Two fields rendered in a single section. The cross-field validation on A2 means changing A1 may require revalidating A2; the UI shows an inline warning if the relationship breaks.

### 3. Settings sub-surface — Integrations > QuickBooks (per-entity auto-expiry + sync prefs)

This is the most complex sub-surface in #4. Eight settings in two groups: per-entity auto-expiry config (4 entity-specific groups) and sync preferences (2 user-choice settings).

**B1. `qb_auto_expire_customer_enabled` + `qb_auto_expire_customer_direction`**

| Attribute | Value |
| :--- | :--- |
| Label | Customer conflicts |
| Description | When a sync conflict on a customer goes unresolved, auto-expire to a chosen direction. |
| Toggle data type | Boolean |
| Direction data type | Enum: `accept_local | accept_remote` |
| System default | OFF (no direction) |
| Save category | Save-on-group-complete (Mockup B) |
| Source | A50 (Tier 1 #2) |
| Master | User choice (no recommended direction) |
| Cross-ref | Mockup B |

**B2. `qb_auto_expire_quote_enabled` + `qb_auto_expire_quote_direction`**

| Attribute | Value |
| :--- | :--- |
| Label | Quote conflicts |
| Description | When a sync conflict on a quote goes unresolved, auto-expire to a chosen direction. |
| Recommended direction | `accept_local` (Pilot is master for Quotes per §5.3) |
| Save category | Save-on-group-complete |
| Source | A50 |

Same field shape as B1 with a "(recommended for quotes)" annotation on the `accept_local` option.

**B3. `qb_auto_expire_invoice_enabled` + `qb_auto_expire_invoice_direction`**

| Attribute | Value |
| :--- | :--- |
| Label | Invoice conflicts |
| Description | When a sync conflict on an invoice goes unresolved, auto-expire to a chosen direction. |
| Recommended direction | `accept_remote` (QB is master for Invoices per §5.3) |
| Save category | Save-on-group-complete |
| Source | A50 |
| Cross-ref | Mockup B (canonical example) |

**B4. `qb_auto_expire_expense_enabled` + `qb_auto_expire_expense_direction`**

| Attribute | Value |
| :--- | :--- |
| Label | Expense conflicts |
| Description | When a sync conflict on an expense goes unresolved, auto-expire to a chosen direction. |
| Recommended direction | (none — user choice per §5.3) |
| Save category | Save-on-group-complete |
| Source | A50 |

**B5. `qb_auto_expire_days`**

| Attribute | Value |
| :--- | :--- |
| Label | Auto-expire delay |
| Description | How long unresolved QuickBooks conflicts wait before auto-expiring. Applies to all enabled entity types. |
| Data type | Integer (days) |
| Range | 1–365 |
| System default | 60 (longer than calendar's 30 because accounting cadence is quarterly per Tier 1 #2 Decision 9) |
| Save category | Save-on-blur |
| Source | A50 |
| Cross-ref | Mockup A |

**B6. `qb_pre_warning_days`**

| Attribute | Value |
| :--- | :--- |
| Label | Pre-warning notice |
| Description | Days before auto-expiry to send a pre-warning notification. |
| Range | 1 to (auto_expire_days - 1) |
| System default | 14 |
| Save category | Save-on-blur |
| Source | A50 |
| Validation | Cross-field: must be less than `qb_auto_expire_days` |

**B7. `qb_sync_preference_customer`**

| Attribute | Value |
| :--- | :--- |
| Label | Customer master direction |
| Description | When a customer is updated in both Pilot and QuickBooks during the same sync window, which side wins by default? Affects column ordering and recommended button in conflict resolution UI. |
| Data type | Enum: `pilot_master | qb_master | user_choice` |
| System default | `user_choice` |
| Save category | Save-on-blur |
| Source | §5.3 (existing schema field; surfacing to UI) |
| Cross-ref | Tier 1 #2 Decision 3 (master-aware column ordering) |

**B8. `qb_sync_preference_expense`**

Same shape as B7, applied to expenses.

**Sub-surface composition**: `Settings > Integrations > QuickBooks > Auto-expiry & sync` is a single page with three sections:

1. **Per-entity auto-expiry** — 4 group rows (B1–B4), each rendering Mockup B
2. **Auto-expiry timing** — 2 rows (B5, B6) rendering Mockup A
3. **Sync direction preferences** — 2 rows (B7, B8) — small enum select; save-on-blur

The page is meaningfully large; the section headings make the structure scannable. A "Disable all auto-expiry" link at the top of section 1 sets all four toggles to OFF in a single atomic operation (sub-feature, not a primary affordance).

### 4. Settings sub-surface — Sync & Storage > Background sync

Four settings live here. The first inherits Mockup C (per-user override); the other three inherit Mockup A.

**C1. `background_sync_enabled`** + meta-toggle for per-user override

| Attribute | Value |
| :--- | :--- |
| Label | Enabled for the team |
| Description | Sync your team's data while Pilot is closed. Uses minimal battery and data. |
| Data type | Boolean (tenant value) + Boolean (per-user override allowed) |
| System default | TRUE for both |
| Save category | Save-on-blur (each toggle saves independently) |
| Source | A51 (Tier 1 #3) |
| Cross-ref | Mockup C |

**C2. `background_sync_wifi_only`**

| Attribute | Value |
| :--- | :--- |
| Label | WiFi-only sync |
| Description | Restrict background sync to WiFi-only connections. Useful for crews with strict cellular policies. |
| Data type | Boolean |
| System default | FALSE |
| Save category | Save-on-blur |
| Source | A51 |
| Cross-ref | Mockup A (system-default-with-tenant-override; Boolean variant) |

**C3. `background_sync_battery_floor_pct`**

| Attribute | Value |
| :--- | :--- |
| Label | Battery floor |
| Description | Below this battery percentage, background sync is skipped to preserve battery. |
| Data type | Integer (percentage) |
| Range | 5–50 |
| System default | 20 |
| Save category | Save-on-blur |
| Source | A51 |
| Cross-ref | Mockup A |

**C4. `background_sync_push_interval_minutes`**

| Attribute | Value |
| :--- | :--- |
| Label | Push frequency |
| Description | Minimum time between server-initiated sync triggers per device. Lower values sync more aggressively but cost more battery. |
| Data type | Integer (minutes) |
| Range | 1–60 |
| System default | 5 |
| Save category | Save-on-blur |
| Source | A51 |
| Cross-ref | Mockup A; system default + tenant override per arch doc §16.5 |

**Sub-surface composition**: `Settings > Sync & Storage > Background sync` is a single page with two sections:

1. **Master controls** — C1's two toggles (Mockup C)
2. **Resource policy** — C2, C3, C4 (Mockup A variants)

Plus a status row at the bottom showing the last background sync attempt and outcome (per Tier 1 #3 Decision 6).

### 5. Settings sub-surface — Sync & Storage > Offline limits

One setting.

**D1. `offline_hard_limit_hours`**

| Attribute | Value |
| :--- | :--- |
| Label | Hard limit on offline operation |
| Description | After this many hours offline, the app blocks new captures until a sync occurs. Tenants doing legitimately extended offline work (rural utility, multi-day mining sites) can disable this. |
| Data type | Integer (hours), nullable to disable |
| Range | 24–720 (one day to one month), or NULL to disable |
| System default | 72 |
| Save category | Save-on-blur |
| Source | Flow 7 D13 |
| Cross-ref | Mockup A |

The 24-hour soft-limit threshold from Flow 7 §13 is intentionally not configurable — Decision noted in Flow 7 itself that 24 hours is a UX threshold, not a policy threshold. The page notes this for transparency: "*Soft warning at 24 hours is fixed and not configurable.*"

**Sub-surface composition**: `Settings > Sync & Storage > Offline limits` is a single page, one field, with a paragraph above explaining the offline-operation model and a paragraph below describing the soft-limit behavior (read-only).

### 6. Settings sub-surface — Sync & Storage > Photos

Two settings.

**E1. `photo_upload_wifi_only`**

| Attribute | Value |
| :--- | :--- |
| Label | Upload photos on WiFi only |
| Description | Restrict photo uploads to WiFi-only connections. Photos wait for WiFi when this is on. |
| Data type | Boolean |
| System default | TRUE |
| Save category | Save-on-blur |
| Source | A41 (Flow 7) |
| Cross-ref | Mockup A (Boolean variant) |

**E2. `photo_local_retention_days`**

| Attribute | Value |
| :--- | :--- |
| Label | Local photo retention |
| Description | How long synced photos remain on device storage before auto-purge. Server copies are always retained. |
| Data type | Integer (days) |
| Range | 1–90 |
| System default | 7 |
| Save category | Save-on-blur |
| Source | A41 (Flow 7) |
| Cross-ref | Mockup A |

**Sub-surface composition**: `Settings > Sync & Storage > Photos` is a single page, two fields, with a paragraph explaining the upload-and-retention model.

### 7. Settings sub-surface — Sync & Storage > Voice capture

Decision: ship a single MVP setting with the architecture-implied limit.

**F1. `voice_offline_audio_storage_limit_mb`**

| Attribute | Value |
| :--- | :--- |
| Label | Voice capture storage limit |
| Description | Maximum on-device storage for voice commands captured while offline (audio waiting to upload). When the limit is reached, the oldest unsynced voice capture is dropped. |
| Data type | Integer (MB) |
| Range | 100–2000 |
| System default | 500 |
| Save category | Save-on-blur |
| Source | A42 (Flow 7) |
| Cross-ref | Mockup A |

This setting was flagged TBD in the framework's inventory. I'm including it in MVP because the architecture (A42) creates the local audio storage path; not surfacing a limit means runaway local storage growth on devices with high offline voice use. The 500 MB default holds roughly 50 hours of typical voice command audio (10 MB per uncompressed minute is a generous estimate).

**Sub-surface composition**: `Settings > Sync & Storage > Voice capture` is a single page, one field, with a paragraph explaining the offline voice capture model from Flow 7 §7.

### 8. Settings sub-surface — Operations > Margin buckets

Two settings.

**G1. `margin_bucket_boundaries`**

| Attribute | Value |
| :--- | :--- |
| Label | Margin bucket thresholds |
| Description | Boundaries that group jobs into profitability buckets in reports and charts. Default ranges: under 10% (red), 10–20% (amber), 20–30% (margin), over 30% (margin saturated). |
| Data type | Array of integers (percentages) |
| Validation | Monotonic ascending; each value 0–100; array length 1–4 |
| System default | `[10, 20, 30]` |
| Save category | Explicit Save (cross-field validation) |
| Source | A17 |
| Cross-ref | Mockup A — but this setting is the rare "explicit Save" case because the array is multi-step |

**Editor treatment**: numeric inputs for each boundary plus an "Add boundary" button (up to 4 boundaries) and a "Remove" affordance per boundary. The monotonicity validation runs against the whole array; partial saves would create invalid state. This is the single MVP setting that lands in the "explicit Save" category from IA framework Decision 5.

**G2. `margin_target_pct`**

| Attribute | Value |
| :--- | :--- |
| Label | Target margin |
| Description | The target margin that profitability indicators compare against. Jobs below this target show as below-target in reports. |
| Data type | Integer (percentage) |
| Range | 0–100 |
| System default | 20 |
| Save category | Save-on-blur |
| Source | A17 |
| Cross-ref | Mockup A |

**Sub-surface composition**: `Settings > Operations > Margin buckets` is a single page, two fields, with a small visual preview of how the buckets render in a chart (a thin horizontal bar showing the current bucket boundaries).

### 9. Settings sub-surface — Operations > Profitability rules

Three settings.

**H1. `etc_variance_note_required_pct`**

| Attribute | Value |
| :--- | :--- |
| Label | Note required when ETC increases by |
| Description | When a tech increases the estimated time to completion by more than this percentage, they're prompted to add a note explaining the variance. |
| Data type | Integer (percentage) |
| Range | 0–200 |
| System default | 10 |
| Save category | Save-on-blur |
| Source | A14/A16 |
| Cross-ref | Mockup A |

**H2. `etc_variance_owner_notify_pct`**

| Attribute | Value |
| :--- | :--- |
| Label | Notify owner when projected exceeds quote by |
| Description | When the projected job total exceeds the original quote by this percentage, the owner gets a notification. |
| Data type | Integer (percentage) |
| Range | 0–500 |
| System default | 50 |
| Save category | Save-on-blur |
| Source | A14/A16 |

**H3. `report_chart_threshold`**

| Attribute | Value |
| :--- | :--- |
| Label | Minimum jobs for chart rendering |
| Description | Reports with fewer jobs than this render as a table instead of a chart (charts are misleading with too few data points). |
| Data type | Integer |
| Range | 2–50 |
| System default | 8 |
| Save category | Save-on-blur |
| Source | A15 |

**Sub-surface composition**: `Settings > Operations > Profitability rules` is a single page with three fields in a single section.

### 10. Settings sub-surface — Operations > Field operations

Three settings.

**I1. `tech_color_palette`**

| Attribute | Value |
| :--- | :--- |
| Label | Tech color palette |
| Description | The color set used for tech identity across the dispatch board, calendar, and reports. Tenants with custom branding can override the default 12-hue system palette. |
| Data type | Array of hex codes |
| Validation | Each entry valid hex; array length 6–24 |
| System default | 12-hue system palette |
| Save category | Explicit Save (cross-field validation; complex multi-step editing) |
| Source | A18 |

**Editor treatment**: a swatch-grid editor where the owner can pick from preset palettes ("Default 12", "High contrast", "Pastel") or build a custom palette by adding hex codes. Custom mode triggers the explicit Save. This is the second of two MVP settings landing in the explicit Save category. **Custom palette editor is the most complex single field in the entire Tier 2 #4 surface.** I considered deferring custom palette to Phase 2 and shipping only the preset selector for MVP — flagging this as Decision 11 below.

**I2. `require_approval_for_tech_quotes`**

| Attribute | Value |
| :--- | :--- |
| Label | Require owner approval for tech-created quotes |
| Description | When ON, tech-created quotes must be reviewed and approved by an owner before customer-facing send. |
| Data type | Boolean |
| System default | ON for multi-user tenants, OFF for solo |
| Save category | Save-on-blur |
| Source | A2 |
| Cross-ref | Mockup A; warning treatment when changing this setting on a tenant with pending quotes |

**Special UX consideration**: turning this setting OFF when the tenant has pending-approval quotes in queue triggers a confirmation: "*N quotes are currently pending your approval. Turning this off will send them all to draft state — they won't auto-send. Confirm?*" The confirmation prevents an accidental "send all pending quotes" outcome.

**I3. `max_discount_pct_owner`**

| Attribute | Value |
| :--- | :--- |
| Label | Maximum discount cap |
| Description | The maximum discount percentage an owner can apply to a quote. Caps the worst case where a discount destroys job margin. |
| Data type | Integer (percentage) |
| Range | 0–50 |
| System default | 15 |
| Save category | Save-on-blur |
| Source | A3 |

**Sub-surface composition**: `Settings > Operations > Field operations` is a single page with three fields in a single section.

### 11. Tech color palette MVP scope

**Decision**: For MVP, ship only the preset palette selector (3 presets: Default 12, High contrast, Pastel). Custom palette editor is deferred to Phase 2.

**Rationale**: The custom palette editor is the most complex single-field UI in Tier 2 #4 (per setting I1 above). Color picker UI, palette validation, accessibility contrast checking, preview rendering across surfaces — all real work for a feature most tenants will never touch. Most small electrical contractors will accept the defaults; tenants with brand-color requirements are rare in the 1–5 person shop segment.

For MVP, the preset selector handles the realistic cases (some tenants want the higher-contrast palette for techs with mild color blindness; some prefer pastel for visual softness). Phase 2 adds the custom palette editor when tenant demand is observed.

**This eliminates the second "explicit Save" category setting from MVP.** I1 (preset selector) is now save-on-blur (single enum field). Only `margin_bucket_boundaries` (G1) lands in explicit Save category for MVP.

## UX patterns established (for inheritance / reuse)

| Pattern | This spec | Inherits from / extends |
| :--- | :--- | :--- |
| System-default-with-tenant-override visual treatment (canonical mockup A) | **NEW canonical implementation** | IA framework Decision 4 (pattern definition) |
| Save-on-group-complete visual treatment (canonical mockup B) | **NEW canonical implementation** | IA framework Decision 5 |
| Per-user override visual treatment (canonical mockup C) | **NEW canonical implementation** | IA framework Decision 6 |
| Three-tier user/tenant/system resolution chain | **NEW** | Arch doc §16.5 (extended from two-tier) |
| Cross-field validation with whole-form Save | Reused | IA framework Decision 5 |
| Inline validation guidance during edit | **NEW** (helper text shifts to range guidance during edit) | — |
| Recommended-direction visual annotation in enum selector | **NEW** | Tier 1 #2 Decision 3 (master-aware) |
| Pending-quote warning when toggling approval setting | **NEW** | — |
| Visual preview of bucket boundaries below the editor | **NEW** | — |

Three new canonical visual implementations (A, B, C) plus six smaller patterns. #5–#7 inherit Mockups A, B, and C directly; their settings are simpler so they reuse without extension.

## Cross-domain considerations

### A. Settings catalog endpoint (A52)

The settings search from IA framework Decision 7 needs a settings catalog — a server-rendered list of all settings with their metadata (label, description, default, range, current effective value). A52 below is this endpoint. The frontend loads it once on settings page entry and caches for the session.

### B. Effective-value resolution endpoint (A53)

The three-tier resolution chain from Mockup C (user / tenant / system / fallback) needs a server-side helper. A53 below extends the existing `get_effective_setting` helper to take a `user_id` parameter.

### C. Audit log captures all settings changes

Per IA framework Cross-Domain G, every settings change goes through `audit_log`. This applies to all settings in #4, including the per-user override changes from Mockup C. The audit row distinguishes tenant-level vs user-level overrides via a `scope` field.

### D. Help surface deep-links into settings (Tier 4 #14)

Each setting has a stable URL: `/settings/integrations/calendar/auto-expiry#calendar_conflict_auto_expire_days` (anchor for direct link to a specific setting on a settings page). Help articles in Tier 4 #14 link directly to these. The settings page handles the anchor on load by scrolling to the setting and briefly highlighting it.

### E. Onboarding flow integration (Tier 3 #10)

Tier 3 #10 walks new tenants through key settings during initial setup. The settings UI built in #4 is the destination for those onboarding steps. The onboarding flow links into specific settings pages with optional onboarding-mode rendering (a slim guided wrapper around the standard settings page).

### F. Mobile read-only renders use the same components

Per IA framework Decision 6, mobile read-only displays of these tenant settings (offline limits, photos, ETC variance notes, quote approval, voice persona) reuse the web settings field components in read-only mode. The web mockups above translate directly to mobile read-only with: edit affordance hidden, "Set by your tenant" / "Default value" provenance annotation surfaced, no edit modal.

### G. Search synonyms for #4 settings

The synonym dictionary from IA framework Decision 7 needs entries for the #4 settings. Recommended initial entries:

- "auto expire" / "auto-expire" → all `*_auto_expire_*` settings
- "margin" → margin_bucket_boundaries, margin_target_pct
- "discount" → max_discount_pct_owner
- "battery" → background_sync_battery_floor_pct
- "WiFi" → background_sync_wifi_only, photo_upload_wifi_only
- "offline" → offline_hard_limit_hours, photo_upload_wifi_only, voice_offline_audio_storage_limit_mb
- "ETC" / "estimate" → etc_variance_note_required_pct, etc_variance_owner_notify_pct
- "approval" → require_approval_for_tech_quotes
- "color" / "palette" → tech_color_palette
- "QuickBooks" / "QB" → all qb_* settings

The synonym dictionary lives in code per IA framework Decision 7; this spec contributes the entries.

### H. Onboarding scope decision for Tier 3 #10

Not every #4 setting needs to be surfaced during onboarding. The framework doc deferred this decision to Tier 3 #10 itself. As input for that decision: settings most worth surfacing during onboarding are the ones with operational impact and tenant-meaningful defaults — `require_approval_for_tech_quotes` (multi-user tenants benefit from understanding this), `margin_target_pct` (sets the tone for profitability tracking), `offline_hard_limit_hours` (techs in extended-offline work need to know about this). Most other settings can stay at defaults.

## Deferred items (Phase 2 / for future iteration)

- **Custom tech color palette editor** (per Decision 11) — Phase 2; preset selector covers MVP
- **Bulk settings import/export** — Phase 2 (per IA framework deferred items)
- **Settings versioning/history** — Phase 2 (per IA framework deferred items)
- **Settings recommendations** ("your default is suboptimal because…") — Phase 2
- **Per-customer settings overrides** (e.g., margin target per customer) — Phase 2
- **Settings change request workflow** — Phase 2
- **Setting-specific advanced editor modes** (e.g., a richer monotonicity-validating editor for margin buckets) — Phase 2; basic explicit-Save form covers MVP

## Validation checklist

Before implementation begins:

- [ ] All 18 settings from this spec match v5 ledger names exactly (no naming drift)
- [ ] Mockup A, B, C visual treatments approved and componentized
- [ ] A52 settings catalog endpoint specified (serves search and the per-page settings list)
- [ ] A53 effective-value resolution endpoint extended for three-tier (user/tenant/system) when applicable
- [ ] A54 tenant settings write endpoints specified per setting category (with audit log capture)
- [ ] A55 per-user override write endpoints specified (only for settings with user override allowed)
- [ ] Cross-field validation rules implemented (`*_pre_warning_days < *_auto_expire_days`)
- [ ] `require_approval_for_tech_quotes` toggle-OFF confirmation behavior tested with pending-quote tenants (per setting I2)
- [ ] Margin bucket monotonicity validation tested (per setting G1)
- [ ] Custom color palette editor explicitly deferred to Phase 2 (per Decision 11)
- [ ] Mobile read-only rendering tested for all mobile-surfaced settings (per IA framework Decision 6)
- [ ] Search synonyms (Cross-Domain G) added to dictionary
- [ ] Onboarding scope decision flagged for Tier 3 #10 (Cross-Domain H input documented)

## Backend additions (new for Tier 2 #4)

### A52. Settings Catalog Endpoint

**Triggered by**: IA framework Decision 7 (settings search) and the canonical mockups in this spec.

**Scope**:
- `GET /api/v1/settings/catalog` — returns a tenant-scoped catalog of all settings with metadata
- Response: array of `{key, label, description, sub_surface_path, data_type, validation_rules, system_default, current_effective_value, current_scope (system | tenant | user), revertible, requires_role}`
- Cached per-tenant on the server (invalidated on settings change)
- Loaded once per settings session on the frontend; powers search and per-page rendering

**Effort estimate**: Small-Medium — 2–3 days. Mostly a metadata aggregator over existing settings tables.

### A53. Effective-Value Resolution Endpoint (Three-Tier Extension)

**Triggered by**: Mockup C (per-user override resolution).

**Scope**:
- Extend existing `get_effective_setting()` helper in `services/setting_resolver.py` to accept optional `user_id` parameter
- Three-tier resolution: user override (if exists and tenant allows) → tenant override → system default → fallback
- New table: `user_setting_override` with columns `tenant_id`, `user_id`, `setting_key`, `value`, `created_at`, `updated_at` (unique constraint on tenant + user + key)
- Endpoint: `GET /api/v1/settings/{key}/effective?user_id=...` — returns effective value with scope annotation

**Effort estimate**: Small-Medium — 2 days.

### A54. Tenant Settings Write Endpoints

**Triggered by**: All tenant settings in Decisions 2–10.

**Scope**:
- `PUT /api/v1/settings/{key}` — write a tenant-level setting (creates or updates `tenant_setting` row)
- `DELETE /api/v1/settings/{key}` — remove tenant override (revert to system default)
- Per-setting validation enforced server-side (range checks, monotonicity, cross-field rules)
- Audit log entry for every write per IA framework Cross-Domain G
- RBAC gate: requires `owner` or `accountant` role per IA framework Decision 8
- Optimistic UI: 200 response includes the new effective value for the frontend to confirm

**Effort estimate**: Medium — 3–4 days. Per-setting validation is the cost; many setting keys means many validation rules.

### A55. Per-User Override Write Endpoints

**Triggered by**: Mockup C and setting C1 (`background_sync_enabled`).

**Scope**:
- `PUT /api/v1/settings/{key}/user-override` — write a user-level override
- `DELETE /api/v1/settings/{key}/user-override` — revert user override to inherit tenant value
- Server-side check that tenant allows per-user override before accepting the write (returns 403 if not)
- Audit log entry with `scope: 'user'` annotation
- Authentication: user can only write their own overrides (no admin write-on-behalf-of-user in MVP)

**Effort estimate**: Small — 1–2 days. Light wrapper over A53/A54 infrastructure.

### Total Tier 2 #4 backend additions

A52 (2–3 days) + A53 (2 days) + A54 (3–4 days) + A55 (1–2 days) = **8–11 days**. Falls within the framework doc's framing estimate of 8–12 days for Tier 2 settings work.

---

## What this surface does NOT cover

- Notification preferences UI — Tier 2 #5
- Voice persona tone UI — Tier 2 #6
- Account settings UI (profile, password, MFA) — Tier 2 #7
- Tier 2 #5–#7's individual backend additions
- Empty / error / loading states for settings pages — Tier 3 #8 states catalog
- First-time-user empty states for settings — Tier 3 #9
- Onboarding wrapper around settings — Tier 3 #10
- Help articles linked from settings — Tier 4 #14

## Next: Tier 2 #5 — Notification Preference Center

Tier 2 #5 is substantially smaller than #4. The scope is the per-user-per-category × per-channel notification preferences matrix (push / email / both / off, per category). It inherits Mockup A wholesale (system-default-with-tenant-override for category-level defaults; user override allowed per category for personal preferences).

Estimated 200–250 lines per the framework's Shape C deliverable definition. The matrix UI itself is the main design problem; the patterns are all already locked.
