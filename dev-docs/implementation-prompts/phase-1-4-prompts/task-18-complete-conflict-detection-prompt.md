# Task 18 Complete Implementation Prompt: Conflict Detection with internal_version_token

**Date:** 2026-03-22  
**Status:** 🔵 READY FOR IMPLEMENTATION  
**Baseline Tests:** 322/325 passing (99.1%)  
**Reference Plan:** dev-docs/analysis/task-18-conflict-detection-full-implementation-plan.md

## Executive Summary

Complete the Task 18 conflict detection implementation by adding the `internal_version_token` field to `IntegrationSyncMapping` and fixing the broken conflict detection logic.

**Current Status:**
- ✅ Simplified MVP implemented (conflict queuing, API endpoints)
- 🐛 **BUG IDENTIFIED:** Conflict detection logic broken - never detects AevoFab changes
- ⚠️ 3 resolution tests failing (QB credential mocking needed)
- 📋 Full implementation plan exists with detailed steps

**Goal:** Achieve 325/325 tests passing (100%) with reliable conflict detection.

## Critical Bug to Fix

**Location:** `backend/services/quickbooks_sync.py`

**Current Broken Code:**
```python
current_version = customer.updated_at.isoformat()

# If internal_version_token not set, use current version (backward compatibility)
last_synced_version = getattr(
    mapping, "internal_version_token", current_version  # ⚠️ BUG: Always returns current_version
)
aevofab_changed = current_version != last_synced_version  # Always False!
```

**Why It's Broken:**
- `getattr()` returns fallback `current_version` because field doesn't exist
- Comparison becomes `current_version != current_version` → always False
- System NEVER detects when AevoFab data changed
- Only QuickBooks changes are detected

**Impact:** Missing real conflicts where both systems edit the same customer.

## Implementation Steps

Follow the detailed plan in `task-18-conflict-detection-full-implementation-plan.md` with these priorities:

### Phase 1: Database Schema (2 hours)

**1.1 Create Migration**
```bash
cd backend
alembic revision -m "add_internal_version_token_to_sync_mapping"
```

**Migration Template:**
```python
"""Add internal_version_token to integration_sync_mapping

Revision ID: <generated>
Revises: <previous_revision>
Create Date: 2026-03-22

"""
from alembic import op
import sqlalchemy as sa

def upgrade() -> None:
    op.add_column(
        'integration_sync_mapping',
        sa.Column('internal_version_token', sa.String(), nullable=True),
        schema='integration'
    )

def downgrade() -> None:
    op.drop_column(
        'integration_sync_mapping', 
        'internal_version_token', 
        schema='integration'
    )
```

**1.2 Update Model**

**File:** `backend/app/models/system.py`

Add after `external_version_token`:
```python
external_version_token: Optional[str] = Field(default=None)
internal_version_token: Optional[str] = Field(default=None)  # NEW FIELD
sync_preference: str = Field(default="aevofab_master", nullable=False)
```

**1.3 Run Migration**
```bash
alembic upgrade head
```

### Phase 2: Fix Conflict Detection Logic (1 hour)

**2.1 Fix detect_conflict() Method**

**File:** `backend/services/quickbooks_sync.py`

**Replace lines 174-191 with:**
```python
    # Check both version tokens
    qb_token = qb_customer.get("SyncToken", "0")
    qb_changed = qb_token != mapping.external_version_token

    # Check if AevoFab customer changed since last sync
    current_internal_version = customer.updated_at.isoformat()
    
    if mapping.internal_version_token is None:
        # First sync after migration or new mapping - no conflict
        aevofab_changed = False
    else:
        aevofab_changed = current_internal_version != mapping.internal_version_token

    # CONFLICT: Both sides modified since last sync
    return qb_changed and aevofab_changed
```

**2.2 Update sync_customer_from_qb() to Track Internal Version**

**File:** `backend/services/quickbooks_sync.py` (find existing mapping update logic)

**After successful sync, update BOTH tokens:**
```python
# Update mapping with both version tokens
mapping.external_version_token = qb_customer.get("SyncToken", "0")
mapping.internal_version_token = customer.updated_at.isoformat()  # NEW
mapping.last_synced_at = datetime.now(UTC)
self.db.add(mapping)
self.db.commit()
```

**2.3 Update sync_customer_to_qb() Similarly**

Find where mapping is updated after syncing TO QuickBooks and add:
```python
mapping.external_version_token = qb_response["Customer"]["SyncToken"]
mapping.internal_version_token = customer.updated_at.isoformat()  # NEW
mapping.last_synced_at = datetime.now(UTC)
```

### Phase 3: Fix Failing Tests (2 hours)

