# Implementation Prompt: FE-B31 — Recurring Jobs Web UI

**Mode**: Pilot React Engineer  
**Batch**: FE-B31 (Recurring-Jobs-B1 — Web Frontend)  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §Phase 1 — Batch 10 (Recurring-Jobs-B1)  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-b21-design.md`  
**Estimated session**: 3–4 hours  
**Platform**: Web only (`apps/web`)  
**Backend companion**: B21 (Python Engineer) — **must be complete and `python export_openapi_json.py` run before starting**  
**Parallel batch**: MOB-B9 runs simultaneously — no dependency between FE-B31 and MOB-B9

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-b21-design.md`** — every section (A–I)

**Critical rules for this batch:**

- **Rule 1**: Run `pnpm sync-api-types` first. The 5 new recurrence rule endpoints were just added by B21. All payload types must come from `@pilot/shared-types` — no hand-written interfaces.
- **Rule 2**: Before writing any hook, verify endpoints in `backend/openapi_schema_map.md`. If `/api/v1/job-recurrence-rules` is NOT there → **STOP and ask Tom**.
- **Rule 3**: All API calls use `apiClient` from `@pilot/shared-api`. `fetch()` is permanently banned.
- **Rule 4**: Route files (`page.tsx`) are thin server components — no `"use client"`, no data fetching. All logic in feature components.
- **Rule 5**: The "Recurring" tab lives under the existing Jobs nav item — do NOT add a new top-level nav item. Add it as a tab alongside the existing job list.
- **Rule 6**: Check `packages/ui/src/index.ts` before creating any new component — reuse `<LoadingState>`, `<ErrorState>`, `<EmptyState>`, `<RoleGate>`.
- **Rule 7**: If ANY test fails — fix it before declaring done. No "pre-existing failure" exceptions.
- **Rule 8**: `pnpm --filter web test` is the ONLY correct test command. Never use `npx vitest run`.

---

## Design Decisions (Do Not Re-Litigate)

From Design Doc §G — these are final:

| Decision | Outcome | Rationale |
|---|---|---|
| Where does the rules list live? | New "Recurring" tab under existing Jobs nav (route `/jobs/recurring`) | Keeps jobs together; owner-facing only |
| First job on rule creation? | Yes — created immediately by backend; `first_job_id` in POST response | Owner sees result right away |
| Skip/bulk-edit/Nth-weekday in MVP? | ❌ P2 only | Scope control per Tom |
| Mobile rule creation? | Web-only for MVP | Complexity; mobile shows badge + banner only |
| Recurring badge on job cards? | ✅ Yes — on both web and mobile | PRD requirement |

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -5
```

Record the exact count. Fix any pre-existing failures before starting.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

Picks up all B21 recurrence rule endpoint types. Types come from `@pilot/shared-types` — never hand-written.

---

## Pre-Work: Verify Endpoints

```bash
grep -A 5 "job-recurrence-rules" backend/openapi_schema_map.md
```

Verified endpoints for this batch:
| Hook | Endpoint | Must confirm |
|---|---|---|
| `useCreateRecurrenceRule` | `POST /api/v1/job-recurrence-rules` | ✅ Confirm in openapi_schema_map.md |
| `useListRecurrenceRules` | `GET /api/v1/job-recurrence-rules` | ✅ Confirm |
| `useUpdateRecurrenceRule` | `PATCH /api/v1/job-recurrence-rules/{rule_id}` | ✅ Confirm |
| `useDeleteRecurrenceRule` | `DELETE /api/v1/job-recurrence-rules/{rule_id}` | ✅ Confirm |

---

## Pre-Work: Read These Source Files

```
frontend/apps/web/src/features/jobs/components/JobFormModal.tsx      ← WHY: understand current modal structure before extending with recurrence toggle
frontend/apps/web/src/features/jobs/components/JobsPage.tsx          ← WHY: understand current tab/list structure before adding Recurring tab + badge
frontend/apps/web/src/features/jobs/hooks/useCreateJob.ts            ← WHY: pattern reference for new mutation hooks
frontend/apps/web/src/features/jobs/hooks/useJobs.ts                 ← WHY: understand current JobListItem shape (has recurrence_rule_id?)
frontend/packages/ui/src/index.ts                                    ← WHY: confirm available shared components before creating new ones
frontend/packages/ui/src/role-gate/permissions.ts                    ← WHY: confirm jobs.create / jobs.edit permission keys exist
frontend/apps/web/src/mocks/handlers/jobs.ts                         ← WHY: understand existing job MSW handlers before extending
frontend/apps/web/src/mocks/handlers/index.ts                        ← WHY: confirm barrel before adding new handler
```

Also run:
```bash
# Check if JobListItem already has recurrence_rule_id from B21 sync
grep -n "recurrence_rule_id" frontend/packages/shared-types/src/api-schema.d.ts

