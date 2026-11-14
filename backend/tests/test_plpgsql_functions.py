"""
Tests for PL/pgSQL database functions.

Tests the 3 critical database-level functions:
1. set_updated_at() - Auto-bump updated_at on UPDATE
2. guard_created_fields_immutable() - Prevent modification of created_at/created_by
3. guard_tenant_user_platform_isolation() - Prevent platform users from being tenant users

Reference: dev-docs/implementation-prompts/task-db-sync-04-prompt.md
"""

import time
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.auth import TenantUser
from app.models.core import User
from app.models.crm import Customer


class TestSetUpdatedAt:
    """Test set_updated_at() function - Auto-bump updated_at on UPDATE."""

    def test_updated_at_auto_bumps_on_update(self, db_session, test_tenant):
        """Test that updated_at auto-bumps on UPDATE without explicit SET."""
        # Create customer with unique name
        customer = Customer(
            tenant_id=test_tenant.id,
            display_name=f"Test Customer {uuid.uuid4()}",
            type="person",
        )
        db_session.add(customer)
        db_session.commit()
        db_session.refresh(customer)

        original_updated_at = customer.updated_at
        time.sleep(0.2)  # Ensure time difference

        # Update customer (without setting updated_at)
        customer.display_name = f"Updated Customer {uuid.uuid4()}"
        db_session.commit()
        db_session.refresh(customer)

        # Verify updated_at changed automatically (clock_timestamp ensures it moves forward)
        assert customer.updated_at > original_updated_at
        assert "Updated Customer" in customer.display_name

    def test_updated_at_bumps_on_multiple_updates(self, db_session, test_tenant):
        """Test that updated_at increases each time on multiple UPDATEs."""
        # Create customer with unique name
        customer = Customer(
            tenant_id=test_tenant.id,
            display_name=f"Test Customer {uuid.uuid4()}",
            type="person",
        )
        db_session.add(customer)
        db_session.commit()
        db_session.refresh(customer)

        first_updated_at = customer.updated_at
        time.sleep(0.2)

        # First update
        customer.display_name = f"Updated Once {uuid.uuid4()}"
        db_session.commit()
        db_session.refresh(customer)
        second_updated_at = customer.updated_at

        assert second_updated_at > first_updated_at
        time.sleep(0.2)

        # Second update
        customer.display_name = f"Updated Twice {uuid.uuid4()}"
        db_session.commit()
        db_session.refresh(customer)
        third_updated_at = customer.updated_at

        assert third_updated_at > second_updated_at
        assert "Updated Twice" in customer.display_name

    def test_updated_at_not_triggered_on_insert(self, db_session, test_tenant):
        """Test that INSERT does not trigger set_updated_at (only UPDATE should fire)."""
        # Create customer
        customer = Customer(
            tenant_id=test_tenant.id,
            display_name=f"Test Customer {uuid.uuid4()}",
            type="person",
        )
        db_session.add(customer)
        db_session.commit()
        db_session.refresh(customer)

        # Verify updated_at was set during INSERT (by default value, not trigger)
        assert customer.updated_at is not None
        # updated_at should be close to created_at on INSERT
        time_diff = abs((customer.updated_at - customer.created_at).total_seconds())
        assert time_diff < 1.0  # Within 1 second


class TestGuardCreatedFieldsImmutable:
    """Test guard_created_fields_immutable() function - Prevent modification of created_at/created_by."""

    def test_update_created_at_raises_exception(self, db_session, test_tenant):
        """Test that updating created_at raises IntegrityError."""
        # Create customer with unique name
        customer = Customer(
            tenant_id=test_tenant.id,
            display_name=f"Test Customer {uuid.uuid4()}",
            type="person",
        )
        db_session.add(customer)
        db_session.commit()
        db_session.refresh(customer)

        # Try to change created_at (should fail)
        with pytest.raises(IntegrityError) as exc:
            customer.created_at = datetime.now(UTC)
            db_session.commit()

        assert "created_at is immutable" in str(exc.value)

    def test_update_created_by_raises_exception(
        self, db_session, test_tenant, test_user
    ):
        """Test that updating created_by raises IntegrityError."""
        # Create customer with created_by and unique name
        customer = Customer(
            tenant_id=test_tenant.id,
            display_name=f"Test Customer {uuid.uuid4()}",
            type="person",
            created_by=test_user.id,
        )
        db_session.add(customer)
        db_session.commit()
        db_session.refresh(customer)

        # Create another user to try changing created_by to
        another_user = User(
            email=f"another-{uuid.uuid4()}@example.com",
            email_verified=True,
        )
        db_session.add(another_user)
        db_session.commit()

        # Try to change created_by (should fail)
        with pytest.raises(IntegrityError) as exc:
            customer.created_by = another_user.id
            db_session.commit()

        assert "created_by is immutable" in str(exc.value)

    def test_update_other_fields_succeeds(self, db_session, test_tenant):
        """Test that UPDATE of other fields succeeds (does not block valid updates)."""
        # Create customer with unique name
        customer = Customer(
            tenant_id=test_tenant.id,
            display_name=f"Test Customer {uuid.uuid4()}",
            type="person",
        )
        db_session.add(customer)
        db_session.commit()
        db_session.refresh(customer)

        original_created_at = customer.created_at

        # Update other fields (should succeed)
        new_name = f"Updated Customer {uuid.uuid4()}"
        customer.display_name = new_name
        customer.type = "company"
        db_session.commit()
        db_session.refresh(customer)

        # Verify updates succeeded and created_at unchanged
        assert customer.display_name == new_name
        assert customer.type == "company"
        assert customer.created_at == original_created_at

    def test_insert_with_created_at_succeeds(self, db_session, test_tenant):
        """Test that INSERT with created_at succeeds (only blocks UPDATE)."""
        # Create customer with explicit created_at and unique name
        explicit_created_at = datetime.now(UTC)
        customer = Customer(
            tenant_id=test_tenant.id,
            display_name=f"Test Customer {uuid.uuid4()}",
            type="person",
            created_at=explicit_created_at,
        )
        db_session.add(customer)
        db_session.commit()
        db_session.refresh(customer)

        # Verify INSERT succeeded
        assert "Test Customer" in customer.display_name
        # created_at might be slightly different due to transaction timing
        time_diff = abs((customer.created_at - explicit_created_at).total_seconds())
        assert time_diff < 1.0  # Within 1 second


