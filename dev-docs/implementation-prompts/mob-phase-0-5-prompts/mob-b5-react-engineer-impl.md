# Implementation Prompt: MOB-B5 — Owner Tab: Full Owner Dashboard

**Mode**: Pilot React Engineer
**Batch**: MOB-B5
**Source plan**: `dev-docs/analysis/pilot-app-beta-fixes-v2-impl-plan.md` §8 MOB-B5
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-mob-b5-design.md`
**Estimated session**: 2–3 days
**Platform**: Mobile only (`apps/mobile`)
**Backend companion**: None required — all endpoints exist
**Prerequisites**: MOB-B1 ✅ complete (job data shapes, `useTechQuotes` migrated)

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:
- **`dev-docs/architecture-design/batch-designs/batch-mob-b5-design.md`** — every section (A–J)
- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full

Critical rules for this batch:
- **Rule A**: Verify all API endpoint shapes from `openapi_schema_map.md`. The QB status response has NO `last_sync_at` — do not display data that isn't in the response.
- **Rule C**: All API calls use `apiClient` from `@pilot/shared-api` — not raw `fetch()`.
- **Rule D**: Read every source file before editing it. `owner.tsx` is a complete rewrite — read it first.
- **Preserve** existing `CalendarSyncStatusSection` and `FieldIssuesSyncStatusSection` — do not modify their hooks or internals.

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter mobile test 2>&1 | tail -8
```

Record the exact test count before any changes.

---

## Pre-Work: Read These Files First

```bash
# Confirm current owner.tsx content
cat frontend/apps/mobile/app/(tabs)/owner.tsx

# Existing sections to preserve
cat frontend/apps/mobile/features/owner-tab/components/CalendarSyncStatusSection.tsx
cat frontend/apps/mobile/features/owner-tab/components/FieldIssuesSyncStatusSection.tsx

# Hook pattern reference — follow exactly for new hooks
cat frontend/apps/mobile/features/owner-tab/hooks/useCalendarStatus.ts
cat frontend/apps/mobile/features/owner-tab/hooks/useFieldIssuesStatus.ts

# Verify pending quotes navigation target
cat frontend/apps/mobile/app/(tabs)/(home)/quotes/pending.tsx

# Check useAuth return shape — needed for tenant_id in subscription endpoint
# Read where useAuth is used and what fields it exposes
grep -rn "useAuth\(\)" frontend/apps/mobile/features/ | head -10

# MSW handler registration pattern
cat frontend/apps/mobile/mocks/handlers/index.ts

# Verify invoice status codes and subscription usage schema from openapi.json
python3 -c "import json; d=json.load(open('backend/openapi.json')); print(json.dumps(d.get('components',{}).get('schemas',{}).get('TenantSubscriptionResponse',{}), indent=2))"
python3 -c "import json; d=json.load(open('backend/openapi.json')); [print(k) for k in d.get('components',{}).get('schemas',{}).keys() if 'invoice' in k.lower() or 'Invoice' in k]"
```

---

## Context: What This Batch Does

Rewrites `owner.tsx` to a full owner dashboard — removes the "coming in FE-B3+" placeholder, adds 4 new sections, converts from centered layout to scrollable, and moves sign-out to the bottom.

| Item | Change |
|---|---|
| `owner.tsx` | **Full rewrite** — ScrollView layout + 6 sections + sign-out at bottom |
| Remove | `<Text>Owner-only dashboard content coming in FE-B3+.</Text>` + centered title |
| Keep | `CalendarSyncStatusSection`, `FieldIssuesSyncStatusSection`, sign-out logic |
| New: `useOwnerPendingQuotes` | `GET /api/v1/quotes?status=pending_approval&limit=100` |
| New: `useQbStatusMobile` | `GET /api/v1/integrations/quickbooks/status` |
| New: `useOwnerArSummary` | `GET /api/v1/invoices/?status=sent&limit=50` |
| New: `useOwnerPlanUsage` | `GET /api/v1/tenants/{tenantId}/subscription` |
| New: `ApprovalsQueueSection` | Pending quote count + navigate to `(home)/quotes/pending` |
| New: `QbSyncStatusSection` | QB connected/disconnected status + deep-link |
| New: `ArSummarySection` | Outstanding invoice count + overdue badge |
| New: `PlanUsageSection` | Tier name + trial status + usage |
| New: `ownerHandlers.ts` | MSW fixtures for all 4 new endpoints |

