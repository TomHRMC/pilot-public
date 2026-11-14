# Implementation Prompt: BETA-B6 — Reports Custom Date Range & Sidebar Permission Fix

**Mode**: Pilot React Engineer  
**Batch**: BETA-B6  
**Source plan**: `dev-docs/analysis/pilot-app-beta-fixes-v1-impl-plan.md` §8 BETA-B6  
**Estimated session**: 1–2 hours  
**No design doc required** — two small, well-defined changes  
**No backend work required** — pure frontend

---

## ⚠️ MANDATORY STOP: Read These Rules First

Before writing a single line of code, read:
- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full

Critical rules for this batch:
- **Rule 1.1**: Check `backend/openapi_schema_map.md` to confirm the Reports endpoint accepts `date_from`/`date_to` (verified in BETA-B2). Do not re-invent — `useProfitability` already accepts these params after BETA-B2.
- **Rule 2**: All API calls use `apiClient`.
- **Rule 7**: Check `packages/ui/src/index.ts` for any date picker components before installing new dependencies.

---

## Context: What This Batch Does

Two targeted fixes:

| Issue | Fix |
|---|---|
| 2.3a — Sidebar owner-only items use wrong permission key (`settings.manage` proxy) | Use explicit `<RoleGate>` or correct permission key for Reports, Operations, Sync sidebar items |
| 2.2 — Reports has no "Custom" date range period | Add `Custom` pill to `PeriodSelector` + date range picker UI that passes `date_from`/`date_to` to `useProfitability` |

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -5
```

---

## Pre-Work: Read These Files First

```bash
# Task 1 — sidebar RBAC
cat frontend/apps/web/src/components/AppSidebar.tsx
cat frontend/packages/ui/src/role-gate/permissions.ts

# Task 2 — period selector
cat frontend/apps/web/src/features/profitability/components/PeriodSelector.tsx
cat frontend/apps/web/src/features/profitability/hooks/useProfitability.ts

# Check what shadcn date picker components are available:
ls frontend/apps/web/src/components/ui/ | grep -i date
```

Read every file with `read_file` before writing any code. Do not assume what they contain.

---

## Task 1: Fix Sidebar Owner-Only Permission Gate

**Issue 2.3a**: The `<AppSidebar>` currently hides Reports, Operations, and Sync items using `useRequiresPermission("settings.manage")` as a proxy. This is fragile — if the permission system changes, the wrong items could show/hide.

### Step 1a: Read `permissions.ts` current state

After BETA-B3 and BETA-B4, `permissions.ts` now contains:
- `customers.view`, `quotes.view`, `invoices.view` (BETA-B3)
- `integrations.manage`, `settings.tenant.write`, `billing.view` (BETA-B4)
- `reports.view` — may already exist (check the file)

If `reports.view` does not exist, add it:

```typescript
// Add to PermissionKey type union:
| "reports.view"     // Reports page access — owner, office_staff, operator
```

Add to `ROLE_PERMISSION_MAP`:
| Permission | owner | office_staff | tech | operator |
|---|---|---|---|---|
| `reports.view` | ✅ | ✅ | ❌ | ✅ |

### Step 1b: Update `AppSidebar.tsx`

Read the actual file first. Find where Reports, Operations, and Sync sidebar items are gated.

**Current approach** (verify this is what exists):
```tsx
// Likely uses:
useRequiresPermission("settings.manage")
// or:
<RoleGate permission="settings.manage">
```

**Target approach** — use the specific permission key for each item:

```tsx
// Reports: use reports.view (already has real data; financial surface)
<RoleGate permission="reports.view">
  <SidebarItem href="/reports" ... />
</RoleGate>

// Operations: use settings.tenant.write (BETA-B4 addition; owners/operators only)
<RoleGate permission="settings.tenant.write">
  <SidebarItem href="/operations" ... />
</RoleGate>

// Sync: use settings.tenant.write (same rationale)
<RoleGate permission="settings.tenant.write">
  <SidebarItem href="/sync" ... />
</RoleGate>
```

> **Read the actual sidebar file first.** The RBAC gating may be implemented differently (using `useRequiresPermission` inline, or a `roleRequired` prop on a shared sidebar item component). Adjust the implementation to match the actual code pattern in the file, not the pseudocode above.

> **If `settings.tenant.write` permission key was not yet added** (BETA-B4 may not have run yet): use `settings.manage` for Operations and Sync as a safe proxy (same as current) and document that it will be updated once BETA-B4 runs. Do not add `settings.tenant.write` here if BETA-B4 hasn't added it yet — check `permissions.ts` first.

### Tests for Task 1

```typescript
// Unit test for new permissions.ts entries (if reports.view was added)
// File: packages/ui/src/role-gate/__tests__/permissions.beta-b6.test.ts

it("tech does NOT have reports.view", () => {
  expect(ROLE_PERMISSION_MAP.tech).not.toContain("reports.view");
});

it("owner has reports.view", () => {
  expect(ROLE_PERMISSION_MAP.owner).toContain("reports.view");
});

