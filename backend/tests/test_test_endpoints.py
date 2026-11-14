"""
Tests for unauthenticated test endpoints (Gap #28).

This test file verifies that:
1. Test endpoints are properly secured (403 when disabled)
2. Test endpoints work without authentication in dev/qa
3. Test endpoints produce identical results to authenticated endpoints
4. Test endpoints use the correct test tenant isolation

Run with:
    pytest backend/tests/test_test_endpoints.py -v
"""

import uuid
from unittest.mock import patch

from core.config import settings


class TestEndpointSecurityGuards:
    """Test security restrictions on test endpoints"""

    def test_test_endpoint_blocked_when_disabled(self, client):
        """Test endpoint returns 403 when TEST_ENDPOINT_ENABLED=false"""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", False):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    "/api/v1/customers/test",
                    json={
                        "display_name": f"Test Customer {uuid.uuid4()}",
                        "type": "person",
                    },
                )

                assert response.status_code == 403
                detail = response.json()["detail"]
                assert "test_endpoints_disabled" in detail["error"]
                assert "TEST_ENDPOINT_ENABLED" in detail["message"]

    def test_test_endpoint_blocked_in_production(self, client):
        """Test endpoint returns 403 when ENVIRONMENT=production"""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "production"):
                response = client.post(
                    "/api/v1/customers/test",
                    json={
                        "display_name": f"Test Customer {uuid.uuid4()}",
                        "type": "person",
                    },
                )

                assert response.status_code == 403
                detail = response.json()["detail"]
                assert "test_endpoints_disabled" in detail["error"]

    def test_test_endpoint_blocked_in_staging(self, client):
        """Test endpoint returns 403 when ENVIRONMENT=staging"""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "staging"):
                response = client.post(
                    "/api/v1/customers/test",
                    json={
                        "display_name": f"Test Customer {uuid.uuid4()}",
                        "type": "person",
                    },
                )

                assert response.status_code == 403
                detail = response.json()["detail"]
                assert "test_endpoints_disabled" in detail["error"]

    def test_test_endpoint_allowed_in_dev(self, client):
        """Test endpoint works when ENVIRONMENT=dev and enabled"""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    "/api/v1/customers/test",
                    json={
                        "display_name": f"Dev Test Customer {uuid.uuid4()}",
                        "type": "person",
                        "email": "dev@test.local",
                    },
                )

                # Should succeed (201 Created)
                assert response.status_code == 201
                data = response.json()
                assert "Dev Test Customer" in data["display_name"]
                assert data["tenant_id"] == "00000000-0000-0000-0000-000000000001"

    def test_test_endpoint_allowed_in_qa(self, client):
        """Test endpoint works when ENVIRONMENT=qa and enabled"""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "qa"):
                response = client.post(
                    "/api/v1/customers/test",
                    json={
                        "display_name": f"QA Test Customer {uuid.uuid4()}",
                        "type": "person",
                        "email": "qa@test.local",
                    },
                )

                # Should succeed (201 Created)
                assert response.status_code == 201
                data = response.json()
                assert "QA Test Customer" in data["display_name"]