---

## Step 0: Create MSW Owner Handlers

**File**: `frontend/apps/mobile/mocks/handlers/ownerHandlers.ts`

Read `mocks/handlers/jobsHandlers.ts` and `mocks/handlers/jobDetailHandlers.ts` for the pattern. The handler must cover:

```typescript
// GET /api/v1/quotes?status=pending_approval — return 2 quotes
// GET /api/v1/integrations/quickbooks/status — return connected fixture AND disconnected fixture
//   (use different query params or path to distinguish in tests)
// GET /api/v1/invoices/ — return 3 invoices, 1 with due_at in past
// GET /api/v1/tenants/:tenantId/subscription — TenantSubscriptionResponse fixture
```

Register in `mocks/handlers/index.ts`:
```typescript
import { ownerHandlers } from "./ownerHandlers";
// Add comment: // MOB-B5: Owner dashboard sections
// Add: ...ownerHandlers
```

---

## Step 1: Create `useOwnerPendingQuotes` Hook

**File**: `frontend/apps/mobile/features/owner-tab/hooks/useOwnerPendingQuotes.ts`

Follow the exact pattern from `useCalendarStatus.ts` — same `staleTime`, `refetchInterval`, `enabled: !isMockAuth`:

```typescript
import { apiClient } from "@pilot/shared-api";
import { useQuery } from "@tanstack/react-query";

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

export function useOwnerPendingQuotes() {
  const isMockAuth = process.env.EXPO_PUBLIC_USE_MOCK_AUTH === "true";
  const query = useQuery({
    queryKey: ["owner-pending-quotes"],
    queryFn: async () => {
      const res = await apiClient.get<OwnerPendingQuote[]>("/api/v1/quotes", {
        params: { status: "pending_approval", limit: 100 },
        // NOTE: NO submitted_by param — owner sees ALL pending quotes
      });
      return res.data;
    },
    staleTime: 60_000,
    refetchOnWindowFocus: false,
    refetchInterval: 5 * 60 * 1000,
    retry: 1,
    enabled: !isMockAuth,
  });

  return {
    quotes: query.data ?? [],
    pendingCount: query.data?.length ?? 0,
    isLoading: query.isLoading,
    isError: query.isError,
    refetch: query.refetch,
  };
}
```

---

## Step 2: Create `useQbStatusMobile` Hook

**File**: `frontend/apps/mobile/features/owner-tab/hooks/useQbStatusMobile.ts`

```typescript
export interface QbConnectionStatus {
  is_connected: boolean;
  realm_id: string | null;
  company_name: string | null;
  connected_at: string | null;
  expires_at: string | null;
  connection_status: string;
}

export function useQbStatusMobile() {
  const isMockAuth = process.env.EXPO_PUBLIC_USE_MOCK_AUTH === "true";
  return useQuery({
    queryKey: ["qb-status-mobile"],
    queryFn: async () => {
      const res = await apiClient.get<QbConnectionStatus>(
        "/api/v1/integrations/quickbooks/status"
      );
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

---

## Step 3: Create `useOwnerArSummary` Hook

**File**: `frontend/apps/mobile/features/owner-tab/hooks/useOwnerArSummary.ts`

```typescript
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

// NOTE: Before using "status=sent", verify valid invoice status codes from openapi.json
// Run: python3 -c "import json; ..." (see pre-work step above)

