# Implementation Prompt: MOB-B9 — Recurring Jobs Mobile UI (Badge + Detail Banner)

**Mode**: Pilot React Engineer  
**Batch**: MOB-B9 (Recurring-Jobs-B1 — Mobile)  
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §Phase 1 — Batch 10 (Recurring-Jobs-B1)  
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-b21-design.md`  
**Estimated session**: 1–2 hours  
**Platform**: Mobile only (`apps/mobile`)  
**Backend companion**: B21 (Python Engineer) — must be complete and `python export_openapi_json.py` run before starting  
**Parallel batch**: FE-B31 runs simultaneously — no dependency between MOB-B9 and FE-B31

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full
- **`dev-docs/architecture-design/batch-designs/batch-b21-design.md`** — §H (surface mockups) and §I (component manifest) in particular

**Critical rules for this batch:**

- **Rule 1**: `pnpm sync-api-types` first — `recurrence_rule_id` on job response types comes from B21's OpenAPI export.
- **Rule 2**: Mobile is **read-only** for recurring jobs in MVP — no create/edit of rules. Only show a badge and an informational banner. Do NOT add any form or navigation to create recurrence rules from mobile.
- **Rule 3**: All mobile integration tests go in `__tests__/batch_mob_b9/` — never co-located with source.
- **Rule 4**: WatermelonDB must be mocked in all tests. Expo Router must be mocked in all screen tests.
- **Rule 5**: Use `.toBeTruthy()` / `not.toBeNull()` (not `toBeInTheDocument()` — that's jsdom/web only).
- **Rule 6**: `pnpm --filter mobile build` = mobile type check. There is no `check-types` script for mobile.
- **Rule 7**: If ANY test fails — fix it before declaring done.
- **Rule 8**: No new npm dependencies without checking `apps/mobile/package.json` first.

---

## Design Decisions (Do Not Re-Litigate)

| Decision | Outcome |
|---|---|
| Mobile create/edit of recurrence rules? | ❌ Web-only for MVP |
| What mobile shows | `↻` badge on job cards + "Part of recurring series" informational banner on job detail |
| Navigation from mobile banner | Static "Manage on web" text — no deep link required for MVP |
| Where the banner lives | At the top of job detail, above the main content |

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter mobile test 2>&1 | tail -8
```

Record exact count. Fix any pre-existing failures before starting.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
```

Picks up `recurrence_rule_id` on job-related types from B21.

---

## Pre-Work: Verify Endpoint Types

```bash
# Confirm recurrence_rule_id is now on job types
grep -n "recurrence_rule_id" frontend/packages/shared-types/src/api-schema.d.ts
```

This field is nullable — present when a job is part of a recurring series, `null` otherwise.

---

## Pre-Work: Read These Source Files

```
frontend/apps/mobile/features/jobs/                     ← WHY: find job card component(s) and job detail screen before modifying
frontend/apps/mobile/app/(tabs)/(home)/index.tsx        ← WHY: Today tab — find job card rendering for badge addition
frontend/apps/mobile/constants/style-constants.ts       ← WHY: get colour/spacing tokens before hardcoding values
frontend/apps/mobile/mocks/handlers/index.ts            ← WHY: understand barrel before adding new handler
```

Also run:
```bash
# Find job card component(s) in mobile
find frontend/apps/mobile/features/jobs -name "*.tsx" | head -20

# Find job detail screen
find frontend/apps/mobile/features/jobs -name "*Detail*" -o -name "*detail*" | head -10

# Find the job list / today tab job rendering
grep -rn "job_number\|JobCard\|jobItem" frontend/apps/mobile/app/(tabs)/(home)/ --include="*.tsx" | head -10

# Confirm recurrence_rule_id available on useJobs / job hooks
grep -rn "recurrence_rule_id\|JobListItem\|JobResponse" frontend/apps/mobile/features/jobs/ --include="*.ts" | head -10
```

---

## Context: What This Batch Does

| # | Step | What | Where |
|---|---|---|---|
| 1 | Recurring badge | `↻` indicator on job cards in Today tab + job list | `features/jobs/` card component + `app/(tabs)/(home)/index.tsx` |
| 2 | Recurring banner | "Part of recurring series (Weekly)" + "Manage on web →" text on job detail | Job detail screen/component |
| 3 | MSW handler extension | Add `recurrence_rule_id` to existing job mock fixtures | Existing job handlers |
| 4 | Tests | Integration tests in `__tests__/batch_mob_b9/` | |

---

## STEP 1 — Add Recurring Badge to Job Cards

Read the job card component(s) and Today tab before modifying. Find where the job number, status, or title is rendered on each card. Add a small recurring indicator when `recurrence_rule_id` is present.

```tsx
// In the job card component — find the exact location by reading the file first:
{job.recurrence_rule_id && (
  <Text
    style={styles.recurringBadge}
    testID="recurring-badge"
  >
    ↻
  </Text>
)}

