# Task 18: Conflict Detection & Resolution Testing Plan
## Manual Testing Guide for QuickBooks Sync Conflicts

**Task Reference:** Phase 3, Task #18 - Conflict Detection & Resolution  
**Created:** 2026-03-22  
**Environment:** Sandbox (Development)  
**Purpose:** Verify conflict detection when both QuickBooks and AevoFab modify the same customer

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Conflict Detection Tests](#-conflict-detection-tests)
3. [Conflict Resolution Tests](#-conflict-resolution-tests)
4. [Edge Cases & Error Handling](#-edge-cases--error-handling)
5. [Reset & Cleanup](#-reset--cleanup-starting-over)
6. [Success Criteria](#-success-criteria)

---

## Prerequisites

### ⚠️ Before Starting

Ensure Tasks 16 & 17 are complete:

```bash
# Verify QuickBooks connected
curl -X GET "http://localhost:8000/api/v1/integrations/quickbooks/status/test"
# Must show: "is_connected": true, "connection_status": "active"

# Verify at least one customer synced
psql postgresql://pilot_user:CHANGE_ME_LOCAL_DB_PW@localhost:5432/pilot_dev \
  -c "SELECT COUNT(*) FROM integration_sync_mapping WHERE entity_type_code = 'customer';"
# Should return count > 0
```

### 📊 Understanding Conflict Detection

**How It Works:**
1. Each sync mapping stores TWO version tokens:
   - **`external_version_token`**: QuickBooks `SyncToken` (integer, auto-incremented)
   - **`internal_version_token`**: AevoFab `customer.updated_at` (ISO timestamp)
2. During sync, the system compares BOTH tokens against current values
3. If **both** changed since last sync → **CONFLICT** (queued for manual resolution)
4. If only **one** changed → normal sync (no conflict)

**Conflict Scenario:**
```
Time 2:00 PM: Last sync completed
              Mapping stores: external_version_token='0', internal_version_token='2026-03-22T14:00:00Z'

Time 2:05 PM: User edits customer in AevoFab
              Customer.updated_at changes to '2026-03-22T14:05:00Z'
              Mapping NOT updated yet (still has old token)

Time 2:10 PM: Accountant edits same customer in QuickBooks
              QB SyncToken increments from 0 to 1
              Mapping NOT updated yet (still has old tokens)

Time 2:15 PM: Sync runs
              ✅ Detects QB changed (SyncToken 0 → 1)
              ✅ Detects AevoFab changed (updated_at timestamp differs)
              🚨 CONFLICT! Both systems modified since last sync
              📋 Queues conflict record for manual resolution
```

---

## 🧪 Conflict Detection Tests

### Test 1: Basic Conflict Detection (Both Systems Modified)

#### Goal
Verify that editing the same customer in both QuickBooks and AevoFab triggers conflict detection.

---

#### Step 1.1: Setup - Create and Sync Test Customer

```bash
# Create customer in AevoFab
curl -X POST "http://localhost:8000/api/v1/customers/test" \
  -H "Content-Type: application/json" \
  -d '{
    "display_name": "Conflict Test Electric",
    "company_name": "Conflict Test Company",
    "email_primary": "conflict@test.com",
    "phone_primary": "(555) 222-3333"
  }'

# Record the customer_id from response
# Example: CUSTOMER_ID=a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

```bash
# Sync to QuickBooks
curl -X POST "http://localhost:8000/api/v1/integrations/quickbooks/sync/customer/<CUSTOMER_ID>/test"

# Record the QuickBooks customer ID from response
# Example: QB_CUSTOMER_ID=70
```

---

#### Step 1.2: Record Initial Version Tokens

```sql
-- Connect to database
psql postgresql://pilot_user:CHANGE_ME_LOCAL_DB_PW@localhost:5432/pilot_dev

-- Save initial version tokens
SELECT 
    ism.id as mapping_id,
    ism.external_id as qb_customer_id,
    ism.external_version_token as qb_sync_token,
    ism.internal_version_token as aevofab_version,
    c.display_name,
    c.updated_at
FROM integration_sync_mapping ism
JOIN customer c ON c.id = ism.entity_id
WHERE c.display_name = 'Conflict Test Electric';

-- Expected Output:
-- external_version_token: '0' (initial QB SyncToken)
-- internal_version_token: (ISO timestamp from customer.updated_at)

-- Record these values:
-- INITIAL_QB_TOKEN=0
-- INITIAL_AEVOFAB_TOKEN=<timestamp>
```

---

#### Step 1.3: Edit Customer in AevoFab

```bash
# Update customer in AevoFab (change email)
curl -X PATCH "http://localhost:8000/api/v1/customers/<CUSTOMER_ID>/test" \
  -H "Content-Type: application/json" \
  -d '{
    "email_primary": "aevofab_edit@test.com"
  }'

# ⚠️ DO NOT sync yet - this is key to creating a conflict
```

---

#### Step 1.4: Edit Same Customer in QuickBooks

1. **Log into QuickBooks Sandbox:** https://app.sandbox.qbo.intuit.com
2. Navigate to **Sales** → **Customers**
3. Find "Conflict Test Electric"
4. Click **Edit**
5. Change:
   ```
   Email: quickbooks_edit@test.com
   Phone: (555) 999-0000
   ```
6. Click **Save**
7. **Note:** QuickBooks increments SyncToken from `0` to `1`

---

#### Step 1.5: Verify Version Tokens Changed in Both Systems

```sql
-- Check AevoFab version changed
SELECT 
    display_name,
    email_primary,
    updated_at
FROM customer
WHERE display_name = 'Conflict Test Electric';

-- Expected:
-- email_primary: 'aevofab_edit@test.com' (local change)
-- updated_at: (new timestamp, different from initial)
```

```sql
-- Check mapping still has OLD tokens (not synced yet)
SELECT 
    external_version_token,
    internal_version_token
FROM integration_sync_mapping
WHERE entity_id = '<CUSTOMER_ID>';

-- Expected (unchanged):
-- external_version_token: '0' (stale - QB now has '1')
-- internal_version_token: <INITIAL_AEVOFAB_TOKEN> (stale)
```

**⚠️ Critical:** At this point, both systems have been modified but sync mapping has NOT been updated. This is the conflict scenario.

---

#### Step 1.6: Trigger Sync - Conflict Should Be Detected

```bash
# Sync customers from QuickBooks
curl -X POST "http://localhost:8000/api/v1/integrations/quickbooks/sync/customers/test"

# Expected Response:
# {
#   "status": "success",
#   "synced_count": 0,
#   "conflicts_detected": 1,
#   "message": "Detected 1 conflict(s) requiring resolution"
# }
```

**Watch Celery Worker Logs:**
```
[INFO] Processing customer: Conflict Test Electric (ID: 70)
[INFO] Conflict detected: Both QB and AevoFab modified since last sync
[INFO] QB SyncToken changed: 0 → 1
[INFO] AevoFab updated_at changed
[INFO] Queuing conflict for manual resolution
[INFO] Conflict queued: <conflict_id>
```

---

#### Step 1.7: Verify Conflict Record Created

```sql
-- Check conflict was queued
SELECT 
    ic.id as conflict_id,
    ic.entity_type_code,
    ic.local_payload_json->>'email_primary' as aevofab_email,
    ic.remote_payload_json->'PrimaryEmailAddr'->>'Address' as qb_email,
    ic.detected_at,
    ic.resolved_at,
    c.display_name
FROM integration_sync_conflict ic
JOIN customer c ON c.id = ic.entity_id
WHERE c.display_name = 'Conflict Test Electric'
ORDER BY ic.detected_at DESC
LIMIT 1;

-- Expected Output:
-- aevofab_email: 'aevofab_edit@test.com'
-- qb_email: 'quickbooks_edit@test.com'
-- detected_at: <recent timestamp>
-- resolved_at: NULL (unresolved)

-- Record the conflict_id for resolution testing
-- CONFLICT_ID=<uuid>
```

---

#### Step 1.8: Verify Customer Data NOT Overwritten

```sql
-- Verify AevoFab customer still has local changes (conflict prevented sync)
SELECT 
    display_name,
    email_primary,
    phone_primary
FROM customer
WHERE display_name = 'Conflict Test Electric';

-- Expected (UNCHANGED from Step 1.3):
-- email_primary: 'aevofab_edit@test.com' (local edit preserved)
-- phone_primary: '(555) 222-3333' (original, NOT QB's (555) 999-0000)
```

**✅ Success Criteria:**
- ✅ Conflict record created in `integration_sync_conflict` table
- ✅ `local_payload_json` contains AevoFab version
- ✅ `remote_payload_json` contains QuickBooks version
- ✅ Customer data in AevoFab NOT overwritten
- ✅ `resolved_at` is NULL (unresolved)

---

## 🔧 Conflict Resolution Tests

### Test 2: List Unresolved Conflicts

```bash
# List all conflicts for tenant
curl -X GET "http://localhost:8000/api/v1/integrations/quickbooks/conflicts/test"

# Expected Response (array of conflicts):
[
  {
    "id": "<conflict_id>",
    "entity_type_code": "customer",
    "entity_id": "<customer_id>",
    "local_payload_json": {
      "display_name": "Conflict Test Electric",
      "email_primary": "aevofab_edit@test.com",
      "phone_primary": "(555) 222-3333",
      "updated_at": "2026-03-22T..."
    },
    "remote_payload_json": {
      "DisplayName": "Conflict Test Electric",
      "PrimaryEmailAddr": {"Address": "quickbooks_edit@test.com"},
      "PrimaryPhone": {"FreeFormNumber": "(555) 999-0000"},
      "SyncToken": "1"
    },
    "detected_at": "2026-03-22T...",
    "resolved_at": null
  }
]
```

**✅ Success Criteria:**
- API returns array of conflicts
- Each conflict shows both local and remote payloads
- Conflicts ordered by `detected_at` DESC

---

### Test 3: Resolve Conflict - Accept Local (AevoFab Wins)

#### Step 3.1: Resolve with "accept_local" Strategy

```bash
# Keep AevoFab version, overwrite QuickBooks
curl -X POST "http://localhost:8000/api/v1/integrations/quickbooks/conflicts/<CONFLICT_ID>/resolve/test" \
  -H "Content-Type: application/json" \
  -d '{
    "strategy": "accept_local",
    "notes": "AevoFab version is correct - overwriting QuickBooks"
  }'

# Expected Response:
{
  "status": "resolved",
  "conflict_id": "<conflict_id>",
  "resolution_strategy": "accept_local",
  "resolved_at": "2026-03-22T...",
  "message": "Conflict resolved successfully"
}
```

---

#### Step 3.2: Verify AevoFab Data Unchanged

```sql
-- AevoFab customer should be unchanged (already had local version)
SELECT 
    display_name,
    email_primary,
    phone_primary
FROM customer
WHERE display_name = 'Conflict Test Electric';

-- Expected:
-- email_primary: 'aevofab_edit@test.com' (AevoFab version preserved)
-- phone_primary: '(555) 222-3333' (original)
```

---

#### Step 3.3: Verify QuickBooks Updated with AevoFab Data

1. **Log into QuickBooks Sandbox**
2. Navigate to "Conflict Test Electric" customer
3. Verify fields match AevoFab:
   - Email: `aevofab_edit@test.com` (overwritten from QB's `quickbooks_edit@test.com`)
   - Phone: `(555) 222-3333` (AevoFab version)

---

#### Step 3.4: Verify Conflict Marked as Resolved

```sql
-- Check conflict is resolved
SELECT 
    id,
    resolution_strategy_code,
    resolved_at,
    resolved_by_user_id,
    resolution_notes
FROM integration_sync_conflict
WHERE id = '<CONFLICT_ID>';

-- Expected:
-- resolution_strategy_code: 'accept_local'
-- resolved_at: <recent timestamp>
-- resolved_by_user_id: <test user UUID>
-- resolution_notes: 'AevoFab version is correct...'
```

---

#### Step 3.5: Verify Version Tokens Updated

```sql
-- Check mapping updated with new tokens
SELECT 
    external_id,
    external_version_token,
    internal_version_token,
    last_synced_at
FROM integration_sync_mapping
WHERE entity_id = (
    SELECT id FROM customer WHERE display_name = 'Conflict Test Electric'
);

-- Expected:
-- external_version_token: '2' (incremented from 1 after AevoFab → QB sync)
-- internal_version_token: <current customer.updated_at>
-- last_synced_at: <recent timestamp>
```

**✅ Success Criteria:**
- QuickBooks customer updated to match AevoFab
- Conflict marked as resolved
- Version tokens synchronized
- No data loss

---

### Test 4: Resolve Conflict - Accept Remote (QuickBooks Wins)

#### Step 4.1: Create Another Conflict

Repeat Test 1 steps with a new customer:
- Customer name: "QB Wins Test"
- AevoFab edit: `email_primary: "aevofab@test.com"`
- QB edit: `email: "qb@test.com"`, `phone: "(555) 888-7777"`
- Trigger sync → conflict detected

Record: `CONFLICT_ID_2=<uuid>`

---

#### Step 4.2: Resolve with "accept_remote"

```bash
# Keep QuickBooks version, overwrite AevoFab
curl -X POST "http://localhost:8000/api/v1/integrations/quickbooks/conflicts/<CONFLICT_ID_2>/resolve/test" \
  -H "Content-Type: application/json" \
  -d '{
    "strategy": "accept_remote",
    "notes": "QuickBooks version is authoritative"
  }'
```

---

#### Step 4.3: Verify AevoFab Updated with QB Data

```sql
-- AevoFab customer should now match QuickBooks
SELECT 
    display_name,
    email_primary,
    phone_primary
FROM customer
WHERE display_name = 'QB Wins Test';

-- Expected:
-- email_primary: 'qb@test.com' (QB version, overwritten from AevoFab)
-- phone_primary: '(555) 888-7777' (QB version)
```

---

#### Step 4.4: Verify QuickBooks Unchanged

1. **In QuickBooks Sandbox:**
2. Verify "QB Wins Test" customer still has:
   - Email: `qb@test.com` (unchanged)
   - Phone: `(555) 888-7777` (unchanged)

**✅ Success Criteria:**
- AevoFab customer updated to match QuickBooks
- QuickBooks customer unchanged
- Conflict resolved successfully

---

### Test 5: Resolve Conflict - Manual Merge

#### Step 5.1: Create Third Conflict

Create conflict with customer "Merge Test" (repeat Test 1 pattern).

Record: `CONFLICT_ID_3=<uuid>`

---

#### Step 5.2: Resolve with "merge" Strategy

```bash
# Provide merged data (best of both)
curl -X POST "http://localhost:8000/api/v1/integrations/quickbooks/conflicts/<CONFLICT_ID_3>/resolve/test" \
  -H "Content-Type: application/json" \
  -d '{
    "strategy": "merge",
    "merged_payload": {
      "display_name": "Merge Test Electric",
      "email_primary": "merged@test.com",
      "phone_primary": "(555) 111-2222"
    },
    "notes": "Manually merged best fields from both systems"
  }'
```

---

#### Step 5.3: Verify Both Systems Updated

```sql
-- Check AevoFab has merged data
SELECT 
    email_primary,
    phone_primary
FROM customer
WHERE display_name = 'Merge Test Electric';

-- Expected:
-- email_primary: 'merged@test.com'
-- phone_primary: '(555) 111-2222'
```

**In QuickBooks Sandbox:**
- Verify "Merge Test Electric" has same merged values

**✅ Success Criteria:**
- Both systems updated with merged data
- Conflict resolved

---

## 🔥 Edge Cases & Error Handling

### Test 6: No Conflict - Only QB Modified

**Scenario:** QuickBooks edited, AevoFab NOT edited → normal sync (no conflict)

#### Step 6.1: Create Customer and Sync

```bash
curl -X POST "http://localhost:8000/api/v1/customers/test" \
  -H "Content-Type: application/json" \
  -d '{"display_name": "No Conflict QB Edit", "email_primary": "original@test.com"}'

curl -X POST "http://localhost:8000/api/v1/integrations/quickbooks/sync/customer/<CUSTOMER_ID>/test"
```

---

#### Step 6.2: Edit ONLY in QuickBooks

1. In QB Sandbox, edit "No Conflict QB Edit"
2. Change email to `qb_only_edit@test.com`
3. Save

---

#### Step 6.3: Sync - Should Update Without Conflict

```bash
curl -X POST "http://localhost:8000/api/v1/integrations/quickbooks/sync/customers/test"

# Expected: synced_count=1, conflicts_detected=0
```

```sql
-- Verify AevoFab updated (no conflict)
SELECT email_primary FROM customer WHERE display_name = 'No Conflict QB Edit';
-- Expected: 'qb_only_edit@test.com'

-- Verify NO conflict created
SELECT COUNT(*) FROM integration_sync_conflict WHERE entity_id = '<CUSTOMER_ID>';
-- Expected: 0
```

**✅ Success:** One-sided edit syncs normally without conflict.

---

### Test 7: No Conflict - Only AevoFab Modified

**Scenario:** AevoFab edited, QB NOT edited → normal sync

Follow similar pattern as Test 6, but edit only in AevoFab.

**✅ Success:** One-sided edit syncs without conflict.

---

### Test 8: Resolve Non-Existent Conflict (404)

```bash
# Try to resolve fake conflict ID
curl -X POST "http://localhost:8000/api/v1/integrations/quickbooks/conflicts/00000000-0000-0000-0000-000000000000/resolve/test" \
  -H "Content-Type: application/json" \
  -d '{"strategy": "accept_local"}'

# Expected Response (404):
{
  "detail": "Conflict not found"
}
```

---

### Test 9: Resolve Already-Resolved Conflict (400)

```bash
# Try to resolve the same conflict twice
curl -X POST "http://localhost:8000/api/v1/integrations/quickbooks/conflicts/<CONFLICT_ID>/resolve/test" \
  -H "Content-Type: application/json" \
  -d '{"strategy": "accept_local"}'

# Expected Response (400):
{
  "detail": "Conflict already resolved"
}
```

---

### Test 10: Invalid Resolution Strategy (422)

```bash
curl -X POST "http://localhost:8000/api/v1/integrations/quickbooks/conflicts/<CONFLICT_ID>/resolve/test" \
  -H "Content-Type: application/json" \
  -d '{"strategy": "invalid_strategy"}'

# Expected Response (422 Validation Error)
```

---

## 🧹 Reset & Cleanup: Starting Over

### Why You Need This

After running manual tests, your dev database will have:
- Test customers in AevoFab
- Sync mappings pointing to QuickBooks
- Resolved and unresolved conflicts
- QuickBooks sandbox customers

To **reset to a clean state** for re-testing, follow these steps.

---

### Option 1: Quick Cleanup Script (Recommended)

Create this Python script:

```python
# backend/tests/scripts/cleanup_conflict_tests.py

import asyncio
from sqlalchemy import select, delete
from app.db import engine, AsyncSession
from app.models.customer import Customer
from app.models.system import (
    IntegrationSyncMapping,
    IntegrationSyncConflict
)

async def cleanup_conflict_tests():
    """
    Clean up all conflict test data
    
    WARNING: Only run in DEV environment!
    """
    async with AsyncSession(engine) as db:
        test_tenant_id = "00000000-0000-0000-0000-000000000001"
        
        print("🧹 Starting conflict test cleanup...")
        
        # 1. Delete all conflicts
        result = await db.execute(
            delete(IntegrationSyncConflict)
            .where(IntegrationSyncConflict.tenant_id == test_tenant_id)
        )
        print(f"✅ Deleted {result.rowcount} conflicts")
        
        # 2. Delete sync mappings for test customers
        test_customer_names = [
            'Conflict Test Electric',
            'QB Wins Test',
            'Merge Test Electric',
            'No Conflict QB Edit',
            'No Conflict Aevo Edit'
        ]
        
        # Get customer IDs
        customers = await db.execute(
            select(Customer.id)
            .where(Customer.tenant_id == test_tenant_id)
            .where(Customer.display_name.in_(test_customer_names))
        )
        customer_ids = [c.id for c in customers.scalars().all()]
        
        # Delete mappings
        if customer_ids:
            result = await db.execute(
                delete(IntegrationSyncMapping)
                .where(IntegrationSyncMapping.entity_id.in_(customer_ids))
            )
            print(f"✅ Deleted {result.rowcount} sync mappings")
        
        # 3. Delete test customers
        result = await db.execute(
            delete(Customer)
            .where(Customer.tenant_id == test_tenant_id)
            .where(Customer.display_name.in_(test_customer_names))
        )
        print(f"✅ Deleted {result.rowcount} test customers")
        
        await db.commit()
        
        print("✨ Cleanup complete! Database reset to pre-test state.")
        print("\n⚠️  Remember to manually delete customers in QuickBooks Sandbox!")

if __name__ == "__main__":
    asyncio.run(cleanup_conflict_tests())
```

**Run the cleanup:**

```bash
cd backend
python tests/scripts/cleanup_conflict_tests.py
```

---

### Option 2: Manual SQL Cleanup

```sql
-- Connect to database
psql postgresql://pilot_user:CHANGE_ME_LOCAL_DB_PW@localhost:5432/pilot_dev

-- Set your test tenant ID
\set test_tenant_id '00000000-0000-0000-0000-000000000001'

-- 1. Delete all conflicts
DELETE FROM integration_sync_conflict
WHERE tenant_id = :'test_tenant_id';

-- 2. Delete sync mappings for test customers
DELETE FROM integration_sync_mapping
WHERE tenant_id = :'test_tenant_id'
  AND entity_id IN (
    SELECT id FROM customer
    WHERE display_name IN (
      'Conflict Test Electric',
      'QB Wins Test',
      'Merge Test Electric',
      'No Conflict QB Edit',
      'No Conflict Aevo Edit'
    )
  );

-- 3. Delete test customers
DELETE FROM customer
WHERE tenant_id = :'test_tenant_id'
  AND display_name IN (
    'Conflict Test Electric',
    'QB Wins Test',
    'Merge Test Electric',
    'No Conflict QB Edit',
    'No Conflict Aevo Edit'
  );

-- Verify cleanup
SELECT 
    (SELECT COUNT(*) FROM integration_sync_conflict WHERE tenant_id = :'test_tenant_id') as conflicts,
    (SELECT COUNT(*) FROM integration_sync_mapping WHERE tenant_id = :'test_tenant_id') as mappings,
    (SELECT COUNT(*) FROM customer WHERE tenant_id = :'test_tenant_id') as customers;
```

---

### QuickBooks Sandbox Cleanup

**⚠️ Important:** Database cleanup does NOT delete customers from QuickBooks.

**Option A: Delete Manually (Recommended for <10 customers)**

1. Log into QuickBooks Sandbox: https://app.sandbox.qbo.intuit.com
2. Navigate to **Sales** → **Customers**
3. For each test customer:
   - Click customer name
   - Click **Edit** → **Make inactive**

**Option B: Create Fresh Sandbox Company**

1. Go to Intuit Developer Portal
2. Navigate to **Dashboard** → **Sandbox**
3. Click **Create New Company**
4. Re-run OAuth flow (Task 16 Step 1)

---

### Data to Record Before Cleanup

```bash
# Save baseline state before cleanup
echo "=== Pre-Cleanup State ===" > cleanup_baseline.txt

# Record counts
psql postgresql://pilot_user:CHANGE_ME_LOCAL_DB_PW@localhost:5432/pilot_dev \
  -c "SELECT COUNT(*) as conflicts FROM integration_sync_conflict;" \
  >> cleanup_baseline.txt

psql postgresql://pilot_user:CHANGE_ME_LOCAL_DB_PW@localhost:5432/pilot_dev \
  -c "SELECT COUNT(*) as customers FROM customer;" \
  >> cleanup_baseline.txt

cat cleanup_baseline.txt
```

---

## ✅ Task 18 Complete Checklist

- [ ] Test 1: Basic conflict detection works
- [ ] Test 2: Conflict listing API returns conflicts
- [ ] Test 3: "accept_local" resolution syncs to QuickBooks
- [ ] Test 4: "accept_remote" resolution updates AevoFab
- [ ] Test 5: "merge" strategy updates both systems
- [ ] Test 6: One-sided QB edit syncs without conflict
- [ ] Test 7: One-sided AevoFab edit syncs without conflict
- [ ] Test 8: Non-existent conflict returns 404
- [ ] Test 9: Already-resolved conflict returns 400
- [ ] Test 10: Invalid strategy returns 422
- [ ] Cleanup script tested and documented

---

## 📊 Performance Benchmarks

| Operation | Expected Time | Acceptable Max |
|-----------|---------------|----------------|
| Detect conflict (single customer) | < 1 second | 2 seconds |
| Queue conflict to database | < 500ms | 1 second |
| List conflicts (20 records) | < 500ms | 1 second |
| Resolve conflict (accept_local) | < 3 seconds | 5 seconds |
| Resolve conflict (accept_remote) | < 3 seconds | 5 seconds |
| Resolve conflict (merge) | < 4 seconds | 6 seconds |

---

## 🎯 Success Criteria

Task 18 is **complete** when:

1. ✅ Simultaneous edits generate conflict record (not silent overwrite)
2. ✅ Tenant can view conflict diffs via API
3. ✅ Resolution updates both systems atomically
4. ✅ No data loss during conflict resolution
5. ✅ Audit trail of who resolved conflict and when
6. ✅ One-sided edits sync normally without triggering conflicts
7. ✅ Error handling works correctly (404, 400, 422)

---

## 📚 Reference Documentation

- **Implementation Plan:** `task-18-conflict-detection-impl-plan.md`
- **Roadmap:** `phase-2-5-implementation-roadmap.md`
- **Conflict Detection Service:** `backend/services/quickbooks_sync.py` (lines 152-250)
- **Resolution API:** `backend/api/routes/integrations.py` (conflict endpoints)
- **Test Suite:** `backend/tests/test_conflict_detection.py`

---

**Created:** 2026-03-22  
**Last Updated:** 2026-03-22  
**Status:** Ready for Manual Testing  
**Maintained By:** AevoFab Architecture Team