export function useOwnerArSummary() {
  const isMockAuth = process.env.EXPO_PUBLIC_USE_MOCK_AUTH === "true";
  const todayStr = new Date().toISOString().slice(0, 10);

  const query = useQuery({
    queryKey: ["owner-ar-summary"],
    queryFn: async () => {
      const res = await apiClient.get<{ items: InvoiceListItem[]; total: number }>(
        "/api/v1/invoices/",
        { params: { status: "sent", limit: 50 } }
      );
      const items = res.data.items;
      const overdueCount = items.filter(
        (inv) => inv.due_at !== null && inv.due_at < todayStr
      ).length;
      return {
        outstandingCount: res.data.total,
        overdueCount,
        items,
      };
    },
    staleTime: 60_000,
    refetchOnWindowFocus: false,
    refetchInterval: 5 * 60 * 1000,
    retry: 1,
    enabled: !isMockAuth,
  });

  return query;
}
```

---

## Step 4: Create `useOwnerPlanUsage` Hook

**File**: `frontend/apps/mobile/features/owner-tab/hooks/useOwnerPlanUsage.ts`

**Before implementing**: Verify the `TenantSubscriptionResponse.usage` shape from `openapi.json` (pre-work step). Also verify how to get `tenantId`:

```bash
# Check what useAuth() exposes on mobile
grep -rn "useAuth" frontend/apps/mobile/app/(tabs)/owner.tsx
# Look at how tenantId is available in the app
grep -rn "tenantId\|tenant_id" frontend/apps/mobile/features/ | grep -v ".test." | head -10
```

```typescript
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
  stripe_customer_id: string | null;
  usage: Record<string, unknown>;  // TODO: replace with typed schema after pre-work
  tier_override: Record<string, unknown> | null;
}

export function useOwnerPlanUsage() {
  const { user } = useAuth();  // Read useAuth shape first — verify field name
  const tenantId = user?.tenantId ?? user?.tenant_id ?? null;  // adjust to actual field
  const isMockAuth = process.env.EXPO_PUBLIC_USE_MOCK_AUTH === "true";

  return useQuery({
    queryKey: ["owner-plan-usage", tenantId],
    queryFn: async () => {
      if (!tenantId) throw new Error("No tenantId available");
      const res = await apiClient.get<TenantSubscriptionSummary>(
        `/api/v1/tenants/${tenantId}/subscription`
      );
      return res.data;
    },
    staleTime: 5 * 60_000,  // 5 minutes — plan info changes rarely
    refetchOnWindowFocus: false,
    retry: 0,  // Fail silently if not implemented / no tenantId
    enabled: !isMockAuth && !!tenantId,
  });
}
```

> **If `tenantId` is not available from `useAuth()`**: Add `retry: 0, enabled: false` and render `PlanUsageSection` with a placeholder `// TODO: wire tenantId` comment. Do not block the batch on this.

---

## Step 5: Create `ApprovalsQueueSection`

**File**: `frontend/apps/mobile/features/owner-tab/components/ApprovalsQueueSection.tsx`

```typescript
import { router } from "expo-router";
import { useOwnerPendingQuotes } from "../hooks/useOwnerPendingQuotes";

export function ApprovalsQueueSection() {
  const { pendingCount, isLoading } = useOwnerPendingQuotes();

  const handlePress = () => {
    router.push("/(tabs)/(home)/quotes/pending" as any);
  };

  if (isLoading) {
    return <OwnerSectionSkeleton testID="approvals-loading" />;
  }

  return (
    <Pressable
      onPress={handlePress}
      testID="approvals-queue-section"
      accessibilityRole="button"
    >
      <View style={styles.row}>
        <View style={styles.labelRow}>
          <Text style={styles.sectionLabel}>Approvals</Text>
          {pendingCount > 0 && (
            <View style={styles.badge}>
              <Text style={styles.badgeText}>{pendingCount}</Text>
            </View>
          )}
        </View>
        {pendingCount > 0 ? (
          <Text style={styles.valueText}>{pendingCount} quotes awaiting approval</Text>
        ) : (
          <Text style={styles.allCaughtUp}>All caught up ✓</Text>
        )}
        <IconSymbol name="chevron.right" size={16} color={colors.neutral[400]} />
      </View>
    </Pressable>
  );
}
```

---

## Step 6: Create `QbSyncStatusSection`

**File**: `frontend/apps/mobile/features/owner-tab/components/QbSyncStatusSection.tsx`

