# Batch Design: PLP-FIX-2 — Dynamic QCO Line Types + Quote-Line FK Hardening + Customer-Tab Add Job + Invoice Custom Lines (FE-B29-1)

**Batch**: PLP-FIX-2 (mixed batch — Part A: Backend, Part B: Frontend web)
**Version**: 1.0
**Date**: 2026-09-01
**Author**: Pilot Architect
**Status**: Approved for prompt authoring
**Bug report**: `dev-docs/analysis/PLP-testing-bugs-2026-08-30.md` — Issues 3, 5 (and FE-B29-1 tail of Issue 2)
**Predecessor batch**: `batch-plp-fix-1-design.md` (v1.1 — closed ✅ 2026-08-30)
**Prompts**: `batch-plp-fix-2-python-engr-prompt.md` (Part A, runs FIRST) · `batch-plp-fix-2-react-engr-prompt.md` (Part B, gated on `pnpm sync-api-types`)

---

## Scope Statement

PLP-FIX-1 unblocked the backend quote→job→invoice flow (de-gated quote creation, added `line_items[]` to `InvoiceCreate`). Production smoke testing then surfaced the next layer of blockers:

| Issue (bug report) | Symptom | Root cause | Fix location |
|---|---|---|---|
| **#5** | "Network Error" on quote Save Draft; ASGI `ForeignKeyViolation: quote_line_qco_line_type_id_fkey` (key `bb1588c7-…`) | `LineItemEditor.tsx` hardcodes **dev-seed UUIDs** for `qco_line_type_id`; prod seed UUIDs differ; **no `GET` endpoint exists** for line types; MSW mocks mirrored dev UUIDs so tests were green | Part A (new endpoint + FK hardening) + Part B (dynamic hook) |
| **#3** | Customer detail → Jobs tab → "New Job" → "Server error" / "Failed to load technicians" | `CustomerJobsList.tsx` links to `/jobs/new?customer_id=…` — **no such route exists**; Next.js App Router matches `/jobs/[id]` with `id="new"` and renders the job-detail page, which 404s/500s on the API | Part B (replace link with `JobFormModal` + new `prefilledCustomerId` prop) |
| **#2 tail (FE-B29-1)** | Invoice builder "custom line" UI adds rows that never persist | `InvoiceBuilderPage.handleSave` never sends `customLines`; `useCreateInvoice`'s payload type lacks `line_items` (backend shipped it in PLP-FIX-1) | Part B (wire `line_items[]`) |
| **#4** | Jobs menu "Add Job" → "Network error" | **Not diagnosed** — needs Tom's Network-tab repro (CORS vs `NEXT_PUBLIC_API_URL` vs mixed content) | ❌ **Explicitly out of scope** — separate batch once diagnosed |

**Out of scope**: Issue 4; any change to `qco_line_type` seed data (all environments already seed the 5 platform rows — that is precisely why the codes are stable and the UUIDs differ); any new UI surface (§1.5 designer-spec gate is **N/A** — see §H).

---

## A. Input Read Summary

