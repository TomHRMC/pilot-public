"""
Tests for FIND-058: Payment Method Customer Vaulting

Coverage:
- GET /customers/{id}/payment-methods (list active methods)
- POST /customers/{id}/payment-methods (vault new method)
- DELETE /customers/{id}/payment-methods/{pm_id} (soft-delete)
- IDOR verification (cross-tenant isolation)
- No PATCH endpoint registered
"""

import pytest
from fastapi import status

from app.models.billing import PaymentMethod, PaymentType
from app.models.crm import Customer


@pytest.fixture
def payment_type(db_session, test_tenant):
    """Create a test payment type."""
    pt = PaymentType(
        tenant_id=test_tenant.id,
        code="card",
        name="Credit Card",
        is_active=True,
    )
    db_session.add(pt)
    db_session.commit()
    db_session.refresh(pt)
    return pt


@pytest.fixture
def customer_a(db_session, test_tenant):
    """Create a test customer in test_tenant."""
    c = Customer(
        tenant_id=test_tenant.id,
        type="person",
        display_name="Test Customer A",
    )
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    return c


@pytest.fixture
def customer_b(db_session, test_tenant):
    """Create a second test customer in test_tenant."""
    c = Customer(
        tenant_id=test_tenant.id,
        type="person",
        display_name="Test Customer B",
    )
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    return c


@pytest.fixture
def other_tenant_customer(db_session, second_tenant):
    """Create a customer in a different tenant for IDOR testing."""
    c = Customer(
        tenant_id=second_tenant.id,
        type="person",
        display_name="Other Tenant Customer",
    )
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    return c


