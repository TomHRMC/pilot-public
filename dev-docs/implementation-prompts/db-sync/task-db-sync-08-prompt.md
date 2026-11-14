# Task 8: Missing Unique Constraints (Phase 3 - Data Integrity)

**Reference:** `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` - Task 8  
**Authority:** `dev-docs/db-design/pilot-db-schema-v2.6h.json`  
**Type:** Schema Synchronization - Data Integrity (Unique Constraints)

---

## Context

We're building AevoFab AI, an AI-powered SaaS platform for electrical contractors with voice-controlled quoting and QuickBooks integration. Following the 80/20 rule to reach MVP quickly.

This is a **targeted schema synchronization task** to achieve 100% alignment between our SQLModel implementations and the Golden Master Database Schema (v2.6h JSON). This is NOT a new feature - it's surgical corrections to ensure database-level data integrity and business rule enforcement.

---

## Completed So Far

**Phase 1: Foundation (COMPLETE - March 30-31, 2026):**
- ✅ Task 1: Timezone enforcement - 9 columns fixed
- ✅ Task 2: Citext conversion for user email
- ✅ Task 3: QuickBooks identity rules on Customer table

**Phase 2: Functions & Triggers (COMPLETE - March 31, 2026):**
- ✅ Task 4: Missing PL/pgSQL functions - 3 functions + 200 triggers implemented
- ✅ Task 5: Function naming standard compliance - all functions renamed
- ✅ Task 6: Audit trigger coverage - 85 audit triggers added
- ✅ Task 7: Operational trigger verification - 293 total triggers documented

**Test Coverage:** 457/457 tests passing (100%)  
**Migrations Applied:** 10 migrations (all successful)  
**See:** `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` for full context

---

## Current Task: Missing Unique Constraints (3 Remaining)

**Status:** 🟡 PARTIALLY COMPLETE (1/4 done)  
**Priority:** HIGH  
**Effort:** 1 day  
**Gap Reference:** Phase 4.5 Plan - Phase 3, Task 8

The Golden Master Schema specifies 4 unique constraints to prevent duplicate records. One was already completed on March 30, 2026 (`contact_portal_invite(contact_id)`). This task implements the **3 remaining unique constraints**.

### The 3 Constraints to Add

| # | Entity | Constraint | Problem Prevented | Files |
|---|--------|------------|-------------------|-------|
| **1** | `PricebookItem` | `UNIQUE(tenant_id, sku)` | Duplicate SKUs in tenant's pricebook | `backend/app/models/quoting.py` |
| **2** | `UserSsoIdentity` | `UNIQUE(sso_provider_code, provider_user_id)` | Same Google account linked to multiple AevoFab users | `backend/app/models/auth.py` |
| **3** | `QuoteAcceptance` | `UNIQUE(quote_version_id, contact_id)` | Contact accepts same quote version multiple times | `backend/app/models/quoting.py` |

**Note:** The 4th constraint (`job_assignment(job_id, user_id)`) will be addressed separately once fulfillment models are finalized.

---

## Requirements

### 1. Implementation Details

#### Constraint 1: `pricebook_item(tenant_id, sku)` - Prevent Duplicate SKUs

**Problem:** Same SKU can be added twice to tenant's pricebook, causing sync conflicts and pricing errors.

**SQLModel Fix:**
```python
# backend/app/models/quoting.py
from sqlalchemy import UniqueConstraint

class PricebookItem(TenantIsolatedMixin, SQLModel, table=True):
    __tablename__ = "pricebook_item"
    __table_args__ = (
        UniqueConstraint('tenant_id', 'sku', name='uq_pricebook_item_tenant_sku'),
    )
    # ... existing fields ...
```

**Migration SQL:**
```sql
-- Pre-migration check for existing duplicates
-- If any found, must be manually resolved first
SELECT tenant_id, sku, COUNT(*) as duplicate_count
FROM pricebook_item 
GROUP BY tenant_id, sku 
HAVING COUNT(*) > 1;

-- Add constraint
ALTER TABLE pricebook_item 
ADD CONSTRAINT uq_pricebook_item_tenant_sku 
UNIQUE (tenant_id, sku);
```

---

#### Constraint 2: `user_sso_identity(sso_provider_code, provider_user_id)` - Prevent Duplicate SSO Links

**Problem:** Same external identity (e.g., Google account) could be linked to multiple AevoFab users, violating identity uniqueness.

