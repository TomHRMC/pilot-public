"""
QB-H1 Task 5 — customer.display_name Uniqueness Collision Resolution Tests

Verifies that ``sync_customer_from_qb`` handles the ``uq_customer_tenant_display_name``
collision gracefully:
  - Two QB customers with identical DisplayName and different Ids → two P4T
    customers; the second is suffixed ``(QB <Id>)``.
  - Exactly one ``display_name_dedup`` conflict row exists (assert by inserted IDs).
  - Same-name update on an already-mapped customer does NOT create a duplicate
    (mapping-first behavior preserved).

NOTE: ``sync_customer_from_qb`` calls ``self.db.commit()`` internally, which
ends the test fixture's transaction. To maintain test isolation, the first
customer is created directly (not via the sync method) so only the second
sync call triggers the dedup path.

Batch: QB-H1
Design: dev-docs/architecture-design/batch-designs/batch-qb-h1-design.md §F.4
"""

import asyncio
import uuid
from datetime import UTC, datetime

import pytest
from sqlmodel import Session, select

from app.models.crm import Customer, CustomerType
from app.models.system import (
    AppService,
    IntegrationSyncConflict,
    IntegrationSyncMapping,
)
from services.quickbooks_sync import QuickBooksSync

pytestmark = [
    pytest.mark.domain_quickbooks,
    pytest.mark.unit,
]


