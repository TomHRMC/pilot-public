"""
BE-UI-NAV-S1 — Bulk tenant notification policy endpoint tests.

Tests:
  1. GET /test/tenant-policy returns policies list (may be empty)
  2. DELETE /test/tenant-policy deletes only tenant rows; system rows (tenant_id=NULL) untouched
  3. DELETE /test/tenant-policy with no tenant rows returns deleted_count=0
  4. GET /test/tenant-policy isolates by tenant (test tenant only sees its own rows)
  5. DELETE /tenant-policy (authenticated) returns 403 for technician role

Domain: notifications_comms
Note: Valid notification_category codes from seed:
  quote_approvals, field_issues, sync_conflicts, job_activity,
  customer_activity, billing, background_sync_alerts, system_announcements
"""

import uuid

import pytest
from sqlmodel import select

from app.models.system import NotificationDefaultPolicy

pytestmark = [
    pytest.mark.domain_notifications_comms,
    pytest.mark.unit,
]

TEST_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

# Valid category codes from notification_category table
CATEGORY_A = "billing"
CATEGORY_B = "job_activity"


class TestGetTenantPolicy:
    def test_get_tenant_policy_test_endpoint_returns_list(self, client, test_tenant):
        """GET /test/tenant-policy returns 200 with policies list (may be empty)."""
        resp = client.get("/api/v1/notifications/test/tenant-policy")
        assert resp.status_code == 200
        data = resp.json()
        assert "policies" in data
        assert isinstance(data["policies"], list)


class TestResetTenantPolicy:
    def test_reset_tenant_policy_deletes_only_tenant_rows(
        self, client, test_tenant, db_session
    ):
        """
        DELETE /test/tenant-policy deletes only tenant-override rows.
        System rows (tenant_id IS NULL) must be untouched after reset.
        """
        # Reset first to clean any leftover state
        client.delete("/api/v1/notifications/test/tenant-policy")

        # Insert 2 known tenant-override rows via test endpoint (uses valid category codes)
        r1 = client.put(
            f"/api/v1/notifications/test/tenant-policy/{CATEGORY_A}/push",
            json={"enabled": True},
        )
        r2 = client.put(
            f"/api/v1/notifications/test/tenant-policy/{CATEGORY_B}/email",
            json={"enabled": False},
        )
        assert r1.status_code == 200
        assert r2.status_code == 200

        # Count system rows (tenant_id IS NULL) before reset
        system_count_before = len(
            db_session.exec(
                select(NotificationDefaultPolicy).where(
                    NotificationDefaultPolicy.tenant_id == None
                )
            ).all()
        )

        # Reset all tenant-override rows
        resp = client.delete("/api/v1/notifications/test/tenant-policy")
        assert resp.status_code == 200
        data = resp.json()
        assert "deleted_count" in data
        assert data["deleted_count"] >= 2  # At least the 2 we just inserted

        # System rows (tenant_id IS NULL) must be untouched
        system_count_after = len(
            db_session.exec(
                select(NotificationDefaultPolicy).where(
                    NotificationDefaultPolicy.tenant_id == None
                )
            ).all()
        )
        assert system_count_after == system_count_before

        # Test-tenant rows must be gone
        tenant_rows_after = db_session.exec(
            select(NotificationDefaultPolicy).where(
                NotificationDefaultPolicy.tenant_id == TEST_TENANT_ID
            )
        ).all()
        assert len(tenant_rows_after) == 0

    def test_reset_tenant_policy_empty_tenant_returns_zero(
        self, client, test_tenant, db_session
    ):
        """DELETE /test/tenant-policy with no tenant rows returns deleted_count=0."""
        # First reset to clean state
        client.delete("/api/v1/notifications/test/tenant-policy")

        # Call delete again when already empty
        resp = client.delete("/api/v1/notifications/test/tenant-policy")
        assert resp.status_code == 200
        assert resp.json()["deleted_count"] == 0

    def test_get_tenant_policy_isolates_by_tenant(
        self, client, test_tenant, second_tenant, db_session
    ):
        """GET /test/tenant-policy only returns rows for the test tenant, not other tenants."""
        # Reset test-tenant state first
        client.delete("/api/v1/notifications/test/tenant-policy")

        # Insert a policy row for second_tenant directly via DB
        # Must use a valid category_id from notification_category
        second_tenant_policy = NotificationDefaultPolicy(
            id=uuid.uuid4(),
            tenant_id=second_tenant.id,
            category_id=CATEGORY_A,  # billing — valid FK
            channel="push",
            enabled=True,
        )
        db_session.add(second_tenant_policy)
        db_session.flush()

        # Insert a row for test_tenant via the test endpoint (different category)
        put_resp = client.put(
            f"/api/v1/notifications/test/tenant-policy/{CATEGORY_B}/push",
            json={"enabled": False},
        )
        assert put_resp.status_code == 200

        # GET test/tenant-policy must only return test_tenant rows
        resp = client.get("/api/v1/notifications/test/tenant-policy")
        assert resp.status_code == 200
        policies = resp.json()["policies"]

        # Verify returned list matches only test_tenant DB rows
        test_tenant_db_rows = db_session.exec(
            select(NotificationDefaultPolicy).where(
                NotificationDefaultPolicy.tenant_id == TEST_TENANT_ID
            )
        ).all()
        assert len(policies) == len(test_tenant_db_rows)

        # Verify second_tenant's policy is NOT in the returned list
        returned_tenant_ids_implied = {
            (p["category_id"], p["channel"]) for p in policies
        }
        # second_tenant row: billing/push — if test_tenant also has billing/push it would
        # be ambiguous, but we only inserted job_activity/push for test_tenant.
        # Assert job_activity/push IS present and billing/push IS NOT present
        # (because we only inserted billing for second_tenant, not test_tenant)
        assert (CATEGORY_B, "push") in returned_tenant_ids_implied
        # billing/push should NOT be returned (it belongs to second_tenant only)
        assert (CATEGORY_A, "push") not in returned_tenant_ids_implied

    def test_reset_tenant_policy_requires_owner_permission(
        self, client, test_tenant, mock_cognito_jwt, db_session
    ):
        """DELETE /tenant-policy (authenticated) returns 403 for technician role."""
        from app.models.core import User

        # Get the seeded tech user (technician role, does NOT have tenant_default.edit)
        tech_user = db_session.exec(
            select(User).where(User.email == "tech@pilot.local")
        ).first()
        assert tech_user is not None, "tech@pilot.local seeded user not found"

        # Mock JWT as the tech user
        mock_cognito_jwt(tech_user)

        # Attempt to DELETE the authenticated endpoint — must return 403
        resp = client.delete("/api/v1/notifications/tenant-policy")
        assert resp.status_code == 403
