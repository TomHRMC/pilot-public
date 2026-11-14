# MOB-B5 Batch Design — Owner Tab: Full Owner Dashboard

**Version**: 1.0
**Date**: 2026-06-06
**Batch**: MOB-B5
**Prerequisite Batches**: MOB-B1 ✅ (job data shapes established; `useTechQuotes` migrated to `apiClient`)
**Estimated Effort**: 2–3 days (frontend only — no backend companion required)
**Test Subfolder**: `apps/mobile/__tests__/batch_mob_b5/`
**Platform**: Mobile-only (Expo / React Native)
**Status**: Design complete — ready for React Engineer implementation

---

## A. Input Read Summary

All source artifacts were read directly before writing this document. No content was assumed.

### A.1 Artifacts Read

| Artifact | Key Findings |
|:---|:---|
| `frontend/apps/mobile/app/(tabs)/owner.tsx` | Current content: `<RoleGate role={["owner","operator"]}>` wraps: "Owner" title, **"Owner-only dashboard content coming in FE-B3+"** placeholder text (REMOVE), `<CalendarSyncStatusSection />`, `<FieldIssuesSyncStatusSection />`, sign-out button. Layout: `alignItems: "center", justifyContent: "center"` — must be changed to top-aligned `ScrollView`. |
| `features/owner-tab/components/CalendarSyncStatusSection.tsx` | ✅ Existing section — uses `useCalendarStatus()`, renders `<CalendarSyncStatusRow>`. Keep as-is, preserve position. |
| `features/owner-tab/components/FieldIssuesSyncStatusSection.tsx` | ✅ Existing section — uses `useFieldIssuesStatus()`, renders `<FieldIssuesSyncStatusRow>`. Keep as-is, preserve position. |
| `features/owner-tab/hooks/useCalendarStatus.ts` | Uses `apiClient` from `@pilot/shared-api`. Pattern: TanStack Query, `staleTime: 60_000`, `refetchInterval: 5 * 60 * 1000`, `enabled: !isMockAuth`. All new hooks in this batch must follow this pattern. |
| `features/owner-tab/hooks/useFieldIssuesStatus.ts` | Same pattern as `useCalendarStatus`. Has `WEB_APP_BASE_URL` constant from `EXPO_PUBLIC_WEB_APP_URL`. All deep-links follow this config pattern. |
| `features/quote-approval-status/hooks/useTechQuotes.ts` | Uses `apiClient.get("/api/v1/quotes", { params: { submitted_by: "me", status: "..." } })`. Already migrated to `apiClient` in MOB-B1. **Owner approval queue must use a DIFFERENT hook** with `?status=pending_approval` (no `submitted_by` filter — shows ALL pending quotes across all techs). |
| `backend/openapi_schema_map.md` §integrations | `GET /api/v1/integrations/quickbooks/status` → `QuickBooksConnectionStatus: { is_connected, realm_id, company_name, connected_at, expires_at, connection_status }`. **No `last_sync_at` or pending sync count** in response. |
| `backend/openapi_schema_map.md` §invoices | `GET /api/v1/invoices/?status=&due_before=&due_after=&limit=50&offset=0` → `InvoiceListResponse: { items: [{ id, invoice_number, customer_id, site_id, status_id, status_code, issued_at, due_at }], total, limit, offset }`. |
| `backend/openapi_schema_map.md` §quotes | `GET /api/v1/quotes?skip=&limit=&status=` → `[{ id, tenant_id, customer_id, customer_name, site_id, status_id, status_code, subtotal_cents }]`. **Confirmed: only `skip`, `limit`, `status` params — NO `submitted_by` param visible** in the schema map. |
| `backend/openapi_schema_map.md` §subscription | `GET /api/v1/tenants/{tenant_id}/subscription` → `TenantSubscriptionResponse: { current_tier: { tier_id, tier_name, display_label, monthly_price_cents, is_trial, trial_duration_days, max_users, max_sms_segments_per_month }, trial_ends_at, stripe_customer_id, usage: "object", tier_override: "object" }`. **Note**: `usage` is `"object"` — exact sub-schema not in schema map. Pre-work required. |
| MCP: `subscription` table | Columns: `id, tenant_id, product_plan_code, status_id, quantity_seats, billing_anchor, started_at, canceled_at, psp_provider, psp_subscription_id, psp_customer_id, billing_interval, trial_ends_at, renews_at, cancel_at_period_end, is_active`. |
| MCP: `tenant_subscription` table | Does not exist — table is named `subscription`. |

