# Task: Fix Module-Level TestClient DB Accumulation in Batch 1E Test Files

**Mode**: Pilot QA Python Engineer
**Priority**: High — must be fixed before dev DB can be purged for UI testing
**Estimated effort**: Small (pure fixture wiring refactor, no logic changes)

---

## Background & Context

Two legacy test files in `backend/tests/batch_1e/` use a module-level `TestClient(app)` instead of the conftest `client` fixture. This bypasses the transaction rollback mechanism, causing every API call in those tests to permanently commit to the `pilot_dev` database. As of May 31, 2026, this has accumulated **7,850 orphaned customer, site, and job stub records** in the dev database, rendering it unsuitable for UI testing.

### The root cause

The `conftest.py` `client` fixture wraps every test in a transaction that is rolled back after each test. A module-level `TestClient(app)` has no such wiring — it uses FastAPI's real `get_db` dependency which commits to the database permanently.

**Full technical explanation**: See `backend/tests/README-adding-tests.md` — section "The Module-Level TestClient Anti-Pattern". **Read this section thoroughly before proceeding.** It explains the exact mechanism, why the tests still pass despite the accumulation, and shows the correct fix pattern.

### The two affected files

1. `backend/tests/batch_1e/test_task_1b2_job_assignment_scheduling.py`
   - Line 28: `client = TestClient(app)` — module-level
   - Helper function `_create_test_job()` calls `/api/v1/customers/test`, `/api/v1/sites/test`, `/api/v1/jobs/test` via this module-level client
   - Every test method calls `_create_test_job()` once → 3 permanent DB rows per test per run

2. `backend/tests/batch_1e/test_task_1b4_conflict_detection.py`
   - Same pattern — module-level `client = TestClient(app)`
   - Helper function `_create_scheduled_assigned_job()` has the same accumulation behavior

---

## Your Task

Execute the following steps **in exact order**. Do not skip ahead. Use the postgres-local MCP server (available in Roo Code) to query the database directly at the verification steps — reference `dev-docs/db-design/postgres-mcp-guide.md` for query syntax.

---

### Step 1: Capture the Full Unit Test Baseline

Before touching any files, run the full unit test suite and record the results.

```bash
cd backend
source .venv/bin/activate
pytest -m unit -q 2>&1 | tee /tmp/baseline_unit_results.txt
tail -5 /tmp/baseline_unit_results.txt
```

Also capture the total collected test count:

```bash
pytest --co -q 2>/dev/null | tail -3
```

**Record and report:**
- Total tests collected
- Unit tests: passed / failed / errors
- Any pre-existing failures (these are NOT regressions — note them so you can distinguish them from regressions after your fix)

---

### Step 2: Run ONLY the Two Affected Test Files and Verify DB Accumulation

**Before running**, query the database to get baseline row counts:

Using the postgres-local MCP server, run:
```sql
SELECT COUNT(*) AS customer_count FROM public.customer 
WHERE display_name LIKE 'CC Customer%' OR display_name LIKE 'Sched Test Customer%';
```

```sql
SELECT COUNT(*) AS job_count FROM public.job;
```

```sql
SELECT COUNT(*) AS site_count FROM public.site;
```

Record these numbers as your **pre-run counts**.

Now run **only** the two affected test files:

```bash
cd backend
source .venv/bin/activate
pytest tests/batch_1e/test_task_1b2_job_assignment_scheduling.py tests/batch_1e/test_task_1b4_conflict_detection.py -v 2>&1 | tee /tmp/affected_tests_before.txt
tail -10 /tmp/affected_tests_before.txt
```

**After running**, re-query the database:
```sql
SELECT COUNT(*) AS customer_count FROM public.customer 
WHERE display_name LIKE 'CC Customer%' OR display_name LIKE 'Sched Test Customer%';
```

```sql
SELECT COUNT(*) AS job_count FROM public.job;
```

```sql
SELECT COUNT(*) AS site_count FROM public.site;
```

