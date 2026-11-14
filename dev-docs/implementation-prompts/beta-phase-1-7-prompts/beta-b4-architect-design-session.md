# Architect Design Session Prompt: BETA-B4 — Settings Missing Pages & Layout Fix

**Paste this entire prompt into a fresh Pilot Architect chat session.**

---

## Your Task

Produce the batch design document `dev-docs/architecture-design/batch-designs/batch-beta-v1-fixes-b4-design.md` for BETA-B4.

This is a Phase 1 Surface Design Session. No implementation happens here — the output is the design doc that the React Engineer will execute against.

**Design Principle**: This document is PRD-driven. The PRD defines what each settings surface must do. When the backend falls short, document the gap as a companion backend task — do not silently drop features from the design.

---

## Background: What BETA-B4 Fixes

During beta testing, clicking the following Settings sidebar items produces a Next.js 404 because no `page.tsx` file exists at that route. These are the pages to build:

| Sidebar Item | Missing Route | MVP Priority |
|---|---|---|
| Integrations > General | `/settings/integrations/general` | P1 |
| Integrations > QuickBooks (index) | `/settings/integrations/quickbooks` | P1 |
| My Account > Security (index) | `/settings/my-account/security` | P1 |
| Notifications > Email | `/settings/notifications/email` | P1 |
| Notifications > SMS | `/settings/notifications/sms` | P1 |
| Notifications > In-app | `/settings/notifications/in-app` | P1 |
| Branding | `/settings/branding` | P2 |
| Team | `/settings/team` | P1 |
| Billing | `/settings/billing` | P1 |
| Security & MFA | `/settings/security` | P1 |
| Data & Privacy | `/settings/data-privacy` | P2 |

Additionally, the Settings double-sidebar layout (main `<AppSidebar>` + `<SettingsSidebar>`) has a visual rendering issue that was partially fixed but may still need a layout pass.

Source issue: `dev-docs/testing-support/fe-ui-testing-open-issues-v1.md` §2.4b and §2.7  
Source plan: `dev-docs/analysis/pilot-app-beta-fixes-v1-impl-plan.md` §8 BETA-B4

---

## Phase 1: Required Reads (Complete ALL Before Writing the Design Doc)

### Step 1: Read the PRD for the relevant settings domains

Read `dev-docs/product-requirements/mvp-prd.md` — focus on these sections:
- §3.5 Identity, Access & Tenant Management (Team management, MFA policy, RBAC)
- §3.7 Notifications & Communications (notification preferences)
- §3.9 QuickBooks Integration (QB connection management)
- §3.11 Subscriptions & Usage (Billing, plan management)
- Any section referencing branding, data privacy, or data export

For each of the 11 missing pages, identify: what does the PRD say this surface must do? This drives the minimum viable content.

### Step 2: Read the existing Settings infrastructure

These files define the Settings shell that all new pages compose within:

```
frontend/apps/web/src/features/settings/components/SettingsShell.tsx
frontend/apps/web/src/features/settings/components/SettingsSidebar.tsx
frontend/apps/web/src/app/(authed)/settings/
```

For the directory listing, use:
```bash
find frontend/apps/web/src/app/(authed)/settings/ -name "page.tsx" | sort
```

This shows every existing settings page. Cross-reference against the 11 missing routes to confirm which ones truly don't exist.

### Step 3: Read existing completed settings pages as pattern references

These settings pages were built in FE-B11/B12 and are complete. Read at least 3 as pattern references:

```
frontend/apps/web/src/app/(authed)/settings/my-account/profile/page.tsx
frontend/apps/web/src/app/(authed)/settings/notifications/preferences/page.tsx
frontend/apps/web/src/app/(authed)/settings/integrations/quickbooks/auto-expiry/page.tsx
```

Read the feature components they import too. Understand the pattern: route imports feature component; feature component uses `<SettingControl>` or `<EffectiveSettingDisplay>` from `@pilot/ui`.

### Step 4: Read the shared settings components catalog

```
frontend/packages/ui/src/setting-control/
frontend/packages/ui/src/index.ts  (search for SettingControl, EffectiveSettingDisplay, RevertToDefaultDialog)
```

Understand: what shared components are available for settings pages? These must be reused rather than recreated.

### Step 5: Verify API endpoints from `backend/openapi_schema_map.md`

For each missing page, identify what backend endpoints it needs. Check `backend/openapi_schema_map.md` for:

1. **Team management** — endpoints for listing users, inviting users, changing roles, deactivating users
2. **Billing/Subscription** — endpoints for subscription tier, payment methods, invoice history
3. **MFA policy** (tenant-level) — endpoint for tenant MFA required policy setting
4. **QB connection status** — endpoint showing QB OAuth connection state and last sync
5. **Notification preferences (email/SMS/in-app channels)** — endpoints for per-channel notification settings
6. **Branding** — endpoint for tenant email branding (logo, colors) — may already exist from FE-B14
7. **Data & Privacy** — endpoints for data export request, data retention settings
8. **Integrations General** — any endpoint showing integration connection status overview

For each endpoint: if it exists, document the path and params. If it does NOT exist in `openapi_schema_map.md`, document it as a backend gap and a companion task.

### Step 6: Read the Settings layout for the visual issue

```
frontend/apps/web/src/features/settings/components/SettingsShell.tsx
frontend/apps/web/src/app/(authed)/settings/layout.tsx  (if it exists)
```

