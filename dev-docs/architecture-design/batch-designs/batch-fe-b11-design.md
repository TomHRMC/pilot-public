# FE-B11 Batch Design — Settings Foundation (Pass 4 Tier 2 #4 + Settings IA Framework)

**Status**: Ready for Implementation
**Date**: 2026-05-26
**Author**: Pilot Architect
**Prerequisite Batches**: FE-B0, FE-B1, FE-B2, FE-B3, FE-B4, FE-B5, FE-B6, FE-B7, FE-B8, FE-B9, FE-B10
**Backend Gate**: BE-B9 (settings infrastructure — A52 catalog endpoint, A53 effective settings resolution, A54 tenant settings write, A55 per-user override write)
**Gates Downstream**: FE-B12 (all settings sub-surfaces inherit `<SettingControl>`, `<EffectiveSettingDisplay>`, `useFormSaveStrategy` from this batch), FE-B13 (onboarding surfaces settings inline)
**Test Subfolder**: `apps/{web,mobile}/__tests__/batch_fe_b11/`

---

## Prerequisite Reads Completed

| Source | Key facts extracted |
|:---|:---|
| `frontend-pass-4-tier-2-settings-ia-framework.md` | 11-group web IA tree; mobile 3-question inclusion rule; State 1/2/3 visual treatment; three-category save behavior; permission gating (hide-not-disable); settings search synonym dictionary |
| `frontend-pass-4-tier-2-flow-4-configurable-thresholds-spec.md` | Three canonical mockups A/B/C; per-setting locked specs for all 18 settings across 7 sub-surfaces; Decision 11 defers custom color palette to Phase 2 (only preset selector for MVP) |
| `pilot-app-mvp-frontend-impl-plan.md §6 FE-B11` | 9-item execution order; key architectural patterns; test targets (60+ unit, 14+ integration, 3+ E2E) |
| `mvp-arch.md §16.5` | `platform_setting` table with `tenant_id` nullable for system defaults; two-tier `system_default → tenant_override` resolver; `get_effective_setting()` helper |
| `mvp-arch.md §16.8` | Optimistic UI mandatory: apply immediately with pending indicator; revert on failure; pending badge pattern established in FE-B7 |
| `pilot-react-engineer-methods.md §1, §3` | `frontend/` monorepo root; `packages/ui/src/` for all shared components; `apps/web/src/features/{kebab}/` for surface-scoped; tokens from `tokens.ts` only |
| `backend/api/routes/settings.py` | Confirmed endpoint paths + Pydantic schemas: `CatalogEntryResponse`, `EffectiveSettingResponse`, `TenantSettingWriteRequest/Response`, `BulkSettingWriteRequest/Response`, `UserOverrideWriteRequest/Response`; `DELETE /{key}/tenant-override` (FIND-158 rename); Redis cache DB=4 |
| `BaseSettingInput.tsx` | Stub props: `label`, `description`, `value: number\|null`, `onChange`, `min`, `max`, `placeholder`, `disabled`, `error`, `suffix`, `testID`; consumed by `CalendarAutoExpirySettings` via local import |
| `packages/ui/src/index.ts` | FE-B0 through FE-B10 exports confirmed; `setting-control/` directory does not yet exist; FE-B11 adds the next export block |
| `apps/web/src/app/(authed)/settings/` | Only `page.tsx` exists; no Operations/, Sync-Storage/, Notifications/ subtrees yet |
| `apps/mobile/app/(tabs)/owner.tsx` | Owner tab exists; hosts `CalendarSyncStatusSection`, `FieldIssuesSyncStatusSection`; mobile settings IA must be added here |

---

## Resolved Design Decisions

### Decision 1 — `SettingControl` Component API and `BaseSettingInput` Replacement

**Decision**: `SettingControl` lives in `packages/ui/src/setting-control/` and is exported from `packages/ui/src/index.ts` as the FE-B11 export block. It does **NOT** inherit the `BaseSettingInput` path — it is a new path at `@pilot/ui`.

**`BaseSettingInput` migration**: `CalendarAutoExpirySettings.tsx` currently imports `BaseSettingInput` from the local `./BaseSettingInput` stub. FE-B11 is responsible for updating this file to `import { SettingControl } from '@pilot/ui'`. The stub file `BaseSettingInput.tsx` is deleted as part of FE-B11 migration.

**`SettingControl` is a superset of `BaseSettingInput`**: every `BaseSettingInput` prop is supported plus the system-default-with-tenant-override tier additions. `CalendarAutoExpirySettings` maps to `SettingControl` as:
- `label` → `label` (same)
- `value: number | null` → `value: number | null` (same)
- `onChange: (value: number | null) => void` → becomes `onSave: (value: number | null) => Promise<void>` (async save; SettingControl calls this on blur per save-on-blur category)
- `min`, `max`, `suffix` → `validationRules: { min?, max? }` + `unit?: string`
- `error` → replaced by SettingControl's internal error state (SettingControl manages its own error display from `onSave` rejection)
- `disabled` → `readOnly: boolean`
- `testID` → `testID` (same)

New props required by `SettingControl` that `CalendarAutoExpirySettings` must provide:
- `scope: 'system' | 'tenant' | 'user'` — sourced from the catalog (`current_scope` field from `CatalogEntryResponse`)
- `defaultValue: number | null` — system default shown in State 1 (sourced from catalog `system_default`)
- `saveMode: 'blur' | 'group' | 'explicit'` — `'blur'` for both calendar auto-expiry fields

**Rationale**: A new path in `packages/ui/` is the correct home for a multi-surface shared component. The local stub was explicit about being a stub (`⚠️ FE-B11 STUB`). FE-B11's migration responsibility is clear and scoped to exactly one consumer file.

---

### Decision 2 — `EffectiveSettingDisplay` vs `SettingControl`: When Each Applies

**Decision**: The two components serve distinct scopes and composability roles:

| Component | When to use | Renders |
|:---|:---|:---|
| `SettingControl` | **Tenant-level** settings where the owner sees the system default (State 1) or their override (State 2) and can edit. The component IS the editable control. | Label + value input + scope annotation + revert-to-default link |
| `EffectiveSettingDisplay` | **Per-user override** settings where the UI must show the three-tier resolution chain (user layer → tenant layer → system layer) simultaneously, making the lineage visible. | Stacked "User / Tenant / System" rows with active-tier indicator + edit affordance for the user's own layer |

**Concrete usage per setting category**:
- `background_sync_enabled`, `voice_persona_tone`: **`EffectiveSettingDisplay`** — both allow per-user override; tech on mobile sees their own value + tenant default; owner on web sees the tenant toggle + `per_user_override_allowed` meta-toggle
- All other Tier 2 #4 settings (Operations, Sync & Storage tenant-only, Integrations auto-expiry): **`SettingControl`** — tenant-level only; no user override layer

**`SettingControl` read-only mode**: when `readOnly={true}`, `SettingControl` renders the value in the same State 1/2 visual style but without the edit affordance. This is the mode used for mobile read-only tenant settings per IA framework Decision 6. Platform-specific rendering: on web it renders a `<div>` block; on mobile it uses Gluestack `VStack`/`Text` primitives. The platform is resolved at render time via `Platform.OS`; a single export from `packages/ui/` handles both.

**`EffectiveSettingDisplay` read-only mode**: when `userCanEdit={false}`, the user layer shows the current value but the edit affordance is hidden. Used when tenant has `per_user_override_allowed: false`.

---

### Decision 3 — `useFormSaveStrategy` Hook API

**Decision**:

```typescript
function useFormSaveStrategy<T>(options: UseFormSaveStrategyOptions<T>): UseFormSaveStrategyReturn<T>
```

**The hook is instantiated once per `saveMode`**. Fields register themselves through returned helper functions.

**Modes**:

**`'blur'`** — saves a single field immediately when it loses focus (or when its value changes for boolean toggles). No group concept.
- Caller provides `onSave: (key: string, value: T) => Promise<void>`
- Hook provides `getFieldProps(key)` which returns `{ onBlur, onChange }` event handlers
- No group state

**`'group'`** — defers save until all required fields in the group are filled
- Caller provides `fields: GroupFieldDef[]` (each `{ key: string, required: boolean }`) + `onSave: (values: Record<string, T>) => Promise<void>`
- Hook tracks which required fields are set; fires `onSave` atomically when all required fields have values
- On navigation-away with an incomplete group: hook calls `onRollback()` (provided by caller) to reset all fields to `lastSavedValues`; the hook internally stores `lastSavedValues` at mount time
- "User abandons mid-group" detection: the hook registers a `beforeunload`/route-change listener; if the group is incomplete when the listener fires, it calls `onRollback()`
- Returns `groupIsComplete: boolean` for `<SaveOnGroupCompleteIndicator>` to consume
- Returns `incompleteFields: string[]` for driving the "required" visual annotation on unfilled fields

**`'explicit'`** — caller provides a Save button; hook tracks dirty state
- Caller provides `initialValues: Record<string, T>` + `onSave: (values: Record<string, T>) => Promise<void>`
- Hook provides `isDirty: boolean` + `handleSave: () => Promise<void>` + `handleDiscard: () => void`
- Discard resets all field values to `initialValues`

**Return type unification**: all three modes return a subset of a common `UseFormSaveStrategyReturn<T>` interface (fields not applicable to the current mode are `undefined`). Callers only destructure what they need.

**Rollback on abandonment** (group mode only): the hook uses `useEffect` cleanup + Next.js router `beforePopState`/`window.beforeunload` to detect navigation. If the group is incomplete at cleanup time, all fields revert to `lastSavedValues`. The rollback call is to `onRollback()` — the caller is responsible for resetting their local state via this callback; the hook does not directly mutate field values.

---

### Decision 4 — Settings Catalog Endpoint Integration and Data-Driven Rendering

**Decision**: The catalog metadata IS sufficient to drive every field's rendering for the 18 Tier 2 #4 settings — `CatalogEntryResponse` includes `data_type`, `validation_rules`, `system_default`, `current_effective_value`, `current_scope`, `allows_user_override`. FE-B11 maps these to `SettingControl` / `EffectiveSettingDisplay` props.

**Hybrid approach**: settings rendering is **catalog-driven for values and validation** but **surface-coded for layout and grouping**. Reason: save-on-group-complete groups (QB per-entity auto-expiry pairs) require coded pairing logic; the catalog cannot express "these two settings form a group where the second is conditional on the first." The seven sub-surface pages are coded components that know which settings belong to each group — they query from the catalog by key to get values and metadata, but they code their own field layout.

