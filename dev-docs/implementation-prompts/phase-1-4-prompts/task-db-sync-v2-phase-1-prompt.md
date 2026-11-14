# Task Phase 1: Critical Foundations - DB Sync v2 (3 Tasks)

**Reference:** `dev-docs/analysis/phase-4.6-db-schema-sync-2-plan.md` - Phase 1, Tasks 1-3
**Authority (Dual Master):**
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - Golden Master JSON
- `dev-docs/db-design/aevofab-db-schema-dump-phase-4.6.sql` - Production SQL Dump
**Type:** Phase 1 - Critical Foundations
**Priority:** HIGH / CRITICAL
**Change Type:** MIGRATION (Tasks 1 & 2) + JSON_UPDATE (Task 3)

---

## Context

This is **Phase 4.6 - DB Sync v#2**, a follow-up reconciliation after completing Phase 4.5. A forensic comparison between the production SQL dump and the Golden Master JSON revealed new inconsistencies. Phase 1 focuses on critical foundations that must be added to the physical database before Phase 4.5 work is lost.

**Key Principle:** This is about **reconciliation and documentation**, not new features. Phase 1 includes actual database migrations (Tasks 1 & 2) and JSON documentation updates (Task 3).

---

## What Was Completed in Phase 4.5

**Phase 4.5 Status:** ✅ COMPLETE (March 30 - April 1, 2026)
- ✅ 572/572 tests passing (100%)
- ✅ 100% alignment between physical database and Golden Master JSON achieved
- ✅ All unique, check, and temporal exclusion constraints implemented
- ✅ All 293 triggers verified and functional

**Current Baseline:** 572/572 tests passing (100%)

**See:** `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` for full Phase 4.5 history

---

## Current Tasks: Phase 1 - Critical Foundations (3 Tasks)

**Effort:** 2-3 days total
**Gap Reference:** Phase 4.6 Analysis - Missing Tables & Constraints
**Change Type:** MIGRATION (Tasks 1 & 2) + JSON_UPDATE (Task 3)

Phase 1 addresses critical gaps where the JSON schema includes production tables and check constraints that do not exist in the physical database. These must be added to prevent breaking discount versioning features and ensure data integrity.

---

## ⚠️ BEFORE YOU START - Establish Regression Baseline

**CRITICAL:** Capture the current test baseline BEFORE making ANY changes.

### Step 1: Activate Virtual Environment

```bash
cd backend
source .venv/bin/activate
```

### Step 2: Run ALL Tests (Current Baseline)

```bash
# Run full test suite
pytest tests/ -v

# Concise output
pytest tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

**Record the output:** `572/572 tests passing` (Phase 4.6 baseline)

### Step 3: Document Your Baseline

**Write down this number before proceeding:**
- Baseline: `572/572` passing

**This is your regression checkpoint. ALL these tests MUST still pass after your work.**

---

## Task 1: Add Missing `discount_version` Table (JSON → SQL)

**Effort:** 1 day
**Priority:** HIGH
**Change Type:** MIGRATION

### What Needs to Be Fixed

| # | Component | Issue | Direction | Complexity |
|---|-----------|-------|-----------|------------|
| **1** | `discount_version` | Complete table missing from physical database | JSON→SQL | MEDIUM |

### Problem

The `discount_version` table is fully defined in the JSON schema but is **completely missing** from the physical database. This will break any discount versioning features.

### SQLModel Implementation

**File:** `backend/app/models/catalog.py`

```python
# Add to catalog.py

from sqlalchemy import Column, Integer, CheckConstraint, ExcludeConstraint
from sqlalchemy.dialects.postgresql import TSTZRANGE
from core.db import AwareDatetime
from app.models.mixins import TenantIsolatedMixin

class DiscountVersion(TenantIsolatedMixin, SQLModel, table=True):
    """
    Discount Version - Temporal versioning for discount changes
    
    Tracks historical changes to discount values with non-overlapping time periods.
    Uses temporal exclusion constraint to prevent concurrent discount definitions.
    """
    __tablename__ = "discount_version"
    __table_args__ = (
        # Temporal exclusion constraint - prevents overlapping periods for same discount
        ExcludeConstraint(
            ('discount_id', '='),
            ('valid_period', '&&'),
            name='discount_version_no_overlap',
            using='gist'
        ),
        # Check constraint - ensure either value_cents OR percentage_bps is set
        CheckConstraint(
            "(discount_type = 'fixed' AND value_cents IS NOT NULL AND percentage_bps IS NULL) OR "
            "(discount_type = 'percentage' AND percentage_bps IS NOT NULL AND value_cents IS NULL)",
            name='discount_version_type_value_check'
        ),
        # Check constraint - validate discount type
        CheckConstraint(
            "discount_type IN ('fixed', 'percentage')",
            name='discount_version_type_check'
        ),
    )
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    discount_id: uuid.UUID = Field(foreign_key="discount.id", nullable=False, index=True)
    valid_period: str = Field(sa_column=Column(TSTZRANGE, nullable=False))
    discount_type: str = Field(nullable=False)  # 'fixed' or 'percentage'
    value_cents: int | None = Field(default=None)
    percentage_bps: int | None = Field(default=None)  # basis points (1% = 100 bps)
    recorded_at: AwareDatetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False),
        default_factory=lambda: datetime.now(timezone.utc)
    )
