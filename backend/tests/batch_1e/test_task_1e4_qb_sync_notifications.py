"""
Task 1-E-4: QB Sync Conflict Notification Wiring — Test Suite

Verifies:
  A. Outbox Wiring  — queue_conflict() creates exactly one NotificationOutbox
                      record (channel='email') in the same DB transaction.
  B. Dashboard Count — GET /integrations/sync-dashboard/test returns
                       requires_attention_count == 3 when 3 pending conflicts
                       are seeded.
  C. Resolved Exclusion — requires_attention_count drops to 2 after one
                          conflict is resolved, proving idx_isc_tenant_status
                          filters correctly.

Reference: dev-docs/analysis/db-schema-domain-mvp-features-impl-plan.md Task 1-E-4
Batch: 1-E
"""

import uuid
from datetime import UTC, datetime

from sqlmodel import Session, select

from app.models.core import EntityType
from app.models.crm import Customer
from app.models.system import (
    AppService,
    IntegrationSyncConflict,
    IntegrationSyncMapping,
    NotificationOutbox,
    NotificationType,
)
from services.quickbooks_sync import QuickBooksSync

# ============================================================
# Seed helpers
# ============================================================


def _seed_qb_app_service(db_session: Session, tenant_id: uuid.UUID) -> AppService:
    """Create a minimal QuickBooks AppService for the test tenant."""
    app_service = AppService(
        tenant_id=tenant_id,
        name="QuickBooks Online",
        category_code="accounting",
        provider_code="quickbooks",
        is_active=True,
    )
    db_session.add(app_service)
    db_session.flush()
    return app_service


def _seed_customer(db_session: Session, tenant_id: uuid.UUID) -> Customer:
    """Create a minimal Customer for the test tenant."""
    customer = Customer(
        tenant_id=tenant_id,
        type="person",
        display_name=f"John Doe {uuid.uuid4().hex[:6]}",
        first_name="John",
        last_name="Doe",
        is_active=True,
    )
    db_session.add(customer)
    db_session.flush()
    return customer


def _seed_sync_mapping(
    db_session: Session,
    tenant_id: uuid.UUID,
    app_service_id: uuid.UUID,
    customer_id: uuid.UUID,
    qb_external_id: str = "QB-001",
) -> IntegrationSyncMapping:
    """Create a sync mapping linking an Pilot for Trades customer to a QB customer."""
    mapping = IntegrationSyncMapping(
        tenant_id=tenant_id,
        app_service_id=app_service_id,
        entity_type_code="customer",
        entity_id=customer_id,
        external_id=qb_external_id,
        sync_preference="bi_directional",
        internal_version_token="v1",
        external_version_token="0",
        last_synced_at=datetime.now(UTC),
    )
    db_session.add(mapping)
    db_session.flush()
    return mapping


def _seed_conflict(
    db_session: Session,
    tenant_id: uuid.UUID,
    app_service_id: uuid.UUID,
    customer_id: uuid.UUID,
    status: str = "pending",
) -> IntegrationSyncConflict:
    """Directly insert an IntegrationSyncConflict record (bypasses service)."""
    conflict = IntegrationSyncConflict(
        tenant_id=tenant_id,
        app_service_id=app_service_id,
        entity_type_code="customer",
        entity_id=customer_id,
        external_id=f"QB-{uuid.uuid4().hex[:8]}",
        status=status,
        internal_payload={"display_name": "John Doe"},
        external_payload={"Id": "QB-999", "DisplayName": "John Doe", "SyncToken": "1"},
    )
    db_session.add(conflict)
    db_session.flush()
    return conflict


def _ensure_notification_type(db_session: Session, code: str, audience: str = "tenant"):
    """Ensure a NotificationType row exists (idempotent)."""
    existing = db_session.exec(
        select(NotificationType).where(NotificationType.code == code)
    ).first()
    if not existing:
        notif_type = NotificationType(
            code=code,
            audience=audience,
            name=code.replace("_", " ").title(),
            is_active=True,
        )
        db_session.add(notif_type)
        db_session.flush()


def _ensure_entity_type(db_session: Session, code: str):
    """Ensure an EntityType row exists (idempotent)."""
    existing = db_session.exec(
        select(EntityType).where(EntityType.code == code)
    ).first()
    if not existing:
        entity_type = EntityType(
            code=code,
            name=code.title(),
            description=code.title(),
            is_active=True,
        )
        db_session.add(entity_type)
        db_session.flush()


# ============================================================
# Test A — Outbox Wiring
# ============================================================


