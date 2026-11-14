# Implementation Prompt: MOB-B7 Part B — LOTO Gate + Create Customer + Today Tab

**Mode**: Pilot React Native Engineer  
**Batch**: MOB-B7 Part B (Mobile Frontend)  
**Source plan**: `dev-docs/analysis/pilot-app-pre-wkstm-3-prep-plan.md` §Phase 0.9 — MOB-B7  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-mob-b7-design.md`  
**Estimated session**: 3–4 hours  
**Platform**: Mobile only (`apps/mobile`)  
**Backend companion**: MOB-B7 Part A (Python Engineer) — **must be complete before starting**

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — §8.2 Mobile rules section in full
- **`dev-docs/architecture-design/batch-designs/batch-mob-b7-design.md`** — every section (A–I)

**Critical rules for this batch:**

- **Rule 1.1**: Before writing `useLotoPolicy`, verify the exact endpoint path from Part A handoff. It may be `GET /api/v1/settings/loto-policy` OR `GET /api/v1/settings/loto_confirmation_required` — confirm from `openapi_schema_map.md`.
- **Rule 1.3**: Run `pnpm sync-api-types` before starting — Part A may have added a new schema.
- **Rule 9 (mobile)**: WatermelonDB must be mocked in ALL tests.
- **Rule 16 (mobile)**: Expo Router must be mocked in ALL screen tests.
- **LOTO default is optional mode, not hidden**: When `loto_confirmation_required = false`, the LOTO section remains visible with an "Optional" badge. It is NEVER hidden entirely. Removing the section entirely is a product defect — LOTO confirms are valuable audit data even when not required.
- **LOTO graceful degradation**: If `useLotoPolicy` errors, default to `loto_confirmation_required = false` (optional mode). Never hide LOTO on error.
- **Today tab — jobs are primary**: The Home tab's primary content is today's job schedule. The voice CTA moves to a compact secondary position (not removed). Customer messages remain at bottom.
- **Create Customer form — keep minimal**: Type + display name + mobile phone + email only. No sites, no payment methods on mobile.

---

## Design Decisions (Do Not Re-Litigate)

From Design Doc §G:

| Decision | Outcome | Rationale |
|---|---|---|
| LOTO `loto_confirmation_required = false` behavior | Show section with "Optional" badge | Audit value even when not required |
| LOTO graceful degradation | Default `false` on error | Never block LOTO access |
| Home tab layout | Jobs list primary; voice CTA compact; SMS messages at bottom | PRD §3.14 spec |
| Create Customer form scope | Type + display_name + mobile_phone + email only | Field is not the place for full customer setup |

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter mobile test 2>&1 | tail -8
```

Record exact count. Fix pre-existing failures or confirm with Tom.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

---

## Pre-Work: Verify Endpoints

```bash
# Check LOTO policy endpoint from Part A
grep -A 3 "loto" backend/openapi_schema_map.md | head -15

# Check customer create endpoint (same as FE-B18)
grep -A 5 "POST /api/v1/customers" backend/openapi_schema_map.md | head -15

# Find existing sync trigger in mobile (for reference — already confirmed in MOB-B6 pre-work)
# If not done: grep -rn "triggerSync\|SyncOrchestrator" frontend/apps/mobile/ --include="*.ts" --include="*.tsx"
```

---

## Pre-Work: Read These Source Files

```
frontend/apps/mobile/features/jobs/components/detail/LotoCheckSection.tsx
  ← read fully — understand current implementation before adding policy gate

frontend/apps/mobile/features/customers/components/CustomersTabScreen.tsx
  ← read fully — understand current layout before adding "+" button

frontend/apps/mobile/app/(tabs)/(home)/index.tsx
  ← read fully — understand current voice-first layout before refactoring

frontend/apps/mobile/features/jobs/components/JobsTabScreen.tsx lines 1–80
  ← understand useTechJobsList pattern for reuse in Home tab

frontend/apps/mobile/mocks/handlers/index.ts (mobile)
  ← find if separate from web handlers
```

Also run:
```bash
# Find mobile mocks handlers
find frontend/apps/mobile/mocks -name "*.ts" | sort

# Check mobile handler barrel
cat frontend/apps/mobile/mocks/handlers/index.ts 2>/dev/null | head -30

# Find existing customer create hook if any
find frontend/apps/mobile/features/customers/hooks -name "*.ts" | sort
```

