# Task 18 Remaining Test Failures - Debug Prompt

**Date:** 2026-03-22  
**Status:** 🔴 5 TESTS FAILING (321/326 passing)  
**Context:** Task 18 conflict detection implementation completed, but 5 tests still failing

## Background

Task 18 successfully implemented the `internal_version_token` field for conflict detection:

### ✅ Completed Work
1. **Database Migration** - Added `internal_version_token` to `backend/app/models/system.py`
2. **Conflict Detection Fix** - Fixed broken logic in `backend/services/quickbooks_sync.py`
3. **Sync Methods Updated** - Both `sync_customer_from_qb()` and `sync_customer_to_qb()` now track internal version
4. **Backfill Script** - Created `backend/migrations/scripts/backfill_internal_version_tokens.py`

### Baseline vs Current
- **Original Baseline:** 322/325 tests passing (3 resolution tests already failing)
- **Current Status:** 321/326 tests passing (added 1 new test)
- **Change:** Same 3 resolution tests failing, plus 2 new issues

## Failing Tests

### Group 1: Resolution API Tests (500 Errors) - 3 TESTS

**Files:**
- Test File: `backend/tests/test_conflict_detection.py`
- Endpoint: `backend/api/routes/integrations.py`

**Tests:**
1. `TestConflictResolutionAPI::test_resolve_conflict_accept_local` (line 335)
2. `TestConflictResolutionAPI::test_resolve_conflict_accept_remote` (line 402)
3. `TestConflictResolutionAPI::test_resolve_conflict_merge` (line 451)

**Symptoms:**
```
assert 500 == 200
  +  where 500 = <Response [500 Internal Server Error]>.status_code
```

**What We've Done:**
- ✅ Added `qb_credential_full` fixture with proper encryption
- ✅ Created sync mappings with `internal_version_token` set
- ✅ Mocked QuickBooks API calls with `patch("httpx.AsyncClient.post")`
- ❌ Still getting 500 errors (no traceback visible in test output)

**Investigation Needed:**
1. **Check server-side error logs** - The 500 error suggests an exception in the endpoint
2. **Verify mock patching** - The mock path `httpx.AsyncClient.post` might not be intercepting the actual call
3. **Check credential decryption** - The endpoint calls `sync.get_access_token()` which decrypts tokens
4. **Inspect sync methods** - Both `sync_customer_to_qb()` and `sync_customer_from_qb()` are called

**Debugging Steps:**
```bash
# Run with full traceback and print statements
cd backend
pytest tests/test_conflict_detection.py::TestConflictResolutionAPI::test_resolve_conflict_accept_local -vv -s --tb=long
```

**Potential Issues:**
- Endpoint might be raising an exception during token refresh check
- Mock not intercepting the HTTP call properly (async context issue?)
- Missing database transaction isolation
- The mapping update logic might be failing

---

### Group 2: Version Token Tracking Test - 1 TEST

**File:** `backend/tests/test_conflict_detection.py`

**Test:** `TestInternalVersionTokenTracking::test_internal_version_token_updated_on_sync`

**Symptom:**
```
AssertionError: External version should be updated
assert '0' == '1'
  - 1
  + 0
```

**Issue:**
The mock is not working - `sync_mapping.external_version_token` remains `"0"` instead of being updated to `"1"` from the mocked QB response.

**Expected Behavior:**
After calling `sync.sync_customer_to_qb()`, the mapping should have:
- `external_version_token = "1"` (from mocked QB response)
- `internal_version_token = <updated customer timestamp>`

**Code:**
```python
with patch("httpx.AsyncClient.post") as mock_post:
    mock_post.return_value = MagicMock(
        status_code=200,
        json=lambda: {"Customer": {"Id": "QB999", "SyncToken": "1"}},
        raise_for_status=lambda: None,
    )
    await sync.sync_customer_to_qb(test_customer.id)
```

**Investigation Needed:**
1. Check if the mock path is correct for async HTTP calls
2. Verify `sync_customer_to_qb()` line 467-488 is actually using the mock
3. Check if transaction commits are happening properly
4. The mapping update might be in a different transaction

**Fix Approaches:**
- Use `patch("httpx.AsyncClient")` with context manager mock
- Mock at the service level instead of HTTP level
- Ensure database session is properly flushed/committed

---

### Group 3: Test Isolation Issue - 1 TEST

**File:** `backend/tests/test_quickbooks_sync.py`

**Test:** `test_get_access_token_not_connected`

**Symptom:**
```
Failed: DID NOT RAISE <class 'ValueError'>
```

**Expected:** Should raise `ValueError` with message "QuickBooks not connected" when no QB credential exists

**Actual:** No exception is raised

**Root Cause:**
Test isolation failure - leftover QuickBooks credential data from previous tests in the suite.

**Investigation Needed:**
1. Check test fixture cleanup in `conftest.py`
2. Verify `db_session` fixture rolls back properly between tests
3. Check if any tests are committing to the database without proper cleanup

**Fix Approaches:**
- Add explicit cleanup in test fixture teardown
- Use `db_session.rollback()` in fixture cleanup
- Isolate this test with `pytest.mark.order` or run it first
- Add `autouse=True` fixture to clean QB credentials between tests

---

## Key Files Reference

### Models
- `backend/app/models/system.py` - IntegrationSyncMapping model
- `backend/app/models/system.py` - IntegrationCredential model

### Services
- `backend/services/quickbooks_sync.py` - QuickBooksSync class
  - Line 65: `get_access_token()` method
  - Line 152: `detect_conflict()` method (FIXED)
  - Line 269: `sync_customer_from_qb()` method (UPDATED)
  - Line 379: `sync_customer_to_qb()` method (UPDATED)

### API Endpoints
- `backend/api/routes/integrations.py` - `/conflicts/{id}/resolve/test` endpoint

### Tests
- `backend/tests/test_conflict_detection.py` - Main conflict detection tests
- `backend/tests/test_quickbooks_sync.py` - QuickBooks sync tests
- `backend/tests/conftest.py` - Test fixtures

### Migration
- `backend/migrations/versions/2026_03_22_1410-40a492ca69ce_add_internal_version_token_to_sync_.py`

## Debug Commands

```bash
# Run all failing tests with full output
cd backend
source .venv/bin/activate

# Test resolution endpoints with detailed trace
pytest tests/test_conflict_detection.py::TestConflictResolutionAPI -vv --tb=long

# Test version tracking
pytest tests/test_conflict_detection.py::TestInternalVersionTokenTracking -vv --tb=long

# Test isolation issue
pytest tests/test_quickbooks_sync.py::test_get_access_token_not_connected -vv --tb=long

# Run all tests to see final count
pytest tests/ -v --tb=no
```

## Success Criteria

- [ ] All 3 resolution tests pass (or understand why they were already failing)
- [ ] Version tracking test passes with proper mock interception
- [ ] Test isolation issue resolved
- [ ] **Target: 326/326 tests passing (100%)**

## Notes

- Original baseline had 322/325 passing with these 3 resolution tests already failing
- The resolution test failures may have existed before this task
- Focus on getting the new version tracking test working first
- Test isolation issue is unrelated to conflict detection changes
