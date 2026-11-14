"""
tests/batch_b4/test_a23_communication_preview.py

B4 / A23 — POST /api/v1/communications/preview (test endpoint)

Test focus areas:
  - Returns rendered body and metadata WITHOUT creating any DB rows
  - No CustomerCommunication row created
  - No NotificationOutbox row created
  - rendered_body contains substituted variables
  - editable_variables excludes auto-resolved (customer_name, sender_name)
  - channel_override is respected in preview
  - Missing mobile_phone → 422
  - Invalid template_code → 422
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlmodel import select

from app.models.communications import CustomerCommunication
from app.models.crm import Customer
from app.models.system import NotificationOutbox


@pytest.fixture
def test_customer(db_session, test_tenant, test_user):
    customer = Customer(
        tenant_id=test_tenant.id,
        display_name="Sarah Williams",
        first_name="Sarah",
        last_name="Williams",
        mobile_phone="+15125550020",
        email="sarah@example.com",
        preferred_contact_channel="sms",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)
    return customer


@pytest.fixture
def test_customer_no_phone(db_session, test_tenant, test_user):
    customer = Customer(
        tenant_id=test_tenant.id,
        display_name="No Phone Again",
        first_name="No",
        last_name="Phone",
        mobile_phone=None,
        email="nophone2@example.com",
        preferred_contact_channel="sms",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)
    return customer


class TestCommunicationPreviewEndpoint:
    """POST /api/v1/communications/preview/test"""

    def test_preview_returns_rendered_body(
        self, client, test_tenant, test_user, test_customer
    ):
        """Preview renders template and returns body with substituted variables."""
        resp = client.post(
            "/api/v1/communications/preview/test",
            json={
                "customer_id": str(test_customer.id),
                "template_code": "on_my_way",
                "variables": {
                    "eta": "2:30 PM",
                    "site_address": "742 Evergreen Terrace",
                },
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "2:30 PM" in data["rendered_body"]
        assert data["recipient_name"] == "Sarah Williams"
        assert data["recipient_address"] == "+15125550020"
        assert data["actual_channel"] == "sms"
        assert data["rendered_subject"] is None  # SMS has no subject

    def test_preview_does_not_create_customer_communication(
        self, client, db_session, test_tenant, test_user, test_customer
    ):
        """CRITICAL: preview NEVER writes CustomerCommunication rows."""
        # Count before
        before = db_session.exec(
            select(CustomerCommunication).where(
                CustomerCommunication.customer_id == test_customer.id
            )
        ).all()
        count_before = len(before)

        resp = client.post(
            "/api/v1/communications/preview/test",
            json={
                "customer_id": str(test_customer.id),
                "template_code": "arrived",
                "variables": {},
            },
        )
        assert resp.status_code == 200

        # Count after — must be the same
        after = db_session.exec(
            select(CustomerCommunication).where(
                CustomerCommunication.customer_id == test_customer.id
            )
        ).all()
        assert len(after) == count_before, (
            "Preview must NEVER write CustomerCommunication rows"
        )

    def test_preview_does_not_create_notification_outbox(
        self, client, db_session, test_tenant, test_user, test_customer
    ):
        """CRITICAL: preview NEVER writes NotificationOutbox rows."""
        before_count = len(
            db_session.exec(
                select(NotificationOutbox).where(
                    NotificationOutbox.tenant_id == test_tenant.id
                )
            ).all()
        )

        resp = client.post(
            "/api/v1/communications/preview/test",
            json={
                "customer_id": str(test_customer.id),
                "template_code": "job_complete",
                "variables": {},
            },
        )
        assert resp.status_code == 200

        after_count = len(
            db_session.exec(
                select(NotificationOutbox).where(
                    NotificationOutbox.tenant_id == test_tenant.id
                )
            ).all()
        )
        assert after_count == before_count, (
            "Preview must NEVER write NotificationOutbox rows"
        )

    def test_preview_editable_variables_exclude_auto_resolved(
        self, client, test_tenant, test_user, test_customer
    ):
        """editable_variables should not include customer_name or sender_name."""
        resp = client.post(
            "/api/v1/communications/preview/test",
            json={
                "customer_id": str(test_customer.id),
                "template_code": "on_my_way",
                "variables": {"eta": "noon", "site_address": "1 Main St"},
            },
        )
        assert resp.status_code == 200
        ev_names = [v["name"] for v in resp.json()["editable_variables"]]
        assert "customer_first_name" not in ev_names
        assert "sender_name" not in ev_names
        assert "customer_name" not in ev_names
        # eta and site_address should be present for on_my_way
        assert "eta" in ev_names
        assert "site_address" in ev_names

    def test_preview_channel_override_respected(
        self, client, test_tenant, test_user, test_customer
    ):
        """channel_override='email' in preview returns email channel."""
        resp = client.post(
            "/api/v1/communications/preview/test",
            json={
                "customer_id": str(test_customer.id),
                "template_code": "on_my_way",
                "variables": {"eta": "4 PM", "site_address": "5 Oak Dr"},
                "channel_override": "email",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["actual_channel"] == "email"
        assert data["recipient_address"] == "sarah@example.com"
        assert data["rendered_subject"] is not None  # email has subject

    def test_preview_missing_phone_returns_422(
        self, client, test_tenant, test_user, test_customer_no_phone
    ):
        """No mobile_phone for SMS channel → 422."""
        resp = client.post(
            "/api/v1/communications/preview/test",
            json={
                "customer_id": str(test_customer_no_phone.id),
                "template_code": "arrived",
                "variables": {},
            },
        )
        assert resp.status_code == 422
        assert "mobile_phone" in resp.json()["detail"].lower()

    def test_preview_unknown_customer_returns_422(self, client, test_tenant, test_user):
        """Random UUID → 422."""
        resp = client.post(
            "/api/v1/communications/preview/test",
            json={
                "customer_id": str(uuid.uuid4()),
                "template_code": "arrived",
                "variables": {},
            },
        )
        assert resp.status_code == 422

    def test_preview_all_six_template_codes(
        self, client, test_tenant, test_user, test_customer
    ):
        """All 6 MVP template codes should preview without error."""
        codes_vars = [
            ("on_my_way", {"eta": "3 PM", "site_address": "1 St"}),
            ("running_late", {"minutes_late": "20"}),
            ("arrived", {}),
            ("job_complete", {}),
            ("parts_delay", {}),
            (
                "confirm_appointment",
                {"date_time": "Tue 10 AM", "site_address": "2 Ave"},
            ),
        ]
        for code, variables in codes_vars:
            resp = client.post(
                "/api/v1/communications/preview/test",
                json={
                    "customer_id": str(test_customer.id),
                    "template_code": code,
                    "variables": variables,
                },
            )
            assert resp.status_code == 200, f"Preview failed for '{code}': {resp.text}"
            assert len(resp.json()["rendered_body"]) > 0