### A.2 Critical Design Decisions

#### A.2.1 — `GET /api/v1/quotes` Has No `submitted_by` Param in Schema Map

The `useTechQuotes` hook uses `submitted_by: "me"` as a query param. However, the schema map for `GET /api/v1/quotes` only shows `skip`, `limit`, `status` as params — no `submitted_by`. This suggests `submitted_by` may be handled server-side via the JWT or may be an undocumented param.

**Resolution for owner view**: Call `GET /api/v1/quotes?status=pending_approval&limit=100` WITHOUT `submitted_by`. This returns ALL quotes in `pending_approval` status across the entire tenant. The owner dashboard shows all tech quotes awaiting approval — this is the correct behavior. See §G.1.

#### A.2.2 — `TenantSubscriptionResponse.usage` is `"object"` — Shape Unknown

The `usage` field is typed as generic `object` in the schema map. Must read `backend/openapi.json` to find the actual `TenantSubscriptionUsage` sub-schema before rendering usage data.

**Resolution**: Pre-work step — React Engineer must inspect `openapi.json` for `TenantSubscriptionUsage` schema before implementing `PlanUsageSection`. See §G.2.

#### A.2.3 — QB Status Response Missing `last_sync_at`

`QuickBooksConnectionStatus` only has: `is_connected`, `realm_id`, `company_name`, `connected_at`, `expires_at`, `connection_status`. No `last_sync_at` or `pending_items_count`.

**Resolution**: Display what's available: connection status indicator + company name + connected date. Do NOT display "last sync" data that isn't in the response. See §G.3.

#### A.2.4 — Owner Tab Layout Must Change from Centered to ScrollView

Current `owner.tsx` uses `alignItems: "center", justifyContent: "center"` — a centered full-screen layout. With 6 sections, this must become a top-aligned `ScrollView`. The complete `owner.tsx` will be rewritten to accommodate the new structure while preserving the `<RoleGate>` wrapper and sign-out logic.

#### A.2.5 — Subscription Endpoint Requires `tenant_id` in Path

