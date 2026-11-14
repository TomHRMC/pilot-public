"""
Test Suite: Phase 4.6 Task 1 - Discount Version Table
Tests discount_version table with check constraints
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.catalog import DiscountVersion


class TestDiscountVersionTable:
    """Test discount_version table exists and has correct structure"""

    def test_discount_version_table_exists(self, db_session: Session):
        """Verify discount_version table was created"""
        result = db_session.execute(
            text(
                "SELECT tablename FROM pg_tables "
                "WHERE schemaname = 'public' AND tablename = 'discount_version'"
            )
        )
        assert result.scalar() == "discount_version"

    def test_discount_version_basic_insert_with_pct_off(
        self, db_session: Session, test_tenant
    ):
        """Valid discount version with pct_off should be created"""
        version = DiscountVersion(
            tenant_id=test_tenant.id,
            code="SUMMER2026",
            pct_off=Decimal("15.000"),
            amount_off_cents=None,
            valid_period="[2026-06-01,2026-09-01)",
            recorded_at=datetime.now(UTC),
        )
        db_session.add(version)
        db_session.commit()

        result = db_session.exec(
            select(DiscountVersion).where(DiscountVersion.id == version.id)
        ).first()
        assert result is not None
        assert result.pct_off == Decimal("15.000")
        assert result.amount_off_cents is None

    def test_discount_version_basic_insert_with_amount_off(
        self, db_session: Session, test_tenant
    ):
        """Valid discount version with amount_off_cents should be created"""
        version = DiscountVersion(
            tenant_id=test_tenant.id,
            code="FLAT50",
            pct_off=None,
            amount_off_cents=5000,  # $50.00
            valid_period="[2026-06-01,2026-09-01)",
            recorded_at=datetime.now(UTC),
        )
        db_session.add(version)
        db_session.commit()

        result = db_session.exec(
            select(DiscountVersion).where(DiscountVersion.id == version.id)
        ).first()
        assert result is not None
        assert result.pct_off is None
        assert result.amount_off_cents == 5000


class TestDiscountVersionCheckConstraints:
    """Test discount_version_value_check constraint"""

    def test_both_pct_and_amount_rejected(self, db_session: Session, test_tenant):
        """Discount with both pct_off AND amount_off_cents should be rejected"""
        version = DiscountVersion(
            tenant_id=test_tenant.id,
            code="INVALID",
            pct_off=Decimal("10.000"),
            amount_off_cents=1000,
            valid_period="[2026-06-01,2026-09-01)",
            recorded_at=datetime.now(UTC),
        )
        db_session.add(version)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert "discount_version_value_check" in str(exc_info.value)

    def test_neither_pct_nor_amount_rejected(self, db_session: Session, test_tenant):
        """Discount with neither pct_off nor amount_off_cents should be rejected"""
        version = DiscountVersion(
            tenant_id=test_tenant.id,
            code="INVALID",
            pct_off=None,
            amount_off_cents=None,
            valid_period="[2026-06-01,2026-09-01)",
            recorded_at=datetime.now(UTC),
        )
        db_session.add(version)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        assert "discount_version_value_check" in str(exc_info.value)

    def test_pct_off_only_allowed(self, db_session: Session, test_tenant):
        """Discount with only pct_off should be allowed"""
        version = DiscountVersion(
            tenant_id=test_tenant.id,
            code="PCT10",
            pct_off=Decimal("10.000"),
            amount_off_cents=None,
            valid_period="[2026-06-01,2026-09-01)",
            recorded_at=datetime.now(UTC),
        )
        db_session.add(version)
        db_session.commit()
        assert version.id is not None

    def test_amount_off_only_allowed(self, db_session: Session, test_tenant):
        """Discount with only amount_off_cents should be allowed"""
        version = DiscountVersion(
            tenant_id=test_tenant.id,
            code="FLAT25",
            pct_off=None,
            amount_off_cents=2500,
            valid_period="[2026-06-01,2026-09-01)",
            recorded_at=datetime.now(UTC),
        )
        db_session.add(version)
        db_session.commit()
        assert version.id is not None


class TestDiscountVersionForeignKeys:
    """Test discount_version foreign key relationships"""

    def test_tenant_foreign_key_works(self, db_session: Session, test_tenant):
        """Discount version should reference valid tenant"""
        version = DiscountVersion(
            tenant_id=test_tenant.id,
            code="TENANTDISC",
            pct_off=Decimal("20.000"),
            valid_period="[2026-06-01,2026-09-01)",
            recorded_at=datetime.now(UTC),
        )
        db_session.add(version)
        db_session.commit()

        # Verify foreign key relationship
        result = db_session.execute(
            text("SELECT tenant_id FROM discount_version WHERE id = :id"),
            {"id": version.id},
        )
        assert result.scalar() == test_tenant.id

    def test_global_discount_null_tenant_allowed(self, db_session: Session):
        """Global discount (NULL tenant_id) should be allowed"""
        version = DiscountVersion(
            tenant_id=None,
            code="GLOBAL10",
            pct_off=Decimal("10.000"),
            valid_period="[2026-01-01,2026-12-31)",
            recorded_at=datetime.now(UTC),
        )
        db_session.add(version)
        db_session.commit()

        result = db_session.exec(
            select(DiscountVersion).where(DiscountVersion.id == version.id)
        ).first()
        assert result is not None
        assert result.tenant_id is None

    def test_invalid_tenant_rejected(self, db_session: Session):
        """Discount version with invalid tenant_id should be rejected"""
        invalid_tenant_id = uuid.uuid4()
        version = DiscountVersion(
            tenant_id=invalid_tenant_id,
            code="INVALID",
            pct_off=Decimal("10.000"),
            valid_period="[2026-06-01,2026-09-01)",
            recorded_at=datetime.now(UTC),
        )
        db_session.add(version)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()
        # Should fail on foreign key constraint
        assert (
            "fk_" in str(exc_info.value).lower()
            or "foreign key" in str(exc_info.value).lower()
        )