class TestPaymentMethodVaulting:
    """FIND-058: Payment Method Customer Vaulting."""

    def test_list_payment_methods_empty(
        self,
        client,
        mock_cognito_jwt,
        test_user,
        customer_a,
    ):
        """GET /customers/{id}/payment-methods returns empty list for new customer."""
        mock_cognito_jwt(test_user)
        response = client.get(f"/api/v1/customers/{customer_a.id}/payment-methods")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_create_payment_method_success(
        self,
        client,
        mock_cognito_jwt,
        test_user,
        customer_a,
        payment_type,
    ):
        """POST /customers/{id}/payment-methods vaults a new payment method."""
        mock_cognito_jwt(test_user)
        payload = {
            "psp_payment_method_id": "pm_1234567890",
            "payment_type_id": str(payment_type.id),
        }
        response = client.post(
            f"/api/v1/customers/{customer_a.id}/payment-methods",
            json=payload,
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["customer_id"] == str(customer_a.id)
        assert data["psp_payment_method_id"] == "pm_1234567890"
        assert data["is_active"] is True
        assert data["psp_provider"] == "stripe"

    def test_list_payment_methods_returns_vaulted(
        self,
        client,
        mock_cognito_jwt,
        test_user,
        customer_a,
        payment_type,
    ):
        """GET /customers/{id}/payment-methods returns vaulted methods."""
        mock_cognito_jwt(test_user)

        # Vault a payment method
        payload = {
            "psp_payment_method_id": "pm_test001",
            "payment_type_id": str(payment_type.id),
        }
        create_resp = client.post(
            f"/api/v1/customers/{customer_a.id}/payment-methods",
            json=payload,
        )
        assert create_resp.status_code == status.HTTP_201_CREATED

        # List payment methods
        list_resp = client.get(f"/api/v1/customers/{customer_a.id}/payment-methods")
        assert list_resp.status_code == status.HTTP_200_OK
        methods = list_resp.json()
        assert len(methods) == 1
        assert methods[0]["psp_payment_method_id"] == "pm_test001"

    def test_delete_payment_method_soft_deletes(
        self,
        client,
        mock_cognito_jwt,
        test_user,
        customer_a,
        payment_type,
    ):
        """DELETE /customers/{id}/payment-methods/{pm_id} soft-deletes (is_active=false)."""
        mock_cognito_jwt(test_user)

        # Vault a payment method
        payload = {
            "psp_payment_method_id": "pm_delete_test",
            "payment_type_id": str(payment_type.id),
        }
        create_resp = client.post(
            f"/api/v1/customers/{customer_a.id}/payment-methods",
            json=payload,
        )
        pm_id = create_resp.json()["id"]

        # Delete payment method
        delete_resp = client.delete(
            f"/api/v1/customers/{customer_a.id}/payment-methods/{pm_id}"
        )
        assert delete_resp.status_code == status.HTTP_200_OK
        assert delete_resp.json()["message"] == "Payment method deleted successfully"
        assert delete_resp.json()["id"] == pm_id

        # Verify it no longer appears in list
        list_resp = client.get(f"/api/v1/customers/{customer_a.id}/payment-methods")
        assert list_resp.status_code == status.HTTP_200_OK
        assert list_resp.json() == []

    def test_customer_not_found_returns_404(
        self,
        client,
        mock_cognito_jwt,
        test_user,
    ):
        """GET /customers/{invalid_id}/payment-methods returns 404."""
        mock_cognito_jwt(test_user)
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/api/v1/customers/{fake_id}/payment-methods")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_idor_cannot_list_other_tenant_customer(
        self,
        client,
        mock_cognito_jwt,
        test_user,
        other_tenant_customer,
    ):
        """Cannot list payment methods for customer in different tenant (IDOR check)."""
        mock_cognito_jwt(test_user)
        response = client.get(
            f"/api/v1/customers/{other_tenant_customer.id}/payment-methods"
        )
        # Should return 404, not expose existence of customer in other tenant
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_idor_cannot_create_for_other_tenant_customer(
        self,
        client,
        mock_cognito_jwt,
        test_user,
        other_tenant_customer,
        payment_type,
    ):
        """Cannot vault payment method for customer in different tenant (IDOR check)."""
        mock_cognito_jwt(test_user)
        payload = {
            "psp_payment_method_id": "pm_hack_attempt",
            "payment_type_id": str(payment_type.id),
        }
        response = client.post(
            f"/api/v1/customers/{other_tenant_customer.id}/payment-methods",
            json=payload,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_idor_cannot_delete_other_tenant_customer_payment_method(
        self,
        client,
        mock_cognito_jwt,
        test_user,
        customer_a,
        other_tenant_customer,
        db_session,
        second_tenant,
    ):
        """Cannot delete payment method from customer in different tenant (IDOR check)."""
        # Create payment method on other_tenant_customer using direct DB insert
        other_pt = PaymentType(
            tenant_id=second_tenant.id,
            code="card",
            name="Credit Card",
            is_active=True,
        )
        db_session.add(other_pt)
        db_session.commit()

        pm = PaymentMethod(
            tenant_id=second_tenant.id,
            customer_id=other_tenant_customer.id,
            payment_type_id=other_pt.id,
            psp_provider="stripe",
            psp_payment_method_id="pm_other_tenant",
        )
        db_session.add(pm)
        db_session.commit()

        # Attempt to delete using test_tenant auth
        mock_cognito_jwt(test_user)
        response = client.delete(
            f"/api/v1/customers/{other_tenant_customer.id}/payment-methods/{pm.id}"
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_multiple_payment_methods_per_customer(
        self,
        client,
        mock_cognito_jwt,
        test_user,
        customer_a,
        payment_type,
    ):
        """Customer can have multiple active payment methods."""
        mock_cognito_jwt(test_user)

        # Vault first method
        payload1 = {
            "psp_payment_method_id": "pm_first",
            "payment_type_id": str(payment_type.id),
        }
        resp1 = client.post(
            f"/api/v1/customers/{customer_a.id}/payment-methods",
            json=payload1,
        )
        assert resp1.status_code == status.HTTP_201_CREATED

        # Vault second method
        payload2 = {
            "psp_payment_method_id": "pm_second",
            "payment_type_id": str(payment_type.id),
        }
        resp2 = client.post(
            f"/api/v1/customers/{customer_a.id}/payment-methods",
            json=payload2,
        )
        assert resp2.status_code == status.HTTP_201_CREATED

        # List and verify both present
        list_resp = client.get(f"/api/v1/customers/{customer_a.id}/payment-methods")
        assert list_resp.status_code == status.HTTP_200_OK
        methods = list_resp.json()
        assert len(methods) == 2
        psp_ids = {m["psp_payment_method_id"] for m in methods}
        assert psp_ids == {"pm_first", "pm_second"}

    def test_payment_methods_isolated_between_customers(
        self,
        client,
        mock_cognito_jwt,
        test_user,
        customer_a,
        customer_b,
        payment_type,
    ):
        """Payment methods for customer A do not appear in customer B's list."""
        mock_cognito_jwt(test_user)

        # Vault method for customer A
        payload_a = {
            "psp_payment_method_id": "pm_customer_a",
            "payment_type_id": str(payment_type.id),
        }
        client.post(
            f"/api/v1/customers/{customer_a.id}/payment-methods",
            json=payload_a,
        )

        # List methods for customer B (should be empty)
        list_resp_b = client.get(f"/api/v1/customers/{customer_b.id}/payment-methods")
        assert list_resp_b.status_code == status.HTTP_200_OK
        assert list_resp_b.json() == []

    def test_duplicate_psp_payment_method_id_rejected(
        self,
        client,
        mock_cognito_jwt,
        test_user,
        customer_a,
        customer_b,
        payment_type,
    ):
        """Cannot vault same PSP payment method ID twice within tenant."""
        mock_cognito_jwt(test_user)

        payload = {
            "psp_payment_method_id": "pm_duplicate_test",
            "payment_type_id": str(payment_type.id),
        }

        # Vault for customer A
        resp_a = client.post(
            f"/api/v1/customers/{customer_a.id}/payment-methods",
            json=payload,
        )
        assert resp_a.status_code == status.HTTP_201_CREATED

        # Attempt same PSP ID for customer B (should fail)
        resp_b = client.post(
            f"/api/v1/customers/{customer_b.id}/payment-methods",
            json=payload,
        )
        assert resp_b.status_code == status.HTTP_400_BAD_REQUEST
        assert "already vaulted" in resp_b.json()["detail"].lower()

    def test_no_patch_endpoint_registered(
        self,
        client,
        mock_cognito_jwt,
        test_user,
        customer_a,
    ):
        """Verify PATCH endpoint does not exist for payment methods."""
        mock_cognito_jwt(test_user)
        response = client.patch(
            f"/api/v1/customers/{customer_a.id}/payment-methods/fake-id",
            json={},
        )
        # 405 Method Not Allowed or 404 depending on routing
        assert response.status_code in (
            status.HTTP_405_METHOD_NOT_ALLOWED,
            status.HTTP_404_NOT_FOUND,
        )
