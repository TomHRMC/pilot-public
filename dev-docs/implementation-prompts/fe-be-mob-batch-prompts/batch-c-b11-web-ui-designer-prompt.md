# UI Design Spec Prompt: C-B11 — Operator Cohort Dashboard

**Mode**: Pilot Web UI Designer
**Batch**: C-B11 (Part B prerequisite — UI design spec)
**Design doc**: `batch-c-b11-design.md` §H (Surface Mockup Reference)
**Output**: `dev-docs/architecture-design/batch-designs/batch-c-b11-ui-design-spec.md`
**Platform**: Web only (`apps/web`)
**Tom gate**: The React Engineer prompt for C-B11 Part B will NOT be authored until this spec is Tom-approved.

---

## Task

Author a UI design spec for the **Operator Cohort Dashboard** — a standalone page at `/operator/cohort` that shows all Charter members in a single table with tripwire alerts and two operator actions (silent extension + cohort close).

### Context

This is a **platform-level operator tool** (not tenant-scoped). It's the first operator-only page in the app. **Path A scope** (Tom decision 2026-08-06): standalone page with its own minimal layout — no tenant shell, no nav sidebar, no tenant impersonation. The platform shell + impersonation is deferred to C-B15.

### What the page shows

A single table with up to 12 rows (Charter cap). Each row is one Charter member:

| Column | Data |
|---|---|
| Member # / Business name | "Charter Member #1 — Acme Electric" |
| Days remaining | Days left in free period (countdown from 90) |
| Stripe status | `trialing` / `active` / `paused` |
| Payment method | Yes / No (card on file) |
| 10DLC status | `not_started` / `active` / etc. |
| Customers | Count |
| Invoices | Count |
| Days since last job | Integer or "Never" |
| Alert | Red / Amber / None (drives row styling) |

### Two visual alerts (color-independent — must use icon + text, not color alone)

1. **Red** — `days_since_last_job > 7` (or no jobs at all). The activation tripwire.
2. **Amber** — `free_period_ends_at` within 14 days. The extension window.
3. Red takes precedence over amber if both are true.

### Two operator actions

1. **Silent Extension** — per-row action. Opens a modal showing: current free-period end date, a date picker for the new end date, a required reason text field, and a confirmation button. This follows the **always-preview-before-send** pattern (§16.7) — the operator sees the new date + reason before confirming. No customer notification.

2. **Cohort Close** — top-level action (button in the header area). Opens a confirmation modal: "This will archive the Charter price and close the cohort to new signups. Existing members keep their locked rate. This cannot be undone." Two buttons: "Cancel" (default, safe action) and "Close Cohort" (destructive).

### API endpoints (already built in C-B11 Part A)

- `GET /api/v1/operator/cohort` → `CohortOverviewResponse` (cohort metadata + members array)
- `POST /api/v1/operator/cohort/{tenant_id}/extend` → `ExtendFreePeriodResponse`
- `POST /api/v1/operator/cohort/close` → `CloseCohortResponse`
- `GET /api/v1/auth/me` → `AuthMeResponse` (login routing — platform user redirects here)

### Design constraints

- **Token-only**: Use `pilotPreset` design tokens — zero hex codes
- **WCAG 2.2 AA**: color-independent status (icon + text for red/amber/none), ≥24×24px targets, `focus-visible` rings, `prefers-reduced-motion` fallbacks
- **Standalone layout**: No sidebar, no tenant shell. Simple header with "Pilot Operator — Charter Cohort" title + cohort close button. The table fills the main content area.
- **Empty state**: When no Charter members exist, show an empty state with "No Charter members yet. Members will appear here when they sign up."
- **Loading state**: Standard loading skeleton while fetching
- **Error state**: Standard error state with retry

### §16 pattern consumption

- **Always-preview-before-send** (§16.7) — extension modal shows new date + reason before confirm
- **Four-class severity** — alert_level drives row styling (red/amber/none)
- **Optimistic UI** (§16.6) — after extension, optimistically update the row's days_remaining

### Component manifest (from design doc §I)

| Component | Purpose |
|---|---|
| `CohortDashboardPage` | Thin route at `/operator/cohort` |
| `CohortDashboardClient` | Orchestrator — fetches data, renders table |
| `CohortMemberRow` | Single row with alert-level styling |
| `ExtendFreePeriodModal` | Date picker + reason + confirm (preview-before-send) |
| `CloseCohortButton` | Cohort close with confirmation modal |

### Read before designing

- `batch-c-b11-design.md` — full design doc (§D for API contracts, §H for surface reference, §I for component manifest)
- `mvp-arch.md` §16 — platform patterns (always-preview-before-send, four-class severity, optimistic UI)
- `.roo/rules-pilot-web-ui-designer/` — web UI designer rules (tokens, WCAG 2.2 AA, design-spec output format)
- `frontend/packages/ui/src/index.ts` — confirm existing shared components before proposing new ones

### Output format

Write the spec to `dev-docs/architecture-design/batch-designs/batch-c-b11-ui-design-spec.md` following the standard pilot-web-ui-designer output format. Include:

1. **Surface overview** — what the page is, who uses it, when
2. **Layout** — standalone page structure (header + table + modals)
3. **Table columns** — each column with data type, formatting, and width guidance
4. **Alert-level styling** — red/amber/none with icon + text + token references (color-independent)
5. **Extension modal** — date picker, reason field, preview-before-send layout, confirm/cancel
6. **Cohort close modal** — confirmation with destructive action styling
7. **Empty/loading/error states** — standard patterns
8. **Accessibility notes** — WCAG 2.2 AA compliance details
9. **Token manifest** — all `pilotPreset` tokens used (zero hex codes)
10. **Component manifest** — reconcile with design doc §I (no orphan components)

**STOP after producing the spec.** Implementation begins only on Tom's approval.