**SQLModel Fix:**
```python
# backend/app/models/auth.py
from sqlalchemy import UniqueConstraint

class UserSsoIdentity(SQLModel, table=True):
    __tablename__ = "user_sso_identity"
    __table_args__ = (
        UniqueConstraint(
            'sso_provider_code', 
            'provider_user_id', 
            name='uq_user_sso_identity_provider_user'
        ),
    )
    # ... existing fields ...
```

**Migration SQL:**
```sql
-- Pre-migration check for existing duplicates
SELECT sso_provider_code, provider_user_id, COUNT(*) as duplicate_count
FROM user_sso_identity
GROUP BY sso_provider_code, provider_user_id
HAVING COUNT(*) > 1;

-- Add constraint
ALTER TABLE user_sso_identity 
ADD CONSTRAINT uq_user_sso_identity_provider_user 
UNIQUE (sso_provider_code, provider_user_id);
```

---

#### Constraint 3: `quote_acceptance(quote_version_id, contact_id)` - Prevent Duplicate Acceptances

**Problem:** Same contact could accept same quote version multiple times, creating duplicate job records and invoices.

**SQLModel Fix:**
```python
# backend/app/models/quoting.py
from sqlalchemy import UniqueConstraint

class QuoteAcceptance(SQLModel, table=True):
    __tablename__ = "quote_acceptance"
    __table_args__ = (
        UniqueConstraint(
            'quote_version_id', 
            'contact_id', 
            name='uq_quote_acceptance_version_contact'
        ),
    )
    # ... existing fields ...
```

**Migration SQL:**
```sql
-- Pre-migration check for existing duplicates
SELECT quote_version_id, contact_id, COUNT(*) as duplicate_count
FROM quote_acceptance
GROUP BY quote_version_id, contact_id
HAVING COUNT(*) > 1;

-- Add constraint
ALTER TABLE quote_acceptance 
ADD CONSTRAINT uq_quote_acceptance_version_contact 
UNIQUE (quote_version_id, contact_id);
```

---

### 2. Implementation Order

Execute in this exact sequence:

1. **SQLModel Changes**
   - Update `backend/app/models/quoting.py`:
     - Add `UniqueConstraint` to `PricebookItem.__table_args__`
     - Add `UniqueConstraint` to `QuoteAcceptance.__table_args__`
   - Update `backend/app/models/auth.py`:
     - Add `UniqueConstraint` to `UserSsoIdentity.__table_args__`

2. **Pre-Migration Duplicate Check**
   ```bash
   cd backend
   # Run the 3 duplicate detection queries manually
   # If any duplicates found, document them and resolve manually before proceeding
   ```

3. **Generate Alembic Migration**
   ```bash
   cd backend
   alembic revision --autogenerate -m "add_missing_unique_constraints_task8"
   ```

4. **Review Migration**
   - Verify all 3 constraints are in the upgrade() function
   - Verify downgrade() drops all 3 constraints
   - Add duplicate check queries to migration docstring

5. **Apply Migration**
   ```bash
   alembic upgrade head
   ```

6. **Create Test Suite**
   - Create `backend/tests/test_unique_constraints_task8.py`
   - Write tests for all 3 constraints (see Test Requirements below)

7. **Run Tests**
   ```bash
   cd backend && source .venv/bin/activate
   pytest tests/test_unique_constraints_task8.py -v
   ```

8. **Verify Complete Success**
   - All 9 new tests pass
   - All 457 existing tests still pass (no regression)
   - Total: 466/466 passing

---

### 3. Test Requirements

**⚠️ ZERO FAILING TESTS POLICY:**
- **ALL 457 existing tests MUST still pass** (baseline cannot regress)
- **ALL 9 new tests MUST pass** (unique constraint verification)
- **Target: 466/466 passing (100%)**

**Test File:** `backend/tests/test_unique_constraints_task8.py`

**Required Tests:**

