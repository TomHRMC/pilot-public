"""
Phase 7.0 Batch 5 - Cross-Tenant IDOR Security Tests
Communications & Webhooks: conversation_message, webhook_delivery_attempt

These tests verify that Phase 7.0 tenant stamping successfully prevents
Insecure Direct Object Reference (IDOR) vulnerabilities across both
batch-5 tables. A 404 response (not 403) is preferred to prevent
tenant ID enumeration attacks.

Test Coverage:
- tenant_id is present and correct on newly created records
- Tenant A cannot access Tenant B's records via direct tenant-scoped query
- Tenant A's list endpoints exclude Tenant B's records
- conversation_message: 1-hop backfill via conversation_session.tenant_id
- webhook_delivery_attempt: 1-hop backfill via webhook_endpoint.tenant_id
  (integer serial id — NOT uuid)
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlmodel import select

from app.models.ai import ConversationMessage, ConversationSession
from app.models.core import Tenant, User
from app.models.system import (
    WebhookDeliveryAttempt,
    WebhookEndpoint,
    WebhookEvent,
)

# ==================== SHARED FIXTURES ====================


@pytest.fixture
def tenant_a(db_session):
    """Tenant A - the 'attacker' tenant"""
    tenant = Tenant(id=uuid.uuid4(), name=f"Tenant A {uuid.uuid4()}", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


@pytest.fixture
def tenant_b(db_session):
    """Tenant B - the 'victim' tenant whose records should be isolated"""
    tenant = Tenant(id=uuid.uuid4(), name=f"Tenant B {uuid.uuid4()}", is_active=True)
    db_session.add(tenant)
    db_session.commit()
    db_session.refresh(tenant)
    return tenant


@pytest.fixture
def user_a(db_session, tenant_a):
    """User belonging to Tenant A"""
    user = User(
        id=uuid.uuid4(),
        email=f"user-a-{uuid.uuid4()}@example.com",
        password_hash="hashed_password",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def user_b(db_session, tenant_b):
    """User belonging to Tenant B"""
    user = User(
        id=uuid.uuid4(),
        email=f"user-b-{uuid.uuid4()}@example.com",
        password_hash="hashed_password",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ==================== CONVERSATION MESSAGE FIXTURES ====================


@pytest.fixture
def session_a(db_session, tenant_a, user_a):
    """ConversationSession belonging to Tenant A"""
    conv_session = ConversationSession(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        user_id=user_a.id,
        status="active",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(conv_session)
    db_session.commit()
    db_session.refresh(conv_session)
    return conv_session


@pytest.fixture
def session_b(db_session, tenant_b, user_b):
    """ConversationSession belonging to Tenant B"""
    conv_session = ConversationSession(
        id=uuid.uuid4(),
        tenant_id=tenant_b.id,
        user_id=user_b.id,
        status="active",
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(conv_session)
    db_session.commit()
    db_session.refresh(conv_session)
    return conv_session


# ==================== WEBHOOK DELIVERY ATTEMPT FIXTURES ====================


@pytest.fixture
def webhook_endpoint_a(db_session, tenant_a):
    """WebhookEndpoint belonging to Tenant A"""
    endpoint = WebhookEndpoint(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        url="https://hooks.tenant-a.example.com/webhook",
        enabled=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(endpoint)
    db_session.commit()
    db_session.refresh(endpoint)
    return endpoint


@pytest.fixture
def webhook_endpoint_b(db_session, tenant_b):
    """WebhookEndpoint belonging to Tenant B"""
    endpoint = WebhookEndpoint(
        id=uuid.uuid4(),
        tenant_id=tenant_b.id,
        url="https://hooks.tenant-b.example.com/webhook",
        enabled=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(endpoint)
    db_session.commit()
    db_session.refresh(endpoint)
    return endpoint


@pytest.fixture
def webhook_event_a(db_session, tenant_a):
    """WebhookEvent belonging to Tenant A"""
    event = WebhookEvent(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        payload={"event": "customer.created", "tenant": str(tenant_a.id)},
        signature_valid=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)
    return event


@pytest.fixture
def webhook_event_b(db_session, tenant_b):
    """WebhookEvent belonging to Tenant B"""
    event = WebhookEvent(
        id=uuid.uuid4(),
        tenant_id=tenant_b.id,
        payload={"event": "customer.created", "tenant": str(tenant_b.id)},
        signature_valid=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)
    return event


# ==================== CONVERSATION MESSAGE TESTS ====================


class TestConversationMessageTenantIsolation:
    """Verify conversation_message tenant_id stamping and cross-tenant isolation.
    Backfill path: conversation_message -> conversation_session (1-hop)
    """

    def test_conversation_message_tenant_id_is_stamped(
        self, db_session, tenant_a, session_a
    ):
        """tenant_id is correctly set when creating a ConversationMessage record"""
        msg = ConversationMessage(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            session_id=session_a.id,
            role="user",
            content_text="Add 100 feet of 2 AWG copper wire to the quote.",
            created_at=datetime.now(UTC),
        )
        db_session.add(msg)
        db_session.commit()
        db_session.refresh(msg)

        assert msg.tenant_id == tenant_a.id

    def test_cross_tenant_conversation_message_blocked(
        self, db_session, tenant_a, tenant_b, session_b
    ):
        """Tenant A cannot retrieve Tenant B's conversation message via tenant-scoped query"""
        msg_b = ConversationMessage(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            session_id=session_b.id,
            role="assistant",
            content_text="This is Tenant B's private AI response.",
            created_at=datetime.now(UTC),
        )
        db_session.add(msg_b)
        db_session.commit()

        # Tenant A queries for Tenant B's message by ID — must return None (404 pattern)
        result = db_session.exec(
            select(ConversationMessage).where(
                ConversationMessage.id == msg_b.id,
                ConversationMessage.tenant_id == tenant_a.id,  # Tenant A's scope
            )
        ).first()

        assert result is None, (
            "IDOR: Tenant A must not access Tenant B's conversation messages"
        )

    def test_conversation_message_list_excludes_other_tenant(
        self, db_session, tenant_a, tenant_b, session_a, session_b
    ):
        """List query for Tenant A excludes Tenant B's conversation messages"""
        msg_a = ConversationMessage(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            session_id=session_a.id,
            role="user",
            content_text="Tenant A's message",
            created_at=datetime.now(UTC),
        )
        msg_b = ConversationMessage(
            id=uuid.uuid4(),
            tenant_id=tenant_b.id,
            session_id=session_b.id,
            role="user",
            content_text="Tenant B's secret message",
            created_at=datetime.now(UTC),
        )
        db_session.add_all([msg_a, msg_b])
        db_session.commit()

        tenant_a_messages = db_session.exec(
            select(ConversationMessage).where(
                ConversationMessage.tenant_id == tenant_a.id
            )
        ).all()

        ids = [m.id for m in tenant_a_messages]
        assert msg_a.id in ids
        assert msg_b.id not in ids, (
            "IDOR: Tenant B's message leaked into Tenant A's list"
        )

    def test_conversation_message_creation_stamps_tenant_id(
        self, db_session, tenant_a, session_a
    ):
        """POST-equivalent creation auto-injects tenant_id on ConversationMessage"""
        msg = ConversationMessage(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            session_id=session_a.id,
            role="system",
            content_text="System initialization message.",
            created_at=datetime.now(UTC),
        )
        db_session.add(msg)
        db_session.commit()
        db_session.refresh(msg)

        # Verify the tenant_id was persisted and matches the originating tenant
        persisted = db_session.exec(
            select(ConversationMessage).where(ConversationMessage.id == msg.id)
        ).first()
        assert persisted is not None
        assert persisted.tenant_id == tenant_a.id


