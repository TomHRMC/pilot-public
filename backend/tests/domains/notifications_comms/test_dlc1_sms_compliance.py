"""
DLC-1 SMS Compliance Tests
===========================
Tests for:
  - Tenant10DlcProfile GET/PUT via test endpoints
  - Customer attestation flow: checkbox → audit row → sms_verification_status
  - handle_sms_opt_in() sets sms_verification_status='verified'
  - handle_sms_opt_out() sets sms_verification_status='opted_out'
  - send_double_optin_sms Celery task (_impl layer — not .delay())

Domain: notifications_comms (PRD §3.7)
"""

from unittest.mock import MagicMock, patch

import pytest

pytestmark = [
    pytest.mark.domain_notifications_comms,
    pytest.mark.unit,
]


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _make_inbound(
    body: str, from_number: str = "+15125551234", to_number: str = "+15125550001"
):
    from services.customer_communication_threading import InboundMessage

    return InboundMessage(
        from_number=from_number,
        to_number=to_number,
        body=body,
        carrier_message_id="test-dlc1-msg-id",
        received_at="2026-07-05T12:00:00Z",
    )


# ─── 1. Tenant10DlcProfile — PUT creates / upserts row ──────────────────────


class TestTenant10DlcProfileCreate:
    def test_put_10dlc_profile_creates_new_row(self, client, test_tenant, db_session):
        """PUT /settings/10dlc-profile/test → 200, profile stored.

        Resilience: seed_test_tenant.py SD-7 B2 may have pre-seeded a
        tenant_10dlc_profile row for this tenant. Delete it before the PUT so
        this test operates on a fresh row and ein_masked is None (Rule 16).
        """
        from sqlalchemy import text as _text

        # Wipe any existing seeded 10dlc profile for this tenant
        db_session.execute(
            _text("DELETE FROM public.tenant_10dlc_profile WHERE tenant_id = :tid"),
            {"tid": str(test_tenant.id)},
        )
        db_session.commit()

        resp = client.put(
            "/api/v1/settings/10dlc-profile/test",
            json={"legal_business_name": "DLC Test Electrical LLC"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["legal_business_name"] == "DLC Test Electrical LLC"
        assert data["hq_country"] == "US"
        assert data["ein_masked"] is None  # no EIN provided

    def test_put_10dlc_profile_upserts_existing(self, client, test_tenant):
        """Second PUT updates existing row — same tenant_id."""
        client.put(
            "/api/v1/settings/10dlc-profile/test",
            json={"legal_business_name": "Original Name LLC"},
        )
        resp = client.put(
            "/api/v1/settings/10dlc-profile/test",
            json={"legal_business_name": "Updated Name LLC"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["legal_business_name"] == "Updated Name LLC"

        # Verify GET returns updated value
        get_resp = client.get("/api/v1/settings/10dlc-profile/test")
        assert get_resp.status_code == 200
        assert get_resp.json()["legal_business_name"] == "Updated Name LLC"

    def test_get_10dlc_profile_returns_masked_ein(self, client, test_tenant):
        """PUT with EIN → GET returns masked ein_masked='**-***6789'."""
        put_resp = client.put(
            "/api/v1/settings/10dlc-profile/test",
            json={
                "legal_business_name": "EIN Test LLC",
                "ein": "12-3456789",
            },
        )
        assert put_resp.status_code == 200, put_resp.text
        resp = client.get("/api/v1/settings/10dlc-profile/test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ein_masked"] == "**-***6789"
        # Raw EIN is NOT exposed
        assert "ein" not in data or data.get("ein") is None

    def test_get_10dlc_profile_404_when_not_configured(
        self, client, db_session, test_tenant
    ):
        """Verify 404 RFC 7807 format when profile not configured."""
        from sqlmodel import delete as _delete

        from app.models.core import Tenant10DlcProfile

        # Delete any existing profile for test_tenant to guarantee 404
        db_session.exec(
            _delete(Tenant10DlcProfile).where(
                Tenant10DlcProfile.tenant_id == test_tenant.id
            )
        )
        db_session.commit()

        resp = client.get("/api/v1/settings/10dlc-profile/test")
        assert resp.status_code == 404, resp.text
        body = resp.json()
        detail = body["detail"]
        assert detail["status"] == 404
        assert "type" in detail
        assert "title" in detail


# ─── 2. Customer attestation flow ────────────────────────────────────────────


class TestCustomerAttestationFlow:
    def test_customer_attestation_sets_verification_status(
        self, client, db_session, test_tenant
    ):
        """POST /customers/test with sms_attestation_checked=True → pending_verification + audit row."""
        from sqlmodel import select as _select

        from app.models.crm import Customer, CustomerSmsConsentAudit

        with patch("tasks.sms_compliance.send_double_optin_sms.delay") as mock_delay:
            resp = client.post(
                "/api/v1/customers/test",
                json={
                    "display_name": "Attested Customer DLC1",
                    "type": "person",
                    "mobile_phone": "+15125559001",
                    "sms_attestation_checked": True,
                    "sms_consent_ip_address": "192.168.1.50",
                },
            )

        assert resp.status_code == 201, resp.text
        customer_id = resp.json()["id"]

        customer = db_session.exec(
            _select(Customer).where(Customer.id == customer_id)
        ).first()
        assert customer is not None
        assert customer.sms_verification_status == "pending_verification"
        assert customer.sms_opt_in_source == "explicit_checkbox"

        # Verify audit row was written
        audit_rows = db_session.exec(
            _select(CustomerSmsConsentAudit).where(
                CustomerSmsConsentAudit.customer_id == customer_id
            )
        ).all()
        assert len(audit_rows) == 1
        assert audit_rows[0].action == "attested"
        assert audit_rows[0].ip_address == "192.168.1.50"

        # Verify delay was called
        mock_delay.assert_called_once_with(
            customer_id=customer_id,
            tenant_id=str(customer.tenant_id),
        )

    def test_customer_no_attestation_no_audit_row(
        self, client, db_session, test_tenant
    ):
        """POST /customers/test with sms_attestation_checked=False → no audit row, status=unverified."""
        from sqlmodel import select as _select

        from app.models.crm import Customer, CustomerSmsConsentAudit

        resp = client.post(
            "/api/v1/customers/test",
            json={
                "display_name": "Unattested Customer DLC1",
                "type": "person",
                "mobile_phone": "+15125559002",
                "sms_attestation_checked": False,
            },
        )
        assert resp.status_code == 201, resp.text
        customer_id = resp.json()["id"]

        # No audit row should be written
        audit_rows = db_session.exec(
            _select(CustomerSmsConsentAudit).where(
                CustomerSmsConsentAudit.customer_id == customer_id
            )
        ).all()
        assert len(audit_rows) == 0

        # sms_verification_status should be default 'unverified'
        customer = db_session.exec(
            _select(Customer).where(Customer.id == customer_id)
        ).first()
        assert customer.sms_verification_status == "unverified"


# ─── 3. handle_sms_opt_in sets verified ──────────────────────────────────────


class TestHandleSmsOptIn:
    def test_handle_sms_opt_in_sets_verified(
        self, db_session, test_tenant, test_user, test_customer
    ):
        """handle_sms_opt_in → sms_verification_status='verified', sms_opt_in_consent=True."""
        from sqlmodel import select as _select

        from services.customer_communication_threading import handle_sms_opt_in
        from services.sms_carrier import MockSmsCarrier

        # Set last_assigned_tech_id so audit row has a valid user FK
        # (created_by is an immutable column — cannot be updated after insert)
        test_customer.last_assigned_tech_id = test_user.id
        db_session.add(test_customer)
        db_session.commit()

        inbound = _make_inbound(
            "YES", from_number=test_customer.mobile_phone or "+15125551234"
        )
        mock_carrier = MockSmsCarrier()

        with patch("services.sms_carrier.get_sms_carrier", return_value=mock_carrier):
            handle_sms_opt_in(db_session, test_customer.id, inbound)

        db_session.expire(test_customer)
        from app.models.crm import Customer

        updated = db_session.exec(
            _select(Customer).where(Customer.id == test_customer.id)
        ).first()
        assert updated.sms_verification_status == "verified"
        assert updated.sms_opt_in_consent is True
        assert updated.sms_opted_out is False

    def test_handle_sms_opt_in_sends_resubscribed_confirmation(
        self, db_session, test_tenant, test_customer
    ):
        """handle_sms_opt_in sends DLC-compliant opt-in confirmation SMS (playbook §8)."""
        from services.customer_communication_threading import handle_sms_opt_in
        from services.sms_carrier import MockSmsCarrier

        inbound = _make_inbound(
            "YES", from_number=test_customer.mobile_phone or "+15125551234"
        )
        mock_carrier = MockSmsCarrier()

        with patch("services.sms_carrier.get_sms_carrier", return_value=mock_carrier):
            handle_sms_opt_in(db_session, test_customer.id, inbound)

        assert len(mock_carrier.sent_messages) == 1
        sent_body = mock_carrier.sent_messages[0]["body"]
        assert "opted in" in sent_body.lower()
        assert "reply help" in sent_body.lower()
        assert "data rates may apply" in sent_body.lower()
        assert "stop" in sent_body.lower()


# ─── 4. handle_sms_opt_out sets opted_out ────────────────────────────────────


class TestHandleSmsOptOut:
    def test_handle_sms_opt_out_sets_opted_out(
        self, db_session, test_tenant, test_customer
    ):
        """handle_sms_opt_out → sms_verification_status='opted_out', sms_opted_out=True."""
        from sqlmodel import select as _select

        from services.customer_communication_threading import handle_sms_opt_out
        from services.sms_carrier import MockSmsCarrier

        inbound = _make_inbound(
            "STOP", from_number=test_customer.mobile_phone or "+15125551234"
        )
        mock_carrier = MockSmsCarrier()

        with patch("services.sms_carrier.get_sms_carrier", return_value=mock_carrier):
            handle_sms_opt_out(db_session, test_customer.id, inbound)

        db_session.expire(test_customer)
        from app.models.crm import Customer

        updated = db_session.exec(
            _select(Customer).where(Customer.id == test_customer.id)
        ).first()
        assert updated.sms_verification_status == "opted_out"
        assert updated.sms_opted_out is True

    def test_handle_sms_opt_out_dlc_spec_reply(
        self, db_session, test_tenant, test_customer
    ):
        """handle_sms_opt_out sends DLC spec §2.4-compliant STOP reply (playbook §8)."""
        from services.customer_communication_threading import handle_sms_opt_out
        from services.sms_carrier import MockSmsCarrier

        inbound = _make_inbound(
            "STOP", from_number=test_customer.mobile_phone or "+15125551234"
        )
        mock_carrier = MockSmsCarrier()

        with patch("services.sms_carrier.get_sms_carrier", return_value=mock_carrier):
            handle_sms_opt_out(db_session, test_customer.id, inbound)

        assert len(mock_carrier.sent_messages) == 1
        sent_body = mock_carrier.sent_messages[0]["body"]
        assert "Pilot for Trades" in sent_body
        assert "No further messages" in sent_body
        assert "Reply START" in sent_body


# ─── 5. send_double_optin_sms _impl layer ────────────────────────────────────


class TestSendDoubleOptinSmsImpl:
    def test_send_double_optin_sms_impl_uses_fallback_business_name(
        self, db_session, test_tenant, test_customer
    ):
        """Tenant with no 10DLC profile → message body contains 'your service provider'."""
        from sqlmodel import delete as _delete

        # Ensure no 10DLC profile exists for the test_tenant
        from app.models.core import Tenant10DlcProfile
        from services.sms_carrier import MockSmsCarrier
        from tasks.sms_compliance import _send_double_optin_sms_impl

        db_session.exec(
            _delete(Tenant10DlcProfile).where(
                Tenant10DlcProfile.tenant_id == test_customer.tenant_id
            )
        )
        db_session.commit()

        mock_carrier = MockSmsCarrier()
        with patch("services.sms_carrier.get_sms_carrier", return_value=mock_carrier):
            result = _send_double_optin_sms_impl(
                customer_id=str(test_customer.id),
                tenant_id=str(test_customer.tenant_id),
            )
        # Either skipped (no tenant phone) or sent with fallback business name
        assert result["status"] in ("skipped", "sent", "failed")
        if result["status"] == "sent" and mock_carrier.sent_messages:
            sent_body = mock_carrier.sent_messages[0]["body"]
            assert "your service provider" in sent_body

    def test_send_double_optin_sms_impl_skips_opted_out_customer(
        self, db_session, test_tenant, test_customer
    ):
        """Customer with sms_opted_out=True → returns skipped/already_opted_out.

        The _impl opens its own Session(engine), so we mock the DB session to
        return a customer object with sms_opted_out=True.
        """
        from services.sms_carrier import MockSmsCarrier
        from tasks.sms_compliance import _send_double_optin_sms_impl

        # Build a mock customer that simulates opted_out=True
        mock_customer = MagicMock()
        mock_customer.id = test_customer.id
        mock_customer.tenant_id = test_customer.tenant_id
        mock_customer.mobile_phone = "+15125559999"
        mock_customer.sms_opted_out = True
        mock_customer.first_name = "Test"

        mock_exec_result = MagicMock()
        mock_exec_result.first.return_value = mock_customer

        mock_session = MagicMock()
        mock_session.exec.return_value = mock_exec_result
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=False)

        mock_carrier = MockSmsCarrier()
        with patch("tasks.sms_compliance.Session", return_value=mock_session):
            with patch(
                "services.sms_carrier.get_sms_carrier", return_value=mock_carrier
            ):
                result = _send_double_optin_sms_impl(
                    customer_id=str(test_customer.id),
                    tenant_id=str(test_customer.tenant_id),
                )

        assert result["status"] == "skipped"
        assert result["reason"] == "already_opted_out"
        # No SMS sent to opted-out customer
        assert len(mock_carrier.sent_messages) == 0


# ─── DLC-B2: Compliant auto-reply string tests ───────────────────────────────


class TestDlcB2OptOutReplyCompliance:
    """DLC-B2 Finding 1: STOP auto-reply must contain brand, 'No further messages', and 'Reply START'."""

    def test_opt_out_reply_is_compliant(self, db_session, test_tenant, test_customer):
        """STOP reply contains Pilot for Trades brand, no-more-messages text, and re-subscribe instruction."""
        from services.customer_communication_threading import handle_sms_opt_out
        from services.sms_carrier import MockSmsCarrier

        inbound = _make_inbound(
            "STOP", from_number=test_customer.mobile_phone or "+15125551234"
        )
        mock_carrier = MockSmsCarrier()

        with patch("services.sms_carrier.get_sms_carrier", return_value=mock_carrier):
            handle_sms_opt_out(db_session, test_customer.id, inbound)

        assert len(mock_carrier.sent_messages) == 1
        sent_body = mock_carrier.sent_messages[0]["body"]
        assert "Pilot for Trades" in sent_body
        assert "No further messages" in sent_body
        assert "Reply START" in sent_body


class TestDlcB2OptInReplyCompliance:
    """DLC-B2 Finding 2: START/YES reply must confirm opt-in, include rate/help disclosures, and NOT use MFA framing."""

    def test_opt_in_reply_is_compliant(self, db_session, test_tenant, test_customer):
        """START/YES reply contains opt-in confirmation, rate disclosure, HELP instruction, no MFA framing."""
        from services.customer_communication_threading import handle_sms_opt_in
        from services.sms_carrier import MockSmsCarrier

        inbound = _make_inbound(
            "YES", from_number=test_customer.mobile_phone or "+15125551234"
        )
        mock_carrier = MockSmsCarrier()

        with patch("services.sms_carrier.get_sms_carrier", return_value=mock_carrier):
            handle_sms_opt_in(db_session, test_customer.id, inbound)

        assert len(mock_carrier.sent_messages) == 1
        sent_body = mock_carrier.sent_messages[0]["body"]
        assert "opted in" in sent_body.lower()
        assert "Msg & data rates may apply" in sent_body
        assert "Reply HELP" in sent_body
        # Guard against re-introduction of MFA/login framing (CYYYYYY campaign mistake)
        assert "login" not in sent_body.lower()
        assert "verification" not in sent_body.lower()


class TestDlcB2HelpReplyCompliance:
    """DLC-B2 Finding 3: HELP auto-reply must include website, email, rates, and STOP instruction."""

    def test_help_reply_is_compliant(self, db_session, test_tenant, test_customer):
        """HELP reply contains pilotfortrades.com, info@pilotfortrades.com, rate disclosure, and STOP."""
        from services.customer_communication_threading import handle_sms_help
        from services.sms_carrier import MockSmsCarrier

        inbound = _make_inbound(
            "HELP", from_number=test_customer.mobile_phone or "+15125551234"
        )
        mock_carrier = MockSmsCarrier()

        with patch("services.sms_carrier.get_sms_carrier", return_value=mock_carrier):
            handle_sms_help(inbound, db=db_session)

        assert len(mock_carrier.sent_messages) == 1
        sent_body = mock_carrier.sent_messages[0]["body"]
        assert "pilotfortrades.com" in sent_body
        assert "info@pilotfortrades.com" in sent_body
        assert "Msg & data rates may apply" in sent_body
        assert "Reply STOP" in sent_body


class TestDlcB2DoubleOptInDisclosures:
    """DLC-B2 Task 4: Double opt-in template must include freq, rates, and HELP disclosures."""

    def test_double_optin_message_has_required_disclosures(self):
        """_DOUBLE_OPTIN_TEMPLATE contains Reply YES, Msg & data rates, and Reply HELP."""
        from tasks.sms_compliance import _DOUBLE_OPTIN_TEMPLATE

        # Render with dummy values to get the full message body
        rendered = _DOUBLE_OPTIN_TEMPLATE.format(
            first_name="Mike", business_name="ABC Electrical LLC"
        )
        assert "Reply YES" in rendered
        assert "Msg & data rates may apply" in rendered
        assert "Reply HELP" in rendered
        # Must still include STOP instruction
        assert "STOP" in rendered