```python
"""
Test unique constraints for Phase 3 Task 8.
"""
import pytest
from sqlalchemy.exc import IntegrityError
from backend.app.models.quoting import PricebookItem, QuoteAcceptance
from backend.app.models.auth import UserSsoIdentity


class TestPricebookItemUnique:
    """Test UNIQUE(tenant_id, sku) constraint."""
    
    def test_duplicate_sku_same_tenant_rejected(self, session, test_tenant, test_user):
        """Attempting to add same SKU twice to same tenant pricebook should raise IntegrityError."""
        # Create first pricebook item
        item1 = PricebookItem(
            tenant_id=test_tenant.id,
            sku="PANEL-200A",
            description="200A Main Panel",
            unit_price_cents=45000,
            unit="EA",
            created_by=test_user.id
        )
        session.add(item1)
        session.commit()
        
        # Attempt duplicate SKU in same tenant
        item2 = PricebookItem(
            tenant_id=test_tenant.id,
            sku="PANEL-200A",  # Same SKU
            description="Different Description",
            unit_price_cents=50000,
            unit="EA",
            created_by=test_user.id
        )
        session.add(item2)
        
        with pytest.raises(IntegrityError) as exc_info:
            session.commit()
        assert "uq_pricebook_item_tenant_sku" in str(exc_info.value)
    
    def test_same_sku_different_tenants_allowed(self, session, test_tenant, test_user):
        """Same SKU can exist in different tenant pricebooks."""
        # Create second tenant
        tenant2 = Tenant(name="Other Electrical Co", created_by=test_user.id)
        session.add(tenant2)
        session.commit()
        
        # Add same SKU to both tenants
        item1 = PricebookItem(
            tenant_id=test_tenant.id,
            sku="PANEL-200A",
            description="200A Main Panel",
            unit_price_cents=45000,
            unit="EA",
            created_by=test_user.id
        )
        item2 = PricebookItem(
            tenant_id=tenant2.id,
            sku="PANEL-200A",  # Same SKU, different tenant
            description="200A Main Panel",
            unit_price_cents=45000,
            unit="EA",
            created_by=test_user.id
        )
        session.add_all([item1, item2])
        session.commit()
        
        # Both should exist
        assert session.query(PricebookItem).filter_by(sku="PANEL-200A").count() == 2
    
    def test_different_skus_same_tenant_allowed(self, session, test_tenant, test_user):
        """Different SKUs in same tenant pricebook are allowed."""
        item1 = PricebookItem(
            tenant_id=test_tenant.id,
            sku="PANEL-200A",
            description="200A Main Panel",
            unit_price_cents=45000,
            unit="EA",
            created_by=test_user.id
        )
        item2 = PricebookItem(
            tenant_id=test_tenant.id,
            sku="PANEL-400A",  # Different SKU
            description="400A Main Panel",
            unit_price_cents=75000,
            unit="EA",
            created_by=test_user.id
        )
        session.add_all([item1, item2])
        session.commit()
        
        assert session.query(PricebookItem).filter_by(tenant_id=test_tenant.id).count() == 2


class TestUserSsoIdentityUnique:
    """Test UNIQUE(sso_provider_code, provider_user_id) constraint."""
    
    def test_duplicate_sso_identity_rejected(self, session, test_user):
        """Same external identity cannot be linked to multiple AevoFab users."""
        # Create second user
        user2 = User(
            email="user2@test.com",
            full_name="User Two",
            password_hash="dummy_hash",
            created_by=test_user.id
        )
        session.add(user2)
        session.commit()
        
        # Link Google account to first user
        identity1 = UserSsoIdentity(
            user_id=test_user.id,
            sso_provider_code="google",
            provider_user_id="google_123456",
            created_by=test_user.id
        )
        session.add(identity1)
        session.commit()
        
        # Attempt to link same Google account to second user
        identity2 = UserSsoIdentity(
            user_id=user2.id,
            sso_provider_code="google",
            provider_user_id="google_123456",  # Same external identity
            created_by=test_user.id
        )
        session.add(identity2)
        
        with pytest.raises(IntegrityError) as exc_info:
            session.commit()
        assert "uq_user_sso_identity_provider_user" in str(exc_info.value)
    
    def test_different_sso_providers_same_user_allowed(self, session, test_user):
        """User can link multiple SSO providers (Google + Microsoft)."""
        identity1 = UserSsoIdentity(
            user_id=test_user.id,
            sso_provider_code="google",
            provider_user_id="google_123456",
            created_by=test_user.id
        )
        identity2 = UserSsoIdentity(
            user_id=test_user.id,
            sso_provider_code="microsoft",
            provider_user_id="microsoft_789012",
            created_by=test_user.id
        )
        session.add_all([identity1, identity2])
        session.commit()
        
        assert session.query(UserSsoIdentity).filter_by(user_id=test_user.id).count() == 2
    
    def test_different_provider_users_same_provider_allowed(self, session, test_user):
        """Different Google accounts can be in system (linked to different users)."""
        # Create second user
        user2 = User(
            email="user2@test.com",
            full_name="User Two",
            password_hash="dummy_hash",
            created_by=test_user.id
        )
        session.add(user2)
        session.commit()
        
        identity1 = UserSsoIdentity(
            user_id=test_user.id,
            sso_provider_code="google",
            provider_user_id="google_123456",
            created_by=test_user.id
        )
        identity2 = UserSsoIdentity(
            user_id=user2.id,
            sso_provider_code="google",
            provider_user_id="google_789012",  # Different Google account
            created_by=test_user.id
        )
        session.add_all([identity1, identity2])
        session.commit()
        
        assert session.query(UserSsoIdentity).filter_by(sso_provider_code="google").count() == 2


class TestQuoteAcceptanceUnique:
    """Test UNIQUE(quote_version_id, contact_id) constraint."""
    
    def test_duplicate_acceptance_rejected(self, session, test_tenant, test_user, test_customer, test_contact):
        """Contact cannot accept same quote version twice."""
        # Create quote
        quote = Quote(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            quote_number="Q-2026-001",
            created_by=test_user.id
        )
        session.add(quote)
        session.commit()
        
        # Create quote version
        quote_version = QuoteVersion(
            quote_id=quote.id,
            version_number=1,
            created_by=test_user.id
        )
        session.add(quote_version)
        session.commit()
        
        # First acceptance
        acceptance1 = QuoteAcceptance(
            quote_version_id=quote_version.id,
            contact_id=test_contact.id,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            created_by=test_user.id
        )
        session.add(acceptance1)
        session.commit()
        
        # Attempt duplicate acceptance
        acceptance2 = QuoteAcceptance(
            quote_version_id=quote_version.id,
            contact_id=test_contact.id,  # Same contact, same version
            ip_address="192.168.1.2",
            user_agent="Mozilla/5.0",
            created_by=test_user.id
        )
        session.add(acceptance2)
        
        with pytest.raises(IntegrityError) as exc_info:
            session.commit()
        assert "uq_quote_acceptance_version_contact" in str(exc_info.value)
    
    def test_same_contact_different_versions_allowed(self, session, test_tenant, test_user, test_customer, test_contact):
        """Contact can accept different versions of same quote."""
        # Create quote
        quote = Quote(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            quote_number="Q-2026-002",
            created_by=test_user.id
        )
        session.add(quote)
        session.commit()
        
        # Create two versions
        version1 = QuoteVersion(quote_id=quote.id, version_number=1, created_by=test_user.id)
        version2 = QuoteVersion(quote_id=quote.id, version_number=2, created_by=test_user.id)
        session.add_all([version1, version2])
        session.commit()
        
        # Accept both versions
        acceptance1 = QuoteAcceptance(
            quote_version_id=version1.id,
            contact_id=test_contact.id,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            created_by=test_user.id
        )
        acceptance2 = QuoteAcceptance(
            quote_version_id=version2.id,  # Different version
            contact_id=test_contact.id,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            created_by=test_user.id
        )
        session.add_all([acceptance1, acceptance2])
        session.commit()
        
        assert session.query(QuoteAcceptance).filter_by(contact_id=test_contact.id).count() == 2
    
    def test_different_contacts_same_version_allowed(self, session, test_tenant, test_user, test_customer, test_contact):
        """Different contacts can accept same quote version (multi-signer scenario)."""
        # Create second contact
        contact2 = Contact(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            first_name="Jane",
            last_name="Doe",
            created_by=test_user.id
        )
        session.add(contact2)
        session.commit()
        
        # Create quote and version
        quote = Quote(
            tenant_id=test_tenant.id,
            customer_id=test_customer.id,
            quote_number="Q-2026-003",
            created_by=test_user.id
        )
        session.add(quote)
        session.commit()
        
        quote_version = QuoteVersion(quote_id=quote.id, version_number=1, created_by=test_user.id)
        session.add(quote_version)
        session.commit()
        
        # Both contacts accept
        acceptance1 = QuoteAcceptance(
            quote_version_id=quote_version.id,
            contact_id=test_contact.id,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            created_by=test_user.id
        )
        acceptance2 = QuoteAcceptance(
            quote_version_id=quote_version.id,
            contact_id=contact2.id,  # Different contact
            ip_address="192.168.1.2",
            user_agent="Mozilla/5.0",
            created_by=test_user.id
        )
        session.add_all([acceptance1, acceptance2])
        session.commit()
        
        assert session.query(QuoteAcceptance).filter_by(quote_version_id=quote_version.id).count() == 2
```