**You should see the row counts INCREASED.** This confirms the accumulation bug is present. Report the delta (how many rows were added by a single test run).

If the counts did NOT increase, stop and investigate — the bug may have already been partially fixed, or there is a different mechanism at play. Do not proceed until you understand the discrepancy.

---

### Step 3: Fix `test_task_1b2_job_assignment_scheduling.py`

**Read the file first**, understand the full structure, then apply these changes:

**Change 1: Remove the module-level client declaration**

Remove this line (approximately line 28):
```python
client = TestClient(app)
```

**Change 2: Update `_create_test_job()` to accept `client` as a parameter**

Change the function signature from:
```python
def _create_test_job() -> str:
```
to:
```python
def _create_test_job(client) -> str:
```

No other changes needed inside `_create_test_job()` — the body uses `client` already.

**Change 3: Update every test method that calls `_create_test_job()` to declare `client` in its signature**

Every test method that calls `_create_test_job()` must declare `client` (and/or `db_session`) as a fixture parameter so pytest injects the conftest fixture. Then pass it through to `_create_test_job(client)`.

Example — before:
```python
def test_patch_scheduled_times_returns_200(self):
    job_id = _create_test_job()
```

After:
```python
def test_patch_scheduled_times_returns_200(self, client):
    job_id = _create_test_job(client)
```

For tests that already declare `db_session` (e.g., `test_reassign_primary_soft_deletes_old`), add `client` alongside it:
```python
def test_reassign_primary_soft_deletes_old(self, client, db_session):
    job_id = _create_test_job(client)
```

Apply this change to **every test method** in the file that calls `_create_test_job()`. Do not miss any.

**Change 4: Add a module-level docstring note about the fix**

At the top of the file, in the existing module docstring, add a note:

```
Fix applied May 2026: Replaced module-level TestClient with conftest `client` fixture
to prevent permanent DB writes. See backend/tests/README-adding-tests.md §"The Module-Level
TestClient Anti-Pattern" for full explanation.
```

---

### Step 4: Fix `test_task_1b4_conflict_detection.py`

**Read the file first**, understand the full structure, then apply the same pattern:

**Change 1: Remove the module-level client declaration**

Find and remove the `client = TestClient(app)` line near the top.

**Change 2: Update `_create_scheduled_assigned_job()` to accept `client` as a parameter**

Find the helper function `_create_scheduled_assigned_job(...)` and add `client` as the first parameter.

**Change 3: Update every caller of `_create_scheduled_assigned_job()` to declare `client` in the test method signature and pass it through**

Same pattern as Step 3 — every test method that calls this helper must declare `client` as a fixture parameter and pass it as the first argument to the helper.

> **Important**: This file is larger (~540 lines). Read the full file before making changes. There may be multiple helper functions and multiple call sites. Find ALL of them — do not miss any.

**Change 4: Add the same docstring fix note** as in Step 3.

---

### Step 5: Run the Fixed Test Files and Verify NO DB Accumulation

**Before running**, query the database again:
```sql
SELECT COUNT(*) AS customer_count FROM public.customer 
WHERE display_name LIKE 'CC Customer%' OR display_name LIKE 'Sched Test Customer%';
```

Record the pre-run count.

Now run only the two fixed test files:

```bash
cd backend
source .venv/bin/activate
pytest tests/batch_1e/test_task_1b2_job_assignment_scheduling.py tests/batch_1e/test_task_1b4_conflict_detection.py -v 2>&1 | tee /tmp/affected_tests_after.txt
tail -10 /tmp/affected_tests_after.txt
```

**After running**, re-query:
```sql
SELECT COUNT(*) AS customer_count FROM public.customer 
WHERE display_name LIKE 'CC Customer%' OR display_name LIKE 'Sched Test Customer%';
```

```sql
SELECT COUNT(*) AS job_count FROM public.job;
```

**The counts must NOT change.** If they increased, the fix is incomplete — go back to Step 3/4 and find the missed call sites.

Also verify all tests still pass — the pass/fail count should match Step 2. If tests now fail, diagnose before proceeding.