```typescript
import { Linking } from "react-native";
import { useQbStatusMobile } from "../hooks/useQbStatusMobile";

const WEB_APP_BASE_URL =
  process.env.EXPO_PUBLIC_WEB_APP_URL ?? "https://app.pilotfortrades.com";

export function QbSyncStatusSection() {
  const { data: qb, isLoading } = useQbStatusMobile();

  const isConnected = qb?.is_connected === true && qb.connection_status === "active";

  const handleConnectPress = () => {
    void Linking.openURL(`${WEB_APP_BASE_URL}/settings/integrations/quickbooks`);
  };

  if (isLoading) return <OwnerSectionSkeleton testID="qb-loading" />;

  return (
    <View style={styles.row} testID="qb-sync-status-section">
      <Text style={styles.sectionLabel}>QuickBooks</Text>
      {isConnected ? (
        <View style={styles.statusRow}>
          <View style={[styles.dot, styles.dotGreen]} />
          <Text style={styles.valueText}>
            Connected{qb?.company_name ? ` · ${qb.company_name}` : ""}
          </Text>
          {/* NOTE: No last_sync_at in QB status response — do NOT display it */}
        </View>
      ) : (
        <Pressable onPress={handleConnectPress} testID="qb-connect-link">
          <View style={styles.statusRow}>
            <View style={[styles.dot, styles.dotOrange]} />
            <Text style={styles.linkText}>Not connected — Connect →</Text>
          </View>
        </Pressable>
      )}
    </View>
  );
}
```

---

## Step 7: Create `ArSummarySection`

**File**: `frontend/apps/mobile/features/owner-tab/components/ArSummarySection.tsx`

```typescript
export function ArSummarySection() {
  const { data, isLoading } = useOwnerArSummary();

  const handlePress = () => {
    void Linking.openURL(`${WEB_APP_BASE_URL}/invoices`);
  };

  if (isLoading) return <OwnerSectionSkeleton testID="ar-loading" />;

  const outstandingCount = data?.outstandingCount ?? 0;
  const overdueCount = data?.overdueCount ?? 0;

  if (outstandingCount === 0) {
    return (
      <View style={styles.row} testID="ar-summary-section">
        <Text style={styles.sectionLabel}>Accounts Receivable</Text>
        <Text style={styles.allCaughtUp}>No outstanding invoices</Text>
      </View>
    );
  }

  return (
    <Pressable onPress={handlePress} testID="ar-summary-section">
      <View style={styles.row}>
        <Text style={styles.sectionLabel}>Accounts Receivable</Text>
        <View style={styles.countRow}>
          <Text style={styles.valueText}>{outstandingCount} outstanding</Text>
          {overdueCount > 0 && (
            <View style={styles.overdueBadge}>
              <Text style={styles.overdueBadgeText}>{overdueCount} overdue</Text>
            </View>
          )}
        </View>
      </View>
    </Pressable>
  );
}
```

---

## Step 8: Create `PlanUsageSection`

**File**: `frontend/apps/mobile/features/owner-tab/components/PlanUsageSection.tsx`

Display available fields — fail silently if hook returns no data.

```typescript
export function PlanUsageSection() {
  const { data, isLoading } = useOwnerPlanUsage();

  if (isLoading) return <OwnerSectionSkeleton testID="plan-loading" />;
  if (!data) return null; // Fail silently — plan section is non-critical

  const tier = data.current_tier;
  const trialEndsAt = data.trial_ends_at
    ? new Date(data.trial_ends_at).toLocaleDateString()
    : null;

  return (
    <View style={styles.row} testID="plan-usage-section">
      <Text style={styles.sectionLabel}>Plan</Text>
      <Text style={styles.valueText}>{tier.display_label}</Text>
      {trialEndsAt && (
        <Text style={styles.trialText}>Trial ends {trialEndsAt}</Text>
      )}
      {/* TODO: render usage fields (sms_segments_used etc.) when schema confirmed from openapi.json */}
    </View>
  );
}
```

---

## Step 9: Rewrite `owner.tsx`

**File**: `frontend/apps/mobile/app/(tabs)/owner.tsx`

Read the file first. Complete rewrite — key changes:
1. Switch from `View` (centered) to `SafeAreaView` + `ScrollView`
2. Remove placeholder text (`"Owner-only dashboard content coming in FE-B3+"`) and centered title
3. Add "Owner" as styled screen header at top of scroll content
4. Compose all 6 sections in order (per design doc §G.6)
5. Move sign-out to bottom of ScrollView
6. Keep `useRouter`, `useQueryClient`, `useAuth`, `handleSignOut` — unchanged logic

