# Task 9: Missing Check Constraints (Data Validation)

**Reference:** `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` - Task 9
**Authority:** `dev-docs/db-design/pilot-db-schema-v2.6h.json`
**Type:** Phase 3 - Data Integrity (Constraints)
**Status:** ✅ COMPLETE (April 1, 2026)

---

## Context

We're building AevoFab AI, an AI-powered SaaS platform for electrical contractors with voice-controlled quoting and QuickBooks integration. Following the 80/20 rule to reach MVP quickly.

This is a **Phase 3 data integrity task** to add database-level CHECK constraints that enforce business rules and data validation. This prevents application bugs from corrupting data by validating enums, formats, and business logic at the database level.

---

## Completed So Far

**Phase 1: Foundation (COMPLETE - March 30-31, 2026):**
- ✅ Task 1: Timezone enforcement (9 columns fixed)
- ✅ Task 2: Citext conversion for user email
- ✅ Task 3: QuickBooks identity rules on Customer table

**Phase 2: Functions & Triggers (COMPLETE - March 31, 2026):**
- ✅ Task 4: Missing PL/pgSQL functions (3 functions + 200 triggers)
- ✅ Task 5: Function naming standard compliance
- ✅ Task 6: Audit trigger coverage (85 audit triggers)
- ✅ Task 7: Operational trigger verification (293 total triggers)

**Phase 3: Data Integrity (PARTIAL):**
- ✅ Task 8: Missing unique constraints (4/4 complete - April 1, 2026)
- ✅ **Task 9: Missing check constraints (9/9 complete - April 1, 2026)**
- 📋 Task 10: Missing temporal exclusion constraints (not started)

**Test Results:** 490/490 tests passing (100%)
**See:** `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md`

---

## Current Task: Missing Check Constraints

**Priority:** HIGH (Data Quality Enforcement)  
**Effort:** 2 days  
**Gap Reference:** Analysis Section 3 - Missing Check Constraints

### Already Complete

✅ **Gap 6 (March 30, 2026):** `AuditEvent.actor_type` CHECK constraint
   ```sql
   CHECK (actor_type IN ('system', 'user', 'platform', 'external_webhook'))
   ```

### Missing Check Constraints (9+ Remaining)

The Golden Master JSON schema specifies CHECK constraints that are **missing entirely** from the physical database. Without these:
- Invalid email addresses can be stored (typos, malformed)
- Invalid enum values can corrupt data (typos, SQL injection attempts)
- Business rules can be violated (wrong customer types, invalid statuses)

---

## Requirements

### Critical Missing Constraints

#### 1. Email Format Validation (2 Tables)

**`user.email` Format Check:**
```sql
ALTER TABLE "user" 
ADD CONSTRAINT user_email_format_chk 
CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$');
```

**SQLModel Update:**
```python
# backend/app/models/core.py
from sqlalchemy import CheckConstraint

class User(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "user"
    __table_args__ = (
        CheckConstraint(
            "email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'",
            name='user_email_format_chk'
        ),
    )
    # ... fields ...
```

**`user_endpoint.value` Format Check (when channel='email'):**
```sql
ALTER TABLE user_endpoint 
ADD CONSTRAINT user_endpoint_email_format_chk 
CHECK (
  channel != 'email' OR 
  value ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
);
```

**SQLModel Update:**
```python
# backend/app/models/core.py
class UserEndpoint(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "user_endpoint"
    __table_args__ = (
        CheckConstraint(
            "channel != 'email' OR value ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'",
            name='user_endpoint_email_format_chk'
        ),
    )
    # ... fields ...
```

---

#### 2. Customer Type Enumeration

**Purpose:** Ensure QuickBooks sync only handles valid customer types

```sql
ALTER TABLE customer 
ADD CONSTRAINT customer_type_chk 
CHECK (type IN ('person', 'company'));
```

**SQLModel Update:**
```python
# backend/app/models/crm.py
class Customer(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "customer"
    __table_args__ = (
        CheckConstraint(
            "type IN ('person', 'company')",
            name='customer_type_chk'
        ),
    )
    # ... fields ...
```

---

#### 3. MFA Channel Validation

**Purpose:** Only email and SMS are supported for OTP delivery