class TestGuardTenantUserPlatformIsolation:
    """Test guard_tenant_user_platform_isolation() function - Prevent platform users from being tenant users."""

    def test_normal_user_can_be_tenant_user(self, db_session, test_tenant):
        """Test normal user (no platform role) can be added to tenant_user (success case)."""
        # Get active status
        from app.models.auth import TenantUserStatus

        status = db_session.execute(
            select(TenantUserStatus).where(TenantUserStatus.code == "active")
        ).scalar_one()

        # Create normal user (no platform role)
        normal_user = User(
            email=f"normal-{uuid.uuid4()}@example.com",
            email_verified=True,
            platform_role_code=None,
        )
        db_session.add(normal_user)
        db_session.commit()

        # Add to tenant (should succeed) - use "owner" role which exists
        tenant_user = TenantUser(
            tenant_id=test_tenant.id,
            user_id=normal_user.id,
            role_code="owner",
            status_id=status.id,
        )
        db_session.add(tenant_user)
        db_session.commit()
        db_session.refresh(tenant_user)

        # Verify success
        assert tenant_user.user_id == normal_user.id
        assert tenant_user.tenant_id == test_tenant.id
        assert tenant_user.role_code == "owner"


class TestIntegration:
    """Integration tests for real-world workflows."""

    def test_invoice_workflow_updated_at_auto_bumps(self, db_session, test_tenant):
        """Test real-world workflow: Create customer, update it, verify updated_at auto-bumped."""
        # Create customer
        customer = Customer(
            tenant_id=test_tenant.id,
            display_name=f"ACME Corp {uuid.uuid4()}",
            type="company",
        )
        db_session.add(customer)
        db_session.commit()
        db_session.refresh(customer)

        original_updated_at = customer.updated_at
        time.sleep(0.2)

        # Update customer (simulating workflow)
        customer.display_name = f"ACME Corporation {uuid.uuid4()}"
        db_session.commit()
        db_session.refresh(customer)

        # Verify updated_at auto-bumped
        assert customer.updated_at > original_updated_at

    def test_audit_trail_created_at_immutability_protects_integrity(
        self, db_session, test_tenant
    ):
        """Test audit trail: Verify created_at immutability protects audit integrity."""
        # Create customer
        customer = Customer(
            tenant_id=test_tenant.id,
            display_name=f"Test Customer {uuid.uuid4()}",
            type="person",
        )
        db_session.add(customer)
        db_session.commit()
        db_session.refresh(customer)

        # Attempt to modify created_at (audit tampering attempt)
        with pytest.raises(IntegrityError) as exc:
            customer.created_at = datetime(2020, 1, 1, tzinfo=UTC)
            db_session.commit()

        assert "created_at is immutable" in str(exc.value)

    def test_user_isolation_normal_user_workflow(self, db_session, test_tenant):
        """Test that normal users can be assigned to tenants in typical workflow."""
        # Get active status
        from app.models.auth import TenantUserStatus

        status = db_session.execute(
            select(TenantUserStatus).where(TenantUserStatus.code == "active")
        ).scalar_one()

        # Create normal user
        normal_user = User(
            email=f"user-{uuid.uuid4()}@example.com",
            email_verified=True,
            platform_role_code=None,
        )
        db_session.add(normal_user)
        db_session.commit()

        # Assign to tenant (typical workflow - should succeed) - use "owner" role
        tenant_user = TenantUser(
            tenant_id=test_tenant.id,
            user_id=normal_user.id,
            role_code="owner",
            status_id=status.id,
        )
        db_session.add(tenant_user)
        db_session.commit()
        db_session.refresh(tenant_user)

        # Verify assignment succeeded
        assert tenant_user.user_id == normal_user.id
        assert tenant_user.tenant_id == test_tenant.id
        assert tenant_user.role_code == "owner"
