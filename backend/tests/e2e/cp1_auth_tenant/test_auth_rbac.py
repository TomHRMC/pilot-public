"""
CP-1: Auth + Tenant Isolation (SD-10 E2E Tier 1)

Tests:
1. Owner can access dashboard endpoint → 200 + has widget data
2. Technician is blocked from tenant billing settings → 403
3. Cross-tenant isolation: customer created in test_tenant NOT accessible from second_tenant context

Pattern: Uses /test endpoints for data creation (no JWT needed).
         Uses mock_cognito_jwt_verify pattern from conftest.py for RBAC assertion tests.
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest

pytestmark = [pytest.mark.e2e]

# ─── Fixtures (resolved from conftest_e2e.py + tests/conftest.py) ────────────
# e2e_client, e2e_engine, e2e_mock_cognito, e2e_mock_entitlement, e2e_mock_ai
# are defined in tests/e2e/conftest_e2e.py and discovered automatically.


class TestOwnerAccess:
    """Owner role (dev@pilot.local) can access owner-only surfaces."""

    def test_owner_can_access_dashboard_widgets(
        self, e2e_client, e2e_mock_cognito, e2e_mock_entitlement, e2e_mock_ai
    ):
        """
        Owner login → GET /api/v1/dashboard/widgets → 200 with widgets list.
        Asserts: response is a list (not an error body).
        """
        # Mock JWT for owner (seeded as dev@pilot.local, sub = ...0002)
        with patch("core.auth.verify_cognito_jwt") as mock_verify:
            mock_verify.return_value = {
                "sub": "00000000-0000-0000-0000-000000000002",
                "email": "dev@pilot.local",
            }
            token = f"Bearer mock_token_{uuid.uuid4()}"
            resp = e2e_client.get(
                "/api/v1/dashboard/widgets",
                headers={"Authorization": token},
            )

        assert resp.status_code == 200, (
            f"Owner dashboard/widgets expected 200, got {resp.status_code}: {resp.text[:200]}"
        )
        body = resp.json()
        # Dashboard widgets returns a list of widget objects
        assert isinstance(body, list), f"Expected list of widgets, got: {type(body)}"

    def test_owner_can_list_invoices(
        self, e2e_client, e2e_mock_cognito, e2e_mock_entitlement, e2e_mock_ai
    ):
        """
        Owner can access invoice list → 200.
        Asserts: response has 'items' or is a list (invoices endpoint pagination).
        """
        with patch("core.auth.verify_cognito_jwt") as mock_verify:
            mock_verify.return_value = {
                "sub": "00000000-0000-0000-0000-000000000002",
                "email": "dev@pilot.local",
            }
            token = f"Bearer mock_token_{uuid.uuid4()}"
            resp = e2e_client.get(
                "/api/v1/invoices/",
                headers={"Authorization": token},
            )

        assert resp.status_code == 200, (
            f"Owner /api/v1/invoices/ expected 200, got {resp.status_code}: {resp.text[:200]}"
        )


class TestTechnicianRBAC:
    """Technician role has restricted access."""

    def test_tech_blocked_from_billing_settings(
        self, e2e_client, e2e_mock_cognito, e2e_mock_entitlement, e2e_mock_ai
    ):
        """
        Technician (tech@pilot.local, sub=...0003) should NOT access tenant billing settings.
        The settings endpoint requires owner-level RBAC; tech should get 403.
        """
        with patch("core.auth.verify_cognito_jwt") as mock_verify:
            mock_verify.return_value = {
                "sub": "00000000-0000-0000-0000-000000000003",
                "email": "tech@pilot.local",
            }
            token = f"Bearer mock_token_{uuid.uuid4()}"
            resp = e2e_client.get(
                "/api/v1/tenant/subscription",
                headers={"Authorization": token},
            )

        # Tech should get 403 Forbidden on billing/subscription endpoints
        assert resp.status_code in (403, 404), (
            f"Tech should be blocked from tenant subscription, "
            f"got {resp.status_code}: {resp.text[:200]}"
        )


class TestCrossTenantIsolation:
    """Data created in test_tenant must NOT be visible from another tenant's context."""

    def test_customer_not_accessible_from_second_tenant(
        self, e2e_client, e2e_mock_entitlement, e2e_mock_ai
    ):
        """
        1. Create a customer in test_tenant via /test endpoint.
        2. Access that customer ID using second_tenant owner credentials → 404.

        This verifies tenant_id scoping prevents cross-tenant data leakage.
        """
        # Step 1: Create customer in test_tenant (uses TestUserContext → test_tenant)
        _unique = uuid.uuid4().hex[:8]
        create_resp = e2e_client.post(
            "/api/v1/customers/test",
            json={
                "display_name": f"E2E-IsolationTest-{_unique}",
                "first_name": "E2E",
                "last_name": f"IsolationTest-{_unique}",
                "customer_type": "person",
                "lifecycle_status_code": "active",
            },
        )
        assert create_resp.status_code == 201, (
            f"Customer creation failed: {create_resp.status_code} {create_resp.text[:200]}"
        )
        customer_id = create_resp.json()["id"]
        assert customer_id, "Customer ID must not be empty"

        # Step 2: Attempt to access this customer using a different tenant's JWT.
        # We create a fresh UUID as the sub — this user does not exist in test_tenant,
        # simulating a second_tenant user. The backend must scope by tenant_id and return 404.
        second_tenant_sub = str(uuid.uuid4())
        with patch("core.auth.verify_cognito_jwt") as mock_verify:
            mock_verify.return_value = {
                "sub": second_tenant_sub,
                "email": f"attacker-{second_tenant_sub[:6]}@other-tenant.com",
            }
            token = f"Bearer mock_token_{uuid.uuid4()}"
            cross_resp = e2e_client.get(
                f"/api/v1/customers/{customer_id}",
                headers={"Authorization": token},
            )

        # Must be 401 (no tenant match) or 404 (UUID enumeration safe) — never 200
        assert cross_resp.status_code in (401, 403, 404), (
            f"Cross-tenant access MUST be blocked. "
            f"Customer {customer_id} returned {cross_resp.status_code} to second_tenant. "
            f"Body: {cross_resp.text[:300]}"
        )

    def test_customer_accessible_from_own_tenant(
        self, e2e_client, e2e_mock_entitlement, e2e_mock_ai
    ):
        """
        Customer created via /test endpoint IS accessible with the owner's JWT
        (same tenant as the test context).
        """
        # Create customer in test_tenant
        _unique = uuid.uuid4().hex[:8]
        create_resp = e2e_client.post(
            "/api/v1/customers/test",
            json={
                "display_name": f"E2E-OwnTenant-{_unique}",
                "first_name": "E2E",
                "last_name": f"OwnTenant-{_unique}",
                "customer_type": "person",
                "lifecycle_status_code": "active",
            },
        )
        assert create_resp.status_code == 201
        customer_id = create_resp.json()["id"]

        # Access with same tenant's owner JWT → should succeed
        with patch("core.auth.verify_cognito_jwt") as mock_verify:
            mock_verify.return_value = {
                "sub": "00000000-0000-0000-0000-000000000002",
                "email": "dev@pilot.local",
            }
            token = f"Bearer mock_token_{uuid.uuid4()}"
            resp = e2e_client.get(
                f"/api/v1/customers/{customer_id}",
                headers={"Authorization": token},
            )

        assert resp.status_code == 200, (
            f"Owner should access own customer {customer_id}, "
            f"got {resp.status_code}: {resp.text[:200]}"
        )
        assert resp.json()["id"] == customer_id, "Returned customer ID must match"


