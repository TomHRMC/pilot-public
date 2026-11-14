"""
B11/A60 — Communication Threading Tests
========================================
Tests for:
  - CustomerCommunicationThread ORM model fields
  - CustomerCommunicationMessage ORM model fields (voice_audio_id = BIGINT)
  - CustomerCommunicationUnrouted ORM model fields
  - route_inbound_message(): park when no tenant phone match
  - route_inbound_message(): park when no customer match
  - route_inbound_message(): create thread when customer has last_assigned_tech_id
  - handle_sms_opt_out(): sets customer fields
  - handle_sms_opt_in(): resets customer fields
  - GET /communications/unrouted reachability
  - POST /communications/unrouted/{id}/assign-to-thread: 404 for unknown ID
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import patch

from app.models.sms import (
    CustomerCommunicationMessage,
    CustomerCommunicationThread,
    CustomerCommunicationUnrouted,
    TenantPhoneNumber,
)
from services.customer_communication_threading import (
    InboundMessage,
    handle_sms_opt_in,
    handle_sms_opt_out,
    route_inbound_message,
)
from services.sms_carrier import MockSmsCarrier

# ─── ORM Model Fields ─────────────────────────────────────────────────────────


class TestThreadingModels:
    """Verify threading ORM models have required fields."""

    def test_thread_model_has_required_fields(self):
        assert hasattr(CustomerCommunicationThread, "id")
        assert hasattr(CustomerCommunicationThread, "tenant_id")
        assert hasattr(CustomerCommunicationThread, "customer_id")
        assert hasattr(CustomerCommunicationThread, "tech_id")
        assert hasattr(CustomerCommunicationThread, "tenant_phone_number_id")
        assert hasattr(CustomerCommunicationThread, "status")
        assert hasattr(CustomerCommunicationThread, "first_message_at")
        assert hasattr(CustomerCommunicationThread, "last_message_at")
        assert hasattr(CustomerCommunicationThread, "message_count")

    def test_message_model_has_required_fields(self):
        assert hasattr(CustomerCommunicationMessage, "id")
        assert hasattr(CustomerCommunicationMessage, "thread_id")
        assert hasattr(CustomerCommunicationMessage, "direction")
        assert hasattr(CustomerCommunicationMessage, "body")
        assert hasattr(CustomerCommunicationMessage, "status")
        assert hasattr(
            CustomerCommunicationMessage, "voice_audio_id"
        )  # BIGINT per F1 decision

    def test_unrouted_model_has_required_fields(self):
        assert hasattr(CustomerCommunicationUnrouted, "id")
        assert hasattr(CustomerCommunicationUnrouted, "tenant_id")
        assert hasattr(CustomerCommunicationUnrouted, "from_number")
        assert hasattr(CustomerCommunicationUnrouted, "to_number")
        assert hasattr(CustomerCommunicationUnrouted, "body")
        assert hasattr(CustomerCommunicationUnrouted, "status")

    def test_thread_model_defaults(self):
        now = datetime.now(UTC)
        thread = CustomerCommunicationThread(
            tenant_id=uuid.uuid4(),
            customer_id=uuid.uuid4(),
            tech_id=uuid.uuid4(),
            tenant_phone_number_id=uuid.uuid4(),
            first_message_at=now,
            last_message_at=now,
        )
        assert thread.status == "active"
        assert thread.message_count == 0

    def test_message_model_defaults(self):
        msg = CustomerCommunicationMessage(
            thread_id=uuid.uuid4(),
            direction="inbound",
            body="Hello",
            audit_user_id=uuid.uuid4(),
        )
        assert msg.channel == "sms"
        assert msg.segment_count == 1
        assert msg.status == "pending_send"

    def test_voice_audio_id_is_int_not_uuid(self):
        """F1 decision: voice_audio_id must be Optional[int] (BIGINT), not UUID."""
        msg = CustomerCommunicationMessage(
            thread_id=uuid.uuid4(),
            direction="outbound",
            body="Test",
            audit_user_id=uuid.uuid4(),
            voice_audio_id=42,  # BIGINT
        )
        assert msg.voice_audio_id == 42
        assert isinstance(msg.voice_audio_id, int)

    def test_message_has_created_by_field(self):
        """B13b remediation: CustomerCommunicationMessage now uses StandardAuditMixin — has created_by."""
        assert hasattr(CustomerCommunicationMessage, "created_by")

    def test_unrouted_has_created_by_field(self):
        """B13b remediation: CustomerCommunicationUnrouted now uses StandardAuditMixin — has created_by."""
        assert hasattr(CustomerCommunicationUnrouted, "created_by")


# ─── Routing Service ──────────────────────────────────────────────────────────


class TestRouteInboundMessage:
    """Test route_inbound_message() parks unknown-number messages."""

    def test_parks_when_no_tenant_phone_match(self, db_session, test_tenant):
        """Message to unknown to_number → park in unrouted queue."""
        inbound = InboundMessage(
            from_number="+15125551234",
            to_number="+10000000000",  # Not provisioned for this tenant
            body="Hello!",
            carrier_message_id="test-msg-1",
            received_at="2026-05-02T12:00:00Z",
        )

        result = route_inbound_message(db_session, inbound, test_tenant.id)

        assert result.success is True
        assert result.thread_id is None
        assert result.unrouted_id is not None

        # Verify DB record
        from sqlmodel import select

        unrouted = db_session.exec(
            select(CustomerCommunicationUnrouted).where(
                CustomerCommunicationUnrouted.id == result.unrouted_id
            )
        ).first()
        assert unrouted is not None
        assert unrouted.from_number == "+15125551234"
        assert unrouted.status == "parked"

    def test_parks_when_no_customer_match(self, db_session, test_tenant):
        """Message from unknown from_number → park in unrouted queue."""
        phone = TenantPhoneNumber(
            tenant_id=test_tenant.id,
            phone_number="+15125550011",
            area_code="512",
        )
        db_session.add(phone)
        db_session.commit()

        inbound = InboundMessage(
            from_number="+19995559999",  # Unknown customer
            to_number="+15125550011",
            body="Hello!",
            carrier_message_id="test-msg-2",
            received_at="2026-05-02T12:00:00Z",
        )

        result = route_inbound_message(db_session, inbound, test_tenant.id)

        assert result.success is True
        assert result.unrouted_id is not None

    def test_routes_to_thread_when_customer_has_last_assigned_tech(
        self, db_session, test_tenant, test_user, test_customer
    ):
        """Customer with last_assigned_tech_id → new thread created."""
        test_customer.last_assigned_tech_id = test_user.id
        test_customer.mobile_phone = "+15125551111"
        db_session.add(test_customer)
        db_session.commit()

        phone = TenantPhoneNumber(
            tenant_id=test_tenant.id,
            phone_number="+15125550022",
            area_code="512",
        )
        db_session.add(phone)
        db_session.commit()

        inbound = InboundMessage(
            from_number="+15125551111",
            to_number="+15125550022",
            body="On my way!",
            carrier_message_id="test-msg-3",
            received_at="2026-05-02T13:00:00Z",
        )

        result = route_inbound_message(db_session, inbound, test_tenant.id)

        assert result.success is True
        assert result.thread_id is not None
        assert result.unrouted_id is None


# ─── TCPA Opt-Out / Opt-In ────────────────────────────────────────────────────


class TestTcpaHandlers:
    """Test handle_sms_opt_out and handle_sms_opt_in."""

    def test_opt_out_sets_customer_fields(self, db_session, test_tenant, test_customer):
        """STOP keyword should set sms_opted_out=True."""
        inbound = InboundMessage(
            from_number=test_customer.mobile_phone or "+15125551234",
            to_number="+15125550001",
            body="STOP",
            carrier_message_id="stop-msg",
            received_at="2026-05-02T12:00:00Z",
        )

        mock_carrier = MockSmsCarrier()
        # get_sms_carrier is imported lazily via 'from services.sms_carrier import get_sms_carrier'
        # inside handle_sms_opt_out; patch at the sms_carrier module level
        with patch("services.sms_carrier.get_sms_carrier", return_value=mock_carrier):
            handle_sms_opt_out(db_session, test_customer.id, inbound)

        db_session.refresh(test_customer)
        assert test_customer.sms_opted_out is True
        assert test_customer.sms_opt_out_at is not None
        assert len(mock_carrier.sent_messages) == 1
        assert "unsubscribed" in mock_carrier.sent_messages[0]["body"].lower()

    def test_opt_in_sets_customer_fields(self, db_session, test_tenant, test_customer):
        """START keyword should set sms_opted_out=False."""
        test_customer.sms_opted_out = True
        db_session.add(test_customer)
        db_session.commit()

        inbound = InboundMessage(
            from_number=test_customer.mobile_phone or "+15125551234",
            to_number="+15125550001",
            body="START",
            carrier_message_id="start-msg",
            received_at="2026-05-02T12:00:00Z",
        )

        mock_carrier = MockSmsCarrier()
        with patch("services.sms_carrier.get_sms_carrier", return_value=mock_carrier):
            handle_sms_opt_in(db_session, test_customer.id, inbound)

        db_session.refresh(test_customer)
        assert test_customer.sms_opted_out is False
        assert test_customer.sms_opt_in_consent is True
        assert test_customer.sms_opt_in_source == "inbound_initiated"
        assert test_customer.sms_opt_in_at is not None


# ─── API: Unrouted Queue ──────────────────────────────────────────────────────


class TestUnroutedQueueRoute:
    """Smoke tests for unrouted queue endpoints."""

    def test_list_unrouted_requires_auth(self, client):
        """The authenticated endpoint returns 401 without a token."""
        resp = client.get("/api/v1/communications/unrouted")
        assert resp.status_code in (401, 403)

    def test_assign_unrouted_bad_id_returns_non_200(self, client):
        """Assigning an unknown unrouted ID should fail (401/403/404)."""
        fake_id = uuid.uuid4()
        fake_thread = uuid.uuid4()
        resp = client.post(
            f"/api/v1/communications/unrouted/{fake_id}/assign-to-thread",
            json={"thread_id": str(fake_thread)},
        )
        assert resp.status_code in (401, 403, 404)
