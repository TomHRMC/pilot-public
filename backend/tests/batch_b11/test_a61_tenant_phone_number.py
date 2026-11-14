"""
B11/A61 — Tenant Phone Number Provisioning Tests
=================================================
Tests for:
  - TenantPhoneNumber ORM model fields
  - provision_for_tenant(): success, duplicate, failure
  - GET list endpoint (returns only numbers for tenant)
  - POST provision endpoint (409 on duplicate)
"""

import uuid
from unittest.mock import patch

from app.models.sms import TenantPhoneNumber
from services.sms_carrier import MockSmsCarrier
from services.sms_provisioning import (
    get_active_number_for_tenant,
    provision_for_tenant,
)

# ─── ORM Model ────────────────────────────────────────────────────────────────


class TestTenantPhoneNumberModel:
    """Verify TenantPhoneNumber ORM fields."""

    def test_model_has_required_fields(self):
        assert hasattr(TenantPhoneNumber, "id")
        assert hasattr(TenantPhoneNumber, "tenant_id")
        assert hasattr(TenantPhoneNumber, "phone_number")
        assert hasattr(TenantPhoneNumber, "area_code")
        assert hasattr(TenantPhoneNumber, "carrier")
        assert hasattr(TenantPhoneNumber, "status")
        assert hasattr(TenantPhoneNumber, "monthly_fee_cents")
        assert hasattr(TenantPhoneNumber, "provisioned_at")
        assert hasattr(TenantPhoneNumber, "released_at")

    def test_model_defaults(self):
        tenant_id = uuid.uuid4()
        record = TenantPhoneNumber(
            tenant_id=tenant_id,
            phone_number="+15125550001",
            area_code="512",
        )
        assert record.carrier == "telnyx"
        assert record.status == "active"
        assert record.monthly_fee_cents == 100


# ─── Provisioning Service ─────────────────────────────────────────────────────


class TestProvisionForTenant:
    """Test provision_for_tenant() service function."""

    def test_success_with_mock_carrier(self, db_session, test_tenant):
        """Provisioning should persist a record and return success."""
        mock_carrier = MockSmsCarrier()

        with patch(
            "services.sms_provisioning.get_sms_carrier", return_value=mock_carrier
        ):
            result = provision_for_tenant(
                db=db_session,
                tenant_id=test_tenant.id,
                area_code="512",
            )

        assert result.success is True
        assert result.phone_number.startswith("+1512")
        assert result.tenant_phone_number_id is not None
        assert result.error is None

        # Verify DB record
        record = get_active_number_for_tenant(db_session, test_tenant.id)
        assert record is not None
        assert record.phone_number == result.phone_number
        assert record.status == "active"
        assert record.carrier == "telnyx"

    def test_duplicate_returns_existing_number(self, db_session, test_tenant):
        """Second provision call should return the existing active number, not create a new one."""
        mock_carrier = MockSmsCarrier()

        with patch(
            "services.sms_provisioning.get_sms_carrier", return_value=mock_carrier
        ):
            result1 = provision_for_tenant(db_session, test_tenant.id, area_code="512")
            result2 = provision_for_tenant(db_session, test_tenant.id, area_code="512")

        assert result1.success is True
        assert result2.success is False
        assert result2.tenant_phone_number_id == result1.tenant_phone_number_id
        assert "already has an active" in result2.error

    def test_carrier_failure_returns_suggestions(self, db_session, test_tenant):
        """On carrier failure, result should be success=False with suggested area codes."""
        failing_carrier = MockSmsCarrier()
        failing_carrier.provision_number = lambda area_code, tenant_id: (
            _ for _ in ()
        ).throw(Exception("Telnyx: no numbers available"))

        with patch(
            "services.sms_provisioning.get_sms_carrier", return_value=failing_carrier
        ):
            result = provision_for_tenant(db_session, test_tenant.id, area_code="512")

        assert result.success is False
        assert result.error is not None
        assert len(result.suggested_area_codes) > 0

    def test_get_active_number_none_when_not_provisioned(self, db_session, test_tenant):
        """No active number for a fresh tenant."""
        # Use a brand-new tenant UUID that has no number
        fresh_id = uuid.uuid4()
        record = get_active_number_for_tenant(db_session, fresh_id)
        assert record is None

    def test_default_area_code_used_when_none_provided(self, db_session, test_tenant):
        """When area_code is None, should default to '512'."""
        mock_carrier = MockSmsCarrier()

        with patch(
            "services.sms_provisioning.get_sms_carrier", return_value=mock_carrier
        ):
            result = provision_for_tenant(db_session, test_tenant.id, area_code=None)

        assert result.success is True
        record = get_active_number_for_tenant(db_session, test_tenant.id)
        assert record.area_code == "512"


# ─── API Route ────────────────────────────────────────────────────────────────


class TestTenantPhoneNumberRoute:
    """Test the provision + list API endpoints."""

    def test_provision_returns_200_with_mock(self, client, test_tenant):
        """Provisioning with MockSmsCarrier should return 200 with phone_number."""
        mock_carrier = MockSmsCarrier()

        with patch(
            "services.sms_provisioning.get_sms_carrier", return_value=mock_carrier
        ):
            resp = client.post(
                f"/api/v1/tenants/{test_tenant.id}/phone-numbers/test/provision",
                json={"area_code": "512"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "phone_number" in data
        assert data["carrier"] == "telnyx"
        assert data["status"] == "active"

    def test_list_endpoint_returns_numbers(self, client, db_session, test_tenant):
        """After provisioning, the list endpoint should show the number."""
        mock_carrier = MockSmsCarrier()

        with patch(
            "services.sms_provisioning.get_sms_carrier", return_value=mock_carrier
        ):
            # Provision first
            provision_for_tenant(db_session, test_tenant.id, area_code="512")

        resp = client.get(
            f"/api/v1/tenants/{test_tenant.id}/phone-numbers/test",
            params={"tenant_id": str(test_tenant.id)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "numbers" in data

    def test_provision_twice_returns_409(self, client, db_session, test_tenant):
        """Second provision call via API should return 409."""
        mock_carrier = MockSmsCarrier()

        with patch(
            "services.sms_provisioning.get_sms_carrier", return_value=mock_carrier
        ):
            # First provision
            provision_for_tenant(db_session, test_tenant.id, area_code="512")

            # Second provision via API
            resp = client.post(
                f"/api/v1/tenants/{test_tenant.id}/phone-numbers/test/provision",
                json={"area_code": "512"},
            )

        assert resp.status_code == 409