```typescript
import React from "react";
import {
  View,
  Text,
  TouchableOpacity,
  ScrollView,
  SafeAreaView,
  StyleSheet,
} from "react-native";
import { useRouter } from "expo-router";
import { useQueryClient } from "@tanstack/react-query";
import { RoleGate } from "@pilot/ui/role-gate";
import { useAuth } from "@pilot/ui/auth";
import { tokens, fontWeights } from "@/constants/style-constants";
import { lightTheme } from "@pilot/ui/tokens";

// Existing sections (preserve — do not modify internals)
import { CalendarSyncStatusSection } from "@/features/owner-tab/components/CalendarSyncStatusSection";
import { FieldIssuesSyncStatusSection } from "@/features/owner-tab/components/FieldIssuesSyncStatusSection";

// New sections (MOB-B5)
import { ApprovalsQueueSection } from "@/features/owner-tab/components/ApprovalsQueueSection";
import { QbSyncStatusSection } from "@/features/owner-tab/components/QbSyncStatusSection";
import { ArSummarySection } from "@/features/owner-tab/components/ArSummarySection";
import { PlanUsageSection } from "@/features/owner-tab/components/PlanUsageSection";

export default function OwnerTab() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { signOut } = useAuth();

  const handleSignOut = async () => {
    queryClient.clear();
    await signOut();
    router.replace("/(auth)/login");
  };

  return (
    <SafeAreaView style={styles.safeArea} testID="owner-tab-screen">
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <RoleGate role={["owner", "operator"]}>
          <Text style={styles.screenTitle}>Owner</Text>
          {/* NOTE: "coming in FE-B3+" placeholder REMOVED */}

          <ApprovalsQueueSection />
          <FieldIssuesSyncStatusSection />
          <CalendarSyncStatusSection />
          <QbSyncStatusSection />
          <ArSummarySection />
          <PlanUsageSection />

          {/* Sign-out always at bottom */}
          <TouchableOpacity
            onPress={() => void handleSignOut()}
            accessibilityLabel="Sign out"
            testID="signout-button"
            style={styles.signOutButton}
            activeOpacity={0.7}
          >
            <Text style={styles.signOutText}>Sign out</Text>
          </TouchableOpacity>
        </RoleGate>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: "#F9FAFB",  // tokens.colors.neutral[50] — verify token path
  },
  scrollContent: {
    padding: tokens.spacing[4],
    paddingBottom: tokens.spacing[10],
    gap: tokens.spacing[3],
  },
  screenTitle: {
    fontSize: tokens.mobileFontSizes.h1,
    fontWeight: fontWeights.medium,
    color: tokens.colors.neutral[900],
    marginBottom: tokens.spacing[2],
  },
  signOutButton: {
    marginTop: tokens.spacing[6],
    paddingVertical: tokens.spacing[2],
    paddingHorizontal: tokens.spacing[4],
    minHeight: tokens.touchTargets.mobile.sm,
    justifyContent: "center",
    alignItems: "center",
  },
  signOutText: {
    fontSize: tokens.mobileFontSizes.body,
    color: lightTheme.danger.bg,
  },
});
```

> **Verify token paths** — read `constants/style-constants.ts` to confirm `tokens.mobileFontSizes.h1`, `tokens.colors.neutral[50]` etc. match the existing token structure.

---

## Tests

### Unit Tests (co-located)

**`useOwnerPendingQuotes.test.ts`**:
- Calls `GET /api/v1/quotes` with `status=pending_approval` param present
- Does NOT include `submitted_by` param
- Returns `pendingCount = array.length`

**`useQbStatusMobile.test.ts`**:
- Calls `GET /api/v1/integrations/quickbooks/status`

**`useOwnerArSummary.test.ts`**:
- Invoice with `due_at` in the past → counted in `overdueCount`
- Invoice with `due_at` in the future → not in `overdueCount`
- `outstandingCount` matches `total` from response

**`ApprovalsQueueSection.test.tsx`**:
- `pendingCount=2` → "2 quotes awaiting approval" visible
- `pendingCount=0` → "All caught up" visible
- Press → `router.push` called with `(home)/quotes/pending`

**`QbSyncStatusSection.test.tsx`**:
- `is_connected=true, connection_status="active"` → "Connected" visible
- `is_connected=false` → "Not connected — Connect →" visible
- Connect link press → `Linking.openURL` called with QB settings URL

**`ArSummarySection.test.tsx`**:
- 3 invoices, 1 overdue → "3 outstanding" + "1 overdue" badge
- 0 invoices → "No outstanding invoices"

### Integration Tests (`__tests__/batch_mob_b5/`)

