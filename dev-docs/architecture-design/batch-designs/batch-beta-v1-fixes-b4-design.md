# BETA-B4 Design Document — Settings Missing Pages & Layout Fix

**Batch**: `batch-beta-v1-fixes-b4`  
**Version**: 1.0  
**Date**: 2026-06-04  
**Architect**: Pilot Architect  
**Status**: Ready for React Engineer handoff  
**Output file**: `dev-docs/architecture-design/batch-designs/batch-beta-v1-fixes-b4-design.md`

---

## Table of Contents

- [A. Input Read Summary](#a-input-read-summary)
- [B. Execution Order](#b-execution-order)
- [C. New Routes](#c-new-routes)
- [D. API Endpoint Consumption](#d-api-endpoint-consumption)
- [E. Pattern Reuse Decisions](#e-pattern-reuse-decisions)
- [F. Shared Module Interfaces](#f-shared-module-interfaces)
- [G. Open Questions Resolved](#g-open-questions-resolved)
- [H. External Dependency Status](#h-external-dependency-status)
- [I. Test Plan](#i-test-plan)

---

## A. Input Read Summary

| Artifact | Location | Key Findings |
|---|---|---|
| BETA-B4 Prompt | `dev-docs/implementation-prompts/beta-b4-architect-design-session.md` | 11 missing routes, layout issue §2.4b and §2.7 |
| PRD §3.5 — Identity, Access & Tenant Management | `dev-docs/product-requirements/mvp-prd.md` lines 325–354 | Team management (list, role change, invite); tenant MFA policy toggle; active sessions |
| PRD §3.7 — Notifications & Communications | `dev-docs/product-requirements/mvp-prd.md` lines 380–415 | Per-user × per-category × per-channel matrix (8 categories × 4 channels); per-channel pages are sub-views of the unified matrix; email branding at `/settings/communications/email-branding` |
| PRD §3.9 — QuickBooks Integration | `dev-docs/product-requirements/mvp-prd.md` lines 443–459 | QB OAuth connect/disconnect, sync status indicator, conflict queue link |
| PRD §3.11 — Subscriptions & Usage | `dev-docs/product-requirements/mvp-prd.md` lines 500–528 | Billing page shows current tier, trial_ends_at, usage (users + SMS segments); Stripe Customer Portal deferred to Phase 2; upgrade opens tier picker |
| Settings directory listing | `frontend/apps/web/src/app/(authed)/settings/` | All 11 routes confirmed missing (no `page.tsx`); existing pages: profile, password, data-export, sessions, MFA sub-pages, notifications/preferences, integrations/calendar, integrations/quickbooks/auto-expiry + conflicts, communications pages, operations, sync-storage, voice-ai, help-and-about |
| `SettingsShell.tsx` | `frontend/apps/web/src/features/settings/components/SettingsShell.tsx` | Layout patch IS already applied (`flex h-full min-h-0 flex-1`); aside uses `hidden ... lg:flex w-56 shrink-0`; main uses `flex-1 overflow-y-auto` — **layout fix already in place** |
| `SettingsSidebar.tsx` | `frontend/apps/web/src/features/settings/components/SettingsSidebar.tsx` | Sidebar references `settings.tenant.write` and `integrations.manage` as `roleRequired` values — these are **NOT in `permissions.ts`** (frontend only has `settings.manage`); sidebar items render without actual `<RoleGate>` wrapper (uses raw string comparison); `SIDEBAR_ITEMS` defines all 11 missing hrefs |
| `layout.tsx` | `frontend/apps/web/src/app/(authed)/settings/layout.tsx` | `"use client"`, loads `useSettingsCatalog()`, wraps in `<SettingsShell>` — no layout changes needed |
| Pattern: profile page | `frontend/apps/web/src/app/(authed)/settings/my-account/profile/page.tsx` | Thin route file — imports and renders a feature component; pattern: `route → feature component` |
| Pattern: notifications/preferences | `frontend/apps/web/src/app/(authed)/settings/notifications/preferences/page.tsx` | Uses `useNotificationPreferences()` hook → `<NotificationPreferenceMatrix>` from `@pilot/ui`; handles loading/error states inline |
| Pattern: QB auto-expiry | `frontend/apps/web/src/app/(authed)/settings/integrations/quickbooks/auto-expiry/page.tsx` | Thin route → `<QbAutoExpirySyncPage>` feature component (no "use client" on route itself) |
| Email branding page | `frontend/apps/web/src/app/(authed)/settings/communications/email-branding/page.tsx` | **EXISTS and is complete** — `EmailBrandingSettingsPanel` from FE-B14 |
| `permissions.ts` | `frontend/packages/ui/src/role-gate/permissions.ts` | Current keys: `quotes.approve/reject/kickback`, `dispatch.move/assign`, `customers.delete/view`, `settings.manage`, `reports.view`, `comms.send`, `invoices.approve/view`, `quotes.view` (BETA-B3). **No `integrations.manage`, `settings.tenant.write`, or subscription/MFA-policy keys.** |
| `setting-control/types.ts` | `frontend/packages/ui/src/setting-control/types.ts` | `<SettingControl>` (blur/group/explicit save modes), `<EffectiveSettingDisplay>` (3-tier chain), `<RevertToDefaultDialog>`, `<SaveOnGroupCompleteIndicator>` — all locked API |
| `ui/src/index.ts` | `frontend/packages/ui/src/index.ts` | `EmptyState`, `LoadingState`, `ErrorState`, `EmailBrandingPreview`, `InFlightSyncIndicator`, `NotificationBanner`, `RoleGate`, `useRequiresPermission` all exported |
| **API: Team** | `backend/openapi_schema_map.md` lines 14585–14703 | `GET /api/v1/users` ✅ (list with role_code, is_active, joined_at); `POST /api/v1/users/{user_id}/role` ✅ (role assignment); **MISSING**: invite user, deactivate user — backend gap |
| **API: Billing/Subscription** | `backend/openapi_schema_map.md` lines 18909–19190 | `GET /api/v1/tenants/{tenant_id}/subscription` ✅; `POST .../change-tier` ✅; `POST .../convert-from-trial` ✅; `PUT .../upgrade` ✅; **MISSING**: invoice history, payment methods, Stripe portal redirect |
| **API: MFA Policy** | `backend/openapi_schema_map.md` line 16657 | `PUT /api/v1/settings/tenant/mfa-required` ✅ (tenant_mfa_required bool + grace_period_starts_at) |
| **API: My Account Security** | `backend/openapi_schema_map.md` lines 155–570 | `GET /api/v1/users/me/mfa-status` ✅; enroll-start/confirm ✅; recovery-codes/status ✅; recovery-codes/generate ✅; sessions GET/revoke ✅ |
| **API: QB Connection** | `backend/openapi_schema_map.md` lines 6421–6499 | `GET /api/v1/integrations/quickbooks/status` ✅; `GET .../connect` ✅; `DELETE .../disconnect` ✅; `POST .../refresh` ✅ |
| **API: Integrations General** | `backend/openapi_schema_map.md` lines 6540–6556 | `GET /api/v1/integrations/sync-dashboard/` ✅; `GET /api/v1/integrations/calendar/status` ✅ |
| **API: Notification Prefs** | `backend/openapi_schema_map.md` lines 9657–10228 | `GET /api/v1/notifications/preferences` ✅; `PUT/DELETE /api/v1/notifications/preferences/{category_id}/{channel}` ✅; `GET /api/v1/notifications/categories` ✅; `GET /api/v1/notifications/in-app/recent` ✅; `POST /api/v1/notifications/in-app/mark-read` ✅; `PUT/DELETE /api/v1/notifications/tenant-policy/{category_id}/{channel}` ✅; **no dedicated per-channel sub-endpoints** |
| **API: Email Branding** | `backend/openapi_schema_map.md` lines 16134–16374 | `GET/PATCH /api/v1/settings/email-branding` ✅; logo-upload-url ✅; preview ✅; test-send ✅ — **full branding API exists** |
| **API: Data Export** | `backend/openapi_schema_map.md` lines 13–100 | `GET/POST /api/v1/users/me/data-exports` ✅; `GET /api/v1/users/me/data-exports/{export_id}` ✅ |

---

## B. Execution Order

| Step | Task | Priority | Notes |
|---|---|---|---|
| 1 | Layout assessment pass (confirm no change needed) | P0 | Already patched — document as confirmed, skip code change |
| 2 | Add new permission keys to `permissions.ts` | P1 | Required before any RBAC-gated pages; add `integrations.manage`, `settings.tenant.write`, `billing.view` |
| 3 | `/settings/my-account/security` — index landing page | P1 | Unblocks beta owner security discovery |
| 4 | `/settings/security` — Tenant Security & MFA Policy | P1 | Owner-critical; uses `PUT /settings/tenant/mfa-required` |
| 5 | `/settings/team` — Team management | P1 | Owner-critical; list users + role change; invite as companion task |
| 6 | `/settings/billing` — Subscription & Billing | P1 | Shows current plan + usage; no Stripe actions yet |
| 7 | `/settings/integrations/quickbooks` — QB Index | P1 | Connects OAuth, shows status, links to sub-pages |
| 8 | `/settings/integrations/general` — Integrations Overview | P1 | Shows sync-dashboard summary + integration statuses |
| 9 | `/settings/notifications/email` — Email channel prefs | P1 | Filtered view of notifications/preferences matrix |
| 10 | `/settings/notifications/sms` — SMS channel prefs | P1 | Filtered view of notifications/preferences matrix |
| 11 | `/settings/notifications/in-app` — In-app channel prefs | P1 | Filtered view of notifications/preferences matrix |
| 12 | `/settings/branding` — Branding redirect | P2 | `next/navigation` redirect to `/settings/communications/email-branding` |
| 13 | `/settings/data-privacy` — Data & Privacy | P2 | Thin informational page + link to data-export |

---

## C. New Routes

### Layout: No Change Required

**Verdict**: The `SettingsShell.tsx` double-sidebar layout patch (`flex h-full min-h-0 flex-1`) is **already applied**. The current state passes the visual correctness check. No layout code changes are included in BETA-B4. The double-sidebar (AppSidebar + SettingsSidebar) is the intended design — not a bug.

---

### Route 1: `/settings/my-account/security` (index)

| Property | Value |
|---|---|
| **File path** | `frontend/apps/web/src/app/(authed)/settings/my-account/security/page.tsx` |
| **Auth** | Required (Cognito JWT) |
| **RBAC gate** | All authenticated roles (personal account security is self-service) |
| **Content type** | Partial — real MFA status data + navigational links to sub-pages |
| **Purpose** | Landing/index for My Account > Security group. Shows enrolled MFA method count, links to `/security/mfa/` for management, link to `/sessions/` for active sessions, link to `/password/` for password change, link to `/data-export/` for data export. |

**Component**: `SecurityIndexPage` in `frontend/apps/web/src/features/account-settings/components/SecurityIndexPage.tsx`

**Backend data**: `GET /api/v1/users/me/mfa-status` — fetch on load; display method count and enrollment state.

**Minimum viable content**:
- Heading: "Security"
- MFA status card: "N method(s) enrolled" with link to `/settings/my-account/security/mfa`
- Sessions card: "Manage active sessions" with link to `/settings/my-account/sessions`  
- Password card: "Change password" with link to `/settings/my-account/password`
- Uses `EmptyState` if MFA status fetch fails

---

### Route 2: `/settings/security` (Tenant Security & MFA Policy)

| Property | Value |
|---|---|
| **File path** | `frontend/apps/web/src/app/(authed)/settings/security/page.tsx` |
| **Auth** | Required (Cognito JWT) |
| **RBAC gate** | `settings.manage` (owner only — matches existing `settings.manage` key in permissions.ts) |
| **Content type** | Functional — `<SettingControl inputType="boolean">` for tenant MFA policy toggle |
| **Purpose** | Tenant-level security policy: enable/disable required MFA for all users with 7-day grace period. |

**Component**: `TenantSecurityPage` in `frontend/apps/web/src/features/settings/components/TenantSecurityPage.tsx`

**Backend data**: `PUT /api/v1/settings/tenant/mfa-required` — response includes `tenant_mfa_required: bool` and `grace_period_starts_at`. No GET endpoint for current state — read current MFA policy from the tenant settings catalog via `GET /api/v1/settings/` (if exists) or use `useSettingsCatalog()` hook.

> **Gap note**: The openapi_schema_map only shows `PUT /api/v1/settings/tenant/mfa-required`. The GET to read current tenant MFA policy state must come from either the settings catalog endpoint or the user's tenant context. **Companion backend check**: verify `GET /api/v1/settings/` or another endpoint returns `tenant_mfa_required` current value. If not, MSW handler needed for initial state display.

**Shared components**:
- `<SettingControl inputType="boolean" saveMode="explicit">` for MFA required toggle
- `<RoleGate permission="settings.manage">` wrapper
- Description text explaining grace period behavior

---

### Route 3: `/settings/team`

| Property | Value |
|---|---|
| **File path** | `frontend/apps/web/src/app/(authed)/settings/team/page.tsx` |
| **Auth** | Required (Cognito JWT) |
| **RBAC gate** | `settings.manage` (owner/accountant can manage team; techs cannot) |
| **Content type** | Partial functional — real user list + role change; invite button shows "invite coming soon" state |
| **Purpose** | List all tenant users with their roles, allow role reassignment, placeholder for invite. |

**Component**: `TeamSettingsPage` in `frontend/apps/web/src/features/settings/components/TeamSettingsPage.tsx`

**Backend data**:
- `GET /api/v1/users` — returns `[{user_id, email, role_code, role_name, permissions, joined_at, is_active}]`
- `POST /api/v1/users/{user_id}/role` — `{role_code: string}` to reassign role

**New hook**: `useTeamUsers` in `frontend/apps/web/src/features/settings/hooks/useTeamUsers.ts`

**Minimum viable content**:
- Heading: "Team"
- User list table: email, role badge (Owner/Tech/Accountant), joined date, role-change dropdown (owner-only action via `<RoleGate>`)
- "Invite team member" button — renders `<EmptyState>` dialog with "Inviting team members is coming soon. Ask your team to sign up and you'll be able to assign their role here." (Companion backend task: user invite endpoint)
- `<LoadingState>` spinner during fetch
- `<ErrorState>` on fetch failure

**Backend gap — Companion Task BETA-B4-BE-01**: No invite user endpoint exists (`POST /api/v1/users/invite` or similar) and no deactivate user endpoint (`PATCH /api/v1/users/{user_id}/deactivate` or similar). Document gap; invite UI renders informational message for beta; deactivate is not surfaced in BETA-B4.

---

### Route 4: `/settings/billing`

| Property | Value |
|---|---|
| **File path** | `frontend/apps/web/src/app/(authed)/settings/billing/page.tsx` |
| **Auth** | Required (Cognito JWT) |
| **RBAC gate** | `settings.manage` (owner/operator only per PRD §3.11 `subscription.view`) |
| **Content type** | Partial functional — real subscription data; no Stripe payment actions (Phase 2) |
| **Purpose** | Show current plan name, price, trial expiry (if applicable), user count usage, SMS quota usage. Upgrade CTA opens tier picker (existing component from FE-B13). |

**Component**: `BillingSettingsPage` in `frontend/apps/web/src/features/settings/components/BillingSettingsPage.tsx`

**Backend data**: `GET /api/v1/tenants/{tenant_id}/subscription` — response:
```ts
{
  current_tier: { tier_name, display_label, monthly_price_cents, is_trial, trial_duration_days, max_users },
  trial_ends_at: string | null,
  stripe_customer_id: string | null,
  usage: object,
  tier_override: object
}
```

**New hook**: `useTenantSubscription` in `frontend/apps/web/src/features/settings/hooks/useTenantSubscription.ts`

**Minimum viable content**:
- Heading: "Billing & Subscription"
- Current plan card: tier name, monthly price, billing interval (monthly/annual)
- Trial banner (if `is_trial=true`): "Trial ends [date] — upgrade to keep access"
- Usage summary: user count vs. max_users, SMS segments (from `usage` object)
- "Upgrade plan" button — visible if on trial or lower tier; opens `<TierPickerCard>` modal (FE-B13 component, already in `@pilot/ui`)
- "Payment methods" section: placeholder card — "Payment method management available after first subscription. Contact support@pilotfortrades.com if needed." (Stripe Customer Portal is Phase 2 per PRD §3.11)
- `<LoadingState>` / `<ErrorState>` handling

**Backend gap — Companion Task BETA-B4-BE-02**: No invoice history endpoint and no payment method management endpoint exist. Stripe Customer Portal deferred to Phase 2. Billing page does NOT attempt to show invoice history in BETA-B4.

---

### Route 5: `/settings/integrations/quickbooks`

| Property | Value |
|---|---|
| **File path** | `frontend/apps/web/src/app/(authed)/settings/integrations/quickbooks/page.tsx` |
| **Auth** | Required (Cognito JWT) |
| **RBAC gate** | `settings.manage` (integrations.manage maps to settings.manage for now — see §G) |
| **Content type** | Functional — real QB connection state, OAuth connect/disconnect |
| **Purpose** | QB integration index: connection status, connect/disconnect OAuth, link to auto-expiry settings, link to conflicts queue. |

**Component**: `QbIntegrationIndexPage` in `frontend/apps/web/src/features/settings/components/QbIntegrationIndexPage.tsx`

**Backend data**:
- `GET /api/v1/integrations/quickbooks/status` — connection state (`connected: bool`, `company_name`, `last_sync_at`, `expires_at`)
- `GET /api/v1/integrations/quickbooks/connect` — initiates OAuth (redirect)
- `DELETE /api/v1/integrations/quickbooks/disconnect` — disconnects

**Existing hook to reuse**: The QB conflicts page at `integrations/quickbooks/conflicts/page.tsx` likely has a `useQbStatus` hook — verify and reuse. If not, create `useQbConnectionStatus` in `frontend/apps/web/src/features/settings/hooks/useQbConnectionStatus.ts`.

**Minimum viable content**:
- Heading: "QuickBooks Integration"
- Connection status card: Connected (company name, last sync timestamp) or Disconnected
- "Connect QuickBooks" button (redirects to OAuth) OR "Disconnect" button (with confirm dialog)
- Links to sub-pages: "Auto-expiry & sync settings" → `/settings/integrations/quickbooks/auto-expiry`, "View conflicts" → `/settings/integrations/quickbooks/conflicts`
- `<InFlightSyncIndicator surface="quickbooks">` for sync state (FE-B15 component)

---

### Route 6: `/settings/integrations/general`

| Property | Value |
|---|---|
| **File path** | `frontend/apps/web/src/app/(authed)/settings/integrations/general/page.tsx` |
| **Auth** | Required (Cognito JWT) |
| **RBAC gate** | `settings.manage` |
| **Content type** | Functional — real sync dashboard summary + navigation to individual integrations |
| **Purpose** | Integrations overview: lists all integrations (QB, Calendar, SMS) with their connection state and a link to each integration's dedicated settings page. |

**Component**: `IntegrationsGeneralPage` in `frontend/apps/web/src/features/settings/components/IntegrationsGeneralPage.tsx`

**Backend data**:
- `GET /api/v1/integrations/sync-dashboard/` — returns sync counts by type
- `GET /api/v1/integrations/quickbooks/status` — QB connection state
- `GET /api/v1/integrations/calendar/status` — Calendar connection state

**New hook**: `useIntegrationsDashboard` in `frontend/apps/web/src/features/settings/hooks/useIntegrationsDashboard.ts` — fan-out fetches for QB status + calendar status + sync-dashboard; aggregates into a single connection overview object.

**Minimum viable content**:
- Heading: "Integrations"
- Integration row cards (3): QuickBooks, Calendar, SMS
  - Each: connection badge (Connected/Disconnected), last sync timestamp or "Not connected", link to dedicated settings page
- "Pending sync items" summary from `sync-dashboard` endpoint (if any)
- `<EmptyState>` if no integrations connected ("Connect an integration to get started")

---

### Route 7: `/settings/notifications/email`

| Property | Value |
|---|---|
| **File path** | `frontend/apps/web/src/app/(authed)/settings/notifications/email/page.tsx` |
| **Auth** | Required (Cognito JWT) |
| **RBAC gate** | All authenticated (personal notification preferences) |
| **Content type** | Functional — filtered view of notification preference matrix (email channel only) |
| **Purpose** | Show user's email notification preferences for all 8 categories. Filtered to email column of the full matrix. |

**Component**: `NotificationEmailPrefsPage` in `frontend/apps/web/src/features/settings/components/NotificationEmailPrefsPage.tsx`

**Backend data**: Reuse `useNotificationPreferences` hook (already used by `/notifications/preferences/page.tsx`). Filter to `channel = 'email'`.

**Minimum viable content**:
- Heading: "Email Notifications"
- Subheading: "Manage which events send you email notifications."
- Link to full preferences matrix at `/settings/notifications/preferences`
- Per-category email toggle list (8 rows from preferences matrix, email column only)
- Uses `<SettingControl inputType="boolean">` per row
- MSW handler: reuse existing notification preferences MSW handler; filter to email channel client-side

---

### Route 8: `/settings/notifications/sms`

| Property | Value |
|---|---|
| **File path** | `frontend/apps/web/src/app/(authed)/settings/notifications/sms/page.tsx` |
| **Auth** | Required (Cognito JWT) |
| **RBAC gate** | All authenticated |
| **Content type** | Functional — filtered view of notification preference matrix (sms channel only) |
| **Purpose** | Show user's SMS notification preferences for all 8 categories. |

**Component**: `NotificationSmsPrefsPage` in `frontend/apps/web/src/features/settings/components/NotificationSmsPrefsPage.tsx`

**Backend data**: Reuse `useNotificationPreferences`. Filter to `channel = 'sms'`.

**Note**: PRD §3.7 (FIND-077 correction) confirmed SMS is an active channel. The sms notification preferences are stored in the same preferences matrix.

---

### Route 9: `/settings/notifications/in-app`

| Property | Value |
|---|---|
| **File path** | `frontend/apps/web/src/app/(authed)/settings/notifications/in-app/page.tsx` |
| **Auth** | Required (Cognito JWT) |
| **RBAC gate** | All authenticated |
| **Content type** | Functional — filtered view of notification preference matrix (in_app channel only) + recent in-app notifications |
| **Purpose** | Show user's in-app notification preferences + recent in-app notification history. |

**Component**: `NotificationInAppPrefsPage` in `frontend/apps/web/src/features/settings/components/NotificationInAppPrefsPage.tsx`

**Backend data**:
- Reuse `useNotificationPreferences`. Filter to `channel = 'in_app'`
- `GET /api/v1/notifications/in-app/recent` — last 50 in-app notifications (for "Notification history" section)
- `POST /api/v1/notifications/in-app/mark-read` — bulk mark as read

---

### Route 10: `/settings/branding` (Redirect)

| Property | Value |
|---|---|
| **File path** | `frontend/apps/web/src/app/(authed)/settings/branding/page.tsx` |
| **Auth** | Required (Cognito JWT) |
| **RBAC gate** | N/A — redirect fires before content renders |
| **Content type** | **Redirect** to `/settings/communications/email-branding` |
| **Purpose** | The sidebar item `/settings/branding` should not 404. The full branding feature (FE-B14) lives at `/settings/communications/email-branding`. This page redirects there. |

**Rationale**: `EmailBrandingSettingsPanel` is complete at `/settings/communications/email-branding`. Duplicating it at `/settings/branding` is wasteful and creates maintenance divergence. A Next.js `redirect()` is the correct pattern.

**Implementation**: Single-line page using Next.js App Router `redirect()`:
```tsx
import { redirect } from 'next/navigation';
export default function BrandingPage() {
  redirect('/settings/communications/email-branding');
}
```
No client component needed — server-side redirect.

---

### Route 11: `/settings/data-privacy`

| Property | Value |
|---|---|
| **File path** | `frontend/apps/web/src/app/(authed)/settings/data-privacy/page.tsx` |
| **Auth** | Required (Cognito JWT) |
| **RBAC gate** | All authenticated |
| **Content type** | Informational — static description + link to data export feature |
| **Purpose** | P2 page. Explains data retention policies and links to the data export feature at `/settings/my-account/data-export`. |

**Component**: Inline page component (no feature component needed for informational page).

**Minimum viable content**:
- Heading: "Data & Privacy"
- Description: "Pilot retains your data for the duration of your subscription. You can export your data at any time."
- "Export your data" card with link to `/settings/my-account/data-export`
- Data retention policy text (static for beta): "Audit logs retained 12 months. Job and financial records retained indefinitely while subscription is active."
- No backend calls needed for this P2 informational page

---

## D. API Endpoint Consumption

| Page | Endpoint Path | Method | Hook | MSW Handler Needed? | Notes |
|---|---|---|---|---|---|
| My Account Security Index | `GET /api/v1/users/me/mfa-status` | GET | `useMfaStatus` (existing from security/mfa page — reuse) | No (stable) | Returns enrolled methods count |
| Tenant Security & MFA | `PUT /api/v1/settings/tenant/mfa-required` | PUT | `useTenantMfaPolicy` (new) | Yes — no GET equivalent confirmed | Read initial state from `useSettingsCatalog()` or create MSW for initial state |
| Team | `GET /api/v1/users` | GET | `useTeamUsers` (new) | No (stable) | Returns `[{user_id, email, role_code, is_active, joined_at}]` |
| Team | `POST /api/v1/users/{user_id}/role` | POST | `useAssignRole` (new, within useTeamUsers) | No (stable) | Role change action |
| Team — invite | **MISSING** | — | — | **Yes — MSW placeholder** | Companion task BETA-B4-BE-01 |
| Billing | `GET /api/v1/tenants/{tenant_id}/subscription` | GET | `useTenantSubscription` (new) | No (stable) | Returns tier, trial, usage |
| Billing — upgrade | `POST /api/v1/tenants/{tenant_id}/subscription/change-tier` | POST | Part of `useTenantSubscription` | No (stable) | Opens TierPickerCard (FE-B13) |
| QB Index | `GET /api/v1/integrations/quickbooks/status` | GET | `useQbConnectionStatus` (new or reuse) | No (stable) | Connection state |
| QB Index | `GET /api/v1/integrations/quickbooks/connect` | GET (OAuth redirect) | Inline handler (no hook) | No | Redirect to OAuth |
| QB Index | `DELETE /api/v1/integrations/quickbooks/disconnect` | DELETE | `useQbDisconnect` (new, within page) | No | Confirm-then-delete |
| Integrations General | `GET /api/v1/integrations/sync-dashboard/` | GET | `useIntegrationsDashboard` (new) | No (stable) | Pending sync counts |
| Integrations General | `GET /api/v1/integrations/quickbooks/status` | GET | Reused within `useIntegrationsDashboard` | No | |
| Integrations General | `GET /api/v1/integrations/calendar/status` | GET | Reused within `useIntegrationsDashboard` | No | |
| Notifications Email | `GET /api/v1/notifications/preferences` | GET | Reuse `useNotificationPreferences` | No | Filter to `channel='email'` client-side |
| Notifications Email | `PUT /api/v1/notifications/preferences/{category_id}/{channel}` | PUT | Reuse `useNotificationPreferences` | No | `channel='email'` |
| Notifications SMS | `GET /api/v1/notifications/preferences` | GET | Reuse `useNotificationPreferences` | No | Filter to `channel='sms'` |
| Notifications In-App | `GET /api/v1/notifications/preferences` | GET | Reuse `useNotificationPreferences` | No | Filter to `channel='in_app'` |
| Notifications In-App | `GET /api/v1/notifications/in-app/recent` | GET | `useRecentInAppNotifications` (new) | No (stable) | Last 50 notifications |
| Notifications In-App | `POST /api/v1/notifications/in-app/mark-read` | POST | Part of `useRecentInAppNotifications` | No | |
| Branding | None (redirect) | — | — | No | Server redirect only |
| Data & Privacy | None (static) | — | — | No | Informational only |

---

## E. Pattern Reuse Decisions

| Page | Pattern Applied | Component(s) Used |
|---|---|---|
| My Account Security Index | Standard page heading pattern (profile page pattern) | `EmptyState`, `LoadingState` if fetch fails |
| Tenant Security & MFA | Two-Tier Configuration Pattern (system default + tenant override); `SettingControl` boolean toggle | `<SettingControl inputType="boolean" saveMode="explicit">`, `<RevertToDefaultDialog>` |
| Team | List + action pattern (no existing template — closest is profile pattern for structure) | `EmptyState` for invite placeholder, `LoadingState`, `ErrorState`, `RoleGate` for role change action |
| Billing | Data display + CTA pattern | `LoadingState`, `EmptyState` (if no subscription), `TierPickerCard` (FE-B13, already in `@pilot/ui`) |
| QB Index | Status card + OAuth action pattern (same as calendar settings pattern) | `InFlightSyncIndicator` (FE-B15), `LoadingState`, `ErrorState` |
| Integrations General | Card list overview pattern | `InFlightSyncIndicator`, `EmptyState`, `LoadingState` |
| Notification Email/SMS/In-App | `SettingControl` boolean per row — reuse exact pattern from `notifications/preferences` page | `<SettingControl inputType="boolean" saveMode="blur">` per category row; `<NotificationPreferenceMatrix>` with `channelFilter` prop if supported, else manual row rendering |
| Branding | Server-side redirect — no pattern components | `redirect()` from `next/navigation` |
| Data & Privacy | Informational landing page — heading + description + link cards | `EmptyState` for "no exports yet" state |

**§16 `mvp-arch.md` patterns consumed**:
- **Two-Tier Configuration**: Tenant Security MFA policy toggle (system default → tenant override)
- **Pre-Commit Staleness Check**: Not required for BETA-B4 pages (no concurrent edit scenarios)
- **Optimistic UI**: Not applied (settings mutations are low-frequency; explicit save is correct for security/billing)
- **Four-Class Severity**: Not consumed (no conflict flows in this batch)

---

## F. Shared Module Interfaces

### New Permission Keys — `permissions.ts`

**BETA-B4 must add these keys** to the `PermissionKey` union and `ROLE_PERMISSION_MAP`:

```typescript
// BETA-B4 additions to PermissionKey
| "integrations.manage"        // integrations settings access — owner, operator
| "settings.tenant.write"      // tenant-level settings write — owner, operator  
| "billing.view"               // subscription/billing view — owner, operator
```

**ROLE_PERMISSION_MAP updates**:
```typescript
// owner — add all three
// office_staff — add none (cannot manage integrations, billing, or tenant settings)
// tech — add none
// operator — add all three
```

**Rationale**: `SettingsSidebar.tsx` references `roleRequired: "settings.tenant.write"` and `roleRequired: "integrations.manage"` as strings on `SidebarItem`. These don't actually gate via `<RoleGate>` today (sidebar uses `roleRequired` string but has no enforcement). Adding proper keys allows future `<RoleGate>` enforcement. `billing.view` is new for the billing page.

---

### New Hook: `useTeamUsers`

```typescript
// Location: frontend/apps/web/src/features/settings/hooks/useTeamUsers.ts

interface TeamUser {
  userId: string;
  email: string;
  roleCode: string;
  roleName: string;
  permissions: string[];
  joinedAt: string | null;
  isActive: boolean;
}

interface UseTeamUsersReturn {
  users: TeamUser[];
  isLoading: boolean;
  isError: boolean;
  assignRole: (userId: string, roleCode: string) => Promise<void>;
  isAssigning: boolean;
}

export function useTeamUsers(): UseTeamUsersReturn;
```

---

### New Hook: `useTenantSubscription`

```typescript
// Location: frontend/apps/web/src/features/settings/hooks/useTenantSubscription.ts

interface SubscriptionTier {
  tierId: string;
  tierName: string;
  displayLabel: string;
  monthlyPriceCents: number;
  isTrial: boolean;
  trialDurationDays: number | null;
  maxUsers: number;
  maxSmsSegmentsPerMonth: number | null;
}

interface TenantSubscription {
  currentTier: SubscriptionTier;
  trialEndsAt: string | null;
  stripeCustomerId: string | null;
  usage: {
    currentUserCount?: number;
    currentSmsSegments?: number;
  };
  tierOverride: object | null;
}

interface UseTenantSubscriptionReturn {
  subscription: TenantSubscription | null;
  isLoading: boolean;
  isError: boolean;
  changeTier: (targetTierId: string) => Promise<void>;
  isChangingTier: boolean;
}

export function useTenantSubscription(): UseTenantSubscriptionReturn;
```

---

### New Hook: `useIntegrationsDashboard`

```typescript
// Location: frontend/apps/web/src/features/settings/hooks/useIntegrationsDashboard.ts

interface IntegrationStatus {
  connected: boolean;
  displayName: string;
  lastSyncAt: string | null;
  settingsHref: string;
}

interface IntegrationsDashboard {
  quickbooks: IntegrationStatus;
  calendar: IntegrationStatus;
  sms: IntegrationStatus; // derived from tenant phone numbers provisioned
  syncDashboard: {
    pendingCount: number;
    errorCount: number;
  } | null;
}

interface UseIntegrationsDashboardReturn {
  dashboard: IntegrationsDashboard | null;
  isLoading: boolean;
  isError: boolean;
}

export function useIntegrationsDashboard(): UseIntegrationsDashboardReturn;
```

---

### New Hook: `useTenantMfaPolicy`

```typescript
// Location: frontend/apps/web/src/features/settings/hooks/useTenantMfaPolicy.ts

interface TenantMfaPolicy {
  tenantMfaRequired: boolean;
  gracePeriodStartsAt: string | null;
}

interface UseTenantMfaPolicyReturn {
  policy: TenantMfaPolicy | null;
  isLoading: boolean;
  isError: boolean;
  setMfaRequired: (required: boolean) => Promise<void>;
  isUpdating: boolean;
}

export function useTenantMfaPolicy(): UseTenantMfaPolicyReturn;
```

**Note**: Initial state must come from `useSettingsCatalog()` or a direct fetch. If neither provides the current `tenant_mfa_required` value on load, the hook uses `PUT` response to sync state and displays a loading skeleton on first render. MSW handler required for test environment.

---

### New Hook: `useRecentInAppNotifications`

```typescript
// Location: frontend/apps/web/src/features/notification-preferences/hooks/useRecentInAppNotifications.ts

interface InAppNotification {
  notificationId: string;
  category: string;
  title: string;
  body: string;
  isRead: boolean;
  createdAt: string;
  deepLinkHref: string | null;
}

interface UseRecentInAppNotificationsReturn {
  notifications: InAppNotification[];
  isLoading: boolean;
  isError: boolean;
  markAllRead: () => Promise<void>;
  isMarkingRead: boolean;
}

export function useRecentInAppNotifications(): UseRecentInAppNotificationsReturn;
```

---

### Existing Hooks Reused (Confirm Import Paths)

| Hook | Source | Used By |
|---|---|---|
| `useNotificationPreferences` | `frontend/apps/web/src/features/notification-preferences/hooks/useNotificationPreferences.ts` | `/notifications/email`, `/notifications/sms`, `/notifications/in-app` |
| `useMfaStatus` | `frontend/apps/web/src/features/account-settings/hooks/useMfaStatus.ts` (verify exists) | My Account Security index |

---

## G. Open Questions Resolved

| Question | Resolution |
|---|---|
| **Is the SettingsShell layout already fixed?** | **YES — confirmed fixed.** `SettingsShell.tsx` current CSS is `flex h-full min-h-0 flex-1`. The patch from `min-h-screen` to `h-full min-h-0 flex-1` is already in place. No layout code changes in BETA-B4. |
| **Is `/settings/branding` a redirect or a new page?** | **Redirect.** `/settings/communications/email-branding` has the complete `EmailBrandingSettingsPanel` from FE-B14 with full branding API support. A server-side `redirect()` eliminates the 404 without any content duplication. |
| **Does `integrations.manage` permission key exist in `permissions.ts`?** | **No.** The sidebar references it as a string but the `PermissionKey` union and `ROLE_PERMISSION_MAP` do not include it. BETA-B4 adds it. For beta, use `settings.manage` as the effective gate for all integrations settings pages (owner + operator only). |
| **What is the MVP scope for the Team page given missing invite/deactivate endpoints?** | **Partial functional.** List all users + role change = achievable with existing endpoints. Invite = companion task BETA-B4-BE-01 with placeholder UI. Deactivate = not surfaced in BETA-B4 (no endpoint, not blocking for beta owner testing). |
| **Is Stripe connected for billing?** | **No.** The subscription endpoint (`GET /api/v1/tenants/{tenant_id}/subscription`) returns `stripe_customer_id: null` for tenants without paid tiers. PRD §3.11 explicitly defers Stripe Customer Portal to Phase 2. Billing page shows plan + usage only — no payment method management. "Upgrade plan" CTA uses the existing `<TierPickerCard>` from FE-B13 which calls `POST .../change-tier` (this endpoint exists). |
| **Are per-channel notification pages separate features or filtered views of the matrix?** | **Filtered views.** The PRD defines a unified per-user × per-category × per-channel matrix. No dedicated per-channel API endpoints exist. Each channel page renders the same preference data filtered to its channel column, with a link to the full matrix at `/settings/notifications/preferences`. The `useNotificationPreferences` hook is reused with client-side channel filter. |
| **My Account > Security index vs. `/settings/security` — how are these different?** | **Different surfaces.** `/settings/my-account/security` is a personal account security hub (user's own MFA methods, sessions, password — already built as sub-pages; this is the index linking them). `/settings/security` is the **tenant-level** security policy page (owner sets MFA required policy for all users). Both needed. |
| **Does `/settings/notifications` (the parent) need a page?** | **Out of scope for BETA-B4.** The sidebar items go directly to sub-pages (`/email`, `/sms`, `/in-app`, `/preferences`). The parent `/settings/notifications` (without trailing path) isn't in the sidebar; no 404 reported there. Not in BETA-B4 scope. |
| **`useMfaStatus` hook — does it exist?** | The MFA management page at `/settings/my-account/security/mfa/page.tsx` exists. It likely has the hook. Before the React Engineer starts, verify hook exists at `frontend/apps/web/src/features/account-settings/hooks/useMfaStatus.ts`. If not, the React Engineer creates it using `GET /api/v1/users/me/mfa-status`. |
| **Where does the SMS integration status come from for Integrations General?** | SMS has no `GET /api/v1/integrations/sms/status` endpoint. SMS status is inferred from whether the tenant has provisioned phone numbers via `GET /api/v1/tenants/{tenant_id}/phone-numbers/`. `useIntegrationsDashboard` includes this fetch; if empty array → not configured. |
| **Does the tenant settings GET endpoint return `tenant_mfa_required`?** | **Unconfirmed.** The openapi_schema_map only shows `PUT /api/v1/settings/tenant/mfa-required`. The `GET /api/v1/settings/` or similar endpoint was not found in the search results. The React Engineer must check the openapi.json directly or use the live server. If no GET exists, the MFA policy hook initializes from `useSettingsCatalog()` data or shows loading until the user first interacts. MSW provides initial `false` state for test environments. This is **Companion Backend Check BETA-B4-BE-03**. |

---

## H. External Dependency Status

| Page | Dependency | Status | Risk |
|---|---|---|---|
| My Account Security Index | `GET /api/v1/users/me/mfa-status` | ✅ Stable (in openapi_schema_map) | Low |
| Tenant Security & MFA | `PUT /api/v1/settings/tenant/mfa-required` | ✅ Stable; GET for initial state TBD | Medium — see BETA-B4-BE-03 |
| Team | `GET /api/v1/users` + `POST .../role` | ✅ Stable | Low |
| Team — invite | Missing backend endpoint | ❌ Backend gap (BETA-B4-BE-01) | Invite UI shows placeholder |
| Billing | `GET /api/v1/tenants/{tenant_id}/subscription` | ✅ Stable | Low |
| Billing — Stripe | Not connected | ❌ Phase 2 per PRD | Payment management shows placeholder |
| QB Index | `GET/DELETE /api/v1/integrations/quickbooks/status+disconnect` | ✅ Stable | Low |
| Integrations General | `sync-dashboard`, QB status, calendar status | ✅ All stable | Low |
| Notifications Email/SMS/In-App | `GET /api/v1/notifications/preferences` | ✅ Stable (used by /preferences page) | Low |
| Notifications In-App | `GET /api/v1/notifications/in-app/recent` | ✅ Stable | Low |
| Branding | None (redirect) | N/A | None |
| Data & Privacy | None (static + link to existing data-export page) | N/A | None |

**Companion Backend Tasks (BETA-B4 only — do not block React Engineer):**

- **BETA-B4-BE-01**: Implement user invite endpoint: `POST /api/v1/users/invite` — `{email: string, role_code: string}` → `{invite_id, status, email, expires_at}`. Also implement deactivate: `PATCH /api/v1/users/{user_id}/deactivate`. Assign to Python Engineer after BETA-B4 React work is complete.
- **BETA-B4-BE-02**: Invoice history and payment method management endpoints. Deferred to Stripe integration phase (post-beta).
- **BETA-B4-BE-03**: Verify whether a GET endpoint exists for the current `tenant_mfa_required` policy value. If not, add `GET /api/v1/settings/tenant/mfa-required` returning `{tenant_mfa_required: bool, grace_period_starts_at: string | null}`. Needed before the tenant security page can initialize correctly without relying only on `useSettingsCatalog()`.

---

## I. Test Plan

All integration test files live in: `frontend/apps/web/__tests__/batch_beta_v1_b4/`

| Page | Unit Test File | Integration Test File | Coverage Requirements |
|---|---|---|---|
| `permissions.ts` additions | `frontend/packages/ui/src/role-gate/__tests__/permissions.beta-b4.test.ts` | — | New keys in union type; ROLE_PERMISSION_MAP correctly assigns `integrations.manage` and `settings.tenant.write` to owner + operator only; office_staff excluded; tech excluded |
| My Account Security Index | `frontend/apps/web/src/features/account-settings/__tests__/SecurityIndexPage.test.tsx` | `__tests__/batch_beta_v1_b4/security-index.test.tsx` | Page renders (not 404); shows MFA method count from mock; shows navigation links to mfa/, sessions/, password/; `LoadingState` on fetch pending; `ErrorState` on fetch failure |
| Tenant Security & MFA | `frontend/apps/web/src/features/settings/__tests__/TenantSecurityPage.test.tsx` | `__tests__/batch_beta_v1_b4/tenant-security.test.tsx` | Page renders (not 404); toggle renders with current state from MSW; MFA required can be toggled; `RoleGate` hides page for tech/office_staff; confirm pattern fires PUT on save |
| Team | `frontend/apps/web/src/features/settings/__tests__/TeamSettingsPage.test.tsx` | `__tests__/batch_beta_v1_b4/team.test.tsx` | Page renders (not 404); user list renders from MSW; role dropdown present for owner; role change fires POST to `/users/{id}/role`; invite button renders placeholder state; tech role cannot see role-change controls |
| Billing | `frontend/apps/web/src/features/settings/__tests__/BillingSettingsPage.test.tsx` | `__tests__/batch_beta_v1_b4/billing.test.tsx` | Page renders (not 404); plan name visible; trial banner visible when `is_trial=true`; user count usage renders; upgrade CTA visible on trial; payment methods section shows placeholder; `LoadingState` on fetch pending |
| QB Index | `frontend/apps/web/src/features/settings/__tests__/QbIntegrationIndexPage.test.tsx` | `__tests__/batch_beta_v1_b4/qb-index.test.tsx` | Page renders (not 404); connected state shows company name + last sync; disconnected state shows connect button; disconnect confirm dialog renders; links to auto-expiry and conflicts sub-pages present |
| Integrations General | `frontend/apps/web/src/features/settings/__tests__/IntegrationsGeneralPage.test.tsx` | `__tests__/batch_beta_v1_b4/integrations-general.test.tsx` | Page renders (not 404); QB card shows connected/disconnected state; Calendar card shows status; SMS card shows provisioning status; `EmptyState` renders when all disconnected |
| Notifications Email | `frontend/apps/web/src/features/settings/__tests__/NotificationEmailPrefsPage.test.tsx` | `__tests__/batch_beta_v1_b4/notifications-email.test.tsx` | Page renders (not 404); email category rows present (8 rows); toggles call PUT with `channel='email'`; link to full preferences matrix present; `LoadingState` while fetching |
| Notifications SMS | `frontend/apps/web/src/features/settings/__tests__/NotificationSmsPrefsPage.test.tsx` | `__tests__/batch_beta_v1_b4/notifications-sms.test.tsx` | Page renders (not 404); sms category rows present; toggles call PUT with `channel='sms'` |
| Notifications In-App | `frontend/apps/web/src/features/settings/__tests__/NotificationInAppPrefsPage.test.tsx` | `__tests__/batch_beta_v1_b4/notifications-in-app.test.tsx` | Page renders (not 404); in-app prefs rows present; recent notifications list renders from MSW; mark-all-read fires POST to `/notifications/in-app/mark-read` |
| Branding (redirect) | — | `__tests__/batch_beta_v1_b4/branding-redirect.test.tsx` | Page does NOT 404; redirect to `/settings/communications/email-branding` fires on render |
| Data & Privacy | `frontend/apps/web/src/features/settings/__tests__/DataPrivacyPage.test.tsx` | `__tests__/batch_beta_v1_b4/data-privacy.test.tsx` | Page renders (not 404); data export link present pointing to `/settings/my-account/data-export`; static retention text renders; no backend calls made |

**Minimum coverage gate per page**: Route renders (not 404) + correct RBAC for owner + primary content visible with MSW mock data.

---

## Appendix: Route Confirmation Table

All 11 routes confirmed as genuinely missing (`page.tsx` does not exist):

| Route | Confirmed Missing |
|---|---|
| `/settings/integrations/general` | ✅ No `page.tsx` at `integrations/general/` |
| `/settings/integrations/quickbooks` | ✅ Only sub-pages exist (`auto-expiry/`, `conflicts/`) |
| `/settings/my-account/security` (index) | ✅ Only children exist (`mfa/`, `mfa/enroll/`) |
| `/settings/notifications/email` | ✅ No `page.tsx` at `notifications/email/` |
| `/settings/notifications/sms` | ✅ No `page.tsx` at `notifications/sms/` |
| `/settings/notifications/in-app` | ✅ No `page.tsx` at `notifications/in-app/` |
| `/settings/branding` | ✅ No `branding/` directory |
| `/settings/team` | ✅ No `team/` directory |
| `/settings/billing` | ✅ No `billing/` directory |
| `/settings/security` | ✅ No `security/` directory (distinct from `my-account/security`) |
| `/settings/data-privacy` | ✅ No `data-privacy/` directory |
