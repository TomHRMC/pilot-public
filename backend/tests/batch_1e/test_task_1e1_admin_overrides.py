"""
Task 1-E-1: Admin Tenant Feature Override API Tests

Verifies endpoints under /api/v1/admin/tenants/{tenant_id}/overrides:

  A. POST /overrides/test → 201, creates TenantProductFeatureOverride in DB.
  B. POST /overrides/test (existing code) → 200/201, updates the row (upsert, no IntegrityError).
  C. Redis DELETE is called with the correct cache key format on every upsert.
  D. Tenant user (role without tenants.manage) hitting the authenticated endpoint → 403 Forbidden.

Reference: dev-docs/analysis/db-schema-domain-mvp-features-impl-plan.md Task 1-E-1
Batch 1-E Verification:
  - Override created/updated via POST /overrides/test is readable via GET /overrides/test.
  - Entitlement cache key deleted on every successful upsert.
"""

import uuid
from unittest.mock import MagicMock, patch

from sqlmodel import select

from app.models.auth import TenantUser, TenantUserRole, TenantUserStatus
from app.models.billing import ProductFeature, TenantProductFeatureOverride
from app.models.core import User

# ============================================================
# Helpers
# ============================================================

_FEATURE_CODE = "voice_quotes_per_month"


def _ensure_product_feature(db_session, code: str = _FEATURE_CODE) -> ProductFeature:
    """Ensure a ProductFeature row exists (FK target for overrides)."""
    feat = db_session.exec(
        select(ProductFeature).where(ProductFeature.code == code)
    ).first()
    if not feat:
        feat = ProductFeature(
            code=code,
            name="Voice Quotes Per Month",
            unit="quotes",
            description="Number of voice-generated quotes allowed per billing month.",
            is_active=True,
        )
        db_session.add(feat)
        db_session.flush()
    return feat


def _make_override_payload(
    feature_code: str = _FEATURE_CODE,
    limit_quantity: int = 50,
    enabled: bool = True,
) -> dict:
    return {
        "product_feature_code": feature_code,
        "limit_quantity": limit_quantity,
        "included_quantity": None,
        "overage_price_cents": None,
        "overage_cap_per_period": None,
        "alert_threshold_pct": 80,
        "enabled": enabled,
    }