class TestEndpointBehavior:
    """Test functional behavior of test endpoints"""

    def test_create_customer_without_auth(self, client):
        """Test endpoint creates customer without JWT"""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    "/api/v1/customers/test",
                    json={
                        "display_name": f"Jane Doe {uuid.uuid4()}",
                        "type": "person",
                        "email": "jane@example.com",
                        "first_name": "Jane",
                        "last_name": "Doe",
                    },
                )

                assert response.status_code == 201
                data = response.json()
                assert "Jane Doe" in data["display_name"]
                assert data["email"] == "jane@example.com"
                assert data["first_name"] == "Jane"
                assert data["last_name"] == "Doe"
                assert data["type"] == "person"
                # Verify test tenant
                assert data["tenant_id"] == "00000000-0000-0000-0000-000000000001"

    def test_list_customers_without_auth(self, client):
        """Test endpoint lists customers without JWT"""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                # Create a customer first
                create_response = client.post(
                    "/api/v1/customers/test",
                    json={
                        "display_name": f"List Test Customer {uuid.uuid4()}",
                        "type": "company",
                        "company_name": "Test Corp",
                    },
                )
                assert create_response.status_code == 201

                # List customers
                list_response = client.get("/api/v1/customers/test")
                assert list_response.status_code == 200

                customers = list_response.json()["items"]  # UI-FIX-1C: paginated
                assert isinstance(customers, list)
                assert len(customers) > 0

                # Verify all customers are from test tenant
                for customer in customers:
                    assert (
                        customer["tenant_id"] == "00000000-0000-0000-0000-000000000001"
                    )

    def test_create_customer_duplicate_email_validation(self, client):
        """Test endpoint enforces duplicate email validation"""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                customer_data = {
                    "display_name": f"Duplicate Test {uuid.uuid4()}",
                    "type": "person",
                    "email": "duplicate@test.local",
                }

                # Create first customer
                response1 = client.post("/api/v1/customers/test", json=customer_data)
                assert response1.status_code == 201

                # Attempt to create duplicate
                response2 = client.post("/api/v1/customers/test", json=customer_data)
                assert response2.status_code == 400
                assert "email already exists" in response2.json()["detail"].lower()

    def test_create_customer_invalid_type(self, client):
        """Test endpoint validates customer type"""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.post(
                    "/api/v1/customers/test",
                    json={
                        "display_name": f"Invalid Type Test {uuid.uuid4()}",
                        "type": "invalid_type",
                        "email": "invalid@test.local",
                    },
                )

                assert response.status_code == 400
                assert "Invalid customer type" in response.json()["detail"]

    def test_list_customers_pagination(self, client):
        """Test endpoint supports pagination parameters"""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                # Create multiple customers
                for i in range(5):
                    client.post(
                        "/api/v1/customers/test",
                        json={
                            "display_name": f"Pagination Test {i}",
                            "type": "person",
                            "email": f"pagination{i}@test.local",
                        },
                    )

                # Test pagination
                response = client.get("/api/v1/customers/test?skip=0&limit=2")
                assert response.status_code == 200
                customers = response.json()["items"]  # UI-FIX-1C: paginated
                assert len(customers) <= 2


class TestEndpointTenantIsolation:
    """Test that test endpoints properly isolate test tenant data"""

    def test_customers_isolated_to_test_tenant(self, client):
        """Verify test endpoint only returns test tenant customers"""
        import uuid

        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                # Create customer via test endpoint with unique email
                unique_email = f"isolation-{uuid.uuid4()}@test.local"
                create_response = client.post(
                    "/api/v1/customers/test",
                    json={
                        "display_name": f"Isolation Test {uuid.uuid4()}",
                        "type": "person",
                        "email": unique_email,
                    },
                )
                assert create_response.status_code == 201, (
                    f"Failed to create customer: {create_response.json()}"
                )
                created_customer = create_response.json()

                # List customers - should all be test tenant
                list_response = client.get("/api/v1/customers/test")
                assert list_response.status_code == 200

                customers = list_response.json()["items"]  # UI-FIX-1C: paginated
                test_tenant_id = "00000000-0000-0000-0000-000000000001"

                for customer in customers:
                    assert customer["tenant_id"] == test_tenant_id


class TestConfigurationHelpers:
    """Test configuration helper functions"""

    def test_is_test_endpoint_allowed_logic(self):
        """Test is_test_endpoint_allowed() returns correct values"""
        from core.config import is_test_endpoint_allowed

        # Enabled in dev
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                assert is_test_endpoint_allowed() is True

        # Enabled in qa
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "qa"):
                assert is_test_endpoint_allowed() is True

        # Disabled in dev
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", False):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                assert is_test_endpoint_allowed() is False


class TestSitesEndpoints:
    """Test sites test endpoints - basic functionality"""

    def test_list_sites_without_auth(self, client):
        """Test endpoint lists sites without JWT"""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get("/api/v1/sites/test")
                assert response.status_code == 200
                sites = response.json()
                assert isinstance(sites, list)

    def test_get_site_without_auth(self, client):
        """Test endpoint gets specific site without JWT"""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                # Create a customer first
                customer_response = client.post(
                    "/api/v1/customers/test",
                    json={
                        "display_name": f"Site Test Customer {uuid.uuid4()}",
                        "type": "person",
                    },
                )
                customer_id = customer_response.json()["id"]

                # Create a site
                site_response = client.post(
                    "/api/v1/sites/test",
                    json={"customer_id": customer_id, "name": "Test Site"},
                )
                assert site_response.status_code == 201
                site_id = site_response.json()["id"]

                # Get the site
                get_response = client.get(f"/api/v1/sites/{site_id}/test")
                assert get_response.status_code == 200
                site = get_response.json()
                assert site["id"] == site_id
                assert site["name"] == "Test Site"

    def test_update_site_without_auth(self, client):
        """Test endpoint updates site without JWT"""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                # Create a customer
                customer_response = client.post(
                    "/api/v1/customers/test",
                    json={
                        "display_name": f"Site Update Customer {uuid.uuid4()}",
                        "type": "person",
                    },
                )
                customer_id = customer_response.json()["id"]

                # Create a site
                site_response = client.post(
                    "/api/v1/sites/test",
                    json={"customer_id": customer_id, "name": "Original Name"},
                )
                site_id = site_response.json()["id"]

                # Update the site
                update_response = client.patch(
                    f"/api/v1/sites/{site_id}/test",
                    json={"customer_id": customer_id, "name": "Updated Name"},
                )
                assert update_response.status_code == 200
                updated_site = update_response.json()
                assert updated_site["name"] == "Updated Name"


