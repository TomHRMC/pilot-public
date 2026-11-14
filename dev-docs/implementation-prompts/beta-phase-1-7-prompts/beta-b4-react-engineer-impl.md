# Implementation Prompt: BETA-B4 — Settings Missing Pages & Layout Fix

**Mode**: Pilot React Engineer  
**Batch**: BETA-B4  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-beta-v1-fixes-b4-design.md`  
**Source plan**: `dev-docs/analysis/pilot-app-beta-fixes-v1-impl-plan.md` §8 BETA-B4  
**Estimated session**: 5–8 hours  
**Contains companion Python Engineer backend tasks** — see §Companion Backend Tasks

---

## ⚠️ MANDATORY STOP: Read These Rules First

Before writing a single line of code, read:
- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full

Key rules for this batch:
- **Rule 1.1**: All endpoints verified in design doc from `openapi_schema_map.md`. Do NOT deviate.
- **Rule 1.3**: Run `pnpm sync-api-types` before starting.
- **Rule 2**: All API calls use `apiClient`. Never raw `fetch()`.
- **Rule 7**: Check `packages/ui/src/index.ts` for shared components — `<SettingControl>`, `<EmptyState>`, `<LoadingState>`, `<ErrorState>`, `<TierPickerCard>`, `<InFlightSyncIndicator>` are all available.

---

## Design Principle

> This batch is PRD-driven. The PRD defines what each settings surface must do. Backend gaps are documented as companion tasks and covered by MSW handlers during development. Frontend components are NOT simplified to match backend limitations — they reflect PRD requirements.

---

## Companion Backend Tasks (Python Engineer — Do Not Block React Work)

| # | Task | What's Needed |
|---|---|---|
| BETA-B4-BE-01 | User invite + deactivate endpoints | `POST /api/v1/users/invite` + `PATCH /api/v1/users/{id}/deactivate` |
| BETA-B4-BE-02 | Invoice history + payment methods | Deferred to Stripe integration phase (post-beta) |
| BETA-B4-BE-03 | GET for current tenant MFA policy | `GET /api/v1/settings/tenant/mfa-required` returning `{tenant_mfa_required, grace_period_starts_at}` |

---

## Context: Layout Fix Already Applied

**The SettingsShell layout is already patched.** `SettingsShell.tsx` currently uses `flex h-full min-h-0 flex-1` — no layout code changes in this batch. Confirm this is still the case before starting:

```bash
grep -n "h-full min-h-0" frontend/apps/web/src/features/settings/components/SettingsShell.tsx
```

If the patch is not present, apply it (replace `min-h-screen` with `h-full min-h-0 flex-1`). If it is present, proceed directly to Step 0.

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter @pilot/ui test 2>&1 | tail -5
pnpm --filter web test 2>&1 | tail -5
```

Record counts. All must still pass at the end.

---

## Pre-Work: Sync API Types + Read Design Doc

```bash
pnpm sync-api-types
```

**Read the full design doc before writing any code:**
```
dev-docs/architecture-design/batch-designs/batch-beta-v1-fixes-b4-design.md
```

---

## Pre-Work: Read Existing Files Before Touching Them

Read each of these before modifying them:

```bash
# permissions.ts (must read before adding to it)
cat frontend/packages/ui/src/role-gate/permissions.ts

# SettingsShell (confirm layout patch)
cat frontend/apps/web/src/features/settings/components/SettingsShell.tsx

# Existing notification preferences page (pattern reference)
cat frontend/apps/web/src/app/(authed)/settings/notifications/preferences/page.tsx

# Existing useNotificationPreferences hook (confirm import path for reuse)
find frontend/apps/web/src/features -name "useNotificationPreferences.ts" | head -5

# Confirm useMfaStatus exists (to reuse vs create)
find frontend/apps/web/src/features -name "useMfaStatus.ts" | head -5

# Confirm QB conflicts page for pattern + potential hook reuse
find frontend/apps/web/src/features -name "*qb*" -o -name "*quickbooks*" | grep -i hook | head -10
```

