# Implementation Prompt: CUST-UI-B1 — Customer Type Confirmation + Site Type on Sites

**Mode**: Pilot React Engineer
**Batch**: CUST-UI-B1 (Frontend web)
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.3 CUST-UI-B1
**Backend companion**: CLASS-B1 ✅ **COMPLETE (2026-07-27)** — `site.site_type` (commercial/residential/industrial, customer-type default on create) + `customer.type` (person/company) in the API.
**Estimated session**: 2–2.5 hours
**Platform**: Web only (`apps/web`)
**Depends on**: CLASS-B1 (+ `pnpm sync-api-types`)

---

## ⚠️ MANDATORY STOP: Read These First

- **`.roo/rules-pilot-react-engineer/react-engineer-rules.md`** — in full

Critical rules for this batch:

- **Rule 1.3**: Run `pnpm sync-api-types` FIRST — CLASS-B1 added `site_type` to `SiteResponse`/`SiteCreate`/`SiteUpdate`. Types come from `@pilot/shared-types`.
- **Rule 2**: All API via `apiClient`. `fetch()` banned.
- **Rule 7**: Reuse existing components — `SiteForm`, `SiteListPanel`, `CustomerOverviewTab`, `CustomerForm` all exist. Edit them; do not recreate.
- **Rule 10**: Any failing test — even apparently pre-existing — fixed before done. Root cause unclear → STOP and ask Tom.

**Seed-Data Awareness (react-engr-std-prompt-inclusions.md §18):** CLASS-B1 seeded real `site_type` on scenario sites (Apex HQ + Metro Office Park → commercial; residences → residential). MSW fixtures for sites must carry varied `site_type` so the display/dropdown tests are meaningful.

---

## Design Decisions (Do Not Re-Litigate)

Tom-approved 2026-07-27 (see CLASS-B1 design §G):

| Decision | Outcome |
|---|---|
| Customer type values | `person` · `company` (already in DB + already displayed — see below) |
| Site type values | `commercial` · `residential` · `industrial` |
| Site type default on create | **customer-type-aware**: `company` customer → `commercial`; `person` customer → `residential`. The **backend already computes this** when `site_type` is omitted (CLASS-B1). The frontend should also pre-select the dropdown to the matching default so the user sees it. |
| Customer type editability | **read-only display** on the detail page (it is already editable via `CustomerForm` in edit mode — do not change that) |
| Site type editability | **editable dropdown** on the SiteForm (create + edit) |