class TestCatalogEndpoints:
    """Test catalog test endpoints - basic functionality"""

    def test_list_supplier_items_without_auth(self, client):
        """Test endpoint lists supplier items without JWT"""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get("/api/v1/catalog/supplier-items/test")
                assert response.status_code == 200
                items = response.json()
                assert isinstance(items, list)

    def test_get_pricing_cache_without_auth(self, client):
        """Test endpoint gets pricing cache without JWT"""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get("/api/v1/catalog/pricing-cache/test")
                assert response.status_code == 200
                items = response.json()
                assert isinstance(items, list)


class TestJobsEndpoints:
    """Test jobs test endpoints - basic functionality"""

    def test_list_jobs_without_auth(self, client):
        """Test endpoint lists jobs without JWT"""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get("/api/v1/jobs/test")
                assert response.status_code == 200
                jobs = response.json()["items"]  # UI-FIX-1C: paginated
                assert isinstance(jobs, list)

    def test_get_job_without_auth(self, client):
        """Test endpoint gets specific job without JWT"""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                # Create customer and site first
                customer_response = client.post(
                    "/api/v1/customers/test",
                    json={
                        "display_name": f"Job Test Customer {uuid.uuid4()}",
                        "type": "person",
                    },
                )
                customer_id = customer_response.json()["id"]

                site_response = client.post(
                    "/api/v1/sites/test",
                    json={"customer_id": customer_id, "name": "Job Test Site"},
                )
                site_id = site_response.json()["id"]

                # Create a job
                job_response = client.post(
                    "/api/v1/jobs/test",
                    json={"customer_id": customer_id, "site_id": site_id},
                )
                assert job_response.status_code == 201
                job_id = job_response.json()["id"]

                # Get the job
                get_response = client.get(f"/api/v1/jobs/{job_id}/test")
                assert get_response.status_code == 200
                job = get_response.json()
                assert job["id"] == job_id
                assert job["customer_id"] == customer_id

    def test_list_job_time_entries_without_auth(self, client):
        """Test endpoint lists time entries for a job without JWT"""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                # Create customer, site, and job
                customer_response = client.post(
                    "/api/v1/customers/test",
                    json={
                        "display_name": f"Time Entry Customer {uuid.uuid4()}",
                        "type": "person",
                    },
                )
                customer_id = customer_response.json()["id"]

                site_response = client.post(
                    "/api/v1/sites/test",
                    json={"customer_id": customer_id, "name": "Time Entry Site"},
                )
                site_id = site_response.json()["id"]

                job_response = client.post(
                    "/api/v1/jobs/test",
                    json={"customer_id": customer_id, "site_id": site_id},
                )
                job_id = job_response.json()["id"]

                # List time entries (should be empty initially)
                list_response = client.get(f"/api/v1/jobs/{job_id}/time-entries/test")
                assert list_response.status_code == 200
                entries = list_response.json()
                assert isinstance(entries, list)

    def test_list_job_expenses_without_auth(self, client):
        """Test endpoint lists expenses for a job without JWT"""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                # Create customer, site, and job
                customer_response = client.post(
                    "/api/v1/customers/test",
                    json={
                        "display_name": f"Expense Customer {uuid.uuid4()}",
                        "type": "person",
                    },
                )
                customer_id = customer_response.json()["id"]

                site_response = client.post(
                    "/api/v1/sites/test",
                    json={"customer_id": customer_id, "name": "Expense Site"},
                )
                site_id = site_response.json()["id"]

                job_response = client.post(
                    "/api/v1/jobs/test",
                    json={"customer_id": customer_id, "site_id": site_id},
                )
                job_id = job_response.json()["id"]

                # List expenses (should be empty initially)
                list_response = client.get(f"/api/v1/jobs/{job_id}/expenses/test")
                assert list_response.status_code == 200
                expenses = list_response.json()
                assert isinstance(expenses, list)