```sql
ALTER TABLE auth_mfa_otp 
ADD CONSTRAINT auth_mfa_otp_channel_chk 
CHECK (channel IN ('email', 'sms'));
```

**SQLModel Update:**
```python
# backend/app/models/auth.py
class AuthMfaOtp(SQLModel, table=True):
    __tablename__ = "auth_mfa_otp"
    __table_args__ = (
        CheckConstraint(
            "channel IN ('email', 'sms')",
            name='auth_mfa_otp_channel_chk'
        ),
    )
    # ... fields ...
```

---

#### 4. Platform Role Validation

**Purpose:** Only 'staff' and 'superadmin' are valid platform roles

```sql
ALTER TABLE "user" 
ADD CONSTRAINT user_platform_role_chk 
CHECK (
  platform_role_code IS NULL OR 
  platform_role_code IN ('staff', 'superadmin')
);
```

**SQLModel Update:**
```python
# backend/app/models/core.py
class User(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "user"
    __table_args__ = (
        CheckConstraint(
            "platform_role_code IS NULL OR platform_role_code IN ('staff', 'superadmin')",
            name='user_platform_role_chk'
        ),
    )
    # ... fields ...
```

---

#### 5. Status Enumerations (Multiple Tables)

**NotificationOutbox Status:**
```sql
ALTER TABLE notification_outbox 
ADD CONSTRAINT notification_outbox_status_chk 
CHECK (status IN ('pending', 'sent', 'failed', 'cancelled'));
```

**SQLModel Update:**
```python
# backend/app/models/system.py
class NotificationOutbox(TenantIsolatedMixin, SQLModel, table=True):
    __tablename__ = "notification_outbox"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'sent', 'failed', 'cancelled')",
            name='notification_outbox_status_chk'
        ),
    )
    # ... fields ...
```

**WebhookDeliveryAttempt Status:**
```sql
ALTER TABLE webhook_delivery_attempt 
ADD CONSTRAINT webhook_delivery_attempt_status_chk 
CHECK (status IN ('pending', 'delivered', 'failed', 'retrying'));
```

**IntegrationSyncConflict Resolution:**
```sql
ALTER TABLE integration_sync_conflict 
ADD CONSTRAINT integration_sync_conflict_resolution_chk 
CHECK (
  resolution_strategy IS NULL OR 
  resolution_strategy IN ('accept_local', 'accept_remote', 'manual')
);
```

**ConnectorRunLog Status:**
```sql
ALTER TABLE connector_run_log 
ADD CONSTRAINT connector_run_log_status_chk 
CHECK (status IN ('running', 'completed', 'failed', 'cancelled'));
```

---

### Full List of Missing Check Constraints

Per the Golden Master analysis, the following tables need CHECK constraints:

1. ✅ ~~`audit_event.actor_type`~~ - **COMPLETE (Gap 6, March 30)**
2. 📋 `user.email` - Email format regex
3. 📋 `user_endpoint.value` - Email format when channel='email'
4. 📋 `customer.type` - Enum: person, company
5. 📋 `auth_mfa_otp.channel` - Enum: email, sms
6. 📋 `user.platform_role_code` - Enum: staff, superadmin (nullable)
7. 📋 `notification_outbox.status` - Enum: pending, sent, failed, cancelled
8. 📋 `webhook_delivery_attempt.status` - Enum: pending, delivered, failed, retrying
9. 📋 `integration_sync_conflict.resolution_strategy` - Enum: accept_local, accept_remote, manual (nullable)
10. 📋 `connector_run_log.status` - Enum: running, completed, failed, cancelled

**Additional constraints per Golden Master:** Review `pilot-db-schema-v2.6h.json` for complete list

---

## Implementation Steps

### 1. Pre-Migration Data Validation

**CRITICAL:** Validate existing data BEFORE applying constraints to prevent migration failures.

