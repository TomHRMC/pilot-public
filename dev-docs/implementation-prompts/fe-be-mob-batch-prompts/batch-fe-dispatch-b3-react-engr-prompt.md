# Implementation Prompt: DISPATCH-B3 — Dispatch Filter Data Fix + Panel Classification Chips

**Mode**: Pilot React Engineer
**Batch**: DISPATCH-B3 (Frontend web)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.3 DISPATCH-B3
**Backend companion**: CLASS-B1 ✅ **COMPLETE (2026-07-27)** — `DispatchBoardJobEntry` now returns real `priority`/`customer_type`/`site_type`/`job_type_code`/`job_type_label`.
**Estimated session**: 2.5–3.5 hours
**Platform**: Web only (`apps/web`)
**Depends on**: CLASS-B1 (+ `pnpm sync-api-types`) · DISPATCH-B2 ✅ (FilterBar exists)

---

## ⚠️ MANDATORY STOP: Read These First

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full

Critical rules for this batch:

- **Rule 1.3**: Run `pnpm sync-api-types` FIRST — CLASS-B1 changed the OpenAPI contract. The new `DispatchBoardJobEntry` fields (`priority`, `customer_type`, `site_type`, `job_type_code`, `job_type_label`) come from `@pilot/shared-types`, not hand-written.
- **Rule 2**: All API via `apiClient`. `fetch()` banned.
- **Rule 7**: Reuse the DISPATCH-B2 components — `FilterBar`, `FilterPill`, `TechFilterPopover` already exist. Do NOT recreate them; edit them.
- **Rule 10**: Any failing test — even apparently pre-existing — fixed before done. Root cause unclear → STOP and ask Tom.

**Seed-Data Awareness (new backend fields — react-engr-std-prompt-inclusions.md §18):** CLASS-B1 seeded **real, varied** values (dispatch scenario: 1 `emergency`, 1 `urgent`, 4 `standard`; sites commercial/residential; job_type per job). The old hardcoded `normalizeJob` fallbacks are now WRONG and must be deleted. Update MSW fixtures so at least one mock job carries a non-default value for each new field — a fixture where every row is identical cannot prove a filter works. Assert by specific value, never by count.

---

## Design Decisions (Do Not Re-Litigate)

The classification concepts were untangled in CLASS-B1 (Tom-approved 2026-07-27). Final values — verified in the live DB + OpenAPI:

| Dimension | Values (exact) | Source |
|---|---|---|
| **Priority** | `standard` · `urgent` · `emergency` | `job.priority` (was the phantom `rush/warranty/standard`) |
| **Customer Type** | `person` · `company` | `customer.type` (was the phantom `commercial/residential`) |
| **Site Type** | `commercial` · `residential` · `industrial` | `site.site_type` (net-new; display-only in dispatch) |
| **Job Type** | dynamic from API (`job_type_code`/`job_type_label`) | `GET /api/v1/job-types` — 11 platform defaults + tenant overrides |