**What comes from the catalog** (fetched once on settings page entry, cached per tenant):
- `current_effective_value` → displayed as the current value
- `current_scope` → drives State 1 (`'system'`) vs State 2 (`'tenant'`/`'user'`) in `SettingControl`
- `system_default` → shown in State 1 annotation ("Default · 30 days")
- `validation_rules` → passed to `SettingControl` for client-side range validation
- `label`, `description` → rendered as field label and helper text
- `allows_user_override` → determines whether `EffectiveSettingDisplay` or `SettingControl` is used

**What is coded per-surface**:
- Which settings keys appear on which page
- Save-on-group-complete groupings (QB toggle + direction pairs)
- Cross-field validation (pre_warning < auto_expire dependency)
- Section headings and layout order

**TanStack Query cache strategy**:

```typescript
// Catalog query key — tenant-scoped
const settingsCatalogQueryKey = ['settings-catalog'] as const;

// Cache config:
staleTime: 5 * 60 * 1000  // 5 minutes; catalog metadata rarely changes
gcTime: 30 * 60 * 1000    // 30 minutes in memory

// Invalidation triggers:
// 1. After any successful PUT /settings/{key} (tenant write)
// 2. After any successful DELETE /settings/{key}/tenant-override (revert)
// 3. After any successful PUT /settings/{key}/user-override
// 4. After any successful PUT /settings/bulk
// queryClient.invalidateQueries({ queryKey: ['settings-catalog'] })
```

**Settings search**: client-side filter over the loaded catalog. The synonym dictionary lives in `packages/ui/src/setting-control/synonyms.ts` (per IA framework Cross-Domain F). Search runs against `label`, `description`, and synonym entries. No backend search endpoint needed for MVP.

---

### Decision 5 — Mobile Read-Only Settings Rendering

**Decision**: `SettingControl` has a `readOnly` prop that renders in React Native via a **platform-aware implementation**. There is no separate `MobileSettingReadOnly` component. The component resolves its platform at runtime using `Platform.OS`:
- **Web** (`Platform.OS === 'web'`): renders using Tailwind `div` + `input` primitives
- **Mobile** (`Platform.OS !== 'web'`): renders using Gluestack `VStack` + `Text` + Pressable primitives

The `readOnly` mobile variant adds the **provenance annotation** (`"Set by your tenant"` when `scope === 'tenant'`, `"Default value"` when `scope === 'system'`) below the value display. This annotation does not appear on web because web owners can see the State 1/2 visual treatment instead.

**Mobile settings location**: the two mobile-only sections live in:
- `apps/mobile/features/settings/` — new feature folder (created in FE-B11)
  - `SyncStorageSettingsSection.tsx` — Sync & Storage read-only (4 settings: wifi_only, battery_floor, offline_limit, photo_wifi_only)
  - `OperationsSettingsSection.tsx` — Operations read-only (2 settings: etc_variance_note_required_pct, require_approval_for_tech_quotes)
  - `VoiceSettingsSection.tsx` — Voice editable (persona_tone per-user override, wake word, volume)

These sections are mounted in a new mobile settings route accessible from the Owner tab or a dedicated Settings entry point in the mobile navigation. They compose `<SettingControl readOnly />` for tenant-locked settings and `<EffectiveSettingDisplay>` for per-user override settings.

**Mobile settings route**: `apps/mobile/app/(tabs)/(home)/settings/` — a new nested route under the home tab group, accessible via a settings icon in the Today tab header.

---

### Decision 6 — Revert-to-Default Micro-Confirmation Pattern