```

### Migration SQL

**Generate Migration:**
```bash
cd backend
source .venv/bin/activate
alembic revision --autogenerate -m "add_discount_version_table_task1"
```

**Expected Migration Content:**
```sql
-- Create discount_version table
CREATE TABLE discount_version (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenant(id),
    discount_id UUID NOT NULL REFERENCES discount(id),
    valid_period TSTZRANGE NOT NULL,
    discount_type TEXT NOT NULL,
    value_cents INTEGER,
    percentage_bps INTEGER,
    recorded_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Temporal exclusion constraint
    CONSTRAINT discount_version_no_overlap 
        EXCLUDE USING gist (discount_id WITH =, valid_period WITH &&),
    
    -- Type validation
    CONSTRAINT discount_version_type_check 
        CHECK (discount_type IN ('fixed', 'percentage')),
    
    -- Value validation
    CONSTRAINT discount_version_type_value_check 
        CHECK (
            (discount_type = 'fixed' AND value_cents IS NOT NULL AND percentage_bps IS NULL) OR
            (discount_type = 'percentage' AND percentage_bps IS NOT NULL AND value_cents IS NULL)
        )
);

-- Create indexes
CREATE INDEX ix_discount_version_discount_id ON discount_version(discount_id);
CREATE INDEX ix_discount_version_tenant_id ON discount_version(tenant_id);

-- Add standard triggers
CREATE TRIGGER trg_discount_version_set_updated_at
    BEFORE UPDATE ON discount_version
    FOR EACH ROW
    EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_discount_version_guard_created_immutable
    BEFORE UPDATE ON discount_version
    FOR EACH ROW
    EXECUTE FUNCTION guard_created_fields_immutable();

CREATE TRIGGER audit_discount_version_changes
    AFTER INSERT OR UPDATE OR DELETE ON discount_version
    FOR EACH ROW
    EXECUTE FUNCTION audit.log_changes();
```

### Database Verification Query

```sql
-- Verify table exists
SELECT tablename FROM pg_tables 
WHERE schemaname = 'public' AND tablename = 'discount_version';

-- Verify temporal exclusion constraint
SELECT conname, contype, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'discount_version'::regclass
  AND conname = 'discount_version_no_overlap';

-- Verify all triggers are active
SELECT tgname, tgenabled
FROM pg_trigger
WHERE tgrelid = 'discount_version'::regclass
  AND tgname IN (
    'trg_discount_version_set_updated_at',
    'trg_discount_version_guard_created_immutable',
    'audit_discount_version_changes'
  );
```

### Test Coverage

**Create:** `backend/tests/test_discount_version_task1.py`

**Minimum 10 Tests Required:**

```python
"""
Test Suite: Phase 4.6 Task 1 - Discount Version Table
Tests discount versioning with temporal exclusion constraints
"""
import pytest
import uuid
from datetime import datetime, timezone
from sqlmodel import Session
from sqlalchemy.exc import IntegrityError

from app.models.catalog import DiscountVersion, Discount


class TestDiscountVersionTable:
    """Test discount_version table exists and has correct structure"""
    
    def test_discount_version_table_exists(self, session: Session):
        """Verify discount_version table was created"""
        result = session.execute(
            "SELECT tablename FROM pg_tables "
            "WHERE schemaname = 'public' AND tablename = 'discount_version'"
        )
        assert result.scalar() == 'discount_version'
    
    def test_discount_version_basic_insert(self, session: Session, test_tenant, test_discount):
        """Valid discount version should be created"""
        version = DiscountVersion(
            tenant_id=test_tenant.id,
            discount_id=test_discount.id,
            valid_period='[2026-01-01,2026-12-31)',
            discount_type='fixed',
            value_cents=1000,
            recorded_at=datetime.now(timezone.utc)
        )
        session.add(version)
        session.commit()
        
        result = session.query(DiscountVersion).filter(
            DiscountVersion.id == version.id
        ).first()
        assert result is not None
        assert result.value_cents == 1000


class TestDiscountVersionTemporalExclusion:
    """Test temporal exclusion constraint prevents overlapping periods"""
    
    def test_non_overlapping_periods_allowed(self, session: Session, test_tenant, test_discount):
        """Non-overlapping periods for same discount should be allowed"""
        version1 = DiscountVersion(
            tenant_id=test_tenant.id,
            discount_id=test_discount.id,
            valid_period='[2026-01-01,2026-06-30)',
            discount_type='fixed',
            value_cents=1000,
            recorded_at=datetime.now(timezone.utc)
        )
        version2 = DiscountVersion(
            tenant_id=test_tenant.id,
            discount_id=test_discount.id,
            valid_period='[2026-07-01,2026-12-31)',
            discount_type='fixed',
            value_cents=1500,
            recorded_at=datetime.now(timezone.utc)
        )
        session.add(version1)
        session.add(version2)
        session.commit()
        
        count = session.query(DiscountVersion).filter(
            DiscountVersion.discount_id == test_discount.id
        ).count()
        assert count == 2
    
    def test_overlapping_periods_rejected(self, session: Session, test_tenant, test_discount):
        """Overlapping periods for same discount should be rejected"""
        version1 = DiscountVersion(
            tenant_id=test_tenant.id,
            discount_id=test_discount.id,
            valid_period='[2026-01-01,2026-12-31)',
            discount_type='fixed',
            value_cents=1000,
            recorded_at=datetime.now(timezone.utc)
        )
        session.add(version1)
        session.commit()
        
        # Try to add overlapping period
        version2 = DiscountVersion(
            tenant_id=test_tenant.id,
            discount_id=test_discount.id,
            valid_period='[2026-06-01,2027-06-30)',  # Overlaps with version1
            discount_type='fixed',
            value_cents=1500,
            recorded_at=datetime.now(timezone.utc)
        )
        session.add(version2)
        
        with pytest.raises(IntegrityError) as exc_info:
            session.commit()
        assert 'discount_version_no_overlap' in str(exc_info.value)