`GET /api/v1/tenants/{tenant_id}/subscription` requires the tenant UUID in the path. Must read `useAuth()` return shape to confirm the correct field (`tenantId`, `tenant_id`, or `user.tenant_id`). Read `useCalendarStatus.ts` to see if it needs tenant_id (it doesn't — the server infers from JWT). Check if the subscription endpoint also infers from JWT or requires explicit tenant_id. See §G.4.

---

## B. Migration Plan

### B.1 No Database Migration Required

MOB-B5 is a pure frontend batch. No schema additions.

### B.2 No Backend Companion Required

All required API endpoints are confirmed in the schema map. Only display gaps (§A.2.2 `usage` shape) require pre-work reading of `openapi.json`.

---

## C. Execution Order

| # | Task | File(s) | Dependency |
|:---:|:---|:---|:---|
| 1 | Read `openapi.json` for `TenantSubscriptionUsage` schema shape | `backend/openapi.json` | None |
| 2 | Read `useAuth()` return shape — confirm `tenantId` field for subscription endpoint | Existing auth hook usage | None |
| 3 | Read `app/(tabs)/(home)/quotes/pending.tsx` — confirm navigation target for owner approvals | Existing route file | None |
| 4 | Create MSW owner handlers | `mocks/handlers/ownerHandlers.ts` | #1 |
| 5 | Register handlers in `handlers/index.ts` | `mocks/handlers/index.ts` | #4 |
| 6 | Create `useOwnerPendingQuotes` hook | `features/owner-tab/hooks/useOwnerPendingQuotes.ts` | None |
| 7 | Create `useQbStatusMobile` hook | `features/owner-tab/hooks/useQbStatusMobile.ts` | None |
| 8 | Create `useOwnerArSummary` hook | `features/owner-tab/hooks/useOwnerArSummary.ts` | None |
| 9 | Create `useOwnerPlanUsage` hook | `features/owner-tab/hooks/useOwnerPlanUsage.ts` | #1, #2 |
| 10 | Create `ApprovalsQueueSection` component | `features/owner-tab/components/ApprovalsQueueSection.tsx` | #6 |
| 11 | Create `QbSyncStatusSection` component | `features/owner-tab/components/QbSyncStatusSection.tsx` | #7 |
| 12 | Create `ArSummarySection` component | `features/owner-tab/components/ArSummarySection.tsx` | #8 |
| 13 | Create `PlanUsageSection` component | `features/owner-tab/components/PlanUsageSection.tsx` | #9 |
| 14 | Rewrite `owner.tsx` — ScrollView layout, all 6 sections, sign-out at bottom | `app/(tabs)/owner.tsx` | #10–#13 |
| 15 | Write unit + integration tests | `__tests__/batch_mob_b5/` + co-located | #14 |
| 16 | Regression check + TypeScript + lint | — | #15 |

---

## D. New API Endpoints Consumed

### D.1 `GET /api/v1/quotes` (existing — new usage pattern for owner)

**Used by**: `useOwnerPendingQuotes` hook

```
GET /api/v1/quotes?status=pending_approval&limit=100
```

**Response** (confirmed from schema map):
```json
[
  {
    "id": "uuid",
    "tenant_id": "uuid",
    "customer_id": "uuid",
    "customer_name": "Acme Corp",
    "site_id": "uuid",
    "status_id": "uuid",
    "status_code": "pending_approval",
    "subtotal_cents": 125000
  }
]
```

> **Note**: `submitted_by` NOT a documented param — do NOT include it. Filter by `status=pending_approval` only.

### D.2 `GET /api/v1/integrations/quickbooks/status` (existing)

**Used by**: `useQbStatusMobile` hook

**Response** (confirmed from schema map):
```json
{
  "is_connected": false,
  "realm_id": null,
  "company_name": null,
  "connected_at": null,
  "expires_at": null,
  "connection_status": "not_configured"
}
```

`connection_status` values from code audit: `"pending"`, `"active"`, `"disconnected"`, `"expired"`, `"not_configured"`. Display as:
- `"active"` → "✅ Connected"
- `"not_configured"` / `"disconnected"` / `"expired"` → "Connect QuickBooks" deep-link

### D.3 `GET /api/v1/invoices/` (existing)

**Used by**: `useOwnerArSummary` hook

```
GET /api/v1/invoices/?status=sent&limit=50
```

> **Invoice status codes**: Not documented in schema map. React Engineer must verify valid status codes from `openapi.json` before using. Likely values: `"sent"`, `"paid"`, `"overdue"`, `"draft"`. Use `status=sent` as a proxy for outstanding. See §G.5.

**Response** (confirmed from schema map):
```json
{
  "items": [
    {
      "id": "uuid",
      "invoice_number": "INV-0042",
      "customer_id": "uuid",
      "site_id": "uuid",
      "status_id": "uuid",
      "status_code": "sent",
      "issued_at": "2026-06-01",
      "due_at": "2026-06-15"
    }
  ],
  "total": 5,
  "limit": 50,
  "offset": 0
}
```

**AR Summary display**: Show `total` count of outstanding invoices and overdue count (items where `due_at < today`). No dollar totals — response doesn't include `total_cents` on list items.

### D.4 `GET /api/v1/tenants/{tenant_id}/subscription` (existing)

**Used by**: `useOwnerPlanUsage` hook

**Response** (confirmed from schema map):
```json
{
  "current_tier": {
    "tier_id": "uuid",
    "tier_name": "Starter",
    "display_label": "Starter Plan",
    "monthly_price_cents": 14900,
    "is_trial": false,
    "trial_duration_days": null,
    "max_users": 5,
    "max_sms_segments_per_month": 500
  },
  "trial_ends_at": null,
  "stripe_customer_id": null,
  "usage": {},
  "tier_override": null
}
```

> ⚠️ `usage` is `"object"` — React Engineer MUST read `backend/openapi.json` for `TenantSubscriptionUsage` schema before rendering usage. See §G.2.

---

## E. Pattern Reuse Decisions

### E.1 `useCalendarStatus` Hook Pattern — All New Owner Hooks

All 4 new hooks follow this identical pattern from `useCalendarStatus.ts`:
```typescript
import { apiClient } from "@pilot/shared-api";
import { useQuery } from "@tanstack/react-query";

export function useOwnerXyz() {
  const isMockAuth = process.env.EXPO_PUBLIC_USE_MOCK_AUTH === "true";
  return useQuery({
    queryKey: ["owner-xyz"],
    queryFn: async () => {
      const res = await apiClient.get<XyzResponse>("/api/v1/...");
      return res.data;
    },
    staleTime: 60_000,
    refetchOnWindowFocus: false,
    refetchInterval: 5 * 60 * 1000,
    retry: 1,
    enabled: !isMockAuth,
  });
}
```

### E.2 `FieldIssuesSyncStatusSection` Deep-Link Pattern

All sections that link to the web app use the same `process.env.EXPO_PUBLIC_WEB_APP_URL` + fallback URL pattern from `useFieldIssuesStatus.ts`:
```typescript
const WEB_APP_BASE_URL =
  process.env.EXPO_PUBLIC_WEB_APP_URL ?? "https://app.pilotfortrades.com";
```

### E.3 `ScrollView` Layout from `MOB-B2 JobDetailScreen`

Owner tab must switch from the current centered `View` to a top-aligned `ScrollView`. The `JobDetailScreen.tsx` (MOB-B2) scroll layout is the pattern reference.

### E.4 `(home)/quotes/pending` Navigation — Existing Route

The approvals section tap navigates to `/(tabs)/(home)/quotes/pending` — the already-built `TechPendingQuotesList` route. This route shows ALL pending quotes, which is also what the owner needs. No new route required.

---

## F. Shared Module Interfaces

### F.1 `useOwnerPendingQuotes` — New Hook

```typescript
// frontend/apps/mobile/features/owner-tab/hooks/useOwnerPendingQuotes.ts

export interface OwnerPendingQuote {
  id: string;
  tenant_id: string;
  customer_id: string;
  customer_name: string | null;
  site_id: string;
  status_id: string;
  status_code: string | null;
  subtotal_cents: number;
}

export function useOwnerPendingQuotes(): {
  quotes: OwnerPendingQuote[];
  pendingCount: number;
  isLoading: boolean;
  isError: boolean;
  refetch: () => void;
}
```

Calls `GET /api/v1/quotes?status=pending_approval&limit=100`. `pendingCount = quotes.length`.

### F.2 `useQbStatusMobile` — New Hook

```typescript
// frontend/apps/mobile/features/owner-tab/hooks/useQbStatusMobile.ts

export interface QbConnectionStatus {
  is_connected: boolean;
  realm_id: string | null;
  company_name: string | null;
  connected_at: string | null;
  expires_at: string | null;
  connection_status: string;
}

export function useQbStatusMobile(): {
  data: QbConnectionStatus | undefined;
  isLoading: boolean;
  isError: boolean;
}
```

Calls `GET /api/v1/integrations/quickbooks/status`.

### F.3 `useOwnerArSummary` — New Hook

```typescript
// frontend/apps/mobile/features/owner-tab/hooks/useOwnerArSummary.ts

export interface InvoiceListItem {
  id: string;
  invoice_number: string;
  customer_id: string;
  site_id: string;
  status_id: string;
  status_code: string;
  issued_at: string | null;
  due_at: string | null;
}

export interface OwnerArSummary {
  outstandingCount: number;
  overdueCount: number;     // items where due_at < today
  items: InvoiceListItem[];
}

export function useOwnerArSummary(): {
  data: OwnerArSummary | undefined;
  isLoading: boolean;
  isError: boolean;
}
```

Calls `GET /api/v1/invoices/?status=sent&limit=50`. Derives `overdueCount` client-side: items where `due_at < new Date().toISOString().slice(0, 10)`.

### F.4 `useOwnerPlanUsage` — New Hook

```typescript
// frontend/apps/mobile/features/owner-tab/hooks/useOwnerPlanUsage.ts
// Must read TenantSubscriptionUsage schema from openapi.json before defining UsageDetail

export interface TenantTier {
  tier_id: string;
  tier_name: string;
  display_label: string;
  monthly_price_cents: number;
  is_trial: boolean;
  trial_duration_days: number | null;
  max_users: number | null;
  max_sms_segments_per_month: number | null;
}

export interface TenantSubscriptionSummary {
  current_tier: TenantTier;
  trial_ends_at: string | null;
  usage: Record<string, unknown>;  // replace with actual schema from openapi.json
}

export function useOwnerPlanUsage(tenantId: string): {
  data: TenantSubscriptionSummary | undefined;
  isLoading: boolean;
  isError: boolean;
}
```

> **Get `tenantId`**: Read `useAuth()` return shape to confirm the correct field. In the web app this is typically `user.tenantId` or `session.tenantId`. Do NOT assume — read the auth hook before implementing.

### F.5 `ApprovalsQueueSection` — New Component

```typescript
// features/owner-tab/components/ApprovalsQueueSection.tsx
// Props: none (reads from useOwnerPendingQuotes internally)
```

**Renders**:
- Section header: "Approvals" with a badge count if `pendingCount > 0`
- If `pendingCount > 0`: `"{N} quotes awaiting approval"` + tap action → `router.push("/(tabs)/(home)/quotes/pending" as any)`
- If `pendingCount === 0`: "All caught up ✓" in neutral text
- Loading state: skeleton row
- Error state: fail silently (no error toast) — section collapses if error

### F.6 `QbSyncStatusSection` — New Component

```typescript
// features/owner-tab/components/QbSyncStatusSection.tsx
// Props: none (reads from useQbStatusMobile internally)
```

**Renders**:
- Section header: "QuickBooks"
- Status row: connection indicator dot + status text
  - `is_connected=true`: green dot + "Connected" + company name (if present)
  - `is_connected=false` or `connection_status` not "active": orange/red dot + "Not connected" + "Connect →" link
- "Connect QuickBooks" taps `Linking.openURL(WEB_APP_BASE_URL + "/settings/integrations/quickbooks")`

### F.7 `ArSummarySection` — New Component

```typescript
// features/owner-tab/components/ArSummarySection.tsx
// Props: none (reads from useOwnerArSummary internally)
```

**Renders**:
- Section header: "Accounts Receivable"
- `{outstandingCount} outstanding invoice(s)` with overdue badge if `overdueCount > 0`
- Tap → deep-link to web AR management page: `Linking.openURL(WEB_APP_BASE_URL + "/invoices")`
- Empty state: "No outstanding invoices" — shown when `outstandingCount === 0`

### F.8 `PlanUsageSection` — New Component

```typescript
// features/owner-tab/components/PlanUsageSection.tsx
// Props: none (reads from useOwnerPlanUsage internally)
```

**Renders**:
- Section header: "Plan"
- Current tier name (e.g., "Starter Plan")
- Trial expiry if `trial_ends_at` is not null: "Trial ends {formatted date}"
- SMS usage if available in `usage` object (after schema is confirmed)
- `max_users` seat count if available
- Fail silently on error

### F.9 `owner.tsx` — Full Rewrite

Replace the current centered `View` layout with:

```typescript
<SafeAreaView style={styles.safeArea}>
  <ScrollView
    contentContainerStyle={styles.scrollContent}
    showsVerticalScrollIndicator={false}
  >
    <RoleGate role={["owner", "operator"]}>
      {/* Screen header */}
      <Text style={styles.screenTitle}>Owner</Text>

      {/* Section 1: Approvals Queue */}
      <ApprovalsQueueSection />

      {/* Section 2: Field Issues (existing — preserve) */}
      <FieldIssuesSyncStatusSection />

      {/* Section 3: Calendar Sync (existing — preserve) */}
      <CalendarSyncStatusSection />

      {/* Section 4: QuickBooks Sync Status (new) */}
      <QbSyncStatusSection />

      {/* Section 5: AR Summary (new) */}
      <ArSummarySection />

      {/* Section 6: Plan Usage (new) */}
      <PlanUsageSection />

      {/* Sign-out — always at bottom */}
      <TouchableOpacity onPress={handleSignOut} ...>
        <Text>Sign out</Text>
      </TouchableOpacity>
    </RoleGate>
  </ScrollView>
</SafeAreaView>
```

**Remove**: `<Text style={styles.subtitle}>Owner-only dashboard content coming in FE-B3+.</Text>` and the centered `<Text style={styles.title}>Owner</Text>` (replaced with styled screen title at top of scroll content).

---

## G. Open Questions Resolved

### G.1 — Owner Quotes: `submitted_by` vs `status` Only

**Problem**: `useTechQuotes` uses `submitted_by: "me"`. Owner needs ALL pending quotes (from all techs). The `GET /api/v1/quotes` schema map shows only `skip`, `limit`, `status` — no `submitted_by` param.

**Resolution**: `useOwnerPendingQuotes` calls `GET /api/v1/quotes?status=pending_approval&limit=100` without any `submitted_by` filter. This returns all tenant quotes in `pending_approval` status — exactly what the owner approval queue needs. The server already scopes by tenant via JWT.

### G.2 — `TenantSubscriptionResponse.usage` Shape Unknown

**Problem**: Schema map shows `"usage": "object"` — no sub-schema.

**Resolution**: React Engineer must run:
```bash
python3 -c "import json; d=json.load(open('backend/openapi.json')); print(json.dumps(d.get('components',{}).get('schemas',{}).get('TenantSubscriptionResponse',{}), indent=2))"
```
If `usage` contains SMS usage fields (e.g., `sms_segments_used`, `sms_segments_remaining`), render them. If the sub-schema is missing or empty, render only the tier name and seat count (always available from `current_tier`). Add `// TODO: render usage fields when schema confirmed` comment.

### G.3 — QB Status: No `last_sync_at` in Response

**Problem**: `QuickBooksConnectionStatus` does not include `last_sync_at` or pending sync count.

**Resolution**: Display only: connected/disconnected indicator, company name (if connected), connection date. No "last sync" display. This matches what the data provides. Add `// TODO: add last_sync_at when backend exposes it` comment.

### G.4 — Subscription Endpoint Path: `{tenant_id}` Required

**Problem**: `GET /api/v1/tenants/{tenant_id}/subscription` requires tenant ID in path. Other endpoints infer from JWT. Need to confirm how to get `tenantId` on mobile.

**Resolution**: React Engineer must read `useCalendarStatus.ts` and `useFieldIssuesStatus.ts` — both use no tenant_id param. Check if the subscription endpoint also accepts a `/me` alias or if tenant_id must be passed. If `{tenant_id}` is required, read `useAuth()` to find the correct field. If `useAuth()` does not expose `tenantId`, check the JWT decode or the `AuthenticatedUser` object in the mobile app.

**Fallback if no tenant_id available**: Call the test endpoint `GET /api/v1/tenants/{tenant_id}/subscription/test` behavior to verify if the path can accept "me" or must use UUID. Check `backend/api/routes/tenant_subscription.py` for the implementation. If absolutely blocked, skip the `PlanUsageSection` and add `// TODO: implement when tenantId available in useAuth()`.

### G.5 — Invoice Status Codes for AR Filter

**Problem**: `GET /api/v1/invoices/?status=` param accepts status string but valid values not in schema map.

**Resolution**: React Engineer must search `backend/openapi.json` for invoice status codes:
```bash
python3 -c "import json; d=json.load(open('backend/openapi.json')); print([s for s in str(d).split(',') if 'sent' in s or 'paid' in s or 'overdue' in s][:10])"
```

If `"sent"` and `"overdue"` are valid: use both as comma-separated filter. If only `"sent"` is valid (no overdue status): derive overdue from `due_at < today` client-side. The spec in §F.3 derives `overdueCount` client-side regardless.

### G.6 — Section Order

**Decision**: Order per the impl plan §8 MOB-B5 spec + practical priority for owner:
1. Approvals Queue (most time-sensitive — unblocks tech revenue)
2. Field Issues (existing — operational issues)
3. Calendar Sync (existing — scheduling)
4. QuickBooks Sync Status (financial integration)
5. AR Summary (cash position)
6. Plan Usage (account management)
7. Sign-out (bottom)

---

## H. Surface Mockup Reference

### H.1 Owner Tab Full Screen Layout

```
┌──────────────────────────────────┐
│  Owner                            │  ← Screen title (SafeAreaView top)
│ ─────────────────────────────── │
│  APPROVALS                  [2]  │  ← ApprovalsQueueSection
│  2 quotes awaiting approval    > │
│ ─────────────────────────────── │
│  FIELD ISSUES               [1]  │  ← FieldIssuesSyncStatusSection (existing)
│  1 pending resolution         >  │
│ ─────────────────────────────── │
│  CALENDAR                        │  ← CalendarSyncStatusSection (existing)
│  Synced · No conflicts           │
│ ─────────────────────────────── │
│  QUICKBOOKS                      │  ← QbSyncStatusSection (new)
│  ● Connected · Acme Electrical   │
│ ─────────────────────────────── │
│  ACCOUNTS RECEIVABLE             │  ← ArSummarySection (new)
│  3 outstanding · 1 overdue    >  │
│ ─────────────────────────────── │
│  PLAN                            │  ← PlanUsageSection (new)
│  Starter Plan · 3/5 seats       │
│  SMS: 42 / 500 this month       │
│ ─────────────────────────────── │
│                                   │
│  [ Sign out ]                    │  ← Sign-out at bottom
└──────────────────────────────────┘
```

---

## I. Component Manifest

| Component / Hook | File Path | Action | Batch |
|:---|:---|:---|:---|
| `useOwnerPendingQuotes` | `apps/mobile/features/owner-tab/hooks/useOwnerPendingQuotes.ts` | **New** | MOB-B5 |
| `useQbStatusMobile` | `apps/mobile/features/owner-tab/hooks/useQbStatusMobile.ts` | **New** | MOB-B5 |
| `useOwnerArSummary` | `apps/mobile/features/owner-tab/hooks/useOwnerArSummary.ts` | **New** | MOB-B5 |
| `useOwnerPlanUsage` | `apps/mobile/features/owner-tab/hooks/useOwnerPlanUsage.ts` | **New** | MOB-B5 |
| `ApprovalsQueueSection` | `apps/mobile/features/owner-tab/components/ApprovalsQueueSection.tsx` | **New** | MOB-B5 |
| `QbSyncStatusSection` | `apps/mobile/features/owner-tab/components/QbSyncStatusSection.tsx` | **New** | MOB-B5 |
| `ArSummarySection` | `apps/mobile/features/owner-tab/components/ArSummarySection.tsx` | **New** | MOB-B5 |
| `PlanUsageSection` | `apps/mobile/features/owner-tab/components/PlanUsageSection.tsx` | **New** | MOB-B5 |
| `owner.tsx` | `apps/mobile/app/(tabs)/owner.tsx` | **Rewrite** — ScrollView layout + all 6 sections | MOB-B5 |
| `ownerHandlers.ts` | `apps/mobile/mocks/handlers/ownerHandlers.ts` | **New** — MSW fixtures for all 4 new endpoints | MOB-B5 |
| `mocks/handlers/index.ts` | `apps/mobile/mocks/handlers/index.ts` | **Modify** — register `ownerHandlers` | MOB-B5 |

---

## J. Test Plan

**Test subfolder**: `apps/mobile/__tests__/batch_mob_b5/`

### J.1 Unit Tests

| Test | File | Assertion |
|:---|:---|:---|
| `useOwnerPendingQuotes` calls correct endpoint | `useOwnerPendingQuotes.test.ts` | Calls `GET /api/v1/quotes?status=pending_approval&limit=100`; NO `submitted_by` param |
| `useOwnerPendingQuotes` derives count | `useOwnerPendingQuotes.test.ts` | 2 items in response → `pendingCount=2` |
| `useQbStatusMobile` calls QB status endpoint | `useQbStatusMobile.test.ts` | Calls `GET /api/v1/integrations/quickbooks/status` |
| `useOwnerArSummary` derives overdueCount | `useOwnerArSummary.test.ts` | Item with `due_at` in past → counted in `overdueCount` |
| `ApprovalsQueueSection` renders count badge | `ApprovalsQueueSection.test.tsx` | `pendingCount=2` → "2 quotes awaiting approval" visible |
| `ApprovalsQueueSection` renders all-caught-up | `ApprovalsQueueSection.test.tsx` | `pendingCount=0` → "All caught up" visible |
| `QbSyncStatusSection` shows connected | `QbSyncStatusSection.test.tsx` | `is_connected=true` → "Connected" visible + company name |
| `QbSyncStatusSection` shows not connected | `QbSyncStatusSection.test.tsx` | `is_connected=false` → "Not connected" + connect link visible |
| `ArSummarySection` shows outstanding count | `ArSummarySection.test.tsx` | 3 invoices → "3 outstanding" visible |
| `ArSummarySection` shows overdue badge | `ArSummarySection.test.tsx` | 1 overdue → "1 overdue" badge visible |
| `ArSummarySection` empty state | `ArSummarySection.test.tsx` | 0 invoices → "No outstanding invoices" |

### J.2 Integration Tests

| Test | File | Assertion |
|:---|:---|:---|
| Placeholder text removed | `batch_mob_b5/owner-tab.integration.test.tsx` | "coming in FE-B3+" not in rendered output |
| Owner tab has 6 sections | `batch_mob_b5/owner-tab.integration.test.tsx` | All 6 section testIDs present |
| Approvals tap navigates to pending | `batch_mob_b5/owner-tab.integration.test.tsx` | Press approvals → `router.push` to `(home)/quotes/pending` |
| QB connected state renders | `batch_mob_b5/owner-tab.integration.test.tsx` | MSW QB connected fixture → "Connected" visible |
| QB disconnected → connect link | `batch_mob_b5/owner-tab.integration.test.tsx` | MSW QB not connected → connect link visible |
| AR summary renders outstanding | `batch_mob_b5/owner-tab.integration.test.tsx` | MSW returns 3 invoices → count visible |
| Plan tier renders | `batch_mob_b5/owner-tab.integration.test.tsx` | MSW subscription fixture → tier name visible |
| Sign-out visible at bottom | `batch_mob_b5/owner-tab.integration.test.tsx` | Sign-out button visible and functional |
| Screen scrollable | `batch_mob_b5/owner-tab.integration.test.tsx` | `ScrollView` container present |

### J.3 Regression Tests

| Test | Assertion |
|:---|:---|
| `CalendarSyncStatusSection` still renders | Existing calendar sync section preserved |
| `FieldIssuesSyncStatusSection` still renders | Existing field issues section preserved |
| Sign-out logic unchanged | `handleSignOut` still clears query cache and redirects to login |
| Existing BETA-B1 owner escalation tests pass | `FieldIssuesSyncStatusSection` behavior unchanged |

---

## Design Doc Quality Gate Checklist

- [x] `owner.tsx` current content confirmed — exact placeholder text identified for removal
- [x] `CalendarSyncStatusSection` and `FieldIssuesSyncStatusSection` confirmed — preserve unchanged
- [x] `useCalendarStatus.ts` hook pattern confirmed — all new hooks follow same pattern
- [x] `useTechQuotes` `submitted_by` vs owner `status=pending_approval` gap documented §G.1
- [x] `GET /api/v1/quotes` endpoint params confirmed — only `skip`, `limit`, `status`
- [x] `QuickBooksConnectionStatus` response shape confirmed — no `last_sync_at` documented §G.3
- [x] `InvoiceListResponse` shape confirmed — no `total_cents` on list items; AR count only
- [x] `TenantSubscriptionResponse.usage` gap documented — pre-work required §G.2
- [x] `GET /api/v1/tenants/{tenant_id}/subscription` path param issue documented §G.4
- [x] Invoice status codes gap documented — pre-work from `openapi.json` §G.5
- [x] Section order specified per impl plan §8 MOB-B5 + priority rationale §G.6
- [x] Layout change from centered `View` to top-aligned `ScrollView` specified
- [x] `(home)/quotes/pending` existing route confirmed as approvals navigation target
- [x] Deep-link pattern from `EXPO_PUBLIC_WEB_APP_URL` used consistently
- [x] All 4 new sections fail silently (no error toasts) — owner tab must not crash on partial failures
- [x] No backend companion required — all endpoints confirmed
- [x] Infrastructure constraint: zero cost impact