| Input | What was read | Key facts extracted |
|---|---|---|
| Bug report | `PLP-testing-bugs-2026-08-30.md` (all 5 issues + Amendment) | Issue 5 evidence: prod ASGI traceback, FK `quote_line_qco_line_type_id_fkey`, key `bb1588c7-e91f-4db8-8497-5d81679bc084` = **dev's** `material` UUID |
| Live DB (postgres-local MCP) | `information_schema.columns` for `qco_line_type`; full row dump | Columns: `id, tenant_id (nullable), code, name, is_default, is_active, qb_item_name_hint` + 4 audit cols. **5 platform rows** (tenant_id NULL): `labor` (is_default=**true**), `material`, `misc`, `discount`, `note` — all `is_active=true` |
| Model | `backend/app/models/quoting.py` §`QcoLineType` (line 76) | `StandardAuditMixin`; `tenant_id` nullable FK (platform rows = NULL) |
| Route pattern reference | `backend/api/routes/job_types.py` (full) | CLASS-B1 lookup pattern: `_list_*_impl` shared by auth + `/test` twin; platform ∪ tenant merge by code; `require_permission("jobs.view")` |
| FK crash site | `backend/api/routes/quotes.py` `_create_quote_line_impl` (387–538) | `qco_line_type_id=line_in.qco_line_type_id` (line 507) inserted **unchecked** → `db.flush()` (line 528) raises FK violation → 500 |
| Request schema | `backend/api/schemas/quotes.py` `QuoteLineCreate` (169–205) | `qco_line_type_id: UUID` — **required, non-nullable** in the contract |
| Response schema pattern | `backend/api/schemas/schemas.py` `JobTypeResponse` (291–306) | `id, code, label, sort_order, is_active, is_tenant_override` — mirror for `QcoLineTypeResponse` |
| Invoice contract (PLP-FIX-1) | `backend/api/schemas/schemas.py` `InvoiceLineItemCreate` (704–739) + `InvoiceCreate` (742–755) | `line_items[]`: `description` (≤500), `quantity` (default 1), `unit`, `unit_price_cents`, `qco_line_type_code` (optional — **default `misc` resolved by code in impl**, env-safe) |
| Router registration | `backend/app/main.py` (125–400) | `app.include_router(x.router, prefix="/api/v1/...", tags=[...])`; lookup precedents: `job-types`, `job-expense-categories` |
| RFC 7807 standard | `backend/python-engr-std-prompt-inclusions.md` §13 | `HTTPException(detail={type,title,status,detail})`; plain-string detail banned for **new** code; 404 (not 403) for tenant-scoped misses |
| FE bug site (Issue 5) | `LineItemEditor.tsx` (1–506) | `QCO_LINE_TYPES` const (26–39) + `DEFAULT_LINE_TYPE_ID` (41) = dev UUIDs; `emptyLine()` (96–104) injects default; both create-flow and edit-flow `<select>`s render from the const |
| FE consumer | `QuoteCreatePage.tsx` (86–131) | Line 113: `qco_line_type_id: line.qco_line_type_id ?? DEFAULT_LINE_TYPE_ID` in the per-line POST loop |
| FE hook pattern | `useAddQuoteLine.ts` (full) | `apiClient` + TanStack Query v5 object form; invalidate `["quotes", quoteId, "detail"]` |
| MSW mirror | `quoteBuilderHandlers.ts` (1–197) + barrel `index.ts` (1–148) | `QCO_LINE_TYPE_IDS` (24–29) mirrors the same dev UUIDs — **why tests were green while prod 500'd**; barrel already spreads `quoteBuilderHandlers` (extending the array needs no `index.ts` change) |
| FE bug site (Issue 3) | `CustomerJobsList.tsx` (200–319) | Line 265: `<a href={/jobs/new?customer_id=…}>`; route dir `app/(authed)/jobs/` contains only `page.tsx`, `[id]/`, `[id]/edit/`, `recurring/` — **no `new/`** |
| Modal to reuse | `JobFormModal.tsx` (1–470) | Props: `open, onClose, onSuccess, prefilledQuoteId`; inner `JobFormContent` initializes `customerId`/`siteId` via `useState("")`; already used by `JobsPage.tsx` and `QuoteDetailPage.tsx` (with `prefilledQuoteId`) |
| FE-B29-1 site | `InvoiceBuilderPage.tsx` (96–285) + `useCreateInvoice.ts` (full) | `CustomLineItem {localId, description, unitPriceCents}` (47–51); `customLines` state (114); `handleAddCustomLine` (257–272); `handleSave` (220–241) **omits `line_items`**; `InvoiceCreatePayload` (18–33) lacks the field |
| Rules | `.roo/rules-pilot-architect/pilot-architect-rules.md` §1.1–§1.5, §2, §3, §11.5; both std-inclusions files (full reads) | Mixed-batch rule §1.3 (one design doc, BE first, FE gated on `pnpm sync-api-types`); MCP-before-SQL gate; Seed Data Rollout rule (→ **N/A**, see §B) |

---

## B. Migration Plan

**No migration. No DB DDL. No seed changes. Code-only batch.**

- Alembic head stays `c8d06a6ffdd2`. The 3-part NOT NULL pattern is not invoked.
- `qco_line_type` already carries the 5 platform rows in **every** environment (dev seed + prod seed run independently — different UUIDs, same codes). The batch's entire premise is that **codes are the stable cross-environment key**, so no data needs to change anywhere.
- **Seed Data Rollout (Rule 11.5): explicitly N/A** — this batch adds/modifies **zero** DB rows, columns, tables, enums, or lookup values. Stated here so the absence is a decision, not an omission.