---

## Implementation: Step-by-Step Execution

Follow Design Doc §B execution order exactly.

---

### STEP 0 (P1): Add New Permission Keys to `permissions.ts`

**File**: `frontend/packages/ui/src/role-gate/permissions.ts`

Read the file first. Then add to the `PermissionKey` type union (preserve ALL existing keys verbatim):

```typescript
// BETA-B4 additions — preserve all existing keys
| "integrations.manage"   // Integrations settings — owner, operator only
| "settings.tenant.write" // Tenant-level settings write — owner, operator only
| "billing.view"          // Subscription/billing view — owner, operator only
```

Add to `ROLE_PERMISSION_MAP` per Design Doc §F:

| Permission | owner | office_staff | tech | operator |
|---|---|---|---|---|
| `integrations.manage` | ✅ | ❌ | ❌ | ✅ |
| `settings.tenant.write` | ✅ | ❌ | ❌ | ✅ |
| `billing.view` | ✅ | ❌ | ❌ | ✅ |

Run tests immediately after:
```bash
pnpm --filter @pilot/ui test 2>&1 | tail -5
```

Create permissions test file: `frontend/packages/ui/src/role-gate/__tests__/permissions.beta-b4.test.ts`

```typescript
import { ROLE_PERMISSION_MAP } from "../permissions";

describe("BETA-B4 permission additions", () => {
  it("owner has integrations.manage", () => {
    expect(ROLE_PERMISSION_MAP.owner).toContain("integrations.manage");
  });
  it("office_staff does NOT have integrations.manage", () => {
    expect(ROLE_PERMISSION_MAP.office_staff).not.toContain("integrations.manage");
  });
  it("tech does NOT have integrations.manage", () => {
    expect(ROLE_PERMISSION_MAP.tech).not.toContain("integrations.manage");
  });
  it("owner has settings.tenant.write", () => {
    expect(ROLE_PERMISSION_MAP.owner).toContain("settings.tenant.write");
  });
  it("owner has billing.view", () => {
    expect(ROLE_PERMISSION_MAP.owner).toContain("billing.view");
  });
  it("operator has all three BETA-B4 permissions", () => {
    expect(ROLE_PERMISSION_MAP.operator).toContain("integrations.manage");
    expect(ROLE_PERMISSION_MAP.operator).toContain("settings.tenant.write");
    expect(ROLE_PERMISSION_MAP.operator).toContain("billing.view");
  });
});
```

---

### STEP 1 (P1): My Account > Security Index Page

**Route file**: `frontend/apps/web/src/app/(authed)/settings/my-account/security/page.tsx`  
**Feature component**: `frontend/apps/web/src/features/account-settings/components/SecurityIndexPage.tsx`

> This is the landing page for the My Account > Security group. It links to existing sub-pages (mfa/, sessions/, password/, data-export/) — it does NOT replace them.

**First**: Verify `useMfaStatus` hook. If it exists, import it. If not, create it:

```typescript
// frontend/apps/web/src/features/account-settings/hooks/useMfaStatus.ts
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export interface MfaStatusResponse {
  enrolled_methods: Array<{ method: string; enrolled_at: string }>;
  method_count: number;
  totp_enabled: boolean;
  sms_enabled: boolean;
  email_enabled: boolean;
  recovery_codes_available: boolean;
}

export function useMfaStatus() {
  return useQuery({
    queryKey: ["mfa-status"],
    queryFn: async (): Promise<MfaStatusResponse> => {
      const res = await apiClient.get("/api/v1/users/me/mfa-status");
      return res.data;
    },
    staleTime: 60_000,
  });
}
```

**Feature component** (`SecurityIndexPage.tsx`):

