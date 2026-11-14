# Implementation Prompt: SEED-FIX-1 — seed_core.py Ownership of Migration-Embedded Seed Rows

**Mode**: Pilot Python Engineer
**Batch**: SEED-FIX-1
**Source plan**: Prod DB sync session 2026-08-09 (Architect-led prod seed validation)
**Design doc**: none — this prompt is self-contained
**Estimated session**: 1–2 hours
**Platform**: Backend only (`backend/migrations/scripts/`, `backend/README-seed-data.md`)

---

## ⚠️ MANDATORY STOP: Read These First

Before writing a single line of code, read:

- **`.roo/rules-pilot-python-engineer/python-engineer-rules.md`** — full document; the 25 hard rules are non-negotiable STOPs
- **`dev-docs/architecture-design/pilot-python-engineer-methods.md`** — §16 (Standard Task Workflow)
- **`backend/README-seed-data.md`** — §3 (Group A–D model), §4 (Current Seed State), §6 (run order), §7 (DELETE safety rule)

Critical rules for this batch:

- **Rule 1**: Never guess column names, data types, or table names. Use `postgres-local` MCP to verify every name before use. If MCP returns an error → **STOP and ask Tom**.
- **Rule 7**: The `postgres-local` MCP is for **read-only verification only**. Never use it to INSERT, UPDATE, or DELETE data — all data changes go through seed scripts or migrations.
- **Rule 11**: If ANY test fails during your work — even one that appears pre-existing — you must fix it before declaring the batch done.
- **Rule 16 (verify, don't assume)**: 186 tables exist. Query `information_schema.columns` for every table you touch this session before writing SQL.
- **Seed DELETE safety (README §7 / Architect rule §11.1)**: any DELETE in `mode_seed` must be value-scoped, never channel-scoped or key-partial.
- **This batch adds NO migration.** It adds rows to `seed_core.py` only. Do not create an Alembic revision.

---

## Background / Context

During the 2026-08-09 prod DB sync, the Architect discovered that prod (built via schema-only `pg_dump` restore + `alembic stamp`, runbook §9.5) was missing 4 platform seed rows. Root cause: two July migrations embedded seed INSERTs that `seed_core.py` never took ownership of, so the seed-script recovery path could not restore them:

1. Migration `f7f30492c3e4` (B20) — 3 `platform_setting_catalog` keys + 3 `platform_setting` system defaults
2. Migration `b1bd90914b77` (B21) — `communication_template` `recurring_job_scheduled` / **email** variant (the SMS variant IS already in `seed_core.py` ~line 1142)

`seed_core.py` is the single source of truth for Group A platform data. This batch closes that ownership gap and corrects stale counts in README-seed-data §4.

---

## Pre-Work: Establish Regression Baseline

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=no -q 2>&1 | tail -5
```

Record the exact count: **`X passed, Y failed`**. If any tests are already failing before you start, do NOT proceed — confirm with Tom first.

---

## Pre-Work: Run MCP Verification Queries

Run **all** of these via `postgres-local` MCP before writing any code. If any query returns unexpected results → **STOP and ask Tom**.

> **MCP Usage Rule**: The `postgres-local` MCP is for **read-only verification only**. Never use it to INSERT, UPDATE, or DELETE. If a query fails → STOP and ask Tom.

```sql
-- 1. Confirm the 3 catalog keys exist in dev (expected: 3 rows)
SELECT key, value_type, category, sort_order, is_active
FROM public.platform_setting_catalog
WHERE key IN ('square_integration_enabled', 'default_payment_terms', 'default_billing_mode')
ORDER BY key;

-- 2. Confirm the 3 system defaults exist in dev (expected: 3 rows, tenant_id NULL)
SELECT key, value FROM public.platform_setting
WHERE key IN ('square_integration_enabled', 'default_payment_terms', 'default_billing_mode')
  AND tenant_id IS NULL
ORDER BY key;

-- 3. Confirm the recurring_job_scheduled email template exists in dev
--    (expected: 2 rows — sms + email; capture the email subject/body verbatim)
SELECT channel, subject, body_template, is_active
FROM public.communication_template
WHERE template_code = 'recurring_job_scheduled' AND tenant_id IS NULL
ORDER BY channel;

-- 4. Full column list of both target tables (verify before writing INSERTs)
SELECT table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('platform_setting_catalog', 'platform_setting', 'communication_template')
ORDER BY table_name, ordinal_position;
```

---

## Pre-Work: Read These Source Files

Read with `read_file` before writing any code:

- `backend/migrations/scripts/seed_core.py` — in particular the `COMMUNICATION_TEMPLATES` list (~line 1142, SMS `recurring_job_scheduled` entry), wherever `platform_setting_catalog` / `platform_setting` rows are seeded, and the `seed` / `show` / `inspect` mode wiring
- `backend/migrations/versions/2026_07_11_2036-f7f30492c3e4_b20_add_invoice_platform_settings.py` — source of truth for the 3 settings rows
- `backend/migrations/versions/2026_07_12_1645-b1bd90914b77_b21_seed_recurring_job_scheduled_.py` — source of truth for the email template row

---

## Task 1 — Add 3 platform_setting_catalog keys + 3 platform_setting defaults to seed_core.py

Add seed coverage matching migration `f7f30492c3e4` **exactly** (values must be identical — `seed_core.py` is the post-schema-restore recovery path):

**`platform_setting_catalog`** (PK `key` → `ON CONFLICT (key) DO NOTHING` is safe):

| key | label | description | value_type | tenant_editable | allows_user_override | allowed_values | category | is_active | sort_order |
|---|---|---|---|---|---|---|---|---|---|
| `square_integration_enabled` | Square payment integration enabled | When enabled, tenants can require card-on-file via Square before work begins. | boolean | true | false | *(none)* | billing | true | 100 |
| `default_payment_terms` | Default invoice payment terms | When invoice.payment_terms is NULL, the invoice builder pre-selects this value. | string | true | false | `["due_on_receipt","net_15","net_30","custom_date"]` (jsonb) | billing | true | 101 |
| `default_billing_mode` | Default invoice billing mode | When the invoice builder opens a blank invoice, this is the default tab selection. | string | true | false | `["line_item","progress"]` (jsonb) | billing | true | 102 |

**`platform_setting`** system defaults (`tenant_id = NULL`). **Caution**: the `(key, tenant_id)` unique constraint does NOT match `NULL = NULL` in PostgreSQL — use the `WHERE NOT EXISTS (... AND tenant_id IS NULL)` guard pattern (same as the migration), not `ON CONFLICT`:

| key | value (jsonb) |
|---|---|
| `square_integration_enabled` | `false` |
| `default_payment_terms` | `"due_on_receipt"` |
| `default_billing_mode` | `"line_item"` |

Match how `seed_core.py` already structures these tables (dict lists + loop, or raw SQL block — follow the existing convention in the file). Ensure the rows appear in `seed`, `show`, and `inspect` modes per the script's existing architecture.

## Task 2 — Add recurring_job_scheduled email template to seed_core.py

Add to the `COMMUNICATION_TEMPLATES` list (next to the existing SMS entry at ~line 1142), matching migration `b1bd90914b77` verbatim:

- `template_code`: `recurring_job_scheduled`
- `channel`: `email`
- `subject`: `Your {{service_description}} is scheduled`
- `body_template`:
  ```
  Hi {{customer_name}},

  Your scheduled {{service_description}} with {{company_name}} is confirmed.

  Date: {{scheduled_date}}
  Time: {{scheduled_time}}
  Address: {{site_address}}

  If you need to reschedule, please contact us at {{company_phone}}.

  Thank you,
  {{company_name}}
  ```

Verify against MCP query 3 output — the dev DB row is authoritative; if the dict structure in `seed_core.py` needs an insert-guard for `(template_code, channel, tenant_id IS NULL)` (no unique constraint on that table — see the migration's docstring), follow the migration's `WHERE NOT EXISTS` pattern or the file's existing dedup approach, keeping `mode_seed` idempotent and value-scoped (README §7).

## Task 3 — Verify seed script end-to-end on dev

```bash
cd <repo>/backend
source .venv/bin/activate
python migrations/scripts/seed_core.py --mode inspect   # all rows present, no diffs
python migrations/scripts/seed_core.py                  # idempotent re-run — no dupes, no errors
python migrations/scripts/seed_core.py --mode inspect   # still clean after re-run
```

Then confirm via `postgres-local` MCP that counts are unchanged (48 catalog / 48 NULL-tenant settings + 1 tenant row / 17 comm templates) and no duplicate rows were created.

## Task 4 — Update README-seed-data.md §4 stale counts

Fix these drifted rows in `backend/README-seed-data.md` §4 (Current Seed State), verified via MCP on 2026-08-09:

| Table | README says | Actual (dev, verified) |
|---|---|---|
| `notification_type` | 9 | **10** (c_b6 added `free_period_warning`) |
| `notification_template` | 27 | **30** (10 types × 3 channels) |
| `entity_type` | 6 | **7** |
| `platform_setting_catalog` | 48 | 48 — confirm row content list includes the 3 B20 keys |
| `communication_template` | 17 | 17 — note now fully owned by `seed_core.py` (sms + email variants) |

Also add a one-line note to the `platform_setting_catalog`/`platform_setting` rows that the 3 B20 invoice-builder keys are seed_core-owned (closing the migration-embedded seed gap found in the 2026-08-09 prod sync).

---

## Final Verification

### Phase 1 — Unit Tests Only

```bash
cd <repo>/backend
source .venv/bin/activate
python -m pytest -m unit --tb=short -q 2>&1 | tail -10
```

All unit tests must pass. A new seed row a test doesn't expect may break count-based assertions — fix seed-resilience failures by asserting by ID/business key, never by count (README §7 "shared DB" rule).

### Phase 2 — Lint (changed files only) + Full Suite

```bash
cd <repo>/backend
source .venv/bin/activate

CHANGED_PY=$(git diff --name-only --diff-filter=d HEAD -- '*.py' | sed 's|^backend/||')
if [ -n "$CHANGED_PY" ]; then
    ruff check --fix $CHANGED_PY
    ruff format $CHANGED_PY
    ruff check $CHANGED_PY
fi

python -m pytest --tb=short -q 2>&1 | tail -10
echo "=== SEED-FIX-1 FINAL VERIFICATION COMPLETE ==="
```

> **Do NOT run `ruff check .` against the whole codebase** — changed files only (rules §23). Any failure in either phase must be fixed before declaring done; if you cannot identify a root cause → STOP and ask Tom.

---

## Definition of Done

- [ ] Pre-modification regression baseline captured (`X passed, Y failed`) using `pytest -m unit`
- [ ] Zero pre-existing unit failures confirmed before starting work (or confirmed with Tom)
- [ ] All 4 MCP pre-work queries run — dev rows confirmed for all 4 gap items; column lists verified via `information_schema.columns` (rules §25)
- [ ] All mandatory source files read before writing any code
- [ ] Task 1: 3 catalog keys + 3 system defaults added to `seed_core.py`, values identical to migration `f7f30492c3e4`, NULL-tenant `WHERE NOT EXISTS` guard used for `platform_setting`
- [ ] Task 2: `recurring_job_scheduled`/email template added to `seed_core.py`, verbatim from migration `b1bd90914b77`
- [ ] Task 3: `seed_core.py --mode inspect` clean before AND after an idempotent re-run; MCP re-count confirms no duplicates
- [ ] Task 4: README-seed-data §4 counts corrected (notification_type 10, notification_template 30, entity_type 7) + ownership note added
- [ ] No Alembic migration created (this batch touches seed scripts + README only)
- [ ] `ruff check --fix && ruff format` run on changed files only — zero remaining issues (rules §23)
- [ ] **Phase 1**: All unit tests pass (`pytest -m unit`) — zero failures
- [ ] **Phase 2**: Full test suite passes (`pytest`) — zero failures, warning-clean
- [ ] Final test count (before → after) documented
- [ ] Completion Summary provided (format below)

---

## Completion Summary

Report back in this exact format:

```markdown
### SEED-FIX-1 — seed_core.py ownership of migration-embedded seed rows: Completion Summary

**Completed**: YYYY-MM-DD
**Mode**: Pilot Python Engineer
**Baseline**: X passed, Y failed
**Final**: X passed, Y failed (delta)

#### What Was Accomplished
- ...

#### Files Changed
| File | Action |
|---|---|
| `backend/migrations/scripts/seed_core.py` | Updated — ... |
| `backend/README-seed-data.md` | Updated — §4 counts ... |

#### MCP Verification Evidence
- [counts before/after for the 4 affected tables]
```

---

## Handoff (for Tom / Architect)

After this batch closes, Tom will run the updated `seed_core.py` + `seed_platform.py` against **prod** via the SSH tunnel (port 5433) to close the prod seed gaps, and the Architect will re-verify prod counts via `postgres-prod` MCP. The one-off SQL hotfix script (`admin-tools/fix_prod_seed_gaps_2026-08-09.sql`) is then **discarded** — superseded by this batch.
