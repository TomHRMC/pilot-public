"""
tests/batch_b4/test_a8_communication_history.py

B4 / A8 — GET /api/v1/customers/{customer_id}/communications (test endpoint)

Test focus areas:
  - Returns paginated history for a customer
  - Empty history returns 200 with empty items list
  - Pagination (page, page_size) works correctly
  - Tenant isolation: cannot view another tenant's customer history
  - 404 for unknown customer
"""

import uuid
from datetime import UTC, datetime

import pytest

from app.models.communications import CustomerCommunication
from app.models.crm import Customer


@pytest.fixture
def test_customer(db_session, test_tenant, test_user):
    """Standard customer with mobile_phone."""
    customer = Customer(
        tenant_id=test_tenant.id,
        display_name="Mike Davis",
        first_name="Mike",
        last_name="Davis",
        mobile_phone="+15125550010",
        email="mike.davis@example.com",
        preferred_contact_channel="sms",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)
    return customer


def _create_comm(
    db_session, tenant_id, customer_id, sender_user_id, template_code="arrived", n=1
):
    """Helper: create n CustomerCommunication rows."""
    comms = []
    for i in range(n):
        comm = CustomerCommunication(
            tenant_id=tenant_id,
            customer_id=customer_id,
            sender_user_id=sender_user_id,
            template_code=template_code,
            rendered_message=f"Test message {i}",
            channel="sms",
            actual_channel="sms",
            customer_preferred_channel="sms",
            channel_override_flag=False,
            status="sent",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session.add(comm)
        comms.append(comm)
    db_session.commit()
    for c in comms:
        db_session.refresh(c)
    return comms


class TestCommunicationHistoryEndpoint:
    """GET /api/v1/customers/{customer_id}/communications/test"""

    def test_empty_history_returns_200(
        self, client, test_tenant, test_user, test_customer
    ):
        """Customer with no comms returns 200 with empty items."""
        resp = client.get(f"/api/v1/customers/test/{test_customer.id}/communications")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["customer_id"] == str(test_customer.id)
        assert data["total"] == 0
        assert data["items"] == []
        assert data["page"] == 1
        assert data["page_size"] == 20

    def test_history_returns_communications(
        self, client, db_session, test_tenant, test_user, test_customer
    ):
        """Customer with comms returns correct items."""
        comms = _create_comm(
            db_session,
            test_tenant.id,
            test_customer.id,
            test_user.id,
            template_code="job_complete",
            n=3,
        )
        resp = client.get(f"/api/v1/customers/test/{test_customer.id}/communications")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3
        # Verify item shape
        item = data["items"][0]
        assert "communication_id" in item
        assert item["template_code"] == "job_complete"
        assert item["actual_channel"] == "sms"
        assert item["status"] == "sent"

    def test_pagination_page_size(
        self, client, db_session, test_tenant, test_user, test_customer
    ):
        """Pagination: page_size=2 with 5 comms returns 2 items on page 1."""
        _create_comm(db_session, test_tenant.id, test_customer.id, test_user.id, n=5)
        resp = client.get(
            f"/api/v1/customers/test/{test_customer.id}/communications",
            params={"page": 1, "page_size": 2},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["page"] == 1
        assert data["page_size"] == 2

    def test_pagination_page_2(
        self, client, db_session, test_tenant, test_user, test_customer
    ):
        """Pagination: page 2 with page_size=2 returns remaining items."""
        _create_comm(db_session, test_tenant.id, test_customer.id, test_user.id, n=5)
        resp = client.get(
            f"/api/v1/customers/test/{test_customer.id}/communications",
            params={"page": 3, "page_size": 2},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 5
        assert len(data["items"]) == 1  # 5 total, 4 on pages 1+2, 1 remaining

    def test_unknown_customer_returns_404(self, client, test_tenant, test_user):
        """Unknown customer UUID → 404."""
        resp = client.get(f"/api/v1/customers/test/{uuid.uuid4()}/communications")
        assert resp.status_code == 404

    def test_tenant_isolation(self, client, db_session, tenant_b, test_user):
        """Customer in another tenant → 404 (test context uses TEST_TENANT)."""
        other_customer = Customer(
            tenant_id=tenant_b.id,
            display_name="Other Tenant Person",
            first_name="Other",
            mobile_phone="+15125559998",
            preferred_contact_channel="sms",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db_session.add(other_customer)
        db_session.commit()
        db_session.refresh(other_customer)

        resp = client.get(f"/api/v1/customers/test/{other_customer.id}/communications")
        assert resp.status_code == 404

    def test_page_size_max_100(self, client, test_tenant, test_user, test_customer):
        """page_size > 100 should be rejected by FastAPI validation."""
        resp = client.get(
            f"/api/v1/customers/test/{test_customer.id}/communications",
            params={"page_size": 200},
        )
        assert resp.status_code == 422