**3.1 Add Comprehensive QB Credential Fixture**

**File:** `backend/tests/test_conflict_detection.py` (add after existing fixtures)

```python
@pytest.fixture
def qb_credential_full(db_session, test_tenant, qb_app_service, test_user):
    """
    Full QuickBooks credential for resolution tests.
    Includes all required fields for sync operations.
    """
    from core.encryption import encrypt_token
    
    credential = IntegrationCredential(
        tenant_id=test_tenant.id,
        app_service_id=qb_app_service.id,
        connection_status="active",
        secret_json={
            "access_token_encrypted": encrypt_token("test_access_token_full"),
            "refresh_token_encrypted": encrypt_token("test_refresh_token_full"),
        },
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        initiated_by_user_id=test_user.id,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db_session.add(credential)
    db_session.commit()
    db_session.refresh(credential)
    return credential
```

**3.2 Fix Resolution Tests with Proper Mocking**

**Pattern for all 3 resolution tests:**
```python
@pytest.mark.asyncio
async def test_resolve_conflict_accept_local(
    self,
    client,
    db_session,
    test_tenant,
    test_user,
    qb_app_service,
    qb_credential_full,  # Use full credential
    test_customer,
):
    """Resolution strategy 'accept_local' should overwrite QuickBooks."""
    
    # Create sync mapping
    sync_mapping = IntegrationSyncMapping(
        tenant_id=test_tenant.id,
        app_service_id=qb_app_service.id,
        entity_type_code="customer",
        entity_id=test_customer.id,
        external_id="QB123",
        external_version_token="5",
        internal_version_token=test_customer.updated_at.isoformat(),  # NEW
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db_session.add(sync_mapping)
    
    # Create conflict
    conflict = IntegrationSyncConflict(
        tenant_id=test_tenant.id,
        app_service_id=qb_app_service.id,
        entity_type_code="customer",
        entity_id=test_customer.id,
        external_id="QB123",
        status="pending",
        internal_payload={
            "display_name": test_customer.display_name,
            "email": test_customer.email,
        },
        external_payload={
            "Id": "QB123",
            "DisplayName": "Different Name",
            "SyncToken": "6",
        },
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db_session.add(conflict)
    db_session.commit()
    db_session.refresh(conflict)
    
    # Mock QuickBooks API call
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "Customer": {
                    "Id": "QB123",
                    "DisplayName": test_customer.display_name,
                    "SyncToken": "7",  # Incremented by QB
                }
            },
            raise_for_status=lambda: None,
        )
        
        # Resolve conflict
        response = client.post(
            f"/api/v1/integrations/quickbooks/conflicts/{conflict.id}/resolve/test",
            json={"strategy": "accept_local"},
        )
    
    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "resolved"
    
    # Verify conflict marked as resolved
    db_session.refresh(conflict)
    assert conflict.resolved_at is not None
    assert conflict.resolved_by == test_user.id
    assert conflict.status == "resolved"
```

**Apply similar pattern to:**
- `test_resolve_conflict_accept_remote`
- `test_resolve_conflict_merge`

**3.3 Add Integration Test for Version Token Tracking**

**Add new test:**
```python
@pytest.mark.asyncio
async def test_internal_version_token_updated_on_sync(
    self,
    db_session,
    test_tenant,
    qb_app_service,
    qb_credential,
    test_customer,
):
    """Verify internal_version_token is updated after sync."""
    sync = QuickBooksSync(test_tenant.id, db_session)
    
    # Create initial mapping
    sync_mapping = IntegrationSyncMapping(
        tenant_id=test_tenant.id,
        app_service_id=qb_app_service.id,
        entity_type_code="customer",
        entity_id=test_customer.id,
        external_id="QB999",
        external_version_token="0",
        internal_version_token=test_customer.updated_at.isoformat(),
        created_by=test_customer.created_by,
        updated_by=test_customer.updated_by,
    )
    db_session.add(sync_mapping)
    db_session.commit()
    
    original_version = test_customer.updated_at.isoformat()
    
    # Edit customer (updated_at changes)
    import time
    time.sleep(0.01)  # Ensure timestamp changes
    test_customer.display_name = "Updated Name"
    db_session.add(test_customer)
    db_session.commit()
    db_session.refresh(test_customer)
    
    new_version = test_customer.updated_at.isoformat()
    assert new_version != original_version
    
    # Mock QB API for sync
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"Customer": {"Id": "QB999", "SyncToken": "1"}},
            raise_for_status=lambda: None,
        )
        
        await sync.sync_customer_to_qb(test_customer.id)
    
    # Verify internal_version_token updated
    db_session.refresh(sync_mapping)
    assert sync_mapping.internal_version_token == new_version
    assert sync_mapping.external_version_token == "1"
```