**Important scope note**: The customer `type` field is **already displayed** in `CustomerOverviewTab.tsx` (a "Type" chip) and **already editable** via `CustomerForm.tsx` (type field). So the customer-type half is largely **verification only** — confirm it renders correctly and is covered by a test. The **net-new work is `site_type`** on the Sites tab.

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
grep -B2 -A2 "site_type" frontend/packages/shared-types/src/api-schema.d.ts | head -20
```
`site_type` must appear on the Site schemas. If not → CLASS-B1 not synced. STOP and confirm with Tom.

---

## Pre-Work: Verify Endpoints

No new endpoints. `site_type` rides on the existing `POST /api/v1/sites/`, `PATCH /api/v1/sites/{id}`, `GET` customer sites. Confirm the field is in the contract:
```bash
grep -A 3 "site_type" backend/openapi_schema_map.md | head
```

---

## Pre-Work: Read These Source Files

```
frontend/apps/web/src/features/customers/components/SiteForm.tsx              ← add site_type <select>; add to SiteFormValues + onSubmit payload
frontend/apps/web/src/features/customers/components/SiteListPanel.tsx          ← pass customerType to SiteForm for default; show site_type on site cards; pass site_type in edit initialValues
frontend/apps/web/src/features/customers/hooks/useCreateSite.ts               ← add site_type to SiteCreateRequest
frontend/apps/web/src/features/customers/hooks/useUpdateSite.ts               ← confirm site_type passes through (likely reuses SiteCreateRequest)
frontend/apps/web/src/features/customers/hooks/useCustomerSites.ts            ← SiteResponse type — confirm site_type present after sync
frontend/apps/web/src/features/customers/hooks/useCustomer.ts                 ← customer.type source for the default logic
frontend/apps/web/src/features/customers/components/CustomerOverviewTab.tsx    ← customer.type ALREADY shown (:143) — verify only
frontend/apps/web/src/features/customers/components/CustomerForm.tsx           ← customer type ALREADY editable — verify only
frontend/apps/web/src/mocks/handlers/  (site handlers)                        ← add site_type to fixtures
```

Locate the site MSW handler + the customer-type source available to SiteListPanel:
```bash
grep -rln "sites/" frontend/apps/web/src/mocks/handlers/
grep -n "useCustomer\b" frontend/apps/web/src/features/customers/components/*.tsx
```

---

## Context: What This Batch Does

| Area | Change |
|---|---|
| `SiteForm.tsx` | Add `site_type` `<select>` (Commercial/Residential/Industrial); default from a new `customerType` prop (company→commercial, person→residential); include in `SiteFormValues` + submit payload |
| `SiteListPanel.tsx` | Pass the customer's `type` into `SiteForm` (for the create default); show a `site_type` chip on each site card; pass `site_type` into edit `initialValues` |
| `useCreateSite.ts` / `useUpdateSite.ts` | Add `site_type?` to `SiteCreateRequest` |
| Customer type display | **Verify only** — already shown + editable |
| MSW | Site fixtures carry varied `site_type` |

---

## STEP 1 — Hooks: add `site_type` to the site request shape

`useCreateSite.ts` — add to `SiteCreateRequest`:
```ts
site_type?: "commercial" | "residential" | "industrial" | null;
```
`useUpdateSite.ts` — confirm it reuses `SiteCreateRequest` (so `site_type` flows automatically); if it has its own type, add the field. `SiteResponse` (in `useCustomerSites.ts`) should get `site_type` from `sync-api-types` — confirm; if the response type is hand-written, add `site_type`.

---

## STEP 2 — `SiteForm.tsx`: site_type dropdown

- Add `site_type` to `SiteFormValues`.
- Add a `customerType?: "person" | "company"` prop.
- Compute the default: `initialValues?.site_type ?? (customerType === "company" ? "commercial" : "residential")`.
- Add a `<select>` (Commercial/Residential/Industrial) using `INPUT_CLASS`/`LABEL_CLASS` already in the file. Place it after Site Name (before Notes).
- Include `site_type` in the `onSubmit(...)` payload.

Read the file first — match the existing `useState` + label/input patterns exactly.

---

## STEP 3 — `SiteListPanel.tsx`: wire default + display chip

- The panel has `customerId`; it needs the customer's `type` for the default. Fetch it via the existing `useCustomer(customerId)` hook (already used elsewhere) OR accept a `customerType` prop from the parent if one is readily available — prefer `useCustomer` to keep the component self-contained. Pass `customerType={customer?.type}` to both the create and edit `<SiteForm>`.
- Edit modal `initialValues`: add `site_type: editingSite.site_type ?? undefined`.
- Site card: add a small `site_type` chip (neutral, capitalized) next to the site name — only when present. Use the existing chip styling pattern from `CustomerOverviewTab` (`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-neutral-100 text-neutral-700 capitalize`). No hardcoded hex.

Intermediate:
```bash
pnpm --filter web test -- apps/web/src/features/customers 2>&1 | tail -10
```

---

## STEP 4 — Verify customer type display (no new code expected)

Confirm `CustomerOverviewTab.tsx` still renders the "Type" chip (person/company) and `CustomerForm.tsx` still has the type field in edit mode. If both are intact, add/confirm a test asserting the Type chip renders — do NOT add duplicate display. If either is missing (regressed), restore it as a read-only chip on the overview.

**Dispatch panel note**: showing `customer_type` on the dispatch `JobPropertiesPanel` is handled by **DISPATCH-B3** (classification chips) — do NOT duplicate it here.

---

## Test Requirements

Web = Vitest + `@testing-library/react`. Mock `next/navigation`. QueryClient `retry: false`. MSW at HTTP level; `afterEach(server.resetHandlers())`.

**MSW**: site fixtures carry varied `site_type` (≥1 commercial, ≥1 residential, ideally 1 industrial); customer fixtures include one `person` + one `company`.

Create in `apps/web/src/__tests__/batch_cust_ui_b1/` + co-located unit tests:
- **SiteForm dropdown**: renders Commercial/Residential/Industrial; with `customerType="company"` defaults to Commercial; with `customerType="person"` defaults to Residential; selecting a value + submit includes `site_type` in the payload.
- **SiteForm edit**: pre-fills `site_type` from `initialValues`.
- **SiteListPanel card**: shows the `site_type` chip for a site with `site_type="commercial"`; omits when null.
- **SiteListPanel default wiring**: opening "Add Site" for a company customer shows Commercial pre-selected (integration).
- **Customer type display (verify)**: `CustomerOverviewTab` renders the Type chip with the customer's `type` value.
- Update any existing SiteForm/SiteListPanel tests that break from the new field.

---

## Final Verification

> ❌ BANNED: `npx vitest run`. Only `pnpm --filter web test`.

### Phase 1 — Targeted
```bash
cd <repo>/frontend
pnpm --filter web test -- apps/web/src/features/customers 2>&1 | tail -10
pnpm --filter web test -- apps/web/src/__tests__/batch_cust_ui_b1/ 2>&1 | tail -10
```
### Phase 2 — Full
```bash
cd <repo>/frontend && echo "=== UI - Type Check ===" && pnpm --filter @pilot/ui check-types && echo "=== Web - Type Check ===" && pnpm --filter web check-types && echo "=== Mobile - Type Check ===" && pnpm --filter mobile build && echo "=== UI - Lint ===" && pnpm --filter @pilot/ui lint && echo "=== Web - Lint ===" && pnpm --filter web lint && echo "=== Mobile - Lint ===" && pnpm --filter mobile lint && echo "=== TYPE+LINT PASS ===" && echo "=== UI - Tests ===" && pnpm --filter @pilot/ui test 2>&1 | tail -6 && echo "=== Web - Tests ===" && pnpm --filter web test 2>&1 | tail -6 && echo "=== Mobile - Tests ===" && pnpm --filter mobile test 2>&1 | tail -8 && echo "=== MVP FINAL VERIFICATION COMPLETE ==="
```
Any failure in either phase fixed before done.

---

## Definition of Done — CUST-UI-B1

- [ ] Regression baseline captured (zero pre-existing failures or confirmed with Tom)
- [ ] `pnpm sync-api-types` run — `site_type` present on Site schemas
- [ ] **STEP 1**: `site_type` added to `SiteCreateRequest` (+ update hook if separate); `SiteResponse` carries it
- [ ] **STEP 2**: `SiteForm` site_type `<select>` with customer-type-aware default; in submit payload
- [ ] **STEP 3**: `SiteListPanel` passes `customerType` to SiteForm; edit initialValues carry `site_type`; site card shows chip
- [ ] **STEP 4**: customer type display verified (Type chip on overview; editable in CustomerForm) — no duplication
- [ ] MSW site fixtures carry varied `site_type`
- [ ] Zero hardcoded design values (chip styling from existing tokens)
- [ ] Unit + integration tests pass
- [ ] **Phase 2 FULL verification passes** (`=== MVP FINAL VERIFICATION COMPLETE ===`)
- [ ] Final test count documented
- [ ] Completion Summary added to launch plan Appendix B

---

## Completion Summary

Add to `pilot-launch-plan.md` Appendix B (React template). Note the customer-type display was already present (verified) and the net-new work was `site_type` on the Sites tab + customer-type-aware create default. Mark CUST-UI-B1 ✅ in §2.0.