```sql
-- Find invalid email addresses in user table
SELECT id, email 
FROM "user" 
WHERE email !~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$';

-- Find invalid email endpoints
SELECT id, channel, value 
FROM user_endpoint 
WHERE channel = 'email' 
  AND value !~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$';

-- Find invalid customer types
SELECT id, type, display_name 
FROM customer 
WHERE type IS NOT NULL 
  AND type NOT IN ('person', 'company');

-- Find invalid MFA channels
SELECT id, channel 
FROM auth_mfa_otp 
WHERE channel NOT IN ('email', 'sms');

-- Find invalid platform roles
SELECT id, email, platform_role_code 
FROM "user" 
WHERE platform_role_code IS NOT NULL 
  AND platform_role_code NOT IN ('staff', 'superadmin');

-- Find invalid notification statuses
SELECT id, status 
FROM notification_outbox 
WHERE status NOT IN ('pending', 'sent', 'failed', 'cancelled');

-- Find invalid webhook statuses
SELECT id, status 
FROM webhook_delivery_attempt 
WHERE status NOT IN ('pending', 'delivered', 'failed', 'retrying');

-- Find invalid integration conflict resolutions
SELECT id, resolution_strategy 
FROM integration_sync_conflict 
WHERE resolution_strategy IS NOT NULL 
  AND resolution_strategy NOT IN ('accept_local', 'accept_remote', 'manual');

-- Find invalid connector run statuses
SELECT id, status 
FROM connector_run_log 
WHERE status NOT IN ('running', 'completed', 'failed', 'cancelled');
```

**If any invalid data found:** Clean it up manually BEFORE creating migration.

---

### 2. Update SQLModel Classes

**Files to Modify:**

1. `backend/app/models/core.py`
   - Add `user_email_format_chk` to User class
   - Add `user_platform_role_chk` to User class
   - Add `user_endpoint_email_format_chk` to UserEndpoint class

2. `backend/app/models/crm.py`
   - Add `customer_type_chk` to Customer class

3. `backend/app/models/auth.py`
   - Add `auth_mfa_otp_channel_chk` to AuthMfaOtp class

4. `backend/app/models/system.py`
   - Add `notification_outbox_status_chk` to NotificationOutbox class
   - Add `webhook_delivery_attempt_status_chk` to WebhookDeliveryAttempt class
   - Add `integration_sync_conflict_resolution_chk` to IntegrationSyncConflict class
   - Add `connector_run_log_status_chk` to ConnectorRunLog class

**Import Requirements:**
```python
from sqlalchemy import CheckConstraint
```

**Merging with Existing `__table_args__`:**
```python
# If table already has __table_args__ (e.g., UniqueConstraint):
class Customer(StandardAuditMixin, SQLModel, table=True):
    __tablename__ = "customer"
    __table_args__ = (
        UniqueConstraint('tenant_id', 'display_name', name='uq_customer_tenant_display_name'),
        CheckConstraint("type IN ('person', 'company')", name='customer_type_chk'),
    )
```

---

### 3. Generate Alembic Migration

```bash
cd backend
alembic revision --autogenerate -m "add_missing_check_constraints_task9"
```

**Review Generated Migration:**
- Verify all 9 CHECK constraints are present
- Ensure constraint names match Golden Master
- Confirm regex patterns use proper escaping

---

### 4. Apply Migration

```bash
alembic upgrade head
```

**Expected Output:**
```
INFO  [alembic.runtime.migration] Running upgrade XXXX -> YYYY, add_missing_check_constraints_task9
```

---

### 5. Create Test Suite

**File:** `backend/tests/test_check_constraints_task9.py`

**Test Coverage (Minimum 18 Tests):**

