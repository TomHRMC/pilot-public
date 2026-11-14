# Debug Prompt: Fix 9 Failing QuickBooks Sync Tests

**Priority:** BLOCKER (prevents Task 20 implementation)  
**Current Status:** 330 passing, 9 failing (should be 339/339)  
**Expected Resolution Time:** 1-2 hours  
**Mode:** Debug

---

## Problem Statement

The test suite has 9 failing tests in `backend/tests/test_quickbooks_sync.py`. All failures follow the same pattern: the tests expect integer return values but the function is returning dictionaries.

### Failing Tests

```bash
$ cd backend && source .venv/bin/activate && pytest tests/test_quickbooks_sync.py -v

FAILED tests/test_quickbooks_sync.py::test_sync_all_customers_initial_sync
FAILED tests/test_quickbooks_sync.py::test_sync_all_customers_incremental_sync
FAILED tests/test_quickbooks_sync.py::test_sync_all_customers_empty_result
... (6 more similar failures)

================== 9 failed, 330 passed, 2 warnings in 5.61s ===================
```

### Error Pattern

**Example from test_sync_all_customers_initial_sync:**
```
AssertionError: assert {'synced': 2, 'conflicts': 0, 'failed': 0} == 2
```

**Analysis:**
- Test expects: `2` (integer)
- Function returns: `{'synced': 2, 'conflicts': 0, 'failed': 0}` (dictionary)

This suggests the function signature changed from returning `int` to returning `Dict[str, int]` but the tests weren't updated.

---

## Your Mission

**Fix all 9 failing tests in test_quickbooks_sync.py to restore 100% test pass rate (339/339 passing).**

### Success Criteria
- [ ] All 9 failing tests now pass
- [ ] All 330 existing passing tests still pass (no regression)
- [ ] Final test run shows: `339 passed` with 0 failures
- [ ] No changes to production code (only test fixes)

---

## Investigation Steps

### Step 1: Examine the Failing Test File

```bash
# Read the test file to understand what's being tested
cat backend/tests/test_quickbooks_sync.py | head -100
```

**Look for:**
- Test functions that are failing
- Assertions that compare function results to integers
- Expected return values in assertions

### Step 2: Examine the Implementation

```bash
# Find the sync function being tested
grep -n "def sync_all_customers" backend/services/quickbooks_sync.py
```

**Questions to answer:**
- What does `sync_all_customers()` actually return?
- Is it documented in the docstring?
- Did it change recently (check Git history if available)?

### Step 3: Identify the Pattern

All 9 failures likely follow the same pattern:
```python
# OLD TEST CODE (what's currently failing)
result = sync_all_customers(...)
assert result == 2  # ❌ Expects integer

# NEW TEST CODE (what it should be)
result = sync_all_customers(...)
assert result['synced'] == 2  # ✅ Access dictionary key
assert result['conflicts'] == 0
assert result['failed'] == 0
```

### Step 4: Fix All Affected Tests

**Pattern to fix:**
1. Find assertions like `assert result == <integer>`
2. Replace with `assert result['synced'] == <integer>`
3. Add assertions for other dictionary keys if relevant
4. Update any other assertions that expect integer returns

**Example fix:**
```python
# Before
def test_sync_all_customers_initial_sync(db_session, test_tenant, mock_qb_api):
    mock_qb_api.query_customers.return_value = [
        {"Id": "1", "DisplayName": "Customer A"},
        {"Id": "2", "DisplayName": "Customer B"}
    ]
    
    result = sync_all_customers(db_session, test_tenant.id)
    assert result == 2  # ❌ WRONG

# After
def test_sync_all_customers_initial_sync(db_session, test_tenant, mock_qb_api):
    mock_qb_api.query_customers.return_value = [
        {"Id": "1", "DisplayName": "Customer A"},
        {"Id": "2", "DisplayName": "Customer B"}
    ]
    
    result = sync_all_customers(db_session, test_tenant.id)
    assert result['synced'] == 2  # ✅ CORRECT
    assert result['conflicts'] == 0
    assert result['failed'] == 0
```

---

## Commands to Run

### Run Only Failing Tests (Fast Feedback)
```bash
cd backend && source .venv/bin/activate
pytest tests/test_quickbooks_sync.py -v
```