**Decision**: The revert-to-default confirmation is an **inline confirmation** (text + Confirm/Cancel buttons appear in-place, replacing the "Revert to default" link). It is NOT a modal dialog. The `<RevertToDefaultDialog>` component name is kept for architectural clarity (it's the "dialog-as-turn" interaction from the spec), but it renders inline within the `SettingControl` field area, not as a floating modal.

**Visual treatment** when `[ Revert to default ]` is clicked:
```
Before click (State 2):
  45 days                              [ Revert to default ]

After click (inline confirmation replaces the link):
  Revert "Auto-expire calendar conflicts" from 45 days → 30 days (system default)?
  [ Cancel ]    [ Revert ]
```
The current value + system default value are both shown inline so the owner knows exactly what they're accepting. This matches the spec's "small confirm-as-turn micro-confirmation" intent without spawning a floating dialog that disrupts the settings page scroll context.

**System default value source**: comes from the catalog response `system_default` field — already loaded in the page's catalog query. No additional API call needed. The `CatalogEntryResponse.system_default` is passed to `SettingControl` as the `defaultValue` prop.

**After confirm**: `DELETE /api/v1/settings/{key}/tenant-override` fires. On success:
1. `queryClient.invalidateQueries({ queryKey: ['settings-catalog'] })` triggers a catalog refetch
2. `SettingControl` transitions to State 1 (scope becomes `'system'`)
3. A brief `NotificationBanner severity="success"` fires: `"Reverted to default."`

**`RevertToDefaultDialog` lives in `packages/ui/`** so FE-B12 can compose it for its own settings fields (notification preferences have revert-to-default affordances too). It is a presentational component that accepts the current value, default value, setting label, `onConfirm`, and `onCancel` as props.

---

### Decision 7 — Settings Search Affordance

**Decision**: Global settings search is **in scope for FE-B11**. The implementation is a **client-side filter** over the loaded catalog response, consistent with IA framework Decision 7 ("runs client-side against the loaded settings catalog — no backend search endpoint").

**Search input placement**: pinned to the top of the settings sidebar (`<SettingsSidebarSearch>`) on web. When the user types, a dropdown appears below the input showing matching settings with path (`Operations > Margin buckets`), current value, and a click handler that navigates to the parent page and scrolls to the specific setting via anchor ID.

**Synonym dictionary**: a flat map in `packages/ui/src/setting-control/synonyms.ts` — an object of `{ [synonym]: string[] }` where values are setting keys. The search algorithm:
1. Find all catalog entries where `label.toLowerCase().includes(query)` or `description.toLowerCase().includes(query)`
2. Additionally find all setting keys whose synonym array contains `query`
3. Merge results, deduplicate by key

**Mobile**: no settings search on mobile (IA framework Decision 7 rationale: mobile tree < 15 leaves; scrolling faster than search). No `<SettingsSidebarSearch>` on mobile.

**FE-B12 impact**: FE-B12 adds Tier 2 #5, #6, #7 settings to the catalog. The search automatically covers them because it queries the live catalog — no FE-B12-side search configuration needed.

---

## A — Component Implementation Plan

### A.1 New Shared Components (`packages/ui/src/`)

#### A.1.1 `SettingControl` (Mockup A — system-default-with-tenant-override)

**File**: `packages/ui/src/setting-control/SettingControl.tsx`

**Purpose**: The canonical setting field component for any tenant-level or user-level setting that follows the system-default-with-tenant-override pattern (arch doc §16.5). Renders three states (State 1: inheriting default, State 2: tenant-overridden, revert-pending: inline confirmation visible). Platform-aware: web uses Tailwind + shadcn primitives; mobile uses Gluestack primitives via `Platform.OS` branch.

**Pattern references**: IA framework Decision 4 (State 1/2/3 visual treatment); Tier 2 #4 Mockup A; arch doc §16.5 (data shape); arch doc §16.8 (optimistic UI)

**Downstream consumers**: FE-B8's `CalendarAutoExpirySettings` (migration target), FE-B11 all 18 Tier 2 #4 settings, FE-B12 notification prefs + voice persona + account settings

**Sub-components co-located in same directory**:
- `packages/ui/src/setting-control/RevertToDefaultDialog.tsx` — inline confirmation panel (Decision 6)
- `packages/ui/src/setting-control/synonyms.ts` — settings search synonym dictionary
- `packages/ui/src/setting-control/index.ts` — barrel export

**Export from**: `packages/ui/src/index.ts` — FE-B11 section

---

#### A.1.2 `useFormSaveStrategy` (Mockup B — save-on-group-complete behavior hook)

**File**: `packages/ui/src/hooks/useFormSaveStrategy.ts`

**Purpose**: The canonical hook implementing three save modes (`'blur'`, `'group'`, `'explicit'`). Established here; consumed by every settings surface in FE-B11 and FE-B12.

**Pattern reference**: IA framework Decision 5 (three-category save behavior); Tier 2 #4 Mockup B

**Export from**: `packages/ui/src/index.ts` — FE-B11 section

---

#### A.1.3 `SaveOnGroupCompleteIndicator`

**File**: `packages/ui/src/setting-control/SaveOnGroupCompleteIndicator.tsx`

**Purpose**: Visual feedback component that renders when a group-save completes (subtle "Saved ✓" tick that auto-fades). Also renders the "incomplete group" visual state (subtle border tint on the unfilled required field + inline message "Pick a direction to complete this setting."). Pairs with `useFormSaveStrategy({ mode: 'group' })`.

**Export from**: `packages/ui/src/index.ts` — FE-B11 section

---

#### A.1.4 `EffectiveSettingDisplay` (Mockup C — per-user override three-tier display)

**File**: `packages/ui/src/setting-control/EffectiveSettingDisplay.tsx`

**Purpose**: Renders the three-tier resolution chain (user → tenant → system) for settings that allow per-user override. Shows scope badges (`User`, `Tenant`, `System`) alongside each tier's value, highlighting the active tier. On web: owner sees tenant default + `per_user_override_allowed` meta-toggle. On mobile: tech sees their own override value + tenant default below + "Match tenant default" revert link.

**Pattern reference**: IA framework Decision 4 (per-user override treatment); Tier 2 #4 Mockup C

**Downstream consumers**: FE-B11 (`background_sync_enabled`), FE-B12 (notification preferences matrix, voice persona tone)

**Export from**: `packages/ui/src/index.ts` — FE-B11 section

---

#### A.1.5 `SettingsSidebarSearch`

**File**: `packages/ui/src/setting-control/SettingsSidebarSearch.tsx`

**Purpose**: Search input + type-ahead results dropdown for the web settings sidebar. Client-side filtering over `CatalogEntry[]`. Shows setting name, current value, and path breadcrumb in results. Navigation on click.

**Export from**: `packages/ui/src/index.ts` — FE-B11 section

---

### A.2 New Web Feature Components

#### A.2.1 Settings IA Shell — `apps/web/src/features/settings/`

| File | Purpose |
|:---|:---|
| `components/SettingsShell.tsx` | Top-level layout: left sidebar (11 group items + `<SettingsSidebarSearch>`), right content area. Sidebar items are role-gated per IA framework Decision 8 (hide-not-disable). |
| `components/SettingsSidebar.tsx` | Sidebar navigation: 11 groups, each linking to their sub-page tree. Active group highlighted. |
| `components/SettingsSection.tsx` | Reusable page section wrapper: section heading, vertical list of `<SettingControl>` / `<EffectiveSettingDisplay>` fields. |
| `hooks/useSettingsCatalog.ts` | TanStack Query: `GET /api/v1/settings/catalog`; returns `CatalogEntry[]`; powers search + per-page value display |
| `hooks/useTenantSettingWrite.ts` | Mutation: `PUT /api/v1/settings/{key}` + optimistic update; invalidates catalog on success |
| `hooks/useTenantSettingRevert.ts` | Mutation: `DELETE /api/v1/settings/{key}/tenant-override`; invalidates catalog on success |
| `hooks/useBulkSettingWrite.ts` | Mutation: `PUT /api/v1/settings/bulk`; used by save-on-group-complete groups; invalidates catalog |
| `hooks/useUserOverrideWrite.ts` | Mutation: `PUT /api/v1/settings/{key}/user-override`; invalidates catalog |
| `hooks/useUserOverrideRevert.ts` | Mutation: `DELETE /api/v1/settings/{key}/user-override`; invalidates catalog |
| `mocks/settingsFixtures.ts` | Typed fixture data: catalog response with all 18+ settings in scope=system and scope=tenant variants |
| `mocks/settingsHandlers.ts` | MSW handlers for all settings endpoints |

#### A.2.2 Operations Sub-Surfaces — `apps/web/src/features/settings-operations/`

| File | Route |
|:---|:---|
| `components/MarginBucketsPage.tsx` | `Settings > Operations > Margin buckets` — G1 (explicit Save) + G2 (save-on-blur) |
| `components/ProfitabilityRulesPage.tsx` | `Settings > Operations > Profitability rules` — H1, H2, H3 (all save-on-blur) |
| `components/FieldOperationsPage.tsx` | `Settings > Operations > Field operations` — I1 (preset selector, save-on-blur), I2 (save-on-blur + pending-quote confirmation), I3 (save-on-blur) |

#### A.2.3 Sync & Storage Sub-Surfaces — `apps/web/src/features/settings-sync-storage/`

| File | Route |
|:---|:---|
| `components/BackgroundSyncPage.tsx` | `Settings > Sync & Storage > Background sync` — C1 (`<EffectiveSettingDisplay>`), C2–C4 (`<SettingControl>`) |
| `components/OfflineLimitsPage.tsx` | `Settings > Sync & Storage > Offline limits` — D1 (save-on-blur) |
| `components/PhotosPage.tsx` | `Settings > Sync & Storage > Photos` — E1, E2 (both save-on-blur) |
| `components/VoiceCapturePage.tsx` | `Settings > Sync & Storage > Voice capture` — F1 (save-on-blur) |

#### A.2.4 Integrations Auto-Expiry Sub-Surfaces (migration/extension of existing pages)

**Calendar auto-expiry**: Already lives in `apps/web/src/features/calendar-conflict/components/CalendarAutoExpirySettings.tsx`. FE-B11 migrates it to use `<SettingControl>` from `@pilot/ui` instead of the `BaseSettingInput` stub. No route change.

**QuickBooks auto-expiry & sync prefs**: New page added to the existing QuickBooks integration settings:

| File | Route |
|:---|:---|
| `components/QbAutoExpirySyncPage.tsx` | `Settings > Integrations > QuickBooks > Auto-expiry & sync` — B1–B4 (save-on-group-complete), B5–B6 (save-on-blur, cross-field validation), B7–B8 (save-on-blur) |

---

### A.3 New Mobile Feature Components

All mobile settings components live in `apps/mobile/features/settings/`.

| File | Purpose |
|:---|:---|
| `components/SyncStorageSettingsSection.tsx` | Read-only display of `background_sync_wifi_only`, `background_sync_battery_floor_pct`, `offline_hard_limit_hours`, `photo_upload_wifi_only` using `<SettingControl readOnly>` with provenance annotation |
| `components/BackgroundSyncUserControl.tsx` | `background_sync_enabled` per-user override using `<EffectiveSettingDisplay>` in mobile mode; editable if tenant allows |
| `components/OperationsSettingsSection.tsx` | Read-only display of `etc_variance_note_required_pct`, `require_approval_for_tech_quotes` using `<SettingControl readOnly>` |
| `components/VoicePersonaSection.tsx` | `voice_persona_tone` per-user override using `<EffectiveSettingDisplay>`; editable if tenant allows |
| `hooks/useMobileSettingsCatalog.ts` | TanStack Query: `GET /api/v1/settings/catalog`; same hook as web but `staleTime: 10 * 60 * 1000` (10 min; mobile reads less frequently) |

---

### A.4 New Routes

#### A.4.1 Web Settings Sub-Routes (new files, all under `(authed)/settings/`)

| Route | File | Auth | Role Gate | Notes |
|:---|:---|:---:|:---|:---|
| `/settings` | `(authed)/settings/page.tsx` | Required | `owner\|accountant` (most groups); see table | Existing file — updated to compose `<SettingsShell>` with full sidebar |
| `/settings/operations` | `(authed)/settings/operations/page.tsx` | Required | `settings.tenant.write` | Redirect to first sub-page |
| `/settings/operations/margin-buckets` | `(authed)/settings/operations/margin-buckets/page.tsx` | Required | `settings.tenant.write` | Explicit Save for G1 |
| `/settings/operations/profitability-rules` | `(authed)/settings/operations/profitability-rules/page.tsx` | Required | `settings.tenant.write` | Save-on-blur |
| `/settings/operations/field-operations` | `(authed)/settings/operations/field-operations/page.tsx` | Required | `settings.tenant.write` | Save-on-blur; pending-quote confirmation for I2 |
| `/settings/sync-storage` | `(authed)/settings/sync-storage/page.tsx` | Required | `settings.tenant.write` | Redirect to first sub-page |
| `/settings/sync-storage/background-sync` | `(authed)/settings/sync-storage/background-sync/page.tsx` | Required | `settings.tenant.write` | Mockup C for C1; Mockup A for C2–C4 |
| `/settings/sync-storage/offline-limits` | `(authed)/settings/sync-storage/offline-limits/page.tsx` | Required | `settings.tenant.write` | Single field |
| `/settings/sync-storage/photos` | `(authed)/settings/sync-storage/photos/page.tsx` | Required | `settings.tenant.write` | Two fields |
| `/settings/sync-storage/voice-capture` | `(authed)/settings/sync-storage/voice-capture/page.tsx` | Required | `settings.tenant.write` | Single field |
| `/settings/integrations/quickbooks/auto-expiry` | `(authed)/settings/integrations/quickbooks/auto-expiry/page.tsx` | Required | `integrations.manage` | QB auto-expiry groups B1–B4 + timing B5–B6 + sync prefs B7–B8 |

#### A.4.2 Mobile Settings Route (new)

| Route | File | Auth | Notes |
|:---|:---|:---:|:---|
| `/(tabs)/(home)/settings` | `apps/mobile/app/(tabs)/(home)/settings/index.tsx` | Required | Mobile settings entry point with sections: My Account, Sync & Storage, Operations, Voice |
| `/(tabs)/(home)/settings/sync-storage` | `apps/mobile/app/(tabs)/(home)/settings/sync-storage.tsx` | Required | `<BackgroundSyncUserControl>` + `<SyncStorageSettingsSection>` |
| `/(tabs)/(home)/settings/operations` | `apps/mobile/app/(tabs)/(home)/settings/operations.tsx` | Required | `<OperationsSettingsSection>` read-only |
| `/(tabs)/(home)/settings/voice` | `apps/mobile/app/(tabs)/(home)/settings/voice.tsx` | Required | `<VoicePersonaSection>` + wake word + volume |

---

## B — Execution Order

| Step | Item | Rationale |
|:---:|:---|:---|
| 1 | **`useSettingsCatalog` hook + MSW handlers for all 5 settings endpoints** | All subsequent surface work must mock the catalog and write endpoints. Write fixtures (scope=system variant + scope=tenant variant for each of the 18 settings) before touching any component. |
| 2 | **`<SettingControl>` + `<RevertToDefaultDialog>` + `synonyms.ts` in `packages/ui/`** | The canonical Mockup A visual treatment. All 7 sub-surfaces compose this. Must be fully tested before wiring to real catalog data. `CalendarAutoExpirySettings` migration waits until Step 3. |
| 3 | **`useFormSaveStrategy` hook + `<SaveOnGroupCompleteIndicator>` in `packages/ui/`** | Mockup B (save-on-group-complete) depends on this hook. QB auto-expiry pairs cannot be built without it. Build and test all three modes independently before any surface uses them. |
| 4 | **`<EffectiveSettingDisplay>` in `packages/ui/`** | Mockup C (per-user override). Required for `BackgroundSyncPage` and `VoiceCapturePage`. Establishes the three-tier display FE-B12 will heavily use for notification preferences. |
| 5 | **Settings IA shell (web): `<SettingsShell>`, `<SettingsSidebar>`, `<SettingsSidebarSearch>` + all new web routes (placeholder pages)** | Before building individual sub-surfaces, the shell and route tree must exist. Placeholder pages with "Coming soon" content verify routing. New Operations/Sync-Storage routes created here. |
| 6 | **Configurable thresholds settings (Tier 2 #4) — all 7 sub-surfaces**: Calendar auto-expiry migration (stub → `SettingControl`); Operations sub-surfaces (G1–G2, H1–H3, I1–I3); Sync & Storage sub-surfaces (C1–C4, D1, E1–E2, F1); QB auto-expiry & sync (B1–B8) | The core Tier 2 #4 deliverable. Build in order: calendar migration (simplest — 2 fields already exist), then Operations (save-on-blur majority), then Sync & Storage, then QB (most complex; save-on-group-complete groups require hook from Step 3). |
| 7 | **Mobile settings IA + read-only sub-surfaces** | Mobile settings route tree, `SyncStorageSettingsSection`, `OperationsSettingsSection`, `BackgroundSyncUserControl`, `VoicePersonaSection`. All read from the same catalog hook established in Step 1. |
| 8 | **`<SettingsSidebarSearch>` wired to live catalog + synonym dictionary** | Search is functional only after all settings keys are in the catalog. Wire after all sub-surfaces are built so synonym entries cover all 18 settings. |
| 9 | **Tenant write + revert-to-default integration** | Wire `useTenantSettingWrite`, `useTenantSettingRevert`, `useBulkSettingWrite` to actual BE-B9 endpoints with `expected_updated_at` optimistic locking. Run final integration tests confirming catalog invalidation on write. |

**Rationale summary**: shared components first (Rule 1 from methods doc); hook before components that consume it (Step 3 before Step 6 QB); mock-driven throughout (Step 1 MSW before any surface work); IA shell before sub-surfaces (routing must exist before pages); mobile after web (mobile composes same `SettingControl` in readOnly mode — web validates the component first).

---

## C — API Contracts

### C.1 `GET /api/v1/settings/catalog` (A52)

**TanStack Query key**: `['settings-catalog']`
**Cache**: `staleTime: 5 * 60 * 1000` (5 min); `gcTime: 30 * 60 * 1000`; `refetchOnWindowFocus: false` (avoid noisy refetches on tab switch)
**Hook**: `useSettingsCatalog()`

**Request**: No params (tenant resolved from auth token)

**Response** (typed from `CatalogResponse`):
```typescript
interface CatalogResponse {
  settings: CatalogEntry[];
}

interface CatalogEntry {
  key: string;                     // e.g. 'calendar_conflict_auto_expire_days'
  label: string;                   // e.g. 'Auto-expire calendar conflicts'
  description: string;             // 1-2 sentence explainer
  sub_surface_path: string;        // e.g. '/settings/integrations/general'
  data_type: 'boolean' | 'integer' | 'decimal' | 'string' | 'array';
  validation_rules: {
    min?: number;
    max?: number;
    allowed_values?: string[];
  };
  system_default: unknown;         // The system default value (null for array types on first load)
  current_effective_value: unknown; // Resolved for requesting user (user → tenant → system)
  current_scope: 'user' | 'tenant' | 'system' | 'fallback';
  revertible: boolean;
  requires_role: string | null;    // null = any role; 'staff' = Pilot staff only
  allows_user_override: boolean;
}
```

**Cache invalidation**: after any successful `PUT /settings/{key}`, `DELETE /settings/{key}/tenant-override`, `PUT /settings/bulk`, `PUT /settings/{key}/user-override`, `DELETE /settings/{key}/user-override` — all mutation hooks call `queryClient.invalidateQueries({ queryKey: ['settings-catalog'] })`.

**Lookup helper** (derived from catalog, no API call):
```typescript
// Convenience selector — memoized in useSettingsCatalog return
function getCatalogEntry(key: string): CatalogEntry | undefined
function getCatalogEntriesForPath(subSurfacePath: string): CatalogEntry[]
```

---

### C.2 `GET /api/v1/settings/{key}/effective` (A53)

**TanStack Query key**: `['settings-effective', key, userId?]`
**Cache**: `staleTime: 0` (always fresh for a decision-surface); `refetchOnWindowFocus: true`
**Hook**: Used internally by `useSettingsCatalog` for initial page load; direct calls only needed when per-user override needs to be explicitly resolved for a specific user

**Response** (typed from `EffectiveSettingResponse`):
```typescript
interface EffectiveSettingResponse {
  key: string;
  value: unknown;
  scope: 'user' | 'tenant' | 'system' | 'fallback';
  tenant_override_exists: boolean;
  user_override_exists: boolean;
  allows_user_override: boolean;
}
```

---

### C.3 `PUT /api/v1/settings/{key}` (A54 — tenant write)

**Hook**: `useTenantSettingWrite()`

**Request body** (typed from `TenantSettingWriteRequest`):
```typescript
interface TenantSettingWriteRequest {
  value: unknown;
  expected_updated_at?: string;    // ISO datetime — optimistic locking; omit for first write
}
```

**Response 200** (typed from `TenantSettingWriteResponse`):
```typescript
interface TenantSettingWriteResponse {
  key: string;
  value: unknown;
  effective_value: unknown;        // post-write resolved value; update UI to this
  scope: string;
  updated_at: string;              // ISO datetime — store as next expected_updated_at
  pending_quote_count?: number;    // Only for require_approval_for_tech_quotes toggle OFF
}
```

**Optimistic update pattern**:
```typescript
// In useTenantSettingWrite onMutate:
const previousCatalog = queryClient.getQueryData(['settings-catalog']);
queryClient.setQueryData(['settings-catalog'], (old: CatalogResponse) => ({
  settings: old.settings.map(s =>
    s.key === key
      ? { ...s, current_effective_value: value, current_scope: 'tenant' }
      : s
  ),
}));
// On error: queryClient.setQueryData(['settings-catalog'], previousCatalog)
// On success: queryClient.invalidateQueries({ queryKey: ['settings-catalog'] })
```

**`pending_quote_count` handling**: when `key === 'require_approval_for_tech_quotes'` and `value === false`, check response `pending_quote_count`. If `> 0`, surface a `NotificationBanner severity="warning"`: `"N quotes are pending your approval. Disabling this won't auto-send them — they'll return to draft. [Confirm] [Cancel]"` before the write fires. The confirmation is surfaced by `FieldOperationsPage` before calling `mutate`.

---

### C.4 `DELETE /api/v1/settings/{key}/tenant-override` (A54 — revert to system default)

**Hook**: `useTenantSettingRevert()`

**No request body**. HTTP DELETE.

**Response 200**: `TenantSettingWriteResponse` where `value: null` and `scope: 'system'` (or `'fallback'`)

**Response 404**: when no tenant override exists — surface `NotificationBanner severity="error"`: `"No override to revert."`

**Optimistic update**: same pattern as C.3 — optimistically set `current_scope: 'system'` and `current_effective_value: system_default` before confirmation; rollback on error.

---

### C.5 `PUT /api/v1/settings/bulk` (A54 — atomic group write)

**Hook**: `useBulkSettingWrite()`

**Request body** (typed from `BulkSettingWriteRequest`):
```typescript
interface BulkSettingWriteRequest {
  values: Record<string, unknown>;  // e.g. { 'qb_auto_expire_invoice_enabled': true, 'qb_auto_expire_invoice_direction': 'accept_remote' }
}
```

**Response 200** (typed from `BulkSettingWriteResponse`):
```typescript
interface BulkSettingWriteResponse {
  updated: string[];
  results: TenantSettingWriteResponse[];
}
```

**When used**: exclusively by `useFormSaveStrategy({ mode: 'group' })` when the group reaches a complete-and-valid state. Single-key `PUT /{key}` is used for all other saves.

**Backend enforcement**: if a key has `save_on_group_complete` in its validation rules and a single-key PUT is attempted, the backend returns 422. The frontend never single-saves group-complete keys (enforced by `useFormSaveStrategy`), but this is the server-side backstop.

---

### C.6 `PUT /api/v1/settings/{key}/user-override` (A55)

**Hook**: `useUserOverrideWrite()`

**Request body** (typed from `UserOverrideWriteRequest`):
```typescript
interface UserOverrideWriteRequest {
  value: unknown;
}
```

**Response 200** (typed from `UserOverrideWriteResponse`):
```typescript
interface UserOverrideWriteResponse {
  key: string;
  value: unknown;
  effective_value: unknown;
  scope: string;
  updated_at: string;
}
```

**403 when `allows_user_override: false`**: `EffectiveSettingDisplay` gates the edit affordance client-side using the catalog's `allows_user_override` field; but the server also enforces this.

---

### C.7 `DELETE /api/v1/settings/{key}/user-override` (A55 — revert user override to tenant/system)

**Hook**: `useUserOverrideRevert()`

**No request body**. HTTP DELETE.

**Response 200**: `UserOverrideWriteResponse` where `value: null` and `scope` reflects the new effective scope after user override removal.

---

## D — State Management

### D.1 Catalog Cache Lifecycle

```
On settings page entry (/settings or any sub-route)
  → useSettingsCatalog() triggers GET /api/v1/settings/catalog
  → Stored at queryKey ['settings-catalog']
  → 5-minute staleTime; no refetch on window focus

On settings write (PUT/DELETE):
  → Optimistic update applied immediately to ['settings-catalog'] cache
  → Mutation completes → invalidateQueries(['settings-catalog']) triggers refetch
  → UI settles to server-confirmed state

On settings page exit (navigate away):
  → Cache persists for 30 minutes (gcTime)
  → If user returns within 5 minutes: stale data; no refetch needed
  → If user returns after 5 minutes: refetch triggered automatically
```

### D.2 `SettingControl` State Machine

```typescript
type SettingControlState =
  | { phase: 'clean' }                   // Displaying current effective value; no pending edit
  | { phase: 'editing'; draftValue: unknown }  // User is actively editing the field
  | { phase: 'save-pending'; draftValue: unknown }  // onSave called; awaiting server confirmation
  | { phase: 'saved'; confirmedAt: number }  // Brief success state; transitions to 'clean' after 2s
  | { phase: 'error'; error: string; draftValue: unknown }  // Save failed; revert to pre-edit value
  | { phase: 'revert-pending' }          // Revert-to-default inline confirmation visible
```

State transitions:
- `clean → editing`: user focuses/clicks into the field
- `editing → save-pending`: field loses focus (blur mode) OR group completes (group mode) OR Save button clicked (explicit mode)
- `save-pending → saved`: server 200 response
- `save-pending → error`: server error (any non-200); field reverts to pre-edit value
- `saved → clean`: 2-second auto-transition
- `clean → revert-pending`: user clicks "Revert to default" link
- `revert-pending → save-pending`: user confirms revert (DELETE mutation fires)
- `revert-pending → clean`: user cancels revert

### D.3 `useFormSaveStrategy` State (group mode)

```typescript
interface GroupSaveState {
  fieldValues: Record<string, unknown>;        // Current values for all fields in the group
  lastSavedValues: Record<string, unknown>;    // Values at mount (for rollback)
  incompleteFields: string[];                  // Required fields not yet filled
  groupIsComplete: boolean;                   // All required fields have values
  savePending: boolean;                        // Bulk write in-flight
  savedAt: number | null;                      // Timestamp of last successful group save
  error: string | null;                        // Group-level error from failed bulk write
}
```

### D.4 Settings Page Local State

| State | Location | Notes |
|:---|:---|:---|
| Catalog entries | TanStack Query `['settings-catalog']` | Shared across all settings pages |
| Write mutation status | Each hook's `mutation.status` | Per-field; not global |
| Group completion state | `useFormSaveStrategy` internal | Per group instance |
| Revert confirmation visibility | `SettingControl` internal (`useState`) | Per-field; inline |
| Pending-quote count (I2) | `TenantSettingWriteResponse.pending_quote_count` | Response field; local state in `FieldOperationsPage` |
| Search query | `useState<string>('')` in `SettingsSidebarSearch` | Local; not persisted |

---

## E — Error States

### E.1 Catalog Load Failure

**Trigger**: `useSettingsCatalog` query returns error state.

**User sees**: Full-page `<ErrorState type="network">` from `packages/ui/src/states/` with retry CTA. Settings sub-pages show the same error state (catalog required for all pages).

**Token**: `text-fault-600` for error headline; `bg-fault-50` for container.

### E.2 Settings Write Failure (Save-on-Blur)

**Trigger**: `PUT /api/v1/settings/{key}` returns non-200.

**User sees**: Field reverts to its pre-edit value (optimistic rollback). An inline error tooltip appears below the field: `"Save failed · [server error message]"`. `SettingControl` transitions to `phase: 'error'`.

**Token**: `text-fault-600` for error text; `border-fault-200` for field border in error state.

### E.3 Settings Write Failure (Save-on-Group-Complete)

**Trigger**: `PUT /api/v1/settings/bulk` returns non-200 for a QB auto-expiry group.

**User sees**: All fields in the group revert to `lastSavedValues` (rollback via `onRollback()` callback). A `NotificationBanner severity="error"` fires at page level: `"Couldn't save — try again."` Group returns to `phase: 'editing'` state.

### E.4 Revert Failure

**Trigger**: `DELETE /api/v1/settings/{key}/tenant-override` returns non-200.

**User sees**: Optimistic rollback to State 2. Inline error in the `<RevertToDefaultDialog>`: `"Revert failed. Try again."`. Revert confirmation remains open.

### E.5 Cross-Field Validation: Pre-Warning > Auto-Expire Conflict

**Trigger**: User sets `calendar_conflict_pre_warning_days` ≥ `calendar_conflict_auto_expire_days` (or equivalent QB fields).

**Client-side**: Immediate inline validation runs in `CalendarAutoExpirySettings` / `QbAutoExpirySyncPage` before the mutation fires. If pre_warning ≥ auto_expire: field border turns `border-fault-200`, error text: `"Pre-warning must be less than the auto-expire period."`. Save is blocked until the relationship is valid.

**Server-side**: Backend also validates; returns 422 if client bypasses. The 422 error message is surfaced as an `E.2`-style field error.

### E.6 Margin Bucket Monotonicity Validation

**Trigger**: `margin_bucket_boundaries` array fails monotonicity check (values not strictly ascending).

**Client-side**: Explicit Save button in `MarginBucketsPage` is disabled when the array is not monotonically ascending. Inline instruction below the array editor: `"Thresholds must be in ascending order."` with `text-fault-600`.

### E.7 Range Validation Failure

**Trigger**: Value outside `validation_rules.min`/`validation_rules.max` from catalog.

**Client-side**: `SettingControl` validates against `validationRules` before calling `onSave`. Inline error: `"Must be between [min] and [max]."` Save is blocked.

### E.8 409 Optimistic Conflict (Concurrent Edit)

**Trigger**: `expected_updated_at` staleness check fails — another session updated the same setting between the user's load and their save.

**User sees**: The field reverts to the latest server value. A `NotificationBanner severity="warning"`: `"This setting was updated by another session. Your change wasn't saved — review the current value and save again."` The current server value is shown.

### E.9 `require_approval_for_tech_quotes` Toggle-OFF with Pending Quotes

**Trigger**: `PUT /settings/require_approval_for_tech_quotes` with `value: false` returns `pending_quote_count > 0`.

**User sees**: Before the mutation fires, `FieldOperationsPage` shows an inline confirmation banner: `"N quotes are currently pending your approval. Disabling this won't auto-send them — they'll return to draft. [Cancel] [Disable anyway]"`. Cancel restores the toggle to ON. "Disable anyway" fires the mutation.

**Token**: `bg-alert-50 border-alert-200 text-alert-700`

---

## F — TypeScript Interfaces

### F.1 `SettingControlProps` (LOCKED for FE-B12)

```typescript
/**
 * <SettingControl> — Locked public API
 *
 * Location: packages/ui/src/setting-control/SettingControl.tsx
 *
 * ⚠️ INTERFACE LOCKED after FE-B11 ships.
 * FE-B12 may add OPTIONAL props via backward-compatible extension only.
 * Renaming or removing existing props requires multi-batch impact review.
 *
 * FE-B12 may extend with:
 *   - additionalHelpText: string (context-specific help for notification pref fields)
 *   - Any new props MUST be optional with sensible defaults
 */
export interface SettingControlProps<T = unknown> {
  /** The setting key (matches catalog key) — used for accessibility and test IDs */
  settingKey: string;

  /** Human-readable label rendered above the field */
  label: string;

  /** Optional 1-2 sentence description rendered below the label */
  description?: string;

  /** The current effective value to display */
  value: T;

  /** The system default value — displayed in State 1 annotation: "Default · {defaultValue} {unit}" */
  defaultValue: T;

  /**
   * The current scope of the effective value.
   * 'system' → State 1 (inheriting default; muted annotation)
   * 'tenant' | 'user' → State 2 (actively overridden; "Revert to default" link visible)
   * 'fallback' → treated same as 'system'
   */
  scope: 'system' | 'tenant' | 'user' | 'fallback';

  /**
   * The save behavior for this field.
   * 'blur' — save fires on field blur (or toggle change)
   * 'group' — this field is part of a save-on-group-complete group; caller manages save via useFormSaveStrategy
   * 'explicit' — save button; caller manages save via useFormSaveStrategy
   */
  saveMode: 'blur' | 'group' | 'explicit';

  /**
   * Called when the value should be saved (blur mode only).
   * For 'group' and 'explicit' modes, the caller manages saving via useFormSaveStrategy —
   * this callback is not used but must still be provided (can be a no-op).
   */
  onSave: (value: T) => Promise<void>;

  /** Called when the revert-to-default is confirmed. Caller fires DELETE mutation. */
  onRevert?: () => Promise<void>;

  /** When true, renders value display only — no edit affordance. Used for mobile read-only tenant settings. */
  readOnly?: boolean;

  /**
   * Input type — drives the rendered control.
   * 'integer' → numeric input; 'boolean' → toggle; 'string' → text input; 'select' → dropdown
   * Default: 'integer'
   */
  inputType?: 'integer' | 'boolean' | 'string' | 'select' | 'preset-select';

  /** Validation constraints passed from catalog */
  validationRules?: {
    min?: number;
    max?: number;
    allowedValues?: string[];
  };

  /** Options for 'select' and 'preset-select' input types */
  selectOptions?: Array<{ value: string; label: string; recommended?: boolean }>;

  /** Unit suffix rendered after the value (e.g. "days", "%") */
  unit?: string;

  /**
   * For State 3: show effective range helper text below the field.
   * e.g. "Effective: 30 days · Pre-warning at: 7 days"
   */
  effectiveRangeLabel?: string;

  /**
   * When readOnly=true on mobile: provenance annotation shown below value.
   * 'tenant' → "Set by your tenant"; 'system' → "Default value"
   */
  provenanceAnnotation?: 'tenant' | 'system';

  /** Test ID for e2e and unit tests */
  testID?: string;
}
```

---

### F.2 `EffectiveSettingDisplayProps` (LOCKED for FE-B12)

```typescript
/**
 * <EffectiveSettingDisplay> — Locked public API
 *
 * Location: packages/ui/src/setting-control/EffectiveSettingDisplay.tsx
 *
 * ⚠️ INTERFACE LOCKED after FE-B11 ships.
 * FE-B12 may add OPTIONAL props only (additive extension).
 */
export interface EffectiveSettingDisplayProps {
  /** The setting key (matches catalog key) */
  settingKey: string;

  /** Human-readable label */
  label: string;

  /** Optional description */
  description?: string;

  /** The three-tier resolution chain values */
  tiers: {
    system: { value: unknown; exists: boolean };
    tenant: { value: unknown; exists: boolean };
    user: { value: unknown; exists: boolean };
  };

  /**
   * The active tier (which layer is currently providing the effective value).
   * Determines which row gets the active-tier visual indicator.
   */
  activeTier: 'user' | 'tenant' | 'system' | 'fallback';

  /** Whether the current user can edit their own user-tier override */
  userCanEdit: boolean;

  /**
   * Whether the tenant allows per-user override for this setting.
   * When false: user tier row shows "Set by your tenant" annotation; edit affordance is hidden.
   */
  allowsUserOverride: boolean;

  /** Called when user saves their own override value */
  onSaveUserOverride?: (value: unknown) => Promise<void>;

  /** Called when user reverts their override to inherit tenant/system value */
  onRevertUserOverride?: () => Promise<void>;

  /**
   * Web mode: shows all three tiers + the per_user_override_allowed meta-toggle
   * Mobile mode: shows user tier + tenant tier summary; system tier hidden unless distinct
   * Default: derived from Platform.OS
   */
  displayMode?: 'web' | 'mobile';

  /** Input type for the user-tier edit affordance */
  inputType?: 'boolean' | 'select';

  /** Options for select inputType */
  selectOptions?: Array<{ value: string; label: string }>;

  /** Test ID */
  testID?: string;
}
```

---

### F.3 `UseFormSaveStrategyOptions` and `UseFormSaveStrategyReturn` (LOCKED for FE-B12)

```typescript
/**
 * useFormSaveStrategy — Locked public API
 *
 * Location: packages/ui/src/hooks/useFormSaveStrategy.ts
 *
 * ⚠️ INTERFACE LOCKED after FE-B11 ships.
 */

// ─── Blur mode ───────────────────────────────────────────────────────────────

export interface BlurSaveOptions<T = unknown> {
  mode: 'blur';
  /** Called when a field blurs with a new value */
  onSave: (key: string, value: T) => Promise<void>;
}

export interface BlurSaveReturn<T = unknown> {
  mode: 'blur';
  /** Returns { onBlur, onChange } handlers for the field */
  getFieldProps: (key: string, currentValue: T) => {
    onBlur: () => void;
    onChange: (value: T) => void;
  };
  savePending: boolean;
  lastError: string | null;
}

// ─── Group mode ──────────────────────────────────────────────────────────────

export interface GroupFieldDef {
  key: string;
  required: boolean;
}

export interface GroupSaveOptions<T = unknown> {
  mode: 'group';
  /** The fields that form this group */
  fields: GroupFieldDef[];
  /** Values at mount — used for rollback on navigation-away */
  initialValues: Record<string, T>;
  /** Called atomically when group is complete */
  onSave: (values: Record<string, T>) => Promise<void>;
  /** Called when navigation-away detected with incomplete group */
  onRollback: () => void;
}

export interface GroupSaveReturn<T = unknown> {
  mode: 'group';
  groupIsComplete: boolean;
  incompleteFields: string[];
  fieldValues: Record<string, T>;
  setFieldValue: (key: string, value: T) => void;
  savePending: boolean;
  savedAt: number | null;
  lastError: string | null;
}

// ─── Explicit mode ────────────────────────────────────────────────────────────

export interface ExplicitSaveOptions<T = unknown> {
  mode: 'explicit';
  initialValues: Record<string, T>;
  onSave: (values: Record<string, T>) => Promise<void>;
}

export interface ExplicitSaveReturn<T = unknown> {
  mode: 'explicit';
  isDirty: boolean;
  fieldValues: Record<string, T>;
  setFieldValue: (key: string, value: T) => void;
  handleSave: () => Promise<void>;
  handleDiscard: () => void;
  savePending: boolean;
  lastError: string | null;
}

// ─── Union ───────────────────────────────────────────────────────────────────

export type UseFormSaveStrategyOptions<T = unknown> =
  | BlurSaveOptions<T>
  | GroupSaveOptions<T>
  | ExplicitSaveOptions<T>;

export type UseFormSaveStrategyReturn<T = unknown> =
  | BlurSaveReturn<T>
  | GroupSaveReturn<T>
  | ExplicitSaveReturn<T>;
```

---

### F.4 `RevertToDefaultDialogProps` (LOCKED for FE-B12)

```typescript
/**
 * <RevertToDefaultDialog> — inline confirmation component
 *
 * Location: packages/ui/src/setting-control/RevertToDefaultDialog.tsx
 *
 * Renders inline within the SettingControl field area (not a floating modal).
 * ⚠️ INTERFACE LOCKED after FE-B11 ships.
 */
export interface RevertToDefaultDialogProps {
  /** The human-readable label of the setting being reverted */
  settingLabel: string;

  /** The current tenant override value (displayed as "from X") */
  currentValue: unknown;

  /** The system default value (displayed as "→ Y (system default)") */
  defaultValue: unknown;

  /** Unit suffix for display (e.g. "days") */
  unit?: string;

  /** Called when the owner confirms the revert */
  onConfirm: () => void;

  /** Called when the owner cancels the revert */
  onCancel: () => void;

  /** True while the revert DELETE mutation is in-flight */
  isReverting: boolean;

  /** Test ID */
  testID?: string;
}
```

---

### F.5 `SaveOnGroupCompleteIndicatorProps` (LOCKED for FE-B12)

```typescript
/**
 * <SaveOnGroupCompleteIndicator>
 *
 * Location: packages/ui/src/setting-control/SaveOnGroupCompleteIndicator.tsx
 *
 * ⚠️ INTERFACE LOCKED after FE-B11 ships.
 */
export interface SaveOnGroupCompleteIndicatorProps {
  /** From useFormSaveStrategy({ mode: 'group' }) return */
  groupIsComplete: boolean;
  incompleteFields: string[];

  /**
   * Timestamp of last successful group save.
   * When present and recent (< 2000ms), shows "Saved ✓" tick before fading.
   */
  savedAt: number | null;

  /** True when bulk write is in-flight — shows spinner */
  savePending: boolean;

  /** Group-level error message from failed bulk write */
  error: string | null;

  /** Prompt shown when group is incomplete, e.g. "Pick a direction to complete this setting." */
  incompletePrompt?: string;

  /** Test ID */
  testID?: string;
}
```

---

### F.6 `CatalogEntry` (typed from backend `CatalogEntryResponse`)

```typescript
/**
 * Frontend representation of CatalogEntryResponse from backend/api/routes/settings.py.
 * camelCase conversion from snake_case happens in useSettingsCatalog normalizer.
 */
export interface CatalogEntry {
  key: string;
  label: string;
  description: string;
  subSurfacePath: string;
  dataType: 'boolean' | 'integer' | 'decimal' | 'string' | 'array';
  validationRules: {
    min?: number;
    max?: number;
    allowedValues?: string[];
  };
  systemDefault: unknown;
  currentEffectiveValue: unknown;
  currentScope: 'user' | 'tenant' | 'system' | 'fallback';
  revertible: boolean;
  requiresRole: string | null;
  allowsUserOverride: boolean;
}
```

---

### F.7 `EffectiveSettingValue` (typed from backend `EffectiveSettingResponse`)

```typescript
/**
 * Frontend representation of EffectiveSettingResponse from backend/api/routes/settings.py.
 */
export interface EffectiveSettingValue {
  key: string;
  value: unknown;
  scope: 'user' | 'tenant' | 'system' | 'fallback';
  tenantOverrideExists: boolean;
  userOverrideExists: boolean;
  allowsUserOverride: boolean;
}
```

---

## G — Test Plan

### G.1 Unit Tests (target: 60+)

**`packages/ui/src/setting-control/`**

| Test | File |
|:---|:---|
| `SettingControl` renders State 1 (scope='system'): muted annotation "Default · {defaultValue}" visible | `SettingControl.test.tsx` |
| `SettingControl` renders State 1: "Revert to default" link is NOT visible | `SettingControl.test.tsx` |
| `SettingControl` renders State 2 (scope='tenant'): value shown without muted annotation | `SettingControl.test.tsx` |
| `SettingControl` renders State 2: "Revert to default" link IS visible | `SettingControl.test.tsx` |
| `SettingControl` State 1 → State 2 transition on first edit + save | `SettingControl.test.tsx` |
| `SettingControl` enters `editing` phase on field focus | `SettingControl.test.tsx` |
| `SettingControl` calls `onSave` with new value on blur (saveMode='blur') | `SettingControl.test.tsx` |
| `SettingControl` shows pending spinner during `save-pending` phase | `SettingControl.test.tsx` |
| `SettingControl` reverts to pre-edit value on `onSave` rejection (error phase) | `SettingControl.test.tsx` |
| `SettingControl` shows inline error text on save failure | `SettingControl.test.tsx` |
| `SettingControl` enters `revert-pending` phase when "Revert to default" clicked | `SettingControl.test.tsx` |
| `SettingControl` shows `<RevertToDefaultDialog>` with correct current + default values | `SettingControl.test.tsx` |
| `SettingControl` calls `onRevert` and transitions to State 1 on confirm | `SettingControl.test.tsx` |
| `SettingControl` returns to State 2 on cancel revert | `SettingControl.test.tsx` |
| `SettingControl readOnly=true` renders value without edit affordance | `SettingControl.test.tsx` |
| `SettingControl readOnly=true` shows provenance annotation "Set by your tenant" (scope='tenant') | `SettingControl.test.tsx` |
| `SettingControl readOnly=true` shows provenance annotation "Default value" (scope='system') | `SettingControl.test.tsx` |
| `SettingControl` renders effectiveRangeLabel helper text (State 3) | `SettingControl.test.tsx` |
| `SettingControl inputType='boolean'` renders toggle; toggle change calls `onSave` immediately | `SettingControl.test.tsx` |
| `SettingControl inputType='select'` renders dropdown with options | `SettingControl.test.tsx` |
| `SettingControl` enforces min/max validation; blocks save when out of range | `SettingControl.test.tsx` |
| `RevertToDefaultDialog` renders current value + default value + unit | `RevertToDefaultDialog.test.tsx` |
| `RevertToDefaultDialog` calls `onConfirm` when "Revert" button clicked | `RevertToDefaultDialog.test.tsx` |
| `RevertToDefaultDialog` calls `onCancel` when "Cancel" button clicked | `RevertToDefaultDialog.test.tsx` |
| `RevertToDefaultDialog` shows spinner when `isReverting=true` | `RevertToDefaultDialog.test.tsx` |
| `SaveOnGroupCompleteIndicator` shows incomplete-group state when `groupIsComplete=false` | `SaveOnGroupCompleteIndicator.test.tsx` |
| `SaveOnGroupCompleteIndicator` shows `incompletePrompt` text | `SaveOnGroupCompleteIndicator.test.tsx` |
| `SaveOnGroupCompleteIndicator` shows "Saved ✓" for 2s after `savedAt` set | `SaveOnGroupCompleteIndicator.test.tsx` |
| `SaveOnGroupCompleteIndicator` shows spinner when `savePending=true` | `SaveOnGroupCompleteIndicator.test.tsx` |
| `SaveOnGroupCompleteIndicator` shows error text when `error` non-null | `SaveOnGroupCompleteIndicator.test.tsx` |

**`packages/ui/src/hooks/useFormSaveStrategy`**

| Test | File |
|:---|:---|
| `useFormSaveStrategy({ mode: 'blur' })` calls `onSave` on field blur | `useFormSaveStrategy.test.ts` |
| `useFormSaveStrategy({ mode: 'blur' })` sets `savePending=true` during onSave | `useFormSaveStrategy.test.ts` |
| `useFormSaveStrategy({ mode: 'group' })` does NOT fire `onSave` when group incomplete | `useFormSaveStrategy.test.ts` |
| `useFormSaveStrategy({ mode: 'group' })` fires `onSave` with all values when all required fields set | `useFormSaveStrategy.test.ts` |
| `useFormSaveStrategy({ mode: 'group' })` `incompleteFields` lists unfilled required keys | `useFormSaveStrategy.test.ts` |
| `useFormSaveStrategy({ mode: 'group' })` calls `onRollback` on navigation-away with incomplete group | `useFormSaveStrategy.test.ts` |
| `useFormSaveStrategy({ mode: 'group' })` saves group atomically when toggle turned OFF (group completes with direction null) | `useFormSaveStrategy.test.ts` |
| `useFormSaveStrategy({ mode: 'explicit' })` `isDirty=false` when values match initialValues | `useFormSaveStrategy.test.ts` |
| `useFormSaveStrategy({ mode: 'explicit' })` `isDirty=true` after any field change | `useFormSaveStrategy.test.ts` |
| `useFormSaveStrategy({ mode: 'explicit' })` `handleDiscard` resets fieldValues to initialValues | `useFormSaveStrategy.test.ts` |

**`packages/ui/src/setting-control/EffectiveSettingDisplay`**

| Test | File |
|:---|:---|
| `EffectiveSettingDisplay` renders three scope rows (User, Tenant, System) in web mode | `EffectiveSettingDisplay.test.tsx` |
| `EffectiveSettingDisplay` active tier row has distinct visual treatment | `EffectiveSettingDisplay.test.tsx` |
| `EffectiveSettingDisplay` `userCanEdit=false` hides edit affordance | `EffectiveSettingDisplay.test.tsx` |
| `EffectiveSettingDisplay` `allowsUserOverride=false` shows "Set by your tenant" annotation | `EffectiveSettingDisplay.test.tsx` |
| `EffectiveSettingDisplay` calls `onSaveUserOverride` when user edits and saves own tier | `EffectiveSettingDisplay.test.tsx` |
| `EffectiveSettingDisplay` calls `onRevertUserOverride` on "Match tenant default" click | `EffectiveSettingDisplay.test.tsx` |
| `EffectiveSettingDisplay displayMode='mobile'` shows user tier + tenant tier; hides system tier when same as tenant | `EffectiveSettingDisplay.test.tsx` |

**`apps/web/src/features/settings/`**

| Test | File |
|:---|:---|
| `useSettingsCatalog` caches at `['settings-catalog']` key | `hooks/useSettingsCatalog.test.ts` |
| `useSettingsCatalog` normalizes snake_case → camelCase | `hooks/useSettingsCatalog.test.ts` |
| `useTenantSettingWrite` applies optimistic update before server response | `hooks/useTenantSettingWrite.test.ts` |
| `useTenantSettingWrite` rolls back optimistic update on error | `hooks/useTenantSettingWrite.test.ts` |
| `useTenantSettingWrite` invalidates `['settings-catalog']` on success | `hooks/useTenantSettingWrite.test.ts` |
| `useTenantSettingRevert` transitions catalog entry to scope='system' optimistically | `hooks/useTenantSettingRevert.test.ts` |
| `FieldOperationsPage` shows pending-quote confirmation before firing mutation when `pending_quote_count > 0` | `components/FieldOperationsPage.test.tsx` |
| `QbAutoExpirySyncPage` direction field surfaces as required when toggle enabled; hidden when disabled | `components/QbAutoExpirySyncPage.test.tsx` |
| `QbAutoExpirySyncPage` fires bulk write only when toggle+direction both set | `components/QbAutoExpirySyncPage.test.tsx` |
| `MarginBucketsPage` Save button disabled when boundary array is not monotonically ascending | `components/MarginBucketsPage.test.tsx` |

---

### G.2 Integration Tests (target: 14+)

**Location**: `apps/{web,mobile}/__tests__/batch_fe_b11/`

| Test | File |
|:---|:---|
| Full settings page flow: load catalog → render Operations > Margin buckets → edit G2 → save → catalog reflects new scope='tenant' | `settings-write-blur.integration.test.tsx` |
| Revert-to-default flow: State 2 → click "Revert" → inline confirmation → confirm → DELETE fires → field transitions to State 1 | `settings-revert.integration.test.tsx` |
| Save-on-group-complete: QB invoice toggle ON → direction not picked → no save fires; direction picked → bulk write fires | `settings-group-complete.integration.test.tsx` |
| Save-on-group-complete abandonment: toggle ON, navigate away before direction picked → rollback to toggle OFF | `settings-group-rollback.integration.test.tsx` |
| Explicit Save: margin bucket boundaries → add boundary → array becomes non-monotonic → Save disabled; reorder → Save enabled → submit | `settings-explicit-save.integration.test.tsx` |
| Cross-field validation: set pre_warning_days ≥ auto_expire_days → inline error blocks save | `settings-cross-field-validation.integration.test.tsx` |
| Optimistic UI: PUT fires → catalog immediately shows new value + pending indicator; on 200 → indicator clears | `settings-optimistic-ui.integration.test.tsx` |
| 409 concurrent-edit conflict: expected_updated_at mismatch → field reverts + warning banner | `settings-409-conflict.integration.test.tsx` |
| Mobile read-only: `SettingControl readOnly` renders value + provenance annotation; no edit affordance | `settings-mobile-readonly.integration.test.tsx` |
| Mobile editable per-user override: `background_sync_enabled` `EffectiveSettingDisplay` mobile mode shows user tier + tenant default + "Match tenant" link | `settings-mobile-user-override.integration.test.tsx` |
| Settings search: typing "margin" → synonym match → "Margin bucket thresholds" result with path shown | `settings-search.integration.test.tsx` |
| Role gating: user without `settings.tenant.write` role → Operations and Sync & Storage routes redirect to `/settings` | `settings-rbac.integration.test.tsx` |
| CalendarAutoExpirySettings migration: component now imports `<SettingControl>` from `@pilot/ui`; BaseSettingInput stub deleted | `calendar-auto-expiry-migration.integration.test.tsx` |
| Tenant write invalidates catalog: POST write → `useSettingsCatalog` refetch triggered → new scope shown | `settings-catalog-invalidation.integration.test.tsx` |

**MSW handlers required** (new file `apps/web/src/features/settings/mocks/settingsHandlers.ts`):
- `GET /api/v1/settings/catalog` — default (all 18 settings at scope=system); variant 'tenant-overrides' (5 settings at scope=tenant)
- `GET /api/v1/settings/{key}/effective` — by key; default and with `user_id` param
- `PUT /api/v1/settings/{key}` — success 200; variant '409-conflict'; variant 'pending-quotes' (key=require_approval_for_tech_quotes, pending_quote_count=3)
- `DELETE /api/v1/settings/{key}/tenant-override` — success 200; variant '404-no-override'
- `PUT /api/v1/settings/bulk` — success 200; variant 'validation-error-422'
- `PUT /api/v1/settings/{key}/user-override` — success 200; variant '403-no-override-allowed'
- `DELETE /api/v1/settings/{key}/user-override` — success 200; variant '404-no-override'

---

### G.3 E2E Tests (target: 3+)

**Location**: `e2e/web/batch_fe_b11/`

| Test | File |
|:---|:---|
| Full Tier 2 #4 modification cycle: load Settings > Operations > Profitability rules → edit `etc_variance_note_required_pct` from 10 to 15 → verify UI shows scope=tenant → revert → verify UI returns to scope=system with value 10 | `settings-full-cycle.e2e.spec.ts` |
| Tenant isolation: log in as Tenant A → modify `background_sync_battery_floor_pct` to 30 → log out → log in as Tenant B → verify still showing system default 20 | `settings-tenant-isolation.e2e.spec.ts` |
| Revert-to-default against dev backend: `calendar_conflict_auto_expire_days` set to 45 → revert → confirm backend returns scope=system → UI shows "Default · 30 days" | `settings-revert-e2e.e2e.spec.ts` |

---

## H — Token Audit

Every color, spacing, and typography value traces to a token from `packages/ui/src/tokens.ts`. No hex values or raw pixel values in component code.

### H.1 Color Tokens

| Usage | Tailwind class | Token | Notes |
|:---|:---|:---|:---|
| State 1 muted annotation text ("Default · 30 days") | `text-neutral-400` | `colors.neutral[400]` | Subtle; communicates "inherited, not active decision" |
| State 1 default marker glyph (↘) | `text-neutral-400` | `colors.neutral[400]` | Same muted treatment |
| State 2 "tenant override" pill background | `bg-brand-100` | `colors.brand[100]` | Subtle brand indigo — "actively configured" |
| State 2 "tenant override" pill text | `text-brand-700` | `colors.brand[700]` | — |
| "Revert to default" link text | `text-brand-600` | `colors.brand[600]` | Brand indigo; interactive affordance |
| "Revert to default" link hover | `text-brand-800` | `colors.brand[800]` | — |
| `RevertToDefaultDialog` inline panel background | `bg-neutral-50` | `lightTheme.background.primary` | Subtle inset panel |
| `RevertToDefaultDialog` border | `border-neutral-200` | `colors.neutral[200]` | — |
| [Revert] confirm button (destructive-adjacent) | `bg-brand-600 text-white hover:bg-brand-700` | `colors.brand[600]`, `colors.brand[700]` | Revert is not destructive per spec; brand primary |
| Save-on-group incomplete border tint | `border-alert-300` | `colors.alert[300]` | Amber — incomplete but not error |
| Save-on-group incomplete required label | `text-alert-600` | `colors.alert[600]` | "(required)" annotation on unfilled field |
| Save-on-group "Pick a direction" inline message | `text-alert-600` | `colors.alert[600]` | — |
| Save-on-group "Saved ✓" tick | `text-margin-600` | `colors.margin[600]` | Green success tick |
| Optimistic pending indicator (spinner / pulse) | `text-neutral-400` | `colors.neutral[400]` | Neutral pending — not alarming |
| Save success indicator (brief tick) | `text-margin-600` | `colors.margin[600]` | Green; same as other success states |
| Field error border | `border-fault-200` | `colors.fault[200]` | — |
| Field error text | `text-fault-600` | `colors.fault[600]` | — |
| Pending-quote confirmation background | `bg-alert-50 border-alert-200` | `colors.alert[50]`, `colors.alert[200]` | Amber; actionable warning |
| Pending-quote text | `text-alert-700` | `colors.alert[700]` | — |
| Settings sidebar active group highlight | `bg-brand-50 text-brand-700` | `colors.brand[50]`, `colors.brand[700]` | Active nav item |
| Settings sidebar inactive group | `text-neutral-700 hover:bg-neutral-100` | `colors.neutral[700]`, `colors.neutral[100]` | — |
| Mobile provenance annotation text | `text-neutral-500` | `colors.neutral[500]` | Slightly more visible than web muted; mobile small screen |
| Page background | `bg-neutral-50` | `lightTheme.background.primary` | — |
| Card / section background | `bg-white` | `lightTheme.background.secondary` | — |
| Subtle border | `border-neutral-200` | `colors.neutral[200]` | — |
| Page body text | `text-neutral-900` | `colors.neutral[900]` | — |
| Secondary text | `text-neutral-600` | `colors.neutral[600]` | — |
| Disabled / hint text | `text-neutral-400` | `colors.neutral[400]` | — |

### H.2 Spacing Tokens

| Usage | Class | Token |
|:---|:---|:---|
| SettingControl card padding | `p-4` | `spacing[4]` = 16px |
| SettingControl label-to-field gap | `space-y-1.5` | `spacing[1.5]` = 6px |
| Section vertical rhythm | `space-y-6` | `spacing[6]` = 24px |
| Sidebar item padding | `px-3 py-2` | `spacing[3]` / `spacing[2]` |
| RevertToDefaultDialog internal padding | `p-3` | `spacing[3]` = 12px |
| Group indicator row gap | `gap-2` | `spacing[2]` = 8px |
| Scope badge padding | `px-2 py-0.5` | `spacing[2]` / `spacing[0.5]` |

### H.3 Typography Tokens

| Usage | Class | Token |
|:---|:---|:---|
| Page heading | `text-h2 font-medium` | `fontSizes.h2`, `fontWeights.medium` |
| Settings group section heading | `text-h3 font-medium` | `fontSizes.h3`, `fontWeights.medium` |
| Field label | `text-body font-medium` | `fontSizes.body`, `fontWeights.medium` |
| Field description | `text-caption` | `fontSizes.caption` |
| State 1 annotation | `text-caption text-neutral-400` | `fontSizes.caption` |
| "Revert to default" link | `text-caption` | `fontSizes.caption` |
| Scope badge text | `text-caption font-medium` | `fontSizes.caption`, `fontWeights.medium` |
| Error text | `text-caption text-fault-600` | `fontSizes.caption` |
| Helper text / effective-range label | `text-caption text-neutral-600` | `fontSizes.caption` |

### H.4 Token Gaps Flagged

One potential gap noted from FE-B9: `margin-500` and `alert-500` were used in FE-B9 field-issues status dots. The token ramp in `tokens.ts` does not have `500` stops confirmed — FE-B9 implementation used `margin-400`/`alert-400` and `margin-600`/`alert-600` as substitutes. FE-B11 avoids `500` stops; uses `400` or `600` per existing pattern. One new entry above (`text-neutral-500` for mobile provenance annotation) uses `neutral[500]` — verify this ramp stop exists in `tokens.ts`. If not, substitute `neutral[600]`.

No other token gaps identified in FE-B11. All design values used in this batch trace to confirmed token ramp stops.

---

## I — Downstream Contract Lock

### I.1 Interfaces Locked by FE-B11 (Consumed by FE-B12)

FE-B12 imports all five shared components established by FE-B11. These interfaces are **locked** after FE-B11 ships. FE-B12 may only extend via backward-compatible optional props — never rename, never remove, never change existing prop semantics.

| Import | From | FE-B12 usage |
|:---|:---|:---|
| `SettingControl` | `packages/ui/src/setting-control/` | Every settings field in notification preferences (#5), voice persona (#6), account settings (#7) |
| `SettingControlProps` | same | FE-B12 instantiates with notification-preference field types |
| `EffectiveSettingDisplay` | `packages/ui/src/setting-control/` | Notification preference matrix cells (each cell = per-user override of tenant default) |
| `EffectiveSettingDisplayProps` | same | FE-B12 provides `inputType='select'` with channel options |
| `useFormSaveStrategy` | `packages/ui/src/hooks/useFormSaveStrategy.ts` | All FE-B12 settings pages use the hook for their save behavior |
| `UseFormSaveStrategyOptions` + `UseFormSaveStrategyReturn` | same | FE-B12 instantiates with `mode: 'blur'` for most fields |
| `RevertToDefaultDialog` | `packages/ui/src/setting-control/` | FE-B12 notification preference cells use revert-to-default to reset to tenant default |
| `RevertToDefaultDialogProps` | same | FE-B12 provides per-channel labels and default values |
| `SaveOnGroupCompleteIndicator` | `packages/ui/src/setting-control/` | FE-B12 MFA policy settings use save-on-group-complete (MFA enabled + grace period form) |
| `SaveOnGroupCompleteIndicatorProps` | same | FE-B12 provides group-specific `incompletePrompt` |

---

### I.2 Props That FE-B12 May Extend

FE-B12 may extend `SettingControlProps` with **additive optional props only**:

```typescript
// FE-B12 extensions (all MUST be optional with sensible defaults):
// These are illustrative — FE-B12 may add these at implementation time:
interface SettingControlProps<T = unknown> {
  // ... all FE-B11 locked props above ...

  // FE-B12 may add (examples only — additive, optional):
  /** Optional contextual help link (? icon → opens help article) — Tier 4 #14 territory */
  helpArticleUrl?: string;

  /** Additional helper text rendered below description — for notification pref context */
  additionalHelperText?: string;
}
```

FE-B12 may **not** add required props to any locked interface. Any required behavioral customization must be achieved via new optional props with defaults that preserve FE-B11 behavior.

---

### I.3 `packages/ui/src/index.ts` FE-B11 Export Block

The following exports are added to `packages/ui/src/index.ts` as a new `FE-B11 Exports` section immediately after the FE-B10 block:

```typescript
// ── FE-B11 Exports ─────────────────────────────────────────────────────────────
// Settings Foundation — system-default-with-tenant-override pattern (arch doc §16.5).
// Canonical visual treatment: SettingControl (Mockup A), EffectiveSettingDisplay (Mockup C)
// Save behavior: useFormSaveStrategy (Mockup B)
// ⚠️ All interfaces LOCKED after FE-B11 ships.
// FE-B12 may only add OPTIONAL additive props.

export { SettingControl } from './setting-control';
export type { SettingControlProps } from './setting-control';

export { EffectiveSettingDisplay } from './setting-control';
export type { EffectiveSettingDisplayProps } from './setting-control';

export { RevertToDefaultDialog } from './setting-control';
export type { RevertToDefaultDialogProps } from './setting-control';

export { SaveOnGroupCompleteIndicator } from './setting-control';
export type { SaveOnGroupCompleteIndicatorProps } from './setting-control';

export { SettingsSidebarSearch } from './setting-control';

export { useFormSaveStrategy } from './hooks/useFormSaveStrategy';
export type {
  UseFormSaveStrategyOptions,
  UseFormSaveStrategyReturn,
  BlurSaveOptions,
  BlurSaveReturn,
  GroupSaveOptions,
  GroupSaveReturn,
  GroupFieldDef,
  ExplicitSaveOptions,
  ExplicitSaveReturn,
} from './hooks/useFormSaveStrategy';

// Canonical settings domain types (frontend representation of backend Pydantic schemas)
export type { CatalogEntry, EffectiveSettingValue } from './setting-control/types';
```

---

### I.4 FE-B8 `CalendarAutoExpirySettings` Migration (FE-B11 Responsibility)

FE-B11 is responsible for migrating `CalendarAutoExpirySettings.tsx` from the local `BaseSettingInput` stub to `SettingControl` from `@pilot/ui`.

**Migration steps**:

1. **Delete** `apps/web/src/features/calendar-conflict/components/BaseSettingInput.tsx` — stub file no longer needed after migration.

2. **Update `CalendarAutoExpirySettings.tsx`** import:
   ```typescript
   // Before (FE-B8 stub):
   import { BaseSettingInput } from './BaseSettingInput';

   // After (FE-B11 real component):
   import { SettingControl } from '@pilot/ui';
   ```

3. **Adapt props** in `CalendarAutoExpirySettings`:
   - `label` → `label` (unchanged)
   - `value: number | null` → `value: number | null` (unchanged)
   - `onChange: (v) => void` → `onSave: async (v) => { await writeTenantSetting(key, v) }`
   - Add `settingKey` (e.g., `"calendar_conflict_auto_expire_days"`)
   - Add `scope={catalogEntry?.currentScope ?? 'system'}`
   - Add `defaultValue={catalogEntry?.systemDefault ?? 30}`
   - Add `saveMode="blur"`
   - `min`, `max` → `validationRules={{ min, max }}`
   - `suffix` → `unit`
   - Remove `error` prop (SettingControl manages its own error display)
   - `disabled` → `readOnly`

4. **Wire** `CalendarAutoExpirySettings` to `useSettingsCatalog` to source `scope`, `defaultValue`, `validationRules` dynamically from the catalog.

**Regression test**: a new test `apps/web/__tests__/batch_fe_b11/calendar-auto-expiry-migration.integration.test.tsx` verifies:
- The migrated component renders State 1 for scope=system and State 2 for scope=tenant
- Existing FE-B8 calendar conflict integration tests (`apps/web/__tests__/batch_fe_b8/`) pass without modification
- `BaseSettingInput` is not imported anywhere in the codebase after migration (confirmed by `grep` in CI)

---

### I.5 Settings Catalog Types — Locked for FE-B13 and FE-B16

**FE-B13 (onboarding)** surfaces a subset of settings inline during the tenant setup wizard. It imports:
- `CatalogEntry` (type) — to read settings metadata for onboarding-surfaced settings
- `useSettingsCatalog` hook — re-used from `apps/web/src/features/settings/hooks/`; not re-implemented
- `SettingControl` — onboarding wrapper renders settings fields using the same shared component

**FE-B16 (help system)** deep-links into settings pages using stable URL anchors (`/settings/{group}/{sub-page}#{settingKey}`). The `subSurfacePath` field on `CatalogEntry` provides the URL path; the setting key is the anchor ID. These URLs are what FE-B16 hard-codes in help article links — **they must not change after FE-B11 ships** without FE-B16 impact review. The `sub_surface_path` values in the backend `PlatformSettingCatalog` table are the source of truth; the frontend `CatalogEntry.subSurfacePath` (camelCase normalized) reflects them.

---

*This document is the complete handoff artifact for the Pilot React Engineer for FE-B11. All 7 design decisions are resolved. All TypeScript interfaces are complete with no placeholders or `any` types. All token references use exact token names from `tokens.ts`. The engineer can execute FE-B11 without returning for architectural decisions.*