# Find existing job form modal to understand its current shape
find frontend/apps/web/src/features/jobs -name "JobFormModal.tsx"

# Confirm CustomerCombobox and SiteCombobox exist (from FE-B28)
find frontend/apps/web/src/components -name "*.tsx" | head -20
```

---

## Context: What This Batch Does

| # | Step | What |
|---|---|---|
| 1 | 3 new hooks | `useCreateRecurrenceRule`, `useListRecurrenceRules`, `useUpdateRecurrenceRule` |
| 2 | Extend `JobFormModal` | Recurrence toggle + pattern/interval/date config (collapsed until checked) |
| 3 | Add recurring badge to job cards | `↻` indicator on `JobsPage` when `recurrence_rule_id` present |
| 4 | New "Recurring" tab in `JobsPage` | Shows `<RecurringJobsPage>` content |
| 5 | New `RecurringJobsPage` component | List of rules with pause/resume + delete |
| 6 | New route `/jobs/recurring/page.tsx` | Thin server component |
| 7 | MSW handlers | Cover all 4 endpoints |
| 8 | Tests | Integration tests in `__tests__/batch_fe_b31/` |

---

## STEP 1 — Create Hooks

### `features/jobs/hooks/useCreateRecurrenceRule.ts`

```typescript
// Read useCreateJob.ts for the established useMutation pattern before writing

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@pilot/shared-api";

interface RecurrenceRuleCreatePayload {
  customer_id: string;
  site_id: string;
  pattern: "daily" | "weekly" | "monthly" | "annually";
  interval_count?: number;  // default 1
  starts_on: string;        // ISO date string "YYYY-MM-DD"
  ends_on?: string | null;
  max_occurrences?: number | null;
  estimated_duration_minutes?: number | null;
  default_tech_user_id?: string | null;
  notes_template?: string | null;
}

export function useCreateRecurrenceRule() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: RecurrenceRuleCreatePayload) => {
      const response = await apiClient.post("/api/v1/job-recurrence-rules", payload);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recurrence-rules"] });
      queryClient.invalidateQueries({ queryKey: ["jobs"] }); // first job was created
    },
    retry: false,
  });
}
```

### `features/jobs/hooks/useListRecurrenceRules.ts`

```typescript
export function useListRecurrenceRules(isActive?: boolean) {
  return useQuery({
    queryKey: ["recurrence-rules", { isActive }],
    queryFn: async () => {
      const params = isActive !== undefined ? { is_active: isActive } : {};
      const response = await apiClient.get("/api/v1/job-recurrence-rules", { params });
      return response.data;  // { items: RecurrenceRuleListItem[], total: number }
    },
    staleTime: 30_000,
    retry: false,
  });
}
```

### `features/jobs/hooks/useUpdateRecurrenceRule.ts`

```typescript
export function useUpdateRecurrenceRule(ruleId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<{
      is_active: boolean;
      ends_on: string | null;
      max_occurrences: number | null;
      default_tech_user_id: string | null;
      notes_template: string | null;
      estimated_duration_minutes: number | null;
    }>) => {
      const response = await apiClient.patch(`/api/v1/job-recurrence-rules/${ruleId}`, payload);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recurrence-rules"] });
    },
    retry: false,
  });
}
```

---

## STEP 2 — Extend `JobFormModal` with Recurrence Toggle

Read `JobFormModal.tsx` in full before modifying. The recurrence section should appear at the bottom of the form, collapsed by default.

```tsx
// Add to JobFormModal state:
const [isRecurring, setIsRecurring] = useState(false);
const [recurrencePattern, setRecurrencePattern] = useState<"daily"|"weekly"|"monthly"|"annually">("weekly");
const [intervalCount, setIntervalCount] = useState(1);
const [startsOn, setStartsOn] = useState("");
const [endsOn, setEndsOn] = useState("");