it("office_staff has reports.view", () => {
  expect(ROLE_PERMISSION_MAP.office_staff).toContain("reports.view");
});
```

Integration test:
```typescript
// apps/web/__tests__/batch_beta_v1_b6/sidebar-rbac.integration.test.tsx
// Test: owner sees Reports/Operations/Sync; tech does not
```

---

## Task 2: Add "Custom" Date Range to Reports `PeriodSelector`

**Issue 2.2**: The `<PeriodSelector>` component shows only 4 period pills (7d, 30d, MTD, YTD). "Custom" was designed but not implemented. It requires a date range picker UI + `date_from`/`date_to` params.

**Prerequisite**: BETA-B2 must be complete — `useProfitability` must already accept `date_from` and `date_to` params directly. Verify this before implementing:

```bash
grep -n "date_from\|customDateFrom\|custom" frontend/apps/web/src/features/profitability/hooks/useProfitability.ts
```

If BETA-B2 is not done, this task cannot be completed — `useProfitability` still sends `?period=` and will return 422.

### Step 2a: Check available date picker components

```bash
ls frontend/apps/web/src/components/ui/ | grep -i date
```

If a shadcn `<DateRangePicker>` or `<Calendar>` component exists, use it. If not, check:
```bash
cat frontend/apps/web/package.json | grep -E "react-day-picker|date-picker|calendar"
```

**Do NOT install new dependencies** without verifying what's already available. If no date picker component exists, use two standard `<input type="date">` HTML inputs (clean, accessible, no dependency). This is the MVP-appropriate approach.

### Step 2b: Update `PeriodSelector.tsx`

Read the actual file first. Then:

1. Add `{ value: "custom", label: "Custom" }` to the `PERIODS` array (preserve exact array structure of existing file)

2. The component needs to handle the custom state. When "Custom" is selected:
   - Show a date range picker (or two date inputs) inline below the pills
   - Pass the selected dates up via props

The `PeriodSelector` likely already receives an `onPeriodChange` or `activePeriod` callback. Read the actual props interface before modifying.

**Extended props interface** (adjust to match actual current interface):

```typescript
interface PeriodSelectorProps {
  activePeriod: string;
  onPeriodChange: (period: string) => void;
  // New for BETA-B6:
  customDateFrom?: string;       // YYYY-MM-DD
  customDateTo?: string;         // YYYY-MM-DD
  onCustomDatesChange?: (from: string, to: string) => void;
}
```

**Date picker rendering** (when `activePeriod === "custom"`):

```tsx
{activePeriod === "custom" && (
  <div className="flex items-center gap-2 mt-3">
    <label className="text-xs text-neutral-600 flex-shrink-0">From</label>
    <input
      type="date"
      value={customDateFrom ?? ""}
      onChange={(e) => onCustomDatesChange?.(e.target.value, customDateTo ?? "")}
      max={customDateTo ?? undefined}
      className="px-2 py-1 text-sm border border-neutral-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-400"
    />
    <label className="text-xs text-neutral-600 flex-shrink-0">To</label>
    <input
      type="date"
      value={customDateTo ?? ""}
      onChange={(e) => onCustomDatesChange?.(customDateFrom ?? "", e.target.value)}
      min={customDateFrom ?? undefined}
      max={new Date().toISOString().slice(0, 10)}
      className="px-2 py-1 text-sm border border-neutral-200 rounded-md focus:outline-none focus:ring-2 focus:ring-brand-400"
    />
  </div>
)}
```

### Step 2c: Update `ProfitabilityPage.tsx` (or wherever `PeriodSelector` is consumed)

Read the consuming component to understand how `activePeriod` and `onPeriodChange` are currently wired. Then:

1. Add state for custom dates:
   ```typescript
   const [customDateFrom, setCustomDateFrom] = useState("");
   const [customDateTo, setCustomDateTo] = useState("");
   ```

2. Pass to `PeriodSelector`:
   ```tsx
   <PeriodSelector
     activePeriod={activePeriod}
     onPeriodChange={setActivePeriod}
     customDateFrom={customDateFrom}
     customDateTo={customDateTo}
     onCustomDatesChange={(from, to) => {
       setCustomDateFrom(from);
       setCustomDateTo(to);
     }}
   />
   ```

3. Wire custom dates to `useProfitability`:
   ```typescript
   // In useProfitability or its calling component:
   // When activePeriod === 'custom', pass customDateFrom/customDateTo directly
   // When activePeriod !== 'custom', use the period conversion logic from BETA-B2
   
   const shouldUseDates = activePeriod === "custom" && customDateFrom && customDateTo;
   
   const { data, isLoading, isError } = useProfitability(
     shouldUseDates
       ? { date_from: customDateFrom, date_to: customDateTo }
       : { period: activePeriod }
   );
   ```

   > **Read `useProfitability.ts` first** (after BETA-B2 updates) to understand its exact signature before wiring this.

4. The API call should NOT fire when "Custom" is selected but dates are incomplete (both `customDateFrom` and `customDateTo` must be set):
   ```typescript
   // In useProfitability or the hook call:
   enabled: activePeriod !== "custom" || (!!customDateFrom && !!customDateTo)
   ```

### Tests for Task 2

**Unit tests** (co-located with `PeriodSelector.tsx`):

```typescript
// PeriodSelector.test.tsx additions