// In styles (use tokens from constants/style-constants.ts — do not hardcode):
recurringBadge: {
  fontSize: 12,
  color: /* use blue/info token */,
  marginLeft: 4,
},
```

Apply this same badge pattern to **both**:
1. Job cards in the **Today tab** (`app/(tabs)/(home)/index.tsx` — wherever jobs are rendered)
2. Job cards in the **Jobs tab** (`features/jobs/` — the main job list screen)

> Read each file first. The exact component structure differs between Today tab and Jobs tab.

---

## STEP 2 — Add Recurring Banner to Job Detail Screen

Read the job detail screen/component before modifying. Find the top of the content area (below the header, above the main sections). Add the informational banner:

```tsx
{/* Add near the top of job detail content, after header/status */}
{job.recurrence_rule_id && (
  <View style={styles.recurringBanner} testID="recurring-series-banner">
    <Text style={styles.recurringBannerText}>
      ↻ Part of a recurring series
      {job.recurrence_pattern && ` (${formatPattern(job.recurrence_pattern)})`}
    </Text>
    <Text style={styles.recurringBannerSubtext}>
      Manage schedule on web
    </Text>
  </View>
)}
```

```typescript
// Helper function — add near the component or in a utils file:
function formatPattern(pattern: string): string {
  const labels: Record<string, string> = {
    daily: "Daily",
    weekly: "Weekly",
    monthly: "Monthly",
    annually: "Annual",
  };
  return labels[pattern] ?? pattern;
}
```

> **Note**: `job.recurrence_pattern` may not be on the job response — the job model only has `recurrence_rule_id`. If `recurrence_pattern` is not available on the job response (verify in the types after `pnpm sync-api-types`): just show "↻ Part of a recurring series" without the pattern label. Do NOT make an extra API call to fetch the rule — keep it simple.

Banner styles (use tokens — do not hardcode hex or px):
```typescript
recurringBanner: {
  backgroundColor: /* light blue surface token */,
  borderRadius: 8,
  padding: 12,
  marginHorizontal: 16,
  marginBottom: 12,
},
recurringBannerText: {
  fontSize: 14,
  fontWeight: "500",
  /* blue/info colour token */
},
recurringBannerSubtext: {
  fontSize: 12,
  marginTop: 2,
  /* neutral/muted colour token */
},
```

---

## STEP 3 — Update MSW Mock Fixtures

Find existing job MSW handlers in `mocks/handlers/`. Add `recurrence_rule_id` to at least one job fixture so tests can assert on the badge/banner:

```typescript
// In existing job mock data (find the file — do not create a duplicate handler):
// Add to one of the mock job objects:
{
  ...existingJobFields,
  recurrence_rule_id: "rule-mock-001",   // triggers badge + banner
}

// Keep at least one job WITHOUT recurrence_rule_id (null) to test the negative case
```

Do NOT create a new separate handler file if the job handlers already exist. Extend the existing job fixture/handler.

Register in `mocks/handlers/index.ts` if any new handlers were added.

---

## STEP 4 — Write Tests

All tests in `frontend/apps/mobile/__tests__/batch_mob_b9/`.

### Test file: `__tests__/batch_mob_b9/recurring_job_indicators.test.tsx`

Required mocks at top of file:
```typescript
jest.mock("expo-router", () => ({
  useRouter: () => ({ push: jest.fn(), back: jest.fn() }),
  useLocalSearchParams: () => ({}),
  router: { push: jest.fn(), back: jest.fn() },
  Link: ({ children }: any) => children,
}));