**MCP verification queries (already executed during design — re-run in Pre-Work):**

```sql
-- 1. Columns (design-time result: id, tenant_id, code, name, is_default,
--    is_active, qb_item_name_hint + created_at/updated_at/created_by/updated_by)
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'qco_line_type'
ORDER BY ordinal_position;

-- 2. Platform rows (design-time result: 5 rows, tenant_id NULL:
--    labor [is_default=true], material, misc, discount, note — all active)
SELECT id, tenant_id, code, name, is_default, is_active
FROM public.qco_line_type
ORDER BY tenant_id NULLS FIRST, code;
```

**Pre-migration state**: N/A. **Rollback**: `git revert` (no schema state to unwind).

---

## C. Execution Order

| # | Step | Owner | Gate |
|---|---|---|---|
| 1 | **Part A — BE**: `QcoLineTypeResponse` schema | Python Engineer | — |
| 2 | **Part A — BE**: `api/routes/qco_line_types.py` (impl + auth GET + `/test` twin) | Python Engineer | — |
| 3 | **Part A — BE**: register router in `app/main.py` | Python Engineer | — |
| 4 | **Part A — BE**: FK hardening in `_create_quote_line_impl` | Python Engineer | — |
| 5 | **Part A — BE**: unit tests (new endpoint + hardening) | Python Engineer | Phase 1 gate |
| 6 | **Part A — BE**: regenerate `openapi.json` + `openapi_schema_map.md`; Phase 2 full suite | Python Engineer | **Handoff gate** |
| 7 | **Handoff**: commit; notify React Engineer | Python Engineer | §1.3 rule |
| 8 | **Part B — FE**: `pnpm sync-api-types` (FIRST Pre-Work step) | React Engineer | types must contain `QcoLineTypeResponse` |
| 9 | **Part B — FE**: `useQcoLineTypes` hook + MSW handler extension | React Engineer | — |
| 10 | **Part B — FE**: `LineItemEditor` dynamic types; `QuoteCreatePage` fallback removal | React Engineer | — |
| 11 | **Part B — FE**: `JobFormModal.prefilledCustomerId` + `CustomerJobsList` modal swap | React Engineer | — |
| 12 | **Part B — FE**: `InvoiceCreatePayload.line_items` + `InvoiceBuilderPage.handleSave` wiring | React Engineer | — |
| 13 | **Part B — FE**: tests (unit + integration); Phase 2 canonical command | React Engineer | DoD |

**BE deploys before FE** — the FE's new hook 404s against a backend that lacks the endpoint. Tom deploys Part A, verifies `GET /api/v1/qco-line-types` returns 200 on prod, then Part B deploys.

---

## D. New API Endpoints

### D.1 — `GET /api/v1/qco-line-types` (NEW)

| Field | Value |
|---|---|
| Method / Path | `GET /api/v1/qco-line-types` |
| Auth | JWT — `require_permission("quotes.view")` (matches every quotes read endpoint) |
| RBAC | Any role with `quotes.view` |
| Query params | None |
| Response `200` | `list[QcoLineTypeResponse]` — platform rows (`tenant_id IS NULL`) ∪ tenant rows, **tenant wins on `code` collision**, `is_active=true` only, sorted by `name` |
| Response item | `{ id: UUID, code: str, name: str, is_default: bool, is_active: bool, is_tenant_override: bool }` |
| Errors | 401 (no/expired JWT), 403 (no `quotes.view`) — standard framework paths only; **no entitlement `feature_code`** (phantom-gate rule §17/§18 — line types are not a PRD §3.11 priced feature) |
| Rate limit | None beyond global |
| Idempotency | N/A (GET) |
| Test twin | `GET /api/v1/qco-line-types/test` (Rule 17b — `TestUserContext`, canonical test tenant) |