// Modify form submit handler:
// When isRecurring = true AND customer/site are selected:
//   Call useCreateRecurrenceRule instead of useCreateJob
//   (or call both — create the rule which creates the first job automatically)
// When isRecurring = false: use existing useCreateJob flow

// UI section to add (after existing fields):
<div className="border-t pt-4 mt-4">
  <label className="flex items-center gap-2 cursor-pointer">
    <input
      type="checkbox"
      checked={isRecurring}
      onChange={(e) => setIsRecurring(e.target.checked)}
      data-testid="recurrence-toggle"
    />
    <span className="text-sm font-medium">Make this a recurring job</span>
  </label>

  {isRecurring && (
    <div className="mt-3 space-y-3 pl-6">
      {/* Pattern dropdown + interval */}
      <div className="flex items-center gap-2">
        <select value={recurrencePattern} onChange={(e) => setRecurrencePattern(e.target.value as any)} data-testid="recurrence-pattern">
          <option value="daily">Daily</option>
          <option value="weekly">Weekly</option>
          <option value="monthly">Monthly</option>
          <option value="annually">Annually</option>
        </select>
        <span className="text-sm text-neutral-500">every</span>
        <input type="number" min={1} value={intervalCount} onChange={(e) => setIntervalCount(+e.target.value)} className="w-16" data-testid="recurrence-interval" />
        <span className="text-sm text-neutral-500">
          {recurrencePattern === "daily" ? "day(s)" : recurrencePattern === "weekly" ? "week(s)" : recurrencePattern === "monthly" ? "month(s)" : "year(s)"}
        </span>
      </div>
      {/* Starts on */}
      <div>
        <label className="text-sm">Starts</label>
        <input type="date" value={startsOn} onChange={(e) => setStartsOn(e.target.value)} data-testid="recurrence-starts-on" />
      </div>
      {/* Ends on (optional) */}
      <div>
        <label className="text-sm">Ends (optional)</label>
        <input type="date" value={endsOn} onChange={(e) => setEndsOn(e.target.value)} data-testid="recurrence-ends-on" />
      </div>
    </div>
  )}
</div>
```

> **Read the file first.** Adjust classNames and field layout to match the existing modal's visual style.

**Intermediate check:**
```bash
pnpm --filter web test -- apps/web/src/features/jobs/ 2>&1 | tail -10
```

---

## STEP 3 — Add Recurring Badge to Job Cards in `JobsPage`

Read `JobsPage.tsx` first. Find where job rows/cards are rendered. Add a small `↻` badge when `job.recurrence_rule_id` is present:

```tsx
// In the job row/cell rendering, after the job number or title:
{job.recurrence_rule_id && (
  <span 
    className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-blue-50 text-blue-700"
    title="Recurring job"
    data-testid="recurring-badge"
  >
    ↻
  </span>
)}
```

> Verify `JobListItem` type has `recurrence_rule_id` after `pnpm sync-api-types`. If it's nullable: `job.recurrence_rule_id != null`.

---

## STEP 4 — Add "Recurring" Tab to `JobsPage`

Read `JobsPage.tsx` in full. Find where the existing tabs/navigation is implemented. Add a "Recurring" tab:

```tsx
// Find existing tab navigation in JobsPage and add:
<Link href="/jobs/recurring" data-testid="recurring-jobs-tab">
  Recurring
