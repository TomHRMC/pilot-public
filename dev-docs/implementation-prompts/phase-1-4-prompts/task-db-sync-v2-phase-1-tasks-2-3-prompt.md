# Task Phase 1: Tasks 2 & 3 - DB Sync v2 Continuation

**Reference:** `dev-docs/implementation-prompts/task-db-sync-v2-phase-1-prompt.md` - Phase 1, Tasks 2-3
**Master Plan:** `dev-docs/analysis/phase-4.6-db-schema-sync-2-plan.md`
**Authority (Dual Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `dev-docs/db-design/aevofab-db-schema-dump-phase-4.6.sql` - Production SQL Dump

---

## Context

**Phase 1 Progress:** Task 1 ✅ COMPLETE (April 2, 2026)
- ✅ Added `discount_version` table with check constraint
- ✅ Migration applied: `2026_04_02_1618-0575f69cd5db_add_discount_version_table_task1.py`
- ✅ Test suite created: `test_discount_version_task1.py` - 10 tests passing
- ✅ Current test count: 555/555 non-integration tests passing (545 baseline + 10 new)

**Remaining Work:** Tasks 2 & 3
- Task 2: Add 4 missing check constraints (MIGRATION)
- Task 3: Update email regex in JSON schema (JSON UPDATE only, no migration)

---

## Task 2: Add Missing Check Constraints (4 Constraints)

**Effort:** 0.5 days
**Priority:** HIGH
**Change Type:** MIGRATION

### Pre-Migration Data Validation (CRITICAL)

**Run these queries BEFORE creating the migration to identify invalid data:**

```sql
-- Check 1: Platform users without MFA
SELECT id, email, platform_role_code, is_mfa_enabled
FROM "user"
WHERE platform_role_code IN ('staff', 'superadmin')
  AND is_mfa_enabled = false;
-- Expected: 0 rows (no violations)

-- Check 2: Invalid invite emails
SELECT id, invite_email FROM contact_portal_invite
WHERE invite_email !~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$';
-- Expected: 0 rows (no violations)

-- Check 3: Invalid customer emails
SELECT id, email FROM customer
WHERE email IS NOT NULL 
  AND email !~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$';
-- Expected: 0 rows (no violations)

-- Check 4: Invalid tenant user invite emails
SELECT id, email FROM tenant_user_invite
WHERE email !~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$';
-- Expected: 0 rows (no violations)
```

**If ANY violations found:** Clean up the data before proceeding with migration.

### SQLModel Updates

#### 1. Update User Model

**File:** `backend/app/models/core.py`

Add to `__table_args__`:
```python
from sqlalchemy import CheckConstraint

# Platform users must have MFA enabled
CheckConstraint(
    "platform_role_code IS NULL OR "
    "(platform_role_code IN ('staff', 'superadmin') AND is_mfa_enabled = true)",
    name='user_platform_mfa_required_chk'
),
```

#### 2. Update ContactPortalInvite Model

**File:** `backend/app/models/crm.py`

Add to `__table_args__`:
```python
# Email format validation
CheckConstraint(
    "invite_email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'",
    name='contact_portal_invite_email_chk'
),
```

#### 3. Update Customer Model

**File:** `backend/app/models/crm.py`

Add to `__table_args__`:
```python
# Email format validation (nullable)
CheckConstraint(
    "email IS NULL OR "
    "email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'",
    name='customer_email_format_chk'
),
```

#### 4. Update TenantUserInvite Model

**File:** `backend/app/models/core.py`

Add to `__table_args__`:
```python
# Email format validation
CheckConstraint(
    "email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'",
    name='tenant_user_invite_email_format_chk'
),
```

### Generate and Apply Migration

```bash
cd backend
source .venv/bin/activate
alembic revision --autogenerate -m "add_missing_check_constraints_task2"
# Review the migration - remove any unrelated changes
alembic upgrade head
```

### Test Suite

**Create:** `backend/tests/test_check_constraints_task2.py`

**Minimum 12 Tests Required:**

```python
"""
Test Suite: Phase 4.6 Task 2 - Missing Check Constraints
Tests platform MFA and email format validation constraints
"""
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.core import User, TenantUserInvite
from app.models.crm import Customer, ContactPortalInvite


class TestPlatformMFAConstraint:
    """Test user_platform_mfa_required_chk constraint"""
    
    def test_staff_user_with_mfa_allowed(self, db_session: Session, test_tenant):
        """Staff user with MFA enabled should be allowed"""
        # Test implementation
    
    def test_staff_user_without_mfa_rejected(self, db_session: Session, test_tenant):
        """Staff user without MFA should be rejected"""
        # Test implementation
    
    def test_regular_user_without_mfa_allowed(self, db_session: Session, test_tenant):
        """Regular user (no platform role) without MFA should be allowed"""
        # Test implementation


class TestContactPortalInviteEmailConstraint:
    """Test contact_portal_invite_email_chk constraint"""
    
    def test_valid_email_allowed(self, db_session: Session, test_tenant, test_contact):
        """Valid email format should be allowed"""
        # Test implementation
    
    def test_invalid_email_rejected(self, db_session: Session, test_tenant, test_contact):
        """Invalid email format should be rejected"""
        # Test implementation
    
    def test_email_missing_domain_rejected(self, db_session: Session, test_tenant, test_contact):
        """Email without proper domain should be rejected"""
        # Test implementation


class TestCustomerEmailConstraint:
    """Test customer_email_format_chk constraint"""
    
    def test_valid_email_allowed(self, db_session: Session, test_tenant):
        """Valid email format should be allowed"""
        # Test implementation
    
    def test_null_email_allowed(self, db_session: Session, test_tenant):
        """NULL email should be allowed (nullable field)"""
        # Test implementation
    
    def test_invalid_email_rejected(self, db_session: Session, test_tenant):
        """Invalid email format should be rejected"""
        # Test implementation


class TestTenantUserInviteEmailConstraint:
    """Test tenant_user_invite_email_format_chk constraint"""
    
    def test_valid_email_allowed(self, db_session: Session, test_tenant, test_user):
        """Valid email format should be allowed"""
        # Test implementation
    
    def test_invalid_email_rejected(self, db_session: Session, test_tenant, test_user):
        """Invalid email format should be rejected"""
        # Test implementation
    
    def test_complex_email_allowed(self, db_session: Session, test_tenant, test_user):
        """Complex but valid email should be allowed"""
        # Test implementation
```

**Reference full test implementations in:** `task-db-sync-v2-phase-1-prompt.md` lines 629-801

### Database Verification

```sql
-- Verify all 4 constraints exist
SELECT conname, conrelid::regclass, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conname IN (
    'user_platform_mfa_required_chk',
    'contact_portal_invite_email_chk',
    'customer_email_format_chk',
    'tenant_user_invite_email_format_chk'
)
ORDER BY conname;
-- Expected: 4 rows
```

### Success Criteria

- [ ] Pre-migration validation completed (0 violations)
- [ ] 4 SQLModel classes updated with check constraints
- [ ] Alembic migration created and applied
- [ ] All 12 new tests written and passing
- [ ] Database verification confirms all 4 constraints active
- [ ] All 567 tests passing (555 baseline + 12 new = 100%)

---

## Task 3: Update Email Regex to Match SQL Standard (SQL → JSON)

**Effort:** 0.5 days
**Priority:** MEDIUM
**Change Type:** JSON_UPDATE (NO MIGRATION)

### Problem

The JSON schema uses a **simple email regex** (`^[^@\s]+@[^@\s]+\.[^@\s]+$`), but the SQL database uses a **stricter, production-grade regex** (`^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$`).

**Decision:** Adopt the **SQL standard** (stricter is safer for production data quality).

### JSON Schema Fix Required

**File:** `dev-docs/db-design/pilot-db-schema-v2.6h.json`

**Find and replace ALL instances of simple email regex with strict regex:**

**BEFORE (Simple Regex):**
```json
{
  "check_constraints": [
    {
      "name": "user_email_chk",
      "expression": "email ~* '^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$'"
    }
  ]
}
```

**AFTER (Strict Regex):**
```json
{
  "check_constraints": [
    {
      "name": "user_email_chk",
      "expression": "email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'"
    }
  ]
}
```

**Affected Constraints (Update ALL 5):**
1. `user.email` - `user_email_chk`
2. `user_endpoint.value` - `user_endpoint_value_email_chk`
3. `customer.email` - `customer_email_format_chk`
4. `contact_portal_invite.invite_email` - `contact_portal_invite_email_chk`
5. `tenant_user_invite.email` - `tenant_user_invite_email_format_chk`

### Database Verification (No Changes Expected)

```sql
-- Confirm database already has correct strict regex
SELECT conname, conrelid::regclass, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conname LIKE '%email%'
  AND contype = 'c'
ORDER BY conname;

-- Expected: All email constraints use strict regex:
-- ^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$
```

### Test Verification

```bash
cd backend
source .venv/bin/activate
pytest tests/ --ignore=tests/integration -v 2>&1 | grep passed | tail -1
# Expected: 567 passed (no change - documentation only)
```

### Success Criteria

- [ ] All 5 email regex patterns updated in JSON schema
- [ ] JSON changes documented for manual review
- [ ] Database verification confirms no changes (already correct)
- [ ] All 567 tests still passing (no regression)

---

## Implementation Order

1. **Pre-Migration Data Validation (Task 2 only)**
   - Run 4 validation queries
   - Clean up invalid data if found

2. **Update SQLModel Classes (Task 2)**
   - Update 4 models with check constraints
   
3. **Generate & Apply Migration (Task 2)**
   ```bash
   cd backend
   source .venv/bin/activate
   alembic revision --autogenerate -m "add_missing_check_constraints_task2"
   # Review & clean migration (remove unrelated changes)
   alembic upgrade head
   ```

4. **Create Test Suite (Task 2)**
   - Create `test_check_constraints_task2.py` with 12 tests
   - Run: `pytest tests/test_check_constraints_task2.py -v`

5. **Update JSON Schema (Task 3)**
   - Edit `pilot-db-schema-v2.6h.json`
   - Replace simple email regex with strict regex (5 constraints)

6. **Run Regression Tests**
   ```bash
   pytest tests/ --ignore=tests/integration -v 2>&1 | grep passed | tail -1
   # Expected: 567 passed (555 baseline + 12 new)
   ```

7. **Update Documentation**
   - Mark Tasks 2 & 3 complete in `phase-4.6-db-schema-sync-2-plan.md`

---

## Final Success Criteria

**MUST COMPLETE ALL BEFORE MARKING PHASE 1 AS DONE:**

### For Task 2 (MIGRATION):
- [ ] Pre-migration data validation completed (0 violations)
- [ ] 4 SQLModel classes updated with check constraints
- [ ] Alembic migration created and applied
- [ ] All 12 new tests written and passing
- [ ] Database verification confirms all 4 constraints active

### For Task 3 (JSON_UPDATE):
- [ ] SQL dump reviewed for correct email regex patterns
- [ ] JSON schema updated (5 email constraints)
- [ ] JSON changes documented for manual review
- [ ] Database verification confirms no changes (already correct)
- [ ] All 567 tests still passing (no regression)

### For Phase 1 Overall:
- [ ] **All 567 tests passing** (555 baseline + 12 new = 100%)
- [ ] **Zero regression** - All existing tests maintained
- [ ] Migration rollback tested
- [ ] Project plan document updated with completion status
- [ ] JSON changes reviewed by founder (Task 3)

---

## Key Files

### Models to Update (Task 2)
- `backend/app/models/core.py` - User, TenantUserInvite
- `backend/app/models/crm.py` - Customer, ContactPortalInvite

### JSON Schema (Task 3)
- `dev-docs/db-design/pilot-db-schema-v2.6h.json`

### Test References
- `backend/tests/test_discount_version_task1.py` - Pattern reference
- `backend/tests/conftest.py` - Test fixtures

---

## Notes

- **Virtual Environment Required:** All Python/pytest commands use `source .venv/bin/activate`
- **Use `session.exec()` not `session.query()`** to avoid deprecation warnings
- **Use `text()` for raw SQL** in tests to avoid SQLAlchemy errors
- **Pre-migration validation is CRITICAL** for Task 2 - don't skip it
- **Task 3 is documentation only** - no database changes, just JSON updates
- **Current test baseline:** 555 non-integration tests passing

---

**Ready to Begin Tasks 2 & 3!** 🚀