```tsx
"use client";
import { useMfaStatus } from "../hooks/useMfaStatus";
import { EmptyState, LoadingState, ErrorState } from "@pilot/ui/states";

export function SecurityIndexPage() {
  const { data, isLoading, isError } = useMfaStatus();

  if (isLoading) return <LoadingState type="inline" label="Loading security settings..." />;

  return (
    <div className="p-6 max-w-2xl">
      <h1 className="text-2xl font-semibold text-neutral-900 mb-6">Security</h1>
      <div className="space-y-4">
        {/* MFA Card */}
        <SecurityNavCard
          title="Multi-Factor Authentication"
          description={
            isError
              ? "Could not load MFA status"
              : `${data?.method_count ?? 0} method${data?.method_count !== 1 ? "s" : ""} enrolled`
          }
          href="/settings/my-account/security/mfa"
        />
        {/* Active Sessions Card */}
        <SecurityNavCard
          title="Active Sessions"
          description="View and revoke active login sessions"
          href="/settings/my-account/sessions"
        />
        {/* Password Card */}
        <SecurityNavCard
          title="Password"
          description="Change your account password"
          href="/settings/my-account/password"
        />
        {/* Data Export Card */}
        <SecurityNavCard
          title="Data Export"
          description="Export a copy of your data"
          href="/settings/my-account/data-export"
        />
      </div>
    </div>
  );
}

function SecurityNavCard({ title, description, href }: { title: string; description: string; href: string }) {
  return (
    <a
      href={href}
      className="flex items-center justify-between p-4 rounded-md border border-neutral-200 hover:border-brand-400 hover:bg-brand-50 transition-colors group"
    >
      <div>
        <p className="font-medium text-neutral-900 text-sm">{title}</p>
        <p className="text-xs text-neutral-500 mt-0.5">{description}</p>
      </div>
      <span className="text-neutral-400 group-hover:text-brand-600 text-lg">→</span>
    </a>
  );
}
```

**Route file** (thin — no `"use client"`):

```tsx
import { SecurityIndexPage } from "@/features/account-settings/components/SecurityIndexPage";
export default function MyAccountSecurityIndexPage() {
  return <SecurityIndexPage />;
}
```

---

### STEP 2 (P1): Tenant Security & MFA Policy Page

**Route file**: `frontend/apps/web/src/app/(authed)/settings/security/page.tsx`  
**Feature component**: `frontend/apps/web/src/features/settings/components/TenantSecurityPage.tsx`  
**New hook**: `frontend/apps/web/src/features/settings/hooks/useTenantMfaPolicy.ts`

**MSW handler required** (no GET endpoint for initial state — BETA-B4-BE-03):

Create/extend `frontend/apps/web/src/mocks/handlers/settings.ts` (or existing settings handler file — read the handlers directory first):

```typescript
// MSW handler for tenant MFA policy — provides initial GET state
// until BETA-B4-BE-03 backend task adds GET /api/v1/settings/tenant/mfa-required
http.get("/api/v1/settings/tenant/mfa-required", () =>
  HttpResponse.json({ tenant_mfa_required: false, grace_period_starts_at: null })
),
http.put("/api/v1/settings/tenant/mfa-required", async ({ request }) => {
  const body = await request.json() as any;
  return HttpResponse.json({
    tenant_mfa_required: body.tenant_mfa_required,
    grace_period_starts_at: body.tenant_mfa_required
      ? new Date().toISOString()
      : null,
  });
}),
```

**Hook** (implement per Design Doc §F):

```typescript
// useTenantMfaPolicy.ts
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

export interface TenantMfaPolicy {
  tenantMfaRequired: boolean;
  gracePeriodStartsAt: string | null;
}

export function useTenantMfaPolicy() {
  const qc = useQueryClient();
  const query = useQuery({
    queryKey: ["tenant-mfa-policy"],
    queryFn: async (): Promise<TenantMfaPolicy> => {
      // GET endpoint may not exist yet — MSW handler covers test env
      // BETA-B4-BE-03 will add this endpoint
      const res = await apiClient.get("/api/v1/settings/tenant/mfa-required");
      return {
        tenantMfaRequired: res.data.tenant_mfa_required,
        gracePeriodStartsAt: res.data.grace_period_starts_at,
      };
    },
    staleTime: 60_000,
  });

  const mutation = useMutation({
    mutationFn: async (required: boolean) => {
      const res = await apiClient.put("/api/v1/settings/tenant/mfa-required", {
        tenant_mfa_required: required,
      });
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tenant-mfa-policy"] }),
  });

  return {
    policy: query.data ?? null,
    isLoading: query.isLoading,
    isError: query.isError,
    setMfaRequired: (required: boolean) => mutation.mutateAsync(required),
    isUpdating: mutation.isPending,
  };
}
```