class TestOutboxWiring:
    """
    Directly invoke QuickBooksSync.queue_conflict() and assert that exactly
    one NotificationOutbox record is inserted with channel='email' and the
    correct tenant_id.
    """

    def test_queue_conflict_creates_notification_outbox(
        self, db_session: Session, test_tenant, test_user
    ):
        """
        Test A: queue_conflict() must create exactly one pending email outbox record
        for the tenant, and the body must mention the customer's display_name.
        """
        # Seed pre-requisites
        _ensure_entity_type(db_session, "customer")
        _ensure_notification_type(db_session, "qb_sync_conflict", audience="tenant")

        app_service = _seed_qb_app_service(db_session, test_tenant.id)
        customer = _seed_customer(db_session, test_tenant.id)
        mapping = _seed_sync_mapping(
            db_session,
            test_tenant.id,
            app_service.id,
            customer.id,
        )
        db_session.commit()

        # Fake QB customer payload (simulates what QB API returns)
        qb_customer = {
            "Id": "QB-CONFLICT-001",
            "DisplayName": customer.display_name,
            "SyncToken": "99",  # Changed — triggers conflict
            "GivenName": "John",
            "FamilyName": "Doe",
        }

        # Invoke the service method under test
        sync = QuickBooksSync(test_tenant.id, db_session)
        import asyncio

        conflict = asyncio.run(
            sync.queue_conflict(mapping, qb_customer, app_service.id)
        )

        # --- Assert: conflict record created ----------------------------------
        assert conflict is not None
        assert conflict.tenant_id == test_tenant.id
        assert conflict.status == "pending"

        # --- Assert: exactly ONE *pending* NotificationOutbox inserted --------
        # Filter by status='pending' to exclude any pre-existing 'sent' records
        # from seed data or previous integration test runs.
        outbox_records = db_session.exec(
            select(NotificationOutbox).where(
                NotificationOutbox.tenant_id == test_tenant.id,
                NotificationOutbox.channel == "email",
                NotificationOutbox.status == "pending",
            )
        ).all()

        assert len(outbox_records) == 1, (
            f"Expected 1 pending outbox record, found {len(outbox_records)}"
        )

        outbox = outbox_records[0]
        assert outbox.channel == "email"
        assert outbox.status == "pending"
        assert outbox.tenant_id == test_tenant.id
        assert customer.display_name in outbox.body


# ============================================================
# Test B — Dashboard Count
# ============================================================


class TestDashboardCount:
    """
    Seed 3 pending IntegrationSyncConflict rows, hit the dashboard endpoint,
    assert requires_attention_count == 3.
    """

    def test_dashboard_requires_attention_count_equals_3(
        self, client, db_session: Session, test_tenant
    ):
        """
        Test B: GET /integrations/sync-dashboard/test returns
        requires_attention_count == 3 when exactly 3 pending conflicts exist.
        """
        app_service = _seed_qb_app_service(db_session, test_tenant.id)

        for _ in range(3):
            customer = _seed_customer(db_session, test_tenant.id)
            _seed_conflict(db_session, test_tenant.id, app_service.id, customer.id)

        db_session.commit()

        response = client.get("/api/v1/integrations/sync-dashboard/test")

        assert response.status_code == 200, response.text
        data = response.json()
        assert "requires_attention_count" in data, (
            f"requires_attention_count missing from response: {data}"
        )
        assert data["requires_attention_count"] == 3, (
            f"Expected 3, got {data['requires_attention_count']}"
        )


# ============================================================
# Test C — Resolved Exclusion
# ============================================================


class TestResolvedExclusion:
    """
    Seed 3 pending conflicts, resolve one, re-hit endpoint and assert count == 2.
    Proves idx_isc_tenant_status filters correctly.
    """

    def test_resolved_conflict_excluded_from_dashboard_count(
        self, client, db_session: Session, test_tenant, test_user
    ):
        """
        Test C: After resolving one conflict (status='resolved_keep_internal'),
        requires_attention_count must drop to 2.
        """
        app_service = _seed_qb_app_service(db_session, test_tenant.id)

        conflicts = []
        for _ in range(3):
            customer = _seed_customer(db_session, test_tenant.id)
            conflict = _seed_conflict(
                db_session, test_tenant.id, app_service.id, customer.id
            )
            conflicts.append(conflict)

        db_session.commit()

        # Verify initial count == 3
        response = client.get("/api/v1/integrations/sync-dashboard/test")
        assert response.status_code == 200
        assert response.json()["requires_attention_count"] == 3

        # Resolve one conflict
        conflict_to_resolve = db_session.get(IntegrationSyncConflict, conflicts[0].id)
        conflict_to_resolve.status = "resolved_keep_internal"
        conflict_to_resolve.resolved_at = datetime.now(UTC)
        conflict_to_resolve.resolved_by = test_user.id
        db_session.add(conflict_to_resolve)
        db_session.commit()

        # Re-hit endpoint — count must be 2
        response = client.get("/api/v1/integrations/sync-dashboard/test")
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["requires_attention_count"] == 2, (
            f"Expected 2 after resolving one conflict, got {data['requires_attention_count']}"
        )