**`owner-tab.integration.test.tsx`**:
- "coming in FE-B3+" NOT in rendered output (placeholder removed)
- All 6 section `testID`s present in rendered tree
- `CalendarSyncStatusSection` (`testID="owner-tab-calendar-sync-row"`) still renders
- `FieldIssuesSyncStatusSection` (`testID="field-issues-sync-status-section"`) still renders
- `ApprovalsQueueSection` with 2 pending → count visible
- `QbSyncStatusSection` with connected fixture → "Connected" visible
- `QbSyncStatusSection` with disconnected → connect link visible
- `ArSummarySection` with 3 invoices → count visible
- Sign-out button (`testID="signout-button"`) visible and callable
- Screen is wrapped in `ScrollView` (not centered `View`)

### Regression Tests

- `CalendarSyncStatusSection` renders without modification
- `FieldIssuesSyncStatusSection` renders without modification
- Sign-out clears query cache and redirects to `/(auth)/login`
- Existing BETA-B1 owner escalation tests pass

---

## Final Verification

```bash
cd <repo>/frontend
pnpm --filter mobile check-types && \
pnpm --filter mobile lint && \
echo "=== TYPE+LINT PASS ===" && \
pnpm --filter mobile test 2>&1 | tail -10 && \
echo "=== MOB-B5 FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done — MOB-B5

Update `pilot-app-beta-fixes-v2-impl-plan.md` §9 Batch Completion Tracker:

- [ ] Pre-modification regression baseline captured
- [ ] `useAuth()` return shape read — `tenantId` field confirmed (or blocked path documented)
- [ ] `TenantSubscriptionResponse.usage` schema read from `backend/openapi.json`
- [ ] Invoice status codes read from `backend/openapi.json` — `"sent"` param confirmed valid
- [ ] All existing source files read before modification (`owner.tsx`, existing sections, existing hooks)
- [ ] `ownerHandlers.ts` MSW fixtures created for all 4 new endpoints + registered in `handlers/index.ts`
- [ ] `useOwnerPendingQuotes`: calls `/api/v1/quotes?status=pending_approval` — NO `submitted_by` param
- [ ] `useQbStatusMobile`: calls `/api/v1/integrations/quickbooks/status`
- [ ] `useOwnerArSummary`: calls `/api/v1/invoices/?status=sent`; derives `overdueCount` client-side
- [ ] `useOwnerPlanUsage`: calls `/api/v1/tenants/{tenantId}/subscription` (or documented as TODO)
- [ ] `ApprovalsQueueSection`: shows pending count; "All caught up" when 0; taps to `(home)/quotes/pending`
- [ ] `QbSyncStatusSection`: "Connected" + company name when active; "Not connected" + deep-link otherwise
- [ ] `QbSyncStatusSection`: NO `last_sync_at` displayed (not in API response)
- [ ] `ArSummarySection`: outstanding count + overdue badge; empty state when 0
- [ ] `PlanUsageSection`: tier name displayed; fails silently if no data
- [ ] `owner.tsx` rewritten — `ScrollView` + `SafeAreaView` layout
- [ ] Placeholder "coming in FE-B3+" REMOVED
- [ ] All 6 sections composed in correct order (Approvals → Field Issues → Calendar → QB → AR → Plan → Sign-out)
- [ ] Sign-out moved to bottom of `ScrollView`
- [ ] `CalendarSyncStatusSection` preserved — no internal changes
- [ ] `FieldIssuesSyncStatusSection` preserved — no internal changes
- [ ] Sign-out logic unchanged (`queryClient.clear()` + `signOut()` + `router.replace("/(auth)/login")`)
- [ ] Unit tests pass (all per §J.1 in design doc)
- [ ] Integration tests pass (all per §J.2 in design doc)
- [ ] Regression tests pass — existing calendar/field-issues/sign-out tests unaffected
- [ ] Zero TypeScript errors (`pnpm --filter mobile check-types`)
- [ ] Zero ESLint warnings
- [ ] No regressions in pre-existing mobile test suite
- [ ] Full verification command passes (`=== MOB-B5 FINAL VERIFICATION COMPLETE ===`)
- [ ] Final test count (before → after) documented in impl plan tracker
- [ ] Summary of work accomplished added to impl plan §9 as new sub-section after MOB-B5 row
