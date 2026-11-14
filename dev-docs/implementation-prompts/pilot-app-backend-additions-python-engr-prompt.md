# Batch Implementation Prompt — Pilot Python Engineer Mode

**Usage**: After the Architect design doc is complete, open a new chat in `🚀 Pilot Python Engineer` mode. Replace `{N}` and `{Batch Name}` with the target batch. Paste this prompt verbatim.

**Prerequisite**: The design doc must exist at `dev-docs/architecture-design/batch-designs/batch-b{N}-design.md` before starting. Do not begin implementation with an incomplete or missing design doc.

---

```
Implement Batch B{N} — {Batch Name}.

Read the design doc in full before writing any code:
dev-docs/architecture-design/batch-designs/batch-b{N}-design.md

> ⚠️ **LEDGER NOTE — applies to remediation / schema-fix batches only** (e.g. B13b, any future "fix" batch):
> The standard batch workflow references the additions ledger (`frontend-backend-mvp-additions-latest.md`) as the authoritative detail source. For remediation batches that have **no A-series entries in the ledger**, Section A of the design doc IS the authoritative source. Do not attempt to look up A-numbers in the ledger for these batches — all migration code, column names, types, and trigger specifications are fully specified in §A of the design doc. The ledger step is N/A for this batch.

Also read the §16 Standard Task Workflow, as well as all of the sections, from this doc to make sure you adhere to all content included:
dev-docs/architecture-design/pilot-python-engineer-methods.md

Execute each item in the execution order defined in Section B of the design doc.
For each item, follow the §16 Standard Task Workflow exactly — do not skip or reorder steps.
For each item, follow the methods and constraints included in the pilot-python-engineer-methods.md file by topic.

─────────────────────────────────────────
LOOP — REPEAT FOR EACH ITEM IN ORDER
─────────────────────────────────────────

PRE-WORK: Regression baseline
  - Run the full test suite:
    - cd backend && source .venv/bin/activate && pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
  - Record the pass/fail/warning count before touching any code
  - Do not proceed if existing tests are failing (fix regressions first)

STEP 1: ORM model updates
  - Consult backend/db_models_map.md to find the correct model file before editing
  - Do not add new models to the wrong file
  - Follow mixin and field conventions from backend/app/models/mixins.py

STEP 2: Manual Alembic migration — NO --autogenerate
  - Create a blank revision only: alembic revision -m "phase_fe_1_batch_b{N}_{short_description}"
  - Write the upgrade() and downgrade() SQL manually
  - Migration naming: phase_fe_1_batch_b{N}_{short_description}
  - Triple-verify every migration before proceeding:
      alembic upgrade head
      alembic downgrade -1
      alembic upgrade head
  - All three commands must succeed cleanly. Any failure stops work on this item.

STEP 3: Master Blueprint Sync
  - Update dev-docs/db-design/pilot-db-schema-v2.6h.json to reflect the migration
  - Ask **Tom** to create backup of schema, then run schema_diff.py, then view schema_diff_report.html and report back
  - ZERO discrepancies required — do not proceed to Step 4 if any discrepancy exists

STEP 4: API + Service layer implementation
  - Follow patterns from Section D and E of the design doc exactly
  - Use real import paths from backend/app_model_import.md
  - Do not invent new patterns — call shared utilities established in this batch or prior batches per §1.5

STEP 5: Tests
  - Create test file(s) in tests/batch_b{N}/
  - Cover every test focus case listed in the design doc for this item
  - Run: pytest tests/batch_b{N}/ -v
  - If passes, with no warnings, run full regression:
    - cd backend && source .venv/bin/activate && pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
  - Both must pass with no warnings before marking this item complete

DEFINITION OF DONE (§16.5) — check all before moving to next item:
  [ ] ORM model changes committed
  [ ] Migration triple-verified (upgrade → downgrade -1 → upgrade all pass)
  [ ] Schema diff = ZERO
  [ ] API/service implementation complete and wired into the app
  [ ] All test focus cases covered in tests/batch_b{N}/
  [ ] Full regression suite passes with no new failures

─────────────────────────────────────────
AFTER ALL ITEMS COMPLETE — BATCH GATE
─────────────────────────────────────────

1. Run the full test suite one final time, confirm zero failures, zero regressions
2. Confirm accumulated batch schema diff = ZERO across all migrations in this batch
3. Update the main table in §7 Batch Completion Tracker in the `dev-docs/analysis/pilot-app-mvp-backend-impl-plan.md` file
3. Then create a new sub-section under §7 Batch Completion Tracker in the `dev-docs/analysis/pilot-app-mvp-backend-impl-plan.md` file
4. In this new sub-section for this Batch{N}, follow Batch 1 thru 7b format and insert the following information:
   - Migration names used (one per item, in order)
   - Test file paths created under tests/batch_b{N}/
   - Any decisions that deviated from the design doc and the reason why

Do not skip the triple-verify step on any migration.
Do not proceed to the next item if the schema diff is non-zero.
Do not use --autogenerate on any migration.
Do not mark the batch complete without the full regression suite passing.
```
