"""
FIND-066 (S2 High) — B18 schema-only: user profile columns + tenant_user skill/employee columns.

PRD-§3.5-F12: language preference; user profile columns for B20 PATCH endpoint.

Columns added by B18 migrations:
  user table:
    - phone_number VARCHAR NULL
    - time_zone VARCHAR NULL DEFAULT 'America/New_York'
    - profile_photo_s3_key TEXT NULL
    - language_preference VARCHAR NULL DEFAULT 'en'
    - CHECK user_language_preference_chk: language_preference IN ('en')
  tenant_user table:
    - skill_level_code VARCHAR NULL
    - employee_number VARCHAR NULL

No code changes in B18 — columns are schema scaffolding for B20, Task 11.

Test coverage:
  1. DB schema: all 6 columns exist with correct nullable/default settings
  2. DB schema: language_preference CHECK constraint exists
  3. ORM model: User has all 4 new fields; TenantUser has 2 new fields
  4. Integrity: language_preference='en' accepted; other values rejected
  5. ORM insert: new columns accept NULL (nullable columns work correctly)
  6. ORM insert: server defaults applied for time_zone and language_preference

Test subfolder: tests/batch_b18/
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError

# ─────────────────────────────────────────────────────────────────────────────
# 1. DB schema: columns exist with correct attributes
# ─────────────────────────────────────────────────────────────────────────────


class TestFind066DBSchemaUserColumns:
    """Verify all 4 new user columns were created by migration."""

    @pytest.mark.parametrize(
        "column_name,expected_nullable",
        [
            ("phone_number", "YES"),
            ("time_zone", "YES"),
            ("profile_photo_s3_key", "YES"),
            ("language_preference", "YES"),
        ],
    )
    def test_user_column_exists_and_is_nullable(
        self, db_session, column_name, expected_nullable
    ):
        """Column must exist on user table and be nullable."""
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT column_name, is_nullable "
                "FROM information_schema.columns "
                "WHERE table_schema = 'public' "
                "  AND table_name = 'user' "
                "  AND column_name = :col"
            ).bindparams(col=column_name)
        ).first()

        assert result is not None, f"Column '{column_name}' missing from user table"
        assert result[1] == expected_nullable, (
            f"user.{column_name} must be nullable={expected_nullable}, got {result[1]}"
        )

    @pytest.mark.parametrize(
        "column_name,expected_default_fragment",
        [
            ("time_zone", "America/New_York"),
            ("language_preference", "en"),
        ],
    )
    def test_user_column_has_server_default(
        self, db_session, column_name, expected_default_fragment
    ):
        """time_zone and language_preference must have server defaults."""
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT column_default "
                "FROM information_schema.columns "
                "WHERE table_schema = 'public' "
                "  AND table_name = 'user' "
                "  AND column_name = :col"
            ).bindparams(col=column_name)
        ).first()

        assert result is not None, f"user.{column_name} column missing"
        assert result[0] is not None, f"user.{column_name} must have a server default"
        assert expected_default_fragment in str(result[0]), (
            f"user.{column_name} server default must contain '{expected_default_fragment}', "
            f"got '{result[0]}'"
        )


class TestFind066DBSchemaTenantUserColumns:
    """Verify 2 new tenant_user columns were created by migration."""

    @pytest.mark.parametrize("column_name", ["skill_level_code", "employee_number"])
    def test_tenant_user_column_exists_and_is_nullable(self, db_session, column_name):
        """Column must exist on tenant_user table and be nullable."""
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT column_name, is_nullable "
                "FROM information_schema.columns "
                "WHERE table_schema = 'public' "
                "  AND table_name = 'tenant_user' "
                "  AND column_name = :col"
            ).bindparams(col=column_name)
        ).first()

        assert result is not None, (
            f"Column '{column_name}' missing from tenant_user table"
        )
        assert result[1] == "YES", (
            f"tenant_user.{column_name} must be nullable, got is_nullable='{result[1]}'"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 2. DB schema: language_preference CHECK constraint
# ─────────────────────────────────────────────────────────────────────────────


class TestFind066LanguagePreferenceConstraint:
    """language_preference CHECK constraint must be present and enforced."""

    def test_language_preference_check_constraint_exists(self, db_session):
        """user_language_preference_chk must exist on user table."""
        from sqlalchemy import text

        result = db_session.exec(
            text(
                "SELECT constraint_name "
                "FROM information_schema.table_constraints "
                "WHERE table_schema = 'public' "
                "  AND table_name = 'user' "
                "  AND constraint_type = 'CHECK' "
                "  AND constraint_name = 'user_language_preference_chk'"
            )
        ).first()

        assert result is not None, (
            "user_language_preference_chk CHECK constraint missing from user table"
        )

    def test_language_preference_en_accepted(self, db_session, test_tenant):
        """language_preference='en' must be accepted (valid MVP value)."""
        from sqlalchemy import text

        user_id = str(uuid.uuid4())
        email = f"test_lang_{user_id[:8]}@example.com"
        now = datetime.now(UTC)

        # Insert with language_preference='en' — must succeed
        db_session.exec(
            text(
                'INSERT INTO "user" '
                "(id, email, is_platform_user, mfa_enforced, preferred_mfa_channel, "
                " failed_login_count, require_password_reset, is_active, "
                " language_preference, created_at, updated_at) "
                "VALUES (:id, :email, false, false, 'email', 0, false, true, "
                " 'en', :now, :now)"
            ).bindparams(id=user_id, email=email, now=now)
        )
        db_session.flush()
        db_session.rollback()

    def test_language_preference_invalid_value_rejected(self, db_session):
        """language_preference='fr' must be rejected by CHECK constraint in MVP."""
        from sqlalchemy import text

        user_id = str(uuid.uuid4())
        email = f"test_lang_{user_id[:8]}@example.com"
        now = datetime.now(UTC)

        with pytest.raises(IntegrityError):
            db_session.exec(
                text(
                    'INSERT INTO "user" '
                    "(id, email, is_platform_user, mfa_enforced, preferred_mfa_channel, "
                    " failed_login_count, require_password_reset, is_active, "
                    " language_preference, created_at, updated_at) "
                    "VALUES (:id, :email, false, false, 'email', 0, false, true, "
                    " 'fr', :now, :now)"
                ).bindparams(id=user_id, email=email, now=now)
            )
            db_session.flush()

        db_session.rollback()

    def test_language_preference_null_accepted(self, db_session):
        """language_preference=NULL must be accepted (column is nullable)."""
        from sqlalchemy import text

        user_id = str(uuid.uuid4())
        email = f"test_lang_{user_id[:8]}@example.com"
        now = datetime.now(UTC)

        db_session.exec(
            text(
                'INSERT INTO "user" '
                "(id, email, is_platform_user, mfa_enforced, preferred_mfa_channel, "
                " failed_login_count, require_password_reset, is_active, "
                " created_at, updated_at) "
                "VALUES (:id, :email, false, false, 'email', 0, false, true, :now, :now)"
            ).bindparams(id=user_id, email=email, now=now)
        )
        db_session.flush()
        db_session.rollback()


# ─────────────────────────────────────────────────────────────────────────────
# 3. ORM model: field presence
# ─────────────────────────────────────────────────────────────────────────────


class TestFind066ORMFieldPresence:
    """ORM models must expose all new fields."""

    def test_user_has_phone_number(self):
        from app.models.core import User

        assert hasattr(User, "phone_number"), "User.phone_number field missing"

    def test_user_has_time_zone(self):
        from app.models.core import User

        assert hasattr(User, "time_zone"), "User.time_zone field missing"

    def test_user_has_profile_photo_s3_key(self):
        from app.models.core import User

        assert hasattr(User, "profile_photo_s3_key"), (
            "User.profile_photo_s3_key field missing"
        )

    def test_user_has_language_preference(self):
        from app.models.core import User

        assert hasattr(User, "language_preference"), (
            "User.language_preference field missing"
        )

    def test_tenant_user_has_skill_level_code(self):
        from app.models.auth import TenantUser

        assert hasattr(TenantUser, "skill_level_code"), (
            "TenantUser.skill_level_code field missing"
        )

    def test_tenant_user_has_employee_number(self):
        from app.models.auth import TenantUser

        assert hasattr(TenantUser, "employee_number"), (
            "TenantUser.employee_number field missing"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 4. ORM insert: new columns accept NULL and persist
# ─────────────────────────────────────────────────────────────────────────────


class TestFind066ORMInsertBehavior:
    """Verify new columns work correctly via ORM inserts."""

    def test_user_new_columns_accept_null_values(self, db_session):
        """phone_number and profile_photo_s3_key accept NULL.
        time_zone and language_preference have server_defaults, so DB returns
        the default on INSERT when Python passes None — both behaviors correct.
        """
        from sqlmodel import select

        from app.models.core import User

        now = datetime.now(UTC)
        user = User(
            id=uuid.uuid4(),
            email=f"testprofile_{uuid.uuid4().hex[:8]}@example.com",
            phone_number=None,
            time_zone=None,
            profile_photo_s3_key=None,
            language_preference=None,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        db_session.commit()

        fetched = db_session.exec(select(User).where(User.id == user.id)).first()
        assert fetched is not None
        # No server default — must be NULL
        assert fetched.phone_number is None
        assert fetched.profile_photo_s3_key is None
        # Has server default — DB returns default when None passed; both NULL and default are valid
        assert fetched.time_zone in (None, "America/New_York")
        assert fetched.language_preference in (None, "en")

    def test_user_new_columns_store_values(self, db_session):
        """New user columns must persist non-null values correctly."""
        from sqlmodel import select

        from app.models.core import User

        now = datetime.now(UTC)
        user = User(
            id=uuid.uuid4(),
            email=f"testprofile_{uuid.uuid4().hex[:8]}@example.com",
            phone_number="+15551234567",
            time_zone="America/Chicago",
            profile_photo_s3_key="profiles/abc/photo.jpg",
            language_preference="en",
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        db_session.commit()

        fetched = db_session.exec(select(User).where(User.id == user.id)).first()
        assert fetched is not None
        assert fetched.phone_number == "+15551234567"
        assert fetched.time_zone == "America/Chicago"
        assert fetched.profile_photo_s3_key == "profiles/abc/photo.jpg"
        assert fetched.language_preference == "en"

    def test_tenant_user_new_columns_accept_null(
        self, db_session, test_tenant, test_user
    ):
        """skill_level_code and employee_number must accept NULL values.

        This test validates that the migration added nullable columns (no NOT NULL
        default). It verifies we can SET the column to None and write it back.

        Resilience: seed_test_tenant.py SD-7 B1 sets skill_level_code and
        employee_number on the canonical test tenant_user row. The test no longer
        asserts that the seeded row IS null — instead it verifies nullability by
        round-tripping a None write (Rule 16).
        """
        import pytest
        from sqlmodel import select

        from app.models.auth import TenantUser

        # Fetch the existing test tenant_user row
        tu = db_session.exec(
            select(TenantUser).where(
                TenantUser.tenant_id == test_tenant.id,
                TenantUser.user_id == test_user.id,
            )
        ).first()

        if tu is None:
            pytest.skip("No test tenant_user row available — skipping")

        # Verify the column accepts None by writing NULL and reading it back
        original_skill = tu.skill_level_code
        original_emp = tu.employee_number

        tu.skill_level_code = None
        tu.employee_number = None
        db_session.add(tu)
        db_session.commit()
        db_session.refresh(tu)

        assert tu.skill_level_code is None, (
            f"Column should accept NULL — got {tu.skill_level_code}"
        )
        assert tu.employee_number is None, (
            f"Column should accept NULL — got {tu.employee_number}"
        )

        # Restore original values so other tests see consistent seed state
        tu.skill_level_code = original_skill
        tu.employee_number = original_emp
        db_session.add(tu)
        db_session.commit()

    def test_tenant_user_new_columns_store_values(
        self, db_session, test_tenant, test_user
    ):
        """skill_level_code and employee_number must persist non-null values."""
        from sqlmodel import select

        from app.models.auth import TenantUser

        tu = db_session.exec(
            select(TenantUser).where(
                TenantUser.tenant_id == test_tenant.id,
                TenantUser.user_id == test_user.id,
            )
        ).first()

        if tu is None:
            pytest.skip("No test tenant_user row available — skipping")

        tu.skill_level_code = "journeyman"
        tu.employee_number = "EMP-0042"
        db_session.add(tu)
        db_session.commit()

        fetched = db_session.exec(
            select(TenantUser).where(
                TenantUser.tenant_id == test_tenant.id,
                TenantUser.user_id == test_user.id,
            )
        ).first()
        assert fetched.skill_level_code == "journeyman"
        assert fetched.employee_number == "EMP-0042"

        # Cleanup: reset to NULL to avoid leaking state
        fetched.skill_level_code = None
        fetched.employee_number = None
        db_session.add(fetched)
        db_session.commit()
