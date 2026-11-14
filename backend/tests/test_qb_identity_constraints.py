"""
Test QuickBooks Identity Rule: Customer Name Uniqueness Within Tenant

This test module validates that customer display names are unique within a tenant,
enforcing the same business rule that QuickBooks Online applies. This prevents
sync failures when pushing customers to QuickBooks.

Golden Master Reference: aevofab-db-schema-v2.6h.json
Gap Reference: Analysis Section 1 - QuickBooks Identity Rule
Migration: 2026_03_31_1804-1be24f24dd6b_add_qb_identity_constraints.py
"""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select, text

from app.models.core import Tenant
from app.models.crm import Customer, CustomerType


def test_customer_duplicate_name_same_tenant_rejected(db_session: Session) -> None:
    """
    Test that duplicate customer names within the same tenant are rejected.

    Validates: QuickBooks business rule enforcement at database level.
    Expected: IntegrityError raised on duplicate display_name within same tenant_id.
    """
    # Create a test tenant
    tenant = Tenant(name=f"QB Test Tenant {uuid.uuid4()}")
    db_session.add(tenant)
    db_session.flush()

    # Create first customer with name "ABC Electric"
    customer1 = Customer(
        tenant_id=tenant.id,
        type=CustomerType.company,
        display_name="ABC Electric",
        company_name="ABC Electric Company",
    )
    db_session.add(customer1)
    db_session.commit()

    # Attempt to create second customer with same name in same tenant
    customer2 = Customer(
        tenant_id=tenant.id,
        type=CustomerType.company,
        display_name="ABC Electric",  # Duplicate name
        company_name="ABC Electric Ltd",  # Different company_name shouldn't matter
    )
    db_session.add(customer2)

    # Should raise IntegrityError due to unique constraint violation
    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()

    # Verify the error message mentions the constraint or duplicate key
    error_message = str(exc_info.value).lower()
    assert (
        "uq_customer_tenant_display_name" in error_message
        or "duplicate" in error_message
    )


def test_customer_duplicate_name_different_tenant_allowed(db_session: Session) -> None:
    """
    Test that the same customer name in different tenants is allowed.

    Validates: Tenant isolation is maintained - different tenants can have
    customers with the same display_name.
    Expected: Both customers created successfully with different tenant_ids.
    """
    # Create two separate test tenants
    tenant1 = Tenant(name=f"QB Test Tenant 1 {uuid.uuid4()}")
    tenant2 = Tenant(name=f"QB Test Tenant 2 {uuid.uuid4()}")
    db_session.add_all([tenant1, tenant2])
    db_session.flush()

    # Create customer "ABC Electric" in Tenant 1
    customer1 = Customer(
        tenant_id=tenant1.id,
        type=CustomerType.company,
        display_name="ABC Electric",
        company_name="ABC Electric Company",
    )
    db_session.add(customer1)
    db_session.commit()

    # Create customer "ABC Electric" in Tenant 2 (should succeed)
    customer2 = Customer(
        tenant_id=tenant2.id,
        type=CustomerType.company,
        display_name="ABC Electric",  # Same name, different tenant
        company_name="ABC Electric Ltd",
    )
    db_session.add(customer2)
    db_session.commit()

    # Both customers should exist with the same display_name but different tenant_ids
    assert customer1.id != customer2.id
    assert customer1.display_name == customer2.display_name == "ABC Electric"
    assert customer1.tenant_id != customer2.tenant_id

    # Verify both customers exist in database
    stmt1 = select(Customer).where(
        Customer.id == customer1.id, Customer.tenant_id == tenant1.id
    )
    stmt2 = select(Customer).where(
        Customer.id == customer2.id, Customer.tenant_id == tenant2.id
    )

    result1 = db_session.exec(stmt1).first()
    result2 = db_session.exec(stmt2).first()

    assert result1 is not None
    assert result2 is not None
    assert result1.display_name == "ABC Electric"
    assert result2.display_name == "ABC Electric"


def test_customer_constraint_exists(db_session: Session) -> None:
    """
    Test that the unique constraint exists in the database schema.

    Validates: Migration successfully created the uq_customer_tenant_display_name constraint.
    Expected: Constraint found in pg_constraint with correct name and type.
    """
    # Query PostgreSQL system catalog for the constraint
    query = text("""
        SELECT conname, contype 
        FROM pg_constraint 
        WHERE conrelid = 'customer'::regclass 
          AND contype = 'u'
          AND conname = 'uq_customer_tenant_display_name'
    """)

    result = db_session.exec(query).first()

    # Constraint should exist
    assert result is not None, "uq_customer_tenant_display_name constraint not found"

    # Verify constraint details
    conname, contype = result
    assert conname == "uq_customer_tenant_display_name"
    assert contype == "u"  # 'u' means unique constraint


def test_customer_name_case_sensitivity(db_session: Session) -> None:
    """
    Test case sensitivity of customer display_name constraint.

    Validates: Whether "ABC Electric" and "abc electric" are treated as duplicates.
    Expected: Since display_name is regular text (not CITEXT), they are distinct.
    """
    # Create a test tenant
    tenant = Tenant(name=f"QB Test Tenant Case {uuid.uuid4()}")
    db_session.add(tenant)
    db_session.flush()

    # Create customer with lowercase name
    customer1 = Customer(
        tenant_id=tenant.id,
        type=CustomerType.company,
        display_name="abc electric",
    )
    db_session.add(customer1)
    db_session.commit()

    # Create customer with uppercase name (should succeed since text is case-sensitive)
    customer2 = Customer(
        tenant_id=tenant.id,
        type=CustomerType.company,
        display_name="ABC ELECTRIC",
    )
    db_session.add(customer2)
    db_session.commit()

    # Both customers should exist because text column is case-sensitive
    assert customer1.id != customer2.id
    assert customer1.display_name == "abc electric"
    assert customer2.display_name == "ABC ELECTRIC"

    # Verify both exist in database
    customers = db_session.exec(
        select(Customer).where(Customer.tenant_id == tenant.id)
    ).all()
    assert len(customers) == 2


def test_customer_update_to_duplicate_name_rejected(db_session: Session) -> None:
    """
    Test that updating a customer to a duplicate name is rejected.

    Validates: Constraint enforcement applies to UPDATEs, not just INSERTs.
    Expected: IntegrityError raised when updating to duplicate display_name.
    """
    # Create a test tenant
    tenant = Tenant(name=f"QB Test Tenant Update {uuid.uuid4()}")
    db_session.add(tenant)
    db_session.flush()

    # Create two customers with different names
    customer1 = Customer(
        tenant_id=tenant.id,
        type=CustomerType.company,
        display_name="ABC Electric",
    )
    customer2 = Customer(
        tenant_id=tenant.id,
        type=CustomerType.company,
        display_name="XYZ Plumbing",
    )
    db_session.add_all([customer1, customer2])
    db_session.commit()

    # Attempt to update customer2's name to match customer1
    customer2.display_name = "ABC Electric"

    # Should raise IntegrityError due to unique constraint violation
    with pytest.raises(IntegrityError) as exc_info:
        db_session.commit()

    # Verify the error message mentions the constraint or duplicate key
    error_message = str(exc_info.value).lower()
    assert (
        "uq_customer_tenant_display_name" in error_message
        or "duplicate" in error_message
    )