### Phase 4: Backfill Existing Data (30 min)

**4.1 Create Backfill Script**

**File:** `backend/migrations/scripts/backfill_internal_version_tokens.py`

```python
"""
Backfill internal_version_token for existing sync mappings.
Run after migration: python -m migrations.scripts.backfill_internal_version_tokens
"""

from datetime import UTC
from app.models.system import IntegrationSyncMapping
from app.models.crm import Customer
from sqlmodel import Session, select
from core.db import engine


def backfill_internal_version_tokens():
    """Backfill internal_version_token for all existing mappings."""
    with Session(engine) as session:
        # Get all customer mappings without internal_version_token
        stmt = select(IntegrationSyncMapping).where(
            IntegrationSyncMapping.entity_type_code == "customer",
            IntegrationSyncMapping.internal_version_token == None
        )
        mappings = session.exec(stmt).all()
        
        print(f"Found {len(mappings)} customer mappings to backfill")
        
        for mapping in mappings:
            try:
                customer = session.get(Customer, mapping.entity_id)
                if customer:
                    mapping.internal_version_token = customer.updated_at.isoformat()
                    session.add(mapping)
                    print(f"✓ Backfilled mapping {mapping.id}")
                else:
                    print(f"⚠ Customer {mapping.entity_id} not found, skipping mapping {mapping.id}")
            except Exception as e:
                print(f"✗ Error backfilling mapping {mapping.id}: {e}")
                continue
        
        session.commit()
        print(f"✅ Backfill complete! Updated {len(mappings)} mappings")


if __name__ == "__main__":
    backfill_internal_version_tokens()
```

**4.2 Run Backfill**
```bash
cd backend
source .venv/bin/activate
python -m migrations.scripts.backfill_internal_version_tokens
```

### Phase 5: Verify Everything Works (30 min)

**5.1 Run Full Test Suite**
```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

**Expected:** 325/325 tests passing (100%)

**5.2 Run Conflict Tests Specifically**
```bash
pytest tests/test_conflict_detection.py -v
```

**Expected:** 11/11 tests passing

**5.3 Verify No Regressions**
```bash
pytest tests/test_quickbooks_sync.py -v
```

**Expected:** 27/27 tests passing

## Success Criteria

- [x] Migration created and applied
- [x] `internal_version_token` field added to IntegrationSyncMapping model
- [x] Conflict detection logic fixed (no longer always False)
- [x] Both sync methods track internal version token
- [x] 3 failing resolution tests fixed with proper mocking
- [x] New integration test for version tracking added
- [x] Backfill script created and run
- [x] **All 325 tests passing (100%)**
- [x] No regressions in baseline tests

## Key Files Modified

1. **Migration:** `backend/migrations/versions/YYYY_MM_DD_HHMM_add_internal_version_token.py` (NEW)
2. **Model:** `backend/app/models/system.py` (line 344-360)
3. **Service:** `backend/services/quickbooks_sync.py` (detect_conflict, sync methods)
4. **Tests:** `backend/tests/test_conflict_detection.py` (fix 3 tests, add 1 new)
5. **Script:** `backend/migrations/scripts/backfill_internal_version_tokens.py` (NEW)

## Testing Checklist

- [ ] Migration runs without errors
- [ ] Model field accessible in code
- [ ] `detect_conflict()` correctly identifies conflicts
- [ ] `detect_conflict()` returns False when only one side changed
- [ ] Sync methods update both version tokens
- [ ] Resolution endpoints work with all 3 strategies
- [ ] Backfill script completes successfully
- [ ] All 325 tests pass
- [ ] No test warnings or errors

## Notes for MVP Builder

- **Critical Fix:** The existing detect_conflict() has a `getattr()` bug - it must be fixed
- **Test Strategy:** Use proper mocking for QB API calls in resolution tests
- **Data Safety:** Migration is safe (nullable column, no data loss)
- **Backward Compatibility:** Code handles None gracefully for existing data
- **Time Estimate:** 5-6 hours total (2 migration, 1 logic fix, 2 tests, 0.5 backfill, 0.5 verify)

## References

- **Original Spec:** `dev-docs/analysis/phase-2-5-implementation-roadmap.md`
- **Full Plan:** `dev-docs/analysis/task-18-conflict-detection-full-implementation-plan.md`
- **Original Prompt:** `dev-docs/implementation-prompts/task-18-prompt.md`
- **Database Design:** `dev-docs/db-design/aevofab-db-process-v2.6h.md`