def _create_technician_user(db_session, test_tenant) -> User:
    """
    Create a user with the 'technician' role under test_tenant.
    The technician role must NOT have 'tenants.manage' permission.
    Returns the created User for JWT mocking.
    """
    # Ensure a 'technician' TenantUserRole exists without tenants.manage
    role = db_session.exec(
        select(TenantUserRole).where(TenantUserRole.code == "technician")
    ).first()
    if not role:
        role = TenantUserRole(
            code="technician",
            name="Technician",
            permissions={"permissions": ["jobs.view", "jobs.update", "voice.create"]},
            is_default=False,
            is_active=True,
        )
        db_session.add(role)
        db_session.flush()

    # TenantUserStatus for this test tenant
    status = db_session.exec(
        select(TenantUserStatus).where(
            TenantUserStatus.tenant_id == test_tenant.id,
            TenantUserStatus.code == "active",
        )
    ).first()
    if not status:
        status = TenantUserStatus(
            id=uuid.uuid4(),
            tenant_id=test_tenant.id,
            code="active",
            name="Active",
            is_default=True,
            is_active=True,
        )
        db_session.add(status)
        db_session.flush()

    # Create a distinct user for this test
    email = f"tech-{uuid.uuid4()}@pilot.local"
    user = User(
        id=uuid.uuid4(),
        email=email,
        first_name="Field",
        last_name="Tech",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    tenant_user = TenantUser(
        tenant_id=test_tenant.id,
        user_id=user.id,
        role_code="technician",
        status_id=status.id,
        is_active=True,
    )
    db_session.add(tenant_user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ============================================================
# Test A — POST creates a new override row (201)
# ============================================================


class TestAdminOverrideCreate:
    """Test A: POSTing a new override returns 201 and persists to DB."""

    def test_post_override_creates_db_row(self, client, db_session, test_tenant):
        """
        POST /api/v1/admin/tenants/{id}/overrides/test with a new feature code
        returns 201 and writes a TenantProductFeatureOverride row to the DB.
        """
        _ensure_product_feature(db_session)
        db_session.commit()

        payload = _make_override_payload(limit_quantity=25)

        with patch("api.routes.admin_tenants._get_redis_client") as mock_redis_factory:
            mock_redis = MagicMock()
            mock_redis_factory.return_value = mock_redis

            resp = client.post(
                f"/api/v1/admin/tenants/{test_tenant.id}/overrides/test",
                json=payload,
            )

        assert resp.status_code == 201, resp.text
        body = resp.json()

        # Response fields
        assert body["tenant_id"] == str(test_tenant.id)
        assert body["product_feature_code"] == _FEATURE_CODE
        assert body["limit_quantity"] == 25
        assert body["alert_threshold_pct"] == 80
        assert body["enabled"] is True

        # DB record exists
        row = db_session.exec(
            select(TenantProductFeatureOverride).where(
                TenantProductFeatureOverride.tenant_id == test_tenant.id,
                TenantProductFeatureOverride.product_feature_code == _FEATURE_CODE,
            )
        ).first()
        assert row is not None
        assert row.limit_quantity == 25
        assert row.enabled is True

    def test_post_override_get_returns_list(self, client, db_session, test_tenant):
        """GET /overrides/test returns the newly created override."""
        _ensure_product_feature(db_session)
        db_session.commit()

        with patch("api.routes.admin_tenants._get_redis_client") as mock_redis_factory:
            mock_redis_factory.return_value = MagicMock()
            client.post(
                f"/api/v1/admin/tenants/{test_tenant.id}/overrides/test",
                json=_make_override_payload(limit_quantity=10),
            )

        resp = client.get(f"/api/v1/admin/tenants/{test_tenant.id}/overrides/test")
        assert resp.status_code == 200, resp.text
        codes = [item["product_feature_code"] for item in resp.json()]
        assert _FEATURE_CODE in codes


# ============================================================
# Test B — POST on existing feature code updates the row (upsert)
# ============================================================


class TestAdminOverrideUpsert:
    """Test B: POSTing an override for an existing feature code updates (no IntegrityError)."""

    def test_upsert_updates_existing_row(self, client, db_session, test_tenant):
        """
        A second POST for the same (tenant_id, product_feature_code) updates the
        existing row instead of raising an IntegrityError / 500.
        """
        _ensure_product_feature(db_session)
        db_session.commit()

        with patch("api.routes.admin_tenants._get_redis_client") as mock_redis_factory:
            mock_redis_factory.return_value = MagicMock()

            # First POST — creates
            r1 = client.post(
                f"/api/v1/admin/tenants/{test_tenant.id}/overrides/test",
                json=_make_override_payload(limit_quantity=10),
            )
            assert r1.status_code == 201, r1.text

            # Second POST — same feature code, new limit
            r2 = client.post(
                f"/api/v1/admin/tenants/{test_tenant.id}/overrides/test",
                json=_make_override_payload(limit_quantity=999),
            )

        # Must succeed — not a 500 / IntegrityError
        assert r2.status_code == 201, r2.text
        assert r2.json()["limit_quantity"] == 999

        # Exactly one DB row (not two)
        rows = db_session.exec(
            select(TenantProductFeatureOverride).where(
                TenantProductFeatureOverride.tenant_id == test_tenant.id,
                TenantProductFeatureOverride.product_feature_code == _FEATURE_CODE,
            )
        ).all()
        assert len(rows) == 1
        assert rows[0].limit_quantity == 999

    def test_upsert_can_toggle_enabled_false(self, client, db_session, test_tenant):
        """Upserting with enabled=False disables the feature for the tenant."""
        _ensure_product_feature(db_session)
        db_session.commit()

        with patch("api.routes.admin_tenants._get_redis_client") as mock_redis_factory:
            mock_redis_factory.return_value = MagicMock()

            client.post(
                f"/api/v1/admin/tenants/{test_tenant.id}/overrides/test",
                json=_make_override_payload(enabled=True),
            )
            r2 = client.post(
                f"/api/v1/admin/tenants/{test_tenant.id}/overrides/test",
                json=_make_override_payload(enabled=False),
            )

        assert r2.status_code == 201, r2.text
        assert r2.json()["enabled"] is False

        row = db_session.exec(
            select(TenantProductFeatureOverride).where(
                TenantProductFeatureOverride.tenant_id == test_tenant.id,
                TenantProductFeatureOverride.product_feature_code == _FEATURE_CODE,
            )
        ).first()
        assert row is not None
        assert row.enabled is False


# ============================================================
# Test C — Redis DELETE called with correct cache key
# ============================================================


class TestAdminOverrideRedisCacheInvalidation:
    """Test C: The Redis delete method is called with the correct cache key format."""

    def test_redis_delete_called_with_correct_key(
        self, client, db_session, test_tenant
    ):
        """
        On every successful upsert, _get_redis_client().delete() must be called
        with the exact key "entitlement:{tenant_id}:{product_feature_code}".
        """
        _ensure_product_feature(db_session)
        db_session.commit()

        expected_key = f"entitlement:{test_tenant.id}:{_FEATURE_CODE}"

        with patch("api.routes.admin_tenants._get_redis_client") as mock_redis_factory:
            mock_client = MagicMock()
            mock_redis_factory.return_value = mock_client

            resp = client.post(
                f"/api/v1/admin/tenants/{test_tenant.id}/overrides/test",
                json=_make_override_payload(),
            )

        assert resp.status_code == 201, resp.text

        # Verify the delete was called at least once with the exact cache key
        mock_client.delete.assert_called_once_with(expected_key)

    def test_redis_delete_called_on_upsert_update(
        self, client, db_session, test_tenant
    ):
        """Redis delete is also called when updating an existing override."""
        _ensure_product_feature(db_session)
        db_session.commit()

        expected_key = f"entitlement:{test_tenant.id}:{_FEATURE_CODE}"

        with patch("api.routes.admin_tenants._get_redis_client") as mock_redis_factory:
            mock_client = MagicMock()
            mock_redis_factory.return_value = mock_client

            # Create
            client.post(
                f"/api/v1/admin/tenants/{test_tenant.id}/overrides/test",
                json=_make_override_payload(limit_quantity=5),
            )
            # Update
            client.post(
                f"/api/v1/admin/tenants/{test_tenant.id}/overrides/test",
                json=_make_override_payload(limit_quantity=100),
            )

        # Should be called twice (once per POST)
        assert mock_client.delete.call_count == 2
        for call in mock_client.delete.call_args_list:
            assert call.args[0] == expected_key


# ============================================================
# Test D — Tenant user (no tenants.manage) gets 403 on authenticated endpoint
# ============================================================


class TestAdminOverrideRBACEnforcement:
    """Test D: A standard tenant user receives 403 Forbidden on the authenticated endpoint."""

    def test_technician_cannot_access_authenticated_endpoint(
        self, client, db_session, test_tenant, mock_cognito_jwt_verify
    ):
        """
        A user with the 'technician' role (permissions: jobs.view, jobs.update,
        voice.create) must receive 403 when attempting to POST to the authenticated
        /overrides endpoint, because they lack 'tenants.manage'.
        """
        _ensure_product_feature(db_session)
        tech_user = _create_technician_user(db_session, test_tenant)

        # Mock JWT to authenticate as the technician user
        mock_cognito_jwt_verify.return_value = {
            "sub": str(tech_user.id),
            "email": tech_user.email,
        }

        resp = client.post(
            f"/api/v1/admin/tenants/{test_tenant.id}/overrides",
            json=_make_override_payload(),
            headers={"Authorization": "Bearer mock_technician_token"},
        )

        assert resp.status_code == 403, resp.text
        body = resp.json()
        # RFC 7807 error format from PermissionDeniedError
        assert body["detail"]["status"] == 403
        assert body["detail"]["required_permission"] == "tenants.manage"

    def test_unauthenticated_request_to_authenticated_endpoint_is_403(
        self, client, db_session, test_tenant
    ):
        """
        A request to POST /overrides (authenticated endpoint) without any
        Authorization header must return 403 (not 201 or 500).
        """
        _ensure_product_feature(db_session)
        db_session.commit()

        # No Authorization header — FastAPI HTTPBearer raises 403 automatically
        resp = client.post(
            f"/api/v1/admin/tenants/{test_tenant.id}/overrides",
            json=_make_override_payload(),
        )
        # HTTPBearer raises 403 when no credentials provided
        assert resp.status_code in (401, 403), resp.text