---

### Step 6: Ask Tom to Purge the Orphaned Records

**Stop here and present Tom with a summary** before purging. The summary must include:

1. Confirmation that the fix is complete and verified (row counts stable after test run)
2. The exact SQL that will be used to purge the orphaned records — Tom must review and approve it before execution
3. A note that this is a **one-time cleanup** — after the fix, future test runs will not re-accumulate

The purge SQL to present for approval:

```sql
-- Preview: how many rows will be deleted
SELECT COUNT(*) FROM public.customer 
WHERE display_name LIKE 'CC Customer%' OR display_name LIKE 'Sched Test Customer%';

SELECT COUNT(*) FROM public.job j
WHERE j.customer_id IN (
  SELECT id FROM public.customer 
  WHERE display_name LIKE 'CC Customer%' OR display_name LIKE 'Sched Test Customer%'
);

SELECT COUNT(*) FROM public.site s
WHERE s.customer_id IN (
  SELECT id FROM public.customer 
  WHERE display_name LIKE 'CC Customer%' OR display_name LIKE 'Sched Test Customer%'
);
```

**Do NOT execute the DELETE/TRUNCATE yourself.** Present the SQL and ask Tom to:
1. Confirm the preview counts look correct
2. Approve the purge
3. Execute it (or ask you to execute it with his explicit approval)

---

### Step 7: Verify the Purge

After Tom approves and executes the purge, verify using the postgres-local MCP server:

```sql
SELECT COUNT(*) FROM public.customer 
WHERE display_name LIKE 'CC Customer%' OR display_name LIKE 'Sched Test Customer%';
-- Expected: 0

SELECT COUNT(*) FROM public.job;
-- Expected: significantly lower (or 0 if all jobs were test stubs)

SELECT COUNT(*) FROM public.site;
-- Expected: significantly lower (or 0 if all sites were test stubs)
```

Report the post-purge counts to confirm the cleanup is complete.

---

### Step 8: Run the Full Unit Test Regression

Run the full unit test suite again and compare against the Step 1 baseline:

```bash
cd backend
source .venv/bin/activate
pytest -m unit -q 2>&1 | tee /tmp/regression_unit_results.txt
tail -5 /tmp/regression_unit_results.txt
```

**Success criteria:**
- Total tests collected matches the Step 1 baseline (same number of tests)
- Pass count matches or exceeds the Step 1 baseline
- No new failures introduced by the fix (pre-existing failures from Step 1 are acceptable; new ones are not)

Report the full comparison:

| Metric | Baseline (Step 1) | After Fix (Step 8) | Delta |
|---|---|---|---|
| Tests collected | | | |
| Passed | | | |
| Failed | | | |
| Errors | | | |

If there are new failures, diagnose and fix them before completing this task.

---

## Completion Criteria

This task is complete when ALL of the following are true:

- [ ] `test_task_1b2_job_assignment_scheduling.py` uses the conftest `client` fixture (no module-level `TestClient`)
- [ ] `test_task_1b4_conflict_detection.py` uses the conftest `client` fixture (no module-level `TestClient`)
- [ ] Running either file produces zero new rows in `customer`, `job`, or `site` tables
- [ ] All tests in both files pass
- [ ] Tom has approved and executed the orphaned record purge
- [ ] Post-purge: `customer` table has 0 rows matching `CC Customer%` or `Sched Test Customer%`
- [ ] Full unit test regression matches the Step 1 baseline (no regressions)

---

## Key Reference Files

- `backend/tests/README-adding-tests.md` — master test guide (read section "The Module-Level TestClient Anti-Pattern" first)
- `backend/tests/conftest.py` — `db_session` and `client` fixture definitions
- `backend/tests/batch_1e/test_task_1b2_job_assignment_scheduling.py` — file to fix
- `backend/tests/batch_1e/test_task_1b4_conflict_detection.py` — file to fix
- `dev-docs/db-design/postgres-mcp-guide.md` — postgres-local MCP query syntax reference
