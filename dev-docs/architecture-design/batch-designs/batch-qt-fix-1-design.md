# Batch Design: QT-FIX-1 — Make `quote_template_line.tenant_id` Nullable (System-Template Lines)

**Batch**: QT-FIX-1
**Owner**: Pilot Python Engineer (backend-only)
**Type**: Schema fix (Alembic migration + model + seed) — **no endpoint changes**
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §2.0 / §2.3
**Prerequisite**: none (current Alembic head `44b3427a0e57`)
**Estimated session**: 1–1.5 hours
**Cost impact**: $0 (no new infrastructure)

---

## Background — The Design Flaw

System quote templates are platform-level (`quote_template.tenant_id IS NULL`, `is_system_template = true`). Three exist today (MCP-verified 2026-07-30):

| Template | `id` | `tenant_id` |
|---|---|---|
| Service Call Basic | `608e2c6e-344c-4a6d-9d43-bd86960d202f` | `NULL` |
| Installation Standard | `7d1647ca-aac4-4be1-bdb2-74325f37198a` | `NULL` |
| Fixed Bid Simple | `d615ecdf-fb53-453c-9631-e895effa1bf5` | `NULL` |

A system template is useless without lines: the "apply template to quote" flow (`_create_quote_from_template_impl`) fetches `QuoteTemplateLine` rows for the template and clones them into `QuoteLine` rows. With no lines, applying a system template yields an **empty quote**.

**The flaw**: `quote_template_line.tenant_id` is `NOT NULL` with a FK to `tenant`, so a line *cannot* exist without a tenant — but system-template lines conceptually belong to **no tenant**. The current seed works around this by inserting the 9 system-template lines under the **canonical test-tenant UUID** `00000000-0000-0000-0000-000000000001` (`seed_core.py`), guarded by a "test tenant must exist" check. This is wrong ownership and breaks on any environment where that tenant is absent.

**The fix**: make `quote_template_line.tenant_id` **nullable** (matching its own parent `quote_template.tenant_id`, which is already nullable with the identical `ON DELETE RESTRICT` FK), convert the 9 existing workaround rows to `tenant_id = NULL`, and update the seed to insert system-template lines with `tenant_id = NULL` and no test-tenant dependency.

---

## A. Input Read Summary

| Input | What was verified | Source |
|---|---|---|
| `quote_template_line` columns | `tenant_id` = `uuid`, `is_nullable = NO`, no default | `postgres-local` MCP `information_schema.columns` |
| `quote_template_line` FK | `fk_quote_template_line_tenant`: `FK (tenant_id) → tenant(id) ON DELETE RESTRICT` | `pg_constraint` (MCP) |
| No UNIQUE on natural key | Only PK on `id`; **no** unique constraint on `(quote_template_id, display_order)` — so `ON CONFLICT` cannot dedup; idempotency is by explicit existence check | `pg_constraint` (MCP) |
| Parent precedent | `quote_template.tenant_id` **is nullable** with identical FK (`fk_quote_template_tenant … ON DELETE RESTRICT`) | `pg_constraint` (MCP) |
| Existing data | 3 system templates (`tenant_id IS NULL`); 9 lines all owned by test-tenant `…0001` | MCP row query |
| `qco_line_type` refs | `labor`/`material`/`misc` platform rows (`tenant_id IS NULL`) exist | MCP |
| Apply-flow query | Filters lines by `quote_template_id` **only** (not tenant) → **no endpoint change needed** | `quote_templates.py` |
| Model | `QuoteTemplateLine.tenant_id` declared `nullable=False` | `quoting.py` |
| Alembic head | `44b3427a0e57` | `alembic_version` (MCP) |
| Migration pattern | Blank migration, raw `op.execute()`, `session_replication_role='replica'` for data ops | `class_b1_classification.py` |

---

## B. Migration Plan

**File**: `backend/migrations/versions/<ts>-<rev>_qt_fix_1_quote_template_line_tenant_nullable.py`
**`down_revision = "44b3427a0e57"`** (current head — verify via MCP `SELECT version_num FROM alembic_version;` before writing).

This is a **DROP NOT NULL** (not an ADD NOT NULL), so the 3-part NOT NULL pattern does **not** apply. The reverse (downgrade) is the constrained direction.

### `upgrade()`

```python
def upgrade() -> None:
    # Data ops touch an audited table — suppress trigger noise for the migration session.
    op.execute("SET LOCAL session_replication_role = 'replica';")

    # 1. Drop the NOT NULL constraint (FK to tenant is retained and stays valid for NULL).
    op.execute(
        "ALTER TABLE public.quote_template_line "
        "ALTER COLUMN tenant_id DROP NOT NULL;"
    )

    # 2. Convert existing system-template lines (workaround: owned by test tenant)
    #    to their correct tenant-agnostic form (tenant_id = NULL). Scoped strictly to
    #    lines whose parent template is a system template (quote_template.tenant_id IS NULL).
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

### `downgrade()`

```python
def downgrade() -> None:
    op.execute("SET LOCAL session_replication_role = 'replica';")

    # 1. Re-attach system-template lines to the canonical test tenant so the
    #    NOT NULL constraint can be restored (reverses the upgrade data step).
    #    CAVEAT: requires test tenant 0000…0001 to exist (FK ON DELETE RESTRICT).
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

> **Downgrade caveat (document in the migration docstring)**: `downgrade()` restores the test-tenant workaround and therefore assumes the canonical test tenant `…0001` exists. On an environment where it does not, the operator must first re-seed the test tenant or manually delete the NULL-tenant system-template lines before downgrading. This is acceptable — downgrade is a dev/local operation and `…0001` is always present there.

