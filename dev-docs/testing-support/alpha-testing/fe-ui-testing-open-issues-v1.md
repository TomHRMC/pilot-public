# Frontend UI Testing — Open Issues Tracker

**Version**: 1.0  
**Date**: 2026-06-03  
**Scope**: Issues discovered during initial frontend UI smoke testing of the MVP web and mobile apps. Each item is something we decided NOT to fix immediately — tracked here so context is preserved across chat sessions.

---

## Table of Contents

- [1. Data](#1-data)
- [2. Frontend Features](#2-frontend-features)
- [3. Backend Features](#3-backend-features)
- [4. Completed Fixes](#4-completed-fixes)
- [5. Learnings](#5-learnings)

---

## 1. Data

Issues where the UI is correct but there is no data in the DB to demonstrate the feature.

### 1.1 Dispatch Board — No Tech or Job Seed Data

**Page**: Schedule (Dispatch Board)  
**Symptom**: Filter sidebar shows "Tech" and "Job Type" sections with no checkboxes. Dispatch grid shows only an "Unassigned" column with 0 jobs. The 6am–7pm day timeline renders but no job blocks appear.  
**Root cause**: `board.techs` and `board.jobs` are empty arrays because there are no `job` rows, `scheduling_job_tech_assignment` rows, or scheduled tech entries in the dev DB for "Pilot Dev Tenant."  
**Resolution needed**: Run seed scripts to populate `job`, `scheduling_job_tech_assignment`, `tech_user`, and related tables with test jobs assigned to test technicians. Reference `dev-docs/seed-data/seed-scripts-usage-reference-analysis.md`.

### 1.2 Dashboard — Recent Customer Messages Widget Shows Empty State

**Page**: Dashboard  
**Symptom**: `<RecentCustomerMessagesWidget>` renders its empty state ("No customer messages yet") because there are no `customer_communication_thread` or `customer_communication_message` rows in the dev DB.  
**Resolution needed**: Seed SMS thread data for "Pilot Dev Tenant."

### 1.3 Dashboard — Onboarding Checklist Not Shown

**Page**: Dashboard  
**Symptom**: `<OnboardingChecklistWidget>` does not render because `GET /api/v1/tenants/{tenant_id}/onboarding/checklist` returns a state where `checklistDismissedPermanently=true` or all items are marked complete.  
**Resolution needed**: Reset the onboarding checklist state for "Pilot Dev Tenant" in the DB or via seed script.

---

## 2. Frontend Features

New UI work, enhancements to existing components, and frontend-only gaps discovered during testing.

### 2.1 Dispatch Board — 4-Day, Week, Month Views Not Implemented

**Page**: Schedule (Dispatch Board)  
**Symptom**: Clicking "4 Day," "Week," or "Month" buttons updates the `activeDate` and drives new API calls with the correct date range, but the grid visual does not change — it always shows the same single-column-per-tech layout.  
**Root cause**: FE-B4 only implemented the Day view grid layout. Multi-day grid (rendering N date columns side-by-side) was not built.  
**Resolution needed**: Implement a multi-day rendering mode in `<DispatchGrid>` that shows one time column per date for 4-Day/Week view, and a month-calendar layout for Month view. The date range is already correctly calculated by `getTabDays()` in `store.ts` and the API calls are correct — only the visual rendering is missing.

### 2.2 Reports — "Custom" Date Range Period Not Implemented

**Page**: Reports (`/reports`)
**Symptom**: The `<PeriodSelector>` component only shows 4 period pills (7 days, 30 days, MTD, YTD). The component docstring says `"7d / 30d / MTD / YTD / Custom pills"` but the `PERIODS` array in `PeriodSelector.tsx` has no "Custom" entry.
**Root cause**: Custom date range was designed but not implemented in FE-B4. It requires a date picker UI + `start`/`end` date params to the `GET /api/v1/reports/profitability` endpoint.
**Resolution needed**: Add `{ value: "custom", label: "Custom" }` to `PERIODS`, wire a date range picker that appears when "Custom" is selected, and pass `?start=&end=` to the API. Requires checking backend endpoint supports arbitrary date ranges.

### 2.3 Web Sidebar — Owner-Only Items Use Wrong Permission Key

**Page**: All authenticated pages  
**Symptom**: Reports, Operations, and Sync sidebar items are hidden for non-owner roles using `useRequiresPermission("settings.manage")`. This is a proxy permission — if the permission system ever changes, these items could show/hide incorrectly.  
**Resolution needed**: Add explicit `PilotRole`-based gating in `<AppSidebar>` or add dedicated `"reports.view"`, `"operations.view"`, `"sync.view"` permission keys to `packages/ui/src/role-gate/permissions.ts`.

### 2.3 Web — Customers, Quotes, Invoices, Reports, Comms, Operations, Sync, Notifications Pages Are FE-B0 Stubs

**Pages**: `/customers`, `/quotes`, `/invoices`, `/reports`, `/comms`, `/operations`, `/sync`, `/notifications`
**Symptom**: Each page renders only an `<h1>` heading with no content. No list, search, or detail surfaces were built for these routes in any FE-B0 through FE-B16 batch.
**Note**: Sub-routes DO have real content — `/customers/[id]/comms` (FE-B6/B10), `/quotes/pending` + `/quotes/[id]` (FE-B5), `/reports` renders `<ProfitabilityPage>` (FE-B4). Only the top-level list/index pages are missing.
**Resolution needed**: Build customer list, quotes list, invoices list, and comms summary pages. These are the primary navigation landing pages users will see first. Prioritize by user role: owner sees reports/schedule; tech sees jobs; all roles see customers.

### 2.4 Mobile — Jobs, Customers, Calcs Tabs Are Stub Placeholders

**Pages**: Mobile Jobs tab, Customers tab, Calcs tab  
**Symptom**: All three tabs show centered text only (e.g., "Jobs"). No real content was built for these tabs in any FE-B batch.  
**Resolution needed**: Design and implement mobile-specific content for Jobs, Customers, and Calcs tabs. These are post-MVP surfaces.

### 2.4 Settings Sub-Navigation Looks Unstyled

**Page**: Settings  
**Symptom**: The settings sub-menu (second-level sidebar via `<SettingsSidebar>`) renders but the user reported it "looks off" alongside the main `<AppSidebar>`.  
**Root cause**: `<SettingsShell>` uses `min-h-screen` which was patched to `h-full min-h-0 flex-1`, but the overall visual treatment of a double-sidebar (main nav + settings nav) may need a dedicated layout pass.  
**Resolution needed**: Visual design review of the Settings layout — consider whether the settings second-level nav should be a top tab bar instead of a left panel when nested inside the main sidebar.

### 2.7 Settings Sidebar — Missing MVP Pages (404 on Click)

**Page**: Settings
**Symptom**: Clicking the following sidebar items produces Next.js 404 pages — no `page.tsx` file exists yet. All are **required for MVP** and must be built:

| Sidebar Item | Missing Route | Notes |
|---|---|---|
| Integrations > General | `/settings/integrations/general` | General integration overview/status page |
| Integrations > QuickBooks (index) | `/settings/integrations/quickbooks` | QB connection status + conflict queue entry |
| My Account > Security (index) | `/settings/my-account/security` | Security overview landing page |
| Notifications > Email | `/settings/notifications/email` | Email notification preferences |
| Notifications > SMS | `/settings/notifications/sms` | SMS notification preferences |
| Notifications > In-app | `/settings/notifications/in-app` | In-app notification preferences |
| Branding | `/settings/branding` | Tenant email + logo branding (built in FE-B14 but as `/settings/communications/email-branding` — may need redirect or re-route) |
| Team | `/settings/team` | Tenant user management (invite, roles, deactivate) |
| Billing | `/settings/billing` | Subscription tier, payment method, invoice history |
| Security & MFA | `/settings/security` | Tenant-level MFA policy (different from `/my-account/security`) |
| Data & Privacy | `/settings/data-privacy` | Data retention, export, GDPR-related settings |

**Root cause**: `SettingsSidebar.tsx` was designed for the full Settings IA (11 groups) but only a subset of those pages were built in FE-B11/B12. The sidebar navigation is complete; the destination pages are not.
**Resolution needed**: Build all 11 missing pages. Each should have a `page.tsx` file at the route listed. Start with the highest-priority owner surfaces: Team, Billing, and Integrations > QuickBooks index.

---

## 3. Backend Features

New API endpoints, auth/authorization improvements, and backend gaps that block frontend features.

### 3.1 `GET /api/v1/owner/field-issues/summary` — Endpoint Does Not Exist

**Consuming component**: `<FieldIssuesSyncStatusSection>` (Owner tab, mobile)  
**Symptom**: Returns 404.  
**Resolution needed**: Implement `GET /api/v1/owner/field-issues/summary` in the backend that returns `{ "pending_count": N }` — the count of escalated mobile sync conflicts awaiting owner resolution. Mirroring the `owner_escalations` route is likely the right approach.

### 3.2 `GET /api/v1/dashboard/widgets/recent-customer-messages` — Returns 403 for Owner

**Consuming component**: `<RecentCustomerMessagesWidget>` (Dashboard)  
**Symptom**: Even logged in as `dev@pilot.local` (owner role in DB), the endpoint returns 403 Forbidden.  
**Root cause under investigation**: The `owner` role has `"*"` wildcard permission in `tenant_user_role`, which should match `communications.view`. Either the wildcard matching is not working for this endpoint, or the JWT is being resolved to a different user than expected.  
**Resolution needed**: Debug `GET /api/v1/dashboard/widgets/recent-customer-messages` permission check. Verify `has_permission(["*"], "communications.view")` returns `True` in the backend `permissions.py` logic.

### 3.3 SSE Board Stream — JWT Token Required as Query Param

**Consuming component**: `<useDispatchSse>` (Schedule page)  
**Symptom**: `GET /api/v1/scheduling/board/stream` returns 422 because the `token` query param is required (browser `EventSource` cannot send `Authorization` headers).  
**Status**: Partially fixed — `useDispatchSse` now fetches the Amplify JWT and passes `?token=JWT`. However, this pattern is not yet applied to other SSE endpoints (e.g., `/api/v1/notifications/in-app/recent`, `/api/v1/sync/stream`).  
**Resolution needed**: Audit all SSE endpoints and ensure each `useSseChannel` call fetches and appends the JWT token as a query param. Consider centralizing this in `useSseChannel` itself by adding an optional `getToken` prop.

### 3.4 `/api/v1/scheduling/dispatch-board` Requires Datetime Not Date

**Consuming component**: `<useDispatchBoard>` (Schedule page)  
**Symptom**: Was returning 422 when `?date=2026-06-03` was passed.  
**Status**: Fixed — updated to `?start_date=2026-06-03T00:00:00Z&end_date=2026-06-03T23:59:59Z`.  
**Residual concern**: The frontend type stub `DispatchBoardResponse` expects a `date` field in the response. If the backend returns `start_date`/`end_date` instead, the response normalization may fail silently. Verify response schema against `openapi.json` once seed data is in place and a real board load is tested.

### 3.5 Reports — `useProfitability` Sends `?period=` But Backend Requires `?date_from=&date_to=` (422)

**Page**: Reports (`/reports`)
**Symptom**: `GET /api/v1/reports/profitability?period=30d` returns 422 for all period selections.
**Root cause**: Backend requires two required params `date_from` (YYYY-MM-DD) and `date_to` (YYYY-MM-DD). The frontend hook `useProfitability` was built with a `?period=7d` shorthand that doesn't match the actual API contract.
**Resolution needed**: Update `apps/web/src/features/profitability/hooks/useProfitability.ts` to convert each period pill to computed dates before calling the API:
- `7d` → `date_from = today - 7 days`, `date_to = today`
- `30d` → `date_from = today - 30 days`, `date_to = today`
- `mtd` → `date_from = first of current month`, `date_to = today`
- `ytd` → `date_from = Jan 1 current year`, `date_to = today`
- `custom` → user-specified `date_from` / `date_to` (see Frontend Features 2.2)

### 3.6 Comms — `/api/v1/communications/recent` Endpoint Does Not Exist (404)

**Page**: Comms (`/comms`)
**Symptom**: `GET /api/v1/communications/recent?page=1&page_size=50` returns 404. The Comms page renders a template but shows "Failed to load communications."
**Root cause**: `/api/v1/communications/recent` is not in `openapi.json`. The actual communications endpoints are scoped per-customer (`/api/v1/customers/{id}/communication-history`) or per-thread.
**Resolution needed**: Either (a) add a new `GET /api/v1/communications/recent` backend endpoint that aggregates recent communications across all customers for the tenant, or (b) update the frontend Comms page to call an existing aggregate endpoint. Check if any other endpoint returns a cross-customer comms summary.

---

## 4. Completed Fixes

Issues found and resolved during this testing session.

### 4.1 Mobile Bottom Tab Bar — Extra Tabs Showing

**Fix**: Added `href: null` for 6 non-tab routes (`more/about`, `more/help/*`, `customers/[id]/comms`, `jobs/[jobId]/comms`) in `apps/mobile/app/(tabs)/_layout.tsx`. Also removed `(home)` stub `index.tsx` so the real Home screen renders.

### 4.2 Web Authenticated Layout — No Navigation Sidebar

**Fix**: Created `apps/web/src/components/AppSidebar.tsx` with all 11 nav sections and wired it into `apps/web/src/app/(authed)/layout.tsx`.

### 4.3 Dashboard Page — Showing Placeholder Text Only

**Fix**: Replaced the FE-B2 placeholder `dashboard/page.tsx` with real widget composition (`<TrialExpiryBanner>`, `<OnboardingChecklistWidget>`, `<RecentCustomerMessagesWidget>`).

### 4.4 All Web Feature Hooks Using Raw `fetch()` Instead of `apiClient`

**Fix**: Migrated ~35 hook files in `apps/web/src/features/` from raw `fetch('/api/v1/...')` to `apiClient` (JWT-intercepted Axios). Also patched all orphaned syntax artifacts left by the regex migration (14 files with parse errors caught by Prettier pre-commit hook).

### 4.5 Next.js Missing API Proxy — All `/api/v1/` Calls Hit Port 3000

**Fix**: Added `rewrites()` in `apps/web/next.config.ts` to proxy all `/api/v1/*` requests to `NEXT_PUBLIC_API_URL` (FastAPI backend at port 8000). Raw `fetch()` calls with relative paths now correctly route to FastAPI.

### 4.6 Dispatch Board — Wrong API Endpoint URLs

**Fix**: Corrected `useDispatchBoard` (`/api/v1/schedule/board` → `/api/v1/scheduling/dispatch-board`) and `useDispatchSse` (`/api/v1/schedule/board/stream` → `/api/v1/scheduling/board/stream`).

### 4.7 `react-native-stub.js` Missing `Linking` Export

**Fix**: Added `Linking` stub to `apps/web/src/lib/react-native-stub.js` to fix the web build error caused by `CalendarSyncStatusRow.tsx` importing `Linking` from `react-native`.

### 4.8 Mobile Owner Tab — Calendar + Field Issues Hooks Calling Backend Without JWT in Mock Mode

**Fix**: Added `enabled: !isMockAuth` to `useCalendarStatus` and `useFieldIssuesStatus` in mobile to prevent 401/404 spam when running with `EXPO_PUBLIC_USE_MOCK_AUTH=true`.

### 4.9 Authorization Model — Role Read from Cognito JWT Claims Instead of DB

**Fix**: Rewrote `AuthProvider.tsx` to call `GET /api/v1/users/me/permissions` after Cognito auth succeeds, instead of reading `custom:role` from the JWT payload. Cognito is now identity-only; role and tenantId come from the local DB. This unblocked `<RoleGate>` on the Schedule page.

### 4.10 `SettingsShell` Using `min-h-screen` — Broken With Sidebar Layout

**Fix**: Changed `min-h-screen` to `h-full min-h-0 flex-1` in `<SettingsShell>` so the settings page composes correctly inside the main sidebar layout.

---

## 5. Learnings

Architectural decisions made and patterns to enforce going forward. Each item flags which design docs may need updating.

### 5.1 Cognito Is Identity Only — Never Use JWT Claims for Authorization

**Learning**: Storing role/tenant in Cognito custom attributes (`custom:role`, `custom:tenant_id`) creates a two-source-of-truth problem — if the DB role changes, the JWT is stale until the next sign-in. The correct pattern is: Cognito verifies identity (who you are), the local DB provides authorization (what you can do). The `AuthProvider` now calls `/api/v1/users/me/permissions` after auth to get role from DB.  
**Action**: Update `dev-docs/devops/aws-cognito-setup.md` to explicitly document this separation. Remove any guidance to set `custom:role` Cognito attributes for new users.

### 5.2 All Frontend API Calls Must Use `apiClient` — Never Raw `fetch()`

**Learning**: Raw `fetch('/api/v1/...')` in the web app hits Next.js at port 3000, not FastAPI at port 8000, and does not attach the Cognito JWT. Every API call must use `apiClient` from `@pilot/shared-api` which: (1) has the correct `baseURL`, (2) attaches the JWT via interceptor, (3) handles 401/token-refresh.  
**Action**: Add an ESLint rule to ban `fetch('/api/v1'` in `packages/eslint-config/` to catch regressions. Update the React Engineer methods doc to call this out explicitly.

### 5.3 SSE Endpoints Require JWT as Query Param `?token=`

**Learning**: Browser `EventSource` cannot send `Authorization` headers. All backend SSE endpoints must accept `?token=JWT` as a query parameter for authentication. The frontend must fetch the Amplify JWT before opening the SSE connection and append it to the URL. `useSseChannel` currently does not handle this automatically — each consumer must do it manually (as `useDispatchSse` now does).  
**Action**: Consider adding a `getToken?: () => Promise<string>` prop to `useSseChannel` so the JWT-fetch pattern is centralized. Update `mvp-arch.md` §SSE to document the `?token=` pattern.

### 5.4 Next.js Requires API Proxy for Relative-Path `fetch()` Calls

**Learning**: If any code (legacy or new) uses relative `fetch('/api/v1/...')` calls instead of `apiClient`, they hit Next.js port 3000 and get 404. The `rewrites()` proxy in `next.config.ts` catches these and forwards to FastAPI. This is a safety net, not a replacement for using `apiClient`. Any change to `next.config.ts` requires a server restart.  
**Action**: Document in the frontend architecture doc that `next.config.ts` has a proxy and why, so future developers understand the two-layer system.

### 5.5 Expo Router Tab Hiding — Use `href: null`, Not Route Group Names

**Learning**: To hide auto-discovered routes from the Expo Router tab bar, use `<Tabs.Screen name="route/path" options={{ href: null }} />`. Route groups using `()` syntax (like `(home)`) are transparent to the tab navigator and must NOT be listed — adding them as Tabs.Screen entries causes navigation crashes. Only concrete file-based routes need explicit suppression.  
**Action**: Update mobile routing documentation / comments in `(tabs)/_layout.tsx` to explain this pattern for future maintenance.

### 5.6 Regex Bulk Migration Leaves Syntax Artifacts — Always Verify With Prettier

**Learning**: Automated regex-based code migrations (like the `fetch()` → `apiClient` migration) often leave orphaned syntax artifacts (stray `` );`); ``, double `;;`, orphaned error handler blocks) that pass a grep check but fail to parse. These only surface when Prettier or the TypeScript compiler runs. Always run `prettier --check` on all migrated files immediately after a bulk script migration.  
**Action**: Add a step to the engineering process checklist: after any bulk file migration, run `cd frontend && npx prettier --check "apps/web/src/features/**/*.ts"` before committing.

### 5.7 Backend API Endpoint URLs Do Not Match Frontend Assumptions

**Learning**: Multiple frontend hooks were built against assumed URL patterns that don't match the actual backend routes (e.g., `/api/v1/schedule/board` vs `/api/v1/scheduling/dispatch-board`; date param `?date=` vs `?start_date=&end_date=`). The `backend/openapi.json` is the authoritative source of truth for endpoint paths and parameter shapes.  
**Action**: Before wiring any new frontend hook, always verify the exact path + parameter schema from `backend/openapi.json`. Add a step to the React Engineer methods doc: "Run `python3 -c \"import json; spec=json.load(open('backend/openapi.json')); ...\"` to verify endpoint before coding the hook."

### 5.8 Dashboard Widget 403 — Wildcard Permission Matching Needs Verification

**Learning**: The `owner` role has `"*"` in its `tenant_user_role.permissions` array, which should match any permission via `has_permission()`. However, `GET /api/v1/dashboard/widgets/recent-customer-messages` (which requires `communications.view`) returns 403 for the owner. This suggests either a bug in the wildcard matching logic or a JWT/user resolution issue. Needs investigation before the 403 can be marked resolved.  
**Action**: Add a backend unit test that verifies `has_permission(["*"], "communications.view")` returns `True`. Also verify with a curl/Insomnia test that the JWT from `dev@pilot.local` Cognito resolves to the correct `tenant_user` row in the DB.