**Key correction**: The dispatch board's "Customer Type" filter was mislabeled `commercial/residential` — that concept now lives on **site** (`site_type`), not customer. The customer-type **filter** dimension becomes **person/company**. `site_type` is **display-only** in dispatch (a chip on the panel), NOT a new filter dimension in this batch.

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/frontend
pnpm --filter web test 2>&1 | tail -5
```
Record the count. Fix any pre-existing failure (or confirm with Tom) before starting.

---

## Pre-Work: Sync API Types

```bash
cd <repo>/frontend
pnpm sync-api-types
grep -A 40 "DispatchBoardJobEntry" frontend/packages/shared-types/src/api-schema.d.ts | grep -E "priority|customer_type|site_type|job_type_code|job_type_label"
```
All five must appear. If not → CLASS-B1 isn't synced. STOP and confirm with Tom.

---

## Pre-Work: Verify Endpoints

```bash
grep -A 6 "job-types" backend/openapi_schema_map.md
grep -A 30 "scheduling/dispatch-board" backend/openapi_schema_map.md | grep -E "priority|customer_type|site_type|job_type"
```
`GET /api/v1/job-types` returns `[{id, code, label, sort_order, is_active, is_tenant_override}]` — confirmed.

---

## Pre-Work: Read These Source Files

```
frontend/apps/web/src/features/dispatch-board/hooks/useDispatchBoard.ts        ← DELETE hardcoded priority/customer_type fallbacks (~:127); carry real values through normalizeJob + RawJobEntry
frontend/apps/web/src/features/dispatch-board/types-stub.ts                    ← DispatchBoardJob priority/customer_type/job_type unions to correct; add site_type, job_type_code/label
frontend/apps/web/src/features/dispatch-board/store.ts                          ← DispatchBoardFilters: priorities + customerTypes union values to correct
frontend/apps/web/src/features/dispatch-board/components/FilterBar.tsx           ← PRIORITY_PILLS + CUSTOMER_TYPE_PILLS to correct (currently rush/warranty + commercial/residential)
frontend/apps/web/src/features/dispatch-board/components/FilterPill.tsx          ← reuse as-is (no change expected)
frontend/apps/web/src/features/dispatch-board/components/TechFilterPopover.tsx   ← reuse as-is
frontend/apps/web/src/features/dispatch-board/components/DispatchBoardPage.tsx   ← applyFilters(); FilterBar wiring; JobPropertiesPanel mount
frontend/apps/web/src/features/dispatch-board/components/JobPropertiesPanel.tsx  ← add read-only classification chips
frontend/apps/web/src/mocks/handlers/dispatchBoardHandlers.ts                    ← add real varied classification values to fixtures
frontend/apps/web/src/mocks/handlers/index.ts                                    ← confirm handler registration
```

Locate the hardcoded fallbacks + filter application:
```bash
grep -n "priority:\|customer_type:\|job_type:" frontend/apps/web/src/features/dispatch-board/hooks/useDispatchBoard.ts
grep -n "priorities\|customerTypes\|jobTypes" frontend/apps/web/src/features/dispatch-board/components/DispatchBoardPage.tsx
```

---

## Context: What This Batch Does

CLASS-B1 gave the dispatch board real classification data. This batch makes the FE consume it: kill the hardcoded fallbacks, correct the filter value sets to match the real schema, and surface the data as read-only chips on the properties panel.

| Area | Change |
|---|---|
| `useDispatchBoard.ts` | Delete hardcoded `priority:"standard"` / `customer_type:"commercial"` / `job_type:""`; read real values from `RawJobEntry`; add `site_type`, `job_type_code`, `job_type_label` |
| `types-stub.ts` | `priority: 'standard'\|'urgent'\|'emergency'`; `customer_type: 'person'\|'company'`; add `site_type`, `job_type_code`, `job_type_label` |
| `store.ts` | `DispatchBoardFilters.priorities` → urgent set; `.customerTypes` → person/company |
| `FilterBar.tsx` | `PRIORITY_PILLS` → Standard/Urgent/Emergency; `CUSTOMER_TYPE_PILLS` → Person/Company |
| `JobPropertiesPanel.tsx` | Read-only chips: priority, customer type, site type, job type |
| MSW | Fixtures carry varied real values |

> **Note (already shipped, do not redo)**: the Techs-popover "always empty" fix (sourcing from `useTenantUsers`) landed as DISPATCH-B2-FIX. Leave that wiring as-is.

---

## STEP 1 — `types-stub.ts`: correct the unions + add fields

Read the file. Update `DispatchBoardJob`:
- `priority: "standard" | "urgent" | "emergency"` (was `rush/standard/warranty`)
- `customer_type: "person" | "company"` (was `commercial/residential`)
- Add `site_type?: "commercial" | "residential" | "industrial" | null`
- Add `job_type_code?: string | null` and `job_type_label?: string | null`
- Keep `job_type` (the raw string) only if still referenced; otherwise prefer `job_type_code`/`job_type_label`. Grep for `.job_type` usages before removing.

> **Note on stubs**: `types-stub.ts` predates full `sync-api-types` coverage for the board. Prefer the generated `@pilot/shared-types` `DispatchBoardJobEntry` where possible; keep the stub minimal. If you keep the stub, its values MUST match the generated union exactly.

---

## STEP 2 — `useDispatchBoard.ts`: delete fallbacks, carry real values

In `RawJobEntry` add: `priority?`, `customer_type?`, `site_type?`, `job_type_code?`, `job_type_label?`.

In `normalizeJob` (~line 127) **delete**:
```ts
priority: "standard",        // ❌ delete
customer_type: "commercial", // ❌ delete
job_type: "",                // ❌ delete
```
Replace with real reads:
```ts
priority: raw.priority ?? "standard",          // real value; "standard" only as null-safety
customer_type: raw.customer_type ?? null,
site_type: raw.site_type ?? null,
job_type_code: raw.job_type_code ?? null,
job_type_label: raw.job_type_label ?? null,
```
(Adjust to the actual normalized shape — read the function first. The `?? "standard"` for priority is null-safety, not a hardcode; every seeded/real job now has a real value.)

Intermediate:
```bash
pnpm --filter web test -- apps/web/src/features/dispatch-board 2>&1 | tail -10
```

---

## STEP 3 — `store.ts`: correct the filter union values

`DispatchBoardFilters`:
- `priorities: Array<"standard" | "urgent" | "emergency">` (was `rush/standard/warranty`)
- `customerTypes: Array<"person" | "company">` (was `commercial/residential`)

The toggle action signatures update to match. `applyFilters` in `DispatchBoardPage` already compares against these arrays — no logic change, just the value domain. Confirm `applyFilters` still reads `job.customer_type` / `job.priority` (it does).

---

## STEP 4 — `FilterBar.tsx`: correct the pill configs

Replace:
```ts
const PRIORITY_PILLS = [
  { label: "Standard", value: "standard" },
  { label: "Urgent",   value: "urgent" },
  { label: "Emergency", value: "emergency" },
];
const CUSTOMER_TYPE_PILLS = [
  { label: "Person",  value: "person" },
  { label: "Company", value: "company" },
];
```
Update the prop types (`onTogglePriority`, `onToggleCustomerType`) to the new unions. The `FilterPill` component + Tech popover + Job Type conditional row are unchanged. Job Type row still derives from `uniqueJobTypes` — but now sources from real data; confirm it reads a populated field (`job_type_label` preferred for display; the filter value should remain the job's stored code so `applyFilters` matches — verify the `jobTypes` filter compares against `job_type_code`, and adjust `applyFilters` + the pill `value` to use `job_type_code` if it currently used the empty `job_type`).

Intermediate:
```bash
pnpm --filter web test -- apps/web/src/features/dispatch-board 2>&1 | tail -10
```

---

## STEP 5 — `JobPropertiesPanel.tsx`: read-only classification chips

Read the panel. In the job info section (near customer/site name/address from B1.5), add a **read-only chip row** showing the four classification values when present:
- **Priority** — colored chip: `emergency` → `bg-fault-100 text-fault-700`; `urgent` → `bg-warn-100 text-warn-700` (use the real warn token — grep `pilotPreset` / existing warn usage); `standard` → `bg-neutral-100 text-neutral-600`. Label capitalized.
- **Customer Type** — `person` → "Person"; `company` → "Company". Neutral chip.
- **Site Type** — Commercial/Residential/Industrial. Neutral chip. Only when `site_type` present.
- **Job Type** — `job_type_label` when present. Neutral chip. Omit when null.

All display-only — no dropdowns, no mutations (JOB-UI-B1 adds editing on the job pages). Use existing chip/badge styling in the panel — read the file and match; do not hardcode hex.

---

## Test Requirements

Web = Vitest + `@testing-library/react`. Mock `next/navigation`. QueryClient `retry: false`. MSW at HTTP level; `afterEach(server.resetHandlers())`.

**MSW fixtures** (`dispatchBoardHandlers.ts`): update board fixture jobs to carry varied real values — at least one `emergency` + one `urgent`, at least one `company` customer, one `commercial` + one `industrial` site, and `job_type_code`/`job_type_label` on ≥2 jobs with different types. This is what makes the filter tests meaningful.

Create in `apps/web/src/__tests__/batch_dispatch_b3/`:
- **Priority filter works**: with a fixture containing 1 emergency + rest standard, selecting the `Emergency` pill hides the standard jobs and shows the emergency one (assert by job ID/number, not count).
- **Customer Type filter works**: selecting `Company` shows only the company-customer job(s).
- **Job Type filter works**: selecting a specific job type shows only jobs of that type.
- **normalizeJob carries real values**: hook test — a raw entry with `priority:"urgent"`, `customer_type:"company"`, `site_type:"industrial"`, `job_type_label:"Panel Upgrade"` normalizes through unchanged (no hardcoded override).
- **Panel chips render**: `JobPropertiesPanel` shows Priority/Customer Type/Site Type/Job Type chips for a job with all four; omits Site Type + Job Type chips when null.
- **FilterBar labels**: Priority pills read Standard/Urgent/Emergency; Customer Type pills read Person/Company (no Rush/Warranty/Commercial/Residential).

Update any existing dispatch-board unit tests that asserted the old `rush`/`commercial` values.

---

## Final Verification

> ❌ BANNED: `npx vitest run`. Only `pnpm --filter web test`.

### Phase 1 — Targeted
```bash
cd <repo>/frontend
pnpm --filter web test -- apps/web/src/features/dispatch-board 2>&1 | tail -10
pnpm --filter web test -- apps/web/src/__tests__/batch_dispatch_b3/ 2>&1 | tail -10
```
### Phase 2 — Full
```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```
Any failure in either phase fixed before done.

---

## Definition of Done — DISPATCH-B3

- [ ] Regression baseline captured (zero pre-existing failures or confirmed with Tom)
- [ ] `pnpm sync-api-types` run — 5 new `DispatchBoardJobEntry` fields present
- [ ] **STEP 1**: `types-stub.ts` unions corrected (priority urgent set; customer_type person/company; +site_type/job_type_code/job_type_label)
- [ ] **STEP 2**: `useDispatchBoard.ts` hardcoded fallbacks DELETED; real values carried through
- [ ] **STEP 3**: `store.ts` `DispatchBoardFilters` priorities + customerTypes value domains corrected
- [ ] **STEP 4**: `FilterBar.tsx` PRIORITY_PILLS → Standard/Urgent/Emergency; CUSTOMER_TYPE_PILLS → Person/Company; job-type filter value = `job_type_code`
- [ ] **STEP 5**: `JobPropertiesPanel.tsx` read-only priority/customer-type/site-type/job-type chips
- [ ] MSW dispatch fixtures carry varied real classification values
- [ ] Priority + Customer Type + Job Type filters verified working end-to-end (assert by ID)
- [ ] Zero hardcoded design values (chip colors from tokens)
- [ ] **Phase 2 FULL verification passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`)
- [ ] Final test count documented
- [ ] Completion Summary added to launch plan Appendix B

---

## Completion Summary

Add to `pilot-launch-plan.md` Appendix B (React template). Note this closes the dispatch filter data gap discovered during DISPATCH-B2 testing — Priority + Customer-Type filters now work against real backing data, and the properties panel surfaces all four classification dimensions read-only. Mark DISPATCH-B3 ✅ in §2.0.