```python
"""
Test Suite: Phase 3 Task 9 - Missing Check Constraints
Tests data validation constraints from Golden Master v2.6h
"""
import pytest
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from app.models.core import User, UserEndpoint
from app.models.crm import Customer
from app.models.auth import AuthMfaOtp
from app.models.system import NotificationOutbox, WebhookDeliveryAttempt, IntegrationSyncConflict, ConnectorRunLog

class TestEmailFormatConstraints:
    """Email format validation using regex CHECK constraints"""
    
    def test_user_email_valid_format(self, session: Session, test_tenant):
        """Valid email addresses should be accepted"""
        user = User(
            email="valid.user@example.com",
            tenant_id=test_tenant.id,
            is_active=True
        )
        session.add(user)
        session.commit()
        assert user.id is not None
    
    def test_user_email_invalid_format(self, session: Session, test_tenant):
        """Invalid email addresses should be rejected"""
        user = User(
            email="invalid-email",  # Missing @domain
            tenant_id=test_tenant.id,
            is_active=True
        )
        session.add(user)
        with pytest.raises(IntegrityError, match="user_email_format_chk"):
            session.commit()
    
    def test_user_endpoint_email_valid(self, session: Session, test_user):
        """Valid email endpoints should be accepted"""
        endpoint = UserEndpoint(
            user_id=test_user.id,
            channel="email",
            value="test@example.com",
            is_verified=True,
            is_primary=True
        )
        session.add(endpoint)
        session.commit()
        assert endpoint.id is not None
    
    def test_user_endpoint_email_invalid(self, session: Session, test_user):
        """Invalid email endpoints should be rejected"""
        endpoint = UserEndpoint(
            user_id=test_user.id,
            channel="email",
            value="not-an-email",  # Invalid format
            is_verified=False,
            is_primary=False
        )
        session.add(endpoint)
        with pytest.raises(IntegrityError, match="user_endpoint_email_format_chk"):
            session.commit()
    
    def test_user_endpoint_non_email_no_validation(self, session: Session, test_user):
        """Non-email channels should not validate email format"""
        endpoint = UserEndpoint(
            user_id=test_user.id,
            channel="sms",
            value="+1234567890",  # Not an email, but that's OK for SMS
            is_verified=True,
            is_primary=False
        )
        session.add(endpoint)
        session.commit()
        assert endpoint.id is not None


class TestCustomerTypeConstraint:
    """Customer type must be 'person' or 'company'"""
    
    def test_customer_type_person_valid(self, session: Session, test_tenant):
        """Type 'person' should be accepted"""
        customer = Customer(
            tenant_id=test_tenant.id,
            display_name="John Doe",
            type="person"
        )
        session.add(customer)
        session.commit()
        assert customer.id is not None
    
    def test_customer_type_company_valid(self, session: Session, test_tenant):
        """Type 'company' should be accepted"""
        customer = Customer(
            tenant_id=test_tenant.id,
            display_name="ACME Corp",
            type="company"
        )
        session.add(customer)
        session.commit()
        assert customer.id is not None
    
    def test_customer_type_invalid(self, session: Session, test_tenant):
        """Invalid type should be rejected"""
        customer = Customer(
            tenant_id=test_tenant.id,
            display_name="Invalid Type Customer",
            type="organization"  # Not in allowed list
        )
        session.add(customer)
        with pytest.raises(IntegrityError, match="customer_type_chk"):
            session.commit()


class TestAuthMfaChannelConstraint:
    """MFA OTP channel must be 'email' or 'sms'"""
    
    def test_mfa_channel_email_valid(self, session: Session, test_user):
        """Channel 'email' should be accepted"""
        otp = AuthMfaOtp(
            user_id=test_user.id,
            channel="email",
            otp_code="123456",
            expires_at=datetime.utcnow() + timedelta(minutes=5)
        )
        session.add(otp)
        session.commit()
        assert otp.id is not None
    
    def test_mfa_channel_sms_valid(self, session: Session, test_user):
        """Channel 'sms' should be accepted"""
        otp = AuthMfaOtp(
            user_id=test_user.id,
            channel="sms",
            otp_code="654321",
            expires_at=datetime.utcnow() + timedelta(minutes=5)
        )
        session.add(otp)
        session.commit()
        assert otp.id is not None
    
    def test_mfa_channel_invalid(self, session: Session, test_user):
        """Invalid channel should be rejected"""
        otp = AuthMfaOtp(
            user_id=test_user.id,
            channel="push_notification",  # Not supported
            otp_code="999999",
            expires_at=datetime.utcnow() + timedelta(minutes=5)
        )
        session.add(otp)
        with pytest.raises(IntegrityError, match="auth_mfa_otp_channel_chk"):
            session.commit()


class TestPlatformRoleConstraint:
    """Platform role must be NULL, 'staff', or 'superadmin'"""
    
    def test_platform_role_null_valid(self, session: Session, test_tenant):
        """NULL platform role should be accepted (tenant user)"""
        user = User(
            email="tenant.user@example.com",
            tenant_id=test_tenant.id,
            platform_role_code=None,
            is_active=True
        )
        session.add(user)
        session.commit()
        assert user.id is not None
    
    def test_platform_role_staff_valid(self, session: Session):
        """Platform role 'staff' should be accepted"""
        user = User(
            email="staff@aevofab.example.com",
            platform_role_code="staff",
            is_active=True
        )
        session.add(user)
        session.commit()
        assert user.id is not None
    
    def test_platform_role_superadmin_valid(self, session: Session):
        """Platform role 'superadmin' should be accepted"""
        user = User(
            email="admin@aevofab.example.com",
            platform_role_code="superadmin",
            is_active=True
        )
        session.add(user)
        session.commit()
        assert user.id is not None
    
    def test_platform_role_invalid(self, session: Session):
        """Invalid platform role should be rejected"""
        user = User(
            email="hacker@evil.com",
            platform_role_code="god_mode",  # Not allowed
            is_active=True
        )
        session.add(user)
        with pytest.raises(IntegrityError, match="user_platform_role_chk"):
            session.commit()


class TestStatusEnumConstraints:
    """Various status field enumerations"""
    
    def test_notification_outbox_status_valid(self, session: Session, test_tenant):
        """Valid notification status should be accepted"""
        for status in ['pending', 'sent', 'failed', 'cancelled']:
            notification = NotificationOutbox(
                tenant_id=test_tenant.id,
                channel="email",
                recipient="test@example.com",
                status=status
            )
            session.add(notification)
            session.commit()
            assert notification.id is not None
    
    def test_notification_outbox_status_invalid(self, session: Session, test_tenant):
        """Invalid notification status should be rejected"""
        notification = NotificationOutbox(
            tenant_id=test_tenant.id,
            channel="email",
            recipient="test@example.com",
            status="delivered"  # Wrong enum value
        )
        session.add(notification)
        with pytest.raises(IntegrityError, match="notification_outbox_status_chk"):
            session.commit()
    
    # Additional status constraint tests for other entities...
```