class TestDiscountVersionTypeValidation:
    """Test discount type and value validation"""
    
    def test_fixed_discount_requires_value_cents(self, session: Session, test_tenant, test_discount):
        """Fixed discount must have value_cents, not percentage_bps"""
        version = DiscountVersion(
            tenant_id=test_tenant.id,
            discount_id=test_discount.id,
            valid_period='[2026-01-01,2026-12-31)',
            discount_type='fixed',
            value_cents=1000,
            percentage_bps=None,
            recorded_at=datetime.now(timezone.utc)
        )
        session.add(version)
        session.commit()
        assert version.id is not None
    
    def test_percentage_discount_requires_percentage_bps(self, session: Session, test_tenant, test_discount):
        """Percentage discount must have percentage_bps, not value_cents"""
        version = DiscountVersion(
            tenant_id=test_tenant.id,
            discount_id=test_discount.id,
            valid_period='[2026-01-01,2026-12-31)',
            discount_type='percentage',
            value_cents=None,
            percentage_bps=1000,  # 10%
            recorded_at=datetime.now(timezone.utc)
        )
        session.add(version)
        session.commit()
        assert version.id is not None
    
    def test_fixed_discount_with_percentage_rejected(self, session: Session, test_tenant, test_discount):
        """Fixed discount with percentage_bps should be rejected"""
        version = DiscountVersion(
            tenant_id=test_tenant.id,
            discount_id=test_discount.id,
            valid_period='[2026-01-01,2026-12-31)',
            discount_type='fixed',
            value_cents=None,
            percentage_bps=1000,
            recorded_at=datetime.now(timezone.utc)
        )
        session.add(version)
        
        with pytest.raises(IntegrityError) as exc_info:
            session.commit()
        assert 'discount_version_type_value_check' in str(exc_info.value)
    
    def test_invalid_discount_type_rejected(self, session: Session, test_tenant, test_discount):
        """Invalid discount type should be rejected"""
        version = DiscountVersion(
            tenant_id=test_tenant.id,
            discount_id=test_discount.id,
            valid_period='[2026-01-01,2026-12-31)',
            discount_type='invalid',
            value_cents=1000,
            recorded_at=datetime.now(timezone.utc)
        )
        session.add(version)
        
        with pytest.raises(IntegrityError) as exc_info:
            session.commit()
        assert 'discount_version_type_check' in str(exc_info.value)


class TestDiscountVersionAuditLogging:
    """Test audit logging trigger is active"""
    
    def test_discount_version_changes_logged(self, session: Session, test_tenant, test_discount):
        """Discount version changes should be logged to audit table"""
        version = DiscountVersion(
            tenant_id=test_tenant.id,
            discount_id=test_discount.id,
            valid_period='[2026-01-01,2026-12-31)',
            discount_type='fixed',
            value_cents=1000,
            recorded_at=datetime.now(timezone.utc)
        )
        session.add(version)
        session.commit()
        
        # Verify audit log entry
        result = session.execute(
            "SELECT operation FROM audit.change_log "
            "WHERE table_name = 'discount_version' AND record_id = :id",
            {"id": str(version.id)}
        )
        assert result.scalar() == 'INSERT'
```

**Note:** You'll need to add a `test_discount` fixture to `conftest.py` if it doesn't exist.

---

## Task 2: Add Missing Check Constraints (4 Constraints) (JSON → SQL)

**Effort:** 0.5 days
**Priority:** HIGH
**Change Type:** MIGRATION

### What Needs to Be Fixed

| # | Component | Issue | Direction | Complexity |
|---|-----------|-------|-----------|------------|
| **1** | `user.platform_role_code` | Platform MFA required check missing | JSON→SQL | LOW |
| **2** | `contact_portal_invite.invite_email` | Email format validation missing | JSON→SQL | LOW |
| **3** | `customer.email` | Email format validation missing | JSON→SQL | LOW |
| **4** | `tenant_user_invite.email` | Email format validation missing | JSON→SQL | LOW |

### Problem

Four check constraints are defined in the JSON schema but **not enforced** in the physical database. This creates data quality risks.

### Pre-Migration Data Validation

**CRITICAL: Run these queries BEFORE creating the migration to identify invalid data:**

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

```python
from sqlalchemy import CheckConstraint

class User(TenantIsolatedMixin, SQLModel, table=True):
    __tablename__ = "user"
    __table_args__ = (
        # ... existing constraints ...
        
        # Platform users must have MFA enabled
        CheckConstraint(
            "platform_role_code IS NULL OR "
            "(platform_role_code IN ('staff', 'superadmin') AND is_mfa_enabled = true)",
            name='user_platform_mfa_required_chk'
        ),
    )
    # ... rest of model ...