### Migration cycle test (required)
```bash
alembic upgrade head && alembic downgrade -1 && alembic upgrade head && alembic current
```

---

## C. Execution Order

| # | Step | File |
|---|---|---|
| 1 | MCP re-verify: `alembic_version`, `quote_template_line` columns/FK, current 9 rows | (MCP) |
| 2 | Model: `tenant_id` → `uuid.UUID | None`, `nullable=True`; update the field comment | `app/models/quoting.py` |
| 3 | Write blank Alembic migration (§B); run upgrade→downgrade→upgrade cycle | `migrations/versions/…` |
| 4 | Update `seed_core.py` system-template-line block: `tenant_id = NULL`, drop test-tenant guard dependency, fix idempotency check + count query + messages | `seed_core.py` |
| 5 | Run `seed_core.py --mode seed` then `--mode inspect`; confirm 9 lines with `tenant_id IS NULL` | (CLI) |
| 6 | Regenerate `db_models_map.md`; update JSON schema via `schema_manager.py` | (CLI) |
| 7 | Add tests (§F); Phase 1 unit → Phase 2 full suite + ruff | `tests/domains/sales_quoting/` |

---

## D. New API Endpoints

**None.** The apply-template query filters lines by `quote_template_id` only, so it already returns system-template lines regardless of their `tenant_id`. No route, schema, or OpenAPI change → **`export_openapi_json.py` is NOT run** for this batch.

---

## E. Pattern Reuse Decisions

- **Blank Alembic migration + raw `op.execute()`** — repo standard (methods §13). No `--autogenerate`.
- **`session_replication_role = 'replica'`** around data ops — matches the data-migration convention (inclusions §5).
- **Nullable-`tenant_id` platform-row pattern** — mirrors the existing `job_type` / `qco_line_type` / `quote_template` platform-vs-tenant model (null-tenant = platform/system row).
- **Idempotency by explicit existence check** — the table has no unique natural key, so the seed keeps its `SELECT 1 … WHERE …` guard (not `ON CONFLICT`), now scoped with `tenant_id IS NULL`.

---

## F. Shared Module Interfaces

### Model change (`quoting.py`)
```python
# BEFORE
tenant_id: uuid.UUID = Field(
    sa_column=Column(PG_UUID, ForeignKey("tenant.id", ondelete="RESTRICT"),
                     nullable=False, index=True),
)
# AFTER — NULL = platform/system-template line (no owning tenant)
tenant_id: uuid.UUID | None = Field(
    default=None,
    sa_column=Column(PG_UUID, ForeignKey("tenant.id", ondelete="RESTRICT"),
                     nullable=True, index=True),
)
```

### Seed change (`seed_core.py`)
- Remove the `test_tenant_id` guard gating line creation (the `if not tenant_exists:` skip). System-template lines no longer need a tenant.
- INSERT with `tenant_id = NULL` (remove the `tid` bind from the VALUES list, or bind `None`).
- Idempotency existence check becomes:
  ```sql
  SELECT 1 FROM public.quote_template_line
  WHERE quote_template_id = CAST(:tmpl_id AS uuid)
    AND display_order = :display_order
    AND tenant_id IS NULL
  ```
- Update the final count query (`WHERE tenant_id IS NULL AND quote_template_id IN (…system ids…)`) and the log strings (drop "test tenant" wording).
- Update the block comment at `seed_core.py` — it currently states `tenant_id is NOT NULL … even for system templates`; that is now false.

> **Migration ↔ seed parity note**: system-template **lines** remain **seed-owned** (they were never Alembic-owned because the NOT NULL constraint previously made an Alembic INSERT with `NULL` impossible). This batch keeps that division: the migration converts *existing* rows; `seed_core.py` is the source of truth for creating them on a fresh DB. No new INSERT is added to the migration.

No Celery tasks, no new services.

---

## G. Open Questions Resolved

1. **Do we need to change the apply-template endpoint query?** No — it filters by `quote_template_id` only; NULL-tenant lines are already returned.
2. **Should system-template lines move to Alembic ownership?** Not in this batch — "keep it small." They stay seed-owned; only the constraint + existing-row conversion is Alembic. (A future DB-MGMT-1 batch may promote them to Alembic-owned with stable UUIDs.)
3. **`ON CONFLICT` for idempotency?** No — no unique natural key exists; keep the explicit existence check.
4. **Downgrade correctness?** Restores the test-tenant workaround (documented caveat); faithful reverse of the upgrade for dev/local.
5. **Any RLS / tenant-scoping leak from NULL tenant lines?** No — lines are only ever read via `quote_template_id` (a template the caller already resolved with the system-OR-own-tenant guard at `quote_templates.py`).

---

## Definition of Done (summary — full checklist in the prompt)

- Migration up/down/up cycle clean; head advances past `44b3427a0e57`.
- `quote_template_line.tenant_id` nullable in live DB (MCP-verified); 9 system lines now `tenant_id IS NULL`.
- Model updated; `db_models_map.md` + JSON schema synced.
- `seed_core.py` seeds system-template lines with NULL tenant, idempotent, no test-tenant dependency.
- New test proves a NULL-tenant system template applies to a quote and produces non-empty `QuoteLine` rows.
- Phase 1 (unit) + Phase 2 (full suite + ruff) green; no OpenAPI regen (no endpoint change).
- Launch plan §2.0 row + card updated to ✅; `README-seed-data.md` §4 note corrected.