**Test Fixtures Required:**
- `test_tenant` - Existing in conftest.py
- `test_user` - Existing in conftest.py
- May need to create fixtures for other entities as needed

---

### 6. Verification Protocol

**Run Tests:**
```bash
cd backend && source .venv/bin/activate

# Run new tests only
pytest tests/test_check_constraints_task9.py -v

# Run full test suite (ensure no regression)
pytest tests/ --ignore=tests/integration/ -v
```

**Expected Results:**
- ✅ All 18+ new tests passing
- ✅ All 466 existing tests still passing
- ✅ **Total: 484+/484+ tests passing (100%)**

**Database Verification:**
```sql
-- Verify all CHECK constraints exist
SELECT
    conname AS constraint_name,
    conrelid::regclass AS table_name,
    pg_get_constraintdef(oid) AS constraint_definition
FROM pg_constraint
WHERE contype = 'c'
  AND connamespace = 'public'::regnamespace
  AND conname LIKE '%_chk'
ORDER BY conrelid::regclass::text, conname;

-- Expected output includes:
-- user_email_format_chk
-- user_platform_role_chk
-- user_endpoint_email_format_chk
-- customer_type_chk
-- auth_mfa_otp_channel_chk
-- notification_outbox_status_chk
-- webhook_delivery_attempt_status_chk
-- integration_sync_conflict_resolution_chk
-- connector_run_log_status_chk
```

---

## Success Criteria

**MUST COMPLETE ALL BEFORE MARKING TASK AS DONE:**

- [x] **Pre-migration data validation completed** - All existing data complies with new constraints
- [x] **All 9 SQLModel classes updated** with CheckConstraint in `__table_args__`
- [x] **Alembic migration created** with all 9 CHECK constraints
- [x] **Migration applied successfully** - `alembic upgrade head` completes without errors
- [x] **All 24 new tests written and passing** (24 comprehensive tests covering all constraints)
- [x] **ALL existing tests still passing** - Zero regression
- [x] **Total: 490/490 tests passing (100%)**
- [x] **Database verification query** confirms all 9 constraints active
- [x] **Migration rollback tested** - `alembic downgrade -1` then `upgrade head` works
- [x] **Documentation updated** - Implementation notes added below

**Zero Tolerance Policy:**
- **Any failing test = INCOMPLETE**
- **Test pass rate MUST be 100%**
- **Any existing invalid data MUST be cleaned before migration**