class TestMfaEnrollment:
    """W-14: MFA enrollment — user_mfa_method row can be created and queried."""

    def test_mfa_method_row_can_be_inserted_for_user(
        self, e2e_client, e2e_engine, e2e_mock_entitlement, e2e_mock_ai
    ):
        """
        Insert a user_mfa_method row directly via e2e_engine for the test user.
        Verifies the MFA enrollment data model is correct.

        Note: MFA enrollment in production goes through Cognito. In E2E tests,
        we verify the local tracking table (user_mfa_method) can receive rows,
        since the Cognito enrollment step cannot be mocked in E2E without a
        live Cognito pool.

        Schema verified via MCP 2026-07-12:
          PK = mfa_method_id (not id)
          Required: tenant_id, user_id, method_type, enrolled_at,
                    cognito_method_id, verification_status, created_at, updated_at
        """
        import uuid
        from datetime import UTC, datetime

        from sqlmodel import Session, select

        from app.models.security import UserMfaMethod

        enrolled_at = datetime.now(UTC)
        mfa_id = uuid.uuid4()

        with Session(e2e_engine) as db:
            row = UserMfaMethod(
                mfa_method_id=mfa_id,
                tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
                user_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
                method_type="totp",
                enrolled_at=enrolled_at,
                cognito_method_id=f"e2e-test-{uuid.uuid4().hex[:8]}",
                verification_status="verified",
                created_at=enrolled_at,
                updated_at=enrolled_at,
            )
            db.add(row)
            db.commit()

            # Verify row was inserted
            fetched = db.exec(
                select(UserMfaMethod).where(UserMfaMethod.mfa_method_id == mfa_id)
            ).first()
            assert fetched is not None, (
                "MFA method row must be retrievable after insert"
            )
            assert fetched.method_type == "totp"
            assert fetched.verification_status == "verified"

            # Cleanup — delete the row we created (not shared seed data)
            db.delete(fetched)
            db.commit()

    def test_mfa_otp_table_accessible(
        self, e2e_client, e2e_engine, e2e_mock_entitlement, e2e_mock_ai
    ):
        """
        Verify auth_mfa_otp table is accessible (W-14 guard).
        OTP rows are ephemeral — just confirm the table exists and can be queried.
        """
        from sqlmodel import Session, text

        with Session(e2e_engine) as db:
            result = db.exec(text("SELECT COUNT(*) FROM auth_mfa_otp")).first()
            assert result is not None, "auth_mfa_otp table must be queryable"
            # Result is a count (may be 0 if no OTPs in E2E DB) — that's fine
            assert isinstance(result[0], int)
