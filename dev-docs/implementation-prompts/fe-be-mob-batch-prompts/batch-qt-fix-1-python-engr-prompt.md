# Implementation Prompt: QT-FIX-1 — Make `quote_template_line.tenant_id` Nullable (System-Template Lines)

**Mode**: Pilot Python Engineer
**Batch**: QT-FIX-1
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.0 / §2.3
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-qt-fix-1-design.md`
**Estimated session**: 1–1.5 hours
**Platform**: Backend only (`backend/`)
**Frontend companion**: none (no OpenAPI change)

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document; the hard rules are non-negotiable STOPs
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; governs test file structure, domain markers, fixture rules
- **`backend/README-seed-data.md`** — §3 (Group A–D model), §6 (run order), §7 (DELETE-safety / idempotency)
- **`batch-qt-fix-1-design.md`** — the design for this batch

Critical rules for this batch:

- **Rule 1 (verify, don't guess)**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. If MCP returns an error → **STOP and ask Tom**.
- **Rule 2 (model map)**: After the `app/models/quoting.py` change → regenerate `backend/db_models_map.md` via `python generate_db_model_map.py app > db_models_map.md`.
- **Rule 4 (blank migrations)**: This migration MUST be a **blank** migration (`alembic revision -m "…"`, never `--autogenerate`). Data changes use raw `op.execute()` with `SET LOCAL session_replication_role = 'replica';`.
- **Rule 6 (`db.get()` banned)**: N/A here (no new queries) but stays in force for any code you touch.
- **Rule 7 (MCP read-only)**: `postgres-local` MCP is **read-only verification only**. Never INSERT/UPDATE/DELETE through it — all data changes go through the migration or seed script.
- **Rule 11 (no "not my fault")**: If ANY test fails during your work — even one that looks pre-existing — you must fix it before declaring done, or STOP and ask Tom.
- **Rule 15 (mixins/tenant_id)**: `QuoteTemplateLine` uses `StandardAuditMixin` and declares `tenant_id` explicitly. You are only changing the **nullability** of that explicit `tenant_id` field — do not touch the mixin timestamps.
- **Rule 16 (verify-before-write SQL)**: Query `information_schema.columns` for `quote_template_line` and `quote_template` this session before writing any SQL.

> **This is a DROP NOT NULL, not an ADD NOT NULL** — the 3-part NOT-NULL backfill pattern does **NOT** apply to `upgrade()`. The constrained direction here is `downgrade()` (which restores NOT NULL).

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current **unit-only** test baseline:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y skipped`**.

> If any tests are already failing before you start: do NOT treat them as "pre-existing" and proceed. Either confirm with Tom it's a known accepted failure, or fix it first. Do not start work with tests in an unexplained failed state.

---

## Pre-Work: Run MCP Verification Queries

> **MCP Usage Rule**: The `postgres-local` MCP is for **read-only verification only**. Use it to confirm table names, column types, and existing data. Never use it to INSERT, UPDATE, or DELETE. If a query fails or returns an error → STOP and ask Tom.

Run **all** of these via `postgres-local` MCP before writing any code. If any query returns unexpected results → **STOP and ask Tom**.

