"""
B14/A77 — Onboarding Checklist tests.

Test focus cases:
1. GET checklist/test auto-creates row if missing, returns all fields
2. mark_first_customer sets first_customer_added=True + timestamp
3. mark_catalog_setup sets catalog_setup=True + timestamp
4. skip quickbooks → quickbooks_skipped=True
5. skip calendar → calendar_skipped=True
6. skip team → team_skipped=True
7. hide checklist → checklist_hidden=True
8. dismiss permanently → checklist_dismissed_permanently=True
9. ensure_checklist_exists sets account_created/legal_accepted/tier_selected=True
10. skip invalid item → ValueError
"""

import uuid

import pytest
from sqlmodel import select

from app.models.onboarding import TenantOnboardingChecklist

# ==================== TEST CASES ====================


class TestChecklistAutoCreate:
    """Test cases 1: GET auto-creates and returns all fields."""

    def test_get_creates_checklist_if_missing(self, client, test_tenant):
        """GET checklist/test creates row if none exists and returns full state."""
        response = client.get(
            f"/api/v1/tenants/{test_tenant.id}/onboarding/checklist/test"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == str(test_tenant.id)
        assert "account_created" in data
        assert "first_customer_added" in data
        assert "checklist_dismissed_permanently" in data

    def test_get_checklist_returns_defaults(self, client, db_session, test_tenant):
        """Fresh checklist has all bool fields False by default.

        Deletes any pre-seeded checklist row (from seed_test_tenant.py) so the
        GET endpoint's auto-create logic creates a fresh row with all defaults.
        """
        from sqlalchemy import text

        # Remove the seed row so the endpoint creates a fresh default checklist
        db_session.execute(
            text(
                "DELETE FROM public.tenant_onboarding_checklist WHERE tenant_id = :tid"
            ),
            {"tid": str(test_tenant.id)},
        )
        db_session.commit()

        response = client.get(
            f"/api/v1/tenants/{test_tenant.id}/onboarding/checklist/test"
        )
        data = response.json()
        assert data["quickbooks_connected"] is False
        assert data["quickbooks_skipped"] is False
        assert data["checklist_hidden"] is False
        assert data["checklist_dismissed_permanently"] is False


class TestOnboardingServiceMarkers:
    """Test cases 2-3: Domain event marking functions."""

    def _ensure_checklist(self, db_session, tenant_id):
        """Create checklist row for tests that don't use the API."""
        from services.onboarding_service import ensure_checklist_exists

        ensure_checklist_exists(db_session, tenant_id)

    def test_mark_first_customer_sets_flag_and_timestamp(self, db_session, test_tenant):
        from sqlalchemy import text

        from services.onboarding_service import mark_first_customer

        # Delete pre-seeded checklist row so ensure_checklist_exists creates a
        # fresh row with first_customer_added=False and first_customer_added_at=None.
        db_session.execute(
            text(
                "DELETE FROM public.tenant_onboarding_checklist WHERE tenant_id = :tid"
            ),
            {"tid": str(test_tenant.id)},
        )
        db_session.commit()

        self._ensure_checklist(db_session, test_tenant.id)
        mark_first_customer(db_session, test_tenant.id)

        checklist = db_session.exec(
            select(TenantOnboardingChecklist).where(
                TenantOnboardingChecklist.tenant_id == test_tenant.id
            )
        ).first()
        assert checklist.first_customer_added is True
        assert checklist.first_customer_added_at is not None

    def test_mark_first_customer_is_idempotent(self, db_session, test_tenant):
        from services.onboarding_service import mark_first_customer

        self._ensure_checklist(db_session, test_tenant.id)
        mark_first_customer(db_session, test_tenant.id)
        first_ts = (
            db_session.exec(
                select(TenantOnboardingChecklist).where(
                    TenantOnboardingChecklist.tenant_id == test_tenant.id
                )
            )
            .first()
            .first_customer_added_at
        )

        mark_first_customer(db_session, test_tenant.id)  # second call
        second_ts = (
            db_session.exec(
                select(TenantOnboardingChecklist).where(
                    TenantOnboardingChecklist.tenant_id == test_tenant.id
                )
            )
            .first()
            .first_customer_added_at
        )

        assert first_ts == second_ts  # idempotent — timestamp unchanged

    def test_mark_catalog_setup_sets_flag_and_timestamp(self, db_session, test_tenant):
        from sqlalchemy import text

        from services.onboarding_service import mark_catalog_setup

        # Delete pre-seeded checklist row so ensure_checklist_exists creates a
        # fresh row with catalog_setup=False and catalog_setup_at=None.
        db_session.execute(
            text(
                "DELETE FROM public.tenant_onboarding_checklist WHERE tenant_id = :tid"
            ),
            {"tid": str(test_tenant.id)},
        )
        db_session.commit()

        self._ensure_checklist(db_session, test_tenant.id)
        mark_catalog_setup(db_session, test_tenant.id)

        checklist = db_session.exec(
            select(TenantOnboardingChecklist).where(
                TenantOnboardingChecklist.tenant_id == test_tenant.id
            )
        ).first()
        assert checklist.catalog_setup is True
        assert checklist.catalog_setup_at is not None


class TestSkipItems:
    """Test cases 4-6: Skip items."""

    def test_skip_quickbooks_sets_flag(self, client, test_tenant):
        response = client.put(
            f"/api/v1/tenants/{test_tenant.id}/onboarding/checklist/skip/quickbooks/test"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["quickbooks_skipped"] is True

    def test_skip_calendar_sets_flag(self, client, test_tenant):
        response = client.put(
            f"/api/v1/tenants/{test_tenant.id}/onboarding/checklist/skip/calendar/test"
        )
        assert response.status_code == 200
        assert response.json()["calendar_skipped"] is True

    def test_skip_team_sets_flag(self, client, test_tenant):
        response = client.put(
            f"/api/v1/tenants/{test_tenant.id}/onboarding/checklist/skip/team/test"
        )
        assert response.status_code == 200
        assert response.json()["team_skipped"] is True

    def test_skip_invalid_item_returns_422(self, db_session, test_tenant):
        from services.onboarding_service import skip_item

        with pytest.raises(ValueError):
            skip_item(db_session, test_tenant.id, "invalid_item")


class TestChecklistVisibility:
    """Test cases 7-8: Hide and dismiss."""

    def test_hide_checklist(self, client, test_tenant):
        # PLP-FIX-10/INV-BUG-14: /hidden/test now accepts HideChecklistRequest
        # payload (parity with the authed endpoint) to support the unhide path.
        response = client.put(
            f"/api/v1/tenants/{test_tenant.id}/onboarding/checklist/hidden/test",
            json={"hidden": True},
        )
        assert response.status_code == 200
        assert response.json()["checklist_hidden"] is True

    def test_dismiss_checklist_permanently(self, client, test_tenant):
        response = client.put(
            f"/api/v1/tenants/{test_tenant.id}/onboarding/checklist/dismissed/test"
        )
        assert response.status_code == 200
        assert response.json()["checklist_dismissed_permanently"] is True


class TestEnsureChecklistExists:
    """Test case 9: ensure_checklist_exists sets wizard completion flags."""

    def test_ensure_checklist_sets_wizard_flags(self, db_session):
        # Create a fresh tenant
        from app.models.core import Tenant
        from services.onboarding_service import ensure_checklist_exists

        tenant = Tenant(
            id=uuid.uuid4(),
            name=f"Onboarding Test Tenant {uuid.uuid4().hex[:8]}",
            is_active=True,
        )
        db_session.add(tenant)
        db_session.commit()

        ensure_checklist_exists(db_session, tenant.id)

        checklist = db_session.exec(
            select(TenantOnboardingChecklist).where(
                TenantOnboardingChecklist.tenant_id == tenant.id
            )
        ).first()
        assert checklist is not None
        assert checklist.account_created is True
        assert checklist.legal_accepted is True
        assert checklist.tier_selected is True