@pytest.fixture
def qb_app_service_dedup(db_session, test_tenant, test_user):
    """QuickBooks AppService for dedup tests (no credential needed — no API calls)."""
    app_service = AppService(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        name="QuickBooks Online",
        category_code="accounting",
        provider_code="quickbooks",
        external_account_id="1234567890123456",
        is_active=True,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db_session.add(app_service)
    db_session.commit()
    db_session.refresh(app_service)
    return app_service


def _make_qb_customer(qb_id: str, display_name: str) -> dict:
    """Create a minimal QB customer dict for sync."""
    return {
        "Id": qb_id,
        "DisplayName": display_name,
        "SyncToken": "0",
        "Active": True,
    }


def _seed_customer_with_mapping(
    db_session: Session,
    tenant_id: uuid.UUID,
    app_service_id: uuid.UUID,
    display_name: str,
    qb_external_id: str,
    test_user_id: uuid.UUID,
) -> Customer:
    """Create a customer + sync mapping directly (bypasses sync_customer_from_qb's commit)."""
    customer = Customer(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        type=CustomerType.person,
        display_name=display_name,
        is_active=True,
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    db_session.add(customer)
    db_session.flush()

    mapping = IntegrationSyncMapping(
        tenant_id=tenant_id,
        entity_id=customer.id,
        entity_type_code="customer",
        app_service_id=app_service_id,
        external_id=qb_external_id,
        external_version_token="0",
        internal_version_token=None,
        sync_preference="pilot_master",
        last_synced_at=datetime.now(UTC),
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    db_session.add(mapping)
    db_session.commit()
    db_session.refresh(customer)
    return customer


class TestDisplayNameDedup:
    """Test the display_name dedup collision resolution.

    NOTE: ``sync_customer_from_qb`` calls ``self.db.commit()`` internally,
    which persists data to the shared dev DB (the test fixture's rollback
    can't undo a committed transaction). Each test cleans up the rows it
    creates by their specific IDs to maintain DB hygiene.
    """

    def test_two_same_name_customers_dedup(
        self, db_session: Session, test_tenant, test_user, qb_app_service_dedup
    ):
        """Two QB customers with identical DisplayName → two P4T customers,
        second suffixed ``(QB <Id>)``, one dedup conflict row."""
        display_name = f"Dedup Test Customer {uuid.uuid4().hex[:8]}"
        qb_id_1 = f"QB-DEDUP-001-{uuid.uuid4().hex[:4]}"
        qb_id_2 = f"QB-DEDUP-002-{uuid.uuid4().hex[:4]}"

        # Find the app_service_id that _get_app_service_id will return
        existing_svc = db_session.exec(
            select(AppService).where(
                AppService.tenant_id == test_tenant.id,
                AppService.provider_code == "quickbooks",
            )
        ).first()
        effective_app_service_id = (
            existing_svc.id if existing_svc else qb_app_service_dedup.id
        )

        # Pre-seed the first customer + mapping directly (avoids the
        # sync method's internal commit() which breaks test isolation)
        customer_1 = _seed_customer_with_mapping(
            db_session,
            test_tenant.id,
            effective_app_service_id,
            display_name,
            qb_id_1,
            test_user.id,
        )

        # Now sync the second QB customer with the SAME display_name but
        # different QB Id — this should trigger the dedup path
        sync = QuickBooksSync(test_tenant.id, db_session)
        qb_customer_2 = _make_qb_customer(qb_id_2, display_name)
        customer_2 = asyncio.run(sync.sync_customer_from_qb(qb_customer_2))

        assert customer_2 is not None
        # Second customer must be suffixed
        assert customer_2.display_name == f"{display_name} (QB {qb_id_2})"

        # Assert exactly one display_name_dedup conflict row for customer_2
        dedup_conflicts = db_session.exec(
            select(IntegrationSyncConflict).where(
                IntegrationSyncConflict.tenant_id == test_tenant.id,
                IntegrationSyncConflict.conflict_subtype == "display_name_dedup",
                IntegrationSyncConflict.external_id == qb_id_2,
            )
        ).all()
        assert len(dedup_conflicts) == 1, (
            f"Expected 1 display_name_dedup conflict for qb_id={qb_id_2}, "
            f"found {len(dedup_conflicts)}"
        )
        assert dedup_conflicts[0].status == "pending"

        # Cleanup: delete the rows we created (commit() persisted them)
        for conflict in dedup_conflicts:
            db_session.delete(conflict)
        for mapping in db_session.exec(
            select(IntegrationSyncMapping).where(
                IntegrationSyncMapping.tenant_id == test_tenant.id,
                IntegrationSyncMapping.external_id.in_([qb_id_1, qb_id_2]),
            )
        ).all():
            db_session.delete(mapping)
        for cust in db_session.exec(
            select(Customer).where(
                Customer.tenant_id == test_tenant.id,
                Customer.id.in_([customer_1.id, customer_2.id]),
            )
        ).all():
            db_session.delete(cust)
        db_session.commit()

    def test_mapped_customer_update_no_duplicate(
        self, db_session: Session, test_tenant, test_user, qb_app_service_dedup
    ):
        """Same-name update on an already-mapped customer does NOT create a
        duplicate (mapping-first behavior preserved).

        NOTE: ``_get_app_service_id`` returns the FIRST app_service with
        ``provider_code='quickbooks'`` for the tenant — which is the seeded
        one (``00000000…``), not the fixture's. The mapping must use the
        same app_service_id that the sync method will look up.
        """
        display_name = f"Mapped Test Customer {uuid.uuid4().hex[:8]}"
        qb_id = f"QB-MAPPED-001-{uuid.uuid4().hex[:4]}"

        # Find the app_service_id that _get_app_service_id will return
        # (the first quickbooks app_service for this tenant)
        existing_svc = db_session.exec(
            select(AppService).where(
                AppService.tenant_id == test_tenant.id,
                AppService.provider_code == "quickbooks",
            )
        ).first()
        effective_app_service_id = (
            existing_svc.id if existing_svc else qb_app_service_dedup.id
        )

        # Pre-seed the customer + mapping using the effective app_service_id
        customer_1 = _seed_customer_with_mapping(
            db_session,
            test_tenant.id,
            effective_app_service_id,
            display_name,
            qb_id,
            test_user.id,
        )

        # Sync the same QB customer again (update) — should UPDATE, not create
        sync = QuickBooksSync(test_tenant.id, db_session)
        qb_customer_updated = _make_qb_customer(qb_id, display_name)
        qb_customer_updated["SyncToken"] = "1"
        customer_updated = asyncio.run(sync.sync_customer_from_qb(qb_customer_updated))

        # Same customer (mapping-first)
        assert customer_updated is not None

        # No dedup conflict should exist for this customer
        dedup_conflicts = db_session.exec(
            select(IntegrationSyncConflict).where(
                IntegrationSyncConflict.tenant_id == test_tenant.id,
                IntegrationSyncConflict.conflict_subtype == "display_name_dedup",
                IntegrationSyncConflict.external_id == qb_id,
            )
        ).all()
        assert len(dedup_conflicts) == 0, (
            "No display_name_dedup conflict expected for mapped customer update"
        )

        # Cleanup
        for mapping in db_session.exec(
            select(IntegrationSyncMapping).where(
                IntegrationSyncMapping.tenant_id == test_tenant.id,
                IntegrationSyncMapping.external_id == qb_id,
            )
        ).all():
            db_session.delete(mapping)
        for cust in db_session.exec(
            select(Customer).where(
                Customer.tenant_id == test_tenant.id,
                Customer.id == customer_1.id,
            )
        ).all():
            db_session.delete(cust)
        db_session.commit()

    def test_normal_create_no_dedup(
        self, db_session: Session, test_tenant, test_user, qb_app_service_dedup
    ):
        """Verify the normal create path still works (no collision, no dedup)."""
        display_name = f"Normal Test Customer {uuid.uuid4().hex[:8]}"
        qb_id = f"QB-NORMAL-001-{uuid.uuid4().hex[:4]}"

        sync = QuickBooksSync(test_tenant.id, db_session)
        qb_customer = _make_qb_customer(qb_id, display_name)
        customer = asyncio.run(sync.sync_customer_from_qb(qb_customer))

        assert customer is not None
        assert customer.display_name == display_name

        # Verify mapping created
        mapping = db_session.exec(
            select(IntegrationSyncMapping).where(
                IntegrationSyncMapping.tenant_id == test_tenant.id,
                IntegrationSyncMapping.external_id == qb_id,
            )
        ).first()
        assert mapping is not None
        assert mapping.entity_id == customer.id

        # No dedup conflict
        dedup_conflicts = db_session.exec(
            select(IntegrationSyncConflict).where(
                IntegrationSyncConflict.tenant_id == test_tenant.id,
                IntegrationSyncConflict.conflict_subtype == "display_name_dedup",
                IntegrationSyncConflict.external_id == qb_id,
            )
        ).all()
        assert len(dedup_conflicts) == 0

        # Cleanup
        for conflict in dedup_conflicts:
            db_session.delete(conflict)
        if mapping:
            db_session.delete(mapping)
        for cust in db_session.exec(
            select(Customer).where(
                Customer.tenant_id == test_tenant.id,
                Customer.id == customer.id,
            )
        ).all():
            db_session.delete(cust)
        db_session.commit()