jest.mock("../../../database", () => ({
  database: {
    write: jest.fn((fn: any) => fn()),
    get: jest.fn(() => ({
      create: jest.fn((fn: any) => {
        const record = { id: "mock-id" };
        fn(record);
        return Promise.resolve(record);
      }),
    })),
  },
}));
```

Tests (5 total):

1. `test_recurring_badge_visible_on_card_with_rule` — render a job card with `recurrence_rule_id: "rule-001"` → `getByTestId("recurring-badge")` is truthy
2. `test_recurring_badge_absent_on_card_without_rule` — render a job card with `recurrence_rule_id: null` → `queryByTestId("recurring-badge")` is null
3. `test_recurring_banner_visible_on_detail_with_rule` — render job detail with `recurrence_rule_id: "rule-001"` → `getByTestId("recurring-series-banner")` is truthy; contains "recurring series" text
4. `test_recurring_banner_absent_on_detail_without_rule` — render job detail with `recurrence_rule_id: null` → `queryByTestId("recurring-series-banner")` is null
5. `test_recurring_banner_shows_manage_text` — job detail with rule → "Manage" text present in banner

---

## Final Verification

### Phase 1 — Targeted (after each step)

```bash
cd <repo>/frontend
pnpm --filter mobile test -- __tests__/batch_mob_b9/ 2>&1 | tail -10
pnpm --filter mobile build 2>&1 | tail -5
```

### Phase 2 — Full verification

```bash
cd <repo>/frontend && pnpm --filter @pilot/ui check-types && pnpm --filter web check-types && pnpm --filter mobile build && pnpm --filter @pilot/ui lint && pnpm --filter web lint && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && pnpm --filter web test 2>&1 | tail -6 && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done — MOB-B9

Update `dev-docs/analysis/pilot-launch-plan.md` §Phase 1 Batch 10:

- [ ] Regression baseline captured — zero pre-existing mobile failures (or confirmed with Tom)
- [ ] `pnpm sync-api-types` run — `recurrence_rule_id` visible on job types
- [ ] Design doc `batch-b21-design.md` §H and §I read before coding
- [ ] All mandatory source files read before modifying (job card component, job detail screen, handlers/index.ts)
- [ ] `recurrence_rule_id` confirmed on job type after `pnpm sync-api-types`
- [ ] **STEP 1**: Recurring `↻` badge added to job cards in Today tab AND Jobs tab — `testID="recurring-badge"`; badge absent when `recurrence_rule_id` is null
- [ ] **STEP 2**: Recurring banner added to job detail screen — `testID="recurring-series-banner"`; contains "recurring series" + "Manage" text; banner absent when `recurrence_rule_id` is null
- [ ] **STEP 3**: At least one job MSW fixture updated with `recurrence_rule_id: "rule-mock-001"` for testing; registered in `mocks/handlers/index.ts` if new file created
- [ ] 5 tests pass in `__tests__/batch_mob_b9/recurring_job_indicators.test.tsx`
- [ ] Zero TypeScript errors (`pnpm --filter mobile build`)
- [ ] Zero ESLint warnings
- [ ] No regressions in mobile test suite
- [ ] **Phase 2 FULL verification passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`)
- [ ] Final test count documented
- [ ] Completion Summary added to `pilot-launch-plan.md` §Phase 1 Batch 10

---

## Completion Summary

Add to `dev-docs/analysis/pilot-launch-plan.md` §Phase 1 Batch 10:

```markdown
### MOB-B9 — Recurring Jobs Mobile UI: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot React Engineer
**Baseline**: X passed (mobile)
**Final**: X+5 passed (+5 new tests)

#### What Was Accomplished
- Recurring ↻ badge added to job cards in Today tab and Jobs tab (present when recurrence_rule_id non-null)
- "Part of recurring series" banner added to job detail screen with "Manage on web" text
- MSW job fixture updated with recurrence_rule_id for testing

#### Files Changed / Created
| File | Action |
|---|---|
| Job card component(s) | Updated — ↻ badge when recurrence_rule_id present |
| Job detail screen | Updated — recurring series banner |
| `mocks/handlers/[job handlers file]` | Updated — recurrence_rule_id in fixtures |
| `__tests__/batch_mob_b9/recurring_job_indicators.test.tsx` | Created — 5 tests |

#### Tests Added
| Test File | Type | Tests | All Pass |
|---|---|---|---|
| `__tests__/batch_mob_b9/recurring_job_indicators.test.tsx` | Integration | 5 | ✅ |
```
