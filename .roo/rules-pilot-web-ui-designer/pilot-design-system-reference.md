# 🎨 Pilot Design System Reference — Web App

> **Design-time agent rule** — written to steer the AI agents during the build and published as last used. Where it differs from the as-built system, [`PROVENANCE.md`](../../PROVENANCE.md) and [`dev-docs/diligence/`](../../dev-docs/diligence/README.md) are correct.

**Purpose**: Quick reference for the Pilot Web UI Designer mode. Use this alongside `web-app-design-standards.md`.

---

## 1. Brand Assets

Logo files live in both the marketing app and must be copied to `apps/web/public/brand/` for web app use:

| File | Use case |
|---|---|
| `logo-primary.jpg` / `.svg` | Full wordmark — expanded sidebar, email headers |
| `logo-icon.jpg` / `.svg` | Icon mark only (P symbol) — collapsed sidebar, favicon variants |
| `logo-wordmark.jpg` / `.svg` | Wordmark without icon — narrow contexts |
| `logo-primary-dark.jpg` / `.svg` | Dark backgrounds |

**Source location**: `frontend/apps/marketing/public/brand/`  
**Web app location**: `frontend/apps/web/public/brand/` (copy on implementation)

---

## 2. Shared Component Library (`@pilot/ui`)

Before designing a new component, check if it already exists in `packages/ui/src/index.ts`:

| Component | Import | Use for |
|---|---|---|
| `NotificationPreferenceMatrix` | `@pilot/ui` | 3-column notification toggle grid |
| `LoadingState` | `@pilot/ui/states` | Spinner + label during data fetch |
| `ErrorState` | `@pilot/ui/states` | Error message with retry option |
| `EmptyState` | `@pilot/ui/states` | Zero-data state with CTA |
| `RoleGate` | `@pilot/ui/role-gate` | RBAC visibility wrapper |
| `InFlightSyncIndicator` | `@pilot/ui` | Offline sync status |
| `NotificationBanner` | `@pilot/ui` | Top-of-page banners (success, error, warning) |
| `MFAEnrollmentWizard` | `@pilot/ui` | MFA setup flow |

---

## 3. Status Badge Colors (App Domain)

These are the canonical badge colors for entity status codes. Use these exact token combinations:

**Job status:**
| Code | Token classes |
|---|---|
| `draft` | `bg-neutral-100 text-neutral-700` |
| `scheduled` | `bg-blue-100 text-blue-700` |
| `in_progress` | `bg-alert-100 text-alert-700` |
| `completed` | `bg-margin-100 text-margin-700` |
| `cancelled` | `bg-fault-100 text-fault-500` |

**Invoice status:**
| Code | Token classes |
|---|---|
| `draft` | `bg-neutral-100 text-neutral-700` |
| `issued` (Sent) | `bg-brand-100 text-brand-700` |
| `partial` | `bg-alert-100 text-alert-700` |
| `paid` | `bg-margin-100 text-margin-700` |
| `void` | `bg-neutral-100 text-neutral-500` |
| `writeoff` | `bg-fault-100 text-fault-500` |

**Quote status:**
| Code | Display label | Token classes |
|---|---|---|
| `draft` | Draft | `bg-neutral-100 text-neutral-700` |
| `pending_approval` | Pending Approval | `bg-alert-100 text-alert-700` |
| `approved` | Approved | `bg-blue-100 text-blue-700` |
| `sent` | Sent | `bg-brand-100 text-brand-700` |
| `accepted` | Accepted | `bg-margin-100 text-margin-700` |
| `rejected` | Rejected | `bg-fault-100 text-fault-600` |
| `expired` | Expired | `bg-neutral-100 text-neutral-500` |
| `converted` | Converted | `bg-margin-100 text-margin-800` |

> **Critical**: Never design an "overdue" status badge for invoices — "overdue" is a derived display state computed from `due_at < today`, not a DB status code. Use the `issued` badge with an aging bucket overlay for overdue invoices.

---

## 4. Navigation Architecture

**Authenticated shell layout** (`AuthedLayout`):
```
┌─────────────────────────────────────────┐
│ HEADER (h-12, bg-white, border-b)       │
│ [Logo]              [Bell] [⚙] [Avatar] │
├──────────┬──────────────────────────────┤
│ SIDEBAR  │ CONTENT AREA                 │
│ (256px)  │ (flex-1, overflow-auto)      │
│          │                              │
│ Nav list │ Page component renders here  │
│          │                              │
└──────────┴──────────────────────────────┘
```

**Settings shell layout** (`SettingsShell`):
```
┌─────────────────────────────────────────┐
│ HEADER (same as above)                  │
├──────────┬────────────────────────────  │
│ APP      │ SETTINGS    │ SETTINGS       │
│ SIDEBAR  │ SIDEBAR     │ CONTENT        │
│ (256px)  │ (224px)     │ (flex-1)       │
│          │ SettingsSB  │ Page content   │
└──────────┴─────────────┴────────────────┘
```

---

## 5. Form Design Patterns

Standard form layout for Settings pages:

* `max-w-2xl` container for single-column forms
* Label above input (`text-sm font-medium text-neutral-700 mb-1`)
* Input: `rounded-md border border-neutral-300 px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500`
* Helper text below: `text-xs text-neutral-500 mt-1`
* Error text below: `text-xs text-fault-600 mt-1`
* Submit button: `bg-brand-600 text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-brand-700`
* Cancel/secondary: `border border-neutral-300 text-neutral-700 rounded-md px-4 py-2 text-sm font-medium hover:bg-neutral-50`

---

## 6. Table / List Page Patterns

Standard table layout (from `PilotTable`):
* Table header: `bg-neutral-50 border-b border-neutral-200 text-sm font-medium text-neutral-700`
* Table row: `border-b border-neutral-100 hover:bg-neutral-50`
* Table cell: `px-4 py-3 text-sm text-neutral-900`
* Filter bar above table: search inputs + status dropdown + date range + Search/Clear buttons
* Pagination: `<PilotPaginator>` below table

---

## 7. Modal Patterns

* Overlay: `fixed inset-0 bg-neutral-900/50 z-50`
* Modal panel: `bg-white rounded-lg shadow-xl max-w-md w-full mx-auto mt-16 p-6`
* Close button: top-right `XMarkIcon` (Heroicons)
* Destructive confirm modal: `bg-fault-600 text-white` for the confirm button; `border border-neutral-300` for cancel
* z-index: modals at `z-50`, dropdowns at `z-40`, sidebar at `z-30`, header at `z-30`

---

## 8. RBAC Visibility Rules for Design

When designing a surface, note which roles see it:

| Permission | Roles |
|---|---|
| `settings.tenant.write` | owner, operator |
| `users.manage` | owner |
| `invoices.view` | owner, office_staff, operator |
| `reports.view` | owner, office_staff, operator |
| `catalog.view` | all authenticated roles |
| `schedule.manage` | owner, office_staff, operator |

Tech role (`tech`) sees: Jobs, Schedule, Comms, Catalog only — no financial data, no settings.

Always note in your design spec which `<RoleGate permission="...">` wraps a surface or action button.