</Link>
```

The tab should be highlighted when the current path is `/jobs/recurring`. Use `usePathname()` from `next/navigation` to determine active state.

---

## STEP 5 — Create `RecurringJobsPage` Component

Create `features/jobs/components/RecurringJobsPage.tsx`:

```tsx
"use client";

import { useListRecurrenceRules } from "../hooks/useListRecurrenceRules";
import { useUpdateRecurrenceRule } from "../hooks/useUpdateRecurrenceRule";
import { LoadingState, ErrorState, EmptyState, RoleGate } from "@pilot/ui";

export function RecurringJobsPage() {
  const { data, isLoading, isError } = useListRecurrenceRules();

  if (isLoading) return <LoadingState />;
  if (isError) return <ErrorState message="Could not load recurring jobs" />;
  if (!data?.items.length) return (
    <EmptyState
      title="No recurring jobs"
      description="Create a recurring job from any job form to schedule automatic repeats."
    />
  );

  return (
    <RoleGate permission="jobs.view">
      <div className="space-y-3" data-testid="recurring-jobs-list">
        {data.items.map((rule) => (
          <RecurringRuleCard key={rule.id} rule={rule} />
        ))}
      </div>
    </RoleGate>
  );
}

function RecurringRuleCard({ rule }: { rule: any }) {
  const update = useUpdateRecurrenceRule(rule.id);

  const patternLabel = {
    daily: `Every ${rule.interval_count} day(s)`,
    weekly: `Every ${rule.interval_count} week(s)`,
    monthly: `Every ${rule.interval_count} month(s)`,
    annually: `Every ${rule.interval_count} year(s)`,
  }[rule.pattern] ?? rule.pattern;

  return (
    <div className="border rounded-lg p-4 flex items-center justify-between" data-testid="recurring-rule-card">
      <div>
        <div className="flex items-center gap-2">
          <span className="font-medium">↻</span>
          <span className="font-medium">{rule.customer_name ?? "—"}</span>
          <span className="text-neutral-500 text-sm">{rule.site_address ?? "—"}</span>
        </div>
        <div className="text-sm text-neutral-600 mt-1">
          {patternLabel}
          {rule.next_job_at && ` · Next: ${new Date(rule.next_job_at).toLocaleDateString()}`}
          {rule.default_tech_display_name && ` · ${rule.default_tech_display_name}`}
        </div>
      </div>
      <div className="flex items-center gap-2">
        <span className={`text-xs px-2 py-1 rounded ${rule.is_active ? "bg-green-100 text-green-700" : "bg-neutral-100 text-neutral-500"}`}>
          {rule.is_active ? "Active" : "Paused"}
        </span>
        <RoleGate permission="jobs.edit">
          <button
            onClick={() => update.mutate({ is_active: !rule.is_active })}
            data-testid={rule.is_active ? "pause-rule-btn" : "resume-rule-btn"}
            className="text-sm text-blue-600 hover:underline"
          >
            {rule.is_active ? "Pause" : "Resume"}
          </button>
        </RoleGate>
      </div>
    </div>
  );
}
```

> **Read `packages/ui/src/index.ts`** to confirm the exact import paths for `LoadingState`, `ErrorState`, `EmptyState`, `RoleGate` before using them.

---

## STEP 6 — Create Route `/jobs/recurring/page.tsx`

```tsx
// app/(authed)/jobs/recurring/page.tsx
// Thin server component — no "use client", no data fetching
import { RecurringJobsPage } from "@/features/jobs/components/RecurringJobsPage";

export default function RecurringJobsRoute() {
  return <RecurringJobsPage />;
}
```

---

## STEP 7 — Create MSW Handlers

Create `apps/web/src/mocks/handlers/recurrenceRuleHandlers.ts`:

```typescript
import { http, HttpResponse } from "msw";