---

## Step B1 — Create Mobile MSW Handlers

Check where mobile MSW handlers live (likely `apps/mobile/mocks/handlers/`). Add:

```typescript
// GET /api/v1/settings/loto-policy (or loto_confirmation_required) — returns false by default
// POST /api/v1/customers/ — returns created customer

// Example:
http.get('/api/v1/settings/loto-policy', () =>
  HttpResponse.json({ loto_confirmation_required: false })
),
http.post('/api/v1/customers/', async ({ request }) => {
  const body = await request.json() as Record<string, unknown>;
  return HttpResponse.json({
    id: 'mob-b7-test-customer',
    ...body,
    is_active: true,
    created_at: new Date().toISOString(),
  }, { status: 201 });
}),
```

Register in mobile handler barrel.

---

## Step B2 — Create `useLotoPolicy` Hook

**File**: `apps/mobile/features/jobs/hooks/useLotoPolicy.ts`

```typescript
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@pilot/shared-api';

interface LotoPolicyResponse {
  loto_confirmation_required: boolean;
}

const LOTO_POLICY_DEFAULT: LotoPolicyResponse = { loto_confirmation_required: false };

export function useLotoPolicy() {
  return useQuery({
    queryKey: ['loto-policy'],
    queryFn: async (): Promise<LotoPolicyResponse> => {
      const res = await apiClient.get('/api/v1/settings/loto-policy');  // verify path from pre-work
      return res.data as LotoPolicyResponse;
    },
    staleTime: 300_000,
    // Graceful degradation: on error, return default (optional mode)
    placeholderData: LOTO_POLICY_DEFAULT,
  });
}
```

---

## Step B3 — Create `useCreateCustomer` Mutation (Mobile)

**File**: `apps/mobile/features/customers/hooks/useCreateCustomer.ts`

```typescript
// POST /api/v1/customers/
// Body: { type: 'person' | 'company', display_name, mobile_phone?, email? }
// On success: invalidate customers query + close bottom sheet via callback
```

Follow the same offline pattern as other mobile mutations (`useCreateExpense`, `useCreateTimeEntry`):
- If online: call API directly
- If offline: queue in WatermelonDB offline sync queue

Read the existing customer hooks in `features/customers/hooks/` before writing.

---

## Step B4 — Gate `LotoCheckSection` on Policy

**File**: `apps/mobile/features/jobs/components/detail/LotoCheckSection.tsx`

Read the full file first. Add `useLotoPolicy()` call at the top:

```typescript
const { data: lotoPolicy } = useLotoPolicy();
const isRequired = lotoPolicy?.loto_confirmation_required ?? false;
```

Then in the render:
- When `isRequired === false` (optional mode):
  - Add "Optional" badge next to section title
  - Keep all three check items tappable (for audit trail)
  - Remove any logic that gates clock-out on LOTO completion
- When `isRequired === true` (required mode):
  - Current behavior (unchanged)

The section header update:
```tsx
<Text style={styles.sectionTitle}>
  LOTO Safety{isRequired ? '' : ' (Optional)'}
</Text>
```

Do NOT hide the section when `isRequired === false`. It remains visible for audit purposes.

---

## Step B5 — Create `CreateCustomerBottomSheet`

**File**: `apps/mobile/features/customers/components/CreateCustomerBottomSheet.tsx`

Simple bottom sheet form with minimal fields:

```typescript
interface CreateCustomerBottomSheetProps {
  visible: boolean;
  onClose: () => void;
}

// Fields:
// - Type: radio/segmented control — "Person" / "Company"
// - Display Name (required): TextInput
// - Mobile Phone (optional): TextInput with numeric keyboard
// - Email (optional): TextInput with email keyboard
// 
// Submit button: "Add Customer"
// On submit: calls useCreateCustomer() → on success: close + show toast
// On error: inline error message
```