**Feature component** — uses `<RoleGate permission="settings.manage">` (existing key):

```tsx
"use client";
import { RoleGate } from "@pilot/ui/role-gate";
import { LoadingState, ErrorState } from "@pilot/ui/states";
import { useTenantMfaPolicy } from "../hooks/useTenantMfaPolicy";

export function TenantSecurityPage() {
  return (
    <RoleGate permission="settings.manage">
      <TenantSecurityContent />
    </RoleGate>
  );
}

function TenantSecurityContent() {
  const { policy, isLoading, isError, setMfaRequired, isUpdating } = useTenantMfaPolicy();

  if (isLoading) return <LoadingState type="inline" label="Loading security policy..." />;
  if (isError) return <ErrorState type="server" title="Could not load security policy" />;

  return (
    <div className="p-6 max-w-2xl">
      <h1 className="text-2xl font-semibold text-neutral-900 mb-2">Security & MFA</h1>
      <p className="text-sm text-neutral-500 mb-6">Configure security policies for all team members.</p>

      <div className="rounded-md border border-neutral-200 p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="font-medium text-neutral-900 text-sm">Require MFA for all users</p>
            <p className="text-xs text-neutral-500 mt-1">
              When enabled, all team members must enroll in MFA within a 7-day grace period.
              {policy?.gracePeriodStartsAt && (
                <span className="block mt-1 text-alert-600">
                  Grace period started {new Date(policy.gracePeriodStartsAt).toLocaleDateString()}.
                </span>
              )}
            </p>
          </div>
          <button
            role="switch"
            aria-checked={policy?.tenantMfaRequired ?? false}
            disabled={isUpdating}
            onClick={() => setMfaRequired(!(policy?.tenantMfaRequired ?? false))}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 disabled:opacity-50 ${
              policy?.tenantMfaRequired ? "bg-brand-600" : "bg-neutral-200"
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                policy?.tenantMfaRequired ? "translate-x-6" : "translate-x-1"
              }`}
            />
          </button>
        </div>
      </div>
    </div>
  );
}
```

**Route file**:
```tsx
import { TenantSecurityPage } from "@/features/settings/components/TenantSecurityPage";
export default function SettingsSecurityPage() { return <TenantSecurityPage />; }
```

---

### STEP 3 (P1): Team Settings Page

**Route file**: `frontend/apps/web/src/app/(authed)/settings/team/page.tsx`  
**Feature component**: `frontend/apps/web/src/features/settings/components/TeamSettingsPage.tsx`  
**New hook**: `frontend/apps/web/src/features/settings/hooks/useTeamUsers.ts`

Implement hook exactly per Design Doc §F:

```typescript
// useTeamUsers.ts — exact interface from design doc
export function useTeamUsers(): UseTeamUsersReturn
// Users from GET /api/v1/users
// Role assignment via POST /api/v1/users/{user_id}/role
```

Feature component requirements:
- `<RoleGate permission="settings.manage">` wraps all content
- User list table: email, role badge, joined date
- Role change dropdown visible only to owner (use `useRequiresPermission("settings.manage")` inline for the dropdown visibility)
- "Invite team member" button renders an informational dialog: "Inviting team members is coming soon. Ask your team member to sign up at [app URL], then you'll be able to assign their role here."
- `<LoadingState>` + `<ErrorState>` handling

Design Doc §C Route 3 has the full content spec — implement to match.

---

### STEP 4 (P1): Billing Settings Page

**Route file**: `frontend/apps/web/src/app/(authed)/settings/billing/page.tsx`  
**Feature component**: `frontend/apps/web/src/features/settings/components/BillingSettingsPage.tsx`  
**New hook**: `frontend/apps/web/src/features/settings/hooks/useTenantSubscription.ts`

Implement hook exactly per Design Doc §F:

```typescript
// useTenantSubscription.ts — exact interface from design doc
// GET /api/v1/tenants/{tenant_id}/subscription
// POST /api/v1/tenants/{tenant_id}/subscription/change-tier
export function useTenantSubscription(): UseTenantSubscriptionReturn
```

Feature component requirements:
- `<RoleGate permission="billing.view">` wraps all content
- Current plan card: tier name, monthly price, billing interval
- Trial banner if `is_trial=true`: "Trial ends [date] — upgrade to keep access"
- Usage summary: user count vs. max_users, SMS segments (from `usage` object — map field names from actual API response, verify against `openapi.json`)
- "Upgrade plan" button visible on trial → opens `<TierPickerCard>` from `@pilot/ui` (FE-B13 component — verify import path from `packages/ui/src/index.ts`)
- "Payment methods" section: static placeholder — "Payment method management coming soon. Contact support@pilotfortrades.com if needed."
- `<LoadingState>` + `<ErrorState>` handling

Design Doc §C Route 4 has the full content spec.

---

### STEP 5 (P1): QuickBooks Integration Index Page

**Route file**: `frontend/apps/web/src/app/(authed)/settings/integrations/quickbooks/page.tsx`  
**Feature component**: `frontend/apps/web/src/features/settings/components/QbIntegrationIndexPage.tsx`

First, check if `useQbConnectionStatus` already exists:
```bash
find frontend/apps/web/src/features -name "*qb*" -o -name "*quickbooks*" | grep -i hook
```

If it exists, reuse it. If not, create `frontend/apps/web/src/features/settings/hooks/useQbConnectionStatus.ts`:
- `GET /api/v1/integrations/quickbooks/status` — returns `{connected, company_name, last_sync_at, expires_at}`

Feature component requirements:
- `<RoleGate permission="settings.manage">` wraps content
- Connected state: company name, last sync time, Disconnect button (with confirm dialog)
- Disconnected state: "Connect QuickBooks" button → `GET /api/v1/integrations/quickbooks/connect` (OAuth redirect)
- Navigation links: "Auto-expiry & sync settings" → `/settings/integrations/quickbooks/auto-expiry`; "View conflicts" → `/settings/integrations/quickbooks/conflicts`
- `<InFlightSyncIndicator surface="quickbooks">` — reuse from `@pilot/ui` (FE-B15)

---

### STEP 6 (P1): Integrations General Overview Page

**Route file**: `frontend/apps/web/src/app/(authed)/settings/integrations/general/page.tsx`  
**Feature component**: `frontend/apps/web/src/features/settings/components/IntegrationsGeneralPage.tsx`  
**New hook**: `frontend/apps/web/src/features/settings/hooks/useIntegrationsDashboard.ts`

Implement hook exactly per Design Doc §F — fan-out fetches for:
- `GET /api/v1/integrations/sync-dashboard/`
- `GET /api/v1/integrations/quickbooks/status`
- `GET /api/v1/integrations/calendar/status`
- `GET /api/v1/tenants/{tenant_id}/phone-numbers/` (for SMS provisioning state)

Feature component requirements:
- `<RoleGate permission="settings.manage">` wraps content
- Three integration row cards: QuickBooks, Calendar, SMS
- Each card: connection badge (Connected/Disconnected), last sync or "Not connected", link to dedicated settings page
- Pending sync items summary from sync-dashboard
- `<EmptyState>` if all disconnected

---

### STEPS 7–9 (P1): Notifications Channel Pages — Email, SMS, In-App

All three pages follow the identical pattern. Read the existing `/settings/notifications/preferences/page.tsx` to understand how `useNotificationPreferences` is used before writing any of these.

**Route files**:
- `frontend/apps/web/src/app/(authed)/settings/notifications/email/page.tsx`
- `frontend/apps/web/src/app/(authed)/settings/notifications/sms/page.tsx`  
- `frontend/apps/web/src/app/(authed)/settings/notifications/in-app/page.tsx`

**Feature components**:
- `frontend/apps/web/src/features/settings/components/NotificationEmailPrefsPage.tsx`
- `frontend/apps/web/src/features/settings/components/NotificationSmsPrefsPage.tsx`
- `frontend/apps/web/src/features/settings/components/NotificationInAppPrefsPage.tsx`

**Implementation pattern** (same for Email and SMS — channel filter differs):

```tsx
"use client";
import { useNotificationPreferences } from "../../notification-preferences/hooks/useNotificationPreferences";
// Adjust import path to match actual hook location — verify with find command above

