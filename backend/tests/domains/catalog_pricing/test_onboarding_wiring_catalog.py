"""
PLP-FIX-6 / FIX4-BE-01b — Rider wiring tests for mark_catalog_setup.

Verifies the endpoint-level wiring from POST /api/v1/catalog/pricebook/test to
the onboarding checklist ``mark_catalog_setup`` service function. The service
function itself is covered by tests/batch_b14/test_a77_onboarding_checklist.py;
these tests prove the wiring from the route handler.

Domain: Catalog & Pricing (PRD §3.2)
"""

import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import text
from sqlmodel import select

from app.models.onboarding import TenantOnboardingChecklist

pytestmark = [
    pytest.mark.domain_catalog_pricing,
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


class TestMarkCatalogSetupWiring:
    """Endpoint-level wiring tests for mark_catalog_setup."""

    def test_create_pricebook_item_advances_checklist(
        self, client, db_session, test_tenant
    ):
        """Creating a pricebook item via /test advances catalog_setup."""
        _delete_checklist(db_session, test_tenant.id)

        sku = f"SKU-WIRE-{uuid.uuid4().hex[:6].upper()}"
        resp = client.post(
            "/api/v1/catalog/pricebook/test",
            json={
                "sku": sku,
                "name": f"Wiring Item {uuid.uuid4().hex[:6]}",
                "initial_price_cents": 1500,
            },
        )
        assert resp.status_code == 201

        checklist = _get_checklist(db_session, test_tenant.id)
        assert checklist is not None
        assert checklist.catalog_setup is True
        assert checklist.catalog_setup_at is not None

    def test_create_pricebook_item_is_idempotent_on_checklist(
        self, client, db_session, test_tenant
    ):
        """A second pricebook item create does not change the timestamp."""
        _delete_checklist(db_session, test_tenant.id)

        # First create
        resp1 = client.post(
            "/api/v1/catalog/pricebook/test",
            json={
                "sku": f"SKU-IDEM1-{uuid.uuid4().hex[:6].upper()}",
                "name": f"Idempotent Item 1 {uuid.uuid4().hex[:6]}",
                "initial_price_cents": 2000,
            },
        )
        assert resp1.status_code == 201
        first_ts = _get_checklist(db_session, test_tenant.id).catalog_setup_at

        # Second create
        resp2 = client.post(
            "/api/v1/catalog/pricebook/test",
            json={
                "sku": f"SKU-IDEM2-{uuid.uuid4().hex[:6].upper()}",
                "name": f"Idempotent Item 2 {uuid.uuid4().hex[:6]}",
                "initial_price_cents": 2500,
            },
        )
        assert resp2.status_code == 201
        second_ts = _get_checklist(db_session, test_tenant.id).catalog_setup_at

        assert first_ts == second_ts

    def test_mark_failure_does_not_fail_create(self, client, db_session, test_tenant):
        """If mark_catalog_setup raises, the pricebook create still returns 201."""
        _delete_checklist(db_session, test_tenant.id)

        sku = f"SKU-ISO-{uuid.uuid4().hex[:6].upper()}"
        with patch(
            "api.routes.catalog.mark_catalog_setup",
            side_effect=RuntimeError("checklist write failed"),
        ):
            resp = client.post(
                "/api/v1/catalog/pricebook/test",
                json={
                    "sku": sku,
                    "name": f"Isolation Item {uuid.uuid4().hex[:6]}",
                    "initial_price_cents": 3000,
                },
            )

        assert resp.status_code == 201
        assert resp.json()["id"] is not None