**Test Execution:**
```bash
# Run existing tests first (validate baseline)
cd backend && source .venv/bin/activate
pytest --ignore=tests/integration/ tests/ -v

# Run new constraint tests
pytest tests/test_unique_constraints_task8.py -v

# Run all tests together (final verification)
pytest tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

---

### 4. Database Verification

**After Migration Applied:**

```sql
-- Verify all 3 constraints exist
SELECT 
    conname AS constraint_name,
    conrelid::regclass AS table_name,
    pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE conname IN (
    'uq_pricebook_item_tenant_sku',
    'uq_user_sso_identity_provider_user',
    'uq_quote_acceptance_version_contact'
)
ORDER BY conname;

-- Expected output (3 rows):
-- uq_pricebook_item_tenant_sku        | pricebook_item     | UNIQUE (tenant_id, sku)
-- uq_quote_acceptance_version_contact | quote_acceptance   | UNIQUE (quote_version_id, contact_id)
-- uq_user_sso_identity_provider_user  | user_sso_identity  | UNIQUE (sso_provider_code, provider_user_id)
```

---

### 5. Pre-Migration Duplicate Detection

**CRITICAL:** Before applying the migration, check for existing duplicate data that would violate the constraints:

```bash
cd backend
python -c "
from sqlalchemy import create_engine, text
import os

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/pilot_dev')
engine = create_engine(DATABASE_URL)