---

## Key Files to Review

### Architecture & Design
- `dev-docs/analysis/phase-4.5-db-schema-sync-to-design-plan.md` - **Task 9 Details** ⭐
- `dev-docs/db-design/pilot-db-schema-v2.6h.json` - **GOLDEN MASTER**
- `dev-docs/db-design/aevofab-db-process-v2.6h.md` - Database operations

### Backend Code (Files to Modify)
- `backend/app/models/core.py` - User, UserEndpoint
- `backend/app/models/crm.py` - Customer
- `backend/app/models/auth.py` - AuthMfaOtp
- `backend/app/models/system.py` - NotificationOutbox, WebhookDeliveryAttempt, IntegrationSyncConflict, ConnectorRunLog

### Migration (To Create)
- `backend/migrations/versions/YYYY_MM_DD_HHMM-*_add_missing_check_constraints_task9.py`

### Tests (To Create)
- `backend/tests/test_check_constraints_task9.py` - 18+ tests
- `backend/tests/conftest.py` - Review for fixtures

---

## Risk Assessment

**Data Validation Risk:** MEDIUM
- Existing data may violate new constraints
- **Mitigation:** Run pre-migration validation queries, clean invalid data

**Performance Impact:** LOW
- CHECK constraints add < 1ms per INSERT/UPDATE
- Regex validation is CPU-bound but very fast for single rows

**Rollback Complexity:** LOW
- Simple `DROP CONSTRAINT` statements in downgrade
- No data transformation required

**Production Impact:** LOW
- All changes are backward compatible
- Constraints prevent future bugs without affecting existing valid data

---

## Notes

- **Email Regex Pattern:** The pattern `^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$` is intentionally simple (RFC 5322 subset)
- **Enum Constraints:** Validated against Golden Master JSON schema - do not add unlisted values
- **Nullable Enums:** `platform_role_code` and `resolution_strategy` allow NULL (CHECK enforces valid non-NULL values)
- **Constraint Naming:** Follow pattern `{table}_{column}_{type}_chk` (e.g., `user_email_format_chk`)
- **Existing Constraints:** Customer table already has `uq_customer_tenant_display_name` - merge in `__table_args__`

**Important:** If you discover additional CHECK constraints in the Golden Master JSON that aren't listed here, add them to ensure 100% alignment.

---

## Questions to Ask

**Before starting:**
1. Have I reviewed the Golden Master JSON for ALL check constraints?
2. Have I run pre-migration validation queries on production-like data?
3. Do I understand how to merge CheckConstraint with existing `__table_args__`?
4. Are all test fixtures available in conftest.py?

**During implementation:**
1. Did I properly escape the regex pattern in Python strings (double backslash)?
2. Are all constraint names consistent with Golden Master naming convention?
3. Have I tested both valid AND invalid values for each constraint?
4. Did I verify nullable columns allow NULL (e.g., `platform_role_code IS NULL OR ...`)?

**After implementation:**
1. Do I have 100% test pass rate (484+/484+)?
2. Can I see all 9 constraints in `pg_constraint` query?
3. Does migration rollback cleanly without orphaned constraints?
4. Have I documented any data cleanup that was required?

---

---

## Implementation Notes (April 1, 2026)

**Completed By:** MVP Builder
**Migration:** `2026_04_01_1230-b78d2b0199e8_add_missing_check_constraints_task9.py`
**Test Suite:** `test_check_constraints_task9.py` - 24 tests
**Final Test Results:** 490/490 tests passing (100%)

### Constraints Implemented

All 9 CHECK constraints were successfully added:

1. ✅ `user.email` - Email format regex validation
2. ✅ `user.platform_role_code` - Platform role enum (NULL, 'staff', 'superadmin')
3. ✅ `user_endpoint.value` - Conditional email format validation (when channel='email')
4. ✅ `customer.type` - Customer type enum ('person', 'company')
5. ✅ `auth_mfa_otp.channel` - MFA channel enum ('email', 'sms')
6. ✅ `notification_outbox.status` - Notification status enum ('pending', 'sent', 'failed', 'cancelled')
7. ✅ `webhook_delivery_attempt.status` - Webhook status enum ('pending', 'delivered', 'failed', 'retrying')
8. ✅ `integration_sync_conflict.status` - Conflict status enum ('pending', 'resolved_keep_internal', 'resolved_keep_external')
9. ✅ `connector_run_log.status` - Connector status enum ('running', 'completed', 'failed', 'cancelled')