**Design notes**:
- Lives in a **new** route file `backend/api/routes/qco_line_types.py` registered at its own prefix — mirrors the `job_types.py` / `job_expense_categories.py` lookup precedent. It is deliberately **not** a `/quotes/qco-line-types` sub-path: the quotes router's `/{quote_id}` dynamic segment makes sub-path registration order-fragile, and the lookup is conceptually cross-domain (invoices will consume it too).
- Response excludes `qb_item_name_hint` (internal QB-mapping concern, not needed by any client; keeps the payload minimal). It stays in the model/DB untouched.
- Sort: `ORDER BY name` (no `sort_order` column exists on this table, unlike `job_type`).

### D.2 — `POST /api/v1/quotes/{quote_id}/lines` (EXISTING — hardened, no contract change)

Behavioral change only, inside `_create_quote_line_impl`:

```python
# NEW — validate BEFORE building the ORM row (insert at ~line 415, after the
# quote ownership check, before any price/tax work):
if line_in.qco_line_type_id is not None:
    line_type = db.exec(
        select(QcoLineType).where(
            QcoLineType.id == line_in.qco_line_type_id,
            (QcoLineType.tenant_id == user_context.tenant_id)
            | (QcoLineType.tenant_id == None),  # platform rows
            QcoLineType.is_active == True,
        )
    ).first()
    if not line_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://errors.pilotfortrades.com/not-found",
                "title": "Line type not found",
                "status": 404,
                "detail": f"qco_line_type_id {line_in.qco_line_type_id} does not exist or is not active.",
            },
        )
```

- **404, not 422**: the UUID is a resource reference; a miss means "no such resource in scope" — consistent with the house tenant-scoped-miss rule (404 prevents enumeration) and with the existing `Quote not found` 404 two lines above.
- **RFC 7807 detail-dict** for the new raise (Rule 13). The pre-existing `detail="Quote not found"` string at line 414 is **not** in scope to change (mechanical-uplift ban — TEST-UPLIFT-1A owns that class).
- Same validation is **not** added to `_persist_custom_lines` (invoices): PLP-FIX-1 already resolves custom invoice lines by **code** (`_resolve_qco_line_type_id(db, "misc")`), which is environment-safe by construction.
- Result: the Issue-5 failure mode changes from a 500 ASGI traceback (FK violation at flush) to a clean, diagnosable RFC 7807 404 — and with Part B shipped, the FE stops sending foreign UUIDs altogether.

---

## E. Pattern Reuse Decisions

| Pattern | Source | Application |
|---|---|---|
| Lookup endpoint shape (impl fn + auth route + `/test` twin) | `job_types.py` (CLASS-B1) | D.1 copies it 1:1, including the platform∪tenant merge with tenant-wins-on-code |
| System-default / tenant-override (§16 locked pattern) | `mvp-arch.md` §16 | The merge rule **is** this pattern at the data layer; `is_tenant_override` flag surfaces it |
| RFC 7807 problem details | inclusions §13 / Rule 13 | New 404 raise uses detail-dict |
| 404-not-403 for scoped misses | inclusions §13 | D.2 decision |
| Test twins (Rule 17b) | python-engineer-rules §17b | `/test` endpoint mandatory for the new entity route |
| Phantom-gate rule | python-engineer-rules §17/§18 | Endpoint carries **no** `feature_code` — line types are not PRD §3.11 priced |
| Tenant-scoped `select()` (never `db.get()` on tenant-scoped models) | architect-methods §7.1 / Rule 4 | D.2 validation uses explicit `select()` with tenant predicate |
| Sync-by-design (Rule 21) | python-engineer-rules §21 | Plain `def` route + sync `Session` — no `async def` |
| MSW fidelity | react rules §13 | Fixture UUIDs intentionally keep local-dev values (MSW mirrors the **local dev DB**); the handler serves the list so components resolve types dynamically in tests exactly as in prod |

No new top-level UX patterns are introduced — Part B composes existing surfaces only (§16 locked patterns untouched).

---

## F. Shared Module Interfaces

### F.1 — Backend

```python
# backend/api/schemas/quotes.py  (quote-domain sibling of QuoteLineCreate)
class QcoLineTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    is_default: bool
    is_active: bool
    is_tenant_override: bool = False
```