print('\\n=== Checking for Duplicate Pricebook Items ===')
with engine.connect() as conn:
    result = conn.execute(text('''
        SELECT tenant_id, sku, COUNT(*) as duplicate_count
        FROM pricebook_item 
        GROUP BY tenant_id, sku 
        HAVING COUNT(*) > 1
    ''')).fetchall()
    if result:
        print(f'❌ FOUND {len(result)} DUPLICATE SKUs:')
        for row in result:
            print(f'   Tenant {row[0]}: SKU \"{row[1]}\" appears {row[2]} times')
    else:
        print('✅ No duplicates found')

print('\\n=== Checking for Duplicate SSO Identities ===')
with engine.connect() as conn:
    result = conn.execute(text('''
        SELECT sso_provider_code, provider_user_id, COUNT(*) as duplicate_count
        FROM user_sso_identity
        GROUP BY sso_provider_code, provider_user_id
        HAVING COUNT(*) > 1
    ''')).fetchall()
    if result:
        print(f'❌ FOUND {len(result)} DUPLICATE SSO LINKS:')
        for row in result:
            print(f'   Provider {row[0]}: User \"{row[1]}\" appears {row[2]} times')
    else:
        print('✅ No duplicates found')

print('\\n=== Checking for Duplicate Quote Acceptances ===')
with engine.connect() as conn:
    result = conn.execute(text('''
        SELECT quote_version_id, contact_id, COUNT(*) as duplicate_count
        FROM quote_acceptance
        GROUP BY quote_version_id, contact_id
        HAVING COUNT(*) > 1
    ''')).fetchall()
    if result:
        print(f'❌ FOUND {len(result)} DUPLICATE ACCEPTANCES:')
        for row in result:
            print(f'   Version {row[0]}, Contact {row[1]}: {row[2]} acceptances')
    else:
        print('✅ No duplicates found')