it("renders Custom pill", () => {
  render(<PeriodSelector activePeriod="7d" onPeriodChange={vi.fn()} />);
  expect(screen.getByText("Custom")).toBeInTheDocument();
});

it("shows date inputs when Custom is selected", () => {
  render(<PeriodSelector activePeriod="custom" onPeriodChange={vi.fn()} />);
  expect(screen.getByLabelText(/from/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/to/i)).toBeInTheDocument();
});

it("does not show date inputs when non-custom period selected", () => {
  render(<PeriodSelector activePeriod="7d" onPeriodChange={vi.fn()} />);
  expect(screen.queryByLabelText(/from/i)).not.toBeInTheDocument();
});

it("calls onCustomDatesChange when from date changes", async () => {
  const user = userEvent.setup();
  const onCustomDatesChange = vi.fn();
  render(
    <PeriodSelector
      activePeriod="custom"
      onPeriodChange={vi.fn()}
      customDateFrom=""
      customDateTo=""
      onCustomDatesChange={onCustomDatesChange}
    />
  );
  const fromInput = screen.getByLabelText(/from/i);
  await user.type(fromInput, "2026-06-01");
  expect(onCustomDatesChange).toHaveBeenCalledWith("2026-06-01", "");
});
```

**Integration test**:

```typescript
// apps/web/__tests__/batch_beta_v1_b6/reports-custom-date.integration.test.tsx

it("custom period passes date_from and date_to to profitability API", async () => {
  const user = userEvent.setup();
  render(<ProfitabilityPage />);

  // Select Custom pill
  await user.click(screen.getByText("Custom"));
  
  // Fill in dates
  await user.type(screen.getByLabelText(/from/i), "2026-05-01");
  await user.type(screen.getByLabelText(/to/i), "2026-05-31");
  
  // Verify API called with correct params (check MSW captured request)
  // MSW should capture: date_from=2026-05-01, date_to=2026-05-31
});

it("API is NOT called when Custom is selected but dates are incomplete", async () => {
  // Select Custom but only fill in date_from — API should not fire
});
```

---

## Final Verification

```bash
cd <repo>/frontend && pnpm --filter @pilot/ui check-types && pnpm --filter web check-types && pnpm --filter mobile build && pnpm --filter @pilot/ui lint && pnpm --filter web lint && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && pnpm --filter web test 2>&1 | tail -6 && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```

---

## Definition of Done — BETA-B6

Update the `pilot-app-beta-fixes-v1-impl-plan.md` §9 Batch Completion Tracker:

- [ ] Pre-modification regression baseline captured
- [ ] `AppSidebar.tsx` read before modification
- [ ] `permissions.ts` read — current state confirmed
- [ ] `PeriodSelector.tsx` read before modification
- [ ] `useProfitability.ts` read — confirmed BETA-B2 date params are in place
- [ ] **Task 1**: `reports.view` permission key added to `permissions.ts` (if not already present)
- [ ] **Task 1**: `reports.view` in `ROLE_PERMISSION_MAP` — owner/office_staff/operator have it; tech does not
- [ ] **Task 1**: Reports sidebar item gated on `reports.view` (not `settings.manage` proxy)
- [ ] **Task 1**: Operations sidebar item gated on correct permission key
- [ ] **Task 1**: Sync sidebar item gated on correct permission key
- [ ] **Task 1**: Permissions unit test passes
- [ ] **Task 1**: Sidebar RBAC integration test passes
- [ ] **Task 2**: `PERIODS` array in `PeriodSelector` includes `{ value: "custom", label: "Custom" }`
- [ ] **Task 2**: Selecting "Custom" shows date range inputs (From / To)
- [ ] **Task 2**: Date inputs do not show for non-custom periods
- [ ] **Task 2**: Custom dates wire to `useProfitability` with `date_from` / `date_to`
- [ ] **Task 2**: API does NOT fire when "Custom" selected but dates incomplete
- [ ] **Task 2**: No new npm dependencies added (using `<input type="date">` or existing shadcn component)
- [ ] PeriodSelector unit tests pass (4 new tests minimum)
- [ ] Reports custom date integration test passes
- [ ] Zero TypeScript errors
- [ ] Zero ESLint `no-hardcoded-design-values` warnings
- [ ] No regressions in pre-existing test suite
- [ ] Full verification command passes (`=== MVP FINAL VERIFICATION COMPLETE ===`)
- [ ] Update this Definition of Done list with completion checks next to each item if completed
- [ ] Final test count (before/after) documented in impl plan tracker in the source plan
- [ ] Summary of work accomplished added to new sub-section in impl plan tracker in Section 9 in the source plan after the last batch entry