export function NotificationEmailPrefsPage() {
  const { preferences, isLoading, isError, updatePreference } = useNotificationPreferences();
  
  // Filter to email channel only
  const emailPrefs = preferences?.filter((p) => p.channel === "email") ?? [];
  
  // ... render table with email category rows
  // Each row: category name | toggle calling updatePreference(categoryId, "email", value)
  // Include link to full matrix: "/settings/notifications/preferences"
}
```

**In-app page** is the same but adds a recent notifications history section (new hook):

Create `frontend/apps/web/src/features/notification-preferences/hooks/useRecentInAppNotifications.ts`:
- `GET /api/v1/notifications/in-app/recent?limit=50`
- `POST /api/v1/notifications/in-app/mark-read` for bulk mark-read

Implement per Design Doc §F exact interface.

---

### STEP 10 (P2): Branding Redirect

**Route file**: `frontend/apps/web/src/app/(authed)/settings/branding/page.tsx`

```tsx
import { redirect } from "next/navigation";
export default function BrandingPage() {
  redirect("/settings/communications/email-branding");
}
```

No feature component. No `"use client"`. Server-side redirect only.

---

### STEP 11 (P2): Data & Privacy Informational Page

**Route file**: `frontend/apps/web/src/app/(authed)/settings/data-privacy/page.tsx`

This is a static informational page — no feature component needed:

```tsx
export default function DataPrivacyPage() {
  return (
    <div className="p-6 max-w-2xl">
      <h1 className="text-2xl font-semibold text-neutral-900 mb-2">Data & Privacy</h1>
      <p className="text-sm text-neutral-500 mb-6">
        Pilot retains your data for the duration of your subscription.
      </p>
      <div className="space-y-4">
        <div className="rounded-md border border-neutral-200 p-4">
          <p className="font-medium text-neutral-900 text-sm mb-1">Data Retention</p>
          <p className="text-xs text-neutral-500">
            Audit logs are retained for 12 months. Job records, quotes, and financial data 
            are retained indefinitely while your subscription is active.
          </p>
        </div>
        <a
          href="/settings/my-account/data-export"
          className="flex items-center justify-between p-4 rounded-md border border-neutral-200 hover:border-brand-400 transition-colors"
        >
          <div>
            <p className="font-medium text-neutral-900 text-sm">Export Your Data</p>
            <p className="text-xs text-neutral-500 mt-0.5">Download a copy of all your data</p>
          </div>
          <span className="text-neutral-400 text-lg">→</span>
        </a>
      </div>
    </div>
  );
}
```

No `"use client"` — server component with no data fetching.

---

## Test Implementation

### Unit Tests (co-located)

Per Design Doc §I — create one unit test file per new feature component. Minimum coverage per file:
- Renders (not 404)
- Correct RBAC (RoleGate blocks unauthorized roles)
- Primary content visible with MSW mock data
- Loading state renders
- Error state renders

Focus on ensuring `<RoleGate>` gates work correctly — this is the highest-value test for security-sensitive settings pages.

### Integration Tests

Create folder: `frontend/apps/web/__tests__/batch_beta_v1_b4/`

Create one integration test file per page per Design Doc §I:
- `security-index.test.tsx`
- `tenant-security.test.tsx`
- `team.test.tsx`
- `billing.test.tsx`
- `qb-index.test.tsx`
- `integrations-general.test.tsx`
- `notifications-email.test.tsx`
- `notifications-sms.test.tsx`
- `notifications-in-app.test.tsx`
- `branding-redirect.test.tsx`
- `data-privacy.test.tsx`

**Minimum integration test coverage per page**:
1. Route does NOT 404 — page renders
2. Correct RBAC: owner can see content; tech cannot (for gated pages)
3. Primary content visible with MSW mock data

The branding redirect test should verify the redirect fires:
```tsx
it("redirects to email-branding", async () => {
  render(<BrandingPage />);
  // verify redirect was called with /settings/communications/email-branding
});
```

### Permissions Test

Already specified in STEP 0 above — `permissions.beta-b4.test.ts`.

### Accessibility

axe-core check on every new page component (same pattern as BETA-B3). Apply to all 9 non-redirect, non-static pages.

---

## Final Verification

```bash
cd <repo>/frontend && pnpm --filter @pilot/ui check-types && pnpm --filter web check-types && pnpm --filter mobile build && pnpm --filter @pilot/ui lint && pnpm --filter web lint && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && pnpm --filter web test 2>&1 | tail -6 && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done — BETA-B4