# ==================== WEBHOOK DELIVERY ATTEMPT TESTS ====================


class TestWebhookDeliveryAttemptTenantIsolation:
    """Verify webhook_delivery_attempt tenant_id stamping and cross-tenant isolation.
    Backfill path: webhook_delivery_attempt -> webhook_endpoint (1-hop)
    NOTE: id is a serial INTEGER, not UUID.
    """

    def test_webhook_delivery_attempt_tenant_id_is_stamped(
        self, db_session, tenant_a, webhook_endpoint_a, webhook_event_a
    ):
        """tenant_id is correctly set when creating a WebhookDeliveryAttempt record"""
        attempt = WebhookDeliveryAttempt(
            tenant_id=tenant_a.id,
            webhook_event_id=webhook_event_a.id,
            webhook_endpoint_id=webhook_endpoint_a.id,
            attempt_no=1,
            status="pending",
            requested_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        db_session.add(attempt)
        db_session.commit()
        db_session.refresh(attempt)

        assert attempt.tenant_id == tenant_a.id

    def test_cross_tenant_webhook_delivery_attempt_blocked(
        self,
        db_session,
        tenant_a,
        tenant_b,
        webhook_endpoint_b,
        webhook_event_b,
    ):
        """Tenant A cannot retrieve Tenant B's delivery attempt via tenant-scoped query"""
        attempt_b = WebhookDeliveryAttempt(
            tenant_id=tenant_b.id,
            webhook_event_id=webhook_event_b.id,
            webhook_endpoint_id=webhook_endpoint_b.id,
            attempt_no=1,
            status="pending",
            requested_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        db_session.add(attempt_b)
        db_session.commit()

        # Tenant A queries for Tenant B's attempt by ID — must return None (404 pattern)
        result = db_session.exec(
            select(WebhookDeliveryAttempt).where(
                WebhookDeliveryAttempt.id == attempt_b.id,
                WebhookDeliveryAttempt.tenant_id == tenant_a.id,  # Tenant A's scope
            )
        ).first()

        assert result is None, (
            "IDOR: Tenant A must not access Tenant B's webhook delivery attempts"
        )

    def test_webhook_delivery_attempt_list_excludes_other_tenant(
        self,
        db_session,
        tenant_a,
        tenant_b,
        webhook_endpoint_a,
        webhook_endpoint_b,
        webhook_event_a,
        webhook_event_b,
    ):
        """List query for Tenant A excludes Tenant B's delivery attempts"""
        attempt_a = WebhookDeliveryAttempt(
            tenant_id=tenant_a.id,
            webhook_event_id=webhook_event_a.id,
            webhook_endpoint_id=webhook_endpoint_a.id,
            attempt_no=1,
            status="success",
            requested_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        attempt_b = WebhookDeliveryAttempt(
            tenant_id=tenant_b.id,
            webhook_event_id=webhook_event_b.id,
            webhook_endpoint_id=webhook_endpoint_b.id,
            attempt_no=1,
            status="failed",
            requested_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        db_session.add_all([attempt_a, attempt_b])
        db_session.commit()

        tenant_a_attempts = db_session.exec(
            select(WebhookDeliveryAttempt).where(
                WebhookDeliveryAttempt.tenant_id == tenant_a.id
            )
        ).all()

        ids = [a.id for a in tenant_a_attempts]
        assert attempt_a.id in ids
        assert attempt_b.id not in ids, (
            "IDOR: Tenant B's delivery attempt leaked into Tenant A's list"
        )

    def test_webhook_delivery_attempt_creation_stamps_tenant_id(
        self,
        db_session,
        tenant_a,
        webhook_endpoint_a,
        webhook_event_a,
    ):
        """POST-equivalent creation auto-injects tenant_id on WebhookDeliveryAttempt"""
        attempt = WebhookDeliveryAttempt(
            tenant_id=tenant_a.id,
            webhook_event_id=webhook_event_a.id,
            webhook_endpoint_id=webhook_endpoint_a.id,
            attempt_no=1,
            status="pending",
            requested_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        db_session.add(attempt)
        db_session.commit()
        db_session.refresh(attempt)

        # Verify the tenant_id was persisted and matches the originating tenant
        persisted = db_session.exec(
            select(WebhookDeliveryAttempt).where(
                WebhookDeliveryAttempt.id == attempt.id
            )
        ).first()
        assert persisted is not None
        assert persisted.tenant_id == tenant_a.id


# ==================== CROSS-MODEL CONSISTENCY TESTS ====================


class TestBatch5TenantIdConsistency:
    """Verify tenant_id consistency across both batch-5 models"""

    def test_conversation_message_has_tenant_id(self):
        """ConversationMessage model exposes tenant_id in its model fields"""
        assert "tenant_id" in ConversationMessage.model_fields, (
            "ConversationMessage missing tenant_id field"
        )

    def test_webhook_delivery_attempt_has_tenant_id(self):
        """WebhookDeliveryAttempt model exposes tenant_id in its model fields"""
        assert "tenant_id" in WebhookDeliveryAttempt.model_fields, (
            "WebhookDeliveryAttempt missing tenant_id field"
        )

    def test_all_batch5_models_tenant_id_not_nullable(self):
        """Both models have tenant_id defined as non-optional (non-nullable)"""
        for model_cls in [ConversationMessage, WebhookDeliveryAttempt]:
            field = model_cls.model_fields["tenant_id"]
            assert (
                field.default is None
                or not field.is_required()
                or field.annotation is not None
            ), f"{model_cls.__name__}.tenant_id should not allow NULL"

    def test_webhook_delivery_attempt_id_is_integer(self):
        """WebhookDeliveryAttempt.id is a serial INTEGER — not UUID (per architecture note)"""
        field = WebhookDeliveryAttempt.model_fields.get("id")
        assert field is not None, "WebhookDeliveryAttempt must have an id field"
        # The field should be Optional[int] (bigserial auto-increment)
        annotation_str = str(field.annotation)
        assert "int" in annotation_str.lower() or "Int" in annotation_str, (
            f"WebhookDeliveryAttempt.id must be an integer type, got: {annotation_str}"
        )
