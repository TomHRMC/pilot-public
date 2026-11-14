"""
PLP-FIX-6 / FIX4-BE-01a — Rider wiring tests for mark_first_customer.

Verifies the endpoint-level wiring from POST /api/v1/customers/test to the
onboarding checklist ``mark_first_customer`` service function. The service
function itself is covered by tests/batch_b14/test_a77_onboarding_checklist.py;
these tests prove the wiring from the route handler.

Domain: CRM (PRD §3.3)
"""

import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import text
from sqlmodel import select

from app.models.onboarding import TenantOnboardingChecklist

pytestmark = [
    pytest.mark.domain_crm,
    pytest.mark.unit,
]


def _delete_checklist(db_session, tenant_id):
    """Remove any pre-existing checklist row so tests start from a clean state."""
    db_session.execute(
        text("DELETE FROM public.tenant_onboarding_checklist WHERE tenant_id = :tid"),
        {"tid": str(tenant_id)},
    )
    db_session.commit()


def _get_checklist(db_session, tenant_id):
    return db_session.exec(
        select(TenantOnboardingChecklist).where(
            TenantOnboardingChecklist.tenant_id == tenant_id
        )
    ).first()


class TestMarkFirstCustomerWiring:
    """Endpoint-level wiring tests for mark_first_customer."""

    def test_create_customer_advances_checklist(self, client, db_session, test_tenant):
        """Creating a customer via /test advances first_customer_added."""
        _delete_checklist(db_session, test_tenant.id)

        resp = client.post(
            "/api/v1/customers/test",
            json={
                "display_name": f"Wiring Test {uuid.uuid4().hex[:6]}",
                "type": "person",
            },
        )
        assert resp.status_code == 201

        checklist = _get_checklist(db_session, test_tenant.id)
        assert checklist is not None
        assert checklist.first_customer_added is True
        assert checklist.first_customer_added_at is not None

    def test_create_customer_is_idempotent_on_checklist(
        self, client, db_session, test_tenant
    ):
        """A second customer create does not change the timestamp."""
        _delete_checklist(db_session, test_tenant.id)

        # First create
        resp1 = client.post(
            "/api/v1/customers/test",
            json={
                "display_name": f"First {uuid.uuid4().hex[:6]}",
                "type": "person",
            },
        )
        assert resp1.status_code == 201
        first_ts = _get_checklist(db_session, test_tenant.id).first_customer_added_at

        # Second create
        resp2 = client.post(
            "/api/v1/customers/test",
            json={
                "display_name": f"Second {uuid.uuid4().hex[:6]}",
                "type": "person",
            },
        )
        assert resp2.status_code == 201
        second_ts = _get_checklist(db_session, test_tenant.id).first_customer_added_at

        assert first_ts == second_ts

    def test_mark_failure_does_not_fail_create(self, client, db_session, test_tenant):
        """If mark_first_customer raises, the customer create still returns 201."""
        _delete_checklist(db_session, test_tenant.id)

        with patch(
            "api.routes.customers.mark_first_customer",
            side_effect=RuntimeError("checklist write failed"),
        ):
            resp = client.post(
                "/api/v1/customers/test",
                json={
                    "display_name": f"Isolation {uuid.uuid4().hex[:6]}",
                    "type": "person",
                },
            )

        assert resp.status_code == 201
        assert resp.json()["id"] is not None