```sql
-- 1. Confirm current head (down_revision for the new migration must equal this)
SELECT version_num FROM public.alembic_version;
-- Expected at authoring time: 44b3427a0e57 (verify — if different, use what MCP returns)

-- 2. Confirm quote_template_line.tenant_id is currently NOT NULL with no default
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'quote_template_line'
ORDER BY ordinal_position;
-- Expected: tenant_id → uuid, is_nullable = NO, column_default = NULL

-- 3. Confirm the tenant FK definition (must remain valid for NULL after the change)
SELECT conname, pg_get_constraintdef(oid) AS def
FROM pg_constraint
WHERE conrelid = 'public.quote_template_line'::regclass AND contype = 'f';
-- Expected: fk_quote_template_line_tenant = FK (tenant_id) REFERENCES tenant(id) ON DELETE RESTRICT

-- 4. Confirm the parent precedent: quote_template.tenant_id is ALREADY nullable
SELECT is_nullable FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'quote_template' AND column_name = 'tenant_id';
-- Expected: YES

-- 5. Confirm the 3 system templates and their 9 workaround lines (owned by test tenant …0001)
SELECT qtl.quote_template_id, qtl.tenant_id, qtl.display_order, qtl.description
FROM public.quote_template_line qtl
JOIN public.quote_template qt ON qtl.quote_template_id = qt.id
WHERE qt.tenant_id IS NULL
ORDER BY qtl.quote_template_id, qtl.display_order;
-- Expected: 9 rows, all tenant_id = 00000000-0000-0000-0000-000000000001

-- 6. Confirm there is NO unique constraint on the natural key (so seed idempotency stays as an existence check, not ON CONFLICT)
SELECT conname, contype FROM pg_constraint
WHERE conrelid = 'public.quote_template_line'::regclass AND contype IN ('u','p');
-- Expected: only the primary key on id
```

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
backend/app/models/quoting.py                        ← QuoteTemplateLine (line ~1224); the tenant_id field to change
backend/api/routes/quote_templates.py                ← _create_quote_from_template_impl (~line 401-509): confirm the apply-flow filters lines by quote_template_id only (NO change needed)
backend/migrations/scripts/seed_core.py              ← system-template-line block (~line 2636-2827) + inspect block (~line 3149)
backend/migrations/versions/2026_07_27_1336-44fb6fed24c3_class_b1_classification.py  ← blank-migration + op.execute pattern reference
backend/tests/conftest.py                            ← available fixtures (test_tenant, test_customer, test_site, test_quote_status)
backend/db_models_map.md                             ← confirm QuoteTemplateLine mapping before/after
```

Also grep for other consumers to confirm nothing else assumes a non-null tenant on template lines:

```bash
grep -rn "QuoteTemplateLine" backend/ --include="*.py"
```

---

## Background / Context

System quote templates are platform-level (`quote_template.tenant_id IS NULL`, `is_system_template = true`) — 3 exist. Their **lines** currently violate the concept: `quote_template_line.tenant_id` is `NOT NULL`, so the seed inserts the 9 system-template lines under the canonical **test-tenant** UUID `00000000-0000-0000-0000-000000000001` as a workaround. That's wrong ownership and fails on any DB without that tenant.

This batch makes `quote_template_line.tenant_id` **nullable** (matching its own already-nullable parent `quote_template.tenant_id`), converts the 9 existing workaround rows to `tenant_id = NULL`, and updates the seed to create system-template lines with `NULL` tenant and no test-tenant dependency.

**No endpoint changes** — `_create_quote_from_template_impl` already filters lines by `quote_template_id` only.

---

## Task 1 — Model: make `tenant_id` nullable

In `backend/app/models/quoting.py`, change `QuoteTemplateLine.tenant_id`:

```python
# BEFORE
tenant_id: uuid.UUID = Field(
    sa_column=Column(
        PG_UUID,
        ForeignKey("tenant.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    ),
)

# AFTER — NULL = platform/system-template line (no owning tenant); mirrors quote_template.tenant_id
tenant_id: uuid.UUID | None = Field(
    default=None,
    sa_column=Column(
        PG_UUID,
        ForeignKey("tenant.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    ),
)
```

Do not change any other field. Keep `StandardAuditMixin`, the `__table_args__` indexes, and all other columns exactly as-is.

Intermediate check: `python -m pytest -m unit --tb=short -q 2>&1 | tail -5`

---

## Task 2 — Alembic migration (blank)

Per `pilot-python-engineer-methods.md` §13:

```bash
cd <repo>/backend && source .venv/bin/activate
alembic revision -m "qt_fix_1_quote_template_line_tenant_nullable"
```

Set `down_revision` to the head confirmed in MCP query #1 (expected `44b3427a0e57`).

`upgrade()`:
```python
def upgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")

    # 1. Drop NOT NULL — the tenant FK (ON DELETE RESTRICT) stays valid for NULL values.
    op.execute(
        "ALTER TABLE public.quote_template_line "
        "ALTER COLUMN tenant_id DROP NOT NULL;"
    )

    # 2. Convert existing system-template lines from the test-tenant workaround to
    #    tenant-agnostic NULL. Scoped to lines whose parent template is a system
    #    template (quote_template.tenant_id IS NULL) — never touches real tenant lines.
    op.execute(
        """
        UPDATE public.quote_template_line qtl
        SET tenant_id = NULL
        FROM public.quote_template qt
        WHERE qtl.quote_template_id = qt.id
          AND qt.tenant_id IS NULL
          AND qtl.tenant_id IS NOT NULL;
        """
    )
```

`downgrade()`:
```python
def downgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")

    # 1. Re-attach system-template lines to the canonical test tenant so NOT NULL
    #    can be restored. CAVEAT: requires test tenant 0000…0001 to exist (documented below).
    op.execute(
        """
        UPDATE public.quote_template_line qtl
        SET tenant_id = '00000000-0000-0000-0000-000000000001'
        FROM public.quote_template qt
        WHERE qtl.quote_template_id = qt.id
          AND qt.tenant_id IS NULL
          AND qtl.tenant_id IS NULL;
        """
    )

    # 2. Restore NOT NULL.
    op.execute(
        "ALTER TABLE public.quote_template_line "
        "ALTER COLUMN tenant_id SET NOT NULL;"
    )
```

Add a docstring documenting the **downgrade caveat**: downgrade restores the test-tenant workaround and assumes tenant `…0001` exists; on a DB without it, delete the NULL-tenant system-template lines (or re-seed the test tenant) before downgrading. Acceptable — downgrade is dev/local only.

Test the full cycle:
```bash
alembic upgrade head && alembic downgrade -1 && alembic upgrade head && alembic current
```

Then MCP-verify the end state:
```sql
SELECT is_nullable FROM information_schema.columns
WHERE table_schema='public' AND table_name='quote_template_line' AND column_name='tenant_id';   -- YES

SELECT count(*) FROM public.quote_template_line qtl
JOIN public.quote_template qt ON qtl.quote_template_id = qt.id
WHERE qt.tenant_id IS NULL AND qtl.tenant_id IS NULL;   -- 9
```

---

## Task 3 — Update `seed_core.py` system-template-line block

In `backend/migrations/scripts/seed_core.py`:

1. **Remove the test-tenant guard** that skips line creation (`test_tenant_id = "…0001"`, the `tenant_exists` check, and the `if not tenant_exists: … else:` wrapper). System-template lines no longer depend on a tenant. Keep the `qco_line_type` lookup and the `template_lines` list exactly as-is (values unchanged).

2. **INSERT with `tenant_id = NULL`** — drop `tenant_id` (and its `:tid` bind) from the INSERT column list, letting it default to NULL, OR set it explicitly to `NULL`:
   ```sql
   INSERT INTO public.quote_template_line
   (id, quote_template_id, display_order, qco_line_type_id, description,
    default_quantity, default_unit_price_cents, customer_visible,
    is_section_header, is_active, created_at, updated_at)
   VALUES (gen_random_uuid(), CAST(:tmpl_id AS uuid), :display_order,
           CAST(:qco_type_id AS uuid), :description, :qty, :price,
           true, false, true, NOW(), NOW())
   ```

3. **Idempotency existence check** becomes `tenant_id IS NULL`-scoped (the table has no unique natural key — keep the existence check, do NOT use `ON CONFLICT`):
   ```sql
   SELECT 1 FROM public.quote_template_line
   WHERE quote_template_id = CAST(:tmpl_id AS uuid)
     AND display_order = :display_order
     AND tenant_id IS NULL
   ```

4. **Update the final count query** (`~line 2817`) to count `WHERE tenant_id IS NULL` scoped to the 3 system template ids (or via the `quote_template.tenant_id IS NULL` join), and fix the log strings that reference the test tenant.

5. **Fix the stale comment** at `~line 2637` — it currently says `tenant_id is NOT NULL … even for system templates`. Replace with a note that system-template lines are `tenant_id = NULL` (platform-level), post QT-FIX-1.

6. **Update the `inspect` mode block** (`~line 3149`) if it filters/labels lines by the test tenant — the count join is already tenant-agnostic (`LEFT JOIN … ON qtl.quote_template_id = qt.id`), so verify it still reports 9 lines across 3 templates.

Run and verify:
```bash
cd <repo>/backend && source .venv/bin/activate
python migrations/scripts/seed_core.py --mode seed 2>&1 | tail -20
python migrations/scripts/seed_core.py --mode inspect 2>&1 | grep -A2 quote_template_line
```
Confirm idempotency: run `--mode seed` **twice**; the second run must report all 9 lines already exist (0 inserted).

---

## Task 4 — Regenerate model map + JSON schema

Model changed → regenerate the model map (redirect to file, pass the `app` dir arg):
```bash
cd <repo>/backend && source .venv/bin/activate
python generate_db_model_map.py app > db_models_map.md
grep -n "QuoteTemplateLine" db_models_map.md
```

Update the master JSON schema via the path-based tool (read `backend/README-schema_manager.md` first). Set `tenant_id.nullable = true` on `quote_template_line`:
```bash
# Inspect current state first
python schema_manager.py get --path tables.quote_template_line.columns.tenant_id

# Write the corrected column definition to a temp payload and set it
cat << 'EOF' > temp_payload.json
{ "type": "uuid", "nullable": true, "foreign_key": "tenant.id", "description": "Owning tenant. NULL = platform/system-template line (no owning tenant). Post QT-FIX-1." }
EOF
python schema_manager.py set --path tables.quote_template_line.columns.tenant_id --payload temp_payload.json
rm temp_payload.json
```
> Match the **existing** column-object shape for `quote_template_line.tenant_id` — run the `get` first and preserve whatever keys are already present (e.g. `index`), only flipping `nullable` to `true` and refreshing the description. If `schema_manager.py` errors → STOP and ask Tom (never hand-edit the JSON).

**No `export_openapi_json.py`** — there are no endpoint or schema (Pydantic) changes in this batch.

---

## Test Requirements

Per `backend/tests/README-adding-tests.md`:

Add tests in `backend/tests/domains/sales_quoting/` (new file, e.g. `test_qt_fix_1_system_template_lines.py`):

```python
pytestmark = [
    pytest.mark.domain_sales_quoting,
    pytest.mark.unit,
]
```

Required coverage:
1. **NULL-tenant line persists** — insert a `QuoteTemplateLine` with `tenant_id=None` on a system template (`tenant_id IS NULL`) via `db_session`; assert it commits and reads back with `tenant_id is None`. (Proves the constraint was dropped.)
2. **Apply system template → non-empty quote** — using the existing 3 system templates (or a fixture template with NULL tenant + NULL-tenant lines), call the apply-template `/test` endpoint (or `_create_quote_from_template_impl` directly with a `TestUserContext`) and assert `lines_created > 0` and that `QuoteLine` rows were created for the new quote scoped by the returned `quote_id`. This is the regression that proves the original bug (empty quote) is fixed.

Test-resilience rules (MANDATORY):
- Use `test_tenant`, `test_customer`, `test_site`, `test_quote_status` fixtures — never hardcoded UUIDs.
- Scope every assertion by IDs you inserted — never `assert len(all_rows) == N` (seed data is present: the 9 system lines already exist).
- Never UPDATE/DELETE shared seed rows; `db_session` rollback is your cleanup.
- The created `QuoteLine` rows belong to `test_tenant` (the applying tenant) even though the source template lines are NULL-tenant — assert on the quote you created.

---

## Final Verification

### Phase 1 — Unit Tests Only (during development)
```bash
cd <repo>/backend && source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```
All unit tests must pass before moving on. Fix any failure — including any that look pre-existing — before proceeding.

### Phase 2 — Lint + Full Suite (once, at the end)
```bash
cd <repo>/backend && source .venv/bin/activate

ruff check . --fix
ruff format .

python -m pytest --tb=short -q 2>&1 | tail -10
python -m pytest tests/domains/sales_quoting/ -v 2>&1 | tail -20

echo "=== QT-FIX-1 FINAL VERIFICATION COMPLETE ==="
```

> Warning-clean is part of done. Any failure in either phase must be fixed before the batch is declared done — no "pre-existing failure" exception without written confirmation from Tom.

---

## Definition of Done

Update the launch plan §2.0 row and the QT-FIX-1 card, plus `README-seed-data.md` §4, when each item is done:

- [ ] Pre-modification regression baseline captured (`X passed, Y skipped`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting (or confirmed with Tom)
- [ ] All 6 MCP pre-work queries run — head, nullability, FK, parent precedent, 9 rows, no-unique-key all confirmed (rules §16/§25)
- [ ] All mandatory source files read before writing code
- [ ] `QuoteTemplateLine.tenant_id` changed to `uuid.UUID | None` / `nullable=True` (no other field touched)
- [ ] Blank Alembic migration created; `down_revision` = MCP-confirmed head; `SET LOCAL session_replication_role = 'replica'` present in both directions
- [ ] `upgrade()` drops NOT NULL + converts 9 system lines to NULL; `downgrade()` restores test-tenant + NOT NULL; caveat documented in docstring
- [ ] Migration up→down→up cycle clean; `alembic current` shows new head
- [ ] MCP post-check: `tenant_id` nullable = YES; 9 system-template lines have `tenant_id IS NULL`
- [ ] `seed_core.py` updated: test-tenant guard removed, INSERT uses NULL tenant, existence check `tenant_id IS NULL`-scoped, count query + comments + inspect block fixed
- [ ] `seed_core.py --mode seed` idempotent across two runs (2nd run inserts 0); `--mode inspect` reports 9 lines / 3 templates
- [ ] `python generate_db_model_map.py app > db_models_map.md` run; `QuoteTemplateLine` present
- [ ] `schema_manager.py set` used for `quote_template_line.tenant_id.nullable = true` (path-based; never hand-edited)
- [ ] NO `export_openapi_json.py` (no endpoint change) — confirmed
- [ ] New test file uses `pytestmark` domain + unit markers; fixtures not hardcoded UUIDs
- [ ] Test 1 (NULL-tenant line persists) + Test 2 (apply system template → non-empty quote) both pass
- [ ] All DB-touching code remains sync `def` (rules §21)
- [ ] `ruff check . --fix && ruff format .` clean, no unjustified `# noqa`
- [ ] **Phase 1**: all unit tests pass
- [ ] **Phase 2**: full suite passes, warning-clean
- [ ] Final test count (before → after) documented
- [ ] Completion Summary added to the launch plan Appendix B
- [ ] `README-seed-data.md` §4 (Current Seed State) note for `quote_template_line` updated to reflect NULL-tenant system lines; if §10 tracks this, mark it ✅

---

## Completion Summary

After all Definition of Done items are complete:

1. Add a **Completion Summary** to `pilot-launch-plan.md` Appendix B using the template below, and flip the §2.0 master-status row + the QT-FIX-1 card to ✅.
2. Update `backend/README-seed-data.md` §4 for `quote_template_line` (system-template lines are now `tenant_id = NULL`), and mark any §10 tracked task ✅.

```markdown
### QT-FIX-1 — quote_template_line.tenant_id Nullable: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Source design doc**: `batch-qt-fix-1-design.md`
**Baseline**: X passed, Y skipped
**Final**: X+N passed, Y skipped (+N new tests)

#### What Was Accomplished
- Dropped NOT NULL on `quote_template_line.tenant_id` (migration `<rev>`); converted 9 system-template lines from the test-tenant workaround to `tenant_id = NULL` (platform-level), matching the already-nullable parent `quote_template.tenant_id`.
- Root cause: system templates (`tenant_id IS NULL`) could not own lines because the child required a tenant → applying a system template produced an empty quote. Now fixed.
- `seed_core.py` seeds system-template lines with NULL tenant, no test-tenant dependency, idempotent.

#### Files Changed / Created
| File | Action |
|---|---|
| `backend/app/models/quoting.py` | Updated — `QuoteTemplateLine.tenant_id` nullable |
| `backend/migrations/versions/<rev>_qt_fix_1_...py` | Created — DROP NOT NULL + data conversion |
| `backend/migrations/scripts/seed_core.py` | Updated — NULL-tenant system-template lines |
| `backend/db_models_map.md` | Regenerated |
| `dev-docs/db-design/pilot-db-schema-v2.6h.json` | Updated via schema_manager.py |

#### Tests Added
| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `tests/domains/sales_quoting/test_qt_fix_1_system_template_lines.py` | `sales_quoting` | N | ✅ |
```

---

## After This Task — Next Step

No frontend companion. Notify Tom on completion; QT-FIX-1 closes independently. `pnpm sync-api-types` is **not** required (no OpenAPI change).