Update the `pilot-app-beta-fixes-v1-impl-plan.md` §9 Batch Completion Tracker:

- [ ] Pre-modification regression baseline captured
- [ ] `pnpm sync-api-types` run
- [ ] Design doc fully read before writing any code
- [ ] Layout patch confirmed still in place (or re-applied if missing)
- [ ] **STEP 0**: `permissions.ts` updated with `integrations.manage`, `settings.tenant.write`, `billing.view`
- [ ] **STEP 0**: `ROLE_PERMISSION_MAP` updated — owner + operator have all three; office_staff and tech do not
- [ ] **STEP 0**: Permissions unit test file `permissions.beta-b4.test.ts` passes
- [ ] `/settings/my-account/security` renders (not 404); shows MFA count + navigation cards
- [ ] `/settings/security` renders (not 404); MFA policy toggle works; `<RoleGate>` hides for tech
- [ ] `/settings/team` renders (not 404); user list renders; role change fires POST; invite shows placeholder
- [ ] `/settings/billing` renders (not 404); plan name + usage visible; trial banner shows when applicable; `<RoleGate>` hides for tech
- [ ] `/settings/integrations/quickbooks` renders (not 404); connection status shown; connect/disconnect functional
- [ ] `/settings/integrations/general` renders (not 404); all three integration cards render
- [ ] `/settings/notifications/email` renders (not 404); email channel prefs rows present; toggles fire PUT with `channel='email'`
- [ ] `/settings/notifications/sms` renders (not 404); sms channel prefs rows present
- [ ] `/settings/notifications/in-app` renders (not 404); in-app prefs + recent notifications list
- [ ] `/settings/branding` redirects to `/settings/communications/email-branding` (not 404)
- [ ] `/settings/data-privacy` renders (not 404); data export link present
- [ ] All 5 new hooks created per design doc §F interfaces
- [ ] MSW handlers added for BETA-B4-BE-03 (tenant MFA policy GET) and Team invite placeholder
- [ ] All unit tests pass per §I
- [ ] All 11 integration tests pass in `batch_beta_v1_b4/`
- [ ] axe-core zero violations on all 9 non-static, non-redirect pages
- [ ] Zero TypeScript errors
- [ ] Zero ESLint `no-hardcoded-design-values` warnings
- [ ] No regressions in pre-existing test suite
- [ ] Full verification command passes (`=== MVP FINAL VERIFICATION COMPLETE ===`)
- [ ] Companion backend tasks (BETA-B4-BE-01, BE-02, BE-03) documented for Python Engineer handoff
- [ ] Update this Definition of Done list with completion checks next to each item if completed
- [ ] Final test count (before/after) documented in impl plan tracker in the source plan
- [ ] Summary of work accomplished added to new sub-section in impl plan tracker in Section 9 in the source plan after the last batch entry