export const MOCK_RECURRENCE_RULES = [
  {
    id: "rule-001",
    pattern: "weekly",
    interval_count: 1,
    customer_name: "Johnson Electrical",
    site_address: "123 Main St, Denver CO",
    next_job_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
    occurrences_created: 3,
    is_active: true,
    default_tech_display_name: "Jane Smith",
  },
  {
    id: "rule-002",
    pattern: "monthly",
    interval_count: 1,
    customer_name: "Smith Residence",
    site_address: "456 Oak Ave, Denver CO",
    next_job_at: null,
    occurrences_created: 1,
    is_active: false,
    default_tech_display_name: null,
  },
];

export const recurrenceRuleHandlers = [
  http.get("/api/v1/job-recurrence-rules", () =>
    HttpResponse.json({ items: MOCK_RECURRENCE_RULES, total: 2 })
  ),
  http.post("/api/v1/job-recurrence-rules", async ({ request }) => {
    const body = await request.json() as any;
    return HttpResponse.json({
      id: "rule-new-001",
      ...body,
      tenant_id: "tenant-001",
      occurrences_created: 1,
      next_job_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
      is_active: true,
      first_job_id: "job-new-001",
    }, { status: 201 });
  }),
  http.patch("/api/v1/job-recurrence-rules/:ruleId", async ({ request, params }) => {
    const body = await request.json() as any;
    const rule = MOCK_RECURRENCE_RULES.find(r => r.id === params.ruleId) ?? MOCK_RECURRENCE_RULES[0];
    return HttpResponse.json({ ...rule, ...body });
  }),
  http.delete("/api/v1/job-recurrence-rules/:ruleId", () =>
    new HttpResponse(null, { status: 204 })
  ),
];
```

Register in `apps/web/src/mocks/handlers/index.ts`:
```typescript
import { recurrenceRuleHandlers } from "./recurrenceRuleHandlers";
// Add to handlers array: ...recurrenceRuleHandlers
```

---

## STEP 8 — Write Tests

All tests in `apps/web/src/__tests__/batch_fe_b31/`.

### Test file 1: `recurring_jobs_page.integration.test.tsx`

Tests (5 total):
1. `test_recurring_page_renders` — `<RecurringJobsPage>` renders without crash; MSW returns 2 rules
2. `test_recurring_page_shows_rules` — customer name "Johnson Electrical" visible
3. `test_recurring_badge_on_job_card` — render job card with `recurrence_rule_id` set → `data-testid="recurring-badge"` present; job without rule → badge absent
4. `test_pause_rule_fires_patch` — click "Pause" button on active rule → `PATCH /api/v1/job-recurrence-rules/rule-001` called with `{ is_active: false }`
5. `test_empty_state` — override MSW to return empty list → `<EmptyState>` renders

### Test file 2: `job_form_recurrence_toggle.integration.test.tsx`

Tests (4 total):
1. `test_recurrence_toggle_hidden_by_default` — recurrence config section not visible initially
2. `test_recurrence_toggle_shows_config` — check `data-testid="recurrence-toggle"` → recurrence config section becomes visible
3. `test_recurrence_form_submits_to_rule_endpoint` — with toggle on + fields filled → POST to `/api/v1/job-recurrence-rules` (not `/api/v1/jobs`)
4. `test_recurrence_form_requires_starts_on` — submit without `starts_on` → form validation prevents submit

---

## Test Requirements

Per `frontend/react-engr-std-prompt-inclusions.md`:

- All tests in `__tests__/batch_fe_b31/`
- Use `vi.mock()` (not `jest.mock()`)
- Use `toBeInTheDocument()` for assertions
- Mock `next/navigation` for any component using `usePathname` or `useRouter`:
  ```typescript
  vi.mock("next/navigation", () => ({
    usePathname: () => "/jobs",
    useRouter: () => ({ push: vi.fn() }),
  }));
  ```
- TanStack Query wrapper with `retry: false` required
- MSW `setupServer` with `afterEach(() => server.resetHandlers())`

---

## Final Verification

> ❌ BANNED: `npx vitest run` — never use this.

### Phase 1 — Targeted

```bash
cd <repo>/frontend
pnpm --filter web test -- apps/web/src/__tests__/batch_fe_b31/ 2>&1 | tail -10
pnpm --filter web check-types 2>&1 | tail -5
```

### Phase 2 — Full

```bash
cd <repo>/frontend && pnpm --filter @pilot/ui check-types && pnpm --filter web check-types && pnpm --filter mobile build && pnpm --filter @pilot/ui lint && pnpm --filter web lint && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && pnpm --filter web test 2>&1 | tail -6 && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done — FE-B31

