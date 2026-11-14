"""
Tests for: GET /api/v1/customers/{customer_id}/threads
Domain: notifications_comms

Endpoint returns { threads: SmsThread[], total: number } for a customer-scoped
thread listing. The SD-02 seed scenario populates customer_communication_thread +
customer_communication_message so real data flows through.

These tests use the /test/{customer_id}/threads endpoint to avoid JWT dependency.
"""

import uuid
from datetime import UTC, datetime

import pytest

pytestmark = [
    pytest.mark.domain_notifications_comms,
    pytest.mark.unit,
]


class TestCustomerSmsThreadsEndpoint:
    def test_returns_200_with_threads_and_total(self, client, test_tenant):
        """GET /api/v1/customers/test/{id}/threads returns 200 with threads + total."""
        # Create a customer via the test endpoint
        resp = client.post(
            "/api/v1/customers/test",
            json={
                "display_name": "Thread Test Customer",
                "type": "person",
            },
        )
        assert resp.status_code == 201
        customer_id = resp.json()["id"]

        response = client.get(f"/api/v1/customers/test/{customer_id}/threads")
        assert response.status_code == 200
        data = response.json()
        assert "threads" in data
        assert "total" in data
        assert isinstance(data["threads"], list)
        assert isinstance(data["total"], int)

    def test_returns_empty_threads_for_customer_with_no_threads(
        self, client, test_tenant
    ):
        """Customer with no SMS threads returns empty list and total=0."""
        resp = client.post(
            "/api/v1/customers/test",
            json={
                "display_name": "No Threads Customer",
                "type": "person",
            },
        )
        assert resp.status_code == 201
        customer_id = resp.json()["id"]

        response = client.get(f"/api/v1/customers/test/{customer_id}/threads")
        assert response.status_code == 200
        data = response.json()
        assert data["threads"] == []
        assert data["total"] == 0

    def test_returns_404_for_nonexistent_customer(self, client, test_tenant):
        """Returns 404 (not 403) for a customer_id not in this tenant."""
        nonexistent_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/customers/test/{nonexistent_id}/threads")
        assert response.status_code == 404
        data = response.json()
        # RFC 7807 shape
        assert "detail" in data
        assert data["detail"]["status"] == 404

    def test_response_shape_matches_frontend_sms_thread_interface(
        self, client, test_tenant, db_session
    ):
        """When threads exist, each thread entry has all required SmsThread fields."""

        from sqlmodel import select

        from app.models.core import User
        from app.models.sms import (
            CustomerCommunicationMessage,
            CustomerCommunicationThread,
            TenantPhoneNumber,
        )

        # Create a customer
        resp = client.post(
            "/api/v1/customers/test",
            json={
                "display_name": "Thread Shape Customer",
                "type": "person",
                "mobile_phone": "+15125550042",
            },
        )
        assert resp.status_code == 201
        customer_id = uuid.UUID(resp.json()["id"])

        # Look up the test user as tech

        tech_user = db_session.exec(
            select(User).where(User.email == "dev@pilot.local")
        ).first()
        assert tech_user is not None, "dev@pilot.local test user not found"

        # Create a TenantPhoneNumber for the tenant
        phone = TenantPhoneNumber(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            phone_number="+15125559999",
            area_code="512",
            carrier="telnyx",
            status="active",
        )
        db_session.add(phone)
        db_session.flush()

        now = datetime.now(UTC)
        thread = CustomerCommunicationThread(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            customer_id=customer_id,
            tech_id=tech_user.id,
            tenant_phone_number_id=phone.id,
            status="active",
            first_message_at=now,
            last_message_at=now,
            message_count=1,
        )
        db_session.add(thread)
        db_session.flush()

        msg = CustomerCommunicationMessage(
            id=uuid.uuid4(),
            thread_id=thread.id,
            direction="outbound",
            channel="sms",
            body="Hello from test",
            segment_count=1,
            status="sent",
            audit_user_id=tech_user.id,
        )
        db_session.add(msg)
        db_session.commit()

        response = client.get(f"/api/v1/customers/test/{customer_id}/threads")
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        t = data["threads"][0]

        # Verify all required SmsThread fields are present
        required_fields = [
            "thread_id",
            "tenant_id",
            "customer_id",
            "customer_name",
            "customer_phone",
            "customer_sms_opted_out",
            "customer_opted_out_at",
            "tech_id",
            "tech_name",
            "tenant_phone_number_id",
            "status",
            "first_message_at",
            "last_message_at",
            "message_count",
            "unread_count",
            "originating_job_id",
            "originating_job_display",
            "created_at",
            "updated_at",
            "messages",
        ]
        for field in required_fields:
            assert field in t, f"Missing field: {field}"

        # Verify values
        assert t["thread_id"] == str(thread.id)
        assert t["customer_id"] == str(customer_id)
        assert t["customer_name"] == "Thread Shape Customer"
        assert t["status"] == "active"
        assert t["message_count"] == 1
        assert t["unread_count"] == 0
        assert t["originating_job_id"] is None
        assert t["originating_job_display"] is None

        # Verify messages are embedded
        assert len(t["messages"]) == 1
        m = t["messages"][0]
        assert m["thread_id"] == str(thread.id)
        assert m["direction"] == "outbound"
        assert m["body"] == "Hello from test"

    def test_authenticated_endpoint_requires_jwt(self, client, test_tenant):
        """Authenticated endpoint without JWT returns 401 or 403."""
        some_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/customers/{some_id}/threads")
        # No Authorization header — expect 401 or 403
        assert response.status_code in (401, 403)

    def test_total_matches_threads_list_length(self, client, test_tenant):
        """total field always equals len(threads)."""
        resp = client.post(
            "/api/v1/customers/test",
            json={"display_name": "Total Check Customer", "type": "company"},
        )
        assert resp.status_code == 201
        customer_id = resp.json()["id"]

        response = client.get(f"/api/v1/customers/test/{customer_id}/threads")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == len(data["threads"])
