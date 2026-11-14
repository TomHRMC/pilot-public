"""
SIGNUP-C / Pathway C — Platform SMS Consent Tests
=================================================
Tests for:
  - user_sms_consent_audit migration: action CHECK accepts valid, rejects invalid;
    append-only (no updated_at column).
  - upsert_owner_sms_endpoint: consent=True → opted_in/pending + attested audit;
    consent=False → unknown/pending; re-call same phone does not duplicate;
    writes user.phone_number.
  - _send_platform_double_optin_sms_impl: opted_in → sends + double_opt_in_sent
    audit; not-opted-in → skipped; no sms endpoint → skipped; FROM = platform
    config number (not a tenant number).
  - webhooks_sms owner handlers: inbound YES from owner number → endpoint
    opted_in/verified + double_opt_in_confirmed audit; STOP → opted_out audit;
    customer path still works (regression).

Domain: notifications_comms (PRD §3.7)
"""

import hashlib
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import select

from app.models.communications import UserSmsConsentAudit
from app.models.core import User, UserEndpoint

pytestmark = [
    pytest.mark.domain_notifications_comms,
    pytest.mark.unit,
]

# tenant_user_status.code='active' id (MCP-verified, seeded platform row).
_ACTIVE_STATUS_ID = "5b67cfd3-ef42-4311-9516-a4eec8642628"


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _make_owner(db_session, test_tenant):
    """Create a fresh owner user + return (user, tenant)."""
    import uuid

    user = User(
        id=uuid.uuid4(),
        email=f"owner-{uuid.uuid4().hex[:8]}@test.local",
        first_name="Owner",
        last_name="Test",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    return user


def _make_inbound(body, from_number="+15125550100", to_number="+15125550001"):
    from services.sms_carrier import InboundMessage

    return InboundMessage(
        from_number=from_number,
        to_number=to_number,
        body=body,
        carrier_message_id="test-signup-c-msg",
        received_at="2026-07-31T12:00:00Z",
    )


# ─── 1. Migration: user_sms_consent_audit CHECK + append-only ────────────────


class TestUserSmsConsentAuditMigration:
    def test_accepts_each_valid_action(self, db_session, test_tenant):
        """Each valid action value inserts cleanly (CHECK passes)."""
        import uuid

        from app.models.communications import UserSmsConsentAudit

        user = _make_owner(db_session, test_tenant)
        for action in [
            "attested",
            "double_opt_in_sent",
            "double_opt_in_confirmed",
            "opted_out",
        ]:
            row = UserSmsConsentAudit(
                id=uuid.uuid4(),
                tenant_id=test_tenant.id,
                user_id=user.id,
                user_endpoint_id=None,
                action=action,
                consent_text_hash=hashlib.sha256(b"x").hexdigest(),
                ip_address="127.0.0.1",
                attested_at=datetime.now(UTC),
                created_at=datetime.now(UTC),
            )
            db_session.add(row)
        db_session.commit()

    def test_rejects_invalid_action(self, db_session, test_tenant):
        """An invalid action value violates the CHECK constraint."""
        import uuid

        from sqlalchemy.exc import IntegrityError

        from app.models.communications import UserSmsConsentAudit

        user = _make_owner(db_session, test_tenant)
        row = UserSmsConsentAudit(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            user_id=user.id,
            action="bogus_action",
            consent_text_hash=hashlib.sha256(b"x").hexdigest(),
            attested_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        db_session.add(row)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()

    def test_no_updated_at_column(self):
        """Append-only: the model must NOT declare updated_at."""
        cols = {c.name for c in UserSmsConsentAudit.__table__.columns}
        assert "updated_at" not in cols
        assert "created_at" in cols


# ─── 2. upsert_owner_sms_endpoint ────────────────────────────────────────────


class TestUpsertOwnerSmsEndpoint:
    def test_consent_true_sets_opted_in_pending_and_attested_audit(
        self, db_session, test_tenant
    ):
        from services.notification_endpoints import upsert_owner_sms_endpoint

        user = _make_owner(db_session, test_tenant)
        disclosure = hashlib.sha256(b"disclosure").hexdigest()

        endpoint = upsert_owner_sms_endpoint(
            db_session,
            user_id=user.id,
            tenant_id=test_tenant.id,
            phone="+15125550100",
            consent=True,
            ip="127.0.0.1",
            disclosure_hash=disclosure,
        )

        assert endpoint.channel == "sms"
        assert endpoint.value == "+15125550100"
        assert endpoint.consent_status == "opted_in"
        assert endpoint.verification_status == "pending"

        # Audit row written with action='attested'
        audits = db_session.exec(
            select(UserSmsConsentAudit).where(
                UserSmsConsentAudit.user_id == user.id,
                UserSmsConsentAudit.action == "attested",
            )
        ).all()
        assert len(audits) == 1
        assert audits[0].consent_text_hash == disclosure
        assert audits[0].user_endpoint_id == endpoint.id

    def test_consent_false_sets_unknown_pending(self, db_session, test_tenant):
        from services.notification_endpoints import upsert_owner_sms_endpoint

        user = _make_owner(db_session, test_tenant)

        endpoint = upsert_owner_sms_endpoint(
            db_session,
            user_id=user.id,
            tenant_id=test_tenant.id,
            phone="+15125550101",
            consent=False,
            ip="127.0.0.1",
            disclosure_hash=hashlib.sha256(b"d").hexdigest(),
        )

        assert endpoint.consent_status == "unknown"
        assert endpoint.verification_status == "pending"

    def test_recall_same_phone_no_duplicate(self, db_session, test_tenant):
        """Value-scoped DELETE+INSERT: re-call with same phone → one endpoint."""
        from services.notification_endpoints import upsert_owner_sms_endpoint

        user = _make_owner(db_session, test_tenant)
        phone = "+15125550102"
        disclosure = hashlib.sha256(b"d").hexdigest()

        upsert_owner_sms_endpoint(
            db_session,
            user_id=user.id,
            tenant_id=test_tenant.id,
            phone=phone,
            consent=True,
            ip="127.0.0.1",
            disclosure_hash=disclosure,
        )
        upsert_owner_sms_endpoint(
            db_session,
            user_id=user.id,
            tenant_id=test_tenant.id,
            phone=phone,
            consent=True,
            ip="127.0.0.1",
            disclosure_hash=disclosure,
        )

        endpoints = db_session.exec(
            select(UserEndpoint).where(
                UserEndpoint.user_id == user.id,
                UserEndpoint.channel == "sms",
                UserEndpoint.value == phone,
            )
        ).all()
        assert len(endpoints) == 1

    def test_writes_user_phone_number(self, db_session, test_tenant):
        from services.notification_endpoints import upsert_owner_sms_endpoint

        user = _make_owner(db_session, test_tenant)
        upsert_owner_sms_endpoint(
            db_session,
            user_id=user.id,
            tenant_id=test_tenant.id,
            phone="+15125550103",
            consent=False,
            ip=None,
            disclosure_hash=hashlib.sha256(b"d").hexdigest(),
        )
        db_session.refresh(user)
        assert user.phone_number == "+15125550103"


# ─── 3. _send_platform_double_optin_sms_impl ────────────────────────────────


class TestPlatformDoubleOptinImpl:
    def test_opted_in_sends_and_writes_audit(
        self, db_session, test_tenant, platform_sms_templates
    ):
        from services.notification_endpoints import upsert_owner_sms_endpoint
        from services.platform_sms_templates import get_platform_sms_body
        from tasks.sms_compliance_platform import _send_platform_double_optin_sms_impl

        user = _make_owner(db_session, test_tenant)
        upsert_owner_sms_endpoint(
            db_session,
            user_id=user.id,
            tenant_id=test_tenant.id,
            phone="+15125550200",
            consent=True,
            ip="127.0.0.1",
            disclosure_hash=hashlib.sha256(b"d").hexdigest(),
        )
        db_session.commit()  # persist so the task's own session sees it

        mock_carrier = MagicMock()
        mock_carrier.send_message.return_value = MagicMock(
            status="sent", carrier_message_id="mock-id", error_message=None
        )

        with (
            patch(
                "tasks.sms_compliance_platform.get_sms_carrier",
                return_value=mock_carrier,
            ),
            patch("tasks.sms_compliance_platform.Session") as mock_session_cls,
            patch("core.config.settings.PILOT_PLATFORM_SMS_NUMBER", "+15125559999"),
        ):
            mock_session_cls.return_value.__enter__.return_value = db_session
            result = _send_platform_double_optin_sms_impl(
                str(user.id), str(test_tenant.id)
            )

        assert result["status"] == "sent"
        # FROM = platform number, not a tenant number
        call_kwargs = mock_carrier.send_message.call_args
        assert call_kwargs.kwargs["from_number"] == "+15125559999"
        assert call_kwargs.kwargs["to_number"] == "+15125550200"
        # Body matches the DB-loaded verbatim template
        expected_body = get_platform_sms_body(db_session, "platform_sms_double_optin")
        assert call_kwargs.kwargs["body"] == expected_body

        # Audit row written
        audits = db_session.exec(
            select(UserSmsConsentAudit).where(
                UserSmsConsentAudit.user_id == user.id,
                UserSmsConsentAudit.action == "double_opt_in_sent",
            )
        ).all()
        assert len(audits) == 1

    def test_not_opted_in_skipped(
        self, db_session, test_tenant, platform_sms_templates
    ):
        from services.notification_endpoints import upsert_owner_sms_endpoint
        from tasks.sms_compliance_platform import _send_platform_double_optin_sms_impl

        user = _make_owner(db_session, test_tenant)
        upsert_owner_sms_endpoint(
            db_session,
            user_id=user.id,
            tenant_id=test_tenant.id,
            phone="+15125550201",
            consent=False,
            ip=None,
            disclosure_hash=hashlib.sha256(b"d").hexdigest(),
        )
        db_session.commit()

        mock_carrier = MagicMock()
        with (
            patch(
                "tasks.sms_compliance_platform.get_sms_carrier",
                return_value=mock_carrier,
            ),
            patch("tasks.sms_compliance_platform.Session") as mock_session_cls,
            patch("core.config.settings.PILOT_PLATFORM_SMS_NUMBER", "+15125559999"),
        ):
            mock_session_cls.return_value.__enter__.return_value = db_session
            result = _send_platform_double_optin_sms_impl(
                str(user.id), str(test_tenant.id)
            )

        assert result["status"] == "skipped"
        assert result["reason"] == "not_opted_in"
        mock_carrier.send_message.assert_not_called()

    def test_no_sms_endpoint_skipped(
        self, db_session, test_tenant, platform_sms_templates
    ):
        from tasks.sms_compliance_platform import _send_platform_double_optin_sms_impl

        user = _make_owner(db_session, test_tenant)
        db_session.commit()

        mock_carrier = MagicMock()
        with (
            patch(
                "tasks.sms_compliance_platform.get_sms_carrier",
                return_value=mock_carrier,
            ),
            patch("tasks.sms_compliance_platform.Session") as mock_session_cls,
        ):
            mock_session_cls.return_value.__enter__.return_value = db_session
            result = _send_platform_double_optin_sms_impl(
                str(user.id), str(test_tenant.id)
            )

        assert result["status"] == "skipped"
        assert result["reason"] == "no_sms_endpoint"
        mock_carrier.send_message.assert_not_called()


# ─── 4. webhooks_sms owner handlers ─────────────────────────────────────────


class TestWebhookOwnerHandlers:
    def test_yes_from_owner_optin_confirmed(
        self, db_session, test_tenant, platform_sms_templates
    ):
        """Inbound YES from owner number → endpoint opted_in/verified + audit."""
        from api.routes.webhooks_sms import (
            _handle_owner_opt_in,
        )
        from services.notification_endpoints import upsert_owner_sms_endpoint

        user = _make_owner(db_session, test_tenant)
        # Attach user to tenant via TenantUser so the audit tenant_id resolves.
        # role_code + status_id are NOT NULL (MCP-verified).
        from app.models.auth import TenantUser

        db_session.add(
            TenantUser(
                tenant_id=test_tenant.id,
                user_id=user.id,
                role_code="owner",
                status_id=_ACTIVE_STATUS_ID,
                is_active=True,
            )
        )
        db_session.flush()

        endpoint = upsert_owner_sms_endpoint(
            db_session,
            user_id=user.id,
            tenant_id=test_tenant.id,
            phone="+15125550300",
            consent=True,
            ip="127.0.0.1",
            disclosure_hash=hashlib.sha256(b"d").hexdigest(),
        )
        db_session.commit()

        inbound = _make_inbound("YES", from_number="+15125550300")
        mock_carrier = MagicMock()
        with patch("services.sms_carrier.get_sms_carrier", return_value=mock_carrier):
            _handle_owner_opt_in(db_session, endpoint, inbound)

        db_session.refresh(endpoint)
        assert endpoint.consent_status == "opted_in"
        assert endpoint.verification_status == "verified"
        assert endpoint.verified_at is not None

        audits = db_session.exec(
            select(UserSmsConsentAudit).where(
                UserSmsConsentAudit.user_id == user.id,
                UserSmsConsentAudit.action == "double_opt_in_confirmed",
            )
        ).all()
        assert len(audits) == 1

        # Reply sent
        mock_carrier.send_message.assert_called_once()
        body = mock_carrier.send_message.call_args.kwargs["body"]
        assert "opted in to account, billing & security alerts" in body

    def test_stop_from_owner_optout(
        self, db_session, test_tenant, platform_sms_templates
    ):
        """Inbound STOP from owner number → endpoint opted_out + audit."""
        from api.routes.webhooks_sms import _handle_owner_opt_out
        from services.notification_endpoints import upsert_owner_sms_endpoint

        user = _make_owner(db_session, test_tenant)
        from app.models.auth import TenantUser

        db_session.add(
            TenantUser(
                tenant_id=test_tenant.id,
                user_id=user.id,
                role_code="owner",
                status_id=_ACTIVE_STATUS_ID,
                is_active=True,
            )
        )
        db_session.flush()

        endpoint = upsert_owner_sms_endpoint(
            db_session,
            user_id=user.id,
            tenant_id=test_tenant.id,
            phone="+15125550301",
            consent=True,
            ip="127.0.0.1",
            disclosure_hash=hashlib.sha256(b"d").hexdigest(),
        )
        db_session.commit()

        inbound = _make_inbound("STOP", from_number="+15125550301")
        mock_carrier = MagicMock()
        with patch("services.sms_carrier.get_sms_carrier", return_value=mock_carrier):
            _handle_owner_opt_out(db_session, endpoint, inbound)

        db_session.refresh(endpoint)
        assert endpoint.consent_status == "opted_out"

        audits = db_session.exec(
            select(UserSmsConsentAudit).where(
                UserSmsConsentAudit.user_id == user.id,
                UserSmsConsentAudit.action == "opted_out",
            )
        ).all()
        assert len(audits) == 1

        mock_carrier.send_message.assert_called_once()
        body = mock_carrier.send_message.call_args.kwargs["body"]
        assert "unsubscribed" in body

    def test_customer_path_still_works(self, db_session, test_tenant):
        """Regression: the customer STOP path (Pathway B) is unaffected."""
        # Create a customer with a mobile phone
        from app.models.crm import Customer
        from services.customer_communication_threading import handle_sms_opt_out

        customer = Customer(
            tenant_id=test_tenant.id,
            display_name="Regression Customer",
            mobile_phone="+15125550400",
            type="person",
        )
        db_session.add(customer)
        db_session.commit()

        inbound = _make_inbound("STOP", from_number="+15125550400")
        mock_carrier = MagicMock()
        with patch("services.sms_carrier.get_sms_carrier", return_value=mock_carrier):
            handle_sms_opt_out(db_session, customer.id, inbound)

        db_session.refresh(customer)
        assert customer.sms_opted_out is True
        assert customer.sms_verification_status == "opted_out"