```python
# backend/api/routes/qco_line_types.py
def _list_qco_line_types_impl(db: Session, tenant_id) -> list[QcoLineTypeResponse]: ...

@router.get("", response_model=list[QcoLineTypeResponse])
def list_qco_line_types(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("quotes.view")),
) -> list[QcoLineTypeResponse]: ...

@router.get("/test", response_model=list[QcoLineTypeResponse])
def list_qco_line_types_test(
    db: Session = Depends(get_db),
    ctx: TestUserContext = Depends(get_test_context),
) -> list[QcoLineTypeResponse]: ...
```

```python
# backend/app/main.py  (add import + registration, placed near the quotes registration)
app.include_router(
    qco_line_types.router,
    prefix="/api/v1/qco-line-types",
    tags=["quotes"],
)  # PLP-FIX-2: QCO line-type lookup (platform defaults ∪ tenant overrides, read-only)
```

No Celery tasks, no new scheduled work.

### F.2 — Frontend

```typescript
// apps/web/src/features/quotes/hooks/useQcoLineTypes.ts (NEW)
export const QCO_LINE_TYPES_QUERY_KEY = ["qco-line-types"] as const;

export function useQcoLineTypes() {
  return useQuery({
    queryKey: QCO_LINE_TYPES_QUERY_KEY,
    queryFn: async () => {
      const res = await apiClient.get("/api/v1/qco-line-types");
      return res.data as QcoLineTypeResponse[]; // components["schemas"]["QcoLineTypeResponse"]
    },
    staleTime: 60 * 60 * 1000, // reference data — deliberate 1h stale (rules §33)
  });
}

// Default resolution helper (exported for editor + tests):
//   1) code === "misc"   2) is_default === true   3) first row
export function resolveDefaultLineTypeId(types: QcoLineTypeResponse[]): string | null
```

```typescript
// JobFormModal.tsx — props delta
interface JobFormModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess?: (job: JobCreateResponse) => void;
  prefilledQuoteId?: string;
  prefilledCustomerId?: string;   // ← NEW (PLP-FIX-2): preselect + drive Site cascade
}
```

```typescript
// useCreateInvoice.ts — payload delta (type from @pilot/shared-types after sync)
export interface InvoiceCreatePayload {
  // …existing fields…
  line_items?: components["schemas"]["InvoiceLineItemCreate"][] | null; // ← NEW
}
```

```typescript
// InvoiceBuilderPage.tsx handleSave — wiring (quantity fixed at 1; backend defaults misc by code)
line_items: customLines.length
  ? customLines.map((cl) => ({
      description: cl.description,
      quantity: 1,
      unit_price_cents: cl.unitPriceCents,
    }))
  : null,
```

---

## G. Open Questions Resolved

1. **New router file vs. sub-path under `/quotes`?** → New file at `/api/v1/qco-line-types`. The quotes router's `/{quote_id}` segment makes a static sub-path registration-order-fragile; lookup precedent (`job-types`, `job-expense-categories`) is standalone prefixes.
2. **FE default line type: DB `is_default` (= `labor`) or current UI behavior (`misc`)?** → **Preserve current behavior**: resolve `code === "misc"` first, then `is_default`, then first row. Changing the default to labor would be an unrequested UX change; the `is_default` flag's semantics serve the backend/voice paths, not the quote-builder default.
3. **404 vs 422 for an unknown `qco_line_type_id`?** → **404** (resource reference miss; anti-enumeration; consistent with the adjacent quote 404).
4. **Include `note` and `discount` types in the editor dropdown?** → **Yes — render every active type the API returns.** Filtering to the old 4 would re-encode a hardcoded list. (`discount` was already in the UI; `note` appears as a new option — acceptable and correct.)
5. **Sort order in the dropdown?** → API sorts by `name` (no `sort_order` column exists). Dropdown order becomes Discount, Labor, Material, Misc, Note — a cosmetic change from today, accepted.
6. **Does `_persist_custom_lines` (invoices) need the same UUID guard?** → **No** — it resolves by **code** (`misc`) via PLP-FIX-1's `_resolve_qco_line_type_id`, which is environment-safe.
7. **Any seed/migration needed so prod UUIDs match dev?** → **No — that is the anti-goal.** Environments generate their own UUIDs; codes are the contract. The FE bug was keying on UUIDs at all.
8. **MSW fixture UUIDs — keep or change?** → **Keep the local-dev values** in `quoteBuilderHandlers.ts` fixtures; add the `GET` handler serving them. Tests then exercise the *dynamic* code path against the same values the local dev DB serves — fidelity preserved, and the fixture can never again drift from what the component requests.
9. **Issue 4 (Jobs-menu "Network error") in scope?** → **No.** Undiagnosed; requires Tom's Network-tab capture (bug report §Issue 4 diagnostic steps). Separate batch once the failing request is identified.
10. **`prefilledCustomerId` — should the customer field be locked when prefilled?** → **No — preselected but editable** (matches `prefilledQuoteId` precedent; the user may legitimately be creating a job for a different customer from the customer tab context).
11. **Should `CustomerJobsList` "New Job" get a `RoleGate`?** → **Yes — wrap with the same permission JobsPage uses for its Add Job button (`jobs.create`)**, so the customer tab can't present a create affordance the list page hides (hide-not-disable, Rule 6).
12. **Designer-spec gate (§1.5)?** → **N/A** — zero new surfaces; all changes are bug fixes inside existing approved surfaces. See §H.

