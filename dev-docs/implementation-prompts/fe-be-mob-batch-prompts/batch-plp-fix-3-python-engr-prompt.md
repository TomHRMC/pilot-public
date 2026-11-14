# Implementation Prompt: PLP-FIX-3 — Quote v1-at-Create + Versionless-Quote Backfill (Issue 6)

**Mode**: Pilot Python Engineer
**Batch**: PLP-FIX-3
**Source plan**: `dev-docs/analysis/pilot-launch-plan.md` §3.23
**Design doc**: `dev-docs/architecture-design/batch-designs/batch-plp-fix-3-design.md` — read sections A–G in full
**Bug report**: `dev-docs/analysis/PLP-testing-bugs-2026-09-02.md` — Issue 6
**Estimated session**: 1.5–2 hours
**Platform**: Backend only (`backend/`)
**Branch**: `feature/plp-founder-mvp-batches`

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document; the hard rules are non-negotiable STOPs
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §13 (Alembic), §8 (Router Design), §5 (Model Design), §16 (Standard Task Workflow)
- **`backend/tests/README-adding-tests.md`** — full document; governs test structure, domain markers, fixture rules

Critical rules for this batch:

- **Rule 1**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. If MCP returns an error → **STOP and ask Tom**.
- **Rule 4**: All Alembic migrations must be written as **blank** migrations (never `--autogenerate`). Data changes use raw `op.execute()` with `SET LOCAL session_replication_role = 'replica';` — this batch's migration is a pure data backfill, so this applies to BOTH `upgrade()` and `downgrade()`.
- **Rule 6**: `db.get()` is permanently banned on tenant-scoped models — any query YOU write uses tenant-scoped `select()`. (Note: the pre-existing `db.get()` at `quotes.py` is explicitly OUT OF SCOPE — do not refactor it; see design doc Out of Scope.)
- **Rule 11**: If ANY test fails during your work — even one that appears pre-existing — fix it before declaring done. **This batch intentionally changes create-quote side effects; suite fallout (version-fixture collisions) is anticipated and is yours to repair per design §G Q3.**
- **Rule 12 (sync routes)**: Every DB-touching route and `_impl()` is a plain `def`. Never convert a handler touching the sync `Session` to `async def`.
- **Rule 14 (Ruff)**: run ruff **only against changed files** (`git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||'`); fix ALL errors in those files.
- **Rule 16 (verify, don't assume)**: 186 tables exist — query `information_schema.columns` for `quote_version` and `quote` this session before writing SQL.

---

## Pre-Work: Establish Regression Baseline

Before touching any file, capture the current **unit-only** test baseline:

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`** (expect ~4751 passed, 1 skipped — the PLP-FIX-2 Part A final).

> **If any tests are already failing before you start**: do NOT proceed on assumption — confirm with Tom or fix first.

---

## Pre-Work: Run MCP Verification Queries

Run **all** of these via `postgres-local` MCP before writing any code. If any query returns unexpected results → **STOP and ask Tom**.

> **MCP Usage Rule**: `postgres-local` is **read-only verification only** — never INSERT/UPDATE/DELETE via MCP. All data changes go through application code, seed scripts, or Alembic migrations. On any error → STOP and ask Tom. (`postgres-prod` exists but needs Tom's SSH tunnel — this batch does NOT use it.)

```sql
-- 1. quote_version columns (engineer safety net — verify before ANY SQL)
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'quote_version'
ORDER BY ordinal_position;
-- Expect 10 columns: id, tenant_id, quote_id, version_no (int4 NN), snapshot (jsonb NN),
-- pdf_object_key (null), is_active (bool NN default true), presentation_style (varchar NN default 'clean'),
-- created_at (NN), created_by (null). NO updated_at/updated_by (AppendOnlyMixin).

-- 2. Constraints the backfill relies on
SELECT conname, contype, pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE conrelid = 'public.quote_version'::regclass
ORDER BY conname;
-- Must include uq_quote_version_quote_id_version_no UNIQUE (quote_id, version_no)
-- and presentation_style CHECK IN ('clean','line_itemed','hybrid').

-- 3. Versionless-quote census (records what the migration will heal — do NOT assume 0)
SELECT count(*) AS versionless
FROM public.quote q
WHERE NOT EXISTS (
  SELECT 1 FROM public.quote_version v
  WHERE v.quote_id = q.id AND v.is_active
);
-- Local expectation: 0 (seeds comply). Record the actual number in your Completion Summary.

-- 4. Current alembic head
SELECT version_num FROM public.alembic_version;
-- Expect c8d06a6ffdd2. If different, your migration's down_revision = whatever this returns.

-- 5. quote table columns referenced by the snapshot (verify the table the backfill SELECTs)
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'quote'
ORDER BY ordinal_position;
```

---

## Pre-Work: Read These Source Files

Use `read_file` on each of these before writing any code:

```
backend/api/routes/quotes.py                     ← _create_quote_impl (123–178), _create_quote_version_impl (568–640), the POST /quotes endpoints (1419+), the /test twins (924+)
backend/services/quote_service.py                ← get_quote_detail (202–311) — the active-version requirement this batch satisfies
backend/api/schemas/quotes.py                    ← QuoteCreate, QuoteVersionCreate, QuoteDetailResponse shapes
backend/app/models/quoting.py                    ← Quote, QuoteVersion (AppendOnlyMixin), QuoteLine
backend/app/models/mixins.py                     ← AppendOnlyMixin semantics
backend/tests/conftest.py                        ← fixtures incl. test_quote_version (1127–1171 — ORM-built; do NOT modify)
backend/migrations/versions/  (most recent file) ← migration style reference (head c8d06a6ffdd2)
backend/tests/domains/sales_quoting/test_plp_fix2_qco_line_types.py ← the sibling batch's test file — style/domain-marker reference
```

Also run these greps to map blast radius:

```bash
grep -rn "_create_quote_version_impl" backend/ --include="*.py"
grep -rn "_create_quote_impl" backend/ --include="*.py"
grep -rln "client.post(\"/api/v1/quotes" backend/tests --include="*.py"
```

---

## Background / Context

**Prod Issue 6** (Tom, 2026-09-02): a newly created quote cannot be viewed — the detail page shows "Failed to load quote / 404".

Root cause (verified at design time): `_create_quote_impl()` never creates a `quote_version` row, but `get_quote_detail()` (the aggregated endpoint behind `GET /api/v1/quotes/{id}/detail`) hard-requires an **active** version and raises RFC 7807 404 *"Quote version not found"* otherwise. Versions are only created later in the lifecycle (submit-for-approval, apply-discount, explicit version POST). Seeds create v1 per quote precisely because the detail endpoint requires it; tests hand-build versions in fixtures — so the suite was green while every real builder-created draft 404'd. Prod never surfaced it because quote creation was 402-dead until PLP-FIX-1.

This batch enforces the invariant **"every quote has an active v1 from creation"** at the write source, backfills existing versionless quotes (Tom's prod test quote), and locks it with real-endpoint regression tests. Full reasoning: design doc §G (Q1–Q8) — those decisions are final, do not re-open them.

---

## Task 1 — Extract `_insert_quote_version()` (behavior-preserving refactor)

In `backend/api/routes/quotes.py`, extract the insert core of `_create_quote_version_impl` into a no-commit inner function with this exact signature (design §F):

```python
def _insert_quote_version(
    quote: Quote,
    db: Session,
    presentation_style: str = "clean",
) -> QuoteVersion:
    """
    Insert the next QuoteVersion for an already tenant-verified Quote.

    Builds the snapshot from the (flushed) quote ORM object + its current
    quote_line rows (taxes nested per line), computes version_no = max+1,
    db.add() + db.flush() ONLY — never commits. Caller owns the transaction.
    """
```

- Move the lines query, snapshot build (including per-line `taxes`), and `next_version_no` computation from `_create_quote_version_impl` into it verbatim.
- `_create_quote_version_impl` keeps its existing signature and outer behavior (tenant check as-is — the `db.get()` at line 596 is out of scope), then delegates: `version = _insert_quote_version(quote, db, create_in.presentation_style)`, then `db.commit()` + `db.refresh(version)` + `return version` — exactly as today.
- The 3 existing call sites (test endpoint ~1187, authenticated versions endpoint ~1703, apply-discount ~2467) must require **zero changes**.

**Intermediate check**: `pytest -m unit --tb=short -q 2>&1 | tail -5` — must match the baseline exactly (pure refactor, no behavior change).

---

## Task 2 — `_create_quote_impl` creates v1 atomically

Replace the bare commit at the end of `_create_quote_impl` (currently lines 175–178):

```python
    db.add(quote)
    db.flush()                          # quote.id available; lines query returns []
    _insert_quote_version(quote, db)    # v1, is_active=True, SAME transaction
    db.commit()
    db.refresh(quote)
    return quote
```

- Single transaction — no two-commit crash window (design §G Q2).
- The returned object and response contract are unchanged (`Quote` → `QuoteResponse`) — **no OpenAPI delta**.
- `set_audit_context_sync()` is already called by the authenticated endpoint before this impl — verify in your reads; do NOT add a second call. The v1 insert inherits the same audit actor context.
- Idempotency replay-safety: the existing `Idempotency-Key` flow short-circuits replays before the impl re-executes — no double v1 (design §E).

**Intermediate check**: `pytest -m unit --tb=short -q 2>&1 | tail -5` — new tests from Task 4 will fail until written; at this point the EXISTING suite must still pass (start watching for version-collision fallout per design §G Q3 — fix any by using the auto v1 or hand-building v2).

---

## Task 3 — Backfill migration `plp_fix_3_backfill_quote_version_v1`

```bash
alembic revision -m "plp_fix_3_backfill_quote_version_v1"   # blank — never --autogenerate
```

Set `down_revision` to the head from MCP query 4. Implement exactly per design §B.2:

- `upgrade()`: `op.execute("SET LOCAL session_replication_role = 'replica';")` then the single idempotent `INSERT … SELECT` from design §B.2 — quotes with **no active version**, `version_no = COALESCE(max,0)+1`, snapshot = `jsonb_build_object('quote', to_jsonb(q), 'lines', COALESCE(agg with '{"taxes": []}' per line, '[]'), 'source', 'plp_fix_3_backfill')`, `is_active=true`, `presentation_style='clean'`, `created_by=NULL`.
- `downgrade()`: `SET LOCAL … 'replica';` then `DELETE FROM public.quote_version WHERE snapshot->>'source' = 'plp_fix_3_backfill';` — exact reverse, surgical via the marker key.

**Scratch-DB proof (design §B.3 — mandatory)**: run the full cycle —

```bash
alembic upgrade head && alembic downgrade -1 && alembic upgrade head && alembic current
```

Then the functional proof: via SQL on the scratch/dev DB, insert a bare versionless quote (mimic Tom's prod case), `alembic upgrade head`, confirm an active v1 exists for it with `snapshot->>'source' = 'plp_fix_3_backfill'`; `alembic downgrade -1`, confirm removal; `alembic upgrade head` to finish at head. Document results in the Completion Summary. (If your local census from MCP query 3 was > 0, also record what the real upgrade healed.)

---

## Task 4 — Regression tests (real-endpoint path — the MSW-blindness antidote)

Create `backend/tests/domains/sales_quoting/test_plp_fix_3_quote_version_at_create.py`:

```python
pytestmark = [
    pytest.mark.domain_sales_quoting,
    pytest.mark.unit,
]
```

| # | Test | Verifies |
|---|---|---|
| 1 | `test_create_quote_creates_active_v1` | `POST /api/v1/quotes/test` → 201; via `db_session`, exactly one `quote_version` for the new quote: `version_no=1`, `is_active=True`, snapshot has `quote` + `lines` keys, `lines == []` |
| 2 | `test_created_quote_viewable_via_detail` | **Issue 6 regression** — `POST /api/v1/quotes/test` (NO hand-built version) → `GET /api/v1/quotes/{id}/detail/test` → 200; `quote_version_id` == the auto v1 id |
| 3 | `test_explicit_version_after_create_is_v2` | `POST /api/v1/quotes/test` → `POST /api/v1/quotes/{id}/versions/test` → 201 with `version_no=2`; detail now returns the v2 id (latest-active rule, design §G Q5) |
| 4 | `test_create_quote_line_then_detail_shows_line` | `POST /quotes/test` → `POST /{id}/lines/test` with a real `qco_line_type_id` (query by `code` via `db_session`, never hardcoded — see `test_plp_fix2_qco_line_types.py` for the pattern) → `GET /{id}/detail/test` → 200 with the line in `line_items` |

Rules: `client` fixture only (no module-level `TestClient`); `test_tenant`/`test_customer`/`test_site` fixtures (no hardcoded UUIDs); assertions scoped by inserted IDs (never row counts); Test Resilience Rule applies (shared seeded DB). Do NOT use or modify the `test_quote_version` conftest fixture.

After writing: `pytest tests/domains/sales_quoting/test_plp_fix_3_quote_version_at_create.py -v 2>&1 | tail -12` — all 4 pass; then `pytest -m unit --tb=short -q 2>&1 | tail -5`.

---

## Task 5 — Suite repairs + regeneration

1. **Collision fallout**: run the full unit suite; any test that HTTP-creates a quote AND hand-builds a v1 for it will now violate `uq_quote_version_quote_id_version_no` (design §G Q3 found none, the suite is the arbiter). Fix by using the auto-created v1 or hand-building v2 — per-test judgment, minimal diff.
2. **Import map** (new test file added):
   ```bash
   python generate_app_import_map.py tests > app_model_imports.md
   ```
3. **N/A this batch** (state each explicitly in the Completion Summary): `generate_db_model_map.py` (no model change), `schema_manager.py` (no schema change), `export_openapi_json.py` (no contract change).

---

## Seed Data Rollout (Core + Scenario)

Per Rule 11.5 / inclusions §20 — this batch adds DB data via the backfill migration:

- **Layer 1 (core/platform)**: N/A — no lookup/reference rows added.
- **Layer 2 (scenario)**: N/A — verified at design time: `seed_scenario_quote_to_cash.py` (line 1346, comment *"quote_version (required by /detail endpoint)"*, and the second site at 1583) already creates v1 per seeded quote. No seed-script change; the migration is the healer for user-created versionless quotes (prod).
- **Verification**: MCP query 3 census before/after the migration on dev (record both numbers); `pytest -m unit` green after migration.
- **README update**: `README-seed-data.md` §4 needs NO change (no seed-model change) — state this verification explicitly in your Completion Summary instead of editing the README.

---

## Final Verification

### Phase 1 — Unit Tests Only (during development)

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

### Phase 2 — Lint (changed files only) + Full Suite, Vendor-Deselected (once, at the end)

```bash
cd <repo>/backend
source .venv/bin/activate

CHANGED_PY=$(git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||')
if [ -n "$CHANGED_PY" ]; then
    ruff check --fix $CHANGED_PY
    ruff format $CHANGED_PY
    ruff check $CHANGED_PY
fi

python -m pytest -m "not integration and not requires_telnyx and not requires_stripe and not requires_sendgrid and not requires_redis and not e2e" --tb=short -q 2>&1 | tail -15

# Batch-specific spot checks
python -m pytest tests/domains/sales_quoting/ -v 2>&1 | tail -25

echo "=== PLP-FIX-3 FINAL VERIFICATION COMPLETE ==="
```

**Vendor-suite inclusion call**: N/A — this batch touches no Telnyx/Stripe/SendGrid/Redis-covered code. Stated explicitly per the Phase 2 rule.

> Any failure in either phase must be fixed before the batch is declared done. If you cannot identify the root cause → STOP and ask Tom.

---

## Definition of Done — PLP-FIX-3

Check off each item **in this prompt doc** as it completes:

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting (or confirmed with Tom)
- [ ] All 5 MCP pre-work queries run — `quote_version` columns re-verified; `uq_quote_version_quote_id_version_no` confirmed; versionless census recorded; alembic head recorded (every touched table verified via `information_schema.columns`, rules §25)
- [ ] All mandatory source files read before writing any code (including `api/schemas/quotes.py`)
- [ ] **Task 1**: `_insert_quote_version()` extracted (no-commit inner); `_create_quote_version_impl` delegates; 3 call sites untouched; suite still green
- [ ] **Task 2**: `_create_quote_impl` creates v1 in the same transaction (`flush` → insert → single `commit`); response contract unchanged
- [ ] **Task 3**: blank migration with `down_revision` = recorded head; `SET LOCAL session_replication_role = 'replica'` in BOTH upgrade and downgrade; INSERT matches design §B.2 exactly (marker key `'source': 'plp_fix_3_backfill'`); downgrade is the surgical marker-key DELETE; scratch-DB cycle + functional proof documented
- [ ] **Task 4**: 4 new tests in `tests/domains/sales_quoting/test_plp_fix_3_quote_version_at_create.py` — all pass; real-endpoint path only (no hand-built versions); `qco_line_type_id` queried by code, never hardcoded
- [ ] **Task 5**: collision fallout repaired (Rule 11); `generate_app_import_map.py tests > app_model_imports.md` run; the 3 N/A regeneration steps stated in the Completion Summary
- [ ] All DB-touching code is sync `def` (rules §21); Pydantic v2 idioms only; no new `db.get()` introduced
- [ ] All new tests use `pytestmark` (domain + unit), `client` fixture, `test_tenant`-family fixtures, ID-scoped assertions
- [ ] `ruff check --fix && ruff format` on changed files only — zero remaining issues, no unjustified `# noqa` (rules §23)
- [ ] **Phase 1**: all unit tests pass — zero failures including any pre-existing
- [ ] **Phase 2**: full vendor-deselected suite passes — zero failures, warning-clean; vendor inclusion call = N/A stated
- [ ] Final test count (before → after) documented
- [ ] Completion Summary filled in at this prompt doc's ending `## Appendix — Completion Summary` (ADR-0017 — never the launch plan)

---

## Completion Summary

After all Definition of Done items are complete:

1. Fill in the **Completion Summary** in the appendix below using the exact format.
2. This batch closes no task tracked in another source spec (the bug report is an analysis doc, not a tracker) — no external spec headers to flip.
3. **Deploy note for Tom in your final message**: the deploy runs the backfill migration automatically (`alembic upgrade head` in the deploy pipeline) — Tom's versionless prod test quote self-heals at deploy; no manual SQL. Verify post-deploy: create a quote on prod → open it → detail renders.

```markdown
### PLP-FIX-3 — Quote v1-at-Create + Versionless Backfill: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X+N passed, Y failed (+N new tests)

#### What Was Accomplished
- [changes + root-cause note]

#### Files Changed / Created
| File | Action |
|---|---|

#### Tests Added
| Test File | Domain | Tests | All Pass |
|---|---|---|---|

#### Migration Proof
- [scratch-DB cycle + functional proof results; versionless census before/after]
```

---

## After This Task — Next Step

PLP-FIX-3 is standalone (no FE companion; no OpenAPI delta; `pnpm sync-api-types` not needed). On close: notify Tom — he deploys (migration included) and re-verifies prod Issue 6 (create → view quote) plus re-checks Issue 13a after the pending PLP-FIX-2 deploy. Next planned batches per the triage: PLP-FIX-4 (React: Issues 7+10+11), Issue 9 debug session, PLP-FIX-5 (mixed: 8+12+13b).

---

## Appendix — Completion Summary

### PLP-FIX-3 — Quote v1-at-Create + Versionless Backfill: Completion Summary

**Completed**: 2026-09-02
**Mode**: Pilot Python Engineer
**Baseline**: 4751 passed, 1 skipped
**Final**: 4755 passed, 1 skipped (+4 new tests)

#### What Was Accomplished

- **Root cause fixed**: `_create_quote_impl()` never created a `quote_version` row, but `get_quote_detail()` hard-requires an active version and 404s otherwise — so every builder-created draft quote was unviewable (prod Issue 6: "Failed to load quote / 404"). This batch enforces the invariant "every quote has an active v1 from creation" at the write source.
- **Task 1**: Extracted `_insert_quote_version()` as a no-commit inner function (db.add + db.flush ONLY, caller owns the transaction). `_create_quote_version_impl()` delegates to it, preserving its existing signature and outer behavior (tenant check as-is — the pre-existing `db.get()` at the tenant-check line is out of scope per design). The 3 existing call sites (test endpoint, authenticated versions endpoint, apply-discount) required zero changes.
- **Task 2**: `_create_quote_impl()` now creates v1 atomically in the same transaction: `db.add(quote)` → `db.flush()` (quote.id available; lines query returns []) → `_insert_quote_version(quote, db)` (v1, is_active=True) → single `db.commit()`. No two-commit crash window (design §G Q2). Response contract unchanged (`Quote` → `QuoteResponse`) — no OpenAPI delta. `set_audit_context_sync()` is already called by the authenticated endpoint before this impl; the v1 insert inherits the same audit actor context (no second call added).
- **Task 3**: Blank data migration `plp_fix_3_backfill_quote_version_v1` (`ec2df153a859`, down_revision `c8d06a6ffdd2`). `upgrade()` begins with `SET LOCAL session_replication_role = 'replica'` then a single idempotent `INSERT ... SELECT` that heals quotes with no active version (`version_no = COALESCE(max,0)+1`, snapshot includes `'source': 'plp_fix_3_backfill'` marker key, `is_active=true`, `presentation_style='clean'`, `created_by=NULL`). `downgrade()` is the surgical marker-key `DELETE FROM public.quote_version WHERE snapshot->>'source' = 'plp_fix_3_backfill'`. Fixed a latent bug in the design SQL: the `quote_line` subquery referenced `to_jsonb(ql)` without aliasing the table — added `FROM public.quote_line ql`.
- **Task 4**: 4 regression tests in `test_plp_fix_3_quote_version_at_create.py` — real-endpoint path only (no hand-built versions), `qco_line_type_id` queried by code (never hardcoded), `client` fixture only, `test_tenant`-family fixtures, ID-scoped assertions.
- **Task 5**: 2 collision fallout tests repaired (design §G Q3 anticipated): `test_quote_versioning` (explicit version POST now yields v2, not v1) and `test_complete_acceptance_flow` (hand-built version bumped to `version_no=2` to avoid `uq_quote_version_quote_id_version_no` collision with the auto v1). Import map regenerated. 16 pre-existing RUF059 ruff errors in the 2 touched test files fixed via `--unsafe-fixes` (unused unpacked vars prefixed with `_`).

#### Files Changed / Created
| File | Action |
|---|---|
| `backend/api/routes/quotes.py` | Modified — extracted `_insert_quote_version()`; `_create_quote_impl` now creates v1 atomically; `_create_quote_version_impl` delegates |
| `backend/migrations/versions/2026_09_02_1417-ec2df153a859_plp_fix_3_backfill_quote_version_v1.py` | Created — backfill migration (upgrade + downgrade) |
| `backend/tests/domains/sales_quoting/test_plp_fix_3_quote_version_at_create.py` | Created — 4 regression tests |
| `backend/tests/test_quotes.py` | Modified — `test_quote_versioning` asserts v2 (collision fallout); RUF059 fixes |
| `backend/tests/test_quote_acceptance.py` | Modified — `test_complete_acceptance_flow` hand-built version bumped to v2; RUF059 fixes |
| `backend/app_model_imports.md` | Regenerated — new test file added |

#### Tests Added
| Test File | Domain | Tests | All Pass |
|---|---|---|---|
| `test_plp_fix_3_quote_version_at_create.py` | sales_quoting | 4 | ✅ |

| # | Test | Verifies |
|---|---|---|
| 1 | `test_create_quote_creates_active_v1` | POST /quotes/test → exactly one active v1; snapshot has quote + lines (== []) |
| 2 | `test_created_quote_viewable_via_detail` | Issue 6 regression — created quote viewable via /detail; quote_version_id == auto v1 |
| 3 | `test_explicit_version_after_create_is_v2` | Explicit version POST yields v2; detail returns v2 id (latest-active rule) |
| 4 | `test_create_quote_line_then_detail_shows_line` | Create → add real line → detail shows line in line_items |

#### Migration Proof

- **Scratch-DB cycle**: `alembic upgrade head` → `alembic downgrade -1` → `alembic upgrade head` → `alembic current` = `ec2df153a859 (head)` ✅
- **Functional proof**: Inserted a bare versionless quote via raw SQL (bypassing the app, `quote_number='QUO-PROOF-999999'`) → 0 versions before upgrade → `alembic upgrade head` → exactly 1 active v1 with `snapshot->>'source' = 'plp_fix_3_backfill'` ✅ → `alembic downgrade -1` → 0 versions (marker-key DELETE removed it) ✅ → cleaned up bare quote → `alembic upgrade head` to finish at head.
- **Versionless census (MCP query 3)**: before = 0 (local dev; seeds comply). After upgrade = 0 (nothing to heal locally). Prod has ≥1 (Tom's test quote) — the deploy migration heals it automatically.

#### Regeneration Status (N/A steps stated)
- `generate_db_model_map.py`: N/A — no model file changed.
- `schema_manager.py`: N/A — no schema JSON change (pure data migration).
- `export_openapi_json.py`: N/A — no API contract change (v1 creation is an internal side effect; `POST /quotes` returns the same `QuoteResponse`).

#### Seed Data Rollout
- Layer 1 (core/platform): N/A — no lookup/reference rows.
- Layer 2 (scenario): N/A — `seed_scenario_quote_to_cash.py` already creates v1 per seeded quote. No seed-script change; the migration is the healer for user-created versionless quotes (prod). `README-seed-data.md` §4 unchanged (no seed-model change).

#### Vendor-Suite Inclusion Call
N/A — this batch touches no Telnyx/Stripe/SendGrid/Redis-covered code.

#### Deploy Note for Tom
This batch includes a data migration (`ec2df153a859` — backfill versionless quotes). Per your manual deploy workflow (`aws-ops-runbook.md` §9.2): **run the migration BEFORE the app redeploy** — SSH tunnel to prod RDS → `cd backend && .venv/bin/alembic upgrade head` → verify `alembic current` shows `ec2df153a859` → then force the new ECS deployment. The migration is idempotent and safe to re-run; it heals Tom's versionless prod test quote (and any other versionless quotes) with an active v1 carrying the `plp_fix_3_backfill` marker key. No manual SQL needed beyond the standard `alembic upgrade head`. Verify post-deploy: create a quote on prod → open it → detail renders.