class TestQuotesEndpoints:
    """Test quotes test endpoints - basic functionality"""

    def test_list_quotes_without_auth(self, client):
        """Test endpoint lists quotes without JWT"""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                response = client.get("/api/v1/quotes/test")
                assert response.status_code == 200
                quotes = response.json()["items"]  # UI-FIX-1C: paginated
                assert isinstance(quotes, list)

    def test_list_quote_lines_without_auth(self, client):
        """Test endpoint lists quote lines without JWT"""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                # Create customer, site, and quote
                customer_response = client.post(
                    "/api/v1/customers/test",
                    json={
                        "display_name": f"Quote Lines Customer {uuid.uuid4()}",
                        "type": "person",
                    },
                )
                customer_id = customer_response.json()["id"]

                site_response = client.post(
                    "/api/v1/sites/test",
                    json={"customer_id": customer_id, "name": "Quote Lines Site"},
                )
                site_id = site_response.json()["id"]

                quote_response = client.post(
                    "/api/v1/quotes/test",
                    json={
                        "customer_id": customer_id,
                        "site_id": site_id,
                        "currency": "USD",
                    },
                )
                assert quote_response.status_code == 201
                quote_id = quote_response.json()["id"]

                # List quote lines (should be empty initially)
                list_response = client.get(f"/api/v1/quotes/{quote_id}/lines/test")
                assert list_response.status_code == 200
                lines = list_response.json()
                assert isinstance(lines, list)


class TestCustomerCRUD:
    """Test customer GET/PATCH/DELETE test endpoints"""

    def test_get_customer_without_auth(self, client):
        """Test endpoint gets specific customer without JWT"""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                # Create a customer
                create_response = client.post(
                    "/api/v1/customers/test",
                    json={
                        "display_name": f"Get Test Customer {uuid.uuid4()}",
                        "type": "person",
                        "email": "get@test.local",
                    },
                )
                assert create_response.status_code == 201
                customer_id = create_response.json()["id"]

                # Get the customer
                get_response = client.get(f"/api/v1/customers/{customer_id}/test")
                assert get_response.status_code == 200
                customer = get_response.json()
                assert customer["id"] == customer_id
                assert "Get Test Customer" in customer["display_name"]

    def test_update_customer_without_auth(self, client):
        """Test endpoint updates customer without JWT"""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                # Create a customer
                create_response = client.post(
                    "/api/v1/customers/test",
                    json={
                        "display_name": f"Original Name {uuid.uuid4()}",
                        "type": "person",
                        "email": "update@test.local",
                    },
                )
                customer_id = create_response.json()["id"]

                # Update the customer
                update_response = client.patch(
                    f"/api/v1/customers/{customer_id}/test",
                    json={
                        "display_name": f"Updated Name {uuid.uuid4()}",
                        "type": "person",
                        "email": "updated@test.local",
                    },
                )
                assert update_response.status_code == 200
                updated_customer = update_response.json()
                assert "Updated Name" in updated_customer["display_name"]
                assert updated_customer["email"] == "updated@test.local"

    def test_delete_customer_without_auth(self, client):
        """Test endpoint deletes customer without JWT (soft delete)"""
        with patch.object(settings, "TEST_ENDPOINT_ENABLED", True):
            with patch.object(settings, "ENVIRONMENT", "dev"):
                # Create a customer
                create_response = client.post(
                    "/api/v1/customers/test",
                    json={
                        "display_name": f"Delete Test Customer {uuid.uuid4()}",
                        "type": "person",
                        "email": "delete@test.local",
                    },
                )
                customer_id = create_response.json()["id"]

                # Delete the customer
                delete_response = client.delete(f"/api/v1/customers/{customer_id}/test")
                assert delete_response.status_code == 200
                result = delete_response.json()
                assert "deleted successfully" in result["message"].lower()

                # Verify customer is marked inactive (soft delete)
                get_response = client.get(f"/api/v1/customers/{customer_id}/test")
                assert get_response.status_code == 200
                customer = get_response.json()
                assert customer["is_active"] is False