---

## H. Surface Mockup Reference (frontend half)

**No new surfaces → §1.5 designer-spec gate is not invoked.** Every change lands inside an existing, previously-approved surface:

| Surface | Change | Nature |
|---|---|---|
| Quote builder (`/quotes/new`) + quote detail line editor | Dropdown options + default now API-driven | Behavioral swap of an existing `<select>`'s data source — identical markup |
| Customer detail → Jobs tab | "New Job" opens the existing `JobFormModal` instead of navigating to a non-existent route | Reuse of the JobsPage pattern already in production |
| Invoice builder | Custom lines now persist via an already-shipped backend field | Wiring only — no visual change |

§16 pattern consumption: none new (no track-changes, no confirm-as-turn, no preview flows touched).

## I. Component Manifest

**New components: none.** New hook only:

| Artifact | Destination | Status |
|---|---|---|
| `useQcoLineTypes.ts` (+ `resolveDefaultLineTypeId`) | `frontend/apps/web/src/features/quotes/hooks/` | **New** |
| `LineItemEditor.tsx` | `frontend/apps/web/src/features/quotes/components/` | Modified — delete `QCO_LINE_TYPES`/`DEFAULT_LINE_TYPE_ID`, consume hook |
| `QuoteCreatePage.tsx` | `frontend/apps/web/src/features/quotes/components/` | Modified — drop `DEFAULT_LINE_TYPE_ID` fallback (line 113) |
| `JobFormModal.tsx` | `frontend/apps/web/src/features/jobs/components/` | Modified — `prefilledCustomerId` prop |
| `CustomerJobsList.tsx` | `frontend/apps/web/src/features/customers/components/` | Modified — anchor→modal swap + `RoleGate` |
| `useCreateInvoice.ts` | `frontend/apps/web/src/features/invoices/hooks/` | Modified — `line_items` in payload type |
| `InvoiceBuilderPage.tsx` | `frontend/apps/web/src/features/invoices/components/` | Modified — send `line_items` in `handleSave` |
| `quoteBuilderHandlers.ts` | `frontend/apps/web/src/mocks/handlers/` | Modified — add `GET /api/v1/qco-line-types` handler |
| `mocks/handlers/index.ts` | `frontend/apps/web/src/mocks/handlers/` | Verified, **unchanged** (barrel already spreads `quoteBuilderHandlers`) |

Reconciliation check (§1.5.4): no orphan components — nothing proposed here lacks an existing home, and `packages/ui` gains nothing (confirmed against the reuse rule before deciding: `LoadingState`/`ErrorState` are consumed, not created).

---

## Verification (post-implementation, Tom on prod)

1. `GET https://api.pilotfortrades.com/api/v1/qco-line-types` with JWT → 200, 5 rows, **prod UUIDs ≠ dev UUIDs**, same codes.
2. Quote Save Draft with a `material` custom line → 201 + line persisted (Issue 5 closed end-to-end).
3. Customer → Jobs tab → New Job → modal opens with customer preselected → create → job appears in list (Issue 3 closed).
4. Invoice builder → custom line → Save Draft → line visible on invoice detail (FE-B29-1 closed).
5. Adversarial: `POST /quotes/{id}/lines` with a random UUID type → clean RFC 7807 **404** (not a 500 traceback).