Assess the current layout behavior: does the double-sidebar look right? What specific CSS/layout problem exists? The issue description says `<SettingsShell>` was patched from `min-h-screen` to `h-full min-h-0 flex-1` — verify whether this is still the current state and whether the visual issue is resolved or still present.

### Step 7: Read the permissions registry

```
frontend/packages/ui/src/role-gate/permissions.ts
```

For each missing settings page, identify: which roles can access it? Does a relevant permission key exist? Note: BETA-B3 added `customers.view`, `quotes.view`, `invoices.view` — verify the current state of the file.

---

## Phase 2: Design Decisions to Make and Document

After completing all reads, make and document these decisions:

### Decision 1: Minimum Viable Content Per Page

For each of the 11 missing routes, determine the minimum content that makes it "not a 404" and useful for beta testing. Options:

- **Full functional page** — real data from backend, all PRD features
- **Partial page** — real data where backend exists, `<EmptyState>` or placeholder where gaps exist
- **Informational landing page** — no interactive data, just heading + description + link to sub-pages
- **Redirect** — if this route should just send to a sub-page that already exists

Prioritize by: which pages are directly blocking owner beta testing? Those are P1 full implementations. Pages with no backend support may be P2 informational.

### Decision 2: Settings Layout Fix

Determine if the double-sidebar layout issue is:
- Already fixed (patch applied, visually correct)
- Still broken (needs a proper layout fix)
- Partially fixed (works but could be better)

If still broken: specify the exact CSS/layout change needed. If a top tab bar is the right answer for the settings secondary nav, specify the component structure.

### Decision 3: Team Page — Scope

The Team page is one of the highest-priority settings surfaces (owners need to invite team members, set roles, deactivate users). Determine:
- What backend endpoints exist for user management?
- What's the minimum viable Team page for beta? (List existing users with their roles? Invite button that shows the email? Role change?)
- Does a complete team management page require backend work not yet done?

### Decision 4: Billing Page — Scope

Billing is always high risk. Determine:
- Does the backend have a subscription status endpoint?
- Is Stripe in test mode or not yet connected?
- For beta, is a "show current plan + placeholder for payment method" sufficient?
- What's achievable without a Stripe integration being live?

### Decision 5: Branding — Redirect or New Page?

FE-B14 built `/settings/communications/email-branding`. The sidebar has a "Branding" item at `/settings/branding`. Determine:
- Does `/settings/communications/email-branding` exist with real content?
- If yes: should `/settings/branding` be a redirect to it?
- If no: what's the minimum branding page?

---

## Phase 3: Write the Design Document

**Output file**: `dev-docs/architecture-design/batch-designs/batch-beta-v1-fixes-b4-design.md`

The design doc MUST contain sections A through I per the standard batch design format:

### A. Input Read Summary

Table of all artifacts read, locations, and key findings. Include what each endpoint check revealed (exists/missing).

### B. Execution Order

List all pages in implementation order. Group: layout fix first (if needed), then P1 pages in dependency order, then P2 pages.

### C. New Routes

For each of the 11 routes:
- File path
- Auth requirement
- RBAC gate (exact permission key, or "all authenticated" if no gate needed)
- Content type: functional / informational / redirect

### D. API Endpoint Consumption

For each page with backend data:
- Endpoint path (verified from `openapi_schema_map.md`)
- Hook name (existing hook to reuse, or new hook to create)
- MSW handler needed? (yes if backend gap; no if stable)
- Any companion backend tasks

### E. Pattern Reuse Decisions

Which shared settings components are used per page:
- `<SettingControl>` for toggle/select settings
- `<EffectiveSettingDisplay>` for three-tier display (user/tenant/system)
- `<RevertToDefaultDialog>` for revert actions
- `<EmptyState>` for pages with no data yet

### F. Shared Module Interfaces

If any new hooks are needed, specify full TypeScript interfaces. If existing hooks are reused, confirm import paths.

### G. Open Questions Resolved

Every ambiguity answered before handoff. No "TBD" items.

### H. External Dependency Status

For each page: what backend/external dependencies does it have? Is Stripe connected? Is QB connection needed? Are notification preference endpoints stable?

### I. Test Plan

Per page:
- Unit test file
- Integration test file (in `apps/web/__tests__/batch_beta_v1_b4/`)
- Coverage: at minimum, page renders (not 404), correct RBAC, primary content

---

## Design Doc Quality Gates

Before finalizing:

- [ ] Every page confirmed as genuinely missing (not already at a different route) via `find` command
- [ ] PRD requirements for each page documented — no pages designed "from memory"
- [ ] Every API endpoint verified from `openapi_schema_map.md` — no invented paths
- [ ] Backend gaps for any page explicitly called out as companion tasks (not silently dropped)
- [ ] Layout fix decision documented with specific CSS/component change if needed
- [ ] Branding page decision (redirect vs new) documented with rationale
- [ ] Team and Billing pages have realistic scope given backend readiness
- [ ] No permission keys invented — all from actual `permissions.ts`
- [ ] Every page has a clear minimum viable content decision (full / partial / informational / redirect)

---

## Output

The completed design doc at:  
**`dev-docs/architecture-design/batch-designs/batch-beta-v1-fixes-b4-design.md`**

Once complete and reviewed by Tom, it becomes the input for the BETA-B4 React Engineer (and Python Engineer if backend companion tasks are identified) implementation prompts.