```

#### 2. Update ContactPortalInvite Model

**File:** `backend/app/models/crm.py`

```python
class ContactPortalInvite(TenantIsolatedMixin, SQLModel, table=True):
    __tablename__ = "contact_portal_invite"
    __table_args__ = (
        # ... existing constraints ...
        
        # Email format validation
        CheckConstraint(
            "invite_email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'",
            name='contact_portal_invite_email_chk'
        ),
    )
    # ... rest of model ...
```

#### 3. Update Customer Model

**File:** `backend/app/models/crm.py`

```python
class Customer(TenantIsolatedMixin, SQLModel, table=True):
    __tablename__ = "customer"
    __table_args__ = (
        # ... existing constraints ...
        
        # Email format validation (nullable)
        CheckConstraint(
            "email IS NULL OR "
            "email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'",
            name='customer_email_format_chk'
        ),
    )
    # ... rest of model ...
```

#### 4. Update TenantUserInvite Model

**File:** `backend/app/models/core.py`

```python
class TenantUserInvite(TenantIsolatedMixin, SQLModel, table=True):
    __tablename__ = "tenant_user_invite"
    __table_args__ = (
        # ... existing constraints ...
        
        # Email format validation
        CheckConstraint(
            "email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'",
            name='tenant_user_invite_email_format_chk'
        ),
    )
    # ... rest of model ...
```

### Migration SQL

**Generate Migration:**
```bash
cd backend
source .venv/bin/activate
alembic revision --autogenerate -m "add_missing_check_constraints_task2"
```

**Verify Migration Contains:**
```sql
-- Add constraint 1: Platform MFA required
ALTER TABLE "user"
ADD CONSTRAINT user_platform_mfa_required_chk
CHECK (
    platform_role_code IS NULL OR 
    (platform_role_code IN ('staff', 'superadmin') AND is_mfa_enabled = true)
);