### Key Implementation Decisions

**1. Conflict Status Enumeration Correction:**
   - Original prompt suggested constraint on `resolution_strategy` column
   - Actual schema inspection revealed column name is `status` not `resolution_strategy`
   - Valid values: 'pending', 'resolved_keep_internal', 'resolved_keep_external'
   - **Application code fixes required:** Updated `integrations.py` to map resolution strategies to correct status values

**2. Test Regressions Fixed:**
   - 6 tests initially failed due to invalid enum values in application code
   - `notification_worker.py`: Changed 'retrying' status to 'pending' with `next_attempt_at`
   - `integrations.py`: Fixed conflict resolution API to use correct status values
   - `test_conflict_detection.py`: Updated test assertions to expect correct status values

**3. Test Fixtures Enhanced:**
   - Added 5 new fixtures to `conftest.py`:
     - `test_notification_event`
     - `test_webhook_endpoint`
     - `test_webhook_event`
     - `test_app_service`
     - `test_supplier`
   - Added platform role fixtures to prevent foreign key violations in tests

**4. Migration Cleanup:**
   - Removed auto-generated `audit.event` table creation from migration (table already exists)
   - Verified all constraint names match Golden Master naming convention

### Pre-Migration Data Validation

All validation queries returned zero rows - no existing data violated new constraints:
- No invalid email addresses found
- No invalid customer types found
- No invalid MFA channels found
- No invalid platform roles found
- No invalid status values found

### Test Coverage

Created comprehensive test suite with 24 tests organized into 8 test classes:

- `TestEmailFormatConstraints` (5 tests) - Email regex validation
- `TestCustomerTypeConstraint` (3 tests) - Customer type enum validation
- `TestAuthMfaChannelConstraint` (3 tests) - MFA channel validation
- `TestPlatformRoleConstraint` (4 tests) - Platform role validation
- `TestNotificationOutboxStatusConstraint` (2 tests) - Notification status enum
- `TestWebhookDeliveryAttemptStatusConstraint` (2 tests) - Webhook status enum
- `TestIntegrationSyncConflictStatusConstraint` (2 tests) - Conflict status enum
- `TestConnectorRunLogStatusConstraint` (2 tests) - Connector status enum

Each test validates both valid and invalid values to ensure constraints work correctly.

### Database Verification

All 9 CHECK constraints verified in the local development database (`pilot_dev`):

```sql
SELECT conname, conrelid::regclass, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE contype = 'c'
  AND connamespace = 'public'::regnamespace
  AND conname IN (
    'user_email_format_chk',
    'user_platform_role_chk',
    'user_endpoint_email_format_chk',
    'customer_type_chk',
    'auth_mfa_otp_channel_chk',
    'notification_outbox_status_chk',
    'webhook_delivery_attempt_status_chk',
    'integration_sync_conflict_status_chk',
    'connector_run_log_status_chk'
  );
```

All constraints confirmed active and enforcing data integrity.

### Migration Rollback Testing

Successfully tested migration reversibility:
```bash
alembic downgrade -1  # Drops all 9 constraints
alembic upgrade head  # Re-adds all 9 constraints
```

No errors encountered. Database schema cleanly rolls back and forward.

### Lessons Learned

1. **Always inspect actual schema:** The prompt referenced `resolution_strategy` column, but actual schema had `status` column
2. **Pre-validation is critical:** Running validation queries before migration prevents deployment failures
3. **Constraint violations reveal application bugs:** Finding invalid 'retrying' and 'resolved' statuses exposed application code bugs
4. **Database-level validation is essential:** Application-level validation can be bypassed; database constraints are the last line of defense

### Next Steps

Task 9 is complete. Recommend proceeding to:
- **Task 10:** Missing temporal exclusion constraints (6 tables)

---

**Task Status:** ✅ COMPLETE (April 1, 2026)
**Test Pass Rate:** 100% (490/490 tests)
**Data Integrity:** Enhanced (9 new CHECK constraints protecting data quality)