### Run Full Test Suite (Verify No Regression)
```bash
cd backend && source .venv/bin/activate
pytest tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

### Expected Output After Fix
```
========================= 339 passed in X.XXs =========================
```

---

## Important Constraints

### DO NOT Change Production Code
- ❌ Do not modify `backend/services/quickbooks_sync.py`
- ❌ Do not modify any files outside of `backend/tests/`
- ✅ Only modify test assertions in `test_quickbooks_sync.py`

**Why:** The dictionary return type is the correct design. It provides more information (synced count, conflict count, failed count) than a simple integer. The tests just need to be updated to match the current implementation.

### Maintain Test Quality
- ✅ Keep the same test coverage (don't delete tests)
- ✅ Test all aspects of the return value (synced, conflicts, failed)
- ✅ Keep test names and docstrings unchanged
- ✅ Follow existing test patterns in the file

---

## Verification Checklist

Before marking this complete, verify:

- [ ] Ran `pytest tests/test_quickbooks_sync.py -v` → All tests pass
- [ ] Ran `pytest tests/ -v` → 339 tests pass, 0 failures
- [ ] No changes to production code (only test_quickbooks_sync.py modified)
- [ ] All assertions check both 'synced' count and 'conflicts'/'failed' counts
- [ ] Git diff shows only test file changes

---

## Expected Changes Summary

**File Modified:** `backend/tests/test_quickbooks_sync.py`

**Change Pattern (repeat for 9+ tests):**
```diff
- assert result == 2
+ assert result['synced'] == 2
+ assert result['conflicts'] == 0
+ assert result['failed'] == 0
```

**Tests to Fix (estimate - verify actual count):**
1. `test_sync_all_customers_initial_sync`
2. `test_sync_all_customers_incremental_sync`
3. `test_sync_all_customers_empty_result`
4. `test_sync_all_<other_entity>_*` (6 more similar patterns)

---

## Context for Reference

**Project:** AevoFab AI - Electrical contractor management platform  
**Phase:** Phase 3 Complete (QuickBooks Integration)  
**Current Baseline:** 330 passing tests (Phase 1-3 complete)  
**Blocker For:** Task 20 - Audit Event Logging (Phase 4)

**Related Files:**
- Implementation: `backend/services/quickbooks_sync.py`
- Tests: `backend/tests/test_quickbooks_sync.py`
- Design: `dev-docs/analysis/phase-4-5-implementation-roadmap.md`

**QuickBooks Sync Function Signature (current):**
```python
def sync_all_customers(
    db: Session,
    tenant_id: uuid.UUID,
    app_service_id: uuid.UUID
) -> Dict[str, int]:
    """
    Sync all customers from QuickBooks to AevoFab.
    
    Returns:
        Dict with keys: 'synced', 'conflicts', 'failed'
    """
    # ... implementation
    return {
        'synced': synced_count,
        'conflicts': conflict_count,
        'failed': failed_count
    }
```

---

## Timeline

- **Start:** Immediately after receiving this prompt
- **Duration:** 1-2 hours (simple assertion updates)
- **Completion:** When `pytest tests/ -v` shows 339/339 passing
- **Blocker:** Task 20 cannot start until this is resolved

---

## Success Message

When complete, respond with:
```
✅ QuickBooks sync tests fixed: 339/339 tests passing

Changes:
- Modified backend/tests/test_quickbooks_sync.py
- Updated 9 test assertions to check dictionary return values
- All tests now pass with 100% success rate

Ready to unblock Task 20 - Audit Event Logging.
```

---

## If You Get Stuck

**Common Issues:**

1. **Still seeing failures after fix:**
   - Double-check you updated ALL assertions in the test
   - Verify you're checking the correct dictionary keys
   - Make sure you didn't introduce syntax errors

2. **Different number of failures than 9:**
   - Run with `-v` flag to see exact test names
   - Some tests may have multiple assertions
   - Fix all instances in each failing test

3. **Other tests now failing:**
   - You may have introduced a typo or syntax error
   - Revert changes and re-apply carefully
   - Use `pytest tests/test_quickbooks_sync.py::test_name -v` to test one at a time

**Escalation:**
If you cannot resolve within 2 hours, document:
- Which tests you fixed
- Which tests are still failing
- Exact error messages
- Any unexpected behavior

---

**Good luck! This is a straightforward fix that unblocks critical Phase 4 work.**