-- Add constraint 2: Contact portal invite email format
ALTER TABLE contact_portal_invite
ADD CONSTRAINT contact_portal_invite_email_chk
CHECK (invite_email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$');

-- Add constraint 3: Customer email format (nullable)
ALTER TABLE customer
ADD CONSTRAINT customer_email_format_chk
CHECK (
    email IS NULL OR 
    email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
);

-- Add constraint 4: Tenant user invite email format
ALTER TABLE tenant_user_invite
ADD CONSTRAINT tenant_user_invite_email_format_chk
CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$');
```

### Database Verification Query

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

### Test Coverage

**Create:** `backend/tests/test_check_constraints_task2.py`

**Minimum 12 Tests Required:**

```python
"""
Test Suite: Phase 4.6 Task 2 - Missing Check Constraints
Tests platform MFA and email format validation constraints
"""
import pytest
from sqlmodel import Session
from sqlalchemy.exc import IntegrityError

from app.models.core import User, TenantUserInvite
from app.models.crm import Customer, ContactPortalInvite


class TestPlatformMFAConstraint:
    """Test user_platform_mfa_required_chk constraint"""
    
    def test_staff_user_with_mfa_allowed(self, session: Session, test_tenant):
        """Staff user with MFA enabled should be allowed"""
        user = User(
            tenant_id=test_tenant.id,
            email="staff@example.com",
            platform_role_code="staff",
            is_mfa_enabled=True
        )
        session.add(user)
        session.commit()
        assert user.id is not None
    
    def test_staff_user_without_mfa_rejected(self, session: Session, test_tenant):
        """Staff user without MFA should be rejected"""
        user = User(
            tenant_id=test_tenant.id,
            email="staff@example.com",
            platform_role_code="staff",
            is_mfa_enabled=False
        )
        session.add(user)
        
        with pytest.raises(IntegrityError) as exc_info:
            session.commit()
        assert 'user_platform_mfa_required_chk' in str(exc_info.value)
    
    def test_regular_user_without_mfa_allowed(self, session: Session, test_tenant):
        """Regular user (no platform role) without MFA should be allowed"""
        user = User(
            tenant_id=test_tenant.id,
            email="user@example.com",
            platform_role_code=None,
            is_mfa_enabled=False
        )
        session.add(user)
        session.commit()
        assert user.id is not None


class TestContactPortalInviteEmailConstraint:
    """Test contact_portal_invite_email_chk constraint"""
    
    def test_valid_email_allowed(self, session: Session, test_tenant, test_contact):
        """Valid email format should be allowed"""
        invite = ContactPortalInvite(
            tenant_id=test_tenant.id,
            contact_id=test_contact.id,
            invite_email="valid@example.com"
        )
        session.add(invite)
        session.commit()
        assert invite.id is not None
    
    def test_invalid_email_rejected(self, session: Session, test_tenant, test_contact):
        """Invalid email format should be rejected"""
        invite = ContactPortalInvite(
            tenant_id=test_tenant.id,
            contact_id=test_contact.id,
            invite_email="invalid-email"
        )
        session.add(invite)
        
        with pytest.raises(IntegrityError) as exc_info:
            session.commit()
        assert 'contact_portal_invite_email_chk' in str(exc_info.value)
    
    def test_email_missing_domain_rejected(self, session: Session, test_tenant, test_contact):
        """Email without proper domain should be rejected"""
        invite = ContactPortalInvite(
            tenant_id=test_tenant.id,
            contact_id=test_contact.id,
            invite_email="user@"
        )
        session.add(invite)
        
        with pytest.raises(IntegrityError) as exc_info:
            session.commit()
        assert 'contact_portal_invite_email_chk' in str(exc_info.value)


class TestCustomerEmailConstraint:
    """Test customer_email_format_chk constraint"""
    
    def test_valid_email_allowed(self, session: Session, test_tenant):
        """Valid email format should be allowed"""
        customer = Customer(
            tenant_id=test_tenant.id,
            type="residential",
            email="customer@example.com"
        )
        session.add(customer)
        session.commit()
        assert customer.id is not None
    
    def test_null_email_allowed(self, session: Session, test_tenant):
        """NULL email should be allowed (nullable field)"""
        customer = Customer(
            tenant_id=test_tenant.id,
            type="residential",
            email=None
        )
        session.add(customer)
        session.commit()
        assert customer.id is not None
    
    def test_invalid_email_rejected(self, session: Session, test_tenant):
        """Invalid email format should be rejected"""
        customer = Customer(
            tenant_id=test_tenant.id,
            type="residential",
            email="not-an-email"
        )
        session.add(customer)
        
        with pytest.raises(IntegrityError) as exc_info:
            session.commit()
        assert 'customer_email_format_chk' in str(exc_info.value)


class TestTenantUserInviteEmailConstraint:
    """Test tenant_user_invite_email_format_chk constraint"""
    
    def test_valid_email_allowed(self, session: Session, test_tenant, test_user):
        """Valid email format should be allowed"""
        invite = TenantUserInvite(
            tenant_id=test_tenant.id,
            inviter_user_id=test_user.id,
            email="newuser@example.com"
        )
        session.add(invite)
        session.commit()
        assert invite.id is not None
    
    def test_invalid_email_rejected(self, session: Session, test_tenant, test_user):
        """Invalid email format should be rejected"""
        invite = TenantUserInvite(
            tenant_id=test_tenant.id,
            inviter_user_id=test_user.id,
            email="bad@email"
        )
        session.add(invite)
        
        with pytest.raises(IntegrityError) as exc_info:
            session.commit()
        assert 'tenant_user_invite_email_format_chk' in str(exc_info.value)
    
    def test_complex_email_allowed(self, session: Session, test_tenant, test_user):
        """Complex but valid email should be allowed"""
        invite = TenantUserInvite(
            tenant_id=test_tenant.id,
            inviter_user_id=test_user.id,
            email="user+tag@sub.example.co.uk"
        )
        session.add(invite)
        session.commit()
        assert invite.id is not None
```

---

## Task 3: Update Email Regex to Match SQL Standard (SQL → JSON)

**Effort:** 0.5 days
**Priority:** MEDIUM
**Change Type:** JSON_UPDATE

### What Needs to Be Fixed

| # | Component | Issue | Direction | Complexity |
|---|-----------|-------|-----------|------------|
| **1** | Email regex patterns in JSON | Simple regex vs production-grade regex | SQL→JSON | LOW |

### Problem

The JSON schema uses a **simple email regex** (`^[^@\s]+@[^@\s]+\.[^@\s]+$`), but the SQL database uses a **stricter, production-grade regex** (`^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$`).

**Analysis:**
- **Simple Regex (JSON):** Allows `user@` (no domain), `user@.com` (no subdomain), `user name@test.com` (spaces before @)
- **Strict Regex (SQL):** Enforces real email structure, blocks common typos

**Decision:** Adopt the **SQL standard** (stricter is safer for production data quality).

### SQL Database Reality (What's Actually Working)

```sql
-- Production SQL (from phase-4.6 dump)
-- Already in database from Phase 4.5

ALTER TABLE "user"
ADD CONSTRAINT user_email_chk
CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$');

ALTER TABLE user_endpoint
ADD CONSTRAINT user_endpoint_value_email_chk
CHECK (
    endpoint_type != 'email' OR
    value ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
);

-- Similar for: customer, contact_portal_invite, tenant_user_invite
```

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

**Affected Constraints (Update ALL):**
1. `user.email` - `user_email_chk`
2. `user_endpoint.value` - `user_endpoint_value_email_chk`
3. `customer.email` - `customer_email_format_chk`
4. `contact_portal_invite.invite_email` - `contact_portal_invite_email_chk`
5. `tenant_user_invite.email` - `tenant_user_invite_email_format_chk`

**⚠️ IMPORTANT: NO DATABASE MIGRATION NEEDED**
- The database already has the correct regex (from Phase 4.5)
- This is a JSON documentation update only
- No `alembic revision` required
- Verification is comparing JSON to SQL dump

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

### JSON Change Tracking

## JSON Schema Changes for Task 3

**File:** `dev-docs/db-design/pilot-db-schema-v2.6h.json`

### Changes Made:

1. **Constraint: `user_email_chk`**
   - **Table:** `user`
   - **Before:** `email ~* '^[^@\s]+@[^@\s]+\.[^@\s]+$'`
   - **After:** `email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'`
   - **Reason:** Standardize on production SQL strict regex

2. **Constraint: `user_endpoint_value_email_chk`**
   - **Table:** `user_endpoint`
   - **Before:** `value ~* '^[^@\s]+@[^@\s]+\.[^@\s]+$'`
   - **After:** `value ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'`
   - **Reason:** Standardize on production SQL strict regex

3. **Constraint: `customer_email_format_chk`**
   - **Table:** `customer`
   - **Before:** `email ~* '^[^@\s]+@[^@\s]+\.[^@\s]+$'`
   - **After:** `email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'`
   - **Reason:** Standardize on production SQL strict regex

4. **Constraint: `contact_portal_invite_email_chk`**
   - **Table:** `contact_portal_invite`
   - **Before:** `invite_email ~* '^[^@\s]+@[^@\s]+\.[^@\s]+$'`
   - **After:** `invite_email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'`
   - **Reason:** Standardize on production SQL strict regex

5. **Constraint: `tenant_user_invite_email_format_chk`**
   - **Table:** `tenant_user_invite`
   - **Before:** `email ~* '^[^@\s]+@[^@\s]+\.[^@\s]+$'`
   - **After:** `email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'`
   - **Reason:** Standardize on production SQL strict regex

### Verification:

- [ ] All JSON email regex patterns align with `aevofab-db-schema-dump-phase-4.6.sql`
- [ ] No functional database changes made (JSON doc only)
- [ ] All 572 tests still passing (no regression)

**⚠️ USER REVIEW REQUIRED:**
The founder will manually review these JSON changes against the SQL dump to confirm accuracy.

---

## Implementation Order

### For Tasks 1 & 2 (MIGRATION Tasks):

1. **✅ Establish Regression Baseline** (572/572 tests)
2. **Pre-Migration Data Validation** (Task 2 only)
   - Run validation queries
   - Clean up invalid data if found
3. **Update SQLModel Classes**
   - Task 1: Add `DiscountVersion` model
   - Task 2: Update 4 existing models with check constraints
4. **Generate Alembic Migrations**
   ```bash
   cd backend
   source .venv/bin/activate
   alembic revision --autogenerate -m "add_discount_version_table_task1"
   alembic revision --autogenerate -m "add_missing_check_constraints_task2"
   ```
5. **Review & Enhance Migrations**
   - Verify all changes captured
   - Add pre-migration checks
   - Ensure downgrade() is complete
6. **Apply Migrations**
   ```bash
   alembic upgrade head
   ```
7. **Create Test Suites**
   - `backend/tests/test_discount_version_task1.py` - 10 tests
   - `backend/tests/test_check_constraints_task2.py` - 12 tests
   - Use `session.query()` NOT `session.exec()` (avoid deprecation warnings)
8. **Run New Tests**
   ```bash
   pytest tests/test_discount_version_task1.py -v
   pytest tests/test_check_constraints_task2.py -v
   ```
9. **Run Regression Tests** (see "After You Complete" section)
10. **Update Documentation**

### For Task 3 (JSON_UPDATE Task):

1. **✅ Establish Regression Baseline** (572/572 tests)
2. **Review SQL Dump**
   - Read `dev-docs/db-design/aevofab-db-schema-dump-phase-4.6.sql`
   - Locate email constraint definitions
3. **Update JSON Schema**
   - Modify `dev-docs/db-design/pilot-db-schema-v2.6h.json`
   - Replace simple email regex with strict regex (5 constraints)
4. **Document JSON Changes** (see "JSON Change Tracking" section above)
5. **Verify Database (No Changes Expected)**
   ```sql
   SELECT conname, pg_get_constraintdef(oid)
   FROM pg_constraint
   WHERE conname LIKE '%email%' AND contype = 'c';
   ```
6. **Run Existing Tests (Verify No Regression)**
   ```bash
   pytest tests/ -v
   # Expected: 572/572 passing (no change)
   ```
7. **Update Documentation**

---

## Test Requirements

**⚠️ ZERO REGRESSION POLICY:**
- **ALL 572 existing tests MUST still pass**
- **New tests (Tasks 1 & 2) MUST pass**
- **Target: 100% pass rate**

### New Test Count Summary

**Task 1:** 10 tests minimum (discount_version table)
**Task 2:** 12 tests minimum (4 check constraints × 3 tests each)
**Task 3:** No new tests (JSON documentation only)

**Total New Tests:** 22 tests
**Expected Final Count:** 594/594 tests passing (100%)

---

## 🎯 AFTER YOU COMPLETE - Verify No Regressions

**CRITICAL:** After all work is complete, verify the baseline.

### Step 1: Activate Virtual Environment

```bash
cd backend
source .venv/bin/activate
```

### Step 2: Run Full Test Suite

```bash
# Run ALL tests
pytest tests/ -v

# Concise output
pytest tests/ -v 2>&1 | grep -E "(passed|failed|===)" | tail -5
```

**Expected:**
- **For Phase 1 Complete:** `594 passed` (572 baseline + 22 new tests)

### Step 3: Verify 100% Pass Rate

**If ANY tests fail:**
1. Identify failing tests
2. Determine if new or existing tests
3. Fix ALL failures before proceeding
4. Re-run until 100% pass rate

---

## Documentation Update

### Update Project Plan Document

**File to Update:** `dev-docs/analysis/phase-4.6-db-schema-sync-2-plan.md`

Find Phase 1, Tasks 1-3 and update with:

```markdown
## 🔍 Phase 1: Critical Foundations

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Timeline:** 2-3 days (actual: X days)
**Priority:** CRITICAL

### Task 1: Add Missing `discount_version` Table (JSON → SQL)

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Effort:** 1 day (actual: X days)
**Change Type:** MIGRATION

**Implementation Summary:**
- Modified: `backend/app/models/catalog.py`
- Migration: `YYYY_MM_DD_HHMM-[hash]_add_discount_version_table_task1.py`
- Test Suite: `test_discount_version_task1.py` - 10 tests ✅
- Final Results: 582/582 tests passing (100%)

**Key Changes:**
- ✅ Created `discount_version` table with temporal exclusion constraint
- ✅ Added check constraints for discount type validation
- ✅ Implemented 3 triggers (updated_at, immutability, audit)
- ✅ 10 comprehensive tests covering temporal exclusion

---

### Task 2: Add Missing Check Constraints (4 Constraints) (JSON → SQL)

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Effort:** 0.5 days (actual: X days)
**Change Type:** MIGRATION

**Implementation Summary:**
- Modified: `backend/app/models/core.py` (User, TenantUserInvite)
- Modified: `backend/app/models/crm.py` (Customer, ContactPortalInvite)
- Migration: `YYYY_MM_DD_HHMM-[hash]_add_missing_check_constraints_task2.py`
- Test Suite: `test_check_constraints_task2.py` - 12 tests ✅
- Final Results: 594/594 tests passing (100%)

**Key Changes:**
- ✅ Added `user_platform_mfa_required_chk` (platform staff must have MFA)
- ✅ Added `contact_portal_invite_email_chk` (email format validation)
- ✅ Added `customer_email_format_chk` (email format validation)
- ✅ Added `tenant_user_invite_email_format_chk` (email format validation)
- ✅ Pre-migration validation: 0 constraint violations found

---

### Task 3: Update Email Regex to Match SQL Standard (SQL → JSON)

**Status:** ✅ COMPLETE (YYYY-MM-DD)
**Effort:** 0.5 days (actual: X days)
**Change Type:** JSON_UPDATE

**Implementation Summary:**
- Updated: `pilot-db-schema-v2.6h.json`
- Changes: 5 email constraints updated with strict regex
- Database: No changes (already correct from Phase 4.5)
- Final Results: 594/594 tests passing (100% - no regression)

**Key Changes:**
- ✅ Replaced simple regex with strict production-grade regex
- ✅ Updated 5 email constraints in JSON schema
- ✅ Standardized on: `^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$`
- ✅ Database verification: All constraints already use strict regex
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING PHASE 1 AS DONE:**

### For Task 1 (MIGRATION):
- [ ] **Regression baseline captured** (572/572 tests)
- [ ] **DiscountVersion SQLModel created** in `catalog.py`
- [ ] **Temporal exclusion constraint** implemented
- [ ] **Check constraints** for discount type validation added
- [ ] **Alembic migration created** and applied
- [ ] **3 triggers verified** (updated_at, immutability, audit)
- [ ] **All 10 new tests written and passing**
- [ ] **Database verification query confirms** table and constraints active

### For Task 2 (MIGRATION):
- [ ] **Pre-migration data validation completed** (0 violations)
- [ ] **4 SQLModel classes updated** with check constraints
- [ ] **Alembic migration created** and applied
- [ ] **All 12 new tests written and passing**
- [ ] **Database verification query confirms** all 4 constraints active

### For Task 3 (JSON_UPDATE):
- [ ] **SQL dump reviewed** for correct email regex patterns
- [ ] **JSON schema updated** (5 email constraints)
- [ ] **JSON changes documented** for manual review
- [ ] **Database verification confirms** no changes (already correct)
- [ ] **ALL 594 tests still passing** (no regression)

### For Phase 1 Overall:
- [ ] **All 594 tests passing** (572 baseline + 22 new = 100%)
- [ ] **Zero regression** - All existing tests maintained
- [ ] **Use session.query() in tests** (not session.exec())
- [ ] **Migration rollback tested** (both migrations)
- [ ] **Project plan document updated** with completion status
- [ ] **JSON changes reviewed by founder** (Task 3)

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-4.6-db-schema-sync-2-plan.md` - **Phase 1 Details** ⭐
- `dev-docs/analysis/phase-4.6-db-schema-sync-2-analysis.md` - Forensic Analysis
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - **Golden Master JSON**
- `dev-docs/db-design/aevofab-db-schema-dump-phase-4.6.sql` - **Production SQL Dump**

### Backend Code
- `backend/app/models/catalog.py` - Add DiscountVersion (Task 1)
- `backend/app/models/core.py` - Update User, TenantUserInvite (Task 2)
- `backend/app/models/crm.py` - Update Customer, ContactPortalInvite (Task 2)

### Tests (Reference for Patterns)
- `backend/tests/test_unique_constraints_task8.py`
- `backend/tests/test_check_constraints_task9.py`
- `backend/tests/conftest.py` - Test fixtures

---

## Risk Assessment

### Task 1 Risks

**Data Migration Risk:** LOW
- New table, no existing data
- No migration of existing records needed

**Blocking Risk:** MEDIUM
- Other code may reference this table
- **Mitigation:** Search codebase for `discount_version` references

**Regression Risk:** LOW
- New table shouldn't affect existing functionality
- **Mitigation:** Maintain 572/572 baseline, test after migration

### Task 2 Risks

**Data Validation Risk:** MEDIUM
- Existing data might violate new constraints
- **Mitigation:** Run pre-migration validation queries, clean up violations

**Regression Risk:** LOW
- Constraints only enforce existing business rules
- **Mitigation:** Comprehensive test coverage (12 tests)

### Task 3 Risks

**JSON Documentation Risk:** LOW
- JSON changes might not perfectly match SQL reality
- **Mitigation:** Founder manually reviews all JSON changes against SQL dump

**Regression Risk:** NONE
- No database changes, documentation only
- **Mitigation:** Verify 594/594 tests still pass

---

## Notes

### Important Patterns to Follow
- **Virtual Environment Required:** All Python/pytest commands use `source .venv/bin/activate`
- **Deprecation Warnings:** Use `session.query()` not `session.exec()` in tests
- **Dual Master Strategy:** JSON is documentation authority, SQL dump is runtime authority
- **Zero Regression Policy:** All 572 existing tests MUST pass after changes

### Phase 4.6 Phase 1 Specific
- **Critical foundations** - don't skip these tasks
- **Database migrations required** for Tasks 1 & 2
- **JSON documentation only** for Task 3
- **Test consistency critical** - new tests must match existing patterns
- **Pre-migration validation essential** for Task 2 (check constraints)

### If You Get Stuck
- Check the SQL dump for exact production definitions
- Review completed Phase 4.5 tasks for patterns
- Use `postgres-local` MCP server to query database
- Verify JSON changes line-by-line against SQL dump (Task 3)
- Search for similar constraints in existing models

---

## Example Task Flow

### For Tasks 1 & 2 (MIGRATION Tasks):

```bash
# 1. Baseline
cd backend
source .venv/bin/activate
pytest tests/ -v 2>&1 | grep passed | tail -1
# Record: 572 passed

# 2. Pre-migration validation (Task 2 only)
# Run validation SQL queries to check for constraint violations

# 3. Update SQLModel classes
# Edit backend/app/models/catalog.py (Task 1)
# Edit backend/app/models/core.py and crm.py (Task 2)

# 4. Generate migrations
alembic revision --autogenerate -m "add_discount_version_table_task1"
alembic revision --autogenerate -m "add_missing_check_constraints_task2"

# 5. Review migrations
# Verify autogenerate captured all changes
# Add pre-migration checks if needed
# Ensure downgrade() is complete

# 6. Apply migrations
alembic upgrade head

# 7. Verify database changes
# Run database verification queries

# 8. Create test suites
# Create backend/tests/test_discount_version_task1.py (10 tests)
# Create backend/tests/test_check_constraints_task2.py (12 tests)

# 9. Run new tests
pytest tests/test_discount_version_task1.py -v
pytest tests/test_check_constraints_task2.py -v

# 10. Regression check
pytest tests/ -v 2>&1 | grep passed | tail -1
# Expected: 594 passed (572 + 22 new)

# 11. Rollback test
alembic downgrade -1
alembic upgrade head

# 12. Update docs
# Edit phase-4.6-db-schema-sync-2-plan.md
```

### For Task 3 (JSON_UPDATE Task):

```bash
# 1. Baseline
cd backend
source .venv/bin/activate
pytest tests/ -v 2>&1 | grep passed | tail -1
# Record: 594 passed (after Tasks 1 & 2)

# 2. Review SQL dump for email constraints
grep -A 5 "email.*CHECK" dev-docs/db-design/aevofab-db-schema-dump-phase-4.6.sql

# 3. Update JSON schema
# Edit dev-docs/db-design/pilot-db-schema-v2.6h.json
# Replace simple email regex with strict regex (5 constraints)

# 4. Document changes
# Create JSON change summary (see template above)

# 5. Verify database (no changes expected)
# Use postgres-local MCP to confirm constraints already correct

# 6. Regression check
pytest tests/ -v 2>&1 | grep passed | tail -1
# Expected: 594 passed (no change - documentation only)

# 7. Update docs
# Edit phase-4.6-db-schema-sync-2-plan.md
```

---

## Questions to Ask

**Before starting:**
1. Have I captured the 572/572 baseline?
2. For Task 2: Have I run pre-migration validation queries?
3. For Task 3: Have I located the correct email constraint definitions in SQL dump?
4. Do I understand the difference between MIGRATION and JSON_UPDATE tasks?

**During implementation:**
1. Am I using `session.query()` (not `session.exec()`) in tests?
2. For Task 3: Am I documenting all JSON changes for founder review?
3. Are my tests consistent with existing test patterns?
4. Have I verified database changes with SQL queries?

**After implementation:**
1. Do I have 100% test pass rate (594/594)?
2. For Task 3: Did baseline stay at 594/594 (no regression)?
3. For Tasks 1 & 2: Have I tested migration rollback?
4. Have I updated the project plan document?
5. For Task 3: Have I provided a clear change list for founder review?

---

**Ready to Begin Phase 1!** 🚀

### Phase 1 Task Checklist:

1. ✅ **Task 1: discount_version Table**
   - Capture baseline (572/572)
   - Update catalog.py with DiscountVersion model
   - Generate and apply migration
   - Create 10 comprehensive tests
   - Run regression tests (expect 582/582)

2. ✅ **Task 2: Missing Check Constraints**
   - Pre-migration validation (check for violations)
   - Update 4 models with check constraints
   - Generate and apply migration
   - Create 12 comprehensive tests
   - Run regression tests (expect 594/594)

3. ✅ **Task 3: Email Regex Alignment**
   - Review SQL dump for email constraints
   - Update JSON schema (5 constraints)
   - Document JSON changes for review
   - Verify database (no changes)
   - Run regression tests (expect 594/594)

4. 📚 **Update Documentation**
   - Mark Phase 1 complete in roadmap
   - Document all implementation details
   - Summarize test results

Remember: Phase 1 is **critical foundations** - these changes prevent production bugs and data quality issues. Don't skip the pre-migration validation for Task 2!