- [ ] Regression baseline captured — zero pre-existing failures (or confirmed with Tom)
- [ ] `pnpm sync-api-types` run — `recurrence_rule_id` on `JobListItem`, recurrence endpoints in types
- [ ] Design doc `batch-b21-design.md` read in full before coding
- [ ] All mandatory source files read before modifying
- [ ] All 4 recurrence rule endpoints confirmed in `openapi_schema_map.md`
- [ ] `useCreateRecurrenceRule` hook created and calls `POST /api/v1/job-recurrence-rules`
- [ ] `useListRecurrenceRules` hook created
- [ ] `useUpdateRecurrenceRule` hook created
- [ ] `JobFormModal` extended — recurrence toggle collapsed by default; when checked shows pattern/interval/dates; submit routes to rule endpoint
- [ ] Recurring `↻` badge on `JobsPage` job cards when `recurrence_rule_id` present
- [ ] "Recurring" tab added to Jobs nav in `JobsPage`
- [ ] `RecurringJobsPage` component created — list with pause/resume; `<RoleGate permission="jobs.view">` wrapping; `<EmptyState>` when no rules
- [ ] `/jobs/recurring/page.tsx` thin server component created
- [ ] `recurrenceRuleHandlers.ts` created; registered in `mocks/handlers/index.ts`
- [ ] 9 integration tests pass in `__tests__/batch_fe_b31/`
- [ ] Zero TypeScript errors (`pnpm --filter web check-types`)
- [ ] Zero ESLint warnings
- [ ] **Phase 2 FULL verification passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`)
- [ ] Final test count documented
- [ ] Completion Summary added to `pilot-launch-plan.md` §Phase 1 Batch 10

---

## Completion Summary

Add to `dev-docs/analysis/pilot-launch-plan.md` §Phase 1 Batch 10:

```markdown
### FE-B31 — Recurring Jobs Web UI: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed (web)
**Final**: X+N passed (+N new tests)

#### What Was Accomplished
- 3 TanStack Query hooks: useCreateRecurrenceRule, useListRecurrenceRules, useUpdateRecurrenceRule
- JobFormModal extended with collapsible recurrence toggle + config (pattern, interval, starts_on, ends_on)
- Recurring ↻ badge on job cards in JobsPage
- "Recurring" tab added to Jobs nav
- RecurringJobsPage — list with pause/resume + empty state
- /jobs/recurring route created

#### Files Changed / Created
| File | Action |
|---|---|
| `features/jobs/hooks/useCreateRecurrenceRule.ts` | Created |
| `features/jobs/hooks/useListRecurrenceRules.ts` | Created |
| `features/jobs/hooks/useUpdateRecurrenceRule.ts` | Created |
| `features/jobs/components/JobFormModal.tsx` | Updated — recurrence toggle |
| `features/jobs/components/JobsPage.tsx` | Updated — badge + Recurring tab |
| `features/jobs/components/RecurringJobsPage.tsx` | Created |
| `app/(authed)/jobs/recurring/page.tsx` | Created |
| `mocks/handlers/recurrenceRuleHandlers.ts` | Created |
| `mocks/handlers/index.ts` | Updated |

#### Tests Added
| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `batch_fe_b31/recurring_jobs_page.integration.test.tsx` | Integration | 5 | ✅ |
| `batch_fe_b31/job_form_recurrence_toggle.integration.test.tsx` | Integration | 4 | ✅ |
```