Follow the pattern of other mobile bottom sheets (`SetLaborRateModal` pattern from FE-B20 if applicable, or `ExpenseSection`'s bottom sheet pattern).

Style using design tokens only — no hardcoded colors/sizes.

---

## Step B6 — Add "+" Button to `CustomersTabScreen`

**File**: `apps/mobile/features/customers/components/CustomersTabScreen.tsx`

Read the full file first. Add to the header area:

```tsx
// In the SafeAreaView header row:
<View style={styles.header}>
  <Text style={styles.title}>Customers</Text>
  <Pressable
    onPress={() => setShowCreate(true)}
    style={styles.addButton}
    accessibilityLabel="Add customer"
    testID="add-customer-button"
  >
    <Text style={styles.addButtonText}>+</Text>
  </Pressable>
</View>

// And at the bottom of the component:
<CreateCustomerBottomSheet
  visible={showCreate}
  onClose={() => setShowCreate(false)}
/>
```

Add `const [showCreate, setShowCreate] = useState(false)` state.

---

## Step B7 — Refactor Home Tab — Today-First Layout

**File**: `apps/mobile/app/(tabs)/(home)/index.tsx`

Read the full file first. Understand the current voice-first layout before modifying.

**New layout order** (from top to bottom):

1. **Compact voice CTA row** (was: large CTA button) — smaller, takes 1 row
2. **Today's Jobs section** — uses `useTechJobsList` (TODAY filter) — primary content
3. **Customer Messages section** (existing `CustomerMessagesSectionRow`) — stays at bottom

```typescript
import { useTechJobsList } from '../../features/jobs/hooks/useTechJobsList';
import { JobCardRow } from '../../features/jobs/components/JobCardRow';

// TODAY jobs from existing hook:
const { todayJobs, isLoading } = useTechJobsList();

// Layout:
return (
  <SafeAreaView style={styles.container}>
    <ScrollView contentContainerStyle={styles.scrollContent}>
      
      {/* Compact voice CTA — secondary, not primary */}
      <View style={styles.voiceRow}>
        <Pressable onPress={handleStartVoiceSession} style={styles.voiceCta}>
          <Text>🎙 Start Voice Session</Text>
        </Pressable>
        <Pressable onPress={handleViewSessions}>
          <Text>Sessions</Text>
        </Pressable>
      </View>

      {/* Today's Jobs — primary content */}
      <Text style={styles.sectionTitle}>{formatTodayHeader()}</Text>
      {isLoading ? (
        <ActivityIndicator />
      ) : todayJobs.length === 0 ? (
        <Text style={styles.emptyText}>No jobs scheduled today</Text>
      ) : (
        todayJobs.map(job => (
          <JobCardRow key={job.id} job={job} onPress={handleJobPress} />
        ))
      )}

      {/* Customer Messages — bottom */}
      <CustomerMessagesSectionRow testID="customer-messages-section" />
      
    </ScrollView>
  </SafeAreaView>
);
```

Adjust the exact structure to match the patterns you find in the file. Preserve existing functionality — do NOT remove `useVoiceSessions` logic.

---

## Test Requirements

### Platform: Mobile (`apps/mobile`) — Jest + react-native

- `jest.mock()`, `.toBeTruthy()`, `fireEvent.press()`
- Mock WatermelonDB in ALL tests
- Mock Expo Router in ALL screen tests
- Mock `useLotoPolicy` and `useCreateCustomer` where needed

### Unit Tests

**`features/jobs/components/detail/__tests__/LotoCheckSection.mob-b7.test.tsx`:**
- When `loto_confirmation_required = false`: shows "Optional" badge + section visible
- When `loto_confirmation_required = true`: no "Optional" badge (current behavior)
- When `useLotoPolicy` errors: shows "Optional" badge (graceful degradation default)
- LOTO section is NEVER hidden regardless of policy

**`features/customers/components/__tests__/CreateCustomerBottomSheet.test.tsx`:**
- Renders form fields (display name, phone, email, type selector)
- Submit with valid data calls `useCreateCustomer`
- Submit with empty display_name shows validation error
- Cancel button calls `onClose`

**`features/customers/components/__tests__/CustomersTabScreen.mob-b7.test.tsx`:**
- "+" button visible in header
- Tapping "+" opens `CreateCustomerBottomSheet`

### Integration Test

**`apps/mobile/__tests__/batch_mob_b7/homeTabToday.integration.test.tsx`:**
1. Home tab renders today's job list as primary content
2. Voice CTA is compact (not the large primary button anymore)
3. Customer Messages section still renders at bottom

---

## Final Verification

### Phase 1 — Targeted

```bash
cd <repo>/frontend

pnpm --filter mobile build 2>&1 | tail -5

pnpm --filter mobile test -- --testPathPattern="LotoCheck|CreateCustomer|homeTabToday" 2>&1 | tail -8
```

### Phase 2 — Full Verification

```bash
cd <repo>/frontend && pnpm --filter mobile build && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MOB-B7 PART B FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done — MOB-B7 Part B

Update `dev-docs/analysis/pilot-app-pre-wkstm-3-prep-plan.md` §Phase 0.9:

- [ ] Regression baseline captured (zero failures or confirmed with Tom)
- [ ] `pnpm sync-api-types` run
- [ ] Design doc read in full (A–I)
- [ ] All mandatory source files read (LotoCheckSection, CustomersTabScreen, home/index.tsx, JobsTabScreen)
- [ ] LOTO policy endpoint path confirmed from Part A handoff
- [ ] **B1**: Mobile MSW handlers for LOTO policy + customer create added and registered
- [ ] **B2**: `useLotoPolicy` hook created with graceful degradation (default `false` on error)
- [ ] **B3**: `useCreateCustomer` mutation created (offline-capable)
- [ ] **B4**: `LotoCheckSection` gated on policy — "Optional" badge shown when `false`; NEVER hidden
- [ ] **B5**: `CreateCustomerBottomSheet` created with type + display_name + phone + email fields
- [ ] **B6**: "+" button added to `CustomersTabScreen` header; opens `CreateCustomerBottomSheet`
- [ ] **B7**: Home tab refactored — today's jobs are primary; voice CTA is compact
- [ ] `LotoCheckSection` unit tests pass: "Optional" badge shows when `false`; section never hidden
- [ ] `CreateCustomerBottomSheet` unit tests pass
- [ ] `CustomersTabScreen` "+" button test passes
- [ ] Home tab integration test: jobs as primary content confirmed
- [ ] Zero TypeScript errors (`pnpm --filter mobile build`)
- [ ] Zero ESLint errors
- [ ] **Phase 2 FULL verification passes** (`=== MOB-B7 PART B FINAL VERIFICATION COMPLETE ===`):
  ```bash
  cd <repo>/frontend && pnpm --filter mobile build && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MOB-B7 PART B FINAL VERIFICATION COMPLETE ==="
  ```
- [ ] Final test count documented
- [ ] Completion Summary added to impl plan §Phase 0.9

---

## Completion Summary

After all DoD items, add a **Completion Summary** to `dev-docs/analysis/pilot-app-pre-wkstm-3-prep-plan.md` under Phase 0.9 — MOB-B7:

```markdown
### MOB-B7 — LOTO Gate + Create Customer + Today Tab: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: React Native Engineer
**Baseline**: X passed (mobile)
**Final**: X+N passed (+N new tests)

#### What Was Accomplished

- LOTO section now respects loto_confirmation_required tenant setting
- "Optional" badge shown when setting is false; section never hidden
- Create Customer form available from Customers tab "+" button
- Home tab refactored to show today's job schedule as primary content
- Voice CTA moved to compact secondary position

#### Files Changed / Created

| File | Action |
|---|---|
| Mobile MSW handlers | Updated |
| `features/jobs/hooks/useLotoPolicy.ts` | Created |
| `features/customers/hooks/useCreateCustomer.ts` | Created |
| `features/jobs/components/detail/LotoCheckSection.tsx` | Updated — policy gate |
| `features/customers/components/CreateCustomerBottomSheet.tsx` | Created |
| `features/customers/components/CustomersTabScreen.tsx` | Updated — "+" button |
| `app/(tabs)/(home)/index.tsx` | Updated — today-first layout |
```

---

## 🎉 Phase 0.9 Complete

**MOB-B7 is the final Phase 0.9 batch.** When this batch closes, all 9 Phase 0.9 batches are complete and the core product loop is fully operational across both web and mobile.

**Summary of Phase 0.9 exit criteria** (from `pilot-app-pre-wkstm-3-prep-plan.md`):
- ✅ Core product loop on web: Catalog → Customer → Quote → Send → Accept → Job → Invoice → Payment
- ✅ Dispatch board job card links to `/jobs/[id]` (FE-B21)
- ✅ Reports page returns data (FE-B17 Part B)
- ✅ Dashboard shows business intelligence (FE-B22, FE-B23)
- ✅ Mobile GPS clock-in and photo upload functional (MOB-B6)
- ✅ All P0 and P1 gaps from gap analysis addressed

Proceed to **Phase 1: Code Quality & Complexity Gates** per `pilot-app-pre-wkstm-3-prep-plan.md`.
