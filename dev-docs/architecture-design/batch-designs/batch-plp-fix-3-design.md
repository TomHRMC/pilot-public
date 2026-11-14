# Batch Design: PLP-FIX-3 — Quote v1-at-Create + Versionless-Quote Backfill (Issue 6)

**Batch**: PLP-FIX-3 (backend only)
**Version**: 1.0
**Date**: 2026-09-02
**Author**: Pilot Architect
**Status**: Approved for prompt authoring
**Bug report**: `dev-docs/analysis/PLP-testing-bugs-2026-09-02.md` — Issue 6
**Predecessor batches**: `batch-plp-fix-1-design.md` (closed ✅ 2026-08-30) · `batch-plp-fix-2-design.md` (closed ✅ 2026-09-01)
**Prompt**: `batch-plp-fix-3-python-engr-prompt.md`
**Platform**: Backend only (`backend/`) — no API contract change, no FE impact, `pnpm sync-api-types` N/A

---

## Scope Statement

Every quote must have an active `quote_version` row from the moment of creation. Today `_create_quote_impl()` creates the `quote` row only; versions appear only at submit-for-approval, apply-discount, or explicit version POST (`quotes.py`). The aggregated detail endpoint (`get_quote_detail()`) hard-requires an active version and 404s otherwise — so every builder-created draft quote is unviewable until a version-triggering action occurs (prod Issue 6: "Failed to load quote / 404"). This batch: (1) creates v1 atomically at quote creation, (2) backfills v1 for existing versionless quotes via an idempotent data migration (Tom's prod test quote), (3) adds regression tests that exercise the real create endpoint without hand-built version fixtures.

**Explicitly out of scope**: the pre-existing `db.get()` usage inside `_create_quote_version_impl` (line 596 — retained as-is to keep the diff minimal; flagged to BE-TESTS-MAINT); version deactivation semantics (unchanged — latest-active-by-`version_no` wins, as today); QuoteDetailPage's `getApiProblem` adoption (routed to BE-TESTS-MAINT per the bug report); quote `snapshot` consumers (public link/PDF — untouched); no schema JSON change, no model change, no OpenAPI delta.

---

## A. Input Read Summary

| Input | What it provided | Read |
|---|---|---|
| `PLP-testing-bugs-2026-09-02.md` Issue 6 | Symptom + verified root-cause chain | ✅ |
| `quotes.py` — `_create_quote_impl` (123–178), `_create_quote_version_impl` (568–640), `get_quote_detail_endpoint` (1582–1609) | Create flow commits quote-only; version impl self-commits; `/detail` delegates to service | ✅ |
| `quote_service.py` — `get_quote_detail` (202–311) | The active-version hard requirement (404 at 286–295); detail reads LIVE `quote_line` rows, not the snapshot | ✅ |
| MCP `information_schema.columns` — `quote_version` | 10 columns: `id`, `tenant_id`, `quote_id`, `version_no` int NN, `snapshot` jsonb NN, `pdf_object_key` null, `is_active` bool NN default true, `presentation_style` varchar NN default 'clean', `created_at` NN, `created_by` null. Append-only (no updated_*) | ✅ 2026-09-02 |
| MCP `pg_constraint` — `quote_version` | `uq_quote_version_quote_id_version_no` UNIQUE(quote_id, version_no); FKs to quote/tenant/user all RESTRICT; `presentation_style` CHECK ∈ {clean, line_itemed, hybrid} | ✅ 2026-09-02 |
| MCP `pg_trigger` — `quote_version` | `audit_quote_version_changes` (log_changes); `trg_quote_version_guard_created_immutable` (UPDATE-guard only — INSERT/DELETE safe) | ✅ 2026-09-02 |
| MCP `alembic_version` | Current head `c8d06a6ffdd2` | ✅ 2026-09-02 |
| MCP quote↔version data check | All 8 sampled local quotes have exactly 1 active version (seed-created); Tom's prod test quote is not local (he tested prod) | ✅ 2026-09-02 |
| `seed_scenario_quote_to_cash.py` | Seed comment: *"quote_version (required by /detail endpoint)"* — seeds already enforce the invariant; no seed change needed | ✅ |
| Test-scaffolding audit (grep `QuoteVersion(` across `backend/`) | Only production instantiation = `_create_quote_version_impl`; all others are test fixtures (conftest:1157, tp_b2/b3, acceptance, phase_9) — why the suite was green. HTTP-create tests (`test_quotes.py`, `test_plp_fix1_quote_create_no_gate.py`, `test_ui_fix_1c_pagination.py`, `test_job_ui_b1.py`) do NOT hand-build versions → no unique-constraint collisions expected; ORM-built fixtures bypass the route layer → unaffected | ✅ |
| `backend/python-engr-std-prompt-inclusions.md` | Full read — section order, §20 Seed Rollout, two-phase gate | ✅ |
| `pilot-architect-methods.md` §3 | This workflow | ✅ |

---

## B. Migration Plan

**One blank data migration** (no DDL — no tables/columns/constraints change). Expected head at authoring: `c8d06a6ffdd2` (engineer re-verifies via `SELECT version_num FROM public.alembic_version;` + `alembic heads`).

### B.1 Pre-Migration Verification (MCP — engineer re-runs all)

1. `quote_version` columns (above) — must match before writing any SQL.
2. `uq_quote_version_quote_id_version_no` present (backfill relies on it for safety).
3. Versionless-quote census: `SELECT count(*) FROM public.quote q WHERE NOT EXISTS (SELECT 1 FROM public.quote_version v WHERE v.quote_id = q.id AND v.is_active);` — record the number; local expectation ~0 (seeded quotes comply), prod has ≥1 (Tom's test quote). The migration must be correct regardless of count.

### B.2 Backfill Migration `plp_fix_3_backfill_quote_version_v1`

`alembic revision -m "plp_fix_3_backfill_quote_version_v1"` (blank) → `down_revision = "c8d06a6ffdd2"` (or whatever `alembic heads` returns at execution time).

**upgrade()** — begins with `op.execute("SET LOCAL session_replication_role = 'replica';")` (Rule 4 data-migration convention; also suppresses audit-trigger churn), then a single idempotent INSERT:

```sql
INSERT INTO public.quote_version
    (id, tenant_id, quote_id, version_no, snapshot, is_active, presentation_style, created_at, created_by)
SELECT
    gen_random_uuid(),
    q.tenant_id,
    q.id,
    COALESCE(mx.max_vn, 0) + 1,
    jsonb_build_object(
        'quote', to_jsonb(q),
        'lines', COALESCE(ls.lines, '[]'::jsonb),
        'source', 'plp_fix_3_backfill'
    ),
    true,
    'clean',
    now(),
    NULL
FROM public.quote q
LEFT JOIN (
    SELECT quote_id, max(version_no) AS max_vn
    FROM public.quote_version GROUP BY quote_id
) mx ON mx.quote_id = q.id
LEFT JOIN (
    SELECT quote_id, jsonb_agg(to_jsonb(ql) || '{"taxes": []}'::jsonb) AS lines
    FROM public.quote_line GROUP BY quote_id
) ls ON ls.quote_id = q.id
WHERE NOT EXISTS (
    SELECT 1 FROM public.quote_version av
    WHERE av.quote_id = q.id AND av.is_active
);
```

Design notes:
- **Scope = quotes with no ACTIVE version** (covers both no-versions-at-all and only-inactive-versions). `version_no = COALESCE(max,0)+1` respects `uq_quote_version_quote_id_version_no`.
- **`'source': 'plp_fix_3_backfill'` marker key** — makes the downgrade surgical. Snapshot consumers read only `["quote"]`/`["lines"]` — an extra top-level key is invisible to them.
- **Line entries carry `"taxes": []`** for shape compatibility with live snapshots (which nest taxes per line). Backfilled v1 snapshots are historical-only: customer-facing artifacts (public link/PDF/acceptance) always reference a fresh version created at submit/send time, never v1.
- **`to_jsonb(q)`** ≈ `quote.model_dump(mode="json")` shape (snake_case keys, ISO timestamps) — close enough for a historical record; documented divergence from live-built snapshots.
- `created_by = NULL` (system backfill; column nullable, FK RESTRICT unaffected).
- Idempotent: re-running heals nothing twice (`NOT EXISTS` guard).

**downgrade()** — `SET LOCAL session_replication_role = 'replica';` then:
```sql
DELETE FROM public.quote_version WHERE snapshot->>'source' = 'plp_fix_3_backfill';
```
Exact reverse; touches only rows this migration created. The `guard_created_fields_immutable` trigger fires on UPDATE only — DELETE is safe.

### B.3 Scratch-DB Proof (§7.6 standing rule)

Before shipping: run the full cycle on a scratch DB — `alembic upgrade head` → `alembic downgrade -1` → `alembic upgrade head` → `alembic current`; plus a functional proof: create a versionless quote directly in SQL pre-upgrade (bypassing the app), upgrade, confirm it has an active v1 with the marker key; downgrade, confirm removal.

### B.4 Seed Data Rollout (Rule 11.5 / inclusions §20)

- **Layer 1 (core/platform)**: N/A — no lookup/reference rows.
- **Layer 2 (scenario)**: N/A — seeds already create v1 per quote (`seed_scenario_quote_to_cash.py`, plus the second draft-quote site at 1583). No seed-script change; the migration is the healer for environments with user-created versionless quotes (prod). `README-seed-data.md` §4 unchanged (no seed-model change) — the engineer states this verification in the Completion Summary.

---

## C. Execution Order

| # | Step | Why this order |
|---|---|---|
| 1 | Pre-work: baseline (`pytest -m unit`), 5 MCP queries, mandatory file reads | Known-good count + verified schema before any code |
| 2 | Task 1 — Extract `_insert_quote_version()` (no-commit inner) from `_create_quote_version_impl`; 3 existing call sites behavior-preserved | Refactor first, alone — proves zero behavior change via the existing suite before the new wiring |
| 3 | Task 2 — `_create_quote_impl` creates v1 in the same transaction (`flush` → insert → single `commit`) | The fix; depends on Task 1's extraction |
| 4 | Task 3 — Backfill migration + scratch-DB cycle proof | Ships the prod healer; after the code fix so new quotes never need it again |
| 5 | Task 4 — Regression tests (4 tests, real-endpoint path) | Locks the invariant |
| 6 | Task 5 — Suite repairs for any version-collision fallout (expected small; see §G Q3), ruff gate, two-phase final verification | Rule 11 — zero failures |

---

## D. New API Endpoints

**None.** No route, contract, request/response, RBAC, or error-shape change. `POST /api/v1/quotes` returns the same `QuoteResponse`; the v1 creation is an internal side effect. OpenAPI regeneration: N/A (no spec delta) — engineer confirms no decorator/schema edits were needed and states it in the Completion Summary.

---

## E. Pattern Reuse Decisions

| Pattern | Source | Application |
|---|---|---|
| Tenant-scoped `select()` (no `db.get()` on tenant-scoped models) | python-engineer Rule 6 / methods §7.1 | Any new query written in this batch (none beyond the extracted inner function, which receives the already-scoped `Quote`) |
| RFC 7807 Problem Details | inclusions §13 | Unchanged — no new raises |
| Idempotency-Key on POST /quotes | infra-constraints §5 / existing `quote.idempotency_key` (`quotes.py`) | Replay-safety: the idempotency layer returns the cached response without re-executing the impl → no double v1. Documented, no code change |
| Blank migration + `SET LOCAL session_replication_role = 'replica'` | Rule 4 / inclusions §5 | Backfill migration (upgrade AND downgrade) |
| Test-endpoint twin pattern (`/test`) | inclusions §11 | Tests use the existing `POST /api/v1/quotes/test`, `POST /{id}/versions/test`, `GET /{id}/detail/test` twins — no new endpoints |

---

## F. Shared Module Interfaces

Exact signatures the engineer implements in `api/routes/quotes.py`:

```python
def _insert_quote_version(
    quote: Quote,
    db: Session,
    presentation_style: str = "clean",
) -> QuoteVersion:
    """
    Insert the next QuoteVersion for an already tenant-verified Quote.

    Builds the snapshot from the (flushed) quote ORM object + its current
    quote_line rows (with nested taxes), computes version_no = max+1,
    db.add() + db.flush() ONLY — never commits. Caller owns the transaction.
    Returns the flushed QuoteVersion (id populated).
    """

def _create_quote_version_impl(  # signature unchanged
    quote_id: UUID,
    db: Session,
    user_context: AuthenticatedUser | TestUserContext,
    create_in: QuoteVersionCreate | None = None,
) -> QuoteVersion:
    """
    Behavior preserved for the 3 existing call sites (test endpoint,
    authenticated POST /{quote_id}/versions, apply-discount):
    tenant-checks the quote (existing shape retained — see Out of Scope),
    delegates to _insert_quote_version(quote, db, create_in.presentation_style),
    then db.commit() + db.refresh() as today.
    """
```

And in `_create_quote_impl` (after line 175, replacing the bare commit):

```python
    db.add(quote)
    db.flush()                                  # quote.id available; lines query returns []
    _insert_quote_version(quote, db)            # v1, is_active=True, same transaction
    db.commit()
    db.refresh(quote)
    return quote
```

No Celery tasks. No service-layer signature changes (`get_quote_detail` untouched).

---

## G. Open Questions Resolved

**Q1 — Why not make `get_quote_detail()` tolerate missing versions instead?**
Rejected. It would leave the "every quote has an active version" invariant broken at the write source and push null-handling into every consumer (`quote_version_id` is used for optimistic locking, public links, approval comments, acceptance). The seed system already treats v1-at-draft as the norm. Enforcing at create is the smaller, more honest change — one writer fixed instead of N readers tolerating.

**Q2 — Atomicity: two commits (quote, then version) or one transaction?**
One transaction (`flush` → insert → single `commit`). A two-commit design leaves a crash window that recreates the exact bug state. The extraction in Task 1 exists precisely to enable this without changing `_create_quote_version_impl`'s external behavior.

**Q3 — Will auto-v1 break existing tests? (regression-risk assessment)**
Audited at design time. Tests fall into three classes: (a) HTTP-create tests that never hand-build versions (`test_quotes.py`, `test_plp_fix1_quote_create_no_gate.py`, `test_ui_fix_1c_pagination.py`, `test_job_ui_b1.py`) — unaffected, they only assert 201s/pagination; (b) ORM-built quote fixtures (`conftest.test_quote_version`, tp_b2/tp_b3, phase_9, acceptance) — bypass the route layer entirely, so no auto-v1 and no `uq_quote_version_quote_id_version_no` collision; (c) any test that HTTP-creates a quote AND THEN hand-builds a v1 for it — would collide (auto v1 already occupies (quote_id, 1)). The design-time grep found no class-(c) test, but the suite is the arbiter: Rule 11 applies — the engineer fixes any collision by using the auto-created v1 or hand-building v2. Also noted: `conftest.test_quote_version` passes `subtotal_cents`/`tax_cents`/`total_cents` kwargs that do NOT exist as DB columns (scaffolding drift) — out of scope; flagged to BE-TESTS-MAINT.

**Q4 — Should v1 creation backfill `quote_line` rows into the snapshot when lines exist?**
At create time there are never lines (`QuoteCreate` carries none; lines are separate POSTs). The backfill migration DOES aggregate existing lines (with `"taxes": []` shape markers) so healed quotes have faithful historical snapshots. Live v1 snapshots therefore always have `lines: []` — consistent and correct; `/detail` reads live lines regardless.

**Q5 — Version deactivation semantics?**
Unchanged. `_create_quote_version_impl` never deactivated older versions and still doesn't; `get_quote_detail` picks the latest active by `version_no` desc. v1-at-create composes with submit-time v2 exactly as seed data already does.

**Q6 — Does v1-at-create affect change-order conflict detection (`quote_version_active` trigger conditions in `seed_core.py`)?**
No. Those are conflict-rule registry values evaluated during QB change-order sync flows, not DB triggers; a draft v1's existence fires nothing by itself. No change-order code path is touched.

**Q7 — Backfill on local dev DB heals nothing (count ≈ 0) — how do we prove it works?**
The scratch-DB functional proof (§B.3): insert a versionless quote via raw SQL (bypassing the app), run upgrade, assert the active v1 exists with the marker key; downgrade removes it. This proves the migration end-to-end without needing dirty local data. Prod application is the normal deploy-migration path (Tom).

**Q8 — Anything needed for `quote_version` audit trail?**
`set_audit_context_sync()` is already called by the authenticated create endpoint before `_create_quote_impl` (existing behavior — verify in pre-work reads, do not add a second call). The v1 insert rides the same session/transaction, so `audit_log` attribution for the version row inherits the same actor context. The migration uses replica role (no audit rows for backfill churn) per data-migration convention.
