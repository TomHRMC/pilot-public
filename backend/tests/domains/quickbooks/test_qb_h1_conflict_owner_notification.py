"""
QB-H1 Task 4 — Conflict Email to Owner: Verify + Close

PRD §3.9 requires the ``qb_sync_conflict`` notification to reach the tenant
owner (SMS or email). This test proves the path: ``queue_conflict`` enqueues
a ``qb_sync_conflict`` notification that resolves to the **tenant owner's**
email endpoint (not all users, not in-app only).

The existing ``batch_1e`` test proves the outbox record is created with
``channel='email'``. This test goes one step further: it asserts the
``to_address`` field resolves to the **owner's** email address specifically.

Batch: QB-H1
Design: dev-docs/architecture-design/batch-designs/batch-qb-h1-design.md §C task 4
"""

import asyncio
import uuid
from datetime import UTC, datetime

import pytest
from sqlmodel import Session, select

from app.models.auth import TenantUser, TenantUserStatus
from app.models.core import EntityType, User
from app.models.crm import Customer
from app.models.system import (
    AppService,
    IntegrationSyncMapping,
    NotificationOutbox,
    NotificationType,
)
from services.quickbooks_sync import QuickBooksSync

pytestmark = [
    pytest.mark.domain_quickbooks,
    pytest.mark.unit,
]


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


def _seed_owner_user(db_session: Session, tenant_id: uuid.UUID) -> User:
    """Create an owner user for the test tenant with a known email."""
    owner_email = f"qb-owner-{uuid.uuid4().hex[:8]}@pilot-test.com"

    # Create a tenant_user_status for this tenant (if not exists)
    status = db_session.exec(
        select(TenantUserStatus).where(
            TenantUserStatus.tenant_id == tenant_id,
            TenantUserStatus.code == "active",
        )
    ).first()
    if not status:
        status = TenantUserStatus(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            code="active",
            name="Active",
            is_default=True,
            is_active=True,
        )
        db_session.add(status)
        db_session.flush()

    user = User(
        id=uuid.uuid4(),
        email=owner_email,
        first_name="QB",
        last_name="Owner",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    tenant_user = TenantUser(
        tenant_id=tenant_id,
        user_id=user.id,
        role_code="owner",
        status_id=status.id,
        is_active=True,
    )
    db_session.add(tenant_user)
    db_session.flush()
    return user


class TestConflictEmailToOwner:
    """Prove queue_conflict resolves the notification to the tenant owner's email."""

    def test_conflict_notification_resolves_to_owner_email(
        self, db_session: Session, test_tenant
    ):
        """
        Trigger queue_conflict and assert the enqueued NotificationOutbox
        ``to_address`` matches the tenant owner's email — not a generic
        fallback, not all users.
        """
        # Seed prerequisites
        _ensure_entity_type(db_session, "customer")
        _ensure_notification_type(db_session, "qb_sync_conflict", audience="tenant")

        # Create an owner user for the test tenant (the seeded test tenant may
        # already have an owner from seed_test_tenant.py — that's fine; the
        # assertion verifies the outbox resolves to *an* owner, not a specific one)
        owner = _seed_owner_user(db_session, test_tenant.id)

        # Collect all known owner emails for this tenant (seeded + test-created)
        all_owner_emails = set(
            db_session.exec(
                select(User.email)
                .join(TenantUser, TenantUser.user_id == User.id)
                .where(
                    TenantUser.tenant_id == test_tenant.id,
                    TenantUser.role_code == "owner",
                    TenantUser.is_active == True,
                )
            ).all()
        )

        # Create QB app_service + customer + mapping
        app_service = AppService(
            tenant_id=test_tenant.id,
            name="QuickBooks Online",
            category_code="accounting",
            provider_code="quickbooks",
            is_active=True,
        )
        db_session.add(app_service)
        db_session.flush()

        customer = Customer(
            tenant_id=test_tenant.id,
            type="person",
            display_name=f"Conflict Test Customer {uuid.uuid4().hex[:6]}",
            first_name="Conflict",
            last_name="Test",
            is_active=True,
        )
        db_session.add(customer)
        db_session.flush()

        mapping = IntegrationSyncMapping(
            tenant_id=test_tenant.id,
            app_service_id=app_service.id,
            entity_type_code="customer",
            entity_id=customer.id,
            external_id="QB-CONFLICT-OWNER-001",
            sync_preference="bi_directional",
            internal_version_token="v1",
            external_version_token="0",
            last_synced_at=datetime.now(UTC),
        )
        db_session.add(mapping)
        db_session.commit()

        # Fake QB customer payload (SyncToken changed → triggers conflict)
        qb_customer = {
            "Id": "QB-CONFLICT-OWNER-001",
            "DisplayName": customer.display_name,
            "SyncToken": "99",
            "GivenName": "Conflict",
            "FamilyName": "Test",
        }

        # Invoke the service method under test
        sync = QuickBooksSync(test_tenant.id, db_session)
        conflict = asyncio.run(
            sync.queue_conflict(mapping, qb_customer, app_service.id)
        )

        # Assert conflict record created
        assert conflict is not None
        assert conflict.tenant_id == test_tenant.id
        assert conflict.status == "pending"

        # Assert exactly ONE pending email outbox record for this conflict
        outbox_records = db_session.exec(
            select(NotificationOutbox).where(
                NotificationOutbox.tenant_id == test_tenant.id,
                NotificationOutbox.channel == "email",
                NotificationOutbox.status == "pending",
            )
        ).all()

        # Filter to the one created by this conflict (by subject containing
        # the customer display_name — the queue_conflict subject format)
        conflict_outbox = [
            o for o in outbox_records if customer.display_name in (o.body or "")
        ]
        assert len(conflict_outbox) == 1, (
            f"Expected 1 conflict outbox for this customer, "
            f"found {len(conflict_outbox)}"
        )

        outbox = conflict_outbox[0]

        # THE KEY ASSERTION: to_address must be an owner's email (not a generic
        # fallback, not a non-owner user). The seeded test tenant may have
        # multiple owners; the resolution picks the first active one.
        assert outbox.to_address in all_owner_emails, (
            f"Expected to_address to be one of the tenant owner emails "
            f"({all_owner_emails}), got to_address={outbox.to_address}"
        )
        # Must NOT be the generic fallback
        assert outbox.to_address != "system@pilot.local", (
            "to_address must resolve to a real owner, not the system fallback"
        )

        # The body must mention the customer's display_name
        assert customer.display_name in outbox.body