print('\\n=== Duplicate Check Complete ===')
print('If duplicates found above, resolve manually before applying migration.')
"
```

**If Duplicates Found:**
1. Document which records are duplicates
2. Determine which to keep (usually the earliest `created_at`)
3. Delete or merge duplicates manually
4. Re-run duplicate check until all clear
5. Then proceed with migration

---

### 6. Code Standards

- **Import statements required:**
  ```python
  from sqlalchemy import UniqueConstraint
  ```
- **Naming convention:** All constraint names start with `uq_` prefix
- **Table args tuple:** Must be a tuple `(constraint,)` with trailing comma if single item
- **No feature creep:** Strictly implement the 3 constraints, nothing more

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

- [ ] Pre-migration duplicate check run (no duplicates found or resolved)
- [ ] All 3 SQLModel classes updated with `__table_args__` UniqueConstraints
- [ ] Alembic migration created with autogenerate
- [ ] Migration includes all 3 `ALTER TABLE ADD CONSTRAINT` statements
- [ ] Migration applied successfully (`alembic upgrade head`)
- [ ] All 9 new tests written and passing
- [ ] **ALL 457 existing tests still passing** (no regression)
- [ ] **Total: 466/466 tests passing (100%)**
- [ ] Migration rollback tested (`alembic downgrade -1` then `upgrade head`)
- [ ] Database verification query shows all 3 constraints exist
- [ ] Plan document updated with Task 8 completion status

**Zero Tolerance Policy:**
- **Any failing test = INCOMPLETE**
- **Test pass rate MUST be 100% (466/466)**
- **Any existing duplicates MUST be resolved before migration**

---

## Key Files to Modify

### SQLModel Files (3 files)
- `backend/app/models/quoting.py` - PricebookItem, QuoteAcceptance
- `backend/app/models/auth.py` - UserSsoIdentity

### Migration (To Create)
- `backend/migrations/versions/YYYY_MM_DD_HHMM-*_add_missing_unique_constraints_task8.py`

### Tests (To Create)
- `backend/tests/test_unique_constraints_task8.py` - 9 tests

### Documentation (To Update)
- `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` - Mark Task 8 complete

---

## Example Task Flow

```bash
# 1. Check current baseline
cd backend && source .venv/bin/activate
pytest --ignore=tests/integration/ tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 457 passed

# 2. Run pre-migration duplicate check
python [duplicate detection script above]
# Must show "No duplicates found" for all 3 checks

# 3. Review current models
grep -A 15 "class PricebookItem" backend/app/models/quoting.py
grep -A 15 "class UserSsoIdentity" backend/app/models/auth.py
grep -A 15 "class QuoteAcceptance" backend/app/models/quoting.py

# 4. Implement SQLModel changes
# [modify backend/app/models/quoting.py - add __table_args__ to PricebookItem]
# [modify backend/app/models/auth.py - add __table_args__ to UserSsoIdentity]
# [modify backend/app/models/quoting.py - add __table_args__ to QuoteAcceptance]

# 5. Generate migration
alembic revision --autogenerate -m "add_missing_unique_constraints_task8"

# 6. Review migration file
cat backend/migrations/versions/[timestamp]_add_missing_unique_constraints_task8.py
# Verify all 3 constraints in upgrade() and downgrade()

# 7. Apply migration
alembic upgrade head

# 8. Verify constraints in database
psql -d pilot_dev -c "
SELECT conname, conrelid::regclass, pg_get_constraintdef(oid) 
FROM pg_constraint 
WHERE conname LIKE 'uq_%' AND conname IN (
  'uq_pricebook_item_tenant_sku',
  'uq_user_sso_identity_provider_user',
  'uq_quote_acceptance_version_contact'
);"

# 9. Create test file
# [create backend/tests/test_unique_constraints_task8.py with 9 tests]

# 10. Run new tests
pytest tests/test_unique_constraints_task8.py -v
# Expected: 9 passed

# 11. Run ALL tests (verify no regression)
pytest tests/ -v 2>&1 | grep -E "(passed|failed)" | tail -1
# Expected: 466 passed

# 12. Test migration rollback
alembic downgrade -1
alembic upgrade head
pytest tests/test_unique_constraints_task8.py -v
# Expected: Still 9 passed

# 13. Update plan document
# [mark Task 8 as complete in phase-4.5-db-schema-sync-to-design-plan.md]
```

---

## Notes

- **Data Integrity Focus:** These constraints prevent common data corruption scenarios
- **Cost Impact:** $0 - Database constraints have negligible performance overhead
- **Production Safe:** All changes are backward compatible if no duplicate data exists
- **Rollback Tested:** Every `upgrade()` must have a working `downgrade()` implementation
- **Golden Master Authority:** These constraints are specified in `pilot-db-schema-v2.6h.json`

**Common Issues:**
- **IntegrityError during migration:** Existing duplicate data detected - run duplicate check script
- **Test fixtures failing:** May need to update test fixtures to use unique values
- **Constraint already exists:** Previous partial migration - check `pg_constraint` table

**If you get stuck:**
- Check for existing duplicate data first (most common issue)
- Review the Golden Master JSON for exact constraint specifications
- Each constraint is LOW complexity (simple ALTER TABLE statement)
- All test code is provided - copy/paste is encouraged

---

**Ready to Begin!** 🚀

Start by running the pre-migration duplicate check, then implement the 3 SQLModel changes, generate the migration, and create the test suite. All SQL and test code is provided above.